import os
import time
import json
import threading
from typing import Dict
from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import random

app = FastAPI()

REPLICA_ID = os.getenv("REPLICA_ID", "s1")
MASTER_URL = os.getenv("MASTER_URL", "http://master:8000")
PROCESS_DELAY_MS = int(os.getenv("PROCESS_DELAY_MS", "0"))
START_DELAY_SEC = int(os.getenv("START_DELAY_SEC", "0"))

PERSIST_FILE = f"/data/{REPLICA_ID}_log.jsonl"
SEEN_FILE = f"/data/{REPLICA_ID}_seen.json"
os.makedirs("/data", exist_ok=True)

applied_seq = 0
pending_buffer: Dict[int, Dict] = {}
seen_ids = set()
persist_lock = threading.Lock()
persisted_log = []

class ReplicateBody(BaseModel):
    seq: int
    id: str
    payload: str

def load_state():
    global applied_seq, persisted_log, seen_ids
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            persisted_log = [json.loads(l) for l in lines]
            if persisted_log:
                applied_seq = max(e["seq"] for e in persisted_log if "seq" in e)
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                seen_ids = set(json.load(f))
        except:
            seen_ids = set()

def persist_entry(msg):
    with persist_lock:
        with open(PERSIST_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        persisted_log.append(msg)
        seen_ids.add(msg["id"])
        with open(SEEN_FILE, "w", encoding="utf-8") as sf:
            json.dump(list(seen_ids), sf)

def try_apply_buffered():
    global applied_seq
    progressed = True
    while progressed:
        progressed = False
        nxt = applied_seq + 1
        if nxt in pending_buffer:
            entry = pending_buffer.pop(nxt)
            applied_seq = nxt
            progressed = True

@app.on_event("startup")
def startup():
    if START_DELAY_SEC > 0:
        time.sleep(START_DELAY_SEC)
    load_state()
    threading.Thread(target=initial_sync, daemon=True).start()

def initial_sync():
    global applied_seq
    from_seq = applied_seq + 1
    try:
        resp = requests.get(f"{MASTER_URL}/entries", params={"from_seq": from_seq, "limit": 1000}, timeout=5)
        if resp.status_code == 200:
            entries = resp.json()
            for e in entries:
                if e["id"] in seen_ids:
                    continue
                persist_entry(e)
                pending_buffer[e["seq"]] = e
            try_apply_buffered()
    except Exception:
        pass

@app.post("/replicate")
def replicate(body: ReplicateBody):
    if PROCESS_DELAY_MS > 0:
        time.sleep(PROCESS_DELAY_MS / 1000.0)

    seq = body.seq
    mid = body.id
    payload = body.payload

    if mid in seen_ids:
        return {"acked": True, "seq": seq}

    msg = {"seq": seq, "id": mid, "payload": payload}
    try:
        persist_entry(msg)
    except Exception:
        return {"error": "persist_fail"}, 500

    pending_buffer[seq] = msg

    try_apply_buffered()

    if random.random() < 0.05:
        return {"error": "random_fail_after_persist"}, 500

    return {"acked": True, "seq": seq}

@app.get("/messages")
def get_messages():
    results = []
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                if e["seq"] <= applied_seq:
                    results.append(e)
    results_sorted = sorted(results, key=lambda x: x["seq"])
    return results_sorted

@app.get("/status")
def status():
    return {"replica": REPLICA_ID, "applied_seq": applied_seq, "buffered": list(pending_buffer.keys()), "seen_count": len(seen_ids)}
