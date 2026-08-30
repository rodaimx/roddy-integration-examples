"""Transport-mode receiver whose brain is the Claude Code CLI.

Roddy forwards each inbound message as a signed `message.inbound` event. This
endpoint verifies it, **acks 200 immediately**, and does the slow work in the
background: run `claude -p`, then send the reply through the public send API.

    pip install -r requirements.txt
    python selftest.py                 # offline signature check
    cp .env.example .env               # webhook secret + send-API credentials
    uvicorn receiver:app --port 8000
    ngrok http 8000                    # that https URL is the webhook

The ack-first shape is the whole point. A `claude -p` turn takes seconds to
minutes; holding the HTTP response open that long means SQS gives up and
redelivers, and the person gets the same answer twice.
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import BackgroundTasks, FastAPI, Request, Response

from auth import RoddyTokenClient
from brain import ask_claude
from roddy_client import RoddyClient, RoddySendError
from signature import is_fresh, is_valid_signature

app = FastAPI(title="Roddy transport mode — Claude Code brain")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

_tokens = RoddyTokenClient(
    os.environ.get("AUTH_TOKEN_URL", ""),
    os.environ.get("CLIENT_ID", ""),
    os.environ.get("CLIENT_SECRET", ""),
)
_roddy = RoddyClient(os.environ.get("RODDY_API_BASE_URL", ""), _tokens)

# event_id is a deterministic uuid5 of stable fields, so a redelivered event
# carries the SAME id. Dedupe on it or you pay for the same turn twice — and
# with this brain a turn is not cheap. In-process is fine for a test; a real
# deployment needs shared storage.
_handled: set[str] = set()


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks) -> Response:
    raw_body = await request.body()  # RAW bytes — required for verification
    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        payload = {}

    if isinstance(payload, dict) and payload.get("type") == "webhook_verification":
        return Response(
            content=json.dumps({"challenge": payload.get("challenge")}),
            media_type="application/json",
        )

    ts = request.headers.get("X-Roddy-Timestamp", "")
    sig = request.headers.get("X-Roddy-Signature", "")
    if not WEBHOOK_SECRET:
        return Response("WEBHOOK_SECRET not set", status_code=500)
    fresh = is_fresh(ts)
    signed = is_valid_signature(WEBHOOK_SECRET, ts, raw_body, sig)
    if not fresh or not signed:
        # Say which check failed. "invalid signature" alone sends you hunting
        # for a secret mismatch when it was clock skew — or the wrong .env.
        print(f"[receiver] 401 fresh={fresh} signature_ok={signed} ts={ts!r}")
        return Response("invalid signature", status_code=401)

    event_type = payload.get("event_type")
    event_id = payload.get("event_id") or ""

    if event_type != "message.inbound":
        # Unknown/forthcoming event types must be ignorable, not fatal.
        print(f"[receiver] ignoring event_type={event_type!r}")
        return Response(status_code=200)

    if event_id in _handled:
        print(f"[receiver] duplicate event {event_id} — already handled")
        return Response(status_code=200)
    _handled.add(event_id)

    channel_id = (payload.get("channel") or {}).get("id", "")
    contact_id = (payload.get("contact") or {}).get("contact_id", "")
    text = (payload.get("data") or {}).get("text") or ""
    print(f"[receiver] inbound contact={contact_id} text={text[:80]!r}")

    if text.strip():
        background.add_task(reply, channel_id, contact_id, text, event_id)

    # ACK NOW. Everything above is cheap; everything slow runs after this.
    return Response(status_code=200)


def reply(channel_id: str, contact_id: str, text: str, event_id: str) -> None:
    answer = ask_claude(text, contact_id)
    try:
        _roddy.send_message(
            channel_id,
            contact_id,
            {"message_type": "text", "text": answer},
            # Derived from the event so a retry of this task replays the send
            # instead of posting a second message.
            idempotency_key=str(uuid.uuid5(uuid.NAMESPACE_URL, event_id or answer)),
        )
        print(f"[receiver] replied to {contact_id} ({len(answer)} chars)")
    except RoddySendError as error:
        print(
            f"[receiver] send failed status={error.status} code={error.code} "
            f"retriable={error.retriable}: {error.message}"
        )
