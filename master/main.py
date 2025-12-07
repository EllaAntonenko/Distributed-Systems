import os
import threading
import time
import uuid
import json
from typing import Dict, List
from queue import Queue
from dataclasses import dataclass, asdict
import requests
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI()

SECONDARIES = os.getenv("SECONDARIES", "")
REPLICA_URLS = [u.strip() for u in SECONDARIES.split(",") if u.strip()]
REPLICAS = [{"id": f"s{i+1}", "url": REPLICA_URLS[i]} for i in range(len(REPLICA_URLS))]

next_seq = 1
next_seq_lock = threading.Lock()
log: Dict[int, Dict] = {}
id_to_seq: Dict[str, int] = {}
pending_writes: Dict[int, Dict] = {}

replica_queues: Dict[str, Queue] = {}
replica_state: Dict[str, Dict] = {}
BASE_DELAY = 0.05
MAX_DELAY = 5.0
JITTER = 0.1
REQUEST_TIMEOUT = 5.0

@dataclass
class Message:
    seq: int
    id: str
    payload: str

class PostBody(BaseModel):
    id: str | None = None
    payload: str
    w: int = 1

def init_replicas():
    for idx, r in enumerate(REPLICAS):
        rid = r["id"]
        replica_queues[rid] = Queue()
        replica_state[rid] = {"last_ack": 0, "url": r["url"], "alive": True}
        t = threading.Thread(target=replica_worker, args=(rid,), daemon=True)
        t.start()

def backoff_sleep(attempt):
    d = min(MAX_DELAY, BASE_DELAY * (2 ** attempt))
    jitter = (1 + (JITTER * (2 * (0.5 - 0.0))))
    time.sleep(d * (1 + (JITTER * (0.5 - 0.5))))  # simple backoff (no random lib to avoid heavier deps)

def replica_worker(replica_id):
    url = replica_state[replica_id]["url"]
    q = replica_queues[replica_id]
    while True:
        seq = q.get()
        attempts = 0
        while True:
            msg = log.get(seq)
            if msg is None:
                break
            try:
                resp = requests.post(f"{url}/replicate", json=msg, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    mark_ack(replica_id, seq)
                    replica_state[replica_id]["last_ack"] = seq
                    replica_state[replica_id]["alive"] = True
                    break
                else:
                    attempts += 1
            except Exception:
                attempts += 1
            sleep = min(MAX_DELAY, BASE_DELAY * (2 ** attempts))
            time.sleep(sleep)

def mark_ack(replica_id, seq):
    pending = pending_writes.get(seq)
    if not pending:
        return
    with pending["cond"]:
        pending["acks"].add(replica_id)
        if len(pending["acks"]) >= pending["required"]:
            pending["cond"].notify_all()

@app.on_event("startup")
def startup():
    init_replicas()

@app.post("/messages")
def post_message(body: PostBody):
    global next_seq
    msg_id = body.id or str(uuid.uuid4())
    payload = body.payload
    w = max(1, body.w)
    if msg_id in id_to_seq:
        seq = id_to_seq[msg_id]
        return {"status": "ok", "seq": seq}

    with next_seq_lock:
        seq = next_seq
        next_seq += 1

    msg = {"seq": seq, "id": msg_id, "payload": payload}
    log[seq] = msg
    id_to_seq[msg_id] = seq

    cond = threading.Condition()
    pending_writes[seq] = {"cond": cond, "acks": set(["master"]), "required": min(w, 1 + len(REPLICAS))}
    for rid in replica_queues:
        replica_queues[rid].put(seq)

    if w == 1:
        return {"status": "ok", "seq": seq, "acked_by": ["master"]}

    with cond:
        if len(pending_writes[seq]["acks"]) >= pending_writes[seq]["required"]:
            return {"status": "ok", "seq": seq, "acked_by": list(pending_writes[seq]["acks"])}
        cond.wait()
        return {"status": "ok", "seq": seq, "acked_by": list(pending_writes[seq]["acks"])}

@app.get("/messages")
def get_messages():
    items = [log[k] for k in sorted(log.keys())]
    return items

@app.get("/entries")
def fetch_entries(from_seq: int = 1, limit: int = 1000):
    out = []
    for s in range(from_seq, max(log.keys(), default=0) + 1):
        if s in log:
            out.append(log[s])
            if len(out) >= limit:
                break
    return out

@app.get("/replicas")
def replicas():
    return {rid: replica_state[rid] for rid in replica_state}

