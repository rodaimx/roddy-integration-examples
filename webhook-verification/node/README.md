# Webhook verification — Node (Express)

A minimal receiver that verifies Roddy's webhook signature over the **raw**
request body, handles the verification handshake, and ships an offline self-test
against the published test vector.

## Files
- `signature.js` — the verification logic, Node `crypto` only. **This is the
  part to copy into your own app.**
- `server.js` — an Express endpoint wiring it up (handshake + signed events).
- `selftest.js` — checks the verifier against the known test vector.

## Run
```bash
npm install
npm run selftest                 # confirm correctness first (no server needed)
cp .env.example .env             # then set WEBHOOK_SECRET
npm start                        # listens on :8000
```

Expose the port so Roddy can reach it (development):
```bash
ngrok http 8000                  # use the https URL as your webhook URL
```

## The one rule
Capture the **raw body** (`express.raw`) and verify over that — never
`JSON.stringify(req.body)`, or non-ASCII payloads (accented names, emoji) will
fail signature checks. `signature.js` takes the raw bytes precisely so this is
hard to get wrong.
