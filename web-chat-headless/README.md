# Web chat, headless (your frontend, Roddy's agent)

Use a Roddy **web-chat** channel from your own product: your web app, mobile
app, or backend talks to Roddy's chat API and Roddy's agent answers. This is
the opposite of [`../transport-mode`](../transport-mode): there, *your* brain
replies through our channel; here, *our* brain replies through your interface.

Full reference (endpoints, claims, error catalog): **Docs → Referencia → API de
chat web** in your Roddy app.

Pick your language:

- [`python/`](./python) — PyJWT token minting + terminal streaming client
- [`node/`](./node) — zero-dep HS256 minting + terminal streaming client (Node 18+)

## The two identity modes

**1. Visitor tokens** — for a chat in *your* frontend, behind *your* login.
Your backend signs a short-lived JWT (HS256) with the channel's **visitor
secret**; the end user's browser/app calls Roddy directly with it.

```
your user ──login──▶ your backend ──signs {sub, exp}──▶ visitor token
your user ──Bearer <visitor token>──▶ RODDY_WEB_CHAT_URL (stream / history / uploads)
```

- Get the secret: channel settings → *Secreto de visitante* (shown **once**;
  rotating invalidates old tokens immediately).
- Claims: `sub` (your user id — decides which conversation), `exp` (≤ 24 h;
  minutes to 1 h recommended), optional `name` / `email`.
- The secret lives **only** on your server. Never ship it to a browser.

**2. Integration relay** — for server-to-server: your backend authenticates
with its OAuth integration (scope **`web_chat.converse`**) and declares which
of your users each turn is for (`subject`). Also gives you the **synchronous**
mode: send `Accept: application/json` and get one JSON body instead of a
stream.

## The wire format

`POST RODDY_WEB_CHAT_URL/` takes the Roddy context (`channel_id`, and
`subject` in integration mode) **and** a [Vercel AI SDK](https://ai-sdk.dev)
v5 request in the same JSON body, and answers with the AI SDK's SSE stream —
so a JS frontend is one hook:

```ts
const { messages, sendMessage } = useChat({
  transport: new DefaultChatTransport({
    api: RODDY_WEB_CHAT_URL,
    body: { channel_id: CHANNEL_ID },
    headers: { Authorization: `Bearer ${visitorToken}` },
  }),
  messages: initialMessagesFromHistory, // GET /history, verbatim
});
```

Two rules that keep a conversation healthy:

- **Replay verbatim.** The client re-sends the whole transcript each turn;
  send messages exactly as `GET /history` / the stream gave them to you.
- **Poll for out-of-band replies** (a human operator answering from the
  inbox): `GET /history?channel_id=…&since_sk=<last message id>`.

## Files

```
python/  mint_token.py   # sign a visitor token (PyJWT)
         chat.py         # interactive terminal chat over the SSE stream
         integration_example.py  # server-to-server: subject + sync JSON mode
node/    mintToken.js    # sign a visitor token (built-in crypto, no deps)
         chat.js         # interactive terminal chat over the SSE stream
         integrationExample.js   # server-to-server: subject + sync JSON mode
```

Every script reads its configuration from the environment — see
`.env.example` in each folder.
