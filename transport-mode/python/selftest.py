"""Offline correctness check using the published test vector — no server needed.

    python selftest.py

If this prints OK, your verifier reproduces Roddy's signature exactly, including
the non-ASCII case (the part most homemade verifiers get wrong).
"""

from signature import compute_signature, is_valid_signature

SECRET = "whsec_test_do_not_use_in_prod_1234567890"
TIMESTAMP = "2026-01-15T12:00:00.000000+00:00"
BODY = (
    '{"version": "1", "event_type": "message.inbound", '
    '"data": {"text": "José ✅"}}'
).encode("utf-8")
EXPECTED = "23e10a62fe99729b24278d75219b908d63ed27cd70dc0bcffd5d8f0ff26dd86b"


def main() -> None:
    got = compute_signature(SECRET, TIMESTAMP, BODY)
    assert got == EXPECTED, f"signature mismatch:\n  expected {EXPECTED}\n  got      {got}"
    assert is_valid_signature(SECRET, TIMESTAMP, BODY, EXPECTED), "verify should accept the valid sig"
    assert not is_valid_signature(SECRET, TIMESTAMP, BODY, "deadbeef"), "verify should reject a bad sig"
    print("OK — signature verification matches the test vector (incl. non-ASCII).")


if __name__ == "__main__":
    main()
