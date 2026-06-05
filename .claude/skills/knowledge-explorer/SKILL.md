---
name: knowledge-explorer
description: Manages the research/ knowledge base of verified tool and library research entries via knowledge-explorer.py. Commands — list (browse by category or SDLC layer), fetch-github (draft entry from GitHub repo), add (validate and route to category dir), update-append (append dated revision), generate-descriptions (repair missing or low-quality descriptions), migrate (convert inline-header entries to frontmatter). Use when browsing KB topics, adding or updating research entries, fetching GitHub repo metadata, generating descriptions in parallel via Haiku subagents, or migrating old-format entries to skill-spec frontmatter.
---

# knowledge-explorer

Manages entries in `research/` — a knowledge base of verified research on tools, libraries, and frameworks. The script is `research/knowledge-explorer.py` (PEP 723, run via `uv run`).

KB root: `research/` relative to repo root. Each entry is a `.md` file inside a category subdirectory (e.g., `research/agent-frameworks/agno.md`).

## Script invocation

```bash
uv run research/knowledge-explorer.py [--verbose] <command> [args]
```

`--verbose` / `-v` prints tracebacks on error.

## Commands

### list

Browse all KB entries grouped by category with freshness metadata.

```bash
uv run research/knowledge-explorer.py list [--layer 0|1|2]
```

**Options:**
- `--layer` / `-l`: Filter by SDLC layer (0=process, 1=language, 2=stack). See [plugins/development-harness/docs/sdlc-layers/](../../../plugins/development-harness/docs/sdlc-layers/).

Observed output (2026-02-22, truncated):

```text
research/
+-- agent-frameworks/  (8 entries, 0 overdue)
|   +-- agno.md  v2.4.7  · verified 2026-01-31  · review 2026-05-01
|   +-- bmad-method.md  6.0.0-Beta.4  · verified 2026-02-01  · review 2026-05-01
+-- developer-tools/  (19 entries, 0 overdue)
|   +-- github-cli.md  v2.64.0  · verified 2026-02-20  · review 2026-05-20
```

Each entry shows: filename, version, verified date, next-review date, and `[OVERDUE]` when `next_review < today`. Categories show total entry count and overdue count. Running the script with no subcommand also invokes `list`.

### show-template

Print the skill-spec frontmatter template for new entries.

```bash
uv run research/knowledge-explorer.py show-template
```

Observed output (2026-02-22):

```yaml
---
name: kebab-case-identifier
description: >-
  Verified reference for <topic>. Use when configuring or working with
  <topic> in deployments. Max 1024 chars.
license: MIT
metadata:
  topic: kebab-case-identifier
  category: category-dir-name  # one of: agent-frameworks, agent-infrastructure, ...
  source_url: https://...
  github: owner/repo
  version: "1.0.0"
  verified: "2026-02-22"
  next_review: "2026-05-23"
  tags: "tag1,tag2"
---

# Display Name

[Body content here]
```

Use this template as the starting point for any new entry before passing it to `add`.

**Valid categories** (verified from source lines 59-86):

```text
agent-frameworks, agent-infrastructure, ai-design-tools, ai-observability,
ai-research-tools, ai-writing-tools, api-frameworks, async-libraries,
code-auditing, coding-agents, context-management, data-infrastructure,
developer-tooling, developer-tools, documentation-tools, evaluation-testing,
installer-tools, llm-infrastructure, low-code-platforms, mcp-ecosystem,
ml-infrastructure, python-runtimes, research-agent-patterns, rust-python-bindings,
skill-generation-tools, task-management
```

### fetch-github

Fetch README and docs/ from a GitHub repository via the `gh` CLI and produce a draft KB entry.

```bash
uv run research/knowledge-explorer.py fetch-github <owner/repo> [--output <path>] [--category <cat>]
```

**Requires**: `gh` CLI installed and authenticated (`gh auth login`).

**Options:**
- `--output` / `-o` PATH — write draft to file instead of printing to stdout
- `--category` / `-c` TEXT — override inferred category (must be a valid category name)

Observed example (2026-02-22):

```bash
uv run research/knowledge-explorer.py fetch-github anthropics/claude-code \
  --output /tmp/test-fetch.md
# Output: Draft written to /tmp/test-fetch.md
```

The produced draft (observed):

```yaml
---
name: claude-code
description: Claude Code is an agentic coding tool that lives in your terminal...
metadata:
  topic: claude-code
  category: UNCATEGORIZED
  source_url: https://github.com/anthropics/claude-code
  github: anthropics/claude-code
  version: "v2.1.50"
  verified: "2026-02-22"
  next_review: "2026-05-23"
---

# claude-code

> Claude Code is an agentic coding tool ...

<!-- DRAFT: Review category and tags, then run: ./knowledge-explorer.py add <this-file> -->

[README content follows]
```

