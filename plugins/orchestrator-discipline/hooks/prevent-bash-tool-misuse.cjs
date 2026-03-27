#!/usr/bin/env node
'use strict';

/**
 * PreToolUse hook — prevents Bash commands that should use built-in tools.
 *
 * Fires on every Bash tool call. Checks the command against patterns that
 * indicate the model should have used Read, Grep, or Glob instead.
 *
 * Exits code 2 (block + feedback) on violations.
 * Exits code 0 (pass) for legitimate bash use.
 *
 * SOURCE: kaizen analysis session 2026-03-02 (session e3280e97)
 * 28 violations of built-in tool rules in a single 233-turn session.
 */

const fs = require('node:fs');

/** Reads all of stdin synchronously. */
function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

/**
 * Violation rules: pattern + redirect tool + message.
 * Pipeline-safe: patterns that are part of legitimate pipelines
 * (e.g., git log | grep, uv run ... | head) are excluded.
 */
const VIOLATIONS = [
  {
    // Standalone grep at start of command — not as pipeline step
    pattern: /^\s*grep\b/,
    redirect: 'Grep',
    message:
      'Use the Grep tool instead of Bash grep. Reason: built-in tools handle encoding and permissions correctly.',
    example: 'Grep(pattern="...", path="...")',
  },
  {
    // find at command start (or after && / ;) searching by name or type — not mid-pipeline
    // Matches: find . -name, find /path -name, find $VAR -name, find . -type f
    // Does NOT match: ... | find "$TMP" -name (pipeline use in test scaffolds)
    pattern: /(?:^|&&|;)\s*find\s+[.$/~"']?\S*\s+-(?:name|type)\b/,
    redirect: 'Glob',
    message:
      'Use the Glob tool instead of Bash find. Reason: built-in tools handle gitignore and permissions correctly.',
    example: 'Glob(pattern="**/*.ts")',
  },
  {
    // ls at start of command (not in pipeline, not ls -la for human consumption)
    pattern: /^\s*ls\b(?!\s+-la\s*$)/,
    redirect: 'Glob',
    message:
      'Use the Glob tool instead of Bash ls. Reason: built-in tools handle encoding and permissions correctly.',
    example: 'Glob(pattern="*", path="/some/dir")',
  },
  {
    // cat a file (not cat /dev/stdin, not cat | something)
    pattern: /^\s*cat\s+[^|]+\.\w+\s*$/,
    redirect: 'Read',
    message:
      'Use the Read tool instead of Bash cat. Reason: built-in tools handle encoding, large files, and binary detection.',
    example: 'Read(file_path="/path/to/file")',
  },
  {
    // sed -n 'N,Mp' for reading a range — use Read with offset/limit
    pattern: /^\s*sed\s+-n\s+['"]?\d+,\d+p['"]?/,
    redirect: 'Read',
    message:
      'Use the Read tool with offset and limit instead of sed -n. Reason: Read handles encoding correctly and is more expressive.',
    example: 'Read(file_path="/path/to/file", offset=10, limit=20)',
  },
  {
    // head -N (reading first N lines)
    pattern: /^\s*head\s+-\d+/,
    redirect: 'Read',
    message:
      'Use the Read tool with limit instead of head. Reason: built-in tools handle encoding and large files correctly.',
    example: 'Read(file_path="/path/to/file", limit=20)',
  },
  {
    // tail -N (reading last N lines) — use Read with offset
    pattern: /^\s*tail\s+-\d+\s+\S+\.\w+\s*$/,
    redirect: 'Read',
    message:
      'Use the Read tool with offset instead of tail. Reason: built-in tools handle encoding and large files correctly.',
    example: 'Read(file_path="/path/to/file", offset=-20)',
  },
];

/**
 * Commands that are legitimate Bash uses even if they match the patterns above.
 * These are pipeline contexts where the bash command is necessary.
 */
const LEGITIMATE_PATTERNS = [
  /\|\s*find\b/, // find as a pipeline step — not standalone file discovery
  /git\s.*\|\s*grep/, // git log | grep, git diff | grep
  /\|\s*grep/, // any pipeline ... | grep
  /grep.*\|\s/, // grep as pipeline source with another step
  /uv run.*\|\s*(head|tail)/, // uv run output piped to head/tail
  /gh\s.*\|\s*(grep|head)/, // gh CLI output piped
  /npm\s.*\|\s*(grep|head)/, // npm output piped
  /cat\s+\/dev\/(stdin|null)/, // cat /dev/stdin or /dev/null
  /cat\s+-/, // cat - (stdin)
  /ls\s+-la\s*$/, // ls -la for human-readable directory listing
  /^\s*ls\b.*(\|\||&&|\|)/, // ls combined with &&, ||, or | — blocking the chain prevents legitimate commands after ls
];

function main() {
  const raw = readStdin();
  if (!raw || !raw.trim()) {
    process.exit(0);
  }

  let event;
  try {
    event = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const toolName = event.tool_name ?? '';
  if (toolName !== 'Bash') {
    process.exit(0);
  }

  const cmd = event.tool_input?.command ?? '';
  if (!cmd.trim()) {
    process.exit(0);
  }

  // Check legitimate pipeline patterns first
  for (const legit of LEGITIMATE_PATTERNS) {
    if (legit.test(cmd)) {
      process.exit(0);
    }
  }

  // Check for violations
  for (const v of VIOLATIONS) {
    if (v.pattern.test(cmd)) {
      process.stderr.write(
        `${[
          '--- Bash Tool Misuse Prevented ---',
          '',
          `Command: ${cmd.trim()}`,
          '',
          v.message,
          '',
          `Use instead: ${v.example}`,
          '',
          'Rule source: orchestrator-discipline plugin — Bash Built-In Tool Enforcement',
          '--- End ---',
        ].join('\n')}\n`,
      );
      process.exit(2);
    }
  }

  process.exit(0);
}

main();
