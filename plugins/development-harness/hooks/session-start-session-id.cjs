#!/usr/bin/env node
'use strict';

/**
 * SessionStart hook — captures session_id from stdin JSON and injects it as
 * CLAUDE_CODE_SESSION_ID into both conversation context and shell environment.
 *
 * Guards:
 *   - Skips if CLAUDE_CODE_SESSION_ID is already set (user-level hook or resume)
 *   - Skips env file write if CLAUDE_ENV_FILE is absent or already contains the var
 *
 * Scope: plugin (development-harness)
 * Fires on: SessionStart (no matcher)
 * Action: non-blocking — injects session ID into context and environment
 *
 * Test:
 *   echo '{"hook_event_name":"SessionStart","session_id":"a4b692e2-9095-43e4-849d-385e9e454782"}' | node ./hooks/session-start-session-id.cjs
 *
 * SOURCE: https://github.com/anthropics/claude-code/issues/20132#issuecomment-3902811178
 */

const fs = require('node:fs');

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  // If already set in environment, do nothing — user-level hook or resumed session
  if (process.env.CLAUDE_CODE_SESSION_ID) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Parse stdin — exit cleanly on failure
  let data = {};
  try {
    data = JSON.parse(input || '{}');
  } catch {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const sessionId = data.session_id;
  if (!sessionId || typeof sessionId !== 'string') {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Inject into shell environment via CLAUDE_ENV_FILE so Bash tool calls can use it.
  // Guard: each session gets its own env file — skip if already written (resume/continue)
  const envFile = process.env.CLAUDE_ENV_FILE;
  if (envFile) {
    try {
      const existing = fs.existsSync(envFile) ? fs.readFileSync(envFile, 'utf8') : '';
      if (!existing.includes('CLAUDE_CODE_SESSION_ID')) {
        fs.appendFileSync(envFile, `export CLAUDE_CODE_SESSION_ID="${sessionId}"\n`);
      }
    } catch {
      // Non-fatal — env injection is best-effort
    }
  }

  // Inject into conversation context so the model can reference it
  const output = {
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: `CLAUDE_CODE_SESSION_ID=${sessionId}`,
    },
  };

  process.stdout.write(JSON.stringify(output));
  process.exit(0);
});
