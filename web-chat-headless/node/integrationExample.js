// Server-to-server web chat: the integration relay + synchronous mode.
//
//   cp .env.example .env   # fill the AUTH_* / CLIENT_* / CHANNEL_ID values
//   npm run integration -- "hola, ¿tienen inventario del SKU 123?"
//
// Your backend authenticates as an OAuth integration (client_credentials)
// whose application holds the `web_chat.converse` scope, DECLARES which of
// your users the turn is for (`subject` — you are accountable for it), and
// asks for one JSON body instead of a stream (Accept: application/json).
//
// Reading the conversation back uses the same declared subject:
//   GET /history?channel_id=…&subject=…

import { randomUUID } from "node:crypto";
import dotenv from "dotenv";

dotenv.config();

const BASE_URL = process.env.RODDY_WEB_CHAT_URL.replace(/\/+$/, "");

async function getAccessToken() {
  const response = await fetch(process.env.AUTH_TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization:
        "Basic " +
        Buffer.from(
          `${process.env.CLIENT_ID}:${process.env.CLIENT_SECRET}`,
        ).toString("base64"),
    },
    body: "grant_type=client_credentials",
  });
  if (!response.ok) {
    throw new Error(`token HTTP ${response.status}: ${await response.text()}`);
  }
  return (await response.json()).access_token;
}

const text = process.argv[2] ?? "hola";
const token = await getAccessToken();

const response = await fetch(`${BASE_URL}/`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    // The sync switch: one JSON body, no SSE.
    Accept: "application/json",
  },
  body: JSON.stringify({
    channel_id: process.env.CHANNEL_ID,
    // Who this turn is for — YOUR id for the end user. Same subject, same
    // conversation. Refused outside the integration mode.
    subject: process.env.SUBJECT ?? "crm-user-42",
    subject_name: "Usuario CRM 42",
    trigger: "submit-message",
    id: "server-job",
    messages: [
      { id: randomUUID(), role: "user", parts: [{ type: "text", text }] },
    ],
  }),
});

if (response.status === 429) {
  throw new Error(`rate_limited — retry in ${response.headers.get("retry-after")}s`);
}
if (!response.ok) {
  throw new Error(`HTTP ${response.status}: ${await response.text()}`);
}

const result = await response.json();
if (result.turn_status.agent_ran) {
  console.log(result.text);
} else {
  // A 200 without the agent is a normal operating mode (human-only channel,
  // paused contact…): the message WAS accepted when message_accepted is true,
  // and an operator will answer.
  console.log(
    `turno sin agente: ${result.turn_status.reason} (accepted=${result.turn_status.message_accepted})`,
  );
}
