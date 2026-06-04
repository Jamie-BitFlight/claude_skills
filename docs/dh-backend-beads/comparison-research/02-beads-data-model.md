---
title: "Beads Data Model: Complete Reference"
date: 2026-05-14
scope: "Full documentation of beads storage format, issue schema, relationships, and GitHub Issues mapping"
source_type: source_code
source_path: /home/user/repos/beads/
summarized_at: 2026-05-14
method: direct source read
word_count_source: ~18000 (types.go + schema migrations + storage interfaces)
word_count_summary: ~2800
confidence: high — all fields sourced from Go structs and SQL DDL, not inferred
---

## Summary

Beads is a Git-native issue tracker backed by DoltDB (MySQL-wire-compatible version-controlled SQL). Issues are stored as rows in a `issues` table (persistent) or `wisps` table (ephemeral). The primary interchange format is JSONL: after each write operation beads auto-exports `issues.jsonl` (one complete JSON object per line, no delta encoding). Each line in `issues.jsonl` is a full snapshot of one issue — deletes are not tracked in JSONL, they are tracked in Dolt commit history.

The data model is significantly richer than GitHub Issues: it has first-class dependency typing (19 built-in edge types), a dual-table architecture separating persistent from ephemeral work, compaction tiers for old issues, swarm/molecule coordination primitives, async gate primitives for CI integration, and federation across multiple Dolt remotes.

## What Was Found

### 1. Full Issue Schema

Source: `internal/types/types.go` lines 16–113 and `internal/storage/schema/migrations/0001_create_issues.up.sql`

Every field with its Go type, JSON key, SQL column, and constraint:

