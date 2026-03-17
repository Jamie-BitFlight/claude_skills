# Improvement Proposals: Agent Deck

**Research entry**: ./research/developer-tools/agent-deck.md
**Generated**: 2026-03-17
**Patterns assessed**: 10
**Backlog items created**: 1 (issues: #776)
**Deferred (low confidence)**: 4
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Hook-based instant status detection via SQLite event store

**Source pattern**: "Agent Deck uses tool-specific hooks (Claude hooks, Gemini hooks, Codex hooks) installed into each tool to detect state changes and write to SQLite. This pattern is more reliable than polling file timestamps and enables instant status updates without excessive polling overhead" (Patterns Worth Adopting, bullet 1)
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the local hook system already writes status changes to task YAML files on every SubagentStop and PostToolUse event. Agent Deck's SQLite approach provides faster indexed queries, but it is unclear whether the current YAML-based approach causes observable query latency in practice. Would need profiling data (e.g., `sam status` latency at >50 tasks) to confirm a real gap.

### Current state

`task_status_hook.py` writes status changes (COMPLETE, LastActivity) directly into YAML frontmatter of task files via `sam_schema.core.query.update_status` and `sam_schema.core.query.update_plan_fields`. The `sam` CLI reads these YAML files to compute status and readiness. There is no indexed event store -- every status query re-parses all task YAML files in the plan directory.

### Target state

A lightweight SQLite event store (or append-only log) that `task_status_hook.py` writes to on every status transition, alongside the existing YAML write. The `sam status` and `sam ready` commands read from the event store for O(1) lookups instead of re-parsing all task files. YAML files remain the source of truth; SQLite is a read-optimization cache rebuilt on startup.

### Measurable signal

Run `uv run sam status P{N}` on a plan with 20+ tasks. Measure wall-clock time before and after the SQLite cache. Target: sub-100ms for status queries regardless of task count.

---

## Improvement 2: Session forking with context inheritance for multi-branch exploration

**Source pattern**: "Forking a session with full history enables exploring multiple solution branches without losing the original approach; applicable to any multi-decision AI workflow" (Patterns Worth Adopting, bullet 2)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the implement-feature loop dispatches tasks sequentially. Forking a session to explore alternative approaches is a fundamentally different interaction model that would require changes to Claude Code's session management, not just to local skill files. The local system cannot implement this without external session management capabilities.

### Current state

`/implement-feature` dispatches one task at a time via the Agent tool. When a task produces a suboptimal result, the only recovery is to re-run the task or create a follow-up task. There is no mechanism to fork the current conversation state to explore an alternative approach while preserving the original.

### Target state

Not actionable within current architecture. Session forking is an Agent Deck feature that operates at the terminal/tmux layer, outside the scope of skill files.

### Measurable signal

N/A -- architectural incompatibility.

---

## Improvement 3: MCP socket pooling for shared MCP server processes

**Source pattern**: "The MCP socket pool reduces memory by 85-90% and auto-recovers from crashes in 3 seconds via a reconnecting proxy; this pattern applies to any resource-intensive service shared across multiple clients" (Patterns Worth Adopting, bullet 3)
**Local system**: .claude/skills/fastmcp-creator/SKILL.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: this repo creates MCP servers (via fastmcp-creator) but does not operate a multi-session MCP client environment. Socket pooling is relevant when running many concurrent Claude Code sessions sharing the same MCP servers, which is Agent Deck's domain, not a local skill concern. The local system has no MCP client pool to optimize.

### Current state

The fastmcp-creator skill generates standalone MCP servers. Each server runs as an independent process. There is no multi-session client pooling because the repo does not manage multiple concurrent Claude Code sessions.

### Target state

Not actionable within current architecture. Socket pooling is an external session manager concern, not a skill/plugin concern.

### Measurable signal

N/A -- architectural incompatibility.

---

## Improvement 4: Conductor pattern -- persistent monitor session for child agent orchestration

**Source pattern**: "Conductors are persistent Claude Code sessions that monitor child sessions, auto-respond when confident, and escalate to Telegram/Slack for remote control" (Problem Addressed table, row 5) and "Conductors are Claude Code sessions that monitor other sessions; this creates a meta-orchestration pattern where Claude Code can be used to build supervisors for Claude Code workloads" (Integration Opportunities, bullet 3)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md, .claude/skills/swarm-patterns/SKILL.md
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: the local `/implement-feature` skill already acts as an orchestrator that dispatches tasks and monitors completion via hooks. Agent Deck's conductor adds heartbeat monitoring with configurable intervals and parent nudges on status transitions, which is conceptually similar to the existing stall-detection backlog items (#87, #448). The specific conductor pattern (persistent session monitoring child sessions with Telegram/Slack escalation) would require infrastructure beyond skill files. However, the heartbeat monitoring interval idea could strengthen the existing stall detection proposals.

### Current state

`/implement-feature` orchestrates tasks synchronously within a single session. `task_status_hook.py` writes `LastActivity` timestamps on every Write/Edit/Bash call, but no process reads this field to detect stalled agents or escalate. The swarm-patterns skill documents parallel agent patterns but does not include a persistent monitor pattern.

### Target state

The `sam status` command includes a `stall_detected` field for tasks where `now - LastActivity > stall_threshold_minutes`. The implement-feature loop checks this field between task dispatches and emits a warning or blocks further dispatch when stalls are detected. This is a subset of the conductor pattern that is achievable within the current architecture.

### Measurable signal

Run `uv run sam status P{N}` on a plan with an in-progress task whose LastActivity is older than threshold. Output includes `"stall_detected": true` for that task.

---

## Improvement 5: Git worktree isolation for concurrent agent sessions

**Source pattern**: "Git worktree integration isolates each session in its own working directory with automatic cleanup and branch management" (Problem Addressed table, row 6) and "Each worktree is isolated working directory with its own branch; multiple agents can work on the same repo without merge conflicts" (Git Worktree Integration section)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md
**Confidence**: High
**Impact**: High
**Backlog**: Skipped -- already tracked as #453 "Systematic git worktree isolation for concurrent task agents"

### Current state

Already tracked in backlog. The implement-feature loop dispatches tasks sequentially. When parallel dispatch is eventually enabled (see #452), concurrent agents will need worktree isolation to avoid file conflicts.

### Target state

See backlog item #453.

### Measurable signal

See backlog item #453.

---

## Improvement 6: Stall detection with heartbeat monitoring interval

**Source pattern**: "Heartbeat monitoring on configurable interval (default 15 minutes); parent nudges when child sessions move running to waiting/error/idle" (Conductor section, Monitoring bullet)
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: High
**Impact**: High
**Backlog**: Skipped -- already tracked as #87 "SAM: Timeout/Stall Detection" and #448 "Stall detection for subagent tasks"

### Current state

Already tracked in backlog. `task_status_hook.py` writes `LastActivity` on every tool call but no process reads this field to detect or act on stalled agents.

### Target state

See backlog items #87 and #448.

### Measurable signal

See backlog items #87 and #448.

---

## Improvement 7: Skills pool management with per-session attach/detach

**Source pattern**: "Skills stored in ~/.agent-deck/skills/pool; apply writes to .agent-deck/skills.toml and materializes into .claude/skills" (Skills Management section) and "Manage a skills pool (~/.agent-deck/skills/pool) and attach/detach per project; state materializes into .claude/skills automatically" (Applications, bullet 3)
**Local system**: .claude/skills/ directory, plugins/*/skills/ directories
**Confidence**: High
**Impact**: Medium
**Backlog**: #776 created

### Current state

Skills in this repo are organized as plugin directories under `plugins/*/skills/` and symlinked into `.claude/skills/`. There is no concept of a "skills pool" where skills can be dynamically attached or detached per project or per session. All skills from installed plugins are always available. The `sam` task system supports per-task `skills:` fields that instruct agents to load specific skills, but this is declarative metadata -- it does not prevent other skills from being available.

The skill-creator skill (`/plugin-creator:skill-creator`) creates skills but has no pool management or per-project scoping capability. Skills are either installed (present in `.claude/skills/`) or not -- there is no intermediate "available but not active" state.

### Target state

A `skills.toml` or equivalent manifest at the project root or `~/.claude/` level that declares which skills are active for the current project/session. Skills in the pool but not in the manifest are available for attachment but not loaded by default. A command or MCP tool (`skill attach <name>`, `skill detach <name>`) manages the manifest and materializes/dematerializes symlinks. This enables project-specific skill scoping without modifying plugin directories.

### Measurable signal

File `skills.toml` exists at project root with a `[project.skills]` section listing active skill names. Running `skill attach <name>` adds an entry and creates the symlink in `.claude/skills/`. Running `skill detach <name>` removes the entry and symlink. `skill list --pool` shows all available skills; `skill list --active` shows only attached skills.

---

## Improvement 8: Concurrency cap for parallel task dispatch

**Source pattern**: "Manage multiple Claude Code instances across projects from a single interface" (Applications, bullet 1) combined with Agent Deck's multi-session management showing practical concurrent agent dispatch
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: Skipped -- already tracked as #452 "Concurrency cap for parallel task dispatch in implement-feature"

### Current state

Already tracked in backlog.

### Target state

See backlog item #452.

### Measurable signal

See backlog item #452.

---

## Improvement 9: SubagentStop hook captures structured work summary

**Source pattern**: "Built-in transition notifiers watch status changes" (Conductor section) and "Hooks write session state changes to SQLite; agent-deck polls and displays status" (Hook System section). Agent Deck's hook system captures structured event data on state transitions, not just timestamps.
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: High
**Impact**: Medium
**Backlog**: Skipped -- already tracked as #576 "SubagentStop hook should capture structured summary of subagent work"

### Current state

Already tracked in backlog.

### Target state

See backlog item #576.

### Measurable signal

See backlog item #576.

---

## Improvement 10: Remote notification integration for long-running agent workflows

**Source pattern**: "Optional Telegram and/or Slack integration via bridge daemon; socket mode support for Slack with slash commands" (Conductor section, Bridging bullet) and "The bridge daemon architecture (Telegram bot + Slack Socket Mode + message routing) provides a pattern for adding remote control to Claude Code workflows without hosting a separate service" (Integration Opportunities, bullet 5)
**Local system**: No direct local system mapping found.
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: no local system exists for remote notifications. Building a Telegram/Slack bridge daemon would be a new standalone service, not an extension of existing skills. Agent Deck already provides this capability -- users seeking remote notifications should use Agent Deck rather than reimplementing the pattern in this repo.

### Current state

No remote notification mechanism exists in this repo. When agent workflows run for extended periods, the user must actively monitor the terminal session.

### Target state

Not actionable as a skill extension. Remote notification is Agent Deck's domain.

### Measurable signal

N/A -- out of scope for skill/plugin architecture.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Hook-based instant status detection via SQLite event store | Medium | Need profiling data showing YAML-parse latency at scale before confirming gap |
| Session forking with context inheritance | Low | Requires external session management; incompatible with current architecture |
| MCP socket pooling for shared processes | Low | Repo creates MCP servers, not multi-session MCP clients; pooling is Agent Deck's domain |
| Conductor pattern for persistent monitoring | Medium | Overlaps with existing stall-detection items #87/#448; specific conductor infrastructure is out of scope |
| Remote notification integration | Low | No local system to extend; Agent Deck provides this natively |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Git worktree isolation for concurrent agents | Already tracked as #453 |
| Stall detection with heartbeat monitoring | Already tracked as #87 and #448 |
| Concurrency cap for parallel task dispatch | Already tracked as #452 |
| SubagentStop hook structured work summary | Already tracked as #576 |
| TOML-based configuration with type safety | Too abstract -- the repo already uses TOML (tomlkit) and YAML (ruamel.yaml) per .claude/rules/yaml-toml-libraries.md; no specific gap identified |
