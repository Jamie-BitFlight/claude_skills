import type { Session } from '../types.js';

interface Props {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  return `${Math.floor(diff / 3_600_000)}h ago`;
}

export function SessionList({ sessions, selectedId, onSelect }: Props) {
  const active = sessions.filter((s) => s.status === 'active');
  const stopped = sessions.filter((s) => s.status === 'stopped');

  return (
    <div className="session-list">
      <div className="session-list-header">
        <span className="session-list-title">Sessions</span>
        <span className="session-count">{active.length} active</span>
      </div>
      {sessions.length === 0 && (
        <div className="session-empty">
          No sessions registered.
          <br />
          Start a Claude Code session to see it here.
        </div>
      )}
      {[...active, ...stopped].map((session) => (
        <button
          key={session.id}
          type="button"
          className={`session-card ${session.status}${selectedId === session.id ? ' selected' : ''}`}
          onClick={() => onSelect(session.id)}
        >
          <div className="session-card-header">
            <span className={`status-dot ${session.status}`} />
            <span className="project-name">{session.projectName}</span>
          </div>
          <div className="session-cwd">{session.cwd}</div>
          <div className="session-meta">
            <span>PID {session.pid}</span>
            <span>{relativeTime(session.lastEventAt)}</span>
          </div>
        </button>
      ))}
    </div>
  );
}
