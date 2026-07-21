'use strict';
// Send messages through the Roddy API — the transport-mode reply path.
//
//   npm install
//   cp .env.example .env      # fill client creds + channel/contact
//   node sendExample.js
//
// Shows: get a token (client-credentials, handled by RoddyTokenClient), send a
// text, then upload an image and send it. client_id is derived from your token.

require('dotenv').config();
const crypto = require('crypto');
const { RoddyTokenClient } = require('./auth');
const { RoddyClient, RoddySendError } = require('./roddyClient');

// A valid 1x1 PNG so the media example is self-contained.
const PIXEL_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64'
);

async function main() {
  const client = new RoddyClient(
    process.env.RODDY_API_BASE_URL,
    new RoddyTokenClient(
      process.env.AUTH_TOKEN_URL,
      process.env.CLIENT_ID,
      process.env.CLIENT_SECRET
    )
  );
  const channelId = process.env.CHANNEL_ID;
  const contactId = process.env.CONTACT_ID;

  try {
    const t = await client.sendMessage(
      channelId, contactId,
      { message_type: 'text', text: 'Hello from the Roddy example ✅' },
      { idempotencyKey: crypto.randomUUID() }
    );
    console.log('sent text →', t.message_id);

    const mediaUrl = await client.uploadMedia(channelId, {
      mimeType: 'image/png', filename: 'pixel.png', fileBytes: PIXEL_PNG,
    });
    const i = await client.sendMessage(
      channelId, contactId,
      { message_type: 'image', media_mime_type: 'image/png', media_url: mediaUrl, text: 'an uploaded image' },
      { idempotencyKey: crypto.randomUUID() }
    );
    console.log('sent image →', i.message_id);
  } catch (e) {
    if (e instanceof RoddySendError) {
      console.error(`send failed: status=${e.status} code=${e.code} retriable=${e.retriable} — ${e.detail}`);
    } else {
      throw e;
    }
  }
}

main();
