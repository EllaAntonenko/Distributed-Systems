from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)
messages = []

logging.basicConfig(level=logging.INFO)
SECONDARIES = os.environ.get("SECONDARIES", "").split(",")

@app.route("/message", methods=["POST"])
def add_message():
    data = request.get_json()
    if not data or "msg" not in data:
        return jsonify({"error": "Message is required"}), 400

    msg = data["msg"]
    messages.append(msg)
    logging.info(f"Added message locally: {msg}")

    for sec in SECONDARIES:
        try:
            r = requests.post(f"{sec}/replicate", json={"msg": msg}, timeout=5)
            if r.status_code != 200 or r.json().get("ack") != True:
                logging.error(f"Replication to {sec} failed")
                return jsonify({"error": "Replication failed"}), 500
        except Exception as e:
            logging.error(f"Replication to {sec} failed: {e}")
            return jsonify({"error": "Replication failed"}), 500

    return jsonify({"status": "Message replicated"}), 200

@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)