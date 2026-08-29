"""Minimal Roddy public-API client: send a message, upload media.

Auth is a Bearer token from :class:`auth.RoddyTokenClient`. Errors are surfaced
as :class:`RoddySendError` carrying the stable machine ``code`` + ``retriable``
hint so callers can branch (e.g. retry only when ``retriable`` is True).
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

import requests


class TokenProvider(Protocol):
    def get_token(self) -> str: ...


class RoddySendError(Exception):
    def __init__(self, status: int, code: Optional[str], message: str, retriable: bool):
        super().__init__(f"[{status}] {code or '-'}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.retriable = retriable


class RoddyClient:
    def __init__(self, api_base_url: str, tokens: TokenProvider) -> None:
        self._base = api_base_url.rstrip("/")
        self._tokens = tokens

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {"Authorization": f"Bearer {self._tokens.get_token()}"}
        h.update(extra or {})
        return h

    def send_message(
        self,
        channel_id: str,
        contact_id: str,
        message: dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """POST a message. ``message`` is one of the send shapes (text, image,
        whatsapp_template, …). ``client_id`` is derived from your token — don't
        send it. Pass ``idempotency_key`` so a retry replays instead of resending.
        """
        url = f"{self._base}/v1/channels/{channel_id}/contacts/{contact_id}/messages"
        headers = self._headers({"Content-Type": "application/json"})
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        resp = requests.post(url, json=message, headers=headers, timeout=30)
        if resp.status_code >= 400:
            _raise(resp)
        return resp.json()

    def upload_media(
        self, channel_id: str, *, mime_type: str, filename: str, file_bytes: bytes
    ) -> str:
        """Mint a size-capped presigned upload, push the bytes straight to
        storage, and return the ``media_url`` to reference on a send.

        The bytes never transit the Roddy API (bypasses the request-size limit),
        and storage enforces the per-type size cap server-side.
        """
        mint = requests.post(
            f"{self._base}/v1/channels/{channel_id}/media",
            json={"mime_type": mime_type, "filename": filename},
            headers=self._headers({"Content-Type": "application/json"}),
            timeout=30,
        )
        if mint.status_code >= 400:
            _raise(mint)
        target = mint.json()  # upload_url, upload_method, fields, media_url, max_bytes, expires_in
        # Multipart POST to storage: every returned field + the file LAST.
        up = requests.post(
            target["upload_url"],
            data=target["fields"],
            files={"file": (filename, file_bytes, mime_type)},
            timeout=60,
        )
        up.raise_for_status()
        return target["media_url"]


def _raise(resp: requests.Response) -> None:
    try:
        body = resp.json()
    except ValueError:
        raise RoddySendError(resp.status_code, None, resp.text, False)
    details = body.get("details") or {}
    raise RoddySendError(
        resp.status_code,
        details.get("code"),
        body.get("error") or body.get("message") or resp.text,
        bool(details.get("retriable")),
    )
