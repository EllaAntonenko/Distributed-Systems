from flask import Flask, request, jsonify
import threading, time, os, logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secondary")

messages = []
messages_lock = threading.Lock()
ids_seen = set()
ids_lock = threading.Lock()

DELAY_SEC = float(os.environ.get("SECONDARY_DELAY_SEC", "0"))
PORT = int(os.environ.get("PORT", 5001))

@app.route("/replicate", methods=["POST"])
def replicate():
    data = request.get_json(silent=True)
    if not data or "id" not in data or "seq" not in data or "msg" not in data:
        return jsonify({"error": "Invalid replication payload"}), 400

    if DELAY_SEC > 0:
        logger.info("Simulating delay %s sec", DELAY_SEC)
        time.sleep(DELAY_SEC)

    entry_id = data["id"]
    with ids_lock:
        if entry_id in ids_seen:
            logger.info("Duplicate replicate received id=%s -> ack", entry_id)
            return jsonify({"ack": True}), 200
        ids_seen.add(entry_id)

    with messages_lock:
        messages.append({
            "id": data["id"],
            "seq": data["seq"],
            "msg": data["msg"],
            "ts": data.get("ts", time.time())
        })
    logger.info("Stored replicate id=%s seq=%s msg=%s", data["id"], data["seq"], data["msg"])
    return jsonify({"ack": True}), 200

@app.route("/messages", methods=["GET"])
def get_messages():
    with messages_lock:
        sorted_msgs = sorted(messages, key=lambda e: e["seq"])
        return jsonify(sorted_msgs), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
