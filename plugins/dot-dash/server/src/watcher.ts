import { openSync, readSync, statSync } from 'node:fs';
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

      const prevPos = positions.get(filePath);

      // First time seeing this file — start tracking from current end, ignore history.
      if (prevPos === undefined) {
        positions.set(filePath, stat.size);
        return;
      }

      // Handle truncation (log rotation or file reset).
      const pos = stat.size < prevPos ? 0 : prevPos;

      if (stat.size <= pos) return;

      // Read only the new bytes using offset-based I/O.
      const length = stat.size - pos;
      const buf = Buffer.allocUnsafe(length);
      const fd = openSync(filePath, 'r');
      try {
        readSync(fd, buf, 0, length, pos);
      } finally {
        // fs.closeSync is not imported to keep the import list minimal; use require inline.
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        require('node:fs').closeSync(fd);
      }

      positions.set(filePath, pos + length);

      const newContent = buf.toString('utf8');
      const lines = newContent.split('\n').filter((l) => l.trim().length > 0);

      // Find which session owns this file.
      const allSessions = sessions.getAll();
      const owningSession = allSessions.find((s) => s.jsonlPath === filePath);
      if (!owningSession) return;

      for (const line of lines) {
        let parsedRecord: unknown;
        try {
          parsedRecord = JSON.parse(line);
        } catch {
          continue;
        }
        const timestampField = (parsedRecord as Record<string, unknown>)?.timestamp;
        const timestamp =
          typeof timestampField === 'string' && timestampField.length > 0
            ? timestampField
            : new Date().toISOString();
        const evt: TranscriptEvent = {
          sessionId: owningSession.id,
          timestamp,
          type: (parsedRecord as Record<string, string>)?.type ?? 'unknown',
          content: parsedRecord,
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
