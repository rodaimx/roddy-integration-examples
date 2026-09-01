"""Interactive terminal chat against a Roddy web-chat channel (visitor mode).

    cp .env.example .env    # fill RODDY_WEB_CHAT_URL, CHANNEL_ID, CHANNEL_VISITOR_SECRET
    python chat.py

What it demonstrates, in the order a real frontend does it:

1. Mint a visitor token (server-side act — here in-process for the demo).
2. `GET /history` and seed the transcript with it, VERBATIM.
3. Each turn: append the user message, `POST /` the WHOLE transcript, and
   print the agent's answer as it streams (SSE, Vercel AI SDK v5 protocol).

The replay rule is the one thing people get wrong: the API expects the full
conversation each turn, exactly as it handed it to you. This client never
reshapes a message it received — it only appends.
"""

from __future__ import annotations

import json
import os
import uuid

import requests

from mint_token import mint_visitor_token

BASE_URL = os.environ["RODDY_WEB_CHAT_URL"].rstrip("/")
CHANNEL_ID = os.environ["CHANNEL_ID"]


def fetch_history(token: str) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/history",
        params={"channel_id": CHANNEL_ID},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["messages"]


def stream_turn(token: str, messages: list[dict]) -> list[dict]:
    """POST the transcript, print text deltas as they arrive, and return the
    assistant message parts so the caller can append them to the transcript."""
    response = requests.post(
        f"{BASE_URL}/",
        json={
            "channel_id": CHANNEL_ID,
            "trigger": "submit-message",
            "id": "terminal-demo",
            "messages": messages,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=300,
        stream=True,
    )
    if response.status_code != 200:
        # Stable machine-readable codes — 401 visitor_token_expired means
        # "mint a fresh token and retry", everything else see the reference.
        raise SystemExit(f"HTTP {response.status_code}: {response.text[:300]}")

    assistant_text: list[str] = []
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[len("data: ") :]
        if payload == "[DONE]":
            break
        chunk = json.loads(payload)
        kind = chunk.get("type")
        if kind == "finish":
            # A turn no agent answered (human-only channel, transport mode) ends
            # at `finish` and never sends [DONE] — verified on the wire. This
            # reader would also exit when the body closes, but stopping on the
            # protocol's own end-of-turn keeps a keep-alive connection from
            # holding the loop open, and is what a hand-rolled client needs.
            break
        if kind == "error":
            # A mid-stream failure keeps HTTP 200: the stream says so, not the
            # status code.
            raise SystemExit(f"\nstream error: {chunk.get('errorText')}")
        if kind == "text-delta":
            delta = chunk.get("delta", "")
            assistant_text.append(delta)
            print(delta, end="", flush=True)
        elif kind == "data-roddy-turn-status":
            # The turn ended without the agent (no agent configured, contact
            # paused, …). `message_accepted` says the message DID land.
            status = chunk.get("data", {})
            print(f"[turno sin agente: {status.get('reason')}]", end="")
    print()

    return [
        {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "parts": [{"type": "text", "text": "".join(assistant_text)}],
        }
    ]


def main() -> None:
    token = mint_visitor_token(
        visitor_secret=os.environ["CHANNEL_VISITOR_SECRET"],
        user_id=os.environ.get("VISITOR_USER_ID", "demo-user-1"),
        name=os.environ.get("VISITOR_NAME", "Demo"),
    )

    messages = fetch_history(token)
    print(f"({len(messages)} mensaje(s) previos)  Ctrl+C para salir.\n")

    while True:
        text = input("tú> ").strip()
        if not text:
            continue
        messages.append(
            {
                "id": uuid.uuid4().hex,
                "role": "user",
                "parts": [{"type": "text", "text": text}],
            }
        )
        print("agente> ", end="", flush=True)
        messages.extend(stream_turn(token, messages))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):  # Ctrl+C / Ctrl+D / piped-input EOF
        print()
