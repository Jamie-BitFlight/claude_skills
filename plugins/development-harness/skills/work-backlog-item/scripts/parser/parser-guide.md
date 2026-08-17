# Work-backlog invocation parser

Guide to **`parse.mjs`** in this directory: how it turns skill arguments into machine-readable JSON, and how to extend routes, flags, item-ref token shapes, and schemas.

Co-located files: **`parse.mjs`**, **`command-routes.json`**, **`command-routes.schema.json`**, **`parse.schema.json`**, and this guide.

## Why this exists

Claude (or any agent) receives `<invocation_args/>` as unstructured text. The parser normalizes that string into a single JSON object on stdout: `mode`, `route`, optional `reference`, `flags`, `item_ref`, and `user_text`. Agents MUST treat that object as the source of truth for which workflow file to load and what parameters apply.

## Files

| File | Role |
|------|------|
| `parse.mjs` | Executable parser (Node ESM). Reads argv, emits one line of `JSON.stringify(output)`. |
| `command-routes.json` | Registry: subcommand token → skill-relative path to the primary reference doc for that route. |
| `command-routes.schema.json` | JSON Schema for `command-routes.json` (validation / editor hints). |
| `parse.schema.json` | JSON Schema for the parser’s stdout payload. |

Paths in `command-routes.json` are relative to the **skill root** (parent of `scripts/`), not relative to this directory.

## Invocation: argv shape

Manual terminal use (you author both quotes and content) — a single quoted argument, so `#` isn't a comment:

```bash
node plugins/development-harness/skills/work-backlog-item/scripts/parser/parse.mjs "groom #50 --auto extra words"
```

Don't build this shape from unauthored, caller-supplied text — pipe via stdin instead; `parse.mjs` reads stdin when argv is empty and it isn't a TTY.

When `process.argv.slice(2).length === 1`, the script **re-splits** that string on whitespace using a regex that preserves quoted segments (`"..."`, `'...'`). This is a deliberate tradeoff: good enough for agent-provided strings; it is not a full POSIX shell lexer.

## Pipeline (order matters)

The implementation follows these phases in order.

### 1. Load registry

`command-routes.json` is read from the **same directory as `parse.mjs`**. The object under `.commands` becomes `commands`; its keys are **exact** argv tokens that count as subcommands (`registryKeys`).

### 2. Freetext delimiter

The first token equal to `--`, `—` (em dash), or `–` (en dash) **splits** the argv into:

- **prefix** — parsed for flags and positionals.
- **suffix** — joined with spaces into freetext (used for `user_text` when a delimiter is present).

**Important:** `--auto`, `--language`, etc. are **not** delimiters. Only the bare delimiter tokens above split prefix/suffix.

### 3. Script-only help

`--help` / `-h` in the prefix causes **exit 0** with no JSON (script convenience). They are stripped before flag/positional parsing.

### 4. Prefix scan → `flags` and `positionals`

Known flags consume the next token or set booleans:

| Token | Effect |
|-------|--------|
| `--language` | Next token → `flags.language` (required value). |
| `--stack` | Next token → `flags.stack` (required value). |
| `--force` | `flags.force = true` |
| `--auto` | `flags.auto = true` |
| `--quick` | `flags.quick = true` |

Any other prefix token is a **positional** (preserves order).

### 5. Discriminators

Only **positionals** are scanned. Two kinds of discriminator are detected:

1. **Registry** — token equals a key in `command-routes.json` → `{ type: 'registry', value, index }`.
2. **Item ref** — token matches `issueRegex` → `{ type: 'item_ref', value, index, parsed }`.

`issueRegex` (current):

```text
^(?:#\d+|\d+|https://github.com/[^/]+/[^/]+/issues/\d+(?:\?.*)?)$
```

`parsed` for item-ref tokens is built by `parseIssue()`: **`#N`** for `#N` or bare digits (leading zeros normalized, e.g. `007` → `"#7"`); **full URL string** unchanged when the token is a GitHub issue URL.

If a token matches `issueRegex` but `parseIssue` returns null (should not happen with the current regex), behavior is undefined; keep regex and `parseIssue` in sync when extending.

### 6. Route resolution

| Discriminators | Result |
|----------------|--------|
| None, no positionals, no flags, no suffix | `route: "none"` (no routing target — follow skill Step 1.1 / interactive browser) |
| None, but flags and/or empty title context | `route: "title_substring"`, `user_text` from suffix or null |
| None, with positionals | `route: "title_substring"`, `user_text` = all positionals joined (or suffix if delimiter) |
| One registry | `route` = token, `reference` = `commands[token]`, `user_text` = other positionals and/or suffix |
| One item ref | `route: "issue"`, `item_ref` set, `user_text` = other positionals and/or suffix |
| Exactly one registry + one item ref | `route` = registry token, `reference` set, `item_ref` set, `user_text` = remaining positionals and/or suffix (e.g. `groom #50 --auto tail` → groom + `#50` + flags + user_text for tail) |
| Any other multi-discriminator mix | **Error** to stderr, exit non-zero (e.g. two registry tokens, two item-ref tokens, three+ discriminators) |

