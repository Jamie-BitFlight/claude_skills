import { useEffect, useRef } from 'react';
import type { TranscriptEvent } from '../types.js';

interface Props {
  sessionId: string | null;
  events: TranscriptEvent[];
}

function extractText(event: TranscriptEvent): string {
  const c = event.content as Record<string, unknown>;
  if (typeof c?.text === 'string') return c.text;
  const parts = c?.content;
  if (Array.isArray(parts) && parts.length > 0) {
    const first = parts[0] as Record<string, unknown>;
    if (typeof first?.text === 'string') return first.text;
  }
  return JSON.stringify(event.content, null, 2);
}

export function Transcript({ sessionId, events }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  const eventsCount = events.length;
  // biome-ignore lint/correctness/useExhaustiveDependencies: eventsCount change triggers scroll when new events arrive; bottomRef is a stable ref
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [eventsCount]);

  if (!sessionId) {
    return (
      <div className="transcript transcript-no-session">
        <div className="transcript-placeholder">Select a session to view transcript</div>
      </div>
    );
  }

  return (
    <div className="transcript">
      <div className="transcript-header">
        <span className="transcript-title">Transcript</span>
        <span className="event-count">{events.length} events</span>
      </div>
      <div className="transcript-body">
        {events.length === 0 && <div className="transcript-empty-session">Waiting for events…</div>}
        {events.map((evt) => {
          const evtKey = `${evt.sessionId}-${evt.timestamp}-${evt.type}`;
          const type = evt.type;
          if (type === 'user' || type === 'human') {
            return (
              <div key={evtKey} className="message user-message">
                <div className="message-role">User</div>
                <div className="message-text">{extractText(evt)}</div>
                <div className="message-time">{new Date(evt.timestamp).toLocaleTimeString()}</div>
              </div>
            );
          }
          if (type === 'assistant') {
            return (
              <div key={evtKey} className="message assistant-message">
                <div className="message-role">Claude</div>
                <div className="message-text">{extractText(evt)}</div>
                <div className="message-time">{new Date(evt.timestamp).toLocaleTimeString()}</div>
              </div>
            );
          }
          return (
            <div key={evtKey} className="event-system">
              <span className="event-type">{type}</span>
              <span className="event-time">{new Date(evt.timestamp).toLocaleTimeString()}</span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
