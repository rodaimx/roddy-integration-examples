"""Roddy custom skill — read Rodai Notify tasks during an agent run.

A working variant of ``../python/skill.py`` that answers with real data instead
of a canned example. Roddy POSTs ``{metadata, arguments}`` and **waits**; this
endpoint queries the Notify API and returns the structured envelope.

    pip install -r requirements.txt
    python selftest.py                 # offline: signature vector + config check
    cp .env.example .env               # set WEBHOOK_SECRET
    uvicorn skill:app --reload --port 8000
    ngrok http 8000                    # use that https URL as the webhook

READ-ONLY. Every action is a GET. See the README before adding writes — an
agent that can create or move cards on a shared board needs an authorization
story this example deliberately does not have.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Request, Response

from notify_client import NotifyClient, NotifyError
from signature import is_fresh, is_valid_signature

app = FastAPI(title="Roddy custom skill — Notify (read-only)")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

# Built once: reading config on every call would re-stat the filesystem while
# an agent run — and a person — is blocked waiting on us.
_client: NotifyClient | None = None
_client_error: str | None = None
try:
    _client = NotifyClient()
except NotifyError as exc:
    _client_error = exc.detail


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

    ts = request.headers.get("X-Roddy-Timestamp", "")
    sig = request.headers.get("X-Roddy-Signature", "")
    if not WEBHOOK_SECRET:
        return Response("WEBHOOK_SECRET not set", status_code=500)
    # Log WHICH check failed. "invalid signature" alone sends you hunting for a
    # secret mismatch when the real cause is often clock skew or a header the
    # proxy renamed. Never log the secret or the expected signature.
    fresh = is_fresh(ts)
    signed = is_valid_signature(WEBHOOK_SECRET, ts, raw_body, sig)
    if not fresh or not signed:
        print(
            f"[skill] 401 fresh={fresh} signature_ok={signed} "
            f"ts={ts!r} sig_len={len(sig)} body_len={len(raw_body)}"
        )
        return Response("invalid signature", status_code=401)

    metadata = payload.get("metadata", {})
    arguments = payload.get("arguments", {})
    print(
        f"[skill] use_case={metadata.get('use_case_id')} "
        f"contact={metadata.get('contact_id')} arguments={arguments}"
    )

    result = handle_tool(arguments, metadata)
    return Response(content=json.dumps(result), media_type="application/json")


def _envelope(text: str, agent_result: str) -> dict:
    return {"messages": [{"type": "text", "text": text}], "agent_result": agent_result}


def handle_tool(arguments: dict, metadata: dict) -> dict:
    """Dispatch on ``action`` and return the structured envelope.

    One webhook backs one Roddy use case, so the operations live behind an
    ``action`` argument rather than as separate endpoints. Declare it as an
    enum in the use case's parameter schema so the model picks a valid value.

    Argument schema:
        action     "list_projects" | "list_cards" | "get_card"   (required)
        query      free text — matches project or card names
        project_id int — required by list_cards
        card_id    int — required by get_card

    Failures come back as a normal 200 envelope, not an HTTP error: the agent
    can then tell the user what went wrong instead of surfacing a tool crash.
    """
    if _client is None:
        return _envelope(
            "No puedo consultar Notify ahora mismo: falta configurar el acceso.",
            f"Notify client unavailable: {_client_error}. Told the user it is unavailable.",
        )

    action = (arguments.get("action") or "").strip()

    try:
        if action == "list_projects":
            projects = _client.list_projects(search=arguments.get("query"))
            if not projects:
                return _envelope(
                    "No encontré tableros con ese criterio.",
                    "No projects matched. Suggest the user rephrase the search.",
                )
            lines = [f"• {p.get('name')} (id {p.get('id')})" for p in projects]
            return _envelope(
                "Tableros que encontré:\n" + "\n".join(lines),
                f"Listed {len(projects)} projects: "
                + ", ".join(f"{p.get('name')}#{p.get('id')}" for p in projects),
            )

        if action == "list_cards":
            project_id = arguments.get("project_id")
            if not project_id:
                return _envelope(
                    "¿De qué tablero quieres las tarjetas?",
                    "Missing project_id. Asked the user which board.",
                )
            cards = _client.list_cards(
                project_id=int(project_id),
                search=arguments.get("query"),
                assignee_id=arguments.get("assignee_id"),
            )
            if not cards:
                return _envelope(
                    "Ese tablero no tiene tarjetas que coincidan.",
                    "No cards matched in that project.",
                )
            lines = [
                f"• #{c.get('id')} {c.get('name')} — {c.get('custom_status_name') or 'sin columna'}"
                for c in cards
            ]
            return _envelope(
                "Tarjetas:\n" + "\n".join(lines),
                f"Listed {len(cards)} cards from project {project_id}.",
            )

        if action == "get_card":
            card_id = arguments.get("card_id")
            if not card_id:
                return _envelope(
                    "¿Qué tarjeta quieres ver?",
                    "Missing card_id. Asked the user which card.",
                )
            card = _client.get_card(int(card_id))
            text = (
                f"#{card.get('id')} — {card.get('name')}\n"
                f"Columna: {card.get('custom_status_name') or 'sin columna'}\n"
                f"Horas registradas: {card.get('logged_time_hours', '0')}"
            )
            return _envelope(
                text,
                f"Card {card_id}: {card.get('name')}, "
                f"status {card.get('custom_status_name')}.",
            )

    except NotifyError as exc:
        # Don't leak the upstream body into the chat; the agent gets the gist.
        print(f"[skill] notify error status={exc.status} detail={exc.detail!r}")
        return _envelope(
            "No pude consultar Notify en este momento.",
            f"Notify call failed with status {exc.status}. Told the user it failed; "
            "do not retry automatically.",
        )
    except (TypeError, ValueError) as exc:
        print(f"[skill] bad arguments: {exc}")
        return _envelope(
            "Esos datos no me cuadran; ¿me los repites?",
            f"Invalid arguments: {exc}. Asked the user to restate them.",
        )

    return _envelope(
        "Esa operación no está disponible.",
        f"Unknown action {action!r}. Valid: list_projects, list_cards, get_card.",
    )
