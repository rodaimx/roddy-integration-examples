'use strict';
// Offline correctness check using the published test vector — no server needed.
//
//   node selftest.js
//
// If this prints OK, your verifier reproduces Roddy's signature exactly,
// including the non-ASCII case (the part most homemade verifiers get wrong).

const assert = require('assert');
const { computeSignature, isValidSignature } = require('./signature');

const SECRET = 'whsec_test_do_not_use_in_prod_1234567890';
const TIMESTAMP = '2026-01-15T12:00:00.000000+00:00';
const BODY = Buffer.from(
  '{"version": "1", "event_type": "message.inbound", "data": {"text": "José ✅"}}',
  'utf8'
);
const EXPECTED = '23e10a62fe99729b24278d75219b908d63ed27cd70dc0bcffd5d8f0ff26dd86b';

assert.strictEqual(computeSignature(SECRET, TIMESTAMP, BODY), EXPECTED, 'signature mismatch');
assert.ok(isValidSignature(SECRET, TIMESTAMP, BODY, EXPECTED), 'should accept the valid signature');
assert.ok(!isValidSignature(SECRET, TIMESTAMP, BODY, 'deadbeef'), 'should reject a bad signature');
console.log('OK — signature verification matches the test vector (incl. non-ASCII).');
