"""Mint a web-chat visitor token — the piece that runs on YOUR backend.

The visitor secret must never reach a browser or a mobile binary: whoever
holds it can talk to your channel as any of your users. In production this
function sits behind your own authenticated endpoint (e.g.
`POST /chat-token`), which mints a token for the user your session already
identified.

    python mint_token.py my-user-42        # prints a token, for piping into chat.py
"""

from __future__ import annotations

import os
import sys
import time

import jwt  # PyJWT


def mint_visitor_token(
    *,
    visitor_secret: str,
    user_id: str,
    name: str | None = None,
    email: str | None = None,
    ttl_seconds: int = 900,
) -> str:
    """Sign a visitor token for one of YOUR users.

    `sub` decides which conversation this is — same `sub`, same conversation,
    on any device. Keep the TTL short (minutes): the client just asks your
    backend for a fresh one when Roddy answers `401 visitor_token_expired`.
    """
    claims: dict = {"sub": user_id, "exp": int(time.time()) + ttl_seconds}
    if name:
        claims["name"] = name
    if email:
        claims["email"] = email
    return jwt.encode(claims, visitor_secret, algorithm="HS256")


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "demo-user-1"
    print(
        mint_visitor_token(
            visitor_secret=os.environ["CHANNEL_VISITOR_SECRET"],
            user_id=user_id,
            name=os.environ.get("VISITOR_NAME") or None,
        )
    )
