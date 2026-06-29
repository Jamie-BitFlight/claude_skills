---
title: "Improvement Proposals: Stakpak Agent"
---

## Improvement 1: Stall detection using LastActivity field in SAM task execution

**Source pattern**: "Secret Substitution / Real-Time Progress Streaming" -- Stakpak streams progress updates for long-running operations instead of blocking on completion (Section: Key Features, item 4 and 8)
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: already tracked as #87 (SAM: Timeout/Stall Detection) and #448 (Stall detection for subagent tasks)

### Current state

`task_status_hook.py` writes `LastActivity` timestamps on every Write/Edit/Bash tool call during task execution. However, no process reads this field to detect stalled agents or provide progress feedback. The `implementation_manager.py` `status` and `ready-tasks` commands return task metadata but do not compare `LastActivity` against a threshold to flag stalls.

### Target state

`implementation_manager.py` `status` command includes a `stall_detected: true/false` field for each IN_PROGRESS task, comparing `now - LastActivity` against a configurable `stall_threshold_minutes` (default: 15). The `/implement-feature` progress loop checks this field and logs a warning when a task appears stalled.

### Measurable signal

Run: `uv run implementation_manager.py status . {slug}` -- output includes `stall_detected` field for IN_PROGRESS tasks. A task with `LastActivity` older than threshold shows `stall_detected: true`.

---

## Improvement 2: Reversible file operations with automatic backup

**Source pattern**: "All file modifications are automatically backed up, enabling rollback recovery if changes prove problematic." (Section: Key Features, item 7 -- Reversible File Operations)
**Local system**: plugins/python3-development/skills/start-task/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the local system relies on git for file recovery; implementing file-level backups outside git would require determining whether the gap is real or whether git already provides equivalent coverage via `git stash` and `git diff`

### Current state

The SAM `/start-task` workflow delegates file modifications to sub-agents that use Write/Edit tools directly. There is no automatic backup mechanism before file modifications. Recovery depends on git (uncommitted changes can be recovered via `git checkout` or `git stash`), but mid-task failures may leave files in an inconsistent state with no easy rollback to the pre-task state.

### Target state

Before a sub-agent begins modifying files for a task, a snapshot of affected files is captured (e.g., via `git stash create` or a file-level backup to `.claude/backups/task-{id}/`). On task failure or BLOCKED status, the orchestrator can restore the snapshot. The backup path is recorded in the task's active context file.

### Measurable signal

After a task fails mid-execution, running a restore command returns all modified files to their pre-task state. The backup directory or stash ref is recorded in `.claude/context/active-task-{session_id}.json`.

---

## Improvement 3: MCP server secret redaction in tool outputs

**Source pattern**: "Secret Substitution: LLM receives variable references, not actual credentials. Agent resolves placeholders at execution time." and "Privacy Mode: Redacts IP addresses, AWS account IDs, and other sensitive metadata from logs and outputs." (Section: Key Features, item 1)
**Local system**: plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: Claude Code's own environment handles API keys via env vars, but the fastmcp-creator skill does not document patterns for preventing sensitive data from appearing in MCP tool outputs or LLM context. Would need to verify whether Claude Code's native sandbox already provides equivalent protection.

### Current state

The fastmcp-creator skill documents how to build MCP servers with tools, resources, and prompts. It does not include guidance on redacting sensitive data from tool return values before they enter the LLM context. MCP servers built with this skill could inadvertently return credentials, tokens, or PII in their tool outputs.

### Target state

The fastmcp-creator skill includes a "Security Patterns" section documenting: (1) how to use environment variable references instead of literal secrets in tool parameters, (2) a redaction utility pattern for stripping sensitive patterns (API keys, tokens, IP addresses) from tool return values before they reach the LLM, (3) example code showing the pattern applied to a tool that accesses external services.

### Measurable signal

The fastmcp-creator SKILL.md or a reference file contains a "Security Patterns" section with a working code example of output redaction. Running `Grep` for "redact" or "secret" in the skill directory returns matches.

---

## Improvement 4: Preflight validation for SAM task execution environment

