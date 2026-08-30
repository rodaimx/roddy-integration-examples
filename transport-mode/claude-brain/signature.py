"""Roddy webhook signature verification — framework-agnostic, no dependencies.

    signature = hex( HMAC_SHA256(secret, timestamp + body) )

``body`` MUST be the exact raw bytes received. Never parse and re-serialize the
JSON before verifying: re-serialization can reorder keys, change spacing, or
escape non-ASCII characters, so the signature would no longer match the one
Roddy computed over the original bytes. Copy this file into your own app.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone


def compute_signature(secret: str, timestamp: str, raw_body: bytes) -> str:
    """Expected hex HMAC-SHA256 over ``timestamp + raw_body`` (UTF-8)."""
    message = timestamp.encode("utf-8") + raw_body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def is_valid_signature(
    secret: str, timestamp: str, raw_body: bytes, signature: str
) -> bool:
    """Constant-time check that ``signature`` matches. ``raw_body`` = exact bytes."""
    expected = compute_signature(secret, timestamp, raw_body)
    return hmac.compare_digest(expected, signature or "")


def is_fresh(timestamp: str, max_age_seconds: int = 300) -> bool:
    """Reject timestamps outside ±``max_age_seconds`` (replay defense).

    Roddy sends an ISO-8601 UTC ``X-Roddy-Timestamp`` but does not enforce a
    window — that check is the integrator's responsibility.
    """
    try:
        sent = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    return abs((datetime.now(timezone.utc) - sent).total_seconds()) <= max_age_seconds
