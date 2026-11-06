import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv() 
msg = os.environ["SECRET_MSG"]
app = Flask(__name__)

@app.get("/")
def hello():
    return msg