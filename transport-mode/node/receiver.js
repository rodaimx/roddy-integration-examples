'use strict';
// Transport-mode event receiver (Express).
// Roddy POSTs each inbound message on a passthrough channel here as a signed
// `message.inbound` event. Verify it, ACK 200 quickly, hand it to your brain,
// and reply later via the send API (see sendExample.js).
//
//   npm install
//   cp .env.example .env            # set WEBHOOK_SECRET
//   node receiver.js                # then `ngrok http 8000`

require('dotenv').config();
const express = require('express');
const { isValidSignature, isFresh } = require('./signature');

const app = express();
const SECRET = process.env.WEBHOOK_SECRET || '';

app.use('/webhook', express.raw({ type: '*/*' })); // RAW body for signature verification

app.post('/webhook', (req, res) => {
  const rawBody = req.body; // Buffer
  let event = {};
  try { event = JSON.parse(rawBody.toString('utf8') || '{}'); } catch (_) { /* {} */ }

  // Unsigned verification handshake.
  if (event && event.type === 'webhook_verification') {
    return res.json({ challenge: event.challenge });
  }

  // Verify freshness + signature over the raw body.
  const ts = req.header('X-Roddy-Timestamp') || '';
  const sig = req.header('X-Roddy-Signature') || '';
  if (!SECRET) return res.status(500).send('WEBHOOK_SECRET not set');
  if (!isFresh(ts) || !isValidSignature(SECRET, ts, rawBody, sig)) {
    return res.status(401).send('invalid signature');
  }

  // Dispatch by event_type. Dedupe on event_id (stable across at-least-once retries).
  if (event.event_type === 'message.inbound') {
    const data = event.data || {};
    const contact = event.contact || {};
    console.log(
      `[inbound] event_id=${event.event_id} contact=${contact.contact_id} ` +
      `text=${JSON.stringify(data.text)} media_count=${(data.media || []).length}`
    );
    // -> your brain decides a reply, then call the send API. Media URLs in
    //    data.media are presigned + short-lived: fetch promptly.
  } else {
    console.log(`[event] unhandled event_type=${event.event_type}`);
  }

  res.json({ status: 'ok' }); // ACK only once durably accepted
});

const port = process.env.PORT || 8000;
app.listen(port, () => console.log(`listening on :${port}`));
