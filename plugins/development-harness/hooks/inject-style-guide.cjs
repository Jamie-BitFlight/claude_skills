#!/usr/bin/env node
'use strict';

/**
 * SessionStart + UserPromptSubmit hook — injects the ASD-STE100 / BLUF writing
 * style as additionalContext so it's re-asserted every turn, not just once.
 *
 * Scope: plugin (development-harness)
 * Fires on: SessionStart (no matcher), UserPromptSubmit (no matcher)
 *
 * Test:
 *   echo '{"hook_event_name":"SessionStart"}' | node ./hooks/inject-style-guide.cjs
 *   echo '{"hook_event_name":"UserPromptSubmit","prompt":"hi"}' | node ./hooks/inject-style-guide.cjs
 */

const STYLE_GUIDE = [
  'Write in ASD-STE100 structure: one instruction per sentence, active voice, present tense, no synonyms for the same concept.',
  'Keep procedural sentences to 20 words and descriptive sentences to 25.',
  'Put the bottom line first (BLUF): after each task, state what the user can act on before you give the supporting detail.',
].join(' ');

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  let data = {};
  try {
    data = JSON.parse(input || '{}');
  } catch {
    data = {};
  }

  const hookEventName = data.hook_event_name || 'SessionStart';

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName,
        additionalContext: STYLE_GUIDE,
      },
    }),
  );
  process.exit(0);
});
