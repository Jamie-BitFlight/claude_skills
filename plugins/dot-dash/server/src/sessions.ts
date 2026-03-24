import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import type { InjectQueueItem, Session } from './types.js';

function findJsonlPath(cwd: string): string | null {
  const encoded = cwd.replace(/^\//, '').replace(/\//g, '-');
  const projectDir = join(homedir(), '.claude', 'projects', encoded);
  if (!existsSync(projectDir)) return null;
  const files = readdirSync(projectDir).filter((f) => f.endsWith('.jsonl'));
  if (files.length === 0) return null;
  return join(projectDir, files[0]);
}

export class SessionManager {
  private sessions = new Map<string, Session>();
  private injectQueues = new Map<string, InjectQueueItem[]>();

  register(id: string, cwd: string, pid: number): Session {
    const existing = this.sessions.get(id);
    if (existing && existing.status === 'active') return existing;
    const session: Session = {
      id,
      cwd,
      pid,
      status: 'active',
      registeredAt: new Date().toISOString(),
      lastEventAt: null,
      projectName: cwd.split('/').filter(Boolean).pop() ?? cwd,
      jsonlPath: findJsonlPath(cwd),
    };
    this.sessions.set(id, session);
    return session;
  }

  deregister(id: string): void {
    const session = this.sessions.get(id);
    if (session) {
      session.status = 'stopped';
      this.sessions.set(id, session);
    }
  }

  getAll(): Session[] {
    return Array.from(this.sessions.values());
  }

  get(id: string): Session | undefined {
    return this.sessions.get(id);
  }

  enqueueInjection(sessionId: string, message: string): void {
    const queue = this.injectQueues.get(sessionId) ?? [];
    queue.push({ message, enqueuedAt: new Date().toISOString() });
    this.injectQueues.set(sessionId, queue);
  }

  dequeueInjection(sessionId: string): InjectQueueItem | undefined {
    const queue = this.injectQueues.get(sessionId);
    if (!queue || queue.length === 0) return undefined;
    return queue.shift();
  }

  updateLastEvent(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.lastEventAt = new Date().toISOString();
      this.sessions.set(sessionId, session);
    }
  }
}
