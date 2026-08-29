# Transport mode — `claude -p` as the brain

The channel is pure transport: Roddy forwards each inbound message, this
receiver produces the reply by shelling out to the **Claude Code CLI** in
headless mode, and sends it back through the public API.

Built for a local experiment behind a tunnel. Read *Cost* and *Tools* before
pointing it at anything real.

| File | What it is |
|---|---|
| `receiver.py` | verify → **ack 200** → background: brain + send |
| `brain.py` | the `claude -p` invocation: tools, session continuity, error handling |
| `auth.py`, `roddy_client.py`, `signature.py` | copied from [`../python`](../python) |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python selftest.py          # offline signature check
cp .env.example .env                  # secret + send-API credentials
set -a; . ./.env; set +a
.venv/bin/uvicorn receiver:app --port 8000
ngrok http 8000                       # that https URL is the webhook
```

Then in Roddy: create a webhook at that URL, verify it (the secret is shown
**once** — put it in `.env`), and set the channel to `routing_mode: passthrough`
subscribed to `message.inbound`.

## Ack first, think later

The receiver returns **200 before** running the brain. That is not an
optimization, it is the contract: a `claude -p` turn takes seconds to minutes,
and a webhook held open that long is treated as failed — SQS redelivers and the
person gets answered twice.

Two consequences the code handles:

- **Dedupe on `event_id`.** It is a deterministic uuid5 of stable fields, so a
  redelivered event carries the *same* id. Without the check you pay for the
  same turn twice. In-process here; real deployments need shared storage.
- **Idempotency key on the send**, derived from the event, so a retried
  background task replays the message instead of posting a second one.

## Session continuity without a database

The CLI session id is `uuid5(namespace, contact_id)`, so a contact always
resumes the same conversation and restarting this process loses nothing. The
first message for a contact uses `--session-id` (creates); later ones use
`--resume` (continues). Passing both is a conflict, so the code picks per
contact and forgets a contact whose resume fails, letting the next message
start fresh.

## Tools — the part that deserves a decision

`CLAUDE_ALLOWED_TOOLS` takes three shapes:

| Value | Effect |
|---|---|
| `""` (default) | no tools; the agent only converses |
| `"Read Glob Grep"` | only those, over `CLAUDE_WORKDIR` |
| `"UNRESTRICTED"` | every Claude Code tool including Bash, via `--dangerously-skip-permissions` |

The input to this agent is whatever someone typed into a chat channel, and it
becomes the prompt of a process running on your machine. Headless mode cannot
prompt for approval, so under `UNRESTRICTED` there is nothing between a chat
message and a shell command. That is defensible on a channel only you can reach
(`access_mode: authenticated`, one tenant, a test). It is not defensible on a
WhatsApp line.

`CLAUDE_WORKDIR` defaults to `/tmp/roddy-claude-brain` rather than a repository
for the same reason: if tools are on, that directory is the blast radius.

## Cost

Measured on this setup, replying `"Anotado: 42."` to a one-line message:

```
[brain] turn cost=$0.1062
```

~28k tokens per turn before the conversation even starts — the Claude Code
system prompt is re-sent on every invocation, and `-p` spawns a fresh process
each time. Two trivial turns took 11.6s and $0.215.

If what you want is *Claude as the model*, the Claude API directly is one
request and a fraction of that. If what you want is *an agent with tools*, the
[Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk) is the same
harness as a library — in-process, with tools and permissions you choose,
instead of a subprocess with all of them.

This example exists because shelling out to the CLI is the fastest way to see
the transport-mode loop close end to end. It is a spike, not an architecture.
