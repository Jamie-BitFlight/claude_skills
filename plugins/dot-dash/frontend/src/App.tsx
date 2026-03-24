import { useCallback, useEffect, useReducer, useState } from 'react';
import { Controls } from './components/Controls.js';
import { SessionList } from './components/SessionList.js';
import { Transcript } from './components/Transcript.js';
import { getToken, setToken } from './lib/api.js';
import { WsManager } from './lib/websocket.js';
import type { Session, TranscriptEvent, WsMessage } from './types.js';

type EventMap = Map<string, TranscriptEvent[]>;

interface AppState {
  sessions: Session[];
  events: EventMap;
  selectedId: string | null;
  wsConnected: boolean;
}

type Action =
  | { type: 'set_sessions'; sessions: Session[] }
  | { type: 'add_session'; session: Session }
  | { type: 'stop_session'; sessionId: string }
  | { type: 'add_event'; event: TranscriptEvent }
  | { type: 'select'; id: string | null }
  | { type: 'set_connected'; connected: boolean };

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'set_sessions':
      return { ...state, sessions: action.sessions };
    case 'add_session':
      return {
        ...state,
        sessions: [...state.sessions.filter((s) => s.id !== action.session.id), action.session],
      };
    case 'stop_session':
      return {
        ...state,
        sessions: state.sessions.map((s) =>
          s.id === action.sessionId ? { ...s, status: 'stopped' as const } : s,
        ),
      };
    case 'add_event': {
      const prev = state.events.get(action.event.sessionId) ?? [];
      const next = new Map(state.events);
      next.set(action.event.sessionId, [...prev, action.event]);
      return { ...state, events: next };
    }
    case 'select':
      return { ...state, selectedId: action.id };
    case 'set_connected':
      return { ...state, wsConnected: action.connected };
    default:
      return state;
  }
}

function TokenGate({ onToken }: { onToken: (t: string) => void }) {
  const [input, setInput] = useState('');
  return (
    <div className="token-gate">
      <div className="token-gate-box">
        <h2>dot-dash</h2>
        <p>Enter your bearer token to connect.</p>
        <p className="token-hint">
          Find it at <code>~/.claude/dot-dash/token</code>
        </p>
        <input
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && input && onToken(input)}
          placeholder="Paste token…"
        />
        <button type="button" onClick={() => input && onToken(input)}>
          Connect
        </button>
      </div>
    </div>
  );
}

export function App() {
  const [state, dispatch] = useReducer(reducer, {
    sessions: [],
    events: new Map(),
    selectedId: null,
    wsConnected: false,
  });

  const [token, setTokenState] = useState<string | null>(getToken);

  const handleToken = useCallback((t: string) => {
    setToken(t);
    setTokenState(t);
  }, []);

  useEffect(() => {
    if (!token) return;
    const manager = new WsManager(token);

    const removeHandler = manager.addHandler((msg: WsMessage) => {
      switch (msg.type) {
        case 'sessions_snapshot':
          dispatch({ type: 'set_sessions', sessions: msg.payload as Session[] });
          dispatch({ type: 'set_connected', connected: true });
          break;
        case 'session_registered':
          dispatch({ type: 'add_session', session: msg.payload as Session });
          break;
        case 'session_stopped':
          dispatch({
            type: 'stop_session',
            sessionId: (msg.payload as { sessionId: string }).sessionId,
          });
          break;
        case 'transcript_event':
          dispatch({ type: 'add_event', event: msg.payload as TranscriptEvent });
          break;
        case 'error':
          break;
      }
    });

    manager.connect();

    return () => {
      removeHandler();
      manager.disconnect();
    };
  }, [token]);

  const selectedSession = state.sessions.find((s) => s.id === state.selectedId) ?? null;
  const selectedEvents = state.selectedId ? (state.events.get(state.selectedId) ?? []) : [];

  if (!token) {
    return <TokenGate onToken={handleToken} />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-title">dot-dash</span>
        <span className="app-subtitle">Claude Code Dashboard</span>
        <span className={`ws-indicator ${state.wsConnected ? 'connected' : 'disconnected'}`}>
          {state.wsConnected ? '● live' : '○ connecting…'}
        </span>
      </header>
      <main className="app-main">
        <SessionList
          sessions={state.sessions}
          selectedId={state.selectedId}
          onSelect={(id) => dispatch({ type: 'select', id })}
        />
        <Transcript sessionId={state.selectedId} events={selectedEvents} />
        <Controls
          selectedSession={selectedSession}
          onSessionDeleted={(id) => dispatch({ type: 'stop_session', sessionId: id })}
        />
      </main>
    </div>
  );
}
