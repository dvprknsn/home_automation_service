from flask import Flask
import os
app = Flask(__name__)
msg = os.environ["SECRET_MSG"]

@app.get("/")
def hello():
    return msg