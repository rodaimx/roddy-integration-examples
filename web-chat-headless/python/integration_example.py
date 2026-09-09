"""Server-to-server web chat: the integration relay + synchronous mode.

    cp .env.example .env    # fill the AUTH_* / CLIENT_* / CHANNEL_ID values
    python integration_example.py "hola, ¿tienen inventario del SKU 123?"

Your backend authenticates as an OAuth integration (client_credentials) whose
application holds the `web_chat.converse` scope, DECLARES which of your users
the turn is for (`subject` — you are accountable for it), and asks for one
JSON body instead of a stream (`Accept: application/json`). Useful when the
consumer is a server job, not a browser.

Send `subject_name` (and optionally `subject_email`) too. They are optional
and easy to skip, and skipping them is the mistake worth avoiding: `subject`
is an id, so without a name your operators get an inbox of ids, and the agent
reads that stand-in as the name of whoever it is talking to. They are the
relay's equivalent of the visitor token's `name` / `email` claims.

Reading the conversation back uses the same declared subject:
`GET /history?channel_id=…&subject=…`.

If you ALSO expose custom skills to this agent, see the `contact_id` note in
`main()` below: it is what links a skill webhook back to your own user.
"""

from __future__ import annotations

import os
import sys
import uuid

import requests

RODDY_WEB_CHAT_URL = os.environ["RODDY_WEB_CHAT_URL"].rstrip("/")
AUTH_TOKEN_URL = os.environ["AUTH_TOKEN_URL"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
SUBJECT = os.environ.get("SUBJECT", "crm-user-42")
# Display hints for the SAME person `SUBJECT` identifies. Keep them together:
# an id that changes while a hardcoded name stays put mislabels the contact.
SUBJECT_NAME = os.environ.get("SUBJECT_NAME", "Usuario CRM 42")
SUBJECT_EMAIL = os.environ.get("SUBJECT_EMAIL") or None


def get_access_token() -> str:
    response = requests.post(
        AUTH_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(os.environ["CLIENT_ID"], os.environ["CLIENT_SECRET"]),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def converse_sync(token: str, text: str) -> dict:
    response = requests.post(
        f"{RODDY_WEB_CHAT_URL}/",
        json={
            "channel_id": CHANNEL_ID,
            # Who this turn is for — YOUR id for the end user. Same subject,
            # same conversation. Refused outside the integration mode.
            "subject": SUBJECT,
            # Optional, and worth sending: this is what your operators and the
            # agent see instead of the raw id. Omit them and the contact shows
            # up as a stand-in name that sticks.
            "subject_name": SUBJECT_NAME,
            **({"subject_email": SUBJECT_EMAIL} if SUBJECT_EMAIL else {}),
            "trigger": "submit-message",
            "id": "server-job",
            "messages": [
                {
                    "id": uuid.uuid4().hex,
                    "role": "user",
                    "parts": [{"type": "text", "text": text}],
                }
            ],
        },
        headers={
            "Authorization": f"Bearer {token}",
            # The sync switch: one JSON body, no SSE.
            "Accept": "application/json",
        },
        timeout=300,
    )
    if response.status_code == 429:
        raise SystemExit(
            f"rate_limited — retry in {response.headers.get('Retry-After')}s"
        )
    response.raise_for_status()
    return response.json()


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else "hola"
    result = converse_sync(get_access_token(), text)
    status = result["turn_status"]

    # THE LINE THAT MATTERS IF YOU ALSO USE CUSTOM SKILLS.
    #
    # `contact_id` is Roddy's id for the person this turn is about — derived
    # from the `subject` you declared. When the agent later calls one of your
    # custom skills, the webhook arrives with `metadata.contact_id`, and that
    # is the field you authorize against. Store this pair ONCE and every skill
    # call afterwards resolves to your own user:
    #
    #     your_db.save_chat_contact(contact_id=result["contact_id"], user_id=SUBJECT)
    #
    # Never derive it yourself from the subject: how Roddy builds it is an
    # internal detail that can change. Read it from here.
    print(f"contact_id: {result['contact_id']}  (tu usuario: {SUBJECT})")

    if status["agent_ran"]:
        print(result["text"])
    else:
        # A 200 without the agent is a normal operating mode (human-only
        # channel, paused contact…): the message WAS accepted when
        # `message_accepted` says so, and an operator will answer.
        print(f"turno sin agente: {status['reason']} (accepted={status['message_accepted']})")


if __name__ == "__main__":
    main()
