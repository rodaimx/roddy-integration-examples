# Custom skill — Python (FastAPI)

A **synchronous** skill: Roddy calls your webhook *during an agent run* with
`{metadata, arguments}` and **waits** for your result in the HTTP response.

## Files
- `signature.py` — webhook signature verification (same as the other examples).
- `selftest.py` — checks the verifier against the known test vector.
- `skill.py` — the skill endpoint: verify → read `arguments` → return a
  **structured** result.

## Run
```bash
pip install -r requirements.txt
python selftest.py                 # confirm the verifier is correct (no server)
cp .env.example .env               # set WEBHOOK_SECRET
uvicorn skill:app --reload --port 8000
ngrok http 8000                    # set the https URL as your use case's webhook
```

## What Roddy sends you
```jsonc
{
  "metadata": {
    "agent_id": "…", "client_id": "…", "use_case_id": "…", "webhook_id": "…",
    "contact_id": "…", "channel_id": "…",
    "contact": { "name": "…", "phone": "…", "email": "…" }
  },
  "arguments": { /* your tool's args — shape = the use case's parameter schema */ }
}
```

## What you return (structured — recommended)
HTTP **200** with an envelope that separates what the **user** sees from what the
**LLM** sees:
```jsonc
{
  "messages": [                         // >= 1; delivered to the user
    { "type": "text", "text": "…" },
    { "type": "document", "url": "https://…", "filename": "…", "mime_type": "…", "caption": "…" },
    { "type": "image", "url": "https://…", "mime_type": "…", "caption": "…" }
  ],
  "agent_result": "short summary the LLM uses to phrase its follow-up"
}
```
Message URLs must be http(s) and reachable by Roddy. Unknown top-level keys are
rejected, so stick to `messages` + `agent_result`.

> **Legacy "text" mode** (basic, not recommended): if your use case is configured
> as `text`, just return a plain-text body instead of the envelope — Roddy passes
> that string straight to the agent. Prefer structured.
