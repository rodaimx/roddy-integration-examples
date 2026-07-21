# Transport mode — Node (Express + fetch)

Two halves of a transport-mode integration:

- **Receive events** (`receiver.js`) — Roddy POSTs each inbound message as a
  signed `message.inbound` event; verify it and `200` ack.
- **Send replies** (`sendExample.js`) — call the public send API (text + media)
  authenticated with an OAuth2 client-credentials token.

Requires **Node 18+** (global `fetch` / `FormData` / `Blob`).

## Files
- `signature.js` — webhook signature verification (same as the verification example).
- `auth.js` — `RoddyTokenClient`: client-credentials token fetch + cache + refetch.
- `roddyClient.js` — `RoddyClient`: `sendMessage()` and `uploadMedia()`, with typed errors.
- `receiver.js` — the event receiver (Express).
- `sendExample.js` — a runnable demo: send text, then upload + send an image.

## Run — receiver
```bash
npm install
cp .env.example .env                 # set WEBHOOK_SECRET
node receiver.js                     # listens on :8000
ngrok http 8000                      # use the https URL as your webhook
```

## Run — sender
```bash
# fill the sending vars in .env (API base, token URL, client id/secret, channel, contact)
node sendExample.js
```

## Auth
Sending uses a Bearer access token from the **client-credentials** grant
(`auth.js`): `client_id` + `client_secret` → access token, cached and re-fetched
on expiry (no refresh token). Create the integration and get those credentials +
the token URL from the Roddy dashboard. Confirm the exact token endpoint against
the auth-service docs; `auth.js` supports credentials in the form body (default)
or HTTP Basic.

## Media
`uploadMedia()` mints a size-capped presigned upload, pushes the bytes straight
to storage (never through the Roddy API), and returns the `media_url` you
reference on the send. base64-in-body also works for small files.
