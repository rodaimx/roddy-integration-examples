// HS256 visitor-token minting with Node's crypto — no JWT library needed
// (use jsonwebtoken if you prefer; the output is identical).
//
// Claims contract (Roddy verifies nothing else):
//   sub   required — YOUR stable id for this person; decides the conversation
//   exp   required — unix seconds, at most 24h out; keep it SHORT (minutes):
//                    the client just re-mints when Roddy answers
//                    401 visitor_token_expired
//   name  optional — what your operators and the agent see as who is talking
//   email optional — informational, shown on the contact card

import crypto from "node:crypto";

const b64url = (input) => Buffer.from(input).toString("base64url");

export function mintVisitorToken({
  visitorSecret,
  userId,
  name,
  email,
  ttlSeconds = 900,
}) {
  const claims = {
    sub: userId,
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
  };
  if (name) claims.name = name;
  if (email) claims.email = email;

  const head = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = b64url(JSON.stringify(claims));
  const signature = crypto
    .createHmac("sha256", visitorSecret)
    .update(`${head}.${body}`)
    .digest("base64url");
  return `${head}.${body}.${signature}`;
}
