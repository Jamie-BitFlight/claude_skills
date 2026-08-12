# DuckDB Lock Fix, --scope Flag, .gitignore, and Consolidation Todo

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the DuckDB write-lock conflict, add `--scope` flag to `sentiment-score.py` for lesson output targeting, create a `.gitignore` for local-scope output, and add a BACKLOG todo for MCP consolidation analysis.

**Architecture:** Three independent changes to the `agentskill-kaizen` plugin: (1) one-line `plugin.json` patch to make the motherduck MCP server read-only, freeing the write lock for the script; (2) a new `--scope` Typer option that routes lesson output to one of three destinations; (3) a `.gitignore` in the plugin root and a BACKLOG todo entry. No new dependencies. No schema changes.

**Tech Stack:** Python 3.11+, Typer, DuckDB, uv/PEP 723, JSON (plugin.json)

---

## Task 1: Fix DuckDB lock — make MCP server read-only

**Files:**
- Modify: `plugins/agentskill-kaizen/.claude-plugin/plugin.json` line 32

**Context:**
`mcp-server-motherduck` is launched with `--read-write`, which acquires DuckDB's exclusive write lock. When `sentiment-score.py` runs while the MCP server is active, it fails with `IOException: Could not set lock`. DuckDB allows multiple readers but only one writer. Making the MCP server read-only releases the write lock so the script can acquire it.

**Step 1: Apply the one-line patch**

In `plugins/agentskill-kaizen/.claude-plugin/plugin.json`, change:

```json
"args": ["mcp-server-motherduck", "--db-path", "${HOME}/.claude/kaizen/kaizen.duckdb", "--read-write"]
```

to:

```json
"args": ["mcp-server-motherduck", "--db-path", "${HOME}/.claude/kaizen/kaizen.duckdb", "--read-only"]
```

**Step 2: Verify the JSON is still valid**

```bash
python3 -c "import json, sys; json.load(open('plugins/agentskill-kaizen/.claude-plugin/plugin.json')); print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add plugins/agentskill-kaizen/.claude-plugin/plugin.json
```

Then `/commit-staged`

---

## Task 2: Add `--scope` flag to `sentiment-score.py`

**Files:**
- Modify: `plugins/agentskill-kaizen/scripts/sentiment-score.py`

**Context:**
The `--scope` flag controls where lesson output (future feature) is written. Three destinations:

| Scope | Destination |
|-------|-------------|
| `user` | `~/.claude/kaizen/lessons/` |
| `project` | `{cwd}/.claude/kaizen/lessons.md` (git-tracked) |
| `local` | `{cwd}/.claude/kaizen/lessons.local.md` (gitignored) |

For now, the flag is plumbing only — it validates, resolves, and prints the resolved destination path to stderr. The actual lesson extraction logic is a separate future task. Adding the flag now means callers can pass `--scope` today and it will be wired up when lesson extraction lands.

**Step 1: Add `ScopeTarget` enum after the `_DEFAULT_DB` constant (around line 392)**

```python
import enum  # add to stdlib imports at top of file


class ScopeTarget(str, enum.Enum):
    """Output scope for lesson files."""

    user = "user"
    project = "project"
    local = "local"
```

Note: `str, enum.Enum` is required for Typer to accept enum values as CLI arguments.

**Step 2: Add `_resolve_scope_path` helper after `ScopeTarget`**

```python
def _resolve_scope_path(scope: ScopeTarget) -> Path:
    """Return the resolved output path for *scope*.

    Args:
        scope: The target scope for lesson output.

    Returns:
        Absolute path to the lesson file or directory.
    """
    if scope == ScopeTarget.user:
        return Path("~/.claude/kaizen/lessons/").expanduser()
    if scope == ScopeTarget.project:
        return Path.cwd() / ".claude" / "kaizen" / "lessons.md"
    # local
    return Path.cwd() / ".claude" / "kaizen" / "lessons.local.md"
```

**Step 3: Add `scope` parameter to the `score()` CLI function**

In the `score()` function signature, add after the `db` parameter:

