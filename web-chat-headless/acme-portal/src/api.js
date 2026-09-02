// The browser side of the identity recipe.
//
// The browser never sees the visitor secret — it holds only short-lived
// tokens minted by Acme's own backend (/api/chat-token), and it treats them
// as disposable: mint lazily, re-mint transparently when Roddy answers
// 401 visitor_token_expired, retry the request once. Users never notice a
// token expiring, and nothing long-lived is sitting in the browser to leak.

async function acmeJson(url, init) {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`${url} → HTTP ${response.status}`);
  return response.json();
}

export const getUsers = () => acmeJson("/api/users");
export const getMe = () => acmeJson("/api/me");
export const getConfig = () => acmeJson("/api/config");
export const login = (userId) =>
  acmeJson("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId }),
  });
export const logout = () => acmeJson("/api/logout", { method: "POST" });

let visitorToken = null;

async function mintToken() {
  const { token } = await acmeJson("/api/chat-token", { method: "POST" });
  visitorToken = token;
  return token;
}

/** Forget the cached token (call on Acme logout/user switch). */
export function resetToken() {
  visitorToken = null;
}

/**
 * fetch() for everything that talks to RODDY: injects the visitor token and,
 * on a 401 (expired or first-use), re-mints once and retries. Handed to the
 * AI SDK transport as its `fetch`, and used directly for GET /history — one
 * token policy for every call.
 */
export async function roddyFetch(input, init = {}) {
  const attempt = async () => {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${visitorToken ?? (await mintToken())}`);
    return fetch(input, { ...init, headers });
  };

  let response = await attempt();
  if (response.status === 401) {
    // Expired mid-session (or stale after a user switch): one fresh token,
    // one retry. Anything still 401 after that is a real refusal — let the
    // caller surface it.
    await mintToken();
    response = await attempt();
  }
  return response;
}

/**
 * The persisted conversation for THIS person on THIS channel, shaped for
 * useChat's initial messages. Replay rule: hand these to the SDK verbatim —
 * the API expects the transcript back exactly as it produced it.
 */
export async function fetchHistory(webChatUrl, channelId) {
  const response = await roddyFetch(
    `${webChatUrl}/history?channel_id=${encodeURIComponent(channelId)}`,
  );
  if (!response.ok) throw new Error(`history → HTTP ${response.status}`);
  return (await response.json()).messages;
}
