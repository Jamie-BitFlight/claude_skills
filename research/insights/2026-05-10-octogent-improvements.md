# Improvement Proposals: Octogent

**Research entry**: ./research/agent-frameworks/octogent.md
**Generated**: 2026-05-10
**Patterns assessed**: 10
**Backlog items created**: 2 (issues: #2238, #2239)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 6

---

## Improvement 1: Todo-driven worker prompt generation from markdown checkbox files

**Source pattern**: "todo.md contains markdown checkbox items. The runtime parses these items and generates worker prompts from them. Incomplete items automatically become worker assignments in swarm runs, and terminal IDs like `<tentacle-id>-swarm-0` are derived from parsed item indices." — Octogent README extract, "Todo-Driven Delegation" section
**Local system**: ./.claude/skills/swarm-patterns/SKILL.md (Pattern 3 — Swarm Self-Organizing) and ./plugins/development-harness/skills/dispatch/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2238 created

### Current state

The swarm patterns in `.claude/skills/swarm-patterns/SKILL.md` Pattern 3 (Self-Organizing) require the orchestrator to write per-task `TaskCreate({ subject, description, activeForm })` calls before spawning workers. There is no mechanism to read a markdown file containing checkbox items (`- [ ] description`) and auto-generate `TaskCreate` calls plus a worker prompt template from each unchecked item. Lines 109-114 show the orchestrator must manually call `TaskCreate` once per file to review. Line 416 of Workflow 3 ("// === CREATE TASK POOL ... For each file to review") explicitly leaves task list construction as a manual orchestrator step. The dispatch skill (`plugins/development-harness/skills/dispatch/SKILL.md`) operates on already-decomposed SAM task YAMLs, not free-form markdown checkbox lists.

### Target state

A new skill `swarm-from-markdown` (or a new section in `swarm-patterns/SKILL.md` referencing a helper script) exposes a workflow: given a path to a markdown file, parse all unchecked `- [ ]` items via `marko` AST walking, emit one `TaskCreate` call per item with the item text as `subject`/`description`, then spawn N workers using a parameterized self-organizing prompt template. Output is the resulting `TaskList()` after creation, plus the team name. Worker IDs derive from item index (`worker-0`, `worker-1`, ...). The skill is invokable as `/swarm-from-markdown <path-to-md> [--workers N]`.

### Measurable signal

File `.claude/skills/swarm-from-markdown/SKILL.md` (or equivalent helper section in `swarm-patterns/SKILL.md`) exists with a worked example showing input markdown and the resulting `TaskCreate` calls. A reference script (e.g., `scripts/markdown_to_task_pool.py`) parses a sample markdown file and emits the JSON command sequence; running it on a fixture markdown file with 5 unchecked items produces 5 `TaskCreate` invocations. The SKILL.md cites octogent's todo-driven delegation as the source pattern.

---

## Improvement 2: Scoped workstream context folder ("tentacle") for durable agent handoffs

**Source pattern**: "A tentacle is a folder under `.octogent/tentacles/<tentacle-id>/` that stores agent-readable markdown files. The important part is that the folder is agent-facing. It is the durable context that a terminal agent can read, edit, and hand off to another terminal." — Octogent docs/concepts/tentacles.md as quoted in research entry
**Local system**: ./plugins/development-harness/CLAUDE.md (State Management section) and ./plugins/development-harness/skills/start-task/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the closest local equivalent (`~/.dh/projects/{slug}/context/active-task-{session-id}.json`) is session-scoped and ephemeral. The proposed "tentacle"-style folder would be workstream-scoped and durable, but it overlaps significantly with the artifact-manifest system (`artifact_register`/`artifact_read` keyed to issue numbers). Further investigation is needed to determine whether issue-number-keyed artifacts already provide durable scoped context, or whether a separate workstream-scoped folder model would close a real gap.

### Current state

`~/.dh/projects/{slug}/context/active-task-{session-id}.json` exists as ephemeral per-session task context (created by `start-task/SKILL.md` step 4 via `sam_active_task` MCP). The artifact manifest system (CLAUDE.md "Artifact Manifest System") keys all durable artifacts to a single GitHub issue number — so artifacts for a feature are scoped to one issue, not to a free-form workstream label. There is no agent-readable folder named after an arbitrary workstream slug (e.g., `auth-system`, `api-runtime`) that survives session restarts and is shared across multiple agents working concurrently on the same workstream without each having its own issue.

### Target state

A scoped-workstream context folder model (e.g., `~/.dh/projects/{slug}/workstreams/<workstream-id>/`) containing at minimum `CONTEXT.md` and `todo.md`, with a registration MCP tool (`workstream_register`) and a read tool (`workstream_read`). Multiple agents working on parallel workstreams can read/write their own folder without colliding, and the folder survives across sessions. The artifact-manifest system's issue-keyed model continues to handle issue-scoped durable artifacts; the workstream model handles workstreams that span multiple issues or have no issue yet.

### Measurable signal

Confidence-deferral resolution would require: (a) reading the artifact-manifest implementation to confirm whether free-form `artifact_type` values (without an issue number) are supported and (b) interviewing the user on whether a multi-issue workstream is a real workflow. If both confirm the gap, then the proposal becomes a backlog item with target-state: a registered MCP tool plus a folder under `~/.dh/projects/{slug}/workstreams/`.

---

## Improvement 3: Idle-injection durable channel queue for inter-agent messages

**Source pattern**: "Channel Queue: in-memory inter-agent messaging system that injects messages when targets become idle" — Octogent research entry, Technical Architecture > API Application section, with the limitation noted as "No Persistence for Channel Messages: Inter-agent messages are stored in memory."
**Local system**: ./.claude/skills/swarm-operations/SKILL.md (SendMessage section)
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence low: Octogent's own README notes that channel messages are stored in memory and are NOT durable, advising agents to "write to tentacle markdown files instead of relying on channel message history." This is a self-documented limitation of Octogent, not a pattern Octogent solved. The actionable improvement direction (durable inter-agent messaging) has merit but its detailed mechanism cannot be derived from Octogent because Octogent does not implement it. Promoting this to a backlog item would be inferring beyond the source. The local repo's existing alternative — durable artifact-register handoff via `artifact_register(issue_number, type, content=...)` — is closer to a "durable handoff" than Octogent's channel queue.

### Current state

Local: `SendMessage` in swarm-operations is the in-session messaging primitive. Messages are scoped to the current swarm session and the team's lifetime. Once `TeamDelete()` is called or the orchestrator session ends, message history is not preserved. The canonical durable handoff mechanism in this repo is the artifact-register system.

### Target state

Cannot be defined from the source pattern alone — see backlog deferral reason above.

### Measurable signal

N/A — proposal not promoted.

---

## Improvement 4: Per-task PTY transcript JSONL persistence keyed by session and task

**Source pattern**: "Transcript Persistence: captures agent conversations to `.octogent/projects/<project-id>/state/transcripts/*.jsonl`" — Octogent research entry, Technical Architecture > API Application section
**Local system**: ./plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: High
**Impact**: Low
**Backlog**: #2239 created

### Current state

`task_status_hook.py` lines 654-720 already include `_extract_prompt_from_transcript` and `_extract_session_id_from_transcript` functions that READ the SubagentStop transcript JSONL to extract a single field (initial prompt and session_id). The hook does NOT copy or persist a snapshot of the transcript to the DH state directory. Transcripts live only at the Claude Code default path (`~/.claude/projects/...`) and are not aggregated under `~/.dh/projects/{slug}/state/transcripts/` keyed by SAM task ID. When investigating "what did agent X do during task T", the only path is to crawl the raw `~/.claude/projects/...` JSONLs, which are not indexed by task ID.

### Target state

`task_status_hook.py` SubagentStop handler additionally writes (or hard-links) the agent's transcript JSONL to `~/.dh/projects/{slug}/state/transcripts/{plan-id}/{task-id}-{session-id}.jsonl` after extracting the existing fields. The transcript is written once on SubagentStop. A new MCP tool `task_transcript_read(plan, task, session_id=None)` exposes the path for query.

### Measurable signal

Run an agent against a SAM task; on SubagentStop, the file `~/.dh/projects/{slug}/state/transcripts/{plan-id}/{task-id}-{session-id}.jsonl` exists and contains the same content as the original transcript at `~/.claude/projects/...`. `mcp__plugin_dh_sam__task_transcript_read(plan="P1", task="T1")` returns a path or content, not an error.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Tentacle scoped workstream folder | medium | The artifact-manifest system covers issue-keyed durable context; whether a workstream-keyed model adds material value requires user input or further investigation of artifact-manifest free-form keys |
| Idle-injection durable channel queue | low | Octogent itself does not implement durable channel messaging — the README explicitly notes the channel is in-memory and recommends writing to tentacle files instead. Cannot derive a target mechanism from the source |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Workspace isolation modes (shared vs worktree) | Already implemented — `plugins/development-harness/skills/work-milestone/SKILL.md` Step 5a creates `git worktree add worktrees/{slug}` per dispatch wave item; `plan/dispatch-state.db` tracks worktree associations |
| Hook-based state integration (agent activity, tool use, idle, stops) | Already implemented — `plugins/development-harness/hooks/hooks.json` registers PostToolUse, SubagentStop, SessionStart, SessionEnd, Stop hooks; `task_status_hook.py` consumes them |
| Stable per-project ID with state directory | Already implemented — `~/.dh/projects/{slug}/` derived from absolute project path with `/` → `-`; documented in `plugins/development-harness/CLAUDE.md` State Management section |
| Maximum live session cap (32 PTYs) | Already covered procedurally — `dispatch_wave_start` and `dispatch_spawn` (in `plugins/development-harness/scripts/run_backlog_server.py`) bound parallelism by wave size set at grooming time |
| Domain-layer ports-and-adapters architectural separation | Already covered — the harness uses backend protocols (`BacklogBackend`, `TaskBackend`) for storage abstraction, documented in `plugins/development-harness/CLAUDE.md` Backend Providers section. Octogent's pattern is at a higher architectural granularity (UI/API/domain split) that does not apply to this skills-and-MCP repo |
| Web UI dashboard ("Deck and Canvas") | Out of scope — this repo is a Claude Code marketplace plugin collection, not a host for dashboard applications. A Node.js/Vite SPA would be incompatible with the plugin distribution model |
| Local API + WebSocket transport | Out of scope — same reason as Web UI; the repo's communication primitives are MCP tools and Claude Code hooks, not HTTP/WebSocket servers |
| Pre-release / single-contributor / npm-not-published caveats | Not patterns — these are limitations of Octogent itself, not patterns to integrate |

---

## Backlog Creation Record

Backlog items are created for the two High-confidence proposals (Improvements 1 and 4). Issue numbers are recorded inline in each proposal's `**Backlog**` field after creation completes. Medium and Low confidence proposals are intentionally not promoted to the backlog per the workflow's confidence-gating rule.
