#!/usr/bin/env node
// Shared path-based rule loader (Claude Code/Codex/Hermes). CLI usage: echo '<hook stdin>' | node context-loader.mjs <file-path>
// Also exports loadRulesFor()/resetSession() for in-process callers (e.g. .claude/hooks/context-rules.mjs).
// Matches manifest.json globs, prints full content once per session_id then a pointer line; state entries older than 48h are pruned; never throws.
// Reset mode: echo '<hook stdin>' | node context-loader.mjs --reset — clears that session_id's dedup state (wire to SessionStart, matcher compact|clear).

import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const RULES_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(RULES_DIR, '..');
const MANIFEST_PATH = join(RULES_DIR, 'manifest.json');
const STATE_PATH = join(REPO_ROOT, '.tmp', 'context-rules-state.json');
const STATE_TTL_MS = 48 * 60 * 60 * 1000;

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

function pruneExpired(state, now) {
  const pruned = {};
  for (const [sessionId, entry] of Object.entries(state)) {
    // Legacy flat-array entries (pre-lastSeen) have no age to check — drop them
    // rather than guess; they self-heal to the new shape on next real activity.
    if (Array.isArray(entry)) continue;
    if (now - entry.lastSeen <= STATE_TTL_MS) pruned[sessionId] = entry;
  }
  return pruned;
}

function saveState(state) {
  try {
    mkdirSync(dirname(STATE_PATH), { recursive: true });
    // ponytail: atomic rename avoids a torn/corrupted state file, but this is
    // not a cross-process lock — two hook invocations racing on the same
    // session_id can still last-writer-wins clobber each other's newly-added
    // entries. Add flock/proper-lockfile if that starts causing visibly
    // duplicated rule re-injection.
    const tmpPath = `${STATE_PATH}.${process.pid}.tmp`;
    writeFileSync(tmpPath, JSON.stringify(state));
    renameSync(tmpPath, STATE_PATH);
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

export function resetSession(sessionId) {
  if (!sessionId) return;
  const state = pruneExpired(loadState(), Date.now());
  delete state[sessionId];
  saveState(state);
}

// Resolves the repo-relative, forward-slash-normalized, containment-checked
// path for a touched file. Returns null when the file is outside the repo —
// none of this repo's rules should ever apply to it.
function resolveRelPath(touchedPath) {
  const relPath = relative(REPO_ROOT, resolve(touchedPath)).split(sep).join('/');
  if (relPath === '..' || relPath.startsWith('../')) return null;
  return relPath;
}

// Core entrypoint for in-process callers: given the raw PostToolUse hook
// payload and the touched file path, returns the additionalContext string
// ('' when nothing matches or there's nothing left to inject). Never throws.
export function loadRulesFor(hookInput, touchedPath) {
  const sessionId = hookInput?.session_id;

  let manifest;
  try {
    manifest = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'));
  } catch (err) {
    process.stderr.write(`context-loader: manifest read/parse failed: ${err.message}\n`);
    return '';
  }

  const relPath = resolveRelPath(touchedPath);
  if (relPath === null) return '';

  const rules = Array.isArray(manifest.rules) ? manifest.rules : [];
  const matchingRules = rules.filter((rule) => matchesAny(relPath, rule.match));
  if (matchingRules.length === 0) return '';

  const now = Date.now();
  // No session_id means we can't tell callers apart — never dedup against
  // an unidentified caller. Show full content every time and skip state I/O.
  const state = sessionId ? pruneExpired(loadState(), now) : {};
  const loadedForSession = new Set(sessionId ? (state[sessionId]?.files ?? []) : []);
  const output = [];

  for (const rule of matchingRules) {
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

  if (sessionId) {
    state[sessionId] = { files: [...loadedForSession], lastSeen: now };
    saveState(state);
  }

  return output.join('\n\n---\n\n');
}

function main() {
  const arg = process.argv[2];
  const hookInput = readStdinJSON();

  if (arg === '--reset') {
    resetSession(hookInput.session_id);
    process.exit(0);
  }

  const touchedPath = arg;
  if (!touchedPath) {
    process.stderr.write('context-loader: no file path argument given\n');
    process.exit(0);
  }

  const content = loadRulesFor(hookInput, touchedPath);
  if (content) {
    process.stdout.write(`${content}\n`);
  }
}

// Only run as a hook when invoked directly (CLI / --reset), not when imported
// by another module (e.g. .claude/hooks/context-rules.mjs calling loadRulesFor).
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isMain) main();
