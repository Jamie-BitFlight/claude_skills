import { readFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import chokidar from 'chokidar';
import type { SessionManager } from './sessions.js';
import type { TranscriptEvent } from './types.js';

export function createWatcher(
  sessions: SessionManager,
  onEvent: (sessionId: string, event: TranscriptEvent) => void,
) {
  const positions = new Map<string, number>();
  const watchGlob = join(homedir(), '.claude', 'projects', '**', '*.jsonl');

  const watcher = chokidar.watch(watchGlob, {
    persistent: true,
    ignoreInitial: true,
    awaitWriteFinish: { stabilityThreshold: 50, pollInterval: 50 },
  });

  function readNewLines(filePath: string) {
    try {
      const stat = statSync(filePath);
      const pos = positions.get(filePath) ?? stat.size;
      if (stat.size <= pos) return;
      const buf = readFileSync(filePath);
      const newContent = buf.slice(pos).toString('utf8');
      positions.set(filePath, stat.size);
      const lines = newContent.split('\n').filter((l) => l.trim().length > 0);
      // Find which session owns this file
      const allSessions = sessions.getAll();
      const owningSession = allSessions.find((s) => s.jsonlPath === filePath);
      if (!owningSession) return;
      for (const line of lines) {
        let parsed: unknown;
        try {
          parsed = JSON.parse(line);
        } catch {
          continue;
        }
        const evt: TranscriptEvent = {
          sessionId: owningSession.id,
          timestamp: new Date().toISOString(),
          type: (parsed as Record<string, string>)?.type ?? 'unknown',
          content: parsed,
          raw: line,
        };
        sessions.updateLastEvent(owningSession.id);
        onEvent(owningSession.id, evt);
      }
    } catch {
      // File may be temporarily unavailable
    }
  }

  watcher.on('add', readNewLines);
  watcher.on('change', readNewLines);

  return watcher;
}
