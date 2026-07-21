# Webhook signature verification

The one thing you **must** get right before anything else: verifying that a
webhook delivery genuinely came from Roddy and wasn't tampered with. Both
transport-mode events and custom-skill calls are signed the same way, so this is
the shared foundation.

Pick your language:

- [`python/`](./python) — FastAPI
- [`node/`](./node) — Express

Both do the same thing: a minimal server that verifies the signature over the
**raw request body** and rejects anything that doesn't match, plus a `selftest`
that checks the implementation against a known test vector — so you can be sure
your verifier is correct **before** pointing a real webhook at it.

## The algorithm

```
signature = hex( HMAC_SHA256(secret, timestamp + body) )
```

- `secret` — your webhook's signing secret (shown once when you verify the
  webhook; regenerate it from the dashboard if lost).
- `timestamp` — the value of the `X-Roddy-Timestamp` header (ISO-8601 UTC).
- `body` — the **exact raw bytes** of the request body. Do **not** parse the
  JSON and re-serialize it before hashing: re-serialization can reorder keys,
  change spacing, or escape non-ASCII characters (e.g. `é` → `é`), and your
  signature will no longer match the one Roddy computed over the original bytes.
- Compare using a **constant-time** comparison (`hmac.compare_digest` /
  `crypto.timingSafeEqual`), not `==`.

Also reject deliveries whose `X-Roddy-Timestamp` is more than ~5 minutes old
(replay protection). Roddy sends the timestamp but does not enforce a window —
that check is yours.

## Test vector

Use this to unit-test your verifier offline. If your implementation reproduces
this signature, it's correct — including the non-ASCII case.

```
secret    = whsec_test_do_not_use_in_prod_1234567890
timestamp = 2026-01-15T12:00:00.000000+00:00
body      = {"version": "1", "event_type": "message.inbound", "data": {"text": "José ✅"}}

signature = 23e10a62fe99729b24278d75219b908d63ed27cd70dc0bcffd5d8f0ff26dd86b
```

> The `José ✅` in the body is deliberate: if your verifier re-serializes the
> body instead of using the raw bytes, it will escape those characters and
> produce a **different** signature — this vector will catch that bug.

## The verification handshake (separate, unsigned)

When you create or edit a webhook, Roddy first proves it can reach your endpoint
with an **unsigned** challenge:

```jsonc
// Roddy POSTs:
{ "type": "webhook_verification", "challenge": "a1b2c3-…", "timestamp": "…" }
// Your endpoint must reply 200 with:
{ "challenge": "a1b2c3-…" }
```

It's unsigned because the shared secret is issued only *after* verification
succeeds — so don't try to verify a signature on this request. The examples
detect `type == "webhook_verification"` and echo the challenge before doing any
signature checks.