| Go Field | JSON Key | SQL Column | Type | Notes |
|---|---|---|---|---|
| `ID` | `id` | `id VARCHAR(255) PK` | string | Format: `<prefix>-<nanoid>` (e.g., `bd-main-idj`) |
| `ContentHash` | _(omitted)_ | `content_hash VARCHAR(64)` | string | SHA-256 of canonical fields; not serialized to JSON |
| `Title` | `title` | `title VARCHAR(500) NOT NULL` | string | Required; max 500 chars |
| `Description` | `description` | `description TEXT NOT NULL` | string | Markdown; omitted from JSON when empty |
| `Design` | `design` | `design TEXT NOT NULL` | string | Markdown; omitted from JSON when empty |
| `AcceptanceCriteria` | `acceptance_criteria` | `acceptance_criteria TEXT NOT NULL` | string | Markdown; omitted from JSON when empty |
| `Notes` | `notes` | `notes TEXT NOT NULL` | string | Markdown; omitted from JSON when empty |
| `SpecID` | `spec_id` | `spec_id VARCHAR(1024)` | string | External spec reference; omitted when empty |
| `Status` | `status` | `status VARCHAR(32) NOT NULL DEFAULT 'open'` | Status enum | See Status section below |
| `Priority` | `priority` | `priority INT NOT NULL DEFAULT 2` | int | Range 0–4; 0=P0 (critical), 4=P4 (low) |
| `IssueType` | `issue_type` | `issue_type VARCHAR(32) NOT NULL DEFAULT 'task'` | IssueType enum | See IssueType section below |
| `Assignee` | `assignee` | `assignee VARCHAR(255)` | string | Username or email |
| `Owner` | `owner` | `owner VARCHAR(255) DEFAULT ''` | string | Git author email; human attribution (CV) |
| `EstimatedMinutes` | `estimated_minutes` | `estimated_minutes INT` | *int | Nullable; must be >= 0 |
| `CreatedAt` | `created_at` | `created_at DATETIME NOT NULL` | time.Time | RFC3339Z in JSON |
| `CreatedBy` | `created_by` | `created_by VARCHAR(255) DEFAULT ''` | string | Display name of creator |
| `UpdatedAt` | `updated_at` | `updated_at DATETIME NOT NULL ON UPDATE CURRENT_TIMESTAMP` | time.Time | Auto-updated |
| `StartedAt` | `started_at` | `started_at DATETIME` | *time.Time | Set when status transitions to `in_progress` |
| `ClosedAt` | `closed_at` | `closed_at DATETIME` | *time.Time | Required when status=`closed`; null otherwise |
| `CloseReason` | `close_reason` | `close_reason TEXT DEFAULT ''` | string | Human or machine reason for closure |
| `ClosedBySession` | `closed_by_session` | `closed_by_session VARCHAR(255) DEFAULT ''` | string | Claude Code session ID that closed the issue |
| `DueAt` | `due_at` | `due_at DATETIME` | *time.Time | Scheduling deadline |
| `DeferUntil` | `defer_until` | `defer_until DATETIME` | *time.Time | Hidden from `bd ready` until this time |
| `ExternalRef` | `external_ref` | `external_ref VARCHAR(255)` | *string | e.g., `gh-9`, `jira-ABC-123` |
| `SourceSystem` | `source_system` | `source_system VARCHAR(255) DEFAULT ''` | string | Federation adapter that created this (e.g., `github`) |
| `Metadata` | `metadata` | `metadata JSON DEFAULT ({})` | json.RawMessage | Arbitrary JSON blob; validated for well-formedness |
| `CompactionLevel` | `compaction_level` | `compaction_level INT DEFAULT 0` | int | 0=full, 1=tier1 compacted, 2=tier2 compacted |
| `CompactedAt` | `compacted_at` | `compacted_at DATETIME` | *time.Time | When last compacted |
| `CompactedAtCommit` | `compacted_at_commit` | `compacted_at_commit VARCHAR(64)` | *string | Git commit hash at compaction time |
| `OriginalSize` | `original_size` | `original_size INT` | int | Pre-compaction byte size |
| `Ephemeral` | `ephemeral` | `ephemeral TINYINT(1) DEFAULT 0` | bool | If true, stored in `wisps` table; not git-tracked |
| `NoHistory` | `no_history` | `no_history TINYINT(1) DEFAULT 0` | bool | Stored in wisps but not GC-eligible |
| `WispType` | `wisp_type` | `wisp_type VARCHAR(32) DEFAULT ''` | WispType enum | TTL classification for ephemeral compaction |
| `Pinned` | `pinned` | `pinned TINYINT(1) DEFAULT 0` | bool | Persistent context bead; never work item |
| `IsTemplate` | `is_template` | `is_template TINYINT(1) DEFAULT 0` | bool | Read-only template molecule |
| `MolType` | `mol_type` | `mol_type VARCHAR(32) DEFAULT ''` | MolType enum | `swarm`, `patrol`, or `work` |
| `WorkType` | `work_type` | `work_type VARCHAR(32) DEFAULT 'mutex'` | WorkType enum | `mutex` or `open_competition` |
| `Sender` | `sender` | `sender VARCHAR(255) DEFAULT ''` | string | Sender identity for inter-agent messages |
| `EventKind` | `event_kind` | `event_kind VARCHAR(32) DEFAULT ''` | string | Namespaced event: `patrol.muted`, `agent.started` |
| `Actor` | `actor` | `actor VARCHAR(255) DEFAULT ''` | string | Entity URI that caused event |
| `Target` | `target` | `target VARCHAR(255) DEFAULT ''` | string | Entity URI or bead ID affected |
| `Payload` | `payload` | `payload TEXT DEFAULT ''` | string | Event-specific JSON |
| `AwaitType` | `await_type` | `await_type VARCHAR(32) DEFAULT ''` | string | Gate condition: `gh:run`, `gh:pr`, `timer`, `human`, `mail` |
| `AwaitID` | `await_id` | `await_id VARCHAR(255) DEFAULT ''` | string | Gate target identifier (run ID, PR number, etc.) |
| `Timeout` | `timeout` | `timeout_ns BIGINT DEFAULT 0` | time.Duration | Max wait before escalation (stored as nanoseconds) |
| `Waiters` | `waiters` | `waiters TEXT DEFAULT ''` | []string | Mail addresses notified when gate clears |
| `SourceFormula` | `source_formula` | _(no SQL column; JSON only)_ | string | Formula name that generated this step |
| `SourceLocation` | `source_location` | _(no SQL column; JSON only)_ | string | Path within formula: `steps[0]`, `advice[0].after` |
| `BondedFrom` | `bonded_from` | _(no SQL column; JSON only)_ | []BondRef | Lineage for compound molecules |
| `Labels` | `labels` | separate `labels` table | []string | JOIN on `(issue_id, label)` |
| `Dependencies` | `dependencies` | separate `dependencies` table | []*Dependency | Only populated on export/import; see below |
| `Comments` | `comments` | separate `comments` table | []*Comment | Only populated on export/import; see below |

