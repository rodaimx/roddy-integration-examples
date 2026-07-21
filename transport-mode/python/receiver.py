"""Transport-mode event receiver (FastAPI).

Roddy forwards each inbound message on a passthrough channel here as a signed
``message.inbound`` event. Verify it, ACK 200 quickly, hand it to your brain,
and reply later via the send API (see ``send_example.py``).

    pip install -r requirements.txt
    cp .env.example .env               # set WEBHOOK_SECRET
    uvicorn receiver:app --reload --port 8000
    # expose it: ngrok http 8000  → use the https URL as your webhook
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Request, Response

from signature import is_fresh, is_valid_signature

app = FastAPI(title="Roddy transport-mode receiver (example)")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    raw_body = await request.body()  # RAW bytes — needed for signature verification
    try:
        event = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        event = {}

    # Unsigned verification handshake.
    if isinstance(event, dict) and event.get("type") == "webhook_verification":
        return Response(
            content=json.dumps({"challenge": event.get("challenge")}),
            media_type="application/json",
        )

    # Verify freshness + signature over the raw body.
    ts = request.headers.get("X-Roddy-Timestamp", "")
    sig = request.headers.get("X-Roddy-Signature", "")
    if not WEBHOOK_SECRET:
        return Response("WEBHOOK_SECRET not set", status_code=500)
    if not is_fresh(ts) or not is_valid_signature(WEBHOOK_SECRET, ts, raw_body, sig):
        return Response("invalid signature", status_code=401)

    # Dispatch by event_type. Dedupe on event_id (stable across at-least-once retries).
    if event.get("event_type") == "message.inbound":
        data = event.get("data", {})
        contact = event.get("contact", {})
        print(
            f"[inbound] event_id={event.get('event_id')} "
            f"contact={contact.get('contact_id')} "
            f"text={data.get('text')!r} media_count={len(data.get('media', []))}"
        )
        # -> your brain decides a reply, then you call the send API. Media URLs
        #    in data['media'] are presigned + short-lived: fetch promptly.
    else:
        # message.status and future event types land here until you handle them.
        print(f"[event] unhandled event_type={event.get('event_type')}")

    # ACK. Return 2xx only once you've durably accepted the event.
    return Response(content=json.dumps({"status": "ok"}), media_type="application/json")