```python
scope: Annotated[
    ScopeTarget | None,
    typer.Option(
        "--scope",
        help=(
            "Lesson output scope: 'user' → ~/.claude/kaizen/lessons/, "
            "'project' → {cwd}/.claude/kaizen/lessons.md (git-tracked), "
            "'local' → {cwd}/.claude/kaizen/lessons.local.md (gitignored)."
        ),
        rich_help_panel="Output Options",
    ),
] = (None,)
```

**Step 4: Add scope path resolution and reporting in the `score()` function body**

After the `_write_duckdb` call (around line 617), add:

```python
if scope is not None:
    scope_path = _resolve_scope_path(scope)
    stderr.print(f"[dim]Lesson scope:[/dim] [cyan]{scope.value}[/cyan] → {scope_path}")
```

**Step 5: Verify the CLI help renders correctly**

```bash
uv run --script plugins/agentskill-kaizen/scripts/sentiment-score.py score --help
```

Expected: `--scope` appears under "Output Options" with the three scope descriptions.

**Step 6: Verify the flag is accepted without error**

```bash
uv run --script plugins/agentskill-kaizen/scripts/sentiment-score.py score --scope local --help
```

Expected: exits 0, no error about unknown option.

**Step 7: Commit**

```bash
git add plugins/agentskill-kaizen/scripts/sentiment-score.py
```

Then `/commit-staged`

---

## Task 3: Add `.gitignore` for local scope output

**Files:**
- Create: `plugins/agentskill-kaizen/.gitignore`

**Context:**
The `local` scope writes `{cwd}/.claude/kaizen/lessons.local.md` — a per-project file that should never be committed. A `.gitignore` in the plugin root handles this for the plugin's own working directory.

**Step 1: Create the `.gitignore`**

Create `plugins/agentskill-kaizen/.gitignore` with content:

```gitignore
# Local-scope lesson output (gitignored by design — use --scope project for tracked lessons)
.claude/kaizen/lessons.local.md
```

**Step 2: Verify git sees it as ignored**

```bash
touch plugins/agentskill-kaizen/.claude/kaizen/lessons.local.md 2>/dev/null || true
git check-ignore -v plugins/agentskill-kaizen/.claude/kaizen/lessons.local.md
```

Expected: output references `.gitignore` and the file pattern.

**Step 3: Clean up the test file**

```bash
rm -f plugins/agentskill-kaizen/.claude/kaizen/lessons.local.md
```

**Step 4: Commit**

```bash
git add plugins/agentskill-kaizen/.gitignore
```

Then `/commit-staged`

---

## Task 4: Add BACKLOG todo for MCP consolidation analysis

**NOTE**: This plan was written when BACKLOG.md was the single-file backlog. The architecture has since changed: GitHub Issues are the source of truth, and `.claude/backlog/` per-item files are the local cache. Use `uv run .claude/skills/backlog/scripts/backlog.py add` instead of editing files directly.

**Context:**
The plugin runs two MCP servers: `kaizen-duckdb` (motherduck, SQL queries) and `kaizen-analysis` (custom server.py, process-mining tools + dashboard). The question is whether `sentiment-score.py` as a standalone script should instead be an MCP tool in `server.py`, and whether the two servers can be consolidated. This needs investigation before any architectural change.

**Step 1: Add a P2 backlog item via the backlog script**

```bash
uv run .claude/skills/backlog/scripts/backlog.py add --priority p2 --title "kaizen: MCP consolidation analysis" --description "The plugin currently runs two MCP servers..." -R Jamie-BitFlight/claude_skills
```

**Step 2: Commit**

```bash
git add .claude/backlog/
```

Then `/commit-staged`

---

## Done

After all four tasks, verify:

```bash
# MCP config is valid JSON
python3 -c "import json; json.load(open('plugins/agentskill-kaizen/.claude-plugin/plugin.json')); print('plugin.json OK')"

# Script help shows --scope
uv run --script plugins/agentskill-kaizen/scripts/sentiment-score.py score --help | grep scope

# .gitignore exists
cat plugins/agentskill-kaizen/.gitignore

# Backlog has the new entry
uv run .claude/skills/backlog/scripts/backlog.py list | grep "MCP consolidation"
```
