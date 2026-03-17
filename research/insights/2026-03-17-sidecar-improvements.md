# Improvement Proposals: Sidecar

**Research entry**: ./research/developer-tools/sidecar.md
**Generated**: 2026-03-17
**Patterns assessed**: 8
**Backlog items created**: 1 (issues: #775)
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Persistent structured session metadata for cross-session context recovery

**Source pattern**: "Context Window Recovery: The Conversations plugin aggregates session history across all supported AI agents, enabling developers to review past conversations, token usage, and reasoning chains when context resets between agent invocations." (Relevance to Claude Code Development > Applications)
**Local system**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #775 created

### Current state

The `task_status_hook.py` writes an ephemeral context file at `.claude/context/active-task-{session_id}.json` containing `task_file_path`, `task_id`, and optionally `parent_issue_number`. This file is deleted by the SubagentStop hook when the sub-agent finishes. The `LastActivity` timestamp is written to the task file's YAML frontmatter on each Write/Edit/Bash call. Once a session ends, there is no persistent record of which agent worked on which task, what skills were loaded, how many tool calls were made, or what the agent's final output summary was. Cross-session context recovery relies entirely on reading the task file's status fields and any code changes committed.

### Target state

The SubagentStop hook, before deleting the active-task context file, appends a structured session summary record to a persistent file at `.claude/context/session-history.jsonl`. Each record contains: `session_id`, `task_id`, `task_file_path`, `agent_type`, `skills_loaded` (list), `started` (ISO timestamp from task), `completed` (ISO timestamp), `last_activity` (ISO timestamp), `parent_issue_number` (if known), and `outcome` (COMPLETE or the final status). This file accumulates across sessions and is never deleted by hooks.

### Measurable signal

File `.claude/context/session-history.jsonl` exists after at least one SubagentStop event. Each line is valid JSON containing at minimum `session_id`, `task_id`, `agent_type`, `completed`, and `outcome` fields. Running `wc -l .claude/context/session-history.jsonl` returns a count equal to the number of completed sub-agent sessions.

---

## Improvement 2: Config-driven skill/plugin feature toggling at runtime

**Source pattern**: "Config-driven feature toggling: Feature flags (--enable-feature, --disable-feature) and config-based plugin enable/disable allow operators to customize Sidecar without recompilation, useful for testing new features or disabling problematic plugins." (Patterns Worth Adopting, item 3)
**Local system**: `.claude/CLAUDE.md` (skill activation), `plugins/*/plugin.json` (plugin registry)
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: The local system's skill activation model (skills loaded on demand via `Skill()` tool calls) may already serve the same purpose as feature flags. Skills not invoked are never loaded. The gap would need validation that there are concrete failure scenarios where disabling a skill at the config level prevents problems that "simply not calling it" does not.

### Current state

Skills are loaded on demand via `Skill(skill="name")` calls. There is no mechanism to mark a skill as "disabled" such that invocation attempts fail fast with a clear error. If a skill is buggy, the only way to prevent its use is to remove or rename the SKILL.md file, which requires a file system edit.

### Target state

A config file (e.g., `.claude/config/disabled-skills.json`) lists skill names that should not be loaded. The skill loading mechanism checks this list and returns a clear error message ("Skill X is disabled via config") instead of loading the skill. This allows operators to disable problematic skills without file deletion.

### Measurable signal

Adding a skill name to `.claude/config/disabled-skills.json` causes subsequent `Skill(skill="that-name")` calls to return an error message containing "disabled via config" instead of loading the skill content.

---

## Improvement 3: Tmux-based agent session isolation with output capture

**Source pattern**: "Tmux integration for agent launchers: Workspaces manages agent sessions via tmux, capturing output and managing lifecycle. This pattern allows agents to run in isolated, observable contexts while Sidecar maintains visibility." (Patterns Worth Adopting, item 4)
**Local system**: `.claude/rules/interactive-terminal-workarounds.md`, `.claude/skills/swarm-operations/SKILL.md`
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: The local system delegates agents via the `Agent()` tool which manages its own lifecycle. Tmux-based isolation would be relevant only if Agent() sessions needed external observability (output capture, session listing). The Agent tool's built-in message passing (`SendMessage`) already provides inter-agent communication. Whether tmux-layer visibility adds value over existing mechanisms needs experimental validation.

### Current state

The `interactive-terminal-workarounds.md` rule documents tmux as a PTY provider for commands requiring a terminal. The `swarm-operations` and `swarm-patterns` skills launch agents via the `Agent()` tool, which manages lifecycle internally. There is no mechanism to observe a running sub-agent's output stream externally or to list active agent sessions from outside the orchestrator.

### Target state

Agent sessions launched via `/implement-feature` are optionally wrapped in tmux sessions (controlled by a config flag). The orchestrator can list active agent tmux sessions and capture their latest output via `tmux capture-pane`. Session names follow a convention: `agent-{task_id}-{session_id}`.

### Measurable signal

Running `tmux list-sessions` during an `/implement-feature` execution shows sessions matching the `agent-{task_id}-*` pattern. Running `tmux capture-pane -t agent-{task_id}-{session_id} -p` returns the agent's recent terminal output.

---

## Improvement 4: Sub-agent direct task/backlog linking during execution

**Source pattern**: "Task Linking: Extend the TD Monitor plugin to accept task creation prompts from Claude Code sessions, allowing agents to directly link ongoing work to task entries without manual user action." (Integration Opportunities, item 2)
**Local system**: `plugins/python3-development/skills/start-task/SKILL.md`, `plugins/python3-development/skills/implement-feature/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: Sub-agents during `/start-task` have access to backlog MCP tools and could create follow-up items. The current design deliberately centralizes follow-up creation in `/complete-implementation` Phase 1 (code-reviewer) to maintain quality gates. Whether allowing sub-agents to create backlog items during execution improves outcomes or fragments the review process needs architectural analysis.

### Current state

During `/start-task` execution, sub-agents implement their assigned task but do not create follow-up backlog items or link discovered issues to the backlog. Follow-up task creation happens post-hoc in `/complete-implementation` Phase 1 (code-reviewer agent). If a sub-agent discovers a pre-existing issue or identifies adjacent work, this information is captured only in divergence notes appended to the task file -- not as trackable backlog items.

### Target state

Sub-agents during `/start-task` can call `mcp__backlog__backlog_add` to create follow-up items tagged with `source: task-{task_id}`. These items are created with status `needs-grooming` and are not acted upon until the `/complete-implementation` quality gates run. The `/start-task` SKILL.md documents this capability and provides guidelines for when sub-agents should create follow-up items (pre-existing bugs found, scope expansion needed, documentation gaps).

### Measurable signal

After a `/start-task` execution where the sub-agent encountered a pre-existing issue, `mcp__backlog__backlog_list(status="needs-grooming")` includes an item with `source` containing `task-{task_id}`.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Config-driven skill/plugin feature toggling | Medium | Need to validate that "simply not calling a skill" is insufficient -- the gap between on-demand loading and explicit disable-flag may not cause observable failures |
| Tmux-based agent session isolation | Medium | Agent() tool manages its own lifecycle; external tmux visibility needs experimental validation to confirm it adds value over SendMessage-based communication |
| Sub-agent direct task/backlog linking | Medium | Current centralized follow-up creation in /complete-implementation is a deliberate architectural choice; allowing sub-agents to create items during execution may fragment review quality |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Plugin-based architecture for extensibility | Already covered: local system has equivalent modular plugin/skill architecture in `plugins/` directory with SKILL.md frontmatter, marketplace.json registry, and skill activation via `Skill()` tool |
| Local-first, read-only philosophy | Too abstract: this is a design philosophy, not a concrete mechanism. The local system's hook scripts already follow read-then-write patterns with explicit user-initiated writes |
| Multi-Agent Orchestration as coordinator | Already covered: `swarm-operations/SKILL.md` and `swarm-patterns/SKILL.md` provide equivalent multi-agent coordination via TeamCreate, SendMessage, Agent() tool, and TaskCreate/TaskUpdate primitives |
| Documentation Generation from diffs | Already covered: `/complete-implementation` Phase 4 (doc-drift-auditor) and Phase 5 (service-docs-maintainer) already generate documentation updates based on code changes. Stall detection already tracked in backlog as #87 and #448 |
