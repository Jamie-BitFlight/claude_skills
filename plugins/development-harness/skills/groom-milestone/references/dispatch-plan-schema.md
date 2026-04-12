# Dispatch Plan Schema

The dispatch plan is persisted by `/groom-milestone` via the `dispatch_create_plan` MCP tool to `plan/milestone-{N}-dispatch.yaml` and read by `/work-milestone` to drive wave-based parallel execution.

## Full Schema Example

```yaml
milestone:
  number: 3
  title: "v1.1 — Milestone Workflow"
  integration_branch: "milestone/3-v1.1-milestone-workflow"

conflict_groups:
  - group_id: 1
    reason: "Both touch plugins/development-harness/skills/"
    items: ["SAM error recovery", "Backlog MCP validation"]
  - group_id: 2
    reason: "Both modify .claude/rules/"
    items: ["Rule consolidation", "Linting exceptions update"]

waves:
  - wave: 1
    parallel: true
    items:
      - title: "Add auth middleware"
        issue: 42
        priority: P0
        conflict_group: null
        depends_on: []
      - title: "Plugin docs update"
        issue: 45
        priority: P1
        conflict_group: null
        depends_on: []
      - title: "SAM error recovery"
        issue: 38
        priority: P0
        conflict_group: 1
        depends_on: []

  - wave: 2
    parallel: true
    items:
      - title: "Backlog MCP validation"
        issue: 39
        priority: P1
        conflict_group: 1
        depends_on: [38]
      - title: "Rule consolidation"
        issue: 50
        priority: P2
        conflict_group: 2
        depends_on: []

  - wave: 3
    parallel: false
    items:
      - title: "Linting exceptions update"
        issue: 51
        priority: P2
        conflict_group: 2
        depends_on: [50]

quality_gates:
  pre_merge:
    - "uv run prek run --all-files"
    - "uv run ruff check ."
  post_merge:
    - "uv run pytest tests/ -x"
```

## Field Definitions

### `milestone`

| Field | Type | Description |
|---|---|---|
| `number` | integer | GitHub milestone number, matches the argument passed to `/groom-milestone` |
| `title` | string | Milestone title from GitHub |
| `integration_branch` | string | Branch name for isolated integration — format `milestone/{N}-{slug}` |

### `conflict_groups`

Items that touch overlapping files must be serialized. They are assigned to the same conflict group and dispatched in separate waves.

| Field | Type | Description |
|---|---|---|
| `group_id` | integer | Unique group identifier referenced by items |
| `reason` | string | Human-readable explanation of the overlap (e.g., shared directory) |
| `items` | list of strings | Item titles belonging to this group |

Items with `conflict_group: null` have no file overlap with any other item and may execute fully in parallel.

### `waves`

Waves define execution order. Items within a wave start simultaneously (when `parallel: true`). Wave N+1 does not start until all items in wave N are merged.

| Field | Type | Description |
|---|---|---|
| `wave` | integer | Wave sequence number, starting at 1 |
| `parallel` | boolean | Whether items in this wave may run concurrently |
| `items` | list | Item entries for this wave |

### Wave item fields

| Field | Type | Description |
|---|---|---|
| `title` | string | Backlog item title — used as selector for `backlog_view` |
| `issue` | integer | GitHub issue number |
| `priority` | string | Priority label — P0, P1, or P2 |
| `conflict_group` | integer or null | References `conflict_groups[].group_id`; null means no overlap |
| `depends_on` | list of integers | Issue numbers that must be merged before this item dispatches |

### `quality_gates`

Commands run by `/work-milestone` before and after merging items to the integration branch.

| Field | Type | Description |
|---|---|---|
| `pre_merge` | list of strings | Commands run in the worktree before merging to integration branch |
| `post_merge` | list of strings | Commands run on the integration branch after all waves complete, before landing to main |

All commands must exit 0 for the gate to pass. Non-zero exit blocks the merge.

## Ordering Rules

Wave assignment follows these rules in priority order:

1. Items with `depends_on` entries wait until all listed issues are merged — they appear in a later wave than their dependencies.
2. Items sharing a `conflict_group` appear in consecutive waves (never the same wave), ordered by priority label (P0 before P1 before P2).
3. Items with `conflict_group: null` and no `depends_on` entries are placed in wave 1.
4. `validate_plan_integrity()` enforces these rules before the file is written — it rejects plans where a dependency issue appears in a later wave than the item that depends on it.

## Integration Branch Naming

Format: `milestone/{N}-{slug}`

Where `{slug}` is derived from the milestone title — lowercase, spaces replaced with hyphens, special characters stripped.

Example: milestone 3 titled "v1.1 — Milestone Workflow" produces `milestone/3-v1.1-milestone-workflow`.

## Worktree Agent Execution Model

This section clarifies how `/work-milestone` uses the dispatch plan when spawning worktree agents. No schema fields are added — the existing wave/item structure contains everything the orchestrator needs.

**Isolation mode is hardcoded, not schema-configured.** Every item dispatches via `Agent(isolation: "worktree")`. There is no per-item field to select isolation mode or agent type. All worktree agents use the same prompt template; per-item specialization is via task content and skills, not agent configuration.

**The orchestrator passes references, not data.** The dispatch plan provides the issue number, title, and integration branch name. The worktree agent self-discovers description, acceptance criteria, task list, and skills by calling `backlog_view` and `sam_task(action='read')` after spawning. The orchestrator does not pre-read item data before dispatch.

**Skills come from SAM task metadata, discovered by the agent.** The worktree agent reads the SAM plan via `sam_task(action='read')` and loads skills from the `skills` field in task metadata. The dispatch plan's wave/item fields do not carry skill metadata, and the orchestrator does not aggregate skills before spawning.

**Each item executes in an isolated worktree.** The worktree agent receives the issue number, integration branch, quality gate commands, and prior-wave relay content. It self-discovers item description, acceptance criteria, task list, and skills via MCP. The agent executes work directly without delegating to subagents (worktree agents cannot spawn further agents).

**Conflict groups handle serialization; no runtime coordination fields are needed.** Items in the same wave are guaranteed non-overlapping by the conflict group analysis performed during `/groom-milestone`. Worktree agents do not communicate with each other. The orchestrator relays context between waves via the discovery relay mechanism.

## Creating Plans via MCP

Use the `dispatch_create_plan` MCP tool (on the backlog server) to create or update dispatch plans. The `plan` parameter accepts a typed DispatchPlan object matching the schema above.

**Parameters:**

- `milestone_number` — GitHub milestone number; the tool writes to `plan/milestone-{N}-dispatch.yaml`
- `plan` — typed DispatchPlan object containing the full dispatch plan (accepts both kebab-case and snake_case keys)
- `overwrite` — Allow replacing an existing plan file; set to `True` when re-grooming (default: `False`)
- `validate` — Run `validate_plan_integrity()` after writing and include results in response (default: `True`)
- `issue` — Optional GitHub issue number; when provided, auto-registers the plan file as a `dispatch-plan` artifact

**Response:** Returns `milestone_number`, `wave_count`, `item_count`, `is_valid`, `errors`, `warnings`, and `messages`. On error, the response contains an `error` key with a description.
