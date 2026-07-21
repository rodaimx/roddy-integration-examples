# Transport mode (channel passthrough)

Turn a channel into pure transport: Roddy forwards each inbound message to your
system as a signed event, and you send replies back through the public API. Your
own AI/brain drives the conversation.

Pick your language:

- [`python/`](./python) — FastAPI receiver + `requests` send client
- [`node/`](./node) — Express receiver + `fetch` send client (Node 18+)

Both cover the two halves of an integration.

## 1. Receive events (async)

Roddy POSTs each inbound message as a signed `message.inbound` event. Verify the
signature (same as [`../webhook-verification`](../webhook-verification)), then
ACK **200** — you don't reply in this response; you reply later via the send API.
The envelope:

```jsonc
{
  "version": "1",
  "event_id": "…",               // deterministic; DEDUPE on it (stable across retries)
  "event_type": "message.inbound",
  "occurred_at": "2026-…T…+00:00",
  "channel": { "id": "…", "type": "whatsapp" },
  "contact": { "contact_id": "…", "identifiers": { "phone": "+52…" } },
  "data": {
    "text": "…",
    "media": [ /* presigned, short-lived URLs — fetch promptly, don't cache */ ],
    "provider_message_id": "…"
  }
}
```

`message.status` (delivery receipts) is a forthcoming event type; treat unknown
`event_type`s and fields as ignorable so you stay forward-compatible.

## 2. Send replies (the public API)

Authenticate with an OAuth2 **client-credentials** access token (Bearer), then:

```text
POST {RODDY_API_BASE_URL}/v1/channels/{channel_id}/contacts/{contact_id}/messages
Authorization: Bearer <access token with channel.send>
Idempotency-Key: <optional, recommended>
Content-Type: application/json
```

Message types: `text`, `whatsapp_template`, `image`/`document`/`video`/`audio`,
`interactive_buttons`/`interactive_list`, `location`, `sticker`, `carousel`. What
a given channel accepts varies (e.g. email = text only); an unsupported type →
`422 content.unsupported_for_channel`.

## Auth (client-credentials)

Create an integration in the dashboard, grant it `channel.send`, generate
credentials, and download the `.env`. Your code exchanges `CLIENT_ID` +
`CLIENT_SECRET` at `AUTH_TOKEN_URL` (ends in `/o/token/`) for a short-lived
access token — **cache it and reuse until it expires** (the endpoint is
rate-limited ~60/min; there is no refresh token). The examples' `RoddyTokenClient`
handles fetch + cache + refetch.

## Media

`upload_media` / `uploadMedia` mints a size-capped presigned upload, pushes the
bytes straight to storage, and returns the `media_url` to reference on the send.
The `media_url` must be one Roddy issued (a foreign URL → `media.url_not_owned`);
base64-in-body also works for small files (≤5 MB).

See each language's README for run steps.
