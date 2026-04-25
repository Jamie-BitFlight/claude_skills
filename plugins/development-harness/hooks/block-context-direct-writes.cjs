#!/usr/bin/env node
'use strict';

/**
 * PreToolUse[Bash] hook — blocks direct writes to active-task context files.
 *
 * Active-task JSON files must only be written via the sam_active_task MCP tool.
 * Direct writes (echo/printf/cat redirect, Python write_text/open) bypass the
 * MCP layer and break session isolation guarantees.
 *
 * Kaizen analysis found 9 instances of agents doing this via inline scripts.
 *
 * Scope: plugin (development-harness)
 * Fires on: PreToolUse — Bash
 * Action: blocking — exit 2 when command writes to an active-task path
 *
 * Test:
 *   # Should block
 *   echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"echo {} > .claude/context/active-task-foo.json"}}' \
 *     | node ./hooks/block-context-direct-writes.cjs
 *
 *   # Should block
 *   echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"python3 -c \"from pathlib import Path; Path(\".claude/context/active-task-foo.json\").write_text(\"{}\")\""}}'  \
 *     | node ./hooks/block-context-direct-writes.cjs
 *
 *   # Should allow
 *   echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"echo hello > /tmp/test.txt"}}' \
 *     | node ./hooks/block-context-direct-writes.cjs
 *
 *   # Should allow (read, not write)
 *   echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"cat .claude/context/active-task-foo.json"}}' \
 *     | node ./hooks/block-context-direct-writes.cjs
 */

/**
 * Returns true when the command writes directly to an active-task context file.
 *
 * Patterns detected:
 *   1. echo|printf|cat ... > path/active-task-*.json
 *   2. python ... write_text(... active-task
 *   3. python ... open(... active-task ...  w   (write mode)
 *   4. Any redirect (>) to a path containing active-task and ending in .json
 *      under .claude/context/ or .dh/projects/.../context/
 *
 * Conservative by design — only matches constructs that clearly write to the
 * active-task path. Read-only operations (cat without redirect, open('r'),
 * Path.read_text) are not matched.
 *
 * @param {string} command
 * @returns {boolean}
 */
function isBlockedWrite(command) {
  if (typeof command !== 'string' || command.length === 0) return false;

  // Pattern 1: output redirect (>) to an active-task JSON path.
  // Matches: echo/printf/cat ... > ...active-task-*.json
  // Also matches any other command redirecting to that path.
  // Does NOT match >> (append) — conservatively not blocked to reduce FP on
  // structured logging, but active-task files should not be appended either;
  // this can be tightened later if needed.
  const redirectToActiveTask = />\s*(?:[^\s>|;]*(?:\/|\\))?.+active-task[^\s]*\.json/;

  // Pattern 2: Python write_text targeting active-task.
  // Agents use: Path('...active-task-foo.json').write_text(...)
  // The path sits inside Path(...) not inside write_text(...), so we match
  // "active-task" appearing before ".write_text(" on the same expression.
  const pythonWriteText = /active-task[^\s'"]*\.json['"]\s*\)\s*\.write_text\s*\(/;

  // Pattern 3: Python open() in write mode targeting active-task.
  // Matches: open('...active-task...', 'w') or open(...active-task..., mode='w')
  // Conservative: requires 'w' write mode to avoid matching reads.
  const pythonOpenWrite =
    /open\s*\([^)]*active-task[^)]*,\s*['"]w['"]|open\s*\([^)]*active-task[^)]*mode\s*=\s*['"]w['"]/;

  // Pattern 4: explicit .claude/context/active-task or /.dh/projects/ context path
  // with a write redirect, as a belt-and-suspenders check on the path structure.
  const dhContextPath =
    />\s*(?:[^\s>|;]*(?:\.claude\/context|\.dh\/projects\/[^/]+\/context)\/active-task[^\s]*\.json)/;

  return (
    redirectToActiveTask.test(command) ||
    pythonWriteText.test(command) ||
    pythonOpenWrite.test(command) ||
    dhContextPath.test(command)
  );
}

const BLOCK_REASON =
  'Direct writes to active-task context files are prohibited. ' +
  'Use the sam_active_task MCP tool instead: ' +
  'mcp__plugin_dh_sam__sam_active_task(config={"action": "set", "plan": "P{N}", "task": "T{M}"})';

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  // Parse stdin — exit cleanly on failure (do not block on bad input)
  let data = {};
  try {
    data = JSON.parse(input || '{}');
  } catch {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Only act on Bash tool calls
  const toolName = data.tool_name || '';
  if (toolName !== 'Bash') {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  const command = (data.tool_input && data.tool_input.command) || '';

  if (!isBlockedWrite(command)) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
  }

  // Exit 2: blocking error — stderr is shown to Claude as the error message
  process.stderr.write(BLOCK_REASON + '\n');
  process.exit(2);
});
