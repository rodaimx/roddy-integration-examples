// Acme Portal's backend — everything YOUR server contributes to the
// integration, and it is deliberately tiny:
//
//   1. Its own authentication (here: a fake pick-a-user login + a session
//      cookie; in your product this is whatever you already have).
//   2. ONE new endpoint, POST /api/chat-token: mint a short-lived visitor
//      token for whoever the session says is logged in.
//
// That's the whole recipe. The browser talks to Roddy directly with that
// token; the visitor secret never leaves this process; and Roddy never sees
// Acme's passwords, sessions, or user store — only the sub/name/email that
// this server chooses to sign.

import "dotenv/config";
import express from "express";
import session from "express-session";
import crypto from "node:crypto";
import { USERS } from "./users.js";
import { mintVisitorToken } from "./visitorToken.js";

for (const key of ["RODDY_WEB_CHAT_URL", "CHANNEL_ID", "CHANNEL_VISITOR_SECRET"]) {
  if (!process.env[key]) {
    console.error(`Missing ${key} — copy .env.example to .env and fill it.`);
    process.exit(1);
  }
}

const app = express();
app.use(express.json());
app.use(
  session({
    // Demo-grade session (in-memory, random key per boot). Your product
    // already has real sessions; the only thing that matters here is that
    // /api/chat-token can answer "who is logged in" server-side.
    secret: crypto.randomBytes(32).toString("hex"),
    resave: false,
    saveUninitialized: false,
  }),
);

// Who can be "logged in" — the picker the login screen shows. Names/roles
// only; the ids stay an implementation detail until login.
app.get("/api/users", (_req, res) => {
  res.json(
    Object.values(USERS).map(({ id, name, role }) => ({ id, name, role })),
  );
});

app.post("/api/login", (req, res) => {
  const user = USERS[req.body?.userId];
  if (!user) return res.status(401).json({ error: "unknown user" });
  req.session.userId = user.id;
  res.json({ user });
});

app.post("/api/logout", (req, res) => {
  // Logging out of ACME ends the ability to mint tokens; it does not (and
  // cannot) erase the conversation. The same person logging in tomorrow gets
  // the same `sub`, hence the same conversation — that continuity is the
  // point of using a stable id.
  req.session.destroy(() => res.json({ ok: true }));
});

app.get("/api/me", (req, res) => {
  const user = USERS[req.session.userId];
  res.json({ user: user ?? null });
});

// What the browser needs to talk to Roddy. NO secret here — the config is as
// public as the page itself.
app.get("/api/config", (_req, res) => {
  res.json({
    webChatUrl: process.env.RODDY_WEB_CHAT_URL.replace(/\/+$/, ""),
    channelId: process.env.CHANNEL_ID,
  });
});

// The one endpoint this whole example exists to demonstrate.
app.post("/api/chat-token", (req, res) => {
  const user = USERS[req.session.userId];
  if (!user) return res.status(401).json({ error: "not logged in" });
  res.json({
    token: mintVisitorToken({
      visitorSecret: process.env.CHANNEL_VISITOR_SECRET,
      // sub = OUR stable id. The conversation follows this value.
      userId: user.id,
      // Display hints: what Roddy's operators and agent call this person.
      name: user.name,
      email: user.email,
      // Short on purpose — the client re-mints transparently on
      // 401 visitor_token_expired (see src/api.js). Lower it to 60 to watch
      // that happen live.
      ttlSeconds: 900,
    }),
  });
});

const port = Number(process.env.PORT ?? 8787);
app.listen(port, () => {
  console.log(`Acme API on http://localhost:${port} (Vite proxies /api here)`);
});
