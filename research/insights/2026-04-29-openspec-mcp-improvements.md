# Improvement Proposals: OpenSpec MCP

**Research entry**: ./research/mcp-ecosystem/openspec-mcp.md
**Generated**: 2026-04-29
**Patterns assessed**: 5
**Backlog items created**: 2 (issues: #1, #2)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: State Machine Enforcement for Feature Change Lifecycle

**Source pattern**: "State progression: `draft` -> `pending_approval` -> `approved` -> `implementing` -> `completed` -> `archived`. Rejection cycles back to `draft` for revision, preserving the audit trail."

**Local system**: `plugins/development-harness/skills/backlog/SKILL.md` and `plugins/development-harness/skills/complete-implementation/SKILL.md`

**Confidence**: High

**Impact**: High

**Backlog**: #1 created

### Current state

The backlog lifecycle implements state transitions via GitHub issue labels (`status:groomed`, `status:in-progress`, `status:done`) but does not enforce a strict state machine. The `backlog_close` tool accepts any terminal reason (`duplicate`, `out_of_scope`, `superseded`, `wontfix`, `blocked`) without validation of prior state or audit trail. The SAM task state model (`Task.status`) supports `{not-started, in-progress, complete, blocked, deferred, skipped}` but rejection (returning to draft) is not modeled — once a task is blocked or rejected, there is no structured recovery path.

File: `plugins/development-harness/skills/backlog/SKILL.md` (lines 22-142) documents `backlog_close` and `backlog_resolve` operations without mentioning state validation or audit trail preservation on rejection.

### Target state

Implement explicit state machine enforcement for backlog items similar to OpenSpec's draft → pending_approval → approved → implementing → completed → archived cycle. The machine should:

1. Only allow transitions from valid prior states (e.g., cannot approve from `draft` without first moving to `pending_approval`)
2. Log all state transitions with timestamp, actor, and reason in a structured audit trail stored in the GitHub issue body or a dedicated state history comment
3. Support rejection cycles (e.g., from `pending_approval` back to `draft`) with audit trail preservation
4. Enforce that terminal states (`archived`/`done`) cannot be exited

File modifications: Add state validation logic to `backlog_core/backend_protocol.py` `BacklogBackend.update_status()` method. Add state transition diagram and rules to `docs/backlog-item-lifecycle.md`.

### Measurable signal

Run `mcp__plugin_dh_backlog__backlog_update(selector='test-item', status='approved')` when item is in `draft` state.

Before fix: Operation succeeds (no state validation).

After fix: Operation fails with error message "Cannot transition from draft to approved. Valid transitions: [pending_approval]."

All state transitions (creation, status changes, rejection cycles) appear as timestamped entries in a state history section within the GitHub issue body or a dedicated comment thread.

---

## Improvement 2: Explicit Review Threads with Resolution State

**Source pattern**: "`openspec_add_review` / `openspec_reply_review` / `openspec_resolve_review` / `openspec_list_reviews` -- threaded review system"

**Local system**: `plugins/development-harness/skills/complete-implementation/SKILL.md` and `dh:code-reviewer` agent

**Confidence**: High

**Impact**: Medium

**Backlog**: #2 created

### Current state

The `dh:code-reviewer` agent produces findings in SAM task format but has no structured mechanism for human acknowledgment or resolution of individual findings. The `complete-implementation` skill dispatches a code-review task (T1) and reads the agent output, but the output is a single markdown report. There is no structured thread model where:

1. Each finding can be replied to with clarification or counter-evidence
2. Finding resolution state (open, replied-to, acknowledged, resolved) is tracked
3. The reviewer can iterate on findings with the implementing agent

File: `plugins/development-harness/skills/complete-implementation/SKILL.md` (lines 173-179) contains the post-dispatch action for T1 Code Review: "No follow-up extraction (proportional gates do not generate follow-ups)" — treating code review as a one-way read.

### Target state

Implement threaded review state tracking where:

1. Each code-reviewer finding is registered as a GitHub issue comment with unique ID
2. Findings support state transitions: `open` → `replied` → `acknowledged` → `resolved`
3. The implementing agent can reply to a finding comment with context or corrections
4. The `complete-implementation` skill can query review state and block progression until all findings reach `resolved` state
5. Audit trail of all replies and state transitions is visible in the GitHub issue comment thread

This maps OpenSpec's `resolve_review` pattern to github issue comment threading for findings.

File modifications: Add `review_thread_state` enum and comment-threading logic to `backlog_core/backend_protocol.py`. Extend `complete-implementation` T1 post-dispatch to read code review comment threads and validate all findings are resolved before allowing completion.

### Measurable signal

Run the `complete-implementation` skill on an issue with code review findings.

Before fix: Skill reads the code-review task output (markdown report) and proceeds to next task regardless of findings status.

After fix: Skill queries the code review GitHub issue comment thread, identifies all findings registered as comments with state `open` or `replied`, and blocks progression with message "3 code review findings await resolution. Implementing agent must reply to findings in comment threads before moving to next phase."

After findings are resolved (state = `resolved`), progression continues. Audit trail of all finding state changes is visible in the GitHub issue.

---

## Improvement 3: Cross-Plugin Documentation Aggregation via Artifact Conventions

**Source pattern**: "Cross-service document aggregation (`openspec_list_cross_service_docs`, `openspec_read_cross_service_doc`) unified through a single MCP interface. Configured via YAML frontmatter in `proposal.md` with `crossService.rootPath`, document list, and `archivePolicy` (snapshot or reference)."

**Local system**: `plugins/development-harness/docs/plan-artifact-lifecycle.md` and artifact conventions in `plugins/development-harness/skills/development-harness/references/artifact-conventions.md`

**Confidence**: Medium

**Impact**: Medium

**Backlog**: Deferred — confidence medium: requires clarification on whether the claude_skills plugin ecosystem should declare cross-plugin doc roots in artifact frontmatter or via a centralized manifest

### Current state

The artifact conventions define artifact types (`feature-context`, `architect`, `task-plan`, etc.) and store them under `~/.dh/projects/{slug}/plan/`. Multi-plugin documentation exists in separate plugin directories (`plugins/plugin-name/skills/`, `plugins/plugin-name/docs/`) with no unified discovery mechanism. An orchestrator cannot query "all architecture documentation across all plugins for this codebase" without manually traversing the filesystem.

File: `plugins/development-harness/skills/development-harness/references/artifact-conventions.md` (lines 1-50) defines artifact storage and naming but does not address cross-plugin discovery.

### Target state

Implement a discoverable cross-plugin documentation registry where:

1. Each plugin declares its documentation roots in a `crossService.rootPaths` field in its `plugin.json` manifest or a dedicated `docs-manifest.yaml`
2. The artifact MCP server can query and list all documentation files across declared plugins
3. An orchestrator can call a unified `artifact_list_cross_plugin_docs(pattern)` to find all documentation matching a pattern (e.g., all architecture specs across plugins)
4. Archive policy (snapshot vs live reference) is declared per-root

This requires:

- Modification to `plugin.json` schema or introduction of a new manifest type
- MCP server enhancement to discover and aggregate plugin docs
- Testing across plugins to verify cross-plugin references resolve correctly

### Measurable signal

Call `list_cross_plugin_docs(pattern="architecture")` and receive a unified list of architecture files from all registered plugin `docs/` and `skills/*/references/` directories.

Before fix: No such tool exists; each plugin's documentation is isolated.

After fix: Tool returns:

```
plugin-creator:docs/architecture.md
development-harness:docs/sdlc-layers/layer-0/context-fit-complexity.md
python3-development:docs/architecture.md
```

---

## Improvement 4: Real-Time Task Progress Dashboard with WebSocket Updates

**Source pattern**: "Real-Time Web Dashboard — Fastify-based HTTP server with WebSocket push for live updates on all pages. Routes: overview, Kanban board, change listings, QA runner, context analysis, approval queue."

**Local system**: `plugins/development-harness/skills/implementation-manager/` and task status tracking

**Confidence**: Low

**Impact**: Low

**Backlog**: Deferred — confidence low: WebSocket integration for real-time progress requires architectural decision (standalone HTTP server vs integration with existing harness) and is already provided by external dashboards (GitHub project boards, Linear); OpenSpec's dashboard is a nice-to-have for internal development visibility

### Current state

Task execution progress is tracked in SAM task files (`status` field) and task hook callbacks write to `task_status_hook.py`. There is no real-time Web dashboard — progress visibility requires querying the task files or GitHub Issues manually. Implementers and orchestrators must poll to see current status.

File: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py` writes task status updates but has no publish mechanism for external listeners.

### Target state

Implement a lightweight WebSocket-based dashboard that:

1. Listens for task status updates from the status hook
2. Broadcasts status changes in real-time to connected Web clients
3. Displays a Kanban-like board showing task state, progress bars, and recent activity
4. Provides a URL that orchestrators can share for visibility during feature implementation

This is a quality-of-life improvement with no impact on feature correctness or completion.

### Measurable signal

Open `http://localhost:3001/dashboard` during feature implementation. Task state changes appear in real-time without requiring page refresh.

---

## Improvement 5: MCP Tool as Explicit State Transition Declaration

**Source pattern**: "State machine enforcement via MCP tools: each state transition is a distinct named tool (e.g., `request_approval`, `approve_change`) rather than a generic 'update status' call, making agent intent explicit and auditable"

**Local system**: `plugins/development-harness/skills/backlog/SKILL.md` and `complete-implementation` skill

**Confidence**: Medium

**Impact**: Medium

**Backlog**: Deferred — confidence medium: requires decision on whether to split `backlog_update` into explicit tools (`request_approval`, `approve_change`, etc.) or add operation enums to the existing tool; OpenSpec approach is cleaner but requires more MCP tools

### Current state

State transitions in the backlog use a generic `backlog_update(selector, status=...)` call. An agent calling `backlog_update(selector='#42', status='approved')` provides no semantic clarity about whether it is the approver, the implementer, or the task-worker making the change.

File: `plugins/development-harness/skills/backlog/SKILL.md` (lines 144-150) documents `backlog_update` as a single catch-all tool.

### Target state

Implement explicit-intent MCP tools for state transitions:

- `backlog_request_approval(selector)` — ask for review/approval
- `backlog_approve_change(selector, reason)` — approve change (requires reviewer role)
- `backlog_reject_change(selector, reason)` — reject change
- `backlog_mark_implementing(selector)` — task-worker starts work
- `backlog_mark_done(selector, summary, findings)` — task-worker completes

Each tool is auditable — the MCP server logs which tool was called (not just a generic status update) and can enforce role-based permissions (e.g., only humans can call `backlog_approve_change`).

### Measurable signal

Agent code changes from:

```
backlog_update(selector='#42', status='approved')
```

to:

```
backlog_approve_change(selector='#42', reason='Code review passed, ready to merge')
```

The MCP server logs the explicit intent tool, making the audit trail more readable.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Real-Time Web Dashboard | Low | External dashboards (GitHub Projects, Linear, project management tools) already provide real-time visibility; integration with existing harness requires architectural decision that may not be worth the added complexity |
| MCP Tool as Explicit State Transition | Medium | Requires decision: split `backlog_update` into 5+ explicit tools (cleaner, more auditable, higher MCP surface) vs add operation enum to single tool (simpler, fewer tools). Need user feedback on preference. |
| Cross-Plugin Documentation Aggregation | Medium | Need clarification: should plugin documentation roots be declared in `plugin.json`, a dedicated manifest, or auto-discovered? Current design (filesystem traversal) works but lacks unified discovery. Worth revisiting after plugin ecosystem stabilizes. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Approval Workflow State Machine (draft → pending_approval → approved → implementing → completed → archived) | Not skipped; implemented as Improvement 1 |
| Review System with Threading | Not skipped; implemented as Improvement 2 |
| Change creation/validation/archive lifecycle | Already covered in `backlog_close`, `backlog_resolve`, and SAM task lifecycle. New state machine (Improvement 1) extends this with audit trail. |