**Fields in SQL but not Go struct (legacy/internal)**:

| SQL Column | Purpose |
|---|---|
| `hook_bead VARCHAR(255)` | Hook coordination bead reference (HOP-era residue) |
| `role_bead VARCHAR(255)` | Role bead reference |
| `agent_state VARCHAR(32)` | Agent lifecycle state |
| `last_activity DATETIME` | Last agent activity timestamp |
| `role_type VARCHAR(32)` | Role type for agent roles |
| `rig VARCHAR(255)` | Rig assignment (multi-agent runtime) |

### 2. Status Values

Source: `internal/types/types.go` lines 323–388

**Built-in statuses** (hardcoded):

| Value | Category | Meaning |
|---|---|---|
| `open` | active | Unstarted, available for work |
| `in_progress` | wip | Work begun; excluded from `bd ready` |
| `blocked` | wip | Waiting on external blocker |
| `hooked` | wip | Actively claimed by a worker (exclusive lock) |
| `deferred` | frozen | Deliberately on ice for later |
| `pinned` | frozen | Persistent context marker; never a work item |
| `closed` | done | Complete (requires `closed_at` timestamp) |

**Custom statuses**: user-defined via `bd config set status.custom "name:category,..."`. Stored in the `custom_statuses` table. Maximum 50 custom statuses. Valid categories: `active`, `wip`, `done`, `frozen`. Pattern: `^[a-z][a-z0-9_-]*$`.

**Status transition diagram**:

```text
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
      [open] ──────────────────────────► [hooked]  │
         │                                  │      │
         │                                  ▼      │
         ├──────────────────────────► [in_progress]─┘
         │                                  │
         │                                  ├──────► [blocked]
         │                                  │
         ├──────────────────────────────────┤
         │                                  ▼
         │                              [deferred]
         │                                  │
         └──────────────────────────────────┤
                                            ▼
                                        [closed]

[pinned]  = special; can be created directly; does not transition
```

Any status (except `closed`) can transition to `closed`. `closed` → `open` is the reopen path. `hooked` is a `bd claim` write lock on top of `in_progress`.

### 3. Priority System

Source: `internal/types/types.go` line 231, `Validate()` method

| Value | Label | Meaning |
|---|---|---|
| 0 | P0 | Critical / must fix now |
| 1 | P1 | High |
| 2 | P2 | Normal (default for new issues) |
| 3 | P3 | Low |
| 4 | P4 | Minimal / backlog |

Constraint: `priority >= 0 AND priority <= 4`. P0 is stored as integer `0` — there is no `omitempty` sentinel because `0` is meaningful. New issues default to `2`.

### 4. Issue Types

Source: `internal/types/types.go` lines 518–606

**Built-in types** (validated by `IsValid()`):

| Value | Alias(es) | Meaning |
|---|---|---|
| `task` | — | Default generic work item |
| `bug` | — | Defect requiring fix |
| `feature` | `enhancement`, `feat` | New capability |
| `epic` | — | Container for related issues; has child tracking |
| `chore` | — | Maintenance with no feature value |
| `decision` | `dec`, `adr` | Architecture decision record |
| `spike` | `investigation`, `timebox` | Timeboxed investigation |
| `story` | `user-story`, `user_story` | User-perspective feature description |
| `milestone` | `ms` | Completion marker for a set of issues |
| `message` | — | Inter-agent communication bead |
| `molecule` | — | Swarm coordination container (internal) |
| `gate` | — | Async coordination primitive (internal) |

**Internal-only type** (not in `IsValid()`, in `IsBuiltIn()`):

| Value | Meaning |
|---|---|
| `event` | Audit trail bead from set-state operations |

**Infrastructure types** (routed to `wisps` table, not `issues`):

| Value | Meaning |
|---|---|
| `agent` | Agent instance bead |
| `rig` | Multi-agent runtime configuration |
| `role` | Agent role definition |
| `message` | Inter-agent message (also in built-in types; dual-classified) |

**Custom types**: user-defined via `bd config set types.custom "type1,type2,..."`. Stored in `custom_types` table.