Empty `user_text` after trim is emitted as omitted (null conceptually — key not present).

### 7. Mode

`mode` is always emitted: **`auto`** if `--auto` appeared in the prefix, else **`interactive`**. It is independent of `route` (e.g. `groom #50 --auto` yields `mode: "auto"` and `route: "groom"`).

### 8. Stdout

One line: `JSON.stringify(output)` with no pretty-printing. Agents parse that line as JSON.

## Output fields (`parse.schema.json`)

| Property | When present |
|----------|----------------|
| `mode` | Always: `auto` if `--auto` was passed, else `interactive`. |
| `route` | Always (string). `none` = empty invocation; see route-resolution table. |
| `reference` | When `route` is a registry key; value is the string from `command-routes.json`. |
| `flags` | Only flags that appeared; object shape is fixed in schema. |
| `item_ref` | When an item-ref discriminator contributed: backlog-style `#N`, or a GitHub issue URL string. |
| `user_text` | Non-empty remaining freetext (positionals after removing discriminators, or whole suffix after delimiter). |

## How to extend

### A. New subcommand (registry route)

1. Add a line to `command-routes.json` under `commands`:

   `"my-command": "references/path/to/doc.md"`

2. Keep the key **exactly** what users/agents will type as one argv token (no spaces; case-sensitive).

3. Optionally run or wire JSON Schema validation against `command-routes.schema.json` in CI or locally.

4. No change to `parse.schema.json` is required for `route` itself (it is an open string), but you MAY document new route names in the `route` property `description` for human editors.

The parser automatically:

- Recognizes the new token as a registry discriminator.
- Pairs it with a single item-ref token (`my-command #12`) without requiring a freetext delimiter.

### B. New CLI flag

1. Edit `parse.mjs` in the prefix loop (same section as `--language`). For a boolean, mirror `--force`; for a value flag, mirror `--language` / `--stack` (validate next token exists and does not start with `-`).

2. Edit `parse.schema.json` → `properties.flags.properties` and keep `additionalProperties: false` so typos are visible at validation time.

3. Document the flag in the skill’s `SKILL.md` (parent directory) Arguments section if end users or agents should rely on it.

### C. New issue URL pattern or token shape

1. Update `issueRegex` so matching tokens are unambiguous with registry keys and titles.

2. Update `parseIssue()` so every match path returns a non-null string: `#N` for numeric forms, or the canonical URL form you want on the wire.

3. Keep `parse.schema.json` → `item_ref` as `type: "string"` unless you intentionally change the wire format.

### D. New output field

1. Set the field on `output` in the script where semantically appropriate (single exit path before `console.log`).

2. Add the property to `parse.schema.json` with correct `required` semantics (prefer optional keys omitted when null).

3. Document the field in this guide and in `SKILL.md` preflight text if agents must use it.

### E. Stricter registry schema

`command-routes.schema.json` allows any property name under `commands` with string values (`additionalProperties: { "type": "string" }`). To restrict to known filenames, you could replace that with `enum` of allowed paths; that requires updating the schema whenever `command-routes.json` grows.

## Verification

After changes, run representative invocations (from repo root):

```bash
node plugins/development-harness/skills/work-backlog-item/scripts/parser/parse.mjs ""
node plugins/development-harness/skills/work-backlog-item/scripts/parser/parse.mjs "#42"
node plugins/development-harness/skills/work-backlog-item/scripts/parser/parse.mjs "groom #50 --auto tail words"
node plugins/development-harness/skills/work-backlog-item/scripts/parser/parse.mjs "close #1 -- reason here"
```

Or from the skill directory:

```bash
node scripts/parser/parse.mjs ""
```

Confirm valid JSON on stdout, expected `mode` / `route` / `reference` / `item_ref` / `user_text`, and stderr + non-zero exit on intentional error cases.

Optionally validate stdout against `parse.schema.json` with a small `ajv` or `jsonschema` one-liner in CI (not currently wired in this repo).

## Limitations (do not “fix” silently without design review)

- Single-string resplitting is not shell-equivalent for all edge cases.
- Registry keys must not contain spaces; multi-word subcommands are not supported as one token.
- A positional that equals both a registry key and is intended as a **title word** is always treated as registry when it matches `command-routes.json` (rare for real titles).
- Two item-ref-shaped tokens or two registry tokens without a resolving rule still errors.

---

**Primary implementation:** `./parse.mjs`
**Output schema:** `./parse.schema.json`
