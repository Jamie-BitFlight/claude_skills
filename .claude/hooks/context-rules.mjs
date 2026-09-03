#!/usr/bin/env node
// PostToolUse hook (matcher: Read|Write|Edit) — pipes tool_input.file_path through rules/context-loader.mjs, wraps its output as additionalContext. Never blocks/crashes.

import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

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
  if (!filePath) {
    process.exit(0);
  }

  const loaderPath = join(__dirname, '..', '..', 'rules', 'context-loader.mjs');
  const result = spawnSync('node', [loaderPath, filePath], {
    input: raw,
    encoding: 'utf8',
  });

  const content = result.stdout ? result.stdout.trim() : '';
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
