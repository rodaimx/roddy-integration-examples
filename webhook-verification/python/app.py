"""Minimal Roddy webhook receiver (FastAPI).

    pip install -r requirements.txt
    python selftest.py                 # prove the verifier is correct, no server
    cp .env.example .env               # set WEBHOOK_SECRET
    uvicorn app:app --reload --port 8000

Then expose the port so Roddy can reach it, e.g. `ngrok http 8000`, and use the
resulting https URL as your webhook URL. See ../README.md.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Request, Response

from signature import is_fresh, is_valid_signature

app = FastAPI(title="Roddy webhook receiver (example)")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    # 1) Read the RAW body FIRST — the signature is over these exact bytes.
    raw_body = await request.body()

    try:
        parsed = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        parsed = {}

    # 2) Verification handshake (UNSIGNED): echo the challenge. The shared secret
    #    is issued only after verification succeeds, so do not check a signature.
    if isinstance(parsed, dict) and parsed.get("type") == "webhook_verification":
        return Response(
            content=json.dumps({"challenge": parsed.get("challenge")}),
            media_type="application/json",
        )

    # 3) Real event: verify freshness + signature over the raw body.
    timestamp = request.headers.get("X-Roddy-Timestamp", "")
    signature = request.headers.get("X-Roddy-Signature", "")
    if not WEBHOOK_SECRET:
        return Response("WEBHOOK_SECRET not set", status_code=500)
    if not is_fresh(timestamp):
        return Response("stale or missing timestamp", status_code=401)
    if not is_valid_signature(WEBHOOK_SECRET, timestamp, raw_body, signature):
        return Response("invalid signature", status_code=401)

    # 4) Verified. Handle the event, then ACK 200 quickly. Dedupe on
    #    parsed["event_id"] — it is stable across Roddy's at-least-once retries.
    print(
        f"verified event: type={parsed.get('event_type')} "
        f"id={parsed.get('event_id')} webhook={request.headers.get('X-Roddy-Webhook-Id')}"
    )
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
