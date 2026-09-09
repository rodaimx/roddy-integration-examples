"""Roddy custom skill (generic use case) — SYNCHRONOUS tool call.

Unlike transport mode (async events), a custom skill answers a tool call *during*
a Roddy agent run: Roddy POSTs ``{metadata, arguments}`` and **waits** for your
result in the HTTP response. This example uses the recommended **structured**
response (a typed envelope). A legacy "text" mode also exists — see the README.

    pip install -r requirements.txt
    python selftest.py                 # verify the signature check offline
    cp .env.example .env               # set WEBHOOK_SECRET
    uvicorn skill:app --reload --port 8000
    # expose it (ngrok http 8000) and set that URL as your use case's webhook.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Request, Response

from signature import is_fresh, is_valid_signature

app = FastAPI(title="Roddy custom skill (example)")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    raw_body = await request.body()  # RAW bytes — needed for signature verification
    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        payload = {}

    # Unsigned verification handshake (same primitive as any Roddy webhook).
    if isinstance(payload, dict) and payload.get("type") == "webhook_verification":
        return Response(
            content=json.dumps({"challenge": payload.get("challenge")}),
            media_type="application/json",
        )

    # Verify the signature over the raw body.
    ts = request.headers.get("X-Roddy-Timestamp", "")
    sig = request.headers.get("X-Roddy-Signature", "")
    if not WEBHOOK_SECRET:
        return Response("WEBHOOK_SECRET not set", status_code=500)
    if not is_fresh(ts) or not is_valid_signature(WEBHOOK_SECRET, ts, raw_body, sig):
        return Response("invalid signature", status_code=401)

    # This is a SYNCHRONOUS tool call — Roddy is WAITING for your result.
    metadata = payload.get("metadata", {})
    arguments = payload.get("arguments", {})  # shape = your use case's parameter schema
    print(
        f"[skill] use_case={metadata.get('use_case_id')} "
        f"contact={metadata.get('contact_id')} arguments={arguments}"
    )

    result = handle_tool(arguments, metadata)

    # Return HTTP 200 with the structured envelope. A non-200 is treated as a
    # tool failure by Roddy.
    return Response(content=json.dumps(result), media_type="application/json")


def handle_tool(arguments: dict, metadata: dict) -> dict:
    """Your skill's business logic. Return a **structured** envelope:

        {
          "messages": [ {type: "text"|"document"|"image", ...}, ... ],  # >= 1
          "agent_result": "short summary string for the LLM"
        }

    - ``messages`` are delivered to the **user**. Kinds (v1): ``text``
      (``{type,text}``), ``document`` (``{type,url,filename?,mime_type?,caption?}``),
      ``image`` (``{type,url,mime_type?,caption?}``). URLs must be http(s) and
      reachable by Roddy.
    - ``agent_result`` is what the **LLM** sees — a short summary so it can phrase
      a natural follow-up. The user never sees this string directly.
    - No extra top-level keys (the envelope is validated strictly).

    This demo pretends to look up an order and returns a message + its invoice.

    **Authorize the arguments against `metadata`, not just the signature.** The
    HMAC proves Roddy called you; it says nothing about whether the person in
    this conversation may see what the arguments ask for. `arguments` is filled
    in by the model from the conversation, so an end user can steer it: "give
    me the invoice for order 10432" produces exactly that call, whoever they
    are. Scope every lookup by `metadata["contact_id"]` (or your own id for
    that person) and return a not-found envelope when it does not match —
    otherwise the skill is an open read of your whole order table.
    """
    order_id = arguments.get("order_id", "UNKNOWN")
    # ... look the order up in your system here — SCOPED to this contact, e.g.
    #     order = orders.find(id=order_id, customer=metadata["contact_id"])
    #     if order is None: return _not_found_envelope(order_id)
    # Skipping that check is the whole vulnerability: the id came from the
    # model, which got it from whatever the user typed.
    return {
        "messages": [
            {
                "type": "text",
                "text": f"Your order {order_id} ships tomorrow. Here's the invoice:",
            },
            {
                "type": "document",
                "url": f"https://files.example.com/invoices/{order_id}.pdf",
                "filename": f"invoice-{order_id}.pdf",
                "mime_type": "application/pdf",
                "caption": "Invoice",
            },
        ],
        "agent_result": (
            f"Told the user order {order_id} ships tomorrow and sent the invoice PDF."
        ),
    }
