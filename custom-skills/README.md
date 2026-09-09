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

## Authorize the arguments, not just the caller

The HMAC signature proves **Roddy** called you. It says nothing about whether
the person in this conversation may see what the call asks for — and those are
different questions.

`arguments` is filled in by the model from the conversation, so an end user
steers it: "give me the invoice for order 10432" produces exactly that call,
whoever they are. Treat every argument as user-supplied input, the same way you
would a query string.

`metadata` is what you authorize against — it carries `client_id`,
`contact_id`, `channel_id` and the contact's own details, and Roddy resolved
those from the channel, not from anything said in the chat:

```python
# Scope the lookup. Never trust the id alone.
order = orders.find(id=arguments["order_id"], customer=metadata["contact_id"])
if order is None:
    return not_found_envelope()          # same answer as "does not exist"
```

### Mapping `contact_id` to your own user

`contact_id` is Roddy's id for the person, stable and present on every channel —
it is the field you authorize against. Turning it into *your* user id:

- **If your backend drives the chat** ([`../web-chat-headless/`](../web-chat-headless))
  it declares a `subject` — your own id — and `metadata["subject"]` is that same
  value echoed back. Use it directly, no lookup needed. It is **absent** on every
  other channel, so read it with `.get("subject")`.
- **On any channel**, store the pair the first time you see it: the relay's turn
  response returns `contact_id`, and for WhatsApp or email you map it when
  someone identifies themselves.

Never rebuild `contact_id` yourself from a subject. How Roddy derives it is an
internal detail that can change; read it from the payload.

Answer a denied lookup exactly like a missing one. "That order is not yours"
confirms the order exists, which is the fact you were protecting.

If a skill can act as more than one of your users, decide who it acts as
**before** it runs, from `metadata` — never from a parameter the model can
fill in. The read-only [`notify`](./notify) example takes the other way out:
it ships GETs only, precisely because it has no per-contact authorization
story.

See each language's README for run steps + the exact request/response shapes.
