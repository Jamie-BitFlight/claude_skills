#!/usr/bin/env node
'use strict';

/**
 * Run a list of commands — continues on failure, shows errors to stderr.
 * Cross-platform (Windows + Linux).
 *
 * Commands from: (1) process.argv (each arg after script path), or
 * (2) stdin JSON with "commands" array (for hook events that pass input).
 *
 * Usage in settings.json:
 *   "command": "node \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/run-commands-try-all.cjs \"uv self update\" \"uv run prek install\""
 *
 * Test:
 *   node .claude/hooks/run-commands-try-all.cjs "echo ok" "exit 1" "echo after"
 */

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');

const isWindows = process.platform === 'win32';
const shell = isWindows ? 'cmd.exe' : 'sh';
const shellArg = isWindows ? '/c' : '-c';

function getCommands() {
  const args = process.argv.slice(2);
  if (args.length > 0) {
    return args;
  }
  try {
    const stdin = fs.readFileSync(0, 'utf8');
    if (!stdin?.trim()) return [];
    const data = JSON.parse(stdin);
    const cmds = data.commands ?? data.command ?? [];
    return Array.isArray(cmds) ? cmds : [String(cmds)];
  } catch {
    return [];
  }
}

function runCommand(cmd, index) {
  const result = spawnSync(shell, [shellArg, cmd], {
    stdio: ['ignore', 'pipe', 'pipe'],
    encoding: 'utf8',
    timeout: 120000,
  });
  const label = `[${index + 1}] ${cmd}`;
  if (result.status !== 0) {
    const err = result.stderr?.trim() || result.stdout?.trim() || `exit code ${result.status}`;
    process.stderr.write(`${label}: FAILED\n${err}\n\n`);
  }
  return result.status;
}

const commands = getCommands();
if (commands.length === 0) {
  process.stderr.write(
    'run-commands-try-all: no commands (pass as argv or stdin {"commands": [...]})\n',
  );
  process.exit(0);
}

for (let i = 0; i < commands.length; i++) {
  runCommand(commands[i], i);
}

process.exit(0);
