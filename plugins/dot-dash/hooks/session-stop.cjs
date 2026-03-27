'use strict';

// SessionEnd hook — deregister Claude Code session from dot-dash server
// Uses only Node.js built-in modules. Never throws — server being down must not break the session.

const http = require('node:http');

function main() {
  try {
    const raw = require('node:fs').readFileSync(0, 'utf8');
    const input = JSON.parse(raw || '{}');

    const session_id = input.session_id || '';

    const port = process.env.DOT_DASH_PORT || '7765';
    const body = JSON.stringify({ session_id });

    const req = http.request(
      {
        hostname: '127.0.0.1',
        port,
        path: '/internal/session/deregister',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
        },
        timeout: 2000,
      },
      (res) => {
        res.resume(); // drain response
      },
    );

    req.on('error', () => {
      // Silently ignore — never block Claude Code
    });
    req.on('timeout', () => {
      req.destroy();
    });

    req.write(body);
    req.end();
  } catch (_err) {
    // Silently ignore all errors — never block Claude Code
  }
}

main();
