from flask import Flask, request, jsonify
import os, logging, time, uuid, threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("master")

messages = []
messages_lock = threading.Lock()

seq_lock = threading.Lock()
seq_counter = 0

SECONDARIES_RAW = os.environ.get("SECONDARIES", "")  # comma separated
SECONDARIES = [s.strip() for s in SECONDARIES_RAW.split(",") if s.strip()]
SECONDARY_TIMEOUT = float(os.environ.get("SECONDARY_TIMEOUT", "30"))  # seconds

def next_seq():
    global seq_counter
    with seq_lock:
        seq_counter += 1
        return seq_counter

def replicate_to_secondary(sec_url, entry):
    """
    Send replication request to a single secondary.
    Returns True on ACK, False otherwise.
    """
    url = sec_url.rstrip("/") + "/replicate"
    try:
        logger.info("Replicating to %s", url)
        r = requests.post(url, json=entry, timeout=SECONDARY_TIMEOUT)
        if r.status_code == 200:
            try:
                body = r.json()
                if body.get("ack") == True:
                    logger.info("ACK from %s", sec_url)
                    return True
            except Exception:
                pass
        logger.warning("Bad response from %s: %s %s", sec_url, r.status_code, r.text)
    except Exception as e:
        logger.exception("Error replicating to %s: %s", sec_url, e)
    return False

@app.route("/message", methods=["POST"])
def post_message():
    payload = request.get_json(silent=True)
    if not payload or "msg" not in payload:
        return jsonify({"error": "Message is required"}), 400

    w = payload.get("w", None)
    try:
        if w is None:
            total_nodes = 1 + len(SECONDARIES)
            w = total_nodes
        else:
            w = int(w)
    except Exception:
        return jsonify({"error": "Invalid write concern w"}), 400

    total_nodes = 1 + len(SECONDARIES)
    if w < 1 or w > total_nodes:
        return jsonify({"error": f"w must be between 1 and {total_nodes}"}), 400

    msg = payload["msg"]
    entry = {
        "id": uuid.uuid4().hex,
        "seq": None,
        "msg": msg,
        "ts": time.time()
    }

    entry["seq"] = next_seq()
    with messages_lock:
        messages.append(entry.copy())
    logger.info("Appended locally: seq=%s id=%s msg=%s", entry["seq"], entry["id"], entry["msg"])

    if w == 1:
        return jsonify({"status": "ok", "entry": entry}), 201

    ack_count = 1  
    futures = []
    executor = ThreadPoolExecutor(max_workers=max(1, len(SECONDARIES)))
    for sec in SECONDARIES:
        futures.append(executor.submit(replicate_to_secondary, sec, entry))

    success = False
    try:
        for fut in as_completed(futures, timeout=SECONDARY_TIMEOUT):
            try:
                ok = fut.result()
            except Exception:
                ok = False
            if ok:
                ack_count += 1
                logger.info("Ack count now %s (w=%s)", ack_count, w)
            if ack_count >= w:
                success = True
                logger.info("Write concern satisfied (w=%s)", w)
                break
    except Exception as e:
        logger.warning("Timeout or error while waiting for secondaries: %s", e)

    executor.shutdown(wait=False)

    if success:
        return jsonify({"status": "ok", "entry": entry, "acks": ack_count}), 201
    else:
        return jsonify({"error": "Replication failed: insufficient ACKs", "acks": ack_count}), 500

@app.route("/messages", methods=["GET"])
def get_messages():
    with messages_lock:
        sorted_msgs = sorted(messages, key=lambda e: e["seq"])
        return jsonify(sorted_msgs), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
