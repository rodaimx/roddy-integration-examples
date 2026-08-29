"""Offline checks — no server, no Roddy, no writes.

    python selftest.py           # signature vector + Notify config resolution
    python selftest.py --live    # also does ONE read-only GET against Notify

The signature half uses the published test vector: if it prints OK, this
verifier reproduces Roddy's HMAC exactly, including the non-ASCII case that
most homemade verifiers get wrong.
"""

from __future__ import annotations

import sys

from notify_client import NotifyClient, NotifyError, load_config
from signature import compute_signature, is_valid_signature

SECRET = "whsec_test_do_not_use_in_prod_1234567890"
TIMESTAMP = "2026-01-15T12:00:00.000000+00:00"
BODY = (
    '{"version": "1", "event_type": "message.inbound", '
    '"data": {"text": "José ✅"}}'
).encode("utf-8")
EXPECTED = "23e10a62fe99729b24278d75219b908d63ed27cd70dc0bcffd5d8f0ff26dd86b"


def check_signature() -> None:
    got = compute_signature(SECRET, TIMESTAMP, BODY)
    assert got == EXPECTED, f"signature mismatch:\n  expected {EXPECTED}\n  got      {got}"
    assert is_valid_signature(SECRET, TIMESTAMP, BODY, EXPECTED), "should accept valid sig"
    assert not is_valid_signature(SECRET, TIMESTAMP, BODY, "deadbeef"), "should reject bad sig"
    print("OK — signature verification matches the test vector (incl. non-ASCII).")


def check_config() -> None:
    token, base_url, source = load_config()
    # Never print the token itself — only whether one resolved.
    print(
        f"OK — Notify config from {source}: url={base_url} "
        f"token={'set' if token else 'MISSING'}"
    )
    if base_url.startswith("https://staging."):
        print("    NOTE: pointing at STAGING — reads do not reflect production.")
    if not token:
        print("    Run `notify config set token` (hidden prompt) before going live.")


def check_live() -> None:
    client = NotifyClient()
    projects = client.list_projects(limit=3)
    print(f"OK — live read returned {len(projects)} project(s):")
    for project in projects:
        print(f"    {project.get('id')} | {project.get('name')}")


def main() -> None:
    check_signature()
    check_config()
    if "--live" in sys.argv:
        try:
            check_live()
        except NotifyError as error:
            print(f"LIVE CHECK FAILED — {error}")
            sys.exit(1)


if __name__ == "__main__":
    main()
