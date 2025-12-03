from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
messages = []

logging.basicConfig(level=logging.INFO)

@app.route("/replicate", methods=["POST"])
def replicate():
    data = request.get_json()
    if not data or "msg" not in data:
        return jsonify({"error": "Message is required"}), 400

    msg = data["msg"]
    messages.append(msg)
    logging.info(f"Replicated message: {msg}")

    return jsonify({"ack": True})

@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)