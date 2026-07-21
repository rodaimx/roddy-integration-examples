'use strict';
// Roddy custom skill (generic use case) — SYNCHRONOUS tool call.
//
// Unlike transport mode (async events), a custom skill answers a tool call
// DURING a Roddy agent run: Roddy POSTs {metadata, arguments} and WAITS for your
// result in the HTTP response. This example uses the recommended STRUCTURED
// response. A legacy "text" mode also exists — see the README.
//
//   npm install
//   npm run selftest                # verify the signature check offline
//   cp .env.example .env            # set WEBHOOK_SECRET
//   node skill.js                   # then `ngrok http 8000`

require('dotenv').config();
const express = require('express');
const { isValidSignature, isFresh } = require('./signature');

const app = express();
const SECRET = process.env.WEBHOOK_SECRET || '';

app.use('/webhook', express.raw({ type: '*/*' })); // RAW body for verification

app.post('/webhook', (req, res) => {
  const rawBody = req.body;
  let payload = {};
  try { payload = JSON.parse(rawBody.toString('utf8') || '{}'); } catch (_) { /* {} */ }

  // Unsigned verification handshake.
  if (payload && payload.type === 'webhook_verification') {
    return res.json({ challenge: payload.challenge });
  }

  // Verify the signature over the raw body.
  const ts = req.header('X-Roddy-Timestamp') || '';
  const sig = req.header('X-Roddy-Signature') || '';
  if (!SECRET) return res.status(500).send('WEBHOOK_SECRET not set');
  if (!isFresh(ts) || !isValidSignature(SECRET, ts, rawBody, sig)) {
    return res.status(401).send('invalid signature');
  }

  // Synchronous tool call — Roddy is WAITING for your result.
  const metadata = payload.metadata || {};
  const args = payload.arguments || {}; // shape = your use case's parameter schema
  console.log(
    `[skill] use_case=${metadata.use_case_id} contact=${metadata.contact_id} ` +
    `arguments=${JSON.stringify(args)}`
  );

  const result = handleTool(args, metadata);

  // HTTP 200 + the structured envelope. A non-200 is a tool failure to Roddy.
  return res.json(result);
});

// Your skill's business logic. Return a structured envelope:
//   { messages: [ {type: text|document|image, ...}, ... ],   // >= 1, user-facing
//     agent_result: "short summary for the LLM" }             // LLM-facing
// URLs must be http(s) and reachable by Roddy. No extra top-level keys.
function handleTool(args, metadata) {
  const orderId = args.order_id || 'UNKNOWN';
  // ... look the order up in your system here ...
  return {
    messages: [
      { type: 'text', text: `Your order ${orderId} ships tomorrow. Here's the invoice:` },
      {
        type: 'document',
        url: `https://files.example.com/invoices/${orderId}.pdf`,
        filename: `invoice-${orderId}.pdf`,
        mime_type: 'application/pdf',
        caption: 'Invoice',
      },
    ],
    agent_result: `Told the user order ${orderId} ships tomorrow and sent the invoice PDF.`,
  };
}

const port = process.env.PORT || 8000;
app.listen(port, () => console.log(`listening on :${port}`));
