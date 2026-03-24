import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

function findJsonlPath(cwd) {
  const encoded = cwd.replace(/^\//, '').replace(/\//g, '-');
  const projectDir = join(homedir(), '.claude', 'projects', encoded);
  if (!existsSync(projectDir)) return null;
  const files = readdirSync(projectDir).filter((f) => f.endsWith('.jsonl'));
  if (files.length === 0) return null;
  return join(projectDir, files[0]);
}
export class SessionManager {
  sessions = new Map();
  injectQueues = new Map();
  register(id, cwd, pid) {
    const existing = this.sessions.get(id);
    if (existing && existing.status === 'active') return existing;
    const session = {
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
  deregister(id) {
    const session = this.sessions.get(id);
    if (session) {
      session.status = 'stopped';
      this.sessions.set(id, session);
    }
  }
  getAll() {
    return Array.from(this.sessions.values());
  }
  get(id) {
    return this.sessions.get(id);
  }
  enqueueInjection(sessionId, message) {
    const queue = this.injectQueues.get(sessionId) ?? [];
    queue.push({ message, enqueuedAt: new Date().toISOString() });
    this.injectQueues.set(sessionId, queue);
  }
  dequeueInjection(sessionId) {
    const queue = this.injectQueues.get(sessionId);
    if (!queue || queue.length === 0) return undefined;
    return queue.shift();
  }
  updateLastEvent(sessionId) {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.lastEventAt = new Date().toISOString();
      this.sessions.set(sessionId, session);
    }
  }
}
