// Interactive terminal chat against a Roddy web-chat channel (visitor mode).
//
//   cp .env.example .env   # fill RODDY_WEB_CHAT_URL, CHANNEL_ID, CHANNEL_VISITOR_SECRET
//   npm start
//
// Same shape as a real frontend: mint a visitor token (server-side act — here
// in-process for the demo), seed the transcript from GET /history VERBATIM,
// then POST the WHOLE transcript each turn and print the SSE stream (Vercel
// AI SDK v5 protocol). In a browser you would not hand-parse SSE — useChat
// does all of this; see ../README.md.

import readline from "node:readline/promises";
import { randomUUID } from "node:crypto";
import dotenv from "dotenv";
import { mintVisitorToken } from "./mintToken.js";

dotenv.config();

const BASE_URL = process.env.RODDY_WEB_CHAT_URL.replace(/\/+$/, "");
const CHANNEL_ID = process.env.CHANNEL_ID;

async function fetchHistory(token) {
  const response = await fetch(
    `${BASE_URL}/history?channel_id=${encodeURIComponent(CHANNEL_ID)}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok) {
    throw new Error(`history HTTP ${response.status}: ${await response.text()}`);
  }
  return (await response.json()).messages;
}

async function streamTurn(token, messages) {
  const response = await fetch(`${BASE_URL}/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      channel_id: CHANNEL_ID,
      trigger: "submit-message",
      id: "terminal-demo",
      messages,
    }),
  });
  if (!response.ok) {
    // Stable codes: 401 visitor_token_expired → mint a fresh token and retry.
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let assistantText = "";
  for await (const bytes of response.body) {
    buffer += decoder.decode(bytes, { stream: true });
    let newline;
    while ((newline = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice("data: ".length);
      if (payload === "[DONE]") continue;
      const chunk = JSON.parse(payload);
      if (chunk.type === "text-delta") {
        assistantText += chunk.delta ?? "";
        process.stdout.write(chunk.delta ?? "");
      } else if (chunk.type === "data-roddy-turn-status") {
        // Turn ended without the agent (human-only channel, paused contact…).
        // message_accepted says the message DID land.
        process.stdout.write(`[turno sin agente: ${chunk.data?.reason}]`);
      }
    }
  }
  process.stdout.write("\n");

  return [
    {
      id: randomUUID(),
      role: "assistant",
      parts: [{ type: "text", text: assistantText }],
    },
  ];
}

const token = mintVisitorToken({
  visitorSecret: process.env.CHANNEL_VISITOR_SECRET,
  userId: process.env.VISITOR_USER_ID ?? "demo-user-1",
  name: process.env.VISITOR_NAME ?? "Demo",
});

const messages = await fetchHistory(token);
console.log(`(${messages.length} mensaje(s) previos)  Ctrl+C para salir.\n`);

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
// Ctrl+D / piped-input EOF closes the interface. Exiting right here would
// race an in-flight turn (killing the reply mid-stream), so flag it and leave
// at the top of the loop, after the current turn finishes.
let stdinClosed = false;
rl.on("close", () => {
  stdinClosed = true;
});
for (;;) {
  if (stdinClosed) process.exit(0);
  let text;
  try {
    text = (await rl.question("tú> ")).trim();
  } catch {
    process.exit(0); // interface closed while we were waiting at the prompt
  }
  if (!text) continue;
  messages.push({
    id: randomUUID(),
    role: "user",
    parts: [{ type: "text", text }],
  });
  process.stdout.write("agente> ");
  messages.push(...(await streamTurn(token, messages)));
}
