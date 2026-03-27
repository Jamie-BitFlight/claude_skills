#!/usr/bin/env node
'use strict';

/**
 * Stop hook — checks after every orchestrator turn whether any kage-bunshin
 * child sessions spawned by THIS session are sitting idle (❯ prompt visible).
 * If idle sessions exist, emits a systemMessage reminding the orchestrator to
 * read or stop them.
 *
 * Session isolation: the hook reads the per-session registry written by
 * spawn.py at ~/.dh/projects/{slug}/kage-bunshin/registry-{session_id}.json
 * and only checks tmux sessions registered under the current session_id.
 *
 * Scope: plugin (development-harness)
 * Fires on: Stop (no matcher)
 * Action: non-blocking — emits systemMessage listing idle sessions with commands
 *
 * Test:
 *   echo '{"hook_event_name":"Stop","stop_hook_active":false,"session_id":"abc123"}' | node ./hooks/stop-kage-bunshin-idle-check.cjs
 */

const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  // Parse stdin — exit cleanly on failure
  let data = {};
  try {
    data = JSON.parse(input || '{}');
  } catch {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Avoid infinite loops — if stop hook is already active, do nothing
  if (data.stop_hook_active) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Skip processing in kage-bunshin child sessions — children must not alert about siblings
  if (process.env.KAGE_BUNSHIN_CHILD === '1') {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Require session_id — without it we cannot scope to this session
  const sessionId = data.session_id;
  if (!sessionId) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Resolve the git repo root to derive the DH state slug
  let repoRoot = '';
  try {
    repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], {
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 3000,
    })
      .toString('utf8')
      .trim();
  } catch {
    // Not inside a git repo — nothing to do
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Derive the project slug: replace all '/' with '-'
  // Example: /home/user/repos/claude_skills → -home-user-repos-claude_skills
  const slug = repoRoot.replace(/\//g, '-');

  // Resolve DH state home (respects DH_STATE_HOME override)
  const dhStateHome = process.env.DH_STATE_HOME || path.join(os.homedir(), '.dh');

  // --- Consume child-session notifications for this master session ---
  // Read notifications-{sessionId}.jsonl before the registry checks so that child
  // notifications are never missed even when the registry is absent (e.g. the child
  // stopped after the master cleaned up its registry). Delete the file after reading
  // to prevent stale notifications accumulating across turns.

  const notificationsPath = path.join(
    dhStateHome,
    'projects',
    slug,
    'kage-bunshin',
    `notifications-${sessionId}.jsonl`,
  );

  /** @type {Array<{tmux_session: string, event: string}>} */
  const notifications = [];
  try {
    const raw = fs.readFileSync(notificationsPath, { encoding: 'utf8' });
    for (const line of raw.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        notifications.push(JSON.parse(trimmed));
      } catch {
        // Malformed line — skip
      }
    }
  } catch {
    // File absent — no notifications pending
  }

  // Delete notifications file — entries are consumed once read
  if (notifications.length > 0) {
    try {
      fs.unlinkSync(notificationsPath);
    } catch {
      // Already gone or unwritable — non-fatal
    }
  }

  // --- Registry-based idle check ---
  // Read the per-session registry and check each registered tmux session for ❯
  const registryPath = path.join(
    dhStateHome,
    'projects',
    slug,
    'kage-bunshin',
    `registry-${sessionId}.json`,
  );
  let registry = {};
  try {
    const raw = fs.readFileSync(registryPath, { encoding: 'utf8' });
    registry = JSON.parse(raw);
  } catch {
    // Registry absent or unreadable — only notifications may produce a block
  }

  const tmuxSessions = Object.values(registry)
    .map((entry) => (entry && typeof entry.tmux_session === 'string' ? entry.tmux_session : null))
    .filter(Boolean);

  /** @type {string[]} */
  const idleSessions = [];

  if (tmuxSessions.length > 0) {
    // Verify tmux is available — list live sessions once for cross-reference
    let rawSessions = '';
    try {
      rawSessions = execFileSync('tmux', ['list-sessions', '-F', '#{session_name}'], {
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 3000,
      }).toString('utf8');
    } catch {
      // tmux not running or not installed — cannot check idle state
    }

    if (rawSessions) {
      const liveSessions = new Set(
        rawSessions
          .split('\n')
          .map((s) => s.trim())
          .filter((s) => s.length > 0),
      );

      // Intersect registry sessions with live tmux sessions
      const sessions = tmuxSessions.filter((s) => liveSessions.has(s));

      // Capture last 5 lines of each session and check for idle prompt (❯)
      for (const session of sessions) {
        let paneContent = '';
        try {
          paneContent = execFileSync(
            'tmux',
            ['capture-pane', '-p', '-J', '-t', session, '-S', '-5'],
            {
              stdio: ['ignore', 'pipe', 'ignore'],
              timeout: 2000,
            },
          ).toString('utf8');
        } catch {
          // Session may have ended between list and capture — skip it
          continue;
        }

        // Find the last non-empty line and check for idle prompt
        const lines = paneContent.split('\n').filter((l) => l.trim().length > 0);
        const lastLine = lines[lines.length - 1] || '';
        if (lastLine.includes('❯')) {
          idleSessions.push(session);
        }
      }
    }
  }

  // --- Classify stopped sessions from notifications: scan pane for interactive states ---
  /** @type {Array<{session: string, type: string, detail: string}>} */
  const interactiveSessions = [];

  const stoppedNotifications = notifications.filter((n) => n.event === 'stopped');
  for (const notification of stoppedNotifications) {
    const notifSession = notification.tmux_session;
    if (!notifSession) continue;

    let paneContent = '';
    try {
      paneContent = execFileSync(
        'tmux',
        ['capture-pane', '-p', '-J', '-t', notifSession, '-S', '-10'],
        {
          stdio: ['ignore', 'pipe', 'ignore'],
          timeout: 2000,
        },
      ).toString('utf8');
    } catch {
      // Session already gone — skip interactive detection
      continue;
    }

    const paneLines = paneContent.split('\n');
    const last5 = paneLines.slice(-5).join('\n');

    // Detect permission approval prompt: lines with Allow or Deny near ❯, >, or ●
    const hasPermissionPrompt = paneLines.some(
      (l) => /^[❯>●]/.test(l.trim()) && /Allow|Deny/.test(l),
    );

    // Detect yes/no prompt in last 5 lines
    const hasYesNo = /\[Y\/n\]|\[y\/N\]/i.test(last5);

    // Detect question-style prompt in last 5 lines (non-shell context)
    const hasQuestion =
      /Do you want to|Would you like to/.test(last5) ||
      (paneLines.some((l) => l.trim().endsWith('?')) &&
        !paneLines.some((l) => /^[❯>]\s*$/.test(l.trim())));

    if (hasPermissionPrompt) {
      interactiveSessions.push({
        session: notifSession,
        type: 'permission_approval',
        detail: 'Needs Allow/Deny response',
      });
    } else if (hasYesNo) {
      interactiveSessions.push({
        session: notifSession,
        type: 'yes_no_prompt',
        detail: 'Needs [Y/n] or [y/N] response',
      });
    } else if (hasQuestion) {
      interactiveSessions.push({
        session: notifSession,
        type: 'question',
        detail: 'Waiting for answer',
      });
    }
  }

  // Collect session_end notifications for mention in block message
  const completedSessions = notifications
    .filter((n) => n.event === 'session_end' && n.tmux_session)
    .map((n) => n.tmux_session);

  // Decide whether to block based on idle OR notification-interactive sessions
  const shouldBlock = idleSessions.length > 0 || interactiveSessions.length > 0;

  if (!shouldBlock) {
    // No idle, no interactive — no block needed
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Build block message
  const spawn = `${process.env.CLAUDE_PLUGIN_ROOT || '.'}/skills/kage-bunshin/scripts/spawn.py`;

  const messageParts = [];

  if (idleSessions.length > 0) {
    const sessionList = idleSessions.map((s) => `  - ${s}`).join('\n');
    const commands = idleSessions
      .map((s) => {
        const match = s.match(/_worktree-(.+)$/);
        const name = match ? match[1] : s;
        return `  uv run ${spawn} read --name ${name}  # read output\n  uv run ${spawn} stop --name ${name}  # graceful Ctrl-C shutdown`;
      })
      .join('\n');

    messageParts.push(
      `Kage-bunshin sessions idle (❯ prompt) — ${idleSessions.length} finished:`,
      sessionList,
      '',
      'Read output and stop when done:',
      commands,
    );
  }

  if (interactiveSessions.length > 0) {
    messageParts.push('');
    messageParts.push('Needs your response:');
    for (const s of interactiveSessions) {
      messageParts.push(`  - ${s.session} [${s.type}]: ${s.detail}`);
    }
  }

  if (completedSessions.length > 0) {
    messageParts.push('');
    messageParts.push('Sessions completed:');
    for (const s of completedSessions) {
      messageParts.push(`  - ${s}`);
    }
  }

  const message = messageParts.join('\n');

  process.stdout.write(JSON.stringify({ decision: 'block', reason: message }));
  process.exit(0);
});