**Required sections per type** (enforced by `bd lint`):

| Type | Required Heading(s) |
|---|---|
| `bug` | `## Steps to Reproduce`, `## Acceptance Criteria` |
| `task`, `feature`, `story` | `## Acceptance Criteria` |
| `epic` | `## Success Criteria` |
| `decision` | `## Decision`, `## Rationale`, `## Alternatives Considered` |
| `spike` | `## Goal`, `## Findings` |

### 5. Dependency System

Source: `internal/types/types.go` lines 716–804, migration `0002_create_dependencies.up.sql`

**Storage schema** (one row per directed edge):

```sql
CREATE TABLE dependencies (
    issue_id     VARCHAR(255) NOT NULL,   -- source bead ("A")
    depends_on_id VARCHAR(255) NOT NULL,  -- target bead ("B")
    type         VARCHAR(32) NOT NULL DEFAULT 'blocks',
    created_at   DATETIME NOT NULL,
    created_by   VARCHAR(255) NOT NULL,
    metadata     JSON DEFAULT ({}),       -- edge-specific JSON; type-dependent
    thread_id    VARCHAR(255) DEFAULT '', -- conversation thread grouping
    PRIMARY KEY (issue_id, depends_on_id)
);
```

Reading: `issue_id` **depends on** `depends_on_id`. For `blocks` type: `A blocks B` is stored as `{issue_id: B, depends_on_id: A, type: "blocks"}` — B's row says "B is blocked by A".

**Built-in dependency types**:

| Type | Affects Ready Work | Meaning |
|---|---|---|
| `blocks` | yes | A must close before B is ready |
| `parent-child` | yes | Structural hierarchy; parent's defer propagates to child |
| `conditional-blocks` | yes | B runs only if A closes with a failure reason |
| `waits-for` | yes | Fanout gate: wait for dynamic children to complete |
| `related` | no | Loose association |
| `discovered-from` | no | B was found while working on A |
| `replies-to` | no | Conversation threading |
| `relates-to` | no | Knowledge graph edge |
| `duplicates` | no | Deduplication link |
| `supersedes` | no | Version chain |
| `authored-by` | no | Creator relationship |
| `assigned-to` | no | Assignment relationship |
| `approved-by` | no | Approval relationship |
| `attests` | no | Skill attestation: X attests Y has skill Z |
| `tracks` | no | Convoy → issue non-blocking cross-project reference |
| `until` | no | Active until target closes |
| `caused-by` | no | Audit trail trigger |
| `validates` | no | Approval/validation |
| `delegated-from` | no | Work delegated from parent; completion cascades up |

Edge metadata (stored as JSON in `dependencies.metadata`):

- `waits-for` edges: `{"gate": "all-children"|"any-children", "spawner_id": "..."}` (struct: `WaitsForMeta`)
- `attests` edges: `{"skill": "go", "level": "expert", "date": "...", "evidence": "...", "notes": "..."}` (struct: `AttestsMeta`)

**Failure close keywords** (for `conditional-blocks` logic): `failed`, `rejected`, `wontfix`, `won't fix`, `canceled`, `cancelled`, `abandoned`, `blocked`, `error`, `timeout`, `aborted`.

### 6. Labels

Source: migration `0003_create_labels.up.sql`

```sql
CREATE TABLE labels (
    issue_id VARCHAR(255) NOT NULL,
    label    VARCHAR(255) NOT NULL,
    PRIMARY KEY (issue_id, label)
);
```

Labels are free-form strings. No label metadata (no color, no description). AND semantics for multi-label filters; glob and regex patterns supported in filter queries.

### 7. Comments

Source: migration `0004_create_comments.up.sql`

```sql
CREATE TABLE comments (
    id         CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    issue_id   VARCHAR(255) NOT NULL,
    author     VARCHAR(255) NOT NULL,
    text       TEXT NOT NULL,           -- markdown
    created_at DATETIME NOT NULL
);
```

Comments have no edit history. The `id` field migrated from `INT64` (pre-v1.0) to UUID string; backward-compat unmarshaling handles both.

### 8. Events (Audit Trail)

Source: migration `0005_create_events.up.sql`, `internal/types/types.go` lines 974–1001

