#!/usr/bin/env node
'use strict';

/**
 * TaskCompleted hook — reminds the orchestrator to clean up kage-bunshin
 * tmux sessions when a task is marked complete.
 *
 * Session isolation: reads the per-session registry at
 * ~/.dh/projects/{slug}/kage-bunshin/registry-{session_id}.json and only
 * reports sessions registered under the current session_id. Falls through
 * silently when session_id is absent or the registry is missing.
 *
 * Scope: plugin (development-harness)
 * Fires on: TaskCompleted (no matcher)
 * Action: non-blocking — emits systemMessage listing active worktree sessions
 *
 * Test:
 *   echo '{"hook_event_name":"TaskCompleted","session_id":"abc123"}' | node ./hooks/task-completed-kage-bunshin-reminder.cjs
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
  const slug = repoRoot.replace(/\//g, '-');

  // Resolve DH state home (respects DH_STATE_HOME override)
  const dhStateHome = process.env.DH_STATE_HOME || path.join(os.homedir(), '.dh');

  // Read the per-session registry
  const registryPath = path.join(
    dhStateHome,
    'projects',
    slug,
    'kage-bunshin',
    `registry-${sessionId}.json`,
  );
  let registry = {};
  try {
    const raw = fs.readFileSync(registryPath, { encoding: 'utf8', timeout: 5000 });
    registry = JSON.parse(raw);
  } catch {
    // Registry absent or unreadable — no sessions registered for this session
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Extract tmux session names registered under this session_id
  const registeredTmuxSessions = new Set(
    Object.values(registry)
      .map((entry) => (entry && typeof entry.tmux_session === 'string' ? entry.tmux_session : null))
      .filter(Boolean),
  );

  if (registeredTmuxSessions.size === 0) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // List tmux sessions — suppress stderr so hook never leaks noise
  let rawSessions = '';
  try {
    rawSessions = execFileSync('tmux', ['list-sessions', '-F', '#{session_name}'], {
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 3000,
    }).toString('utf8');
  } catch {
    // tmux not running or not installed — no sessions to report
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Filter to kage-bunshin worktree sessions belonging to THIS session's registry
  const sessions = rawSessions
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.includes('_worktree-') && registeredTmuxSessions.has(s));

  if (sessions.length === 0) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Build reminder message
  const spawn = `${process.env.CLAUDE_PLUGIN_ROOT || '.'}/skills/kage-bunshin/scripts/spawn.py`;
  const sessionList = sessions.map((s) => `  - ${s}`).join('\n');
  const commands = sessions
    .map((s) => {
      const match = s.match(/_worktree-(.+)$/);
      const name = match ? match[1] : s;
      return `  uv run ${spawn} read --name ${name}  # check if idle (❯) or working\n  uv run ${spawn} stop --name ${name}  # graceful Ctrl-C shutdown`;
    })
    .join('\n');
  const fullMessage = [
    `Kage-bunshin worktree sessions still running (${sessions.length}):`,
    sessionList,
    '',
    'Check state then gracefully stop:',
    commands,
    '',
    `List all sessions: uv run ${spawn} list`,
  ].join('\n');

  // Truncate to 500 chars — injected on every task completion; 51 firings × full message
  // consumed 105K+ chars. The orchestrator needs session count and registry path only;
  // full command listings can be found in the registry file.
  const MAX_CHARS = 500;
  const message =
    fullMessage.length > MAX_CHARS
      ? `${fullMessage.slice(0, MAX_CHARS)}\u2026[truncated \u2014 full details at: ${registryPath}]`
      : fullMessage;

  const output = {
    systemMessage: message,
  };

  process.stdout.write(JSON.stringify(output));
  process.exit(0);
});