**Source pattern**: "Preflight Checks: `stakpak autopilot doctor` validates system readiness before startup." (Section: Key Features, item 2 -- Autopilot)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the implement-feature skill assumes the environment is ready (plan directory exists, implementation_manager.py is runnable, hooks are installed). Failures surface only after task dispatch begins. However, the `validate` command in implementation_manager.py partially covers this for task file validation -- the gap is specifically about runtime environment readiness (hooks installed, MCP servers available, agents resolvable).

### Current state

The `/implement-feature` skill begins executing by querying task status and dispatching to agents. There is no preflight check that validates: (1) hooks are properly installed and functional, (2) required MCP servers are running, (3) the task file passes structural validation, (4) required agents are resolvable. The `implementation_manager.py validate` command checks task file structure but not the runtime environment.

### Target state

The `/implement-feature` progress loop includes a Step 0 "Preflight" that runs `implementation_manager.py validate` on the task file AND checks that hooks are installed (via `prek` status), MCP servers respond, and agent types referenced in tasks are valid. Preflight failures block execution with a clear diagnostic message rather than failing mid-task.

### Measurable signal

Running `/implement-feature` on a task file with a missing hook configuration or invalid agent reference produces a preflight error message before any task dispatch occurs, rather than failing during task execution.

---

## Improvement 5: Budget-aware context reduction for long SAM sessions

**Source pattern**: "Context Management & History Reduction -- Stakpak implements multiple context reduction strategies for long conversations: Task Board Context Manager, Simple Context Manager, File Scratchpad Manager. Reduction is budget-aware -- when conversation exceeds the LLM's context window threshold, the agent automatically trims history." (Section: Context Management & History Reduction)
**Local system**: .claude/CLAUDE.md (Context Window Discipline section)
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: CLAUDE.md contains context window discipline rules (orchestrator reads constraints, file pointer pattern) that serve a similar purpose but are policy-based rather than automated. Whether automated context reduction is feasible within Claude Code's architecture (where compaction is handled by the platform) would require investigation.

### Current state

The CLAUDE.md "Context Window Discipline" section defines policy rules about what the orchestrator should and should not read. The "File pointer pattern" instructs agents to write results to files and return only paths. These are behavioral guidelines enforced by prompt, not automated mechanisms. There is no budget-aware system that monitors token usage and automatically triggers context trimming during long SAM implementation sessions.

### Target state

A context budget monitoring mechanism tracks approximate token usage during `/implement-feature` sessions. When usage approaches a threshold, the orchestrator proactively writes intermediate state to a file (e.g., `.claude/context/session-state-{id}.json`) and references it instead of keeping full history in context. This extends the Structured session work logs concept (#317) with budget awareness.

### Measurable signal

During a long `/implement-feature` session (10+ tasks), a context state file is written at a threshold point, and subsequent task dispatches reference this file rather than replaying full history.

---

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Stall detection using LastActivity (Improvement 1) | medium | Already tracked as #87 and #448. Would need to verify those items cover the specific `implementation_manager.py status` integration described here. |
| MCP server secret redaction (Improvement 3) | medium | Need to verify whether Claude Code's native sandbox already prevents sensitive data leakage in MCP tool outputs, making this guidance unnecessary. |
| Preflight validation for SAM execution (Improvement 4) | medium | The `validate` command partially covers this. Need to audit what percentage of runtime failures would be caught by a preflight vs. already being caught by existing mechanisms. |
| Reversible file operations (Improvement 2) | low | Git provides file-level recovery. Need to measure how often mid-task failures leave files in an unrecoverable state to determine if additional backup is warranted. |
| Budget-aware context reduction (Improvement 5) | low | Claude Code platform handles compaction. Need to determine whether application-level context management is feasible or redundant within the platform's architecture. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-Provider LLM Abstraction | Not applicable -- this repo is Claude Code-specific, operates exclusively with Anthropic models. Multi-provider abstraction is architecturally incompatible. |
| Autonomous Scheduling (24/7 runtime) | Not applicable -- Claude Code is session-based, not a daemon. Stakpak's systemd/launchd service model is architecturally incompatible with Claude Code's execution model. |
| Editor Integration (ACP protocol) | Not applicable -- Claude Code already has its own editor integrations (VS Code extension). ACP is Zed-specific and a different product category. |
