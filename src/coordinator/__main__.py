import asyncio
import logging
import sys

from dotenv import load_dotenv

from .mqtt_client import MqttClient

load_dotenv()
logging.basicConfig(level=logging.INFO)


async def on_message(topic: str, payload: str) -> None:
    logging.info("%s = %s", topic, payload)


async def main() -> None:
    mqtt = MqttClient(["home/#"], on_message, dry_run=True)
    await mqtt.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        # aiomqtt/paho needs add_reader, which Windows' default Proactor loop lacks
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main()) 