// Mint a web-chat visitor token — the piece that runs on YOUR backend.
//
// The visitor secret must never reach a browser or a mobile binary: whoever
// holds it can talk to your channel as any of your users. In production this
// sits behind your own authenticated endpoint (e.g. POST /chat-token), which
// mints a token for the user your session already identified.
//
// Zero dependencies: an HS256 JWT is just two base64url JSON parts plus an
// HMAC — Node's crypto covers it. Use jsonwebtoken if you prefer.
//
//   node mintToken.js my-user-42     # prints a token

import crypto from "node:crypto";

const b64url = (input) =>
  Buffer.from(input).toString("base64url");

/**
 * Sign a visitor token for one of YOUR users.
 *
 * `sub` decides which conversation this is — same sub, same conversation, on
 * any device. Keep the TTL short (minutes): the client just asks your backend
 * for a fresh one when Roddy answers 401 visitor_token_expired.
 */
export function mintVisitorToken({
  visitorSecret,
  userId,
  name,
  email,
  ttlSeconds = 900,
}) {
  const claims = { sub: userId, exp: Math.floor(Date.now() / 1000) + ttlSeconds };
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

if (import.meta.url === `file://${process.argv[1]}`) {
  const { default: dotenv } = await import("dotenv");
  dotenv.config();
  console.log(
    mintVisitorToken({
      visitorSecret: process.env.CHANNEL_VISITOR_SECRET,
      userId: process.argv[2] ?? "demo-user-1",
      name: process.env.VISITOR_NAME || undefined,
    }),
  );
}
