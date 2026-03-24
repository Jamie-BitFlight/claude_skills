'use strict';

// SessionEnd hook — deregister Claude Code session from dot-dash server
// Uses only Node.js built-in modules. Never throws — server being down must not break the session.

const { spawnSync } = require('node:child_process');

function main() {
  try {
    const fd0 = require('node:fs').readFileSync('/dev/stdin');
    const input = JSON.parse(fd0.toString('utf8') || '{}');

    const session_id = input.session_id || '';

    const port = process.env.DOT_DASH_PORT || '7765';
    const url = `http://127.0.0.1:${port}/internal/session/deregister`;
    const body = JSON.stringify({ session_id });

    spawnSync(
      'curl',
      ['-s', '-X', 'POST', '-H', 'Content-Type: application/json', '-d', body, url],
      { timeout: 2000 },
    );
  } catch (_err) {
    // Silently ignore all errors — never block Claude Code
  }
}

main();
