# Acme Portal — the identity recipe, running

A made-up product with its own login, and Roddy's agent chatting inside it.
The other folders here show the *mechanics* (sign a token, parse the stream);
this one shows the **decisions** — what an integration actually has to choose
about identity, played out in a runnable proof of concept.

Your real system won't look like Acme. It might be microservices, an IdP,
a mobile app, three login flows. That's fine: the shape below survives all of
it, because it only asks your system for one thing it already has — a
server-side answer to *"who is logged in right now?"*

```
┌──────────── your product ────────────┐
│ browser ── your login ── your server │           ┌── Roddy ──┐
│    │                        │        │           │           │
│    │   POST /chat-token     │  signs {sub,exp}   │           │
│    │ ─────────────────────▶ │  with the channel  │           │
│    │ ◀───── visitor token ──│  visitor secret    │           │
│    │                                 │           │           │
│    │──────── Bearer <visitor token> ─┼──────────▶│  agent    │
│    │◀─────────── SSE stream ─────────┼───────────│  answers  │
└──────────────────────────────────────┘           └───────────┘
```

## Run it

```bash
cp .env.example .env    # channel id + visitor secret + web-chat URL
npm install
npm start               # Acme API on :8787, page on http://localhost:5173
```

Log in as **Ana** or **Luis**, chat, switch users, come back — and watch what
that demonstrates (below).

## The five identity decisions, and what Acme chose

**1. What is `sub`?** — *Your stable internal id.* Acme signs `emp-1042`, not
`ana.torres@acme.example`. The `sub` **is** the conversation key: same value,
same conversation, on any device, forever. Emails change hands; usernames get
edited; ids don't. (`server/users.js`)

**2. Where does the secret live?** — *One place: your server's env.* The
browser gets tokens, never the secret — whoever holds the secret can talk to
your channel as anyone. The whole server-side surface of this integration is
one endpoint, `POST /api/chat-token`, gated by the session you already have.
(`server/server.js`)

**3. How long do tokens live, and who refreshes them?** — *Short, and nobody
manually.* Acme mints 15-minute tokens and the browser treats them as
disposable: on `401 visitor_token_expired` it re-mints once and retries, so a
person mid-conversation never notices. Set `ttlSeconds` to 60 in
`server/server.js` and watch it happen. (`src/api.js` — `roddyFetch`)

**4. What do Roddy's operators see?** — *What you sign.* The `name` and
`email` claims become the contact card in Roddy's inbox: sign "Ana Torres" and
your operators answer Ana Torres, not `emp-1042`. Optional, but the difference
between an inbox of people and an inbox of ids.

**5. What does logout mean?** — *No more tokens — not amnesia.* Logging out of
Acme stops the minting; it doesn't erase the conversation. Ana tomorrow is
still `emp-1042`, so she gets her history back — that continuity is the point.
Switch users in the demo and notice each one has their own transcript
(`key={user.id}` remounts the chat, because a different `sub` IS a different
conversation).

## What the client does (and doesn't)

`src/Chat.jsx` is ordinary [Vercel AI SDK](https://ai-sdk.dev) usage —
`useChat` + `DefaultChatTransport`. The Roddy-specific surface is three lines:
the endpoint, `body: { channel_id }`, and `fetch: roddyFetch` (token
injection + refresh). Two rules keep a conversation healthy:

- **Seed history verbatim.** `GET /history` output goes into `useChat`'s
  `messages` untouched — the SDK replays the whole transcript each turn, and
  the API expects it back exactly as produced.
- **Render parts, not strings.** Text parts are the reply;
  `data-roddy-turn-status` (turn ended without the agent — the message DID
  land, a human will answer) and `data-roddy-tool-activity` (the agent is
  working) are Roddy's two extra parts, safe to ignore, better to surface.

## Mapping this onto your real system

| If your system… | then `/chat-token` … |
| --- | --- |
| has a session cookie (like Acme) | reads the session, signs that user |
| uses an IdP (Auth0/Cognito/your OIDC) | validates YOUR access token, signs *your* user id from its claims |
| is a mobile app | same endpoint, called with your app's existing auth |
| is multi-tenant itself | put your tenant in the sub: `acct-77:user-19` — subs are opaque to Roddy, only stability matters |
| has no end-user auth at all | stop — that's the anonymous-visitor case, not yet available; don't mint tokens for guests |

And if the *server* should talk for users instead of their browsers (batch
jobs, a CRM writing on someone's behalf), that's the other mode — the
integration relay with `web_chat.converse` — see
[`../python/integration_example.py`](../python/integration_example.py) /
[`../node/integrationExample.js`](../node/integrationExample.js).

Full endpoint reference and error catalog: **Docs → Referencia → API de chat
web** in your Roddy app.
