# Improvement Proposals: 1Code

**Research entry**: ./research/coding-agents/1code.md
**Generated**: 2026-03-17
**Patterns assessed**: 8
**Backlog items created**: 1 (issues: #758)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 6

---

## Improvement 1: Add plan-mode gate to implement-feature SAM execution workflow before destructive agent dispatch

**Source pattern**: "Plan mode before agent mode: requiring the agent to produce and surface a structured plan for review before executing destructive operations (file edits, bash commands) reduces irreversible mistakes — directly applicable to skill design." (Research entry §Relevance to Claude Code Development > Patterns Worth Adopting)
**Local system**: `plugins/python3-development/skills/implement-feature/SKILL.md`, `plugins/python3-development/skills/start-task/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #758 created

### Current state

`plugins/python3-development/skills/implement-feature/SKILL.md` dispatches task agents directly into full execution mode via `Skill(skill="start-task", ...)`. No mechanism exists for the agent to surface a structured plan for human review before the sub-agent executes file edits, bash commands, or other irreversible operations.

`plugins/python3-development/skills/start-task/SKILL.md` claims the task at step 3 and immediately proceeds to implementation at step 6 (`Implement against the task acceptance criteria`). There is no plan-first phase between claiming and executing.

The `swarm-patterns` skill (`/home/user/claude_skills/.claude/skills/swarm-patterns/SKILL.md`) documents Pattern 5 (Plan Approval Workflow) using `mode: "plan"` with team swarms and `plan_approval_response` messages, but this pattern is not wired into the SAM task execution path.

### Target state

`implement-feature` supports an optional `--plan-first` mode (or a task-level flag `plan_review: true` in task YAML frontmatter). When the flag is set, the sub-agent invoked via `start-task` enters a plan-only phase before any Write/Edit/Bash calls: it reads task acceptance criteria, produces a structured markdown plan listing each file it will edit, each bash command it will run, and rationale, writes the plan to `plan/task-plan-{task_id}.md`, and halts. The orchestrator (implement-feature loop) reads the plan file, surfaces it to the user for approval, and only dispatches the full execution agent after approval is received. Rejection feeds back to the agent and requests a revised plan.

### Measurable signal

`implement-feature` SKILL.md contains a `--plan-first` flag description and a plan-approval step in its Progress Loop section. `start-task` SKILL.md documents a `plan_review: true` task YAML field that triggers plan-only mode before execution. A task YAML file with `plan_review: true` causes `start-task` to write `plan/task-plan-{task_id}.md` and exit without any Write/Edit/Bash tool calls in the sub-agent session.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Pinned binary versions for agent CLIs | Low | 1Code pins a downloaded Claude CLI binary version. This repo does not download or manage CLI binaries — subagent dispatch uses `subagent_type` strings resolved at runtime by the Claude Code platform. The gap would only be actionable if this repo had a build step that downloads binaries, which it does not. No local file to observe this gap in. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Parallel agent sessions / Git worktree isolation per chat | Already tracked as backlog #453 (Systematic git worktree isolation for concurrent task agents, P2). No new item created. |
| tRPC for type-safe IPC | Architecture-incompatible. This repo has no Electron renderer-to-main process communication. The pattern applies only to multi-process desktop app architectures. |
| Sub-chat forking with sessionId resume tokens | Electron chat UI feature with no equivalent concept in a skill/agent workflow repository. The `subChats` SQLite table and `sessionId` resume mechanism are specific to 1Code's persistent chat application. |
| BYOK / multi-account Anthropic credentials | Application-level authentication concern. This repo has no credential storage, no OAuth flow, and no account switching logic. The `anthropicAccounts` schema is not applicable to skill files or workflow scripts. |
| MCP server lifecycle management via pluginsRouter | 1Code's `pluginsRouter` provides a UI for toggling/configuring MCP servers without editing config files. This repo is a skill/plugin content repository, not an MCP client host. Skills document how to use MCP servers; they do not manage server registrations. Pattern is out of scope. |
| Worktree path indexed as hot path in DB | SQLite schema optimization concern. This repo has no database. Observation about `chats_worktree_path_idx` is not transferable. |
