"""Send messages through the Roddy API — the transport-mode reply path.

    cp .env.example .env      # fill client creds + channel/contact
    python send_example.py

Shows: get a token (client-credentials, handled by RoddyTokenClient), send a
text, then upload an image and send it. `client_id` is derived from your token,
so it's never in the body.
"""

from __future__ import annotations

import base64
import os
import uuid

from auth import RoddyTokenClient
from roddy_client import RoddyClient, RoddySendError

# A valid 1x1 PNG, so the media example is self-contained (no asset file needed).
PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def main() -> None:
    client = RoddyClient(
        os.environ["RODDY_API_BASE_URL"],
        RoddyTokenClient(
            os.environ["AUTH_TOKEN_URL"],
            os.environ["CLIENT_ID"],
            os.environ["CLIENT_SECRET"],
        ),
    )
    channel_id = os.environ["CHANNEL_ID"]
    contact_id = os.environ["CONTACT_ID"]

    try:
        # 1) A plain text message.
        r = client.send_message(
            channel_id,
            contact_id,
            {"message_type": "text", "text": "Hello from the Roddy example ✅"},
            idempotency_key=str(uuid.uuid4()),
        )
        print("sent text →", r.get("message_id"))

        # 2) Media: upload the bytes, then send by the returned (owned) URL.
        media_url = client.upload_media(
            channel_id, mime_type="image/png", filename="pixel.png", file_bytes=PIXEL_PNG
        )
        r = client.send_message(
            channel_id,
            contact_id,
            {
                "message_type": "image",
                "media_mime_type": "image/png",
                "media_url": media_url,
                "text": "an uploaded image",
            },
            idempotency_key=str(uuid.uuid4()),
        )
        print("sent image →", r.get("message_id"))

    except RoddySendError as e:
        # Branch on the stable code; retry only when retriable.
        print(f"send failed: status={e.status} code={e.code} retriable={e.retriable} — {e.message}")


if __name__ == "__main__":
    main()
