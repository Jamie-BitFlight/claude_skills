import { useState } from 'react';
import { deleteSession, injectPrompt } from '../lib/api.js';
import type { Session } from '../types.js';

interface Props {
  selectedSession: Session | null;
  onSessionDeleted: (id: string) => void;
}

export function Controls({ selectedSession, onSessionDeleted }: Props) {
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  async function handleInject() {
    if (!selectedSession || !message.trim()) return;
    try {
      await injectPrompt(selectedSession.id, message.trim());
      setMessage('');
      setStatus('Queued — will inject on next user prompt');
      setTimeout(() => setStatus(null), 3000);
    } catch (err) {
      setStatus(`Error: ${String(err)}`);
    }
  }

  async function handleStop() {
    if (!selectedSession) return;
    try {
      await deleteSession(selectedSession.id);
      onSessionDeleted(selectedSession.id);
    } catch (err) {
      setStatus(`Error: ${String(err)}`);
    }
  }

  return (
    <div className="controls">
      <div className="controls-header">Controls</div>
      {!selectedSession ? (
        <div className="controls-empty">Select a session</div>
      ) : (
        <>
          <div className="controls-section">
            <div className="controls-label">Inject prompt into</div>
            <div className="controls-session-name">{selectedSession.projectName}</div>
          </div>
          <div className="controls-section">
            <textarea
              className="inject-textarea"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Message to inject before next user prompt…"
              rows={6}
            />
            <button
              type="button"
              className="inject-button"
              onClick={() => void handleInject()}
              disabled={!message.trim()}
            >
              Queue Injection
            </button>
            {status && <div className="status-message">{status}</div>}
          </div>
          <div className="controls-section">
            <button
              type="button"
              className="stop-button"
              onClick={() => void handleStop()}
              disabled={selectedSession.status !== 'active'}
            >
              Deregister Session
            </button>
          </div>
        </>
      )}
    </div>
  );
}