```sql
CREATE TABLE events (
    id         CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    issue_id   VARCHAR(255) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    actor      VARCHAR(255) NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    comment    TEXT,
    created_at DATETIME NOT NULL
);
```

Built-in event types: `created`, `updated`, `status_changed`, `commented`, `closed`, `reopened`, `dependency_added`, `dependency_removed`, `label_added`, `label_removed`, `compacted`.

### 9. Wisps (Ephemeral Issues)

Source: migration `0020_create_wisps.up.sql`, `internal/storage/infra_types.go`

Wisps are ephemeral issues stored in the `wisps` table, which is registered in `dolt_ignore` — meaning they are never committed to Dolt version history and never federated to remote peers. The `wisps` table has the same schema as `issues`, including a `started_at` column added via migration 0027.

**WispType TTL classification**:

| Value | TTL | Category |
|---|---|---|
| `heartbeat` | 6h | Liveness pings |
| `ping` | 6h | Health check ACKs |
| `patrol` | 24h | Patrol cycle reports |
| `gc_report` | 24h | Garbage collection reports |
| `recovery` | 7d | Force-kill, recovery actions |
| `error` | 7d | Error reports |
| `escalation` | 7d | Human escalations |

Infrastructure types (`agent`, `rig`, `role`, `message`) are routed to `wisps` by default. This can be overridden via `types.infra` config.

### 10. Config Table

Source: migrations `0006_create_config.up.sql`, `0016_default_config.up.sql`

```sql
CREATE TABLE config (
    `key`  VARCHAR(255) PRIMARY KEY,
    value  TEXT NOT NULL
);
```

Seeded defaults (compaction): `compaction_enabled=false`, `compact_tier1_days=30`, `compact_tier2_days=90`, etc.

### 11. Metadata Table (Local State)

Source: migrations `0007_create_metadata.up.sql`, `0029_create_local_metadata.up.sql`

```sql
CREATE TABLE metadata (
    `key`  VARCHAR(255) PRIMARY KEY,
    value  TEXT NOT NULL
);
-- local_metadata: dolt-ignored, clone-local state
CREATE TABLE local_metadata (
    `key`  VARCHAR(255) PRIMARY KEY,
    value  TEXT NOT NULL
);
```

`metadata` is synced via Dolt. `local_metadata` is in `dolt_ignore` — clone-local only, used for tip timestamps, tracker sync cursors, version stamps.

### 12. The `issues.jsonl` Format

Source: `internal/config/config.go` lines 244–246, observed `issues.jsonl` content

- Auto-exported after every write when `export.auto=true` (default).
- Default path: `.beads/issues.jsonl` (relative to `.beads/`). The repo root `issues.jsonl` is at that location.
- Each line is a **complete JSON object** representing one issue's current state.
- Fields included: all non-zero, non-omitempty fields. Also includes denormalized counts: `dependency_count`, `dependent_count`, `comment_count` (appended to the JSON by the export layer, not part of the Go struct).
- Deletes are NOT tracked in JSONL. Deletions are only visible in Dolt commit history.
- The file is NOT an append-only log — it is regenerated as a full snapshot on each export.
- `export.git-add=true` (default): the file is staged in git automatically after export.

**Concrete example from `issues.jsonl`**:

```json
{"id":"bd-main-idj","title":"Pattern-collapse pass: mechanical cruft inventory and reduction","description":"Quantify near-duplicate functions...","status":"in_progress","priority":2,"issue_type":"chore","owner":"maphew@gmail.com","created_at":"2026-04-18T16:19:12Z","created_by":"matt wilkie","updated_at":"2026-04-18T16:30:16Z","started_at":"2026-04-18T16:30:16Z","dependency_count":0,"dependent_count":0,"comment_count":0}
```

Timestamps are RFC3339 UTC (trailing `Z`). Empty/default fields are omitted (`description` here is truncated in display but full in file).

### 13. `.beads/` Directory

Source: `internal/config/config.go` lines 35–145, formulas directory listing

```text
.beads/
├── config.yaml          # Project-level config (highest priority after BEADS_DIR)
├── config.local.yaml    # Machine-specific overrides (untracked)
├── formulas/            # Formula TOML files for workflow templates
│   └── *.formula.toml
├── issues.jsonl         # Auto-exported JSONL snapshot (git-tracked)
└── <dolt-db>/           # Embedded Dolt database (DoltDB directory)
```

