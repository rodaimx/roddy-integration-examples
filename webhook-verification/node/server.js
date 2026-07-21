'use strict';
// Minimal Roddy webhook receiver (Express).
//
//   npm install
//   npm run selftest                 # prove the verifier is correct, no server
//   cp .env.example .env             # set WEBHOOK_SECRET
//   npm start                        # listens on :8000
//
// Then expose the port (e.g. `ngrok http 8000`) and use that https URL as your
// webhook URL. See ../README.md.

require('dotenv').config();
const express = require('express');
const { isValidSignature, isFresh } = require('./signature');

const app = express();
const SECRET = process.env.WEBHOOK_SECRET || '';

// CRITICAL: capture the RAW body. express.json() would give only the parsed
// object; signature verification needs the exact bytes Roddy signed.
app.use('/webhook', express.raw({ type: '*/*' }));

app.post('/webhook', (req, res) => {
  const rawBody = req.body; // Buffer (from express.raw)
  let parsed = {};
  try { parsed = JSON.parse(rawBody.toString('utf8') || '{}'); } catch (_) { /* leave {} */ }

  // Verification handshake (UNSIGNED): echo the challenge. The shared secret is
  // issued only after verification succeeds, so don't check a signature here.
  if (parsed && parsed.type === 'webhook_verification') {
    return res.json({ challenge: parsed.challenge });
  }

  // Real event: verify freshness + signature over the raw body.
  const timestamp = req.header('X-Roddy-Timestamp') || '';
  const signature = req.header('X-Roddy-Signature') || '';
  if (!SECRET) return res.status(500).send('WEBHOOK_SECRET not set');
  if (!isFresh(timestamp)) return res.status(401).send('stale or missing timestamp');
  if (!isValidSignature(SECRET, timestamp, rawBody, signature)) {
    return res.status(401).send('invalid signature');
  }

  // Verified. Handle it, then ACK 200 quickly. Dedupe on parsed.event_id — it's
  // stable across Roddy's at-least-once retries.
  console.log(
    `verified event: type=${parsed.event_type} id=${parsed.event_id} ` +
    `webhook=${req.header('X-Roddy-Webhook-Id')}`
  );
  res.json({ status: 'ok' });
});

const port = process.env.PORT || 8000;
app.listen(port, () => console.log(`listening on :${port}`));
