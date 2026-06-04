---
title: "Beads (bd) CLI Command Reference"
date: 2026-05-14
scope: "Complete reference of every bd subcommand, flags, lifecycle, and feature capabilities. Research target: determining how beads can replace GitHub Issues as a backend for the development-harness backlog tool."
sources:
  - /home/user/repos/beads/docs/CLI_REFERENCE.md
  - /home/user/repos/beads/README.md
  - /home/user/repos/beads/AGENT_INSTRUCTIONS.md
  - /home/user/repos/beads/docs/MOLECULES.md
  - /home/user/repos/beads/docs/SYNC_CONCEPTS.md
  - /home/user/repos/beads/docs/ADVANCED.md
---

# Beads (bd) CLI Command Reference

**BLUF**: Beads is a Dolt-powered distributed graph issue tracker with 70+ CLI commands, native JSON output (`--json` on virtually every command), dependency-aware graph execution, a molecule/formula workflow system, multi-assignee/claim semantics, a persistent memory system, and bidirectional sync with GitHub, Linear, Jira, GitLab, ADO, and Notion. It is a strong candidate to replace GitHub Issues as a backlog backend.

---

## Table of Contents

1. [Issue Lifecycle](#1-issue-lifecycle)
2. [Core Issue Commands](#2-core-issue-commands)
3. [Dependency Commands](#3-dependency-commands)
4. [Assignment and Claiming](#4-assignment-and-claiming)
5. [Memory System](#5-memory-system)
6. [Formula and Molecule System](#6-formula-and-molecule-system)
7. [Output Formats and JSON Support](#7-output-formats-and-json-support)
8. [Sync and Federation](#8-sync-and-federation)
9. [Git Hooks and Automation](#9-git-hooks-and-automation)
10. [Views and Reporting](#10-views-and-reporting)
11. [Maintenance and Database Operations](#11-maintenance-and-database-operations)
12. [Integrations](#12-integrations)
13. [Global Flags](#13-global-flags)
14. [Feature Capabilities Summary](#14-feature-capabilities-summary)

---

## 1. Issue Lifecycle

### States

```
open        Available to work (no blockers)
in_progress Currently being worked (claimed)
blocked     Waiting on dependencies (dependency-blocked issues remain "open" stored status;
            use bd blocked to find them — they don't appear in bd ready)
deferred    Deliberately postponed (hidden from bd ready)
closed      Completed
```

Custom statuses can be defined via `bd config set status.custom "in_review:active,qa_testing:wip"`.

Status categories control `bd ready` visibility:
- `active` — appears in `bd ready` and default `bd list`
- `wip` — excluded from `bd ready`, visible in default `bd list`
- `done` — excluded from both
- `frozen` — excluded from both

### Lifecycle State Diagram

```
                   ┌─────────────────────────────────────────────────────┐
                   │                      OPEN                           │
                   │  (created; visible in bd ready if no blockers)      │
                   └──────────┬──────────┬──────────┬───────────────────┘
                              │          │          │
                  claim       │          │ defer    │ dep add (blocker)
                   ↓          │          ↓          ↓
            IN_PROGRESS     block     DEFERRED  [dependency-blocked]
                │             │         │         (still stored as open)
                │ close       │         │ undefer
                ↓             │         ↓
             CLOSED    ←──────┘       OPEN
                │
                │ reopen
                ↓
              OPEN
```

### Issue Types

| Type | Description |
|------|-------------|
| `task` | General work item (default) |
| `bug` | Something broken |
| `feature` | New functionality (aliases: `enhancement`, `feat`) |
| `epic` | Large feature with subtasks |
| `chore` | Maintenance work |
| `decision` | ADR/decision record (aliases: `dec`, `adr`) |
| `event` | System event bead |
| `gate` | Async wait condition (internal) |
| `molecule` | Workflow template instance (internal) |
| `message` | Threading/messaging bead |
| `merge-request` | MR tracking bead |

Custom types: `bd config set types.custom "patrol,convoy"`.

### Priority Levels

| Priority | Meaning |
|----------|---------|
| `0` (P0) | Critical (security, data loss, broken builds) |
| `1` (P1) | High (major features, important bugs) |
| `2` (P2) | Medium (default) |
| `3` (P3) | Low (polish, optimization) |
| `4` (P4) | Backlog (future ideas) |

### Issue ID Format

Hash-based IDs with configurable prefix: `bd-a1b2`, `bd-a3f8`. Hierarchical IDs for epics:
- `bd-a3f8` — Epic
- `bd-a3f8.1` — Task (child of epic)
- `bd-a3f8.1.1` — Sub-task

---

## 2. Core Issue Commands

### `bd create`

Create a new issue.

**Synopsis**: `bd create [title] [flags]`
**Aliases**: `new`

**Key flags**:

```
-t, --type string          Issue type (bug|feature|task|epic|chore|decision) [default: task]
-p, --priority string      Priority (0-4 or P0-P4) [default: 2]
-a, --assignee string      Assignee
-d, --description string   Issue description
    --design string        Design notes
    --acceptance string    Acceptance criteria
    --notes string         Additional notes
    --parent string        Parent issue ID (creates hierarchical child)
-l, --labels strings       Labels (comma-separated)
    --deps strings         Dependencies in format 'type:id' or 'id'
    --body-file string     Read description from file (use - for stdin)
    --stdin                Read description from stdin
    --due string           Due date (+6h, +1d, +2w, tomorrow, next monday, 2025-01-15)
    --defer string         Defer until date
    --external-ref string  External reference (e.g., 'gh-9', 'jira-ABC')
    --silent               Output only the issue ID (for scripting)
    --dry-run              Preview without creating
    --ephemeral            Create as ephemeral (short-lived, subject to TTL compaction)
-e, --estimate int         Time estimate in minutes
    --graph string         Create a graph of issues from JSON plan file
-f, --file string          Create multiple issues from markdown file
    --id string            Explicit issue ID (for partitioning)
    --metadata string      Set custom metadata (JSON or @file.json)
    --skills string        Required skills for this issue
    --spec-id string       Link to specification document
    --waits-for string     Spawner issue ID (creates waits-for dep for fanout gate)
    --validate             Validate description has required sections for type
```

**Examples**:

```bash
bd create "Fix auth bug" -t bug -p 1 --json
bd create "Add OAuth" -t feature -p 2 --description "Implement OAuth2 flow"
bd create "Task" --deps discovered-from:bd-123 --json
echo 'Description with `backticks`' | bd create "Title" --stdin
bd create "Batch" --file issues.md
bd create "Epic" -t epic && bd create "Task" --parent bd-abc123
```

### `bd show`

Show issue details.

**Synopsis**: `bd show [id...] [--id=<id>...] [--current] [flags]`
**Aliases**: `view`

**Key flags**:

```
    --as-of string    Show issue as it existed at a specific commit hash or branch
    --children        Show only the children of this issue
    --current         Show the currently active issue
    --long            Show all available fields (extended metadata, agent identity, gate fields)
    --refs            Show issues that reference this issue (reverse lookup)
    --short           Show compact one-line output per issue
    --thread          Show full conversation thread (for messages)
    --local-time      Show timestamps in local time
-w, --watch           Watch for changes and auto-refresh display
```

**Examples**:

```bash
bd show bd-123 --json
bd show bd-123 bd-456 --json
bd show bd-123 --long
bd show bd-123 --as-of HEAD~5
bd show --current
bd show bd-123 --json | jq '.[0] | {id,title,metadata}'
```

### `bd update`

Update one or more issues.

**Synopsis**: `bd update [id...] [flags]`

**Key flags**:

```
    --title string             New title
-d, --description string       Issue description (use --body-file for file)
    --design string            Design notes
    --acceptance string        Acceptance criteria
    --notes string             Notes (replaces; use --append-notes to append)
    --append-notes string      Append to existing notes
-p, --priority string          Priority (0-4 or P0-P4)
-s, --status string            New status
-a, --assignee string          Assignee (use "" to unassign)
    --claim                    Atomically claim (sets assignee=you, status=in_progress; idempotent)
    --add-label strings        Add labels (repeatable)
    --remove-label strings     Remove labels (repeatable)
    --set-labels strings       Set labels, replacing all existing
    --due string               Due date (empty to clear)
    --defer string             Defer until date (empty to clear)
    --parent string            New parent issue ID (reparents; use "" to remove parent)
    --metadata string          Set custom metadata (JSON or @file.json)
    --set-metadata stringArray Set metadata key=value (repeatable)
    --unset-metadata stringArray Remove metadata key
    --external-ref string      External reference
    --spec-id string           Link to specification document
    --ephemeral                Mark as ephemeral
    --persistent               Mark as persistent (promote wisp)
    --body-file string         Read description from file (use - for stdin)
    --stdin                    Read description from stdin
-t, --type string              New type
-e, --estimate int             Time estimate in minutes
    --session string           Claude Code session ID for status=closed
```

**Examples**:

```bash
bd update bd-123 --claim --json
bd update bd-123 --priority 0 --status in_progress
bd update bd-123 --assignee alice
bd update bd-123 --assignee ""  # unassign
bd update bd-123 --add-label urgent --remove-label draft
echo "new description" | bd update bd-123 --description=-
```

### `bd close`

Close one or more issues.

**Synopsis**: `bd close [id...] [flags]`
**Aliases**: `done`

**Key flags**:

```
-r, --reason string        Reason for closing
    --reason-file string   Read close reason from file (use - for stdin)
-f, --force                Force close pinned issues or unsatisfied gates
    --claim-next           Automatically claim next highest priority available issue
    --continue             Auto-advance to next step in molecule
    --no-auto              With --continue, show next step but don't claim it
    --suggest-next         Show newly unblocked issues after closing
    --session string       Claude Code session ID
```

**Examples**:

```bash
bd close bd-123 --reason "Completed" --json
bd close bd-123 --claim-next   # close and pick up next work
bd close                       # closes last touched issue
```

### `bd list`

List issues.

**Synopsis**: `bd list [flags]`

**Key flags** (extensive):

```
    --all                   Show all issues including closed
-a, --assignee string       Filter by assignee
-l, --label strings         Filter by labels (AND: must have ALL)
    --label-any strings     Filter by labels (OR: must have AT LEAST ONE)
    --label-pattern string  Filter by label glob (e.g., 'tech-*')
    --label-regex string    Filter by label regex
-n, --limit int             Limit results (default 50; 0 for unlimited)
    --no-pager              Disable pager output
    --parent string         Filter by parent issue ID (shows children)
    --no-parent             Show only top-level issues
-p, --priority string       Priority (0-4 or P0-P4)
    --priority-min string   Minimum priority (inclusive)
    --priority-max string   Maximum priority (inclusive)
-r, --reverse               Reverse sort order
    --ready                 Show only ready issues (same semantics as bd ready)
    --sort string           Sort by: priority, created, updated, closed, status, id, title, type, assignee
-s, --status string         Filter by status (open, in_progress, blocked, deferred, closed). Comma-separated
-t, --type string           Filter by type
    --title string          Filter by title text (case-insensitive substring)
    --desc-contains string  Filter by description substring
    --notes-contains string Filter by notes substring
    --created-after string  Filter by creation date
    --created-before string Filter by creation date
    --updated-after string  Filter by update date
    --updated-before string Filter by update date
    --due-after string      Filter by due date
    --due-before string     Filter by due date
    --overdue               Show only overdue issues
    --deferred              Show only deferred issues
    --pinned                Show only pinned issues
    --no-pinned             Exclude pinned issues
    --no-labels             Filter issues with no labels
    --no-assignee           Filter issues with no assignee
    --empty-description     Filter issues with empty description
    --has-metadata-key string Filter issues with this metadata key set
    --metadata-field stringArray Filter by metadata field (key=value)
    --flat                  Disable tree format
    --long                  Show detailed multi-line output
    --pretty                Display in tree format
    --tree                  Hierarchical tree format (default true)
-w, --watch                 Watch for changes and auto-update
    --format string         Output format: 'digraph', 'dot', or Go template
    --include-gates         Include gate issues in output
    --include-infra         Include infrastructure beads
    --include-templates     Include template molecules
    --mol-type string       Filter by molecule type: swarm, patrol, work
    --spec string           Filter by spec_id prefix
    --wisp-type string      Filter by wisp type
```

**Examples**:

```bash
bd list --json
bd list --status open --priority 1 --assignee alice
bd list --label urgent --sort priority
bd list --type bug --created-after 2025-01-01
bd list --format dot | dot -Tsvg > graph.svg
```

### `bd ready`

Show ready work (open, no active blockers).

**Synopsis**: `bd ready [flags]`

**Examples**:

```bash
bd ready
bd ready --json
bd ready --assignee alice
```

### `bd blocked`

Show blocked issues (those waiting on dependencies).

**Synopsis**: `bd blocked [flags]`

**Key flags**:

```
    --parent string   Filter to descendants of this bead/epic
```

### `bd search`

Search issues by text query.

**Synopsis**: `bd search [query] [flags]`

ID-like queries use fast exact/prefix matching. Text queries search titles. Use `--desc-contains` for description search.

**Key flags**:

```
    --desc-contains string  Filter by description substring
-a, --assignee string       Filter by assignee
-l, --label strings         Filter by labels (AND)
    --label-any strings     Filter by labels (OR)
-n, --limit int             Limit results
-s, --status string         Filter by status (open, closed, all)
-t, --type string           Filter by type
    --sort string           Sort by field
    --priority-min string   Minimum priority
    --priority-max string   Maximum priority
    --created-after string  Created after date
    --external-contains string Filter by external ref substring
    --no-assignee           Issues with no assignee
    --no-labels             Issues with no labels
```

**Examples**:

```bash
bd search "authentication bug"
bd search "bd-5q"           # Partial ID prefix match
bd search "bug" --sort priority
bd search "api" --status all  # Include closed
```

### `bd query`

Query using a simple query language with compound filters and boolean operators.

**Synopsis**: `bd query [expression] [flags]`

**Supported fields**: `status`, `priority`, `type`, `assignee`, `owner`, `label`, `title`, `description`, `notes`, `created`, `updated`, `started`, `closed`, `id`, `spec`, `pinned`, `ephemeral`, `template`, `parent`, `mol_type`

**Operators**: `=`, `!=`, `>`, `>=`, `<`, `<=`, `AND`, `OR`, `NOT`, `(` `)` grouping

**Examples**:

```bash
bd query "status=open AND priority<=2 AND updated>7d"
bd query "(status=open OR status=blocked) AND priority<2"
bd query "type=bug AND label=urgent"
bd query "assignee=none AND type=task"
bd query "title=authentication AND priority=0"
```

### `bd reopen`

Reopen closed issues.

**Synopsis**: `bd reopen [id...] [flags]`

**Key flags**:

```
-r, --reason string   Reason for reopening
```

### `bd delete`

Delete one or more issues and clean up references.

**Synopsis**: `bd delete <issue-id> [issue-id...] [flags]`

**Key flags**:

```
    --cascade        Recursively delete all dependent issues
    --dry-run        Preview without deleting
-f, --force          Actually delete (required)
    --from-file string Read issue IDs from file (one per line)
```

### `bd q` (Quick Capture)

Create issue and output only ID (for scripting).

**Synopsis**: `bd q [title] [flags]`

**Key flags**:

```
-l, --labels strings    Labels
-p, --priority string   Priority (0-4)
-t, --type string       Issue type
```

**Examples**:

```bash
ISSUE=$(bd q "New feature")
bd q "Fix login bug"   # Outputs: bd-a1b2
bd q "Task" | xargs bd show
```

### `bd comment` / `bd comments`

Add or view comments.

**Synopsis**:
- `bd comment <id> [text...] [flags]`
- `bd comments [issue-id] [flags]`
- `bd comments add [issue-id] [text] [flags]`

**Key flags**:

```
    --file string   Read comment text from file
    --stdin         Read from stdin
-a, --author string Add author to comment (comments add)
```

**Examples**:

```bash
bd comment bd-123 "Working on this now"
echo "from pipe" | bd comment bd-123 --stdin
bd comments bd-123 --json
bd comments add bd-123 -f notes.txt
```

### `bd note`

Append a note to an issue's notes field.

**Synopsis**: `bd note <id> [text...] [flags]`

Shorthand for `bd update <id> --append-notes "text"`.

### `bd assign`

Assign an issue to someone.

**Synopsis**: `bd assign <id> <name>`

Shorthand for `bd update <id> --assignee <name>`. Use `""` to unassign.

### `bd priority`

Set the priority of an issue.

**Synopsis**: `bd priority <id> <n>`

Shorthand for `bd update <id> --priority <n>`.

### `bd tag`

Add a label to an issue.

**Synopsis**: `bd tag <id> <label>`

Shorthand for `bd update <id> --add-label <label>`.

### `bd defer` / `bd undefer`

Defer or restore issues.

```bash
bd defer bd-abc                   # Status-based defer
bd defer bd-abc --until=tomorrow  # Time-based defer
bd undefer bd-abc                 # Restore to open
```

### `bd reopen`

Reopen closed issues, emitting a Reopened event.

### `bd label`

Manage issue labels.

```bash
bd label add bd-123 urgent
bd label remove bd-123 draft
bd label list bd-123
bd label list-all
bd label propagate bd-epic123 team-auth   # Push label to all children
```

### `bd todo`

Manage TODO items (convenience wrapper for task issues).

```bash
bd todo add "Fix lint errors"   # Create task P2
bd todo                          # List open todos
bd todo done bd-abc              # Close todo
bd todo list --all               # Include completed
```

### `bd set-state`

Atomically set operational state on an issue (dimension:value convention).

**Synopsis**: `bd set-state <issue-id> <dimension>=<value> [flags]`

**Examples**:

```bash
bd set-state agent-abc patrol=muted --reason "Investigating stuck worker"
bd set-state agent-abc mode=degraded
bd state agent-abc patrol       # Output: muted
bd state list agent-abc         # List all state dimensions
```

### `bd count`

Count issues matching filters.

**Synopsis**: `bd count [flags]`

**Key flags**:

```
    --by-status     Group count by status
    --by-priority   Group count by priority
    --by-type       Group count by issue type
    --by-assignee   Group count by assignee
    --by-label      Group count by label
```

**Examples**:

```bash
bd count --status open
bd count --by-status --json
bd count --assignee alice --by-status
```

---

## 3. Dependency Commands

### `bd dep add`

Add a dependency between two issues.

**Synopsis**: `bd dep add [issue-id] [depends-on-id] [flags]`

**Key flags**:

```
    --blocked-by string  Issue ID that blocks the first issue
    --depends-on string  Alias for --blocked-by
    --file string        Read dependency edges from JSONL file or stdin
    --no-cycle-check     Skip cycle detection (use for bulk wiring)
-t, --type string        Dependency type (see below)
```

**Dependency types**:

| Type | Semantics | Blocks `bd ready`? |
|------|-----------|---------------------|
| `blocks` | B can't start until A closes | Yes |
| `parent-child` | Hierarchy; children parallel by default | Yes (if parent blocked) |
| `waits-for` | B waits for all of A's children | Yes |
| `conditional-blocks` | B runs only if A fails | Yes |
| `tracks` | Tracking/observation relationship | No |
| `related` | See-also (non-blocking) | No |
| `discovered-from` | Discovery provenance | No |
| `replies-to` | Thread reply | No |
| `until` | Time-based | Situational |
| `caused-by` | Causality | No |
| `validates` | Validation relationship | No |
| `supersedes` | Replacement | No |

**Examples**:

```bash
bd dep add bd-42 bd-41                          # bd-42 depends on bd-41 (blocks)
bd dep add bd-42 --blocked-by bd-41             # Same
bd dep add bd-42 bd-41 --type related           # Non-blocking
bd dep add bd-42 bd-41 --no-cycle-check         # Bulk wiring
bd dep add --file deps.jsonl                    # Bulk: {"from":"bd-42","to":"bd-41"}
bd dep add gt-xyz external:beads:mol-run-assignee  # Cross-project dep
```

### `bd dep list`

List dependencies or dependents.

**Synopsis**: `bd dep list [issue-id...] [flags]`

**Key flags**:

```
    --direction string  'down' (dependencies, default) or 'up' (dependents)
-t, --type string       Filter by dependency type
```

### `bd dep tree`

Show dependency tree.

**Synopsis**: `bd dep tree [issue-id] [flags]`

**Key flags**:

```
    --direction string  'down' (default), 'up', or 'both'
    --format string     Output format: 'mermaid' for Mermaid.js flowchart
-d, --max-depth int     Maximum depth (default 50)
    --status string     Filter to only show issues with this status
    --show-all-paths    Show all paths (no deduplication for diamond dependencies)
```

### `bd dep remove`

Remove a dependency.

**Synopsis**: `bd dep remove [issue-id] [depends-on-id]`

### `bd dep relate` / `bd dep unrelate`

Create/remove bidirectional `relates_to` links.

```bash
bd dep relate bd-abc bd-xyz   # Link two related issues
bd dep unrelate bd-abc bd-xyz  # Remove the link
```

### `bd dep cycles`

Detect dependency cycles.

**Synopsis**: `bd dep cycles`

### `bd link`

Shorthand for `bd dep add`. Creates a `blocks` dependency by default.

**Synopsis**: `bd link <id1> <id2> [flags]`

**Key flags**:

```
-t, --type string   Dependency type (blocks|tracks|related|parent-child|discovered-from)
```

### `bd graph`

Display dependency graph visualization.

**Synopsis**: `bd graph [issue-id] [flags]`

**Key flags**:

```
    --all     Show graph for all open issues
    --box     ASCII boxes showing layers
    --compact Tree format, one line per issue
    --dot     Output Graphviz DOT format
    --html    Output self-contained interactive HTML
```

**Examples**:

```bash
bd graph bd-epic-123
bd graph --dot bd-epic-123 | dot -Tsvg > graph.svg
bd graph --html bd-epic-123 > graph.html
bd graph --all --html > all.html
```

### `bd graph check`

Check dependency graph for cycles, orphans, and integrity issues. Returns exit code 0 if clean.

### `bd duplicate`

Mark an issue as a duplicate (closes it with reference).

**Synopsis**: `bd duplicate <id> --of <canonical>`

### `bd supersede`

Mark an issue as superseded by a newer one (closes it).

**Synopsis**: `bd supersede <id> --with <new>`

### `bd children`

List child beads of a parent (includes closed by default).

**Synopsis**: `bd children <parent-id>`

---

## 4. Assignment and Claiming

Claiming is atomic — it sets both assignee and status atomically, preventing race conditions in multi-agent environments.

### `bd update <id> --claim`

Atomically claim an issue. Sets `assignee` to the current actor and `status` to `in_progress`. Idempotent if already claimed by the same actor.

```bash
bd update bd-abc --claim --json
```

**Actor resolution order**: `--actor` flag → `$BEADS_ACTOR` → git `user.name` → `$USER`

### `bd assign <id> <name>`

Assign an issue without changing status.

```bash
bd assign bd-123 alice
bd assign bd-123 ""   # unassign
```

### `bd update <id> --assignee <name>`

Same as `bd assign`. Can be combined with other update flags.

### Execution Metadata

Issues can carry structured execution hints in their `metadata` field:

```bash
bd show <id> --json | jq '.[0] | .metadata'
```

Recognized keys:
- `execution_agent_type` — which subagent type should execute this
- `execution_suggested_model` — model to use
- `execution_reasoning_effort` — effort level
- `execution_mode` — execution mode
- `execution_parallel_group` — parallel group identifier

---

## 5. Memory System

The memory system stores project-wide persistent knowledge that survives session boundaries and is injected at prime time.

### `bd remember`

Store a persistent memory.

**Synopsis**: `bd remember "<insight>" [flags]`

**Key flags**:

```
    --key string   Explicit key (auto-generated if not set; updates in place if key exists)
```

**Examples**:

```bash
bd remember "always run tests with -race flag"
bd remember "auth module uses JWT not sessions" --key auth-jwt
bd remember "Dolt phantom DBs hide in three places" --key dolt-phantoms
```

### `bd memories`

List or search persistent memories.

**Synopsis**: `bd memories [search]`

**Examples**:

```bash
bd memories              # List all
bd memories dolt         # Search for memories about dolt
bd memories "race flag"  # Search for phrase
```

### `bd recall`

Retrieve the full content of a memory by key.

**Synopsis**: `bd recall <key>`

**Examples**:

```bash
bd recall auth-jwt
bd recall dolt-phantoms
```

### `bd forget`

Remove a persistent memory by key.

**Synopsis**: `bd forget <key>`

**Examples**:

```bash
bd forget auth-jwt
```

### `bd prime`

Output AI-optimized workflow context (includes memories). Called at session start by hooks.

**Synopsis**: `bd prime [flags]`

**Key flags**:

```
    --export          Output default content (ignores PRIME.md override)
    --full            Force full CLI output (ignore MCP detection)
    --hook-json       Wrap output in SessionStart hook JSON envelope
    --mcp             Force MCP mode (minimal ~50 token output)
    --memories-only   Output only persistent memories
    --stealth         Stealth mode (no git operations)
```

Automatically detects MCP server active (MCP mode: ~50 tokens) vs CLI mode (~1-2k tokens). Supports `.beads/PRIME.md` override.

---

## 6. Formula and Molecule System

Beads has a chemistry-metaphor workflow system for reusable work templates.

### Phase Concepts

| Phase | Name | Storage | Synced | Purpose |
|-------|------|---------|--------|---------|
| Solid | Proto | `.beads/` | Yes | Frozen template |
| Liquid | Mol | `.beads/` | Yes | Active persistent work |
| Vapor | Wisp | `.beads/` (Wisp=true) | No | Ephemeral operations |

### `bd formula`

Manage workflow formula files (TOML/JSON).

Search paths (in order): project `.beads/formulas/`, repo `.beads/formulas/`, `~/.beads/formulas/`, `$GT_ROOT/.beads/formulas/`.

```bash
bd formula list                 # List all formulas
bd formula list --type workflow # Filter by type
bd formula show shiny           # Show formula details
bd formula convert shiny        # Convert JSON to TOML
bd formula convert --all        # Convert all JSON formulas
```

### `bd cook`

Compile a formula into a proto.

**Synopsis**: `bd cook <formula-file> [flags]`

**Modes**:
- `compile` (default): keep `{{variable}}` placeholders intact
- `runtime`: substitute variables (when `--var` flags provided)

**Key flags**:

```
    --dry-run               Preview what would be created
    --force                 Replace existing proto
    --mode string           'compile' or 'runtime'
    --persist               Write proto to database (legacy)
    --var stringArray       Variable substitution (key=value)
    --search-path strings   Additional paths for formula inheritance
```

**Examples**:

```bash
bd cook mol-feature.formula.json                   # Compile-time
bd cook mol-feature --var name=auth                # Runtime substitution
bd cook mol-release.formula.json --persist --force # Write to database
```

### `bd mol` — Molecule Commands

#### `bd mol pour <proto>`

Instantiate a proto as a persistent mol (solid → liquid).

#### `bd mol wisp <proto>`

Instantiate a proto as an ephemeral wisp (solid → vapor).

#### `bd mol squash <id>`

Compress molecule execution into a digest (permanent record).

#### `bd mol burn <id>`

Delete a molecule without creating a digest (discard).

#### `bd mol show <id>`

Show molecule details.

#### `bd mol current`

Show current position in molecule workflow.

#### `bd mol progress`

Show molecule progress summary.

#### `bd mol ready`

Find molecules ready for gate-resume dispatch.

#### `bd mol bond <A> <B>`

Bond two protos or molecules together.

**Bonding semantics**:

| Operands | Effect |
|----------|--------|
| epic + epic | Creates dependency edge |
| proto + epic | Spawns proto as new issues, attaches to epic |
| proto + proto | Creates compound template |

```bash
bd mol bond A B                    # B depends on A (sequential)
bd mol bond A B --type parallel    # Organizational link, no blocking
bd mol bond A B --type conditional # B runs only if A fails
```

#### `bd mol distill`

Extract a formula from an existing epic.

#### `bd mol stale`

Detect complete-but-unclosed molecules.

#### `bd mol last-activity`

Show last activity timestamp for a molecule.

#### `bd mol seed`

Verify formula accessibility.

### `bd swarm` — Swarm Management

Structured parallel work coordination on epics.

```bash
bd swarm create bd-epic-123              # Create swarm molecule for epic
bd swarm list                            # List all swarms
bd swarm status bd-epic-123              # Show swarm status (computed from beads)
bd swarm validate bd-epic-123            # Validate epic structure for swarming
```

### `bd promote`

Promote a wisp (ephemeral issue) to a permanent bead.

**Synopsis**: `bd promote <wisp-id> [flags]`

---

## 7. Output Formats and JSON Support

**JSON output is available on virtually every command** via the global `--json` flag.

### Global `--json` flag

Returns structured JSON output. All list commands return arrays, all show commands return arrays of issue objects.

```bash
bd list --json
bd show bd-123 --json
bd ready --json
bd status --json
bd create "Title" --json        # Returns created issue
bd update bd-123 --claim --json # Returns updated issue
bd close bd-123 --json          # Returns closed issue
```

### Issue JSON Schema (selected fields from `bd export` / `bd show --json`)

```
id                    Issue ID (e.g., "bd-a1b2")
title                 Issue title
description           Long-form body
design                Design notes
notes                 Additional notes
acceptance_criteria   Acceptance criteria
issue_type            bug|feature|task|epic|chore|...
priority              0-4
status                open|in_progress|blocked|deferred|closed
assignee              Assigned user
owner                 Issue owner
created_by            Creator
labels                Array of strings
dependencies          Array of {issue_id, depends_on_id, type, ...}
comments              Array of comment objects
external_ref          Cross-system identifier (e.g., "gh-9")
source_system         Source system
due_at                RFC3339 timestamp
defer_until           RFC3339 timestamp
created_at            RFC3339 timestamp
updated_at            RFC3339 timestamp
started_at            RFC3339 timestamp
closed_at             RFC3339 timestamp
metadata              Arbitrary JSON object
ephemeral             boolean
pinned                boolean
template              boolean
parent                Parent issue ID
mol_type              swarm|patrol|work (for molecules)
```

### Other Output Formats

`bd list` supports `--format` with:
- `digraph` — for `golang.org/x/tools/cmd/digraph`
- `dot` — Graphviz DOT format
- Go template

`bd dep tree` supports `--format mermaid`.

`bd graph` supports `--dot`, `--html`, `--box`, `--compact`.

### `bd export`

Export all issues to JSONL format.

**Synopsis**: `bd export [flags]`

**Key flags**:

```
    --all                Include all records (infra, templates, gates, memories)
    --include-infra      Include infrastructure beads
    --include-memories   Include persistent memories
-o, --output string      Output file path (default: stdout)
    --scrub              Exclude test/pollution records
```

### `bd import`

Import issues from JSONL.

**Synopsis**: `bd import [file|-] [flags]`

Supports full round-trip: `bd export | bd import`. Memory records auto-imported. Upsert semantics.

**Key flags**:

```
    --dedup   Skip lines whose title matches an existing open issue
    --dry-run Show what would be imported
```

### `bd sql`

Execute raw SQL against the beads database (Dolt/SQLite-compatible).

```bash
bd sql 'SELECT COUNT(*) FROM issues'
bd sql 'SELECT id, title FROM issues WHERE status = "open" LIMIT 5'
bd sql --csv 'SELECT id, title, status FROM issues'
```

---

## 8. Sync and Federation

### Storage Backend

Beads uses Dolt as its database (version-controlled SQL with cell-level merge). Two modes:
- **Embedded mode** (default): Dolt runs in-process. Data in `.beads/embeddeddolt/`. Single-writer only.
- **Server mode** (`--server`): External `dolt sql-server`. Supports multiple concurrent writers.

### `bd dolt push` / `bd dolt pull`

Primary sync mechanism. Uses `refs/dolt/data` separate from git source branches.

```bash
bd dolt push              # Push to configured remote
bd dolt pull              # Pull from configured remote
bd dolt push --force      # Force push
bd dolt pull --remote staging  # Pull from named remote
```

### `bd dolt remote`

Manage Dolt remotes.

```bash
bd dolt remote add origin <git-origin-url>
bd dolt remote list
bd dolt remote remove origin
```

### `bd bootstrap`

Set up beads on a fresh clone. Auto-detects: sync.remote, git origin with `refs/dolt/data`, backup JSONL, or creates fresh.

```bash
bd bootstrap
bd bootstrap --dry-run
bd bootstrap --yes        # Non-interactive
```

### `bd backup`

Backup and restore the Dolt database.

```bash
bd backup init /path/to/backup        # Configure backup destination
bd backup init https://doltremoteapi.dolthub.com/user/repo  # DoltHub
bd backup sync                        # Push to backup
bd backup restore --force /path/to/backup  # Restore
bd backup status                      # Show backup status
bd backup remove                      # Remove backup config
```

### Cross-Machine Sync Workflow

```bash
# Machine A (initial setup)
bd init
bd dolt remote add origin <git-url>
bd dolt push

# Machine B (fresh clone)
git clone <git-url>
bd bootstrap   # Detects refs/dolt/data and clones it

# Ongoing sync
bd dolt push   # After writing issues
bd dolt pull   # Before reading on another machine
```

### `bd vc` — Version Control

```bash
bd vc status          # Show current branch and uncommitted changes
bd vc commit -m "msg" # Commit pending changes
bd vc merge feature-xyz --strategy ours  # Merge branch (conflict: 'ours' or 'theirs')
bd branch             # List branches
bd branch feature-xyz # Create branch
bd diff main HEAD     # Show changes between refs
```

### Dolt Auto-Commit Policy

Global `--dolt-auto-commit` flag (or config `dolt.auto-commit`):
- `off` (default): no auto-commit per command
- `on`: commit after each write
- `batch`: defer commits; SIGTERM/SIGHUP flush

### Federation

P2P federation (requires CGO build). Configured via `bd config set federation.sovereignty` (T1-T4) and `federation.remote`.

### `bd repo` — Multi-Repo Hydration

Hydrate issues from multiple beads repositories into one database.

```bash
bd repo add ~/beads-planning     # Add planning repo
bd repo list                     # Show all configured repos
bd repo remove ~/beads-planning  # Remove
bd repo sync                     # Import from all configured repos
```

---

## 9. Git Hooks and Automation

### `bd hooks install`

Install git hooks for beads integration.

**Synopsis**: `bd hooks install [flags]`

**Installed hooks**:
- `pre-commit` — Run chained hooks before commit; refreshes `.beads/issues.jsonl` when `export.auto=true`
- `post-merge` — Run chained hooks after pull/merge
- `pre-push` — Run chained hooks before push
- `post-checkout` — Run chained hooks after branch checkout
- `prepare-commit-msg` — Add agent identity trailers (forensics)

**Key flags**:

```
    --beads   Install to .beads/hooks/ (recommended for Dolt backend)
    --shared  Install to .beads-hooks/ (versioned, shareable)
    --chain   Chain with existing hooks
    --force   Overwrite existing hooks
```

```bash
bd hooks install
bd hooks install --beads
bd hooks list            # Show status
bd hooks uninstall
bd hooks run pre-commit  # Execute manually
```

### `bd setup`

Install integration for specific AI editors/tools.

**Supported recipes**: `cursor`, `claude`, `gemini`, `aider`, `factory`, `codex`, `mux`, `opencode`, `junie`, `windsurf`, `cody`, `kilocode`

```bash
bd setup claude          # Install Claude Code integration (hooks/settings)
bd setup claude --global # Install globally
bd setup codex           # Install Codex skill + AGENTS.md
bd setup --list          # Show all recipes
bd setup claude --check  # Verify installation
bd setup claude --remove # Uninstall
```

### `bd prime` as Hook Context

`bd prime --hook-json` wraps output in SessionStart JSON envelope for Claude Code, Gemini CLI, Codex hooks. Injects memories and workflow context at every session start.

### `bd audit`

Record agent interactions for audit/training (append-only JSONL at `.beads/interactions.jsonl`).

```bash
bd audit record --kind llm_call --prompt "..." --response "..."
bd audit record --kind tool_call --tool-name bd_create
bd audit label <entry-id> --label good --reason "Correct"
```

### `bd batch`

Run multiple write operations in a single database transaction.

```bash
# From pipe
bd list --status stale -q | awk '{print "close",$1," stale"}' | bd batch

# From file
bd batch -f operations.txt

# Inline
printf 'close bd-1 done\nupdate bd-2 status=in_progress\n' | bd batch
```

**Supported batch commands**: `close`, `update` (status/priority/title/assignee), `create`, `dep add`, `dep remove`

### `bd kv` — Key-Value Store

Persistent key-value store for flags/config across sessions.

```bash
bd kv set feature_flag true
bd kv get feature_flag
bd kv clear feature_flag
bd kv list
```

### `bd gate` — Async Coordination Gates

Gates block workflow steps until conditions are met.

**Gate types**:
- `human` — Requires manual `bd gate resolve`
- `timer` — Auto-expires after timeout
- `gh:run` — Waits for GitHub Actions workflow
- `gh:pr` — Waits for PR merge
- `bead` — Waits for cross-rig bead to close

```bash
bd gate list                           # Show open gates
bd gate list --all                     # Include closed
bd gate create --blocks bd-abc         # Create human gate
bd gate create --type=timer --blocks bd-abc --timeout=2h
bd gate create --type=gh:pr --blocks bd-abc --await-id=42
bd gate check                          # Evaluate all open gates
bd gate check --type=gh                # Check only GitHub gates
bd gate resolve <gate-id>              # Manually resolve
bd gate discover                       # Auto-discover GH run IDs
bd gate add-waiter <gate-id> <waiter>  # Register waiter
```

### `bd merge-slot` — Exclusive Access Primitive

Serialize conflict resolution in multi-agent environments.

```bash
bd merge-slot create    # Create slot for current rig
bd merge-slot check     # Check availability
bd merge-slot acquire   # Try to acquire (--wait to queue)
bd merge-slot release   # Release after conflict resolution
```

---

## 10. Views and Reporting

### `bd status` / `bd stats`

Show issue database overview and statistics.

```bash
bd status
bd status --json
bd status --assigned   # Show issues assigned to current user
bd status --no-activity # Skip git activity (faster)
```

### `bd stale`

Show issues not updated recently.

```bash
bd stale
bd stale --days 14
bd stale --status in_progress
```

### `bd history`

Show version history for an issue (all Dolt commits where it was modified).

```bash
bd history bd-123
bd history bd-123 --limit 5
```

### `bd orphans`

Identify orphaned issues (referenced in commits but still open).

### `bd lint`

Check issues for missing template sections (Acceptance Criteria, Steps to Reproduce, etc.).

```bash
bd lint                 # All open issues
bd lint bd-abc          # Specific issue
bd lint --type bug      # Filter by type
bd lint --status all    # Include closed
```

### `bd find-duplicates`

Find semantically similar issues using text analysis or AI.

```bash
bd find-duplicates                  # Mechanical similarity (default)
bd find-duplicates --method ai      # LLM-based (requires ANTHROPIC_API_KEY)
bd find-duplicates --threshold 0.4  # Lower = more results
```

### `bd duplicates`

Find exact-content duplicates and optionally merge.

```bash
bd duplicates
bd duplicates --auto-merge
bd duplicates --dry-run
```

### `bd preflight`

Show PR readiness checklist.

```bash
bd preflight --check
bd preflight --check --json
```

### `bd epic status` / `bd epic close-eligible`

```bash
bd epic status                         # Show epic completion status
bd epic status --eligible-only         # Only epics ready to close
bd epic close-eligible                 # Close epics where all children done
bd epic close-eligible --dry-run       # Preview
```

### `bd human` — Human Escalation Management

```bash
bd human list                         # List all human-needed beads
bd human respond bd-123 -r "Approved" # Respond (adds comment + closes)
bd human dismiss bd-123               # Dismiss without responding
bd human stats                        # Summary statistics
```

### `bd statuses` / `bd types`

List valid statuses and types.

```bash
bd statuses --json
bd types --json
```

---

## 11. Maintenance and Database Operations

### `bd init`

Initialize beads in the current directory.

**Key flags**:

```
-p, --prefix string      Issue prefix (default: directory name)
    --stealth            Enable stealth mode (no git commits)
    --contributor        OSS contributor setup wizard
    --server             Use external dolt sql-server
    --shared-server      Shared Dolt server mode
    --skip-agents        Skip AGENTS.md generation
    --skip-hooks         Skip git hooks installation
    --from-jsonl         Import from .beads/issues.jsonl
    --quiet              Suppress output
    --non-interactive    Skip all prompts
    --role string        Set role: "maintainer" or "contributor"
```

### `bd doctor`

Check and fix beads installation health.

```bash
bd doctor
bd doctor --fix          # Auto-fix issues
bd doctor --fix --yes    # Non-interactive fix
bd doctor --agent --json # AI-agent-facing diagnostics (ZFC-compliant)
bd doctor --deep         # Full graph integrity validation
bd doctor --perf         # Performance diagnostics
bd doctor --server       # Dolt server mode health checks
```

### `bd gc`

Full lifecycle garbage collection (decay closed issues + compact Dolt commits + Dolt GC).

```bash
bd gc
bd gc --older-than 30    # Decay issues closed 30+ days ago
bd gc --dry-run
bd gc --skip-decay       # Only compact + GC
bd gc --force            # Skip confirmation
```

### `bd compact` / `bd flatten`

Compact Dolt commit history.

```bash
bd compact --days 30 --force   # Squash commits older than 30 days
bd flatten --force             # Nuclear: squash ALL history to single commit
```

### `bd prune` / `bd purge`

Delete closed issues.

```bash
bd prune --older-than 30d --force    # Delete closed regular beads > 30 days
bd purge --force                     # Delete all closed ephemeral beads
```

### `bd migrate`

Database migration commands.

```bash
bd migrate                     # Check and update database metadata
bd migrate hooks --apply       # Migrate git hooks to marker format
bd migrate issues --from ~/old --to . --dry-run  # Move issues between repos
bd migrate sync beads-sync     # Configure sync branch workflow
```

### `bd admin`

Administrative database commands.

```bash
bd admin cleanup --force              # Delete all closed issues
bd admin cleanup --older-than 30 --force  # Only older issues
bd admin compact --analyze --json     # Export compaction candidates
bd admin compact --apply --id bd-42 --summary summary.txt
bd admin reset --force                # Remove all beads data
```

### `bd rename-prefix`

Rename the issue prefix for all issues.

```bash
bd rename-prefix kw-           # Rename from current to 'kw-'
bd rename-prefix kw- --dry-run # Preview
bd rename-prefix mtg- --repair # Consolidate multiple prefixes
```

### `bd config`

Manage configuration settings.

```bash
bd config set export.auto false
bd config set jira.url "https://company.atlassian.net"
bd config set status.custom "awaiting_review,awaiting_testing"
bd config get export.auto
bd config list
bd config show                  # All effective config with provenance
bd config unset jira.url
bd config apply                 # Reconcile state to match config
bd config drift                 # Detect config vs reality inconsistencies
bd config validate              # Validate sync-related config
```

---

## 12. Integrations

### GitHub (`bd github`)

Bidirectional sync with GitHub Issues.

```bash
bd github sync --pull-only
bd github sync --push-only
bd github sync --dry-run
bd github sync --prefer-local  # On conflict, keep local
bd github pull bd-abc           # Pull specific bead from GitHub
bd github push bd-abc           # Push specific bead to GitHub
bd github repos                 # List accessible repos
bd github status                # Show sync status
```

**Configuration**:

```bash
bd config set github.token "YOUR_TOKEN"
bd config set github.owner "owner"
bd config set github.repo "repo"
# Or: bd config set github.repository "owner/repo"
```

### Linear (`bd linear`)

Bidirectional sync with Linear.

```bash
bd linear sync --pull
bd linear sync --push --create-only
bd linear sync --pull-if-stale --threshold 5m
bd linear sync --push --type=task,feature  # Type filtering
bd linear sync --push --parent=bd-abc123   # Push tree
bd linear status
bd linear teams   # List accessible teams
```

**Priority mapping**, **state mapping**, **label-to-type mapping**, **relation mapping** all configurable via `bd config set linear.*`.

### Jira (`bd jira`)

Bidirectional sync with Jira.

```bash
bd jira sync --pull
bd jira sync --push
bd jira sync --dry-run
bd jira status
```

### Azure DevOps (`bd ado`)

Bidirectional sync with Azure DevOps.

```bash
bd ado sync
bd ado sync --pull-only --project "MyProject"
bd ado sync --push-only --types "Bug,Task"
bd ado status
bd ado projects  # List accessible projects
```

### GitLab (`bd gitlab`)

Bidirectional sync with GitLab.

```bash
bd gitlab sync --pull-only
bd gitlab sync --push-only
bd gitlab status
bd gitlab projects  # List accessible projects
```

### Notion (`bd notion`)

Bidirectional sync with Notion.

```bash
bd notion init           # Create dedicated Beads database in Notion
bd notion connect        # Connect to existing Notion database
bd notion sync
bd notion status
```

---

## 13. Global Flags

Available on all commands:

```
    --actor string             Actor name for audit trail
                               (default: $BEADS_ACTOR, git user.name, $USER)
    --db string                Database path (default: auto-discover .beads/*.db)
-C, --directory string         Change to this directory before running
    --dolt-auto-commit string  Dolt auto-commit policy (off|on|batch)
    --global                   Use the global shared-server database
    --json                     Output in JSON format
    --profile                  Generate CPU profile for performance analysis
-q, --quiet                    Suppress non-essential output (errors only)
    --readonly                 Read-only mode: block write operations
    --sandbox                  Sandbox mode: disables Dolt auto-push
-v, --verbose                  Enable verbose/debug output
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `BEADS_ACTOR` | Default actor for audit trail |
| `BEADS_DIR` | Override `.beads/` directory location |
| `BEADS_DB` | Override database path |
| `BD_NON_INTERACTIVE` | Skip all interactive prompts |
| `BEADS_DOLT_SERVER_HOST` | Dolt server host |
| `BEADS_DOLT_SERVER_PORT` | Dolt server port |
| `BEADS_DOLT_SERVER_SOCKET` | Unix socket path |
| `BEADS_DOLT_SERVER_USER` | Dolt MySQL user |
| `BEADS_DOLT_PASSWORD` | Dolt server password |
| `GT_ROOT` | Shared workspace root (formula search path) |
| `GITHUB_TOKEN` | GitHub integration |
| `LINEAR_API_KEY` | Linear integration |
| `JIRA_API_TOKEN` | Jira integration |
| `ANTHROPIC_API_KEY` | AI-powered features (find-duplicates, compact) |
| `CLAUDE_SESSION_ID` | Claude Code session ID for close events |

---

## 14. Feature Capabilities Summary

| Feature | Capability | Notes |
|---------|-----------|-------|
| **JSON output** | Yes | Global `--json` flag on virtually every command |
| **Create issue** | Yes | `bd create` with full field support |
| **Read issue** | Yes | `bd show`, `bd list`, `bd query`, `bd search` |
| **Update issue** | Yes | `bd update` with all fields |
| **Close issue** | Yes | `bd close` with reason |
| **Reopen issue** | Yes | `bd reopen` with reason |
| **Delete issue** | Yes | `bd delete` with cascade option |
| **Priorities** | Yes | 5-level P0-P4 system |
| **Issue types** | Yes | Built-in + custom types |
| **Labels** | Yes | Multiple labels per issue, propagation |
| **Assignees** | Yes | Single assignee; atomic claim (`--claim`) |
| **Comments** | Yes | `bd comment`, `bd comments` |
| **Dependencies** | Yes | 10+ dependency types; blocking and non-blocking |
| **Dependency graph** | Yes | DAG visualization (terminal, DOT, HTML, Mermaid) |
| **Hierarchy / epics** | Yes | Parent-child with hierarchical IDs |
| **Ready work detection** | Yes | `bd ready` — dependency-aware |
| **Blocking detection** | Yes | `bd blocked` |
| **Custom metadata** | Yes | Arbitrary JSON on every issue |
| **Persistent memories** | Yes | `bd remember`, `bd memories`, `bd recall` |
| **Formula/workflow templates** | Yes | TOML/JSON formulas, proto → mol/wisp lifecycle |
| **Swarm/parallel orchestration** | Yes | `bd swarm`, multi-agent DAG execution |
| **Async gates** | Yes | human, timer, gh:run, gh:pr, bead gate types |
| **Merge slot (mutex)** | Yes | Serialized conflict resolution |
| **Dolt push/pull sync** | Yes | `bd dolt push/pull` via `refs/dolt/data` |
| **Multi-repo hydration** | Yes | `bd repo add/sync` |
| **Backup/restore** | Yes | `bd backup` (local + DoltHub) |
| **GitHub sync** | Yes | `bd github sync` — bidirectional |
| **Linear sync** | Yes | `bd linear sync` — bidirectional |
| **Jira sync** | Yes | `bd jira sync` — bidirectional |
| **GitLab sync** | Yes | `bd gitlab sync` — bidirectional |
| **ADO sync** | Yes | `bd ado sync` — bidirectional |
| **Notion sync** | Yes | `bd notion sync` — bidirectional |
| **Git hooks** | Yes | pre-commit, post-merge, pre-push, post-checkout |
| **AI agent hooks (prime)** | Yes | `bd prime --hook-json` for SessionStart |
| **Batch operations** | Yes | `bd batch` — transactional multi-command |
| **Raw SQL access** | Yes | `bd sql` — direct Dolt query |
| **Version history** | Yes | `bd history`, `bd diff`, `bd vc` |
| **Branch support** | Yes | `bd branch`, `bd vc merge` |
| **Git worktrees** | Yes | `bd worktree` — parallel development |
| **Key-value store** | Yes | `bd kv` — persistent per-project |
| **Audit log** | Yes | `bd audit` — append-only JSONL |
| **AI duplicate detection** | Yes | `bd find-duplicates --method ai` |
| **Stale issue detection** | Yes | `bd stale` |
| **Lint/template validation** | Yes | `bd lint` |
| **Deferred issues** | Yes | `bd defer --until` |
| **Compaction/GC** | Yes | `bd gc`, `bd compact`, `bd admin compact` |
| **Cross-project deps** | Yes | `external:<project>:<capability>` dep format |
| **External refs** | Yes | `--external-ref` on create/update |
| **Stealth mode** | Yes | `bd init --stealth` — no git commits |
| **Git-free usage** | Yes | `BEADS_DIR` + `--stealth` |
| **Multi-assignee** | No | Single assignee field only |
| **Issue templates (per-type)** | Partial | Lint validates sections; not UI forms |
| **Webhooks/callbacks** | No | Hooks are local git hooks only |
| **Real-time notifications** | No | Poll-based via `bd ready --watch` |
| **Native pagination in API** | Partial | `--limit` and `--offset` on most list commands |
| **Issue pinning** | Yes | Pinned issues excluded from GC; `--pinned` filter |
| **Issue due dates** | Yes | `--due` with flexible formats |
| **Time estimates** | Yes | `--estimate` in minutes |
| **Spec linking** | Yes | `--spec-id` links to specification doc |
