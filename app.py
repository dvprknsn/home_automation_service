import os
from dotenv import load_dotenv
from nicegui import ui

load_dotenv() 
msg = os.environ["SECRET_MSG"]

ui.label(msg)
ui.run()