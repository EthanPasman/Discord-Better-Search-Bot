from flask import Flask
from threading import Thread
import waitress

app = Flask("")

@app.route('/')
def home():
  return "Web server online"

def run():
  waitress.serve(app, host="0.0.0.0", port=8080)
  #app.run(host="0.0.0.0", port=8080)

def ping():
  t = Thread(target = run)
  t.start()