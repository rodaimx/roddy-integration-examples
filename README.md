# Roddy Integration Examples

Runnable, copy-paste reference projects for integrating with the **Roddy**
platform — receiving webhook events and calling the send API. Clone a folder,
set a few environment variables, run it. Every example is self-contained.

> These examples target **v1** of the Roddy integration contract. They are
> maintained alongside the platform; if anything here disagrees with the API in
> practice, open an issue.

## The webhook is one primitive, used two ways

Roddy signs and delivers to your endpoint the same way in both cases (see
[`webhook-verification/`](./webhook-verification) — read this first). What
differs is the **interaction model**:

| Model | Directory | Roddy sends you | You respond with | Sync? |
|---|---|---|---|---|
| **Channel transport mode** (a.k.a. passthrough) | [`transport-mode/`](./transport-mode) | an **event** (`message.inbound`, …) | `200 OK` (ack) — you reply later via the **send API** | async |
| **Custom skills** (generic use case) | [`custom-skills/`](./custom-skills) | a tool call: `{ metadata, arguments }` | the **result** in the HTTP response body | sync |

- **Transport mode** turns a channel into pure transport: Roddy forwards each
  inbound message to your system, and you send replies back through the public
  send API. Your AI/brain drives the conversation.
- **Custom skills** let your endpoint answer a tool call *during* a Roddy agent
  run: Roddy POSTs the arguments and waits for your result.

Both verify the signature identically; only the payload and the response
contract differ.

## Repository layout

```
webhook-verification/   # the shared security primitive, done right + a test vector
  python/   node/
transport-mode/         # receive events (async) + send via the public API (+ media)
  python/   node/
custom-skills/          # sync tool call: receive {metadata,arguments}, return a structured result
  python/   node/
```

## Security model (read once, applies everywhere)

Every delivery Roddy sends carries three headers:

| Header | Meaning |
|---|---|
| `X-Roddy-Signature` | hex HMAC-SHA256 (lowercase, 64 chars, **no prefix**) |
| `X-Roddy-Timestamp` | ISO-8601 UTC timestamp used in the signature |
| `X-Roddy-Webhook-Id` | which of your webhooks this is |

The signature is `HMAC_SHA256(secret, timestamp + body)` over the **exact raw
bytes** of the request body. **Always verify over the raw body** — never
re-serialize the parsed JSON first, or non-ASCII characters (accented names,
emoji) will change and the signature won't match. Reject deliveries whose
timestamp is older than a few minutes (recommended: 5). Full walkthrough +
runnable code + a fixed **test vector** in [`webhook-verification/`](./webhook-verification).

The **verification handshake** (when you create/edit a webhook) is a separate,
**unsigned** challenge-response: Roddy POSTs `{ "type": "webhook_verification",
"challenge": "…" }` and your endpoint echoes `{ "challenge": "…" }` with `200`.
It is unsigned because the shared secret is issued only *after* verification
succeeds. The examples handle both paths.

## Authentication (for calling the send API)

Outbound calls use a **Bearer access token** from the **OAuth 2.0
client-credentials** grant (server-to-server; no refresh token). In the Roddy
dashboard you create an integration, grant it `channel.send`, generate
credentials, and download a `.env` with `AUTH_TOKEN_URL` (the token endpoint,
ends in `/o/token/`), `CLIENT_ID`, and `CLIENT_SECRET`. Your code exchanges those
at `AUTH_TOKEN_URL` for a short-lived token and sends it as
`Authorization: Bearer …` to the API (`RODDY_API_BASE_URL` — a **different**
host). **Cache the token until it expires** — the token endpoint is rate-limited
(~60 requests/min per credential). The `transport-mode/` examples' token client
does all of this.

## Roadmap

- An OpenAPI specification for the API (Postman import + client/SDK generation).
- Official SDKs.

## License

MIT — see [LICENSE](./LICENSE).
