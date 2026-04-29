#!/usr/bin/env node
/**
 * PreToolUse hook: warns when the orchestrator runs diagnostic commands directly.
 *
 * Diagnostic commands (ty, ruff, pytest, pylint, etc.) produce large outputs
 * that consume orchestrator context. The orchestrator should delegate these to an
 * agent and receive a summary instead.
 *
 * Fires on: Bash tool calls matching diagnostic command patterns
 * Action: injects additionalContext reminder (non-blocking)
 *
 * Non-blocking by design — the exception for post-edit verification of a specific
 * file is documented in the warning text, so the orchestrator can make the call.
 */

/**
 * Diagnostic command patterns that produce large output unsuitable for
 * direct consumption in the orchestrator's context window.
 */
const DIAGNOSTIC_PATTERNS = [
  /\bty\s+check\b/,
  /\bruff\s+check\b/,

  /\bpyright\b/,
  /\bbasedpyright\b/,
  /\bpylint\b/,
  /\bpytest\b/,
  /\bpre-commit\s+run\b/,
  /\bprek\s+run\b/,
  /\beslint\b/,
  /\btsc\b.*--noEmit/,
  /\bcargo\s+check\b/,
  /\bcargo\s+clippy\b/,
  /\bgo\s+vet\b/,
];

/**
 * Detect whether a command starts with a known shell wrapper (sh, bash, zsh,
 * etc.), optionally preceded by `env VAR=val ...` or a path prefix.
 *
 * @param {string} str
 * @returns {boolean}
 */
function isKnownShellInvocation(str) {
  return /^\s*(?:env\s+(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*)?(?:\S+\/)?(?:bash|sh|zsh|ksh|dash|fish|ash)\b/.test(
    str,
  );
}

/**
 * Prepare a shell command string for diagnostic pattern matching.
 *
 * For known shell-wrapper invocations (e.g. `bash -c "ruff check src"`,
 * `bash -lc "ruff check src"`), unquote `-c`/`-lc`/`-ic`/etc. payloads so
 * the inner command is still scanned. For non-shell tools (e.g.
 * `grep -c 'ruff check'`), do NOT preserve the `-c` payload — quoted args
 * are descriptive and should be stripped to avoid false positives.
 *
 * Strips all other quoted strings to prevent false positives from
 * string arguments (e.g. `spawn --name x 'run ruff check on foo'`).
 *
 * @param {string} str
 * @returns {string}
 */
function stripQuotedStrings(str) {
  let normalized = str;

  if (isKnownShellInvocation(str)) {
    // Preserve -c payloads only for known shell wrappers, including combined
    // flags like -lc (login + command), -ic (interactive + command), -eoc,
    // etc. Match any `-` followed by zero or more alphabetic characters
    // ending in `c`.
    normalized = normalized
      .replace(/-[a-zA-Z]*c\s+'([^']*)'/g, '-c $1')
      .replace(/-[a-zA-Z]*c\s+"([^"]*)"/g, '-c $1');
  }

  return normalized.replace(/'[^']*'/g, ' ').replace(/"[^"]*"/g, ' ');
}

/**
 * @param {string} command
 * @returns {string|null} matched pattern description, or null if no match
 */
function matchesDiagnosticCommand(command) {
  if (!command) return null;
  const stripped = stripQuotedStrings(command);
  for (const pattern of DIAGNOSTIC_PATTERNS) {
    const match = stripped.match(pattern);
    if (match) return match[0];
  }
  return null;
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  let data = {};
  try {
    data = JSON.parse(input);
  } catch {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Skip warning for subagent sessions — subagents SHOULD run diagnostics.
  // When running inside a subagent, the hook input includes agent_id and agent_type
  // fields that are absent in the orchestrator session. Verified 2026-03-23.
  if (data.agent_id) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const toolName = data.tool_name || '';
  if (toolName !== 'Bash') {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const command = data.tool_input?.command || '';
  const matched = matchesDiagnosticCommand(command);

  if (!matched) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const output = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      additionalContext: `<orchestrator-diagnostic-warning>
CONTEXT WINDOW CHECK: You are about to run a diagnostic command as the orchestrator.

Command matched: "${matched}"
Full command: ${command.substring(0, 200)}

RULE: The orchestrator MUST NOT run diagnostic commands that produce large output
directly into its context. Diagnostic output consumes shared context but the
orchestrator rarely edits based on it — delegate instead.

CORRECT APPROACH:
1. Delegate to an Explore agent or specialist:
   "Run: ${command.substring(0, 100)} and report: total count by category,
   affected file paths, representative example of each category."
2. Receive the summary (low token cost).
3. Delegate fixes to the appropriate specialist agent with file paths.

ANTI-PATTERN: Run diagnostic → read output → "now I understand" →
  read more files → plan to self-implement
CORRECT: Delegate diagnostic → receive summary → delegate fix

EXCEPTION: If you just Edited a specific file and need to verify that file only,
proceed — but scope the check to that single file, not the entire codebase.
</orchestrator-diagnostic-warning>`,
    },
  };

  process.stdout.write(JSON.stringify(output));
  process.exit(0);
});