**What it fetches** (verified from source lines 361-408):
- Repository metadata via `gh api repos/{slug}`
- Latest release tag via `gh api repos/{slug}/releases/latest` (404 = no releases, silently skipped)
- Root directory listing to detect `docs/` or `doc/` subdirectory
- README content via `gh api repos/{slug}/readme` (base64-decoded)
- If docs dir found: lists files in comment block inside the draft

**Category inference**: Matches GitHub repo topics against `VALID_CATEGORIES`; falls back to `UNCATEGORIZED` when no match. Always review and correct `category` before running `add`.

**Workflow after fetch-github:**

```text
1. Review draft: check category, tags, description
2. Edit body if needed
3. Run: uv run research/knowledge-explorer.py add <draft-file>
```

### add

Route a frontmatter entry file to the correct category directory and update `README.md`.

```bash
uv run research/knowledge-explorer.py add <file>
# or pipe from stdin:
cat entry.md | uv run research/knowledge-explorer.py add
```

**What it does** (verified from source lines 1774-1847):
1. Reads file (or stdin if omitted)
2. Validates format is frontmatter (not inline-header)
3. Parses entry and validates all required fields
4. Auto-generates description from body first paragraph if `description` is empty (warns)
5. Validates topic slug (1-64 chars, lowercase alphanumeric + hyphens, no leading/trailing/consecutive hyphens)
6. Validates category is in `VALID_CATEGORIES`
7. Checks for topic conflicts at target path
8. Writes entry to `research/<category>/<topic>.md`
9. Updates `research/README.md` table (warns if update fails, does not abort)

**Required frontmatter fields**: `name`, `description`, `metadata.topic`, `metadata.category`, `metadata.source_url`, `metadata.verified`, `metadata.next_review`

**Exit codes**: 0 = success, 1 = parse/write error, 2 = validation error (invalid topic slug or category)

<example>

```bash
# Typical add workflow
uv run research/knowledge-explorer.py fetch-github some-org/some-tool \
  --output /tmp/some-tool-draft.md
# Edit /tmp/some-tool-draft.md: set correct category, review description
uv run research/knowledge-explorer.py add /tmp/some-tool-draft.md
```

</example>

### update-append

Append a dated update section to an existing KB entry. Opens `$EDITOR` for the update content.

```bash
uv run research/knowledge-explorer.py update-append <topic-slug>
```

**What it does** (verified from source lines 1719-1766):
1. Searches all KB files for the entry matching the topic slug
2. Migrates entry to frontmatter format in-place if it was inline-header
3. Opens `$EDITOR` with placeholder `<!-- Replace this with your update content -->`
4. If editor closed with unchanged placeholder or empty content: aborts with exit 0
5. Appends a dated section: `## Update: YYYY-MM-DD\n\n<content>`
6. Updates `verified` to today and `next_review` to today + 90 days
7. Writes updated entry atomically

**Editor interaction**: This command requires interactive terminal access. It uses `typer.edit()` which invokes `$EDITOR` (or system default). When running in a non-interactive context (e.g., scripted agent loop), set `EDITOR` to a script that writes content to the temp file programmatically, or use `VISUAL`.

**Topic not found**: If slug is not found, suggests up to 3 alternatives using Levenshtein distance <= 2.

<example>

```bash
uv run research/knowledge-explorer.py update-append agno
# Opens $EDITOR → write update content → save → exits
# Result: ## Update: 2026-02-22\n\n<content> appended to agent-frameworks/agno.md
```

</example>

### generate-descriptions

Generate or repair frontmatter `description` fields for KB entries that are missing, empty, truncated, or auto-generated from prose.

**When to run:** User asks to "fix descriptions", "generate descriptions", or "repair KB descriptions", or the `add` command warns about an empty description.

**Orchestrator workflow:**

```bash
# Step 1 — get only the entries that need fixing (JSON array)
uv run research/knowledge-explorer.py list-candidates
```

Output is a JSON array of entries that fail the bad-description heuristics. Empty array means nothing to do. Each object contains `topic`, `file_path`, `name`, `category`, `tags`, `current_description`, `body`.

```bash
# Step 2 — spawn one Haiku subagent per entry in parallel
# Pass each entry object + the description rules below to the agent.
# The agent generates the description and writes it directly:
uv run research/knowledge-explorer.py set-description <topic> "<description>"
# Exit 0 = success (silent). Exit 1 = topic not found. Exit 2 = invalid description.
```