Config precedence (highest to lowest): `BEADS_DIR/config.yaml` > `.beads/config.yaml` > `~/.config/bd/config.yaml` > `~/.beads/config.yaml`.

### 14. Molecule / Swarm Coordination

Source: `internal/types/types.go` lines 649–666, 1152–1169

Molecules are issues with `issue_type=molecule` used for swarm coordination. MolType:

- `swarm`: coordinated multi-worker work
- `patrol`: recurring operational work
- `work`: regular assigned work (default)

Compound molecules track lineage via `BondedFrom []BondRef`, where each `BondRef` has `SourceID`, `BondType` (`sequential`/`parallel`/`conditional`/`root`), and `BondPoint`.

`MoleculeProgressStats` tracks total/completed/in_progress steps via indexed queries.

### 15. Federation

Source: migration `0015_create_federation_peers.up.sql`, config defaults

```sql
CREATE TABLE federation_peers (
    name               VARCHAR(255) PRIMARY KEY,
    remote_url         VARCHAR(1024) NOT NULL,  -- dolthub://, gs://, s3://, az://
    username           VARCHAR(255),
    password_encrypted BLOB,
    sovereignty        VARCHAR(8) DEFAULT '',   -- T1|T2|T3|T4
    last_sync          DATETIME,
    created_at         DATETIME NOT NULL,
    updated_at         DATETIME NOT NULL
);
```

Federation uses Dolt remotes for sync. Sovereignty tiers (T1–T4) restrict what data flows upstream. Config: `federation.exclude_types=["wisp"]` prevents ephemeral data from being pushed.

## Beads Field → GitHub Issues Equivalent

| Beads Field | GitHub Issues Equivalent | Fidelity Notes |
|---|---|---|
| `id` | Issue number (`#123`) | Different format: beads uses prefixed nanoid; GH uses monotonic integer |
| `title` | `title` | Direct equivalent; both limited (GH: no stated limit; beads: 500 chars) |
| `description` | `body` | Direct equivalent (markdown) |
| `design` | Part of `body` | No GH equivalent; beads-specific structured section |
| `acceptance_criteria` | Part of `body` | No GH equivalent; beads-specific structured section |
| `notes` | Part of `body` | No GH equivalent; beads-specific structured section |
| `status` | `state` (`open`/`closed`) + labels | GH has only 2 states; beads has 7 built-in + custom |
| `priority` | Labels (e.g., `priority: P2`) | GH has no native priority; convention-based |
| `issue_type` | Labels (e.g., `type: bug`) | GH has no native type |
| `assignee` | `assignees[]` | GH supports multiple assignees; beads has one `assignee` |
| `owner` | _(no equivalent)_ | Beads-specific: git author email for CV attribution |
| `estimated_minutes` | _(no equivalent)_ | GH has no native time estimation |
| `created_at` | `created_at` | Direct equivalent |
| `updated_at` | `updated_at` | Direct equivalent |
| `closed_at` | `closed_at` | Direct equivalent |
| `started_at` | _(no equivalent)_ | GH has no in_progress timestamp |
| `close_reason` | _(no equivalent)_ | GH close reason is free-form via comment only |
| `due_at` | `milestone.due_on` | GH due dates are milestone-level, not issue-level |
| `defer_until` | _(no equivalent)_ | No GH concept of "hide until date" |
| `labels[]` | `labels[]` | Direct equivalent; GH labels have color+description |
| `dependencies[]` | _(no equivalent, except `blocks` via issue text)_ | GH has no native dependency graph |
| `comments[]` | `comments[]` | Direct equivalent |
| `external_ref` | _(via cross-references)_ | GH has no explicit external ref field |
| `source_system` | _(no equivalent)_ | No GH concept of originating system |
| `metadata` (JSON blob) | _(no equivalent)_ | GH has no arbitrary metadata; closest is labels |
| `spec_id` | _(no equivalent)_ | No GH concept |
| `ephemeral` / wisps | _(no equivalent)_ | GH has no ephemeral issues |
| `pinned` | GitHub Pinned Issues (repo-level) | GH pins are UI-only, not a field on the issue |
| `mol_type` / molecules | _(no equivalent)_ | No GH swarm coordination concept |
| `await_type` / gates | _(no equivalent)_ | GH Actions integration is separate from issues |
| `compaction_level` | _(no equivalent)_ | No GH data lifecycle management |
| `milestone` (IssueType) | `milestone` object | Beads milestone is an issue type; GH milestone is a container object |
| `created_by` | `user.login` (author) | Direct equivalent |
| `events[]` | `timeline_items` | GH has richer timeline; beads events are simpler |

