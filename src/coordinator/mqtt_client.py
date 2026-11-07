import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import aiomqtt

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Publish:
    topic: str
    payload: str
    retain: bool = False
    qos: int = 0


OnMessage = Callable[[str, str], Awaitable[None]]


class MqttClient:
    def __init__(
        self,
        subscriptions: list[str],
        on_message: OnMessage,
        client_id: str = "coordinator",
        status_topic: str = "coordinator/status",
        dry_run: bool = False,
    ):
        self.host = os.environ["MQTT_SRV"]
        self.port = int(os.environ.get("MQTT_PORT", "1883"))
        self.user = os.environ.get("MQTT_USER")
        self.password = os.environ.get("MQTT_PWD")

        self.subscriptions = subscriptions
        self.on_message = on_message
        self.client_id = client_id
        self.status_topic = status_topic
        self.dry_run = dry_run  # shadow mode: log instead of publishing
        self._outbox: asyncio.Queue[Publish] = asyncio.Queue()

    def publish(self, msg: Publish) -> None:
        """Queue a message. Safe to call from anywhere on the loop."""
        self._outbox.put_nowait(msg)

    async def run(self) -> None:
        """Run forever, reconnecting with capped backoff."""
        delay = 1
        while True:
            try:
                await self._session()
                delay = 1
            except aiomqtt.MqttError as e:
                log.warning("MQTT connection lost: %s (retry in %ss)", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def _session(self) -> None:
        will = aiomqtt.Will(self.status_topic, "offline", qos=1, retain=True)
        async with aiomqtt.Client(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            identifier=self.client_id,
            will=will,
        ) as client:
            log.info("Connected to %s:%s", self.host, self.port)
            await client.publish(self.status_topic, "online", qos=1, retain=True)
            for topic in self.subscriptions:
                await client.subscribe(topic)

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._receive(client))
                tg.create_task(self._send(client))

    async def _receive(self, client: aiomqtt.Client) -> None:
        async for m in client.messages:
            try:
                payload = m.payload.decode() if isinstance(m.payload, (bytes, bytearray)) else str(m.payload)
                await self.on_message(m.topic.value, payload)
            except Exception:
                # A bad handler must not kill the connection
                log.exception("Error handling %s", m.topic)

    async def _send(self, client: aiomqtt.Client) -> None:
        while True:
            msg = await self._outbox.get()
            if self.dry_run:
                log.info("[shadow] would publish %s = %s", msg.topic, msg.payload)
                continue
            await client.publish(msg.topic, msg.payload, qos=msg.qos, retain=msg.retain)