# Custom skills (generic use case)

A custom skill lets your endpoint answer a **tool call during a Roddy agent run**
— the **synchronous** counterpart to transport mode. Roddy POSTs
`{metadata, arguments}` to your webhook and **waits** for your result in the HTTP
response; the agent uses it to continue the conversation.

Pick your language:

- [`python/`](./python) — FastAPI
- [`node/`](./node) — Express

Same signed webhook primitive as everything else (verify with
[`../webhook-verification`](../webhook-verification)); the difference is you
**return a result** instead of acking an event.

## Sync (custom skill) vs async (transport mode)

| | Custom skill | Transport mode |
|---|---|---|
| Roddy sends you | `{ metadata, arguments }` (a tool call) | a `message.inbound` **event** |
| You respond with | the **result** in the HTTP body | `200` ack (you reply later via the send API) |
| Timing | during an agent run — Roddy **waits** | fire-and-forget |

## What you return: structured (recommended)

HTTP **200** with a typed envelope that separates what the **user** sees from
what the **LLM** sees:

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

Message kinds (v1): `text` / `document` / `image`. URLs must be http(s) and
reachable by Roddy. Unknown top-level keys are rejected.

> A legacy **text** mode exists (return a plain-text body instead of the
> envelope) but is basic — prefer structured.

See each language's README for run steps + the exact request/response shapes.
