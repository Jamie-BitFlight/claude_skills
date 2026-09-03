#!/usr/bin/env node
// Shared path-based rule loader (Claude Code/Codex/Hermes). Usage: echo '<hook stdin>' | node context-loader.mjs <file-path>
// Matches manifest.json globs, prints full content once per session_id then a pointer line; never throws.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const RULES_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(RULES_DIR, '..');
const MANIFEST_PATH = join(RULES_DIR, 'manifest.json');
const STATE_PATH = join(REPO_ROOT, '.tmp', 'context-rules-state.json');

const REGEX_METACHARS = new Set(['.', '+', '?', '^', '$', '{', '}', '(', ')', '|', '[', ']', '\\']);

function globToRegExp(glob) {
  // Supports '**' (any depth), '*' (one segment, no '/'), literal text.
  let pattern = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*' && glob[i + 1] === '*') {
      pattern += '.*';
      i++;
      if (glob[i + 1] === '/') i++;
    } else if (c === '*') {
      pattern += '[^/]*';
    } else if (REGEX_METACHARS.has(c)) {
      pattern += `\\${c}`;
    } else {
      pattern += c;
    }
  }
  return new RegExp(`^${pattern}$`);
}

function matchesAny(relPath, matchField) {
  const base = basename(relPath);
  const patterns = matchField.split(',').map((p) => p.trim());
  // A pattern with no '/' is a bare-filename shorthand ('*.py', 'SKILL.md') —
  // match it against the basename anywhere in the tree, not just top-level.
  // A pattern with '/' matches the full repo-relative path.
  return patterns.some((p) => globToRegExp(p).test(p.includes('/') ? relPath : base));
}

function loadState() {
  try {
    if (!existsSync(STATE_PATH)) return {};
    return JSON.parse(readFileSync(STATE_PATH, 'utf8'));
  } catch (err) {
    process.stderr.write(`context-loader: state read failed, treating as empty: ${err.message}\n`);
    return {};
  }
}

function saveState(state) {
  try {
    mkdirSync(dirname(STATE_PATH), { recursive: true });
    writeFileSync(STATE_PATH, JSON.stringify(state));
  } catch (err) {
    process.stderr.write(`context-loader: state write failed (non-fatal): ${err.message}\n`);
  }
}

function readStdinJSON() {
  try {
    const raw = readFileSync(0, 'utf8');
    if (!raw.trim()) return {};
    return JSON.parse(raw);
  } catch (err) {
    process.stderr.write(
      `context-loader: stdin parse failed, no session dedup this call: ${err.message}\n`,
    );
    return {};
  }
}

function main() {
  const touchedPath = process.argv[2];
  if (!touchedPath) {
    process.stderr.write('context-loader: no file path argument given\n');
    process.exit(0);
  }

  const hookInput = readStdinJSON();
  const sessionId = hookInput.session_id ?? 'no-session-id';

  let manifest;
  try {
    manifest = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'));
  } catch (err) {
    process.stderr.write(`context-loader: manifest read/parse failed: ${err.message}\n`);
    process.exit(0);
  }

  const relPath = relative(REPO_ROOT, resolve(touchedPath));
  const state = loadState();
  const loadedForSession = new Set(state[sessionId] ?? []);
  const output = [];

  for (const rule of manifest.rules ?? []) {
    if (!matchesAny(relPath, rule.match)) continue;

    const ruleFile = join(RULES_DIR, rule.file);
    if (loadedForSession.has(rule.file)) {
      output.push(
        `The conventions for editing this file should be read here: ${relative(REPO_ROOT, ruleFile)}`,
      );
      continue;
    }

    try {
      output.push(readFileSync(ruleFile, 'utf8').trim());
      loadedForSession.add(rule.file);
    } catch (err) {
      process.stderr.write(`context-loader: failed to read ${rule.file}: ${err.message}\n`);
    }
  }

  if (output.length > 0) {
    process.stdout.write(output.join('\n\n---\n\n') + '\n');
  }

  state[sessionId] = [...loadedForSession];
  saveState(state);
}

main();
