# Webhook verification — Python (FastAPI)

A minimal receiver that verifies Roddy's webhook signature over the **raw**
request body, handles the verification handshake, and ships an offline self-test
against the published test vector.

## Files
- `signature.py` — the verification logic, no framework deps. **This is the part
  to copy into your own app.**
- `app.py` — a FastAPI endpoint wiring it up (handshake + signed events).
- `selftest.py` — checks the verifier against the known test vector.

## Run
```bash
pip install -r requirements.txt
python selftest.py                 # confirm correctness first (no server needed)
cp .env.example .env               # then set WEBHOOK_SECRET
uvicorn app:app --reload --port 8000
```

Expose the port so Roddy can reach it (development):
```bash
ngrok http 8000                    # use the https URL as your webhook URL
```

## The one rule
Verify over the **raw request bytes** (`await request.body()`), never a parsed +
re-serialized copy — otherwise non-ASCII payloads (accented names, emoji) will
fail. `signature.py` takes `raw_body: bytes` precisely to make that hard to get
wrong.
