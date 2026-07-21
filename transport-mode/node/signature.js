'use strict';
// Roddy webhook signature verification — Node `crypto` only, no deps.
//
//     signature = hex( HMAC_SHA256(secret, timestamp + body) )
//
// `rawBody` MUST be the exact bytes received. Never JSON.stringify(req.body) and
// hash that — re-serialization changes key order / spacing / non-ASCII escaping,
// so the signature won't match the one Roddy computed over the original bytes.
// Copy this file into your own app.

const crypto = require('crypto');

function computeSignature(secret, timestamp, rawBody) {
  const body = Buffer.isBuffer(rawBody) ? rawBody : Buffer.from(rawBody, 'utf8');
  const message = Buffer.concat([Buffer.from(timestamp, 'utf8'), body]);
  return crypto.createHmac('sha256', secret).update(message).digest('hex');
}

function isValidSignature(secret, timestamp, rawBody, signature) {
  const expected = computeSignature(secret, timestamp, rawBody);
  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(signature || '', 'utf8');
  // Length check first: timingSafeEqual throws on length mismatch.
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Reject timestamps outside ±maxAgeSeconds (replay defense). Roddy sends the
// ISO-8601 timestamp but does not enforce a window — that check is yours.
function isFresh(timestamp, maxAgeSeconds = 300) {
  const t = Date.parse(timestamp);
  if (Number.isNaN(t)) return false;
  return Math.abs(Date.now() - t) / 1000 <= maxAgeSeconds;
}

module.exports = { computeSignature, isValidSignature, isFresh };
