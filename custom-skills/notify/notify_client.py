"""Minimal read-only client for the Rodai Notify REST API.

The token is NEVER stored in this repo. It is read at runtime from the same
places the `notify` CLI reads it, in the same order:

    1. env vars ``RODAI_NOTIFY_TOKEN`` / ``RODAI_NOTIFY_URL`` (override)
    2. ``.rodai-notify.json`` found walking up from the current directory
    3. ``~/.config/rodai-notify/config.json`` (written by ``notify config set token``)

So if the CLI works on this machine, the skill works — no copying secrets
around. If you deploy this somewhere, set the env vars there instead; don't
ship the config file.

Read-only on purpose: this is a test skill. Every call an agent can trigger is
a GET. Adding writes means adding an authorization story first (see README).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://rodainotify.com"
GLOBAL_CONFIG_PATH = Path.home() / ".config" / "rodai-notify" / "config.json"
LOCAL_CONFIG_NAME = ".rodai-notify.json"
API_VERSION = "v1"


class NotifyError(Exception):
    """An API call failed. ``detail`` is safe to log; it never holds the token."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"Notify HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _find_local_config() -> Path | None:
    here = Path.cwd().resolve()
    for directory in (here, *here.parents):
        candidate = directory / LOCAL_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def load_config() -> tuple[str | None, str, str]:
    """Return ``(token, base_url, source)``. ``source`` is for logging only."""
    config: dict = {}
    source = "defaults"

    if GLOBAL_CONFIG_PATH.is_file():
        config.update({k: v for k, v in _read_json(GLOBAL_CONFIG_PATH).items() if v})
        source = str(GLOBAL_CONFIG_PATH)

    local = _find_local_config()
    if local:
        config.update({k: v for k, v in _read_json(local).items() if v})
        source = str(local)

    token = os.environ.get("RODAI_NOTIFY_TOKEN") or config.get("token")
    url = os.environ.get("RODAI_NOTIFY_URL") or config.get("url") or DEFAULT_URL
    if os.environ.get("RODAI_NOTIFY_TOKEN"):
        source = "env"
    return token, url.rstrip("/"), source


class NotifyClient:
    """Thin GET-only wrapper. Raises :class:`NotifyError` on any non-2xx."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self.token, self.base_url, self.source = load_config()
        self.timeout = timeout_seconds
        if not self.token:
            raise NotifyError(
                0,
                "no Notify token configured — run `notify config set token`, "
                "or set RODAI_NOTIFY_TOKEN",
            )

    def get(self, path: str, params: dict | None = None) -> object:
        query = dict(params or {})
        query.setdefault("version", API_VERSION)
        clean = {k: v for k, v in query.items() if v is not None}
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(clean, doseq=True)}"

        request = urllib.request.Request(
            url, method="GET", headers={"Authorization": f"Bearer {self.token}"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            # Read the body for context, but cap it — a stack trace from the
            # server is not something to forward verbatim into a chat message.
            detail = (error.read() or b"")[:300].decode("utf-8", "replace")
            raise NotifyError(error.code, detail or error.reason) from error
        except urllib.error.URLError as error:
            raise NotifyError(0, f"cannot reach {self.base_url}: {error.reason}") from error

        return json.loads(body) if body else None

    # --- read-only operations exposed to the agent -------------------------

    def list_projects(self, search: str | None = None, limit: int = 10) -> list[dict]:
        # Projects filter on `q`; tasks filter on `search`. Not a typo.
        data = self.get("/projects/api/project/", {"q": search, "is_active": "true"})
        rows = data.get("results", data) if isinstance(data, dict) else data
        # The projects endpoint keys the id as `pk`; tasks use `id`. Normalize
        # here so callers don't have to remember which is which.
        return [{**row, "id": row.get("pk", row.get("id"))} for row in (rows or [])][:limit]

    def list_cards(
        self,
        project_id: int,
        search: str | None = None,
        assignee_id: int | None = None,
        limit: int = 10,
    ) -> list[dict]:
        data = self.get(
            "/projects/api/tasks/",
            {
                "project": project_id,
                "search": search,
                "usertask__user": assignee_id,
                # The endpoint has no default ordering, so a paginated read
                # duplicates some rows and drops others. Force a stable sort.
                "ordering": "id",
            },
        )
        rows = data.get("results", data) if isinstance(data, dict) else data
        return list(rows or [])[:limit]

    def get_card(self, card_id: int) -> dict:
        data = self.get(f"/projects/api/tasks/{card_id}/")
        if not isinstance(data, dict):
            raise NotifyError(0, f"unexpected payload for card {card_id}")
        return data
