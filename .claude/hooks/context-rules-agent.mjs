#!/usr/bin/env node
// PostToolUse hook (matcher: Agent) — delegation rules have no file path to glob-match against,
// so this fires on every Agent tool call instead. Never blocks/crashes.

import { readFileSync } from 'node:fs';
import { loadRulesByNames } from '../../rules/context-loader.mjs';

const DELEGATION_RULES = [
  'agent-delegation.md',
  'fix-delegation-discipline.md',
  'model-selection.md',
];

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

  let content = '';
  try {
    content = loadRulesByNames(DELEGATION_RULES, input.session_id);
  } catch (err) {
    process.stderr.write(
      `context-rules-agent: loader threw, no context injected: ${err.message}\n`,
    );
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
