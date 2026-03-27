#!/usr/bin/env node
'use strict';

/**
 * SessionEnd hook — gracefully stops all kage-bunshin tmux sessions owned by
 * the ending orchestrator session. Prevents orphaned sessions running with no
 * controller.
 *
 * Session isolation: reads the per-session registry at
 * ~/.dh/projects/{slug}/kage-bunshin/registry-{session_id}.json and only
 * cleans up sessions registered under the ending session_id. Sessions
 * belonging to other active orchestrators are left untouched.
 *
 * Scope: plugin (development-harness)
 * Fires on: SessionEnd (no matcher)
 * Action: side effect — sends C-c to each session then force-kills stragglers
 *
 * Test:
 *   echo '{"hook_event_name":"SessionEnd","reason":"other","session_id":"abc123"}' | node ./hooks/session-end-kage-bunshin-cleanup.cjs
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

  // Skip processing in kage-bunshin child sessions — children manage no subordinate sessions
  if (process.env.KAGE_BUNSHIN_CHILD === '1') {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Require session_id — without it we cannot scope cleanup to this session
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
    // Not inside a git repo — nothing to clean up
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
    // Registry absent or unreadable — no sessions to clean up for this session
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Extract tmux session names registered under this session_id
  const sessions = Object.values(registry)
    .map((entry) => (entry && typeof entry.tmux_session === 'string' ? entry.tmux_session : null))
    .filter(Boolean);

  if (sessions.length === 0) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Fire-and-forget: signal then immediately kill each session.
  // No polling — the hook budget is 8s actual work inside the 10s timeout.
  for (const session of sessions) {
    try {
      execFileSync('tmux', ['send-keys', '-t', session, 'C-c', ''], {
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 2000,
      });
    } catch {
      // Session may have already exited — ignore
    }
    try {
      execFileSync('tmux', ['kill-session', '-t', session], {
        stdio: ['ignore', 'pipe', 'ignore'],
        timeout: 2000,
      });
    } catch {
      // Already gone — ignore
    }
  }

  process.stdout.write(JSON.stringify({}));
  process.exit(0);
});
