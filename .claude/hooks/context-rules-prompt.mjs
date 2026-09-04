#!/usr/bin/env node
// UserPromptSubmit hook — heuristic for fact-verification-first.md's trigger
// (a named product/version in the prompt). A regex heuristic is imprecise by
// nature; it complements, not replaces, the always-on manifest entry that
// still guarantees delivery on the first file touch either way. Never
// blocks/crashes.

import { readFileSync } from 'node:fs';
import { loadRulesByNames } from '../../rules/context-loader.mjs';

// Capitalized word(s) followed by a version-like token ("GPT 5", "React 20",
// "Gemini 3 Pro"), or an explicit vX.Y(.Z) / X.Y.Z version string.
const PRODUCT_VERSION_PATTERN =
  /\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*){0,2}\s+v?\d+(\.\d+){0,2}\b|\bv\d+\.\d+(\.\d+)?\b/;

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

  const prompt = input.prompt;
  if (typeof prompt !== 'string' || !PRODUCT_VERSION_PATTERN.test(prompt)) {
    process.exit(0);
  }

  let content = '';
  try {
    content = loadRulesByNames(['fact-verification-first.md'], input.session_id);
  } catch (err) {
    process.stderr.write(
      `context-rules-prompt: loader threw, no context injected: ${err.message}\n`,
    );
  }

  if (!content) {
    process.exit(0);
  }

  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'UserPromptSubmit',
        additionalContext: content,
      },
    }),
  );
}

main();
