import { useMemo, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { roddyFetch } from "./api.js";

/**
 * The chat pane. This is ordinary Vercel AI SDK usage — the only
 * Roddy-specific pieces are:
 *
 *  - `fetch: roddyFetch`  → visitor token injected + re-minted on expiry;
 *  - `body: { channel_id }` → which Roddy channel this is;
 *  - `messages: history`  → the persisted conversation, passed VERBATIM.
 *
 * Who is talking is NOT in this component at all: the token decides it.
 * Mount it with a `key` per logged-in user so a user switch gets a fresh
 * transport and a fresh transcript.
 */
export function Chat({ webChatUrl, channelId, history }) {
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${webChatUrl}/`,
        body: { channel_id: channelId },
        fetch: roddyFetch,
      }),
    [webChatUrl, channelId],
  );

  const { messages, sendMessage, status, error } = useChat({
    transport,
    messages: history,
  });
  const [draft, setDraft] = useState("");

  const submit = (event) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text || status === "streaming" || status === "submitted") return;
    setDraft("");
    sendMessage({ text });
  };

  return (
    <div className="chat">
      <div className="messages">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {status === "submitted" && <div className="typing">pensando…</div>}
        {error && <div className="error">Algo falló: {String(error)}</div>}
      </div>
      <form onSubmit={submit} className="composer">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Escribe tu mensaje…"
          autoFocus
        />
        <button disabled={status === "streaming" || status === "submitted"}>
          Enviar
        </button>
      </form>
    </div>
  );
}

function Message({ message }) {
  // A message is parts, not a string. Text is what we render; Roddy's own
  // data parts (data-roddy-turn-status, data-roddy-tool-activity) arrive as
  // standard data parts — surface the two interesting ones, ignore the rest.
  const texts = message.parts.filter((part) => part.type === "text");
  const turnStatus = message.parts.find(
    (part) => part.type === "data-roddy-turn-status",
  );
  const activity = message.parts.filter(
    (part) => part.type === "data-roddy-tool-activity",
  );

  return (
    <div className={`bubble ${message.role}`}>
      {activity.length > 0 && (
        <div className="activity">
          {activity.map((part, index) => (
            <span key={index}>⚙ {part.data?.label ?? "trabajando…"}</span>
          ))}
        </div>
      )}
      {texts.map((part, index) => (
        <p key={index}>{part.text}</p>
      ))}
      {turnStatus && !texts.length && (
        <p className="muted">
          {/* No agent answered (human-only channel, paused, …). The message
              WAS received — say so instead of showing an empty bubble. */}
          Recibido — una persona del equipo te responderá aquí.
        </p>
      )}
    </div>
  );
}
