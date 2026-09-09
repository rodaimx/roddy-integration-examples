# Custom skill — Node (Express)

A **synchronous** skill: Roddy calls your webhook *during an agent run* with
`{metadata, arguments}` and **waits** for your result in the HTTP response.

## Files
- `signature.js` — webhook signature verification (same as the other examples).
- `selftest.js` — checks the verifier against the known test vector.
- `skill.js` — the skill endpoint: verify → read `arguments` → return a
  **structured** result.

## Run
```bash
npm install
npm run selftest                 # confirm the verifier is correct (no server)
cp .env.example .env             # set WEBHOOK_SECRET
node skill.js                    # listens on :8000
ngrok http 8000                  # set the https URL as your use case's webhook
```

## What Roddy sends you
```jsonc
{
  "metadata": {
    "agent_id": "…", "client_id": "…", "use_case_id": "…", "webhook_id": "…",
    "contact_id": "…", "channel_id": "…",
    "contact": { "name": "…", "phone": "…", "email": "…" },
    "subject": "…"   // only when a headless relay declared one; absent otherwise
  },
  "arguments": { /* your tool's args — shape = the use case's parameter schema */ }
}
```

Treat `metadata` as **extensible**: authorize against the fields you know
and ignore any you do not recognise.

## What you return (structured — recommended)
HTTP **200** with an envelope separating what the **user** sees from what the
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
> as `text`, return a plain-text body instead of the envelope — Roddy passes that
> string straight to the agent. Prefer structured.