The orchestrator only hears back from an agent on non-zero exit. Generated descriptions never route through the orchestrator.

**`--all` flag:** include every entry regardless of current description quality.

```bash
uv run research/knowledge-explorer.py list-candidates --all
```

**Description rules (pass verbatim to each subagent):**
- Single line, no newlines
- Max 1024 characters
- Front-load what the KB covers, then when an agent should load it
- Include specific trigger keywords (tool name, alternatives, use cases)
- Format: `{what it covers}. Use when {trigger scenarios}.`
- Output ONLY the description string — no quotes, no YAML, no explanation
- After writing, validate with `uvx skilllint@latest check --fix <file>`

<example>

Subagent receives:

```json
{
  "topic": "dasel",
  "name": "dasel",
  "category": "developer-tools",
  "tags": ["cli", "json", "yaml", "toml", "csv", "xml"],
  "body": "Dasel (Data Selection) is a command-line tool and Go library..."
}
```

Subagent generates and writes:

```bash
uv run research/knowledge-explorer.py set-description dasel "Dasel CLI and Go library for reading and writing JSON, YAML, TOML, CSV, and XML via a unified selector syntax. Use when querying or transforming structured config files, scripting data pipelines, or replacing jq/yq with a single multi-format tool."
```

</example>

### migrate

Migrate old-format entries to skill-spec frontmatter in-place across the entire KB.

```bash
uv run research/knowledge-explorer.py migrate [--dry-run]
```

**Options:**
- `--dry-run` — show what would change without writing (safe to run at any time)
- `--all` — migrate all entries (default; no effect to omit)

**Source formats handled** (verified from source lines 1956-2008):
- **inline-header**: `# Heading` + bold/table field pairs before `## Body` — converted to skill-spec frontmatter
- **flat frontmatter**: top-level KB fields (`topic`, `name`, etc.) — moved into `metadata` sub-mapping
- **skill-spec frontmatter**: already has `metadata.topic` — skipped

**Summary output** (from source lines 1998-2007):

```text
Migrated: N  Already done: M  Failed: P
  FAILED relative/path.md: reason
```

Run with `--dry-run` first to preview changes before committing.

## Frontmatter schema

Skill-spec format (canonical, written by all write operations):

```yaml
---
name: kebab-case-tool-name          # top-level: Agent Skills spec name
description: "..."                  # top-level: max 1024 chars
license: MIT                        # top-level: optional SPDX identifier
metadata:                           # KB tracking fields
  topic: kebab-case-tool-name       # kebab-case slug; must match filename stem
  category: developer-tools         # must be in VALID_CATEGORIES
  source_url: https://...           # primary reference URL
  github: owner/repo                # optional: owner/repo slug only
  version: "1.2.3"                  # optional: quoted string
  verified: "2026-02-22"            # ISO date string, quoted
  next_review: "2026-05-23"         # ISO date string, quoted; 90 days after verified
  tags: "tag1,tag2"                 # optional: comma-separated, quoted
---
```

**Key constraints** (verified from source lines 1321-1340, 1467-1503):
- `topic` slug: 1-64 chars, `[a-z0-9][a-z0-9-]*[a-z0-9]` or single char, no `--`
- `description` max: 1024 chars
- `category` must be exact match in `VALID_CATEGORIES`
- Date fields must be quoted strings (not YAML date scalars) — the script handles this via `DoubleQuotedScalarString`

## Error handling

- **`ExternalCommandError`**: `gh` not on PATH or returned non-zero. Hint shown in error panel. Fix: `gh auth login` or install gh CLI.
- **`TopicNotFoundError`**: topic slug not found; up to 3 Levenshtein suggestions shown.
- **`TopicConflictError`**: target path exists with a different topic slug.
- **`ParseError`**: file format unrecognisable or required field missing.
- **`FrontmatterValidationError`**: frontmatter present but fails schema (missing required fields).

All errors render as a Rich panel on stderr. Use `--verbose` to include full traceback.

## Source reference

Script: `research/knowledge-explorer.py` (1911 lines, verified 2026-02-24)

Key line ranges:
- Constants and valid categories: lines 46-88
- `fetch-github` command: lines 1637-1711
- `update-append` command: lines 1719-1766
- `add` command: lines 1774-1847
- `migrate` command: lines 1956-2008
- Frontmatter schema serializer: lines 1261-1300
- Name validation rules: lines 1321-1340
