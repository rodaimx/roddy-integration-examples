'use strict';
// Minimal Roddy public-API client: send a message, upload media.
// Auth is a Bearer token from a token provider with an async getToken().
// Errors surface as RoddySendError carrying the stable machine `code` +
// `retriable` hint. Requires Node 18+ (global fetch/FormData/Blob).

class RoddySendError extends Error {
  constructor(status, code, message, retriable) {
    super(`[${status}] ${code || '-'}: ${message}`);
    this.status = status;
    this.code = code;
    this.detail = message;
    this.retriable = retriable;
  }
}

class RoddyClient {
  constructor(apiBaseUrl, tokens) {
    this._base = apiBaseUrl.replace(/\/+$/, '');
    this._tokens = tokens;
  }

  async _headers(extra) {
    return { Authorization: `Bearer ${await this._tokens.getToken()}`, ...(extra || {}) };
  }

  // `message` is one of the send shapes (text, image, whatsapp_template, …).
  // client_id is derived from your token — don't send it. Pass idempotencyKey
  // so a retry replays instead of resending.
  async sendMessage(channelId, contactId, message, { idempotencyKey } = {}) {
    const url = `${this._base}/v1/channels/${channelId}/contacts/${contactId}/messages`;
    const headers = await this._headers({ 'Content-Type': 'application/json' });
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    const resp = await fetch(url, { method: 'POST', headers, body: JSON.stringify(message) });
    if (!resp.ok) await raise(resp);
    return resp.json();
  }

  // Mint a size-capped presigned upload, push the bytes straight to storage,
  // and return the media_url to reference on a send.
  async uploadMedia(channelId, { mimeType, filename, fileBytes }) {
    const mint = await fetch(`${this._base}/v1/channels/${channelId}/media`, {
      method: 'POST',
      headers: await this._headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ mime_type: mimeType, filename }),
    });
    if (!mint.ok) await raise(mint);
    const target = await mint.json(); // upload_url, fields, media_url, max_bytes, ...

    const form = new FormData();
    for (const [k, v] of Object.entries(target.fields)) form.append(k, v);
    form.append('file', new Blob([fileBytes], { type: mimeType }), filename); // file LAST
    const up = await fetch(target.upload_url, { method: 'POST', body: form });
    if (!up.ok) throw new Error(`media upload failed: ${up.status} ${await up.text()}`);
    return target.media_url;
  }
}

async function raise(resp) {
  let body;
  try {
    body = await resp.json();
  } catch (_) {
    throw new RoddySendError(resp.status, null, await resp.text().catch(() => ''), false);
  }
  const d = body.details || {};
  throw new RoddySendError(resp.status, d.code || null, body.error || body.message || '', Boolean(d.retriable));
}

module.exports = { RoddyClient, RoddySendError };
