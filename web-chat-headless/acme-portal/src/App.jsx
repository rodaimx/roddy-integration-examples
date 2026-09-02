import { useEffect, useState } from "react";
import {
  fetchHistory,
  getConfig,
  getMe,
  getUsers,
  login,
  logout,
  resetToken,
} from "./api.js";
import { Chat } from "./Chat.jsx";

/**
 * Acme Portal — a made-up internal tool with its own login, and Roddy's chat
 * as one pane of it. The shell owns Acme's session; the chat pane owns
 * nothing about identity (see Chat.jsx). The `key={user.id}` on the chat
 * subtree is what makes "switch user" honest: new user, new transport, new
 * transcript — because a different `sub` IS a different conversation.
 */
export function App() {
  const [users, setUsers] = useState([]);
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    Promise.all([getUsers(), getMe()])
      .then(([list, me]) => {
        setUsers(list);
        setUser(me.user);
      })
      .finally(() => setBooting(false));
  }, []);

  const switchUser = async (userId) => {
    resetToken(); // the old user's visitor token must not leak into the new session
    const { user: logged } = await login(userId);
    setUser(logged);
  };

  const leave = async () => {
    await logout();
    resetToken();
    setUser(null);
  };

  if (booting) return <div className="shell">cargando…</div>;

  return (
    <div className="shell">
      <header>
        <h1>Acme Portal</h1>
        {user && (
          <div className="who">
            <span>
              {user.name} · {user.role} <code>({user.id})</code>
            </span>
            <button onClick={leave}>Salir</button>
          </div>
        )}
      </header>

      {!user ? (
        <Login users={users} onPick={switchUser} />
      ) : (
        <ChatSession key={user.id} />
      )}
    </div>
  );
}

function Login({ users, onPick }) {
  return (
    <main className="login">
      <p>
        Inicia sesión en <strong>Acme</strong> (no en Roddy — Roddy nunca ve
        este login; solo recibe tokens firmados por el backend de Acme):
      </p>
      {users.map((candidate) => (
        <button key={candidate.id} onClick={() => onPick(candidate.id)}>
          {candidate.name} — {candidate.role}
        </button>
      ))}
    </main>
  );
}

/** Loads config + this person's persisted history BEFORE mounting the chat,
 * so useChat is seeded exactly once with the verbatim transcript. */
function ChatSession() {
  const [state, setState] = useState({ phase: "loading" });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const config = await getConfig();
        const history = await fetchHistory(config.webChatUrl, config.channelId);
        if (alive) setState({ phase: "ready", config, history });
      } catch (error) {
        if (alive) setState({ phase: "error", error });
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (state.phase === "loading") return <main>abriendo tu conversación…</main>;
  if (state.phase === "error")
    return <main className="error">No se pudo abrir el chat: {String(state.error)}</main>;

  return (
    <Chat
      webChatUrl={state.config.webChatUrl}
      channelId={state.config.channelId}
      history={state.history}
    />
  );
}
