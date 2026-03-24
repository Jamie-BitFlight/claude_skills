'use strict';

// UserPromptSubmit hook — check injection queue and prepend queued message to user prompt
// Uses only Node.js built-in modules. Never throws — if server is down, prompt passes through unmodified.

const { spawnSync } = require('node:child_process');

function main() {
  let originalPrompt = '';

  try {
    const fd0 = require('node:fs').readFileSync('/dev/stdin');
    const input = JSON.parse(fd0.toString('utf8') || '{}');

    const session_id = input.session_id || '';
    originalPrompt = input.prompt || '';

    const port = process.env.DOT_DASH_PORT || '7765';
    const url = `http://127.0.0.1:${port}/internal/inject/${encodeURIComponent(session_id)}`;

    const result = spawnSync('curl', ['-s', url], { timeout: 2000 });

    if (result.status === 0 && result.stdout) {
      const responseText = result.stdout.toString('utf8').trim();
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
    }
  } catch (_err) {
    // Silently ignore all errors — pass through unmodified
  }

  // No injection or error — accept without modification
  process.stdout.write(JSON.stringify({ decision: 'accept' }));
}

main();
