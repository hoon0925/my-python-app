from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)

@app.route("/")
def hello():
    return jsonify({
        "message": "Hello v2! Pipeline rocks!",
        "version": os.getenv("APP_VERSION", "dev"),
        "hostname": socket.gethostname()
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
