# Custom skill — Rodai Notify (read-only)

A **working** custom skill: where [`../python`](../python) returns a canned
example, this one answers a Roddy tool call with real data from
[Rodai Notify](https://rodainotify.com). Same synchronous contract — Roddy
POSTs `{metadata, arguments}` and **waits** for the envelope in your response.

Built to run on a laptop behind a tunnel. Read the caveats before pointing it
at anything that matters.

## Files

| File | What it is |
|---|---|
| `signature.py` | webhook signature verification (identical to the other examples) |
| `notify_client.py` | GET-only Notify API client + token resolution |
| `skill.py` | the endpoint: verify → dispatch on `action` → structured envelope |
| `selftest.py` | offline signature vector + config check; `--live` adds one real GET |

## The token never lives in this repo

`notify_client.py` resolves credentials exactly like the `notify` CLI, in order:

1. `RODAI_NOTIFY_TOKEN` / `RODAI_NOTIFY_URL` env vars
2. `.rodai-notify.json` walking up from the working directory
3. `~/.config/rodai-notify/config.json` — what `notify config set token` writes

So if the CLI works here, the skill works, with nothing copied anywhere. When
you deploy this, set the env vars on the host instead of shipping the file.

Check which one is active without printing the secret:

```bash
python selftest.py
```

It prints the config source, the base URL, and whether a token resolved — and
warns if you are pointed at **staging**, which is easy to forget.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python selftest.py --live      # confirm signature + Notify access
cp .env.example .env                     # set WEBHOOK_SECRET
.venv/bin/uvicorn skill:app --reload --port 8000
ngrok http 8000                          # use the https URL as the webhook
```

The webhook must be **HTTPS** — that is the one thing Roddy validates. Nothing
else about the host is checked, so a tunnel to localhost is fine for a test.

## Arguments

One webhook backs one Roddy use case, so the operations sit behind an `action`
argument. Declare it as an enum in the use case's parameter schema so the model
can only pick a valid value:

| `action` | Other arguments | Returns |
|---|---|---|
| `list_projects` | `query` (optional) | matching boards with their ids |
| `list_cards` | `project_id` (required), `query`, `assignee_id` | cards on that board |
| `get_card` | `card_id` (required) | name, column, logged hours |

Every response is the structured envelope: `messages` is what the person reads,
`agent_result` is the short summary the model uses to phrase its follow-up.

Failures return a normal **200** with an envelope explaining the problem, not an
HTTP error — that way the agent can tell the user what happened instead of
surfacing a tool crash. Upstream error bodies are logged, never forwarded into
the chat.

## Two API quirks this client works around

Both were found by comparing against the CLI; neither is documented:

- **The id field differs by endpoint.** `/projects/api/project/` returns `pk`;
  `/projects/api/tasks/` returns `id`. The client normalizes both to `id`.
- **The search parameter differs by endpoint.** Projects filter on `q`, tasks
  on `search`. Sending the wrong one is not an error — you silently get an
  unfiltered list, which the model will happily summarize as if it were a
  search result.

Also: the tasks endpoint has no default ordering, so paginated reads duplicate
some rows and drop others. The client forces `ordering=id`.

## Read-only, on purpose

Every action is a GET. Before adding writes, decide who the agent is acting as
— the Notify API ties everything to the token's user, so an agent with a
service token creates cards that all look like they came from one person, with
that person's permissions. On a shared board that is a real problem, not a
cosmetic one. There is no per-contact token story here.

Two more things worth knowing if you go further:

- **Nothing the API does shows up in a card's activity history.** Notify only
  writes history from its WebSocket flow, so agent actions appear with no
  author and no reason. A comment is the only trace you get.
- **`checklist add` is broken server-side** and `comments add` / `tags create`
  need a fix that is on staging but not production. Don't build on them yet.

## Timeout

The use case's `timeout_seconds` is configurable **1–60, default 30**. A Notify
read takes a few hundred milliseconds, so set it to ~10: the skill is
synchronous, and while it waits, the agent is stopped and a person is watching
a spinner. Fail fast rather than hanging.
