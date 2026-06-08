#!/usr/bin/env node
/**
 * update-agent-map.mjs
 *
 * Manages agent metadata in a SQLite store (`./agent-map.sqlite`).
 * Requires Node.js >= 22.5.0 (node:sqlite built-in).
 *
 * Write mode — concurrent-safe, called by many agents simultaneously:
 *   node update-agent-map.mjs --name <id> [--capabilities <string>] [--description <string>]
 *
 * Dump mode — called once after all agents finish:
 *   node update-agent-map.mjs dump --file <path-to.json>
 *
 * Load mode — seeds database from an existing JSON file (existing keys preserved):
 *   node update-agent-map.mjs load --file <path-to.json>
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';

/**
 * Parses named arguments and the first positional subcommand from process.argv.
 *
 * Supports: --key value
 * The first token after `node script.mjs` that does not start with `--` is
 * treated as the subcommand.
 *
 * @param {string[]} argv - The full process.argv array
 * @returns {{ subcommand: string | null, flags: Map<string, string> }}
 */
function parseArgs(argv) {
  const flags = new Map();
  let subcommand = null;
  const tokens = argv.slice(2);

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token.startsWith('--')) {
      const key = token.slice(2);
      const next = tokens[i + 1];
      if (next !== undefined && !next.startsWith('--')) {
        flags.set(key, next);
        i++;
      } else {
        flags.set(key, '');
      }
    } else if (subcommand === null) {
      subcommand = token;
    }
  }

  return { subcommand, flags };
}

const DB_PATH = resolve(process.cwd(), 'agent-map.sqlite');

/**
 * Opens the SQLite database at `DB_PATH` and ensures the schema exists.
 * WAL mode is enabled for concurrent-safe writes from parallel agents.
 *
 * @returns {DatabaseSync}
 */
function openDb() {
  const db = new DatabaseSync(DB_PATH);
  db.exec(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS agents (
      name TEXT PRIMARY KEY,
      capabilities TEXT,
      description TEXT
    )
  `);
  return db;
}

/**
 * Write mode: reads the existing entry for `name` (if any), merges the
 * provided fields, and writes the result back.
 *
 * Only fields whose flags were explicitly present on the command line are
 * overwritten; absent flags leave the stored value untouched.
 *
 * @param {{ subcommand: string | null, flags: Map<string, string> }} parsed
 */
function runWrite(parsed) {
  const { flags } = parsed;
  const name = flags.get('name');

  if (!name || name.trim() === '') {
    process.stderr.write('Error: --name is required\n');
    process.exit(1);
  }

  const db = openDb();

  try {
    const existing = db
      .prepare('SELECT capabilities, description FROM agents WHERE name = ?')
      .get(name) ?? { capabilities: null, description: null };

    const merged = {
      capabilities: flags.has('capabilities')
        ? (flags.get('capabilities') ?? null)
        : existing.capabilities,
      description: flags.has('description')
        ? (flags.get('description') ?? null)
        : existing.description,
    };

    db.prepare(
      'INSERT OR REPLACE INTO agents (name, capabilities, description) VALUES (?, ?, ?)',
    ).run(name, merged.capabilities, merged.description);

    process.stdout.write(`Updated agent-map.sqlite: added/updated entry "${name}"\n`);
  } finally {
    db.close();
  }
}

/**
 * Dump mode: reads all entries from SQLite, merges them with the existing
 * JSON file at `--file` (SQLite wins per top-level key), and writes the
 * result back with 2-space indentation and a trailing newline.
 *
 * @param {{ subcommand: string | null, flags: Map<string, string> }} parsed
 */
function runDump(parsed) {
  const { flags } = parsed;
  const filePath = flags.get('file');

  if (!filePath || filePath.trim() === '') {
    process.stderr.write('Error: --file is required for dump mode\n');
    process.exit(1);
  }

  const resolvedPath = resolve(process.cwd(), filePath);

  /** @type {Record<string, unknown>} */
  let existingJson = {};

  try {
    const raw = readFileSync(resolvedPath, 'utf8');
    try {
      existingJson = JSON.parse(raw);
    } catch {
      process.stderr.write(`Error: ${resolvedPath} contains invalid JSON\n`);
      process.exit(1);
    }
  } catch (err) {
    if (err.code !== 'ENOENT') {
      process.stderr.write(`Error: could not read ${resolvedPath}: ${err.message}\n`);
      process.exit(1);
    }
    // File absent — start with empty object
  }

  const db = openDb();

  /** @type {Record<string, { capabilities: string | null, description: string | null }>} */
  const dbEntries = {};

  try {
    const rows = db.prepare('SELECT name, capabilities, description FROM agents').all();
    for (const row of rows) {
      dbEntries[row.name] = { capabilities: row.capabilities, description: row.description };
    }
  } finally {
    db.close();
  }

  // Merge: JSON keys not in SQLite are preserved; SQLite wins on overlap
  const merged = { ...existingJson, ...dbEntries };
  const entryCount = Object.keys(dbEntries).length;

  writeFileSync(resolvedPath, `${JSON.stringify(merged, null, 2)}\n`, 'utf8');
  process.stdout.write(`Dumped agent-map.sqlite to ${resolvedPath} (${entryCount} entries)\n`);
}

/**
 * Load mode: reads a JSON file at `--file`, iterates its top-level keys, and
 * writes each key to SQLite only if it does not already exist (SQLite wins).
 *
 * Prints a summary of how many keys were written vs skipped.
 *
 * @param {{ subcommand: string | null, flags: Map<string, string> }} parsed
 */
function runLoad(parsed) {
  const { flags } = parsed;
  const filePath = flags.get('file');

  if (!filePath || filePath.trim() === '') {
    process.stderr.write('Error: --file is required for load mode\n');
    process.exit(1);
  }

  const resolvedPath = resolve(process.cwd(), filePath);

  /** @type {Record<string, unknown>} */
  let sourceJson;

  try {
    const raw = readFileSync(resolvedPath, 'utf8');
    try {
      sourceJson = JSON.parse(raw);
    } catch {
      process.stderr.write(`Error: ${resolvedPath} contains invalid JSON\n`);
      process.exit(1);
    }
  } catch (err) {
    process.stderr.write(`Error: could not read ${resolvedPath}: ${err.message}\n`);
    process.exit(1);
  }

  const db = openDb();
  let written = 0;
  let skipped = 0;

  try {
    const stmt = db.prepare(
      'INSERT OR IGNORE INTO agents (name, capabilities, description) VALUES (?, ?, ?)',
    );
    for (const [key, value] of Object.entries(sourceJson)) {
      const result = stmt.run(key, value.capabilities ?? null, value.description ?? null);
      if (result.changes > 0) {
        written++;
      } else {
        skipped++;
      }
    }
  } finally {
    db.close();
  }

  process.stdout.write(
    `Loaded agent-map.sqlite from ${resolvedPath}: ${written} written, ${skipped} skipped\n`,
  );
}

// ── Entry point ────────────────────────────────────────────────────────────────

const parsed = parseArgs(process.argv);

if (parsed.subcommand === 'dump') {
  runDump(parsed);
} else if (parsed.subcommand === 'load') {
  runLoad(parsed);
} else {
  runWrite(parsed);
}
