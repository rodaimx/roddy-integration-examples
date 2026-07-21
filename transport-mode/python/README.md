# Transport mode — Python (FastAPI + requests)

Two halves of a transport-mode integration:

- **Receive events** (`receiver.py`) — Roddy POSTs each inbound message as a
  signed `message.inbound` event; verify it and `200` ack.
- **Send replies** (`send_example.py`) — call the public send API (text + media)
  authenticated with an OAuth2 client-credentials token.

## Files
- `signature.py` — webhook signature verification (same as the verification example).
- `auth.py` — `RoddyTokenClient`: client-credentials token fetch + cache + refetch.
- `roddy_client.py` — `RoddyClient`: `send_message()` and `upload_media()`, with typed errors.
- `receiver.py` — the event receiver (FastAPI).
- `send_example.py` — a runnable demo: send text, then upload + send an image.

## Run — receiver
```bash
pip install -r requirements.txt
cp .env.example .env                       # set WEBHOOK_SECRET
uvicorn receiver:app --reload --port 8000
ngrok http 8000                            # use the https URL as your webhook
```

## Run — sender
```bash
# fill the sending vars in .env (API base, token URL, client id/secret, channel, contact)
python send_example.py
```

## Auth
Sending uses a Bearer access token from the **client-credentials** grant
(`auth.py`): your `client_id` + `client_secret` → access token, cached and
re-fetched on expiry (no refresh token). Create the integration and get those
credentials + the token URL from the Roddy dashboard. Confirm the exact token
endpoint against the auth-service docs; `auth.py` supports credentials in the
form body (default) or HTTP Basic.

## Media
`upload_media()` mints a size-capped presigned upload, pushes the bytes straight
to storage (never through the Roddy API — bypasses the request-size limit and
lets storage enforce the size cap), and returns the `media_url` you reference on
the send. base64-in-body also works for small files.
