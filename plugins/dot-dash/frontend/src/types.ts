export interface Session {
  id: string;
  cwd: string;
  pid: number;
  status: 'active' | 'stopped';
  registeredAt: string;
  lastEventAt: string | null;
  projectName: string;
  jsonlPath: string | null;
}

export interface TranscriptEvent {
  sessionId: string;
  timestamp: string;
  type: string;
  content: unknown;
  raw: string;
}

export type WsMessageType =
  | 'session_registered'
  | 'session_stopped'
  | 'transcript_event'
  | 'sessions_snapshot'
  | 'error';

export interface WsMessage {
  type: WsMessageType;
  payload: unknown;
}
