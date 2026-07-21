'use strict';
// OAuth 2.0 client-credentials token client for the Roddy API.
//
// Server-to-server auth. Exchange your integration's CLIENT_ID + CLIENT_SECRET
// for a short-lived Bearer access token, cache it, and fetch a fresh one when it
// expires. The client-credentials grant has NO refresh token — when the token
// expires you just request another with the same credentials.
//
// Contract (from the Roddy integration docs):
//   POST <AUTH_TOKEN_URL>                     // full token URL, ends in /o/token/
//   Content-Type: application/x-www-form-urlencoded
//   grant_type=client_credentials & client_id=<CLIENT_ID> & client_secret=<CLIENT_SECRET>
//   (scope is optional; omit it → the token carries all granted permissions)
//   -> { access_token, token_type: "Bearer", expires_in: 900, scope }
//
// You get AUTH_TOKEN_URL / CLIENT_ID / CLIENT_SECRET in the .env you download when
// you create the integration in the Roddy dashboard.
//
// IMPORTANT: the token endpoint is rate-limited (~60 req/min per credential).
// CACHE the token and reuse it until it expires — never fetch one per API call.
// This client does that for you. Requires Node 18+ (global fetch).

const querystring = require('querystring');

class RoddyTokenClient {
  constructor(tokenUrl, clientId, clientSecret, { earlyRefreshSeconds = 60 } = {}) {
    this._tokenUrl = tokenUrl;
    this._id = clientId;
    this._secret = clientSecret;
    this._early = earlyRefreshSeconds;
    this._token = null;
    this._expiresAt = 0; // epoch seconds
  }

  async getToken() {
    if (this._token && Date.now() / 1000 < this._expiresAt - this._early) return this._token;
    const resp = await fetch(this._tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: querystring.stringify({
        grant_type: 'client_credentials',
        client_id: this._id,
        client_secret: this._secret,
      }),
    });
    if (!resp.ok) throw new Error(`token request failed: ${resp.status} ${await resp.text()}`);
    const data = await resp.json();
    // Read expires_in from the response — default 900s but may change.
    this._token = data.access_token;
    this._expiresAt = Date.now() / 1000 + (data.expires_in || 900);
    return this._token;
  }
}

module.exports = { RoddyTokenClient };
