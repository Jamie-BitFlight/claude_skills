'use strict';

// UserPromptSubmit hook — check injection queue and prepend queued message to user prompt
// Uses only Node.js built-in modules. Never throws — if server is down, prompt passes through unmodified.

const http = require('node:http');

function main() {
  let originalPrompt = '';

  try {
    const raw = require('node:fs').readFileSync(0, 'utf8');
    const input = JSON.parse(raw || '{}');

    const session_id = input.session_id || '';
    originalPrompt = input.prompt || '';

    const port = process.env.DOT_DASH_PORT || '7765';
    const path = `/internal/inject/${encodeURIComponent(session_id)}`;

    const req = http.get(
      {
        hostname: '127.0.0.1',
        port,
        path,
        timeout: 2000,
      },
      (res) => {
        const chunks = [];
        res.on('data', (chunk) => chunks.push(chunk));
        res.on('end', () => {
          try {
            const responseText = Buffer.concat(chunks).toString('utf8').trim();
            if (responseText) {
              const response = JSON.parse(responseText);
              if (response && typeof response.message === 'string' && response.message.length > 0) {
                const modifiedPrompt = `${response.message}\n${originalPrompt}`;
                process.stdout.write(
                  JSON.stringify({
                    decision: 'accept',
                    hookSpecificOutput: { modifiedUserPrompt: modifiedPrompt },
                  }),
                );
                return;
              }
            }
          } catch {
            // Malformed response — fall through to accept
          }
          // No injection or unparseable — accept without modification
          process.stdout.write(JSON.stringify({ decision: 'accept' }));
        });
      },
    );

    req.on('error', () => {
      // Server down — pass through unmodified
      process.stdout.write(JSON.stringify({ decision: 'accept' }));
    });
    req.on('timeout', () => {
      req.destroy();
      process.stdout.write(JSON.stringify({ decision: 'accept' }));
    });

    return; // output is written asynchronously above
  } catch (_err) {
    // Silently ignore all errors — pass through unmodified
  }

  // Synchronous fallback (e.g. readFileSync or JSON.parse threw)
  process.stdout.write(JSON.stringify({ decision: 'accept' }));
}

main();
