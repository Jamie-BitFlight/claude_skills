#!/usr/bin/env node
// PostToolUse hook (matcher: Read|Write|Edit) — calls rules/context-loader.mjs's
// loadRulesFor() in-process and wraps its output as additionalContext. Never blocks/crashes.

import { readFileSync } from 'node:fs';
import { loadRulesFor } from '../../rules/context-loader.mjs';

function readStdin() {
  try {
    return readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function main() {
  const raw = readStdin();
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const filePath = input.tool_input?.file_path;
  if (typeof filePath !== 'string' || !filePath) {
    process.exit(0);
  }

  let content = '';
  try {
    content = loadRulesFor(input, filePath);
  } catch (err) {
    process.stderr.write(`context-rules: loader threw, no context injected: ${err.message}\n`);
  }

  if (!content) {
    process.exit(0);
  }

  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PostToolUse',
        additionalContext: content,
      },
    }),
  );
}

main();
