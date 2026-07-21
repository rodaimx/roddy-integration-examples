"""OAuth 2.0 client-credentials token client for the Roddy API.

Server-to-server auth. Exchange your integration's ``CLIENT_ID`` +
``CLIENT_SECRET`` for a short-lived Bearer **access token**, cache it, and fetch
a fresh one when it expires. The client-credentials grant has **no refresh
token** — when the token expires you simply request another with the same
credentials.

Contract (from the Roddy integration docs):

    POST <AUTH_TOKEN_URL>                     # the full token URL, ends in /o/token/
    Content-Type: application/x-www-form-urlencoded

    grant_type=client_credentials
    client_id=<CLIENT_ID>
    client_secret=<CLIENT_SECRET>
    # scope is optional; omit it and the token carries every permission the
    # tenant admin granted the integration (the sensible default).

    -> { "access_token": "<JWT>", "token_type": "Bearer",
         "expires_in": 900, "scope": "channel.send" }

You get ``AUTH_TOKEN_URL`` / ``CLIENT_ID`` / ``CLIENT_SECRET`` in the ``.env`` you
download when you create the integration in the Roddy dashboard.

IMPORTANT: the token endpoint is rate-limited (~60 requests/min per credential).
**Cache the token and reuse it until it expires** — never request one per API
call. This client does that for you.
"""

from __future__ import annotations

import threading
import time

import requests


class RoddyTokenClient:
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        early_refresh_seconds: int = 60,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._early = early_refresh_seconds
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        """Return a valid Bearer token, fetching a new one only when needed."""
        with self._lock:
            if self._token and time.time() < self._expires_at - self._early:
                return self._token
            token, ttl = self._fetch()
            self._token = token
            self._expires_at = time.time() + ttl
            return token

    def _fetch(self) -> tuple[str, int]:
        resp = requests.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()  # 401 invalid_client, 429 rate_limit_exceeded, ...
        body = resp.json()
        # Read expires_in from the response — the default is 900s but may change.
        return body["access_token"], int(body.get("expires_in", 900))
