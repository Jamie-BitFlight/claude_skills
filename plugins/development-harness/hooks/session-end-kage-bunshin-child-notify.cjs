#!/usr/bin/env node
'use strict';

/**
 * SessionEnd hook — child-session notification writer.
 *
 * Fires when a kage-bunshin child session's session ends (logout, other, or
 * prompt_input_exit — not /clear, which is a routine context reset). Appends a
 * JSONL entry to the parent session's notifications file so the master Stop
 * hook can report which sessions have completed.
 *
 * Scope: plugin (development-harness)
 * Fires on: SessionEnd — matcher: logout|other|prompt_input_exit
 * Action: non-blocking — fs.appendFileSync to notifications file, exits 0
 *
 * Only active in kage-bunshin child sessions (KAGE_BUNSHIN_CHILD === '1').
 * Master sessions pass through immediately at the first guard check.
 *
 * Test:
 *   KAGE_BUNSHIN_CHILD=1 \
 *   KAGE_BUNSHIN_PARENT_SESSION_ID=abc123 \
 *   KAGE_BUNSHIN_TMUX_SESSION=claude_skills_worktree-test-1 \
 *   echo '{"hook_event_name":"SessionEnd","reason":"logout","session_id":"child456"}' \
 *     | node ./hooks/session-end-kage-bunshin-child-notify.cjs
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
  // SessionEnd hook does not need to inspect event fields — consume stdin and proceed.

  // Only fire in child sessions — master sessions have nothing to notify
  if (process.env.KAGE_BUNSHIN_CHILD !== '1') {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Require both env vars — without them we cannot write to the correct file
  const parentSessionId = process.env.KAGE_BUNSHIN_PARENT_SESSION_ID;
  const tmuxSession = process.env.KAGE_BUNSHIN_TMUX_SESSION;
  if (!parentSessionId || !tmuxSession) {
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
    // Not inside a git repo — nothing to notify
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Derive the project slug: replace all '/' with '-'
  const slug = repoRoot.replace(/\//g, '-');

  // Resolve DH state home (respects DH_STATE_HOME override)
  const dhStateHome = process.env.DH_STATE_HOME || path.join(os.homedir(), '.dh');

  // Resolve the notifications file path scoped to the parent session
  const notificationsDir = path.join(dhStateHome, 'projects', slug, 'kage-bunshin');
  const notificationsPath = path.join(notificationsDir, `notifications-${parentSessionId}.jsonl`);

  // Build the notification entry
  const entry = JSON.stringify({
    event: 'session_end',
    tmux_session: tmuxSession,
    ts: Date.now(),
  });

  // Append to the notifications file — create dir if needed
  try {
    fs.mkdirSync(notificationsDir, { recursive: true });
    fs.appendFileSync(notificationsPath, `${entry}\n`, { encoding: 'utf8' });
  } catch {
    // File write failure is non-fatal — child hooks must not block the session
  }

  process.stdout.write(JSON.stringify({}));
  process.exit(0);
});