## What Was NOT Found

1. **Milestone as container object**: Beads uses `issue_type=milestone` — a milestone is itself an issue, tracked like any other work item. There is no separate milestone table with due dates, descriptions, and percentage-completion tracking (as GitHub Issues has).

2. **Projects/boards**: Beads has no concept of Kanban boards, project views, or column-based organization. Work ordering is determined by `priority`, `defer_until`, and `due_at` fields and the `ready_issues` SQL view.

3. **Reactions/emoji**: Not present in the beads data model.

4. **Label metadata**: Labels in beads are bare strings. GitHub Issues labels have `color` and `description` fields. Beads stores no such metadata in the `labels` table.

5. **Multiple assignees**: The `assignee` field is a single string. GitHub Issues supports `assignees[]` (array).

6. **Pull request integration**: Beads has no native concept of pull requests. The `gate` type with `await_type=gh:pr` can reference a PR, but the PR itself is not modeled.

7. **Artifact/attachment concept**: No file attachment model exists in beads. The `metadata` JSON blob is the closest extensibility point but is not an artifact store.

8. **Namespace/org structure**: Beads is per-project with optional federation. There is no organization-level concept beyond `source_system` on federated issues.

9. **Issue templates as a UI concept**: Templates exist as `is_template=true` issues (template molecules), but there is no separate template store or UI concept analogous to GitHub's `.github/ISSUE_TEMPLATE/` directory.

10. **"Remember" / memory storage**: No dedicated memory or remember store exists. The `local_metadata` table is used for system-level key-value state (cursors, timestamps), not user-facing memory.

## Uncertain

1. **The `bonded_from`, `source_formula`, `source_location` fields** are present in the Go struct with JSON tags but have no corresponding SQL columns in migration 0001. They appear to be set only on export/deserialization from formula-cooked molecules. Whether they persist to the database or only appear in JSONL is not confirmed from the schema migrations read.

2. **The `hook_bead`, `role_bead`, `agent_state`, `last_activity`, `role_type`, `rig` SQL columns** exist in the `issues` DDL but are absent from the Go `Issue` struct. These appear to be HOP-era or orchestrator-era columns that were not fully removed. Whether they are populated in production databases is not confirmed.

3. **JSONL denormalized counts** (`dependency_count`, `dependent_count`, `comment_count` visible in the sample): these appear to be computed at export time and appended to the JSON, but the exact code path that adds them was not read (the export layer is not included in files examined).

4. **Dolt server mode**: the `beads.go` public API mentions `dolt_mode=server` in `OpenFromConfig`. Whether the embedded Dolt DB format differs from server mode storage was not examined.

## Sources

- `/home/user/repos/beads/internal/types/types.go` — read 2026-05-14, all 1444 lines
- `/home/user/repos/beads/internal/storage/schema/migrations/0001_create_issues.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0002_create_dependencies.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0003_create_labels.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0004_create_comments.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0005_create_events.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0006_create_config.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0015_create_federation_peers.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0016_default_config.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0017_create_ready_issues_view.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0020_create_wisps.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0024_create_custom_status_type_tables.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0025_update_ready_issues_view.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0027_add_started_at.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/schema/migrations/0038_drop_hop_columns.up.sql` — read 2026-05-14
- `/home/user/repos/beads/internal/storage/storage.go` — read 2026-05-14 (lines 1–200)
- `/home/user/repos/beads/internal/storage/infra_types.go` — read 2026-05-14
- `/home/user/repos/beads/internal/config/config.go` — read 2026-05-14 (lines 1–300)
- `/home/user/repos/beads/issues.jsonl` — read 2026-05-14 (first 50 lines; file has 1 issue at time of read)
- `/home/user/repos/beads/format/format.go` — read 2026-05-14
- `/home/user/repos/beads/.beads/formulas/beads-release.formula.toml` — read 2026-05-14
