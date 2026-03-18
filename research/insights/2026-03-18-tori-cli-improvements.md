# Improvement Proposals: tori-cli

**Research entry**: ./research/developer-tools/tori-cli.md
**Generated**: 2026-03-18
**Patterns assessed**: 11
**Backlog items created**: 2 (issues: #781, #782)
**Deferred (low confidence)**: 5
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Declarative condition syntax for task readiness and acceptance criteria

**Source pattern**: "Tori's 3-token condition format (`scope.field op value`) could be adapted to define task readiness conditions, success criteria, or SLA alerts in Claude Code's task management system." (Integration Opportunities section)
**Local system**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #781 created

### Current state

Task readiness in the SAM system is determined solely by dependency graph resolution: a task is "ready" when its status is `NOT STARTED` and all dependency tasks have status `COMPLETE`. There is no mechanism to express conditional readiness based on observable system state (e.g., "file X exists", "command Y exits 0", "field Z in config has value V"). Acceptance criteria in task files are free-text prose that agents interpret; they are not machine-evaluable conditions.

File: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` -- the `get_ready_tasks` function checks only `status` and `dependencies` fields. No condition evaluation exists.

### Target state

Task YAML frontmatter supports an optional `conditions` field containing a list of 3-token expressions in the format `scope.field op value` (e.g., `file.plan/architect-auth.md exists true`, `command.uv_run_tests exit_code 0`). The `sam ready` command evaluates these conditions alongside dependency checks. A task is "ready" only when both dependency graph and all conditions pass. The condition evaluator is a standalone function that can be tested independently.

### Measurable signal

Run: `uv run sam ready P{N}` on a plan where a task has `conditions: ["file.some/path.md exists true"]` -- output includes or excludes the task based on whether the file exists. The `conditions` field is documented in `.claude/docs/TASK_FILE_FORMAT.md`.

---

## Improvement 2: Deterministic time injection in task_status_hook.py

**Source pattern**: "The Alerter's `now func() time.Time` field allows time-based logic to be tested without `time.Sleep`. A pattern worth adopting in any agent system with time-dependent state." (Patterns Worth Adopting section)
**Local system**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: High
**Impact**: Low
**Backlog**: #782 created

### Current state

The `get_iso_timestamp()` function at line 227 of `task_status_hook.py` calls `datetime.now(UTC).isoformat(timespec="seconds")` directly. All callers (`handle_subagent_stop`, `handle_post_tool_use`) use this function without the ability to inject a fixed time. Tests for this hook must either mock `datetime.now` at the module level or accept non-deterministic timestamps, making assertions about timestamp ordering or staleness detection fragile.

File: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`, line 227-233.

### Target state

`get_iso_timestamp()` accepts an optional `now` parameter (callable returning `datetime`) that defaults to `lambda: datetime.now(UTC)`. Test code passes a fixed `now` callable, enabling deterministic timestamp assertions. The same pattern is applied to any future time-dependent logic (e.g., stall detection threshold comparison).

### Measurable signal

File `task_status_hook.py` contains `def get_iso_timestamp(*, now: Callable[[], datetime] | None = None)`. At least one test in `tests/test_task_status_hook/` calls `get_iso_timestamp(now=lambda: fixed_dt)` and asserts the exact returned string.

---

## Improvement 3: Alert state machine for task status transitions

**Source pattern**: "The alert state machine (inactive -> pending -> firing -> resolved) is a clean pattern for managing long-lived conditions that require hysteresis (preventing flapping). Applicable to agent status tracking and availability detection." (Applications section)
**Local system**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: Low
**Impact**: High
**Backlog**: Deferred -- confidence low: the existing backlog items #87 "SAM: Timeout/Stall Detection" and #448 "Stall detection for subagent tasks" already cover the stall detection use case. The state machine pattern would be the implementation mechanism for those items, not a separate concern. Additionally, task status transitions in SAM are currently simple (NOT STARTED -> IN PROGRESS -> COMPLETE | BLOCKED) and the hysteresis benefit (preventing flapping) applies mainly to monitoring systems, not task execution where transitions are agent-driven and unidirectional.

---

## Improvement 4: Configuration validation at TOML/YAML parse time for skill frontmatter

**Source pattern**: "Alert conditions are validated at TOML parse time via a whitelist parser, catching errors early rather than during evaluation. This pattern could improve Claude Code's skill configuration validation." (Patterns Worth Adopting section)
**Local system**: `plugins/plugin-creator/skills/skill-creator/` (skill creator workflow), `packages/sam_schema/` (task schema)
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the research entry names the pattern clearly (validate at parse time via whitelist), but I could not locate a `skill-creator/SKILL.md` to confirm the absence of frontmatter validation. The existing backlog item #88 "SAM: Artifact Schema Validation" partially overlaps. The `skilllint` tool (`uvx skilllint@latest`) exists for post-hoc validation but whether it runs at load time or only on demand requires examination of the skill-loading code path, which I did not read.

---

## Improvement 5: Version handshake for agent-orchestrator protocol

**Source pattern**: "The version handshake approach (client sends version, server checks and warns but never blocks) is a pragmatic upgrade strategy that could apply to Claude Code's agent protocol evolution." (Applications section)
**Local system**: `plugins/python3-development/skills/implement-feature/SKILL.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: Claude Code agents communicate via prompt text, not a structured wire protocol. There is no client-server handshake to version. The pattern is architecturally incompatible with the current prompt-based delegation model where the orchestrator constructs prompts and sub-agents execute them in the same process space.

---

## Improvement 6: SSH-first architecture for remote agent deployment

**Source pattern**: "Tori's design (no exposed ports, SSH tunnels only) is relevant for secure agent deployment patterns where the orchestrator must access remote agents without HTTP endpoints." (Applications section)
**Local system**: No direct local equivalent exists.
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: Claude Code agents run as sub-processes within the same Claude Code session, not as remote services. The SSH tunnel pattern addresses a problem (secure remote access) that does not exist in the current architecture. If remote agent execution were added, this pattern would become relevant, but no such feature is planned or in the backlog.

---

## Improvement 7: Binary distribution pattern for skills/plugins

**Source pattern**: "The single-binary Go approach with a simple shell install script mirrors best practices for distributing CLI tools. Tori's install.sh pattern (curl | sh with version pinning) is worth studying for packaging Claude Code skills as distributable binaries." (Applications section)
**Local system**: Plugin marketplace distribution (marketplace.json, plugin.json)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: Claude Code skills are markdown files and Python scripts, not compiled binaries. The distribution model is fundamentally different (marketplace JSON manifests vs. compiled artifacts). The install.sh pattern is not applicable because skills are loaded by Claude Code's plugin system, not installed as standalone binaries.

---

## Improvement 8: Pub/sub hub for multi-consumer streaming

**Source pattern**: "The Hub's topic-based fan-out (clients subscribe to `metrics`, `logs`, `alerts`, `containers`) is a clean pattern for broadcasting updates from a single producer (the agent) to multiple consumers (TUI, external clients). Applicable to skill pub/sub and multi-consumer streaming." (Patterns Worth Adopting section)
**Local system**: No direct local equivalent. Task status updates are file-based (YAML frontmatter writes).
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the local system uses file-based state (task YAML files) rather than in-memory message passing. A pub/sub hub would require fundamental architectural change to the hook system. The research entry's pattern is for a long-running agent process with connected clients, which does not map to Claude Code's stateless hook execution model.

---

## Improvement 9: Flat package structure for domain cohesion

**Source pattern**: "Tori's `internal/agent/` package (no sub-packages, one file per concern) demonstrates how to organize related code without premature abstraction hierarchy." (Patterns Worth Adopting section)
**Local system**: `packages/sam_schema/` (Python package)
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: the `sam_schema` package uses `core/models.py`, `core/query.py` submodules. Whether this hierarchy is premature or appropriate requires reading the full package structure. The Go idiom of flat packages does not directly translate to Python conventions where `__init__.py`-based packages are standard. The pattern is more of a code style preference than an actionable gap.

---

## Improvement 10: Remote log streaming for agent output

**Source pattern**: "Tori's remote log streaming with filtering/search could inspire how Claude Code retrieves and searches logs from distributed agent executions without requiring central log aggregation." (Integration Opportunities section)
**Local system**: No direct local equivalent. Agent output is captured by Claude Code's built-in session logs.
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: Claude Code agents do not produce independent log streams. Their output is part of the Claude Code session context. The remote log streaming pattern addresses a distributed systems problem that does not exist in the single-session agent model.

---

## Improvement 11: Container grouping by project label

**Source pattern**: "Automatic grouping by Docker Compose project via `com.docker.compose.project` label" (Key Features section)
**Local system**: SAM task organization -- tasks grouped by plan/feature slug.
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: the pattern is Docker-specific (label-based grouping). SAM already groups tasks by plan file. The analogy is too loose to produce an actionable improvement.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Alert state machine for task status transitions | Low | Already tracked as #87 and #448. State machine is an implementation detail of those items, not a separate concern. Would need to verify those backlog items do not already specify a state machine approach. |
| Configuration validation at parse time | Medium | Could not confirm absence of load-time validation in skill-creator. Need to read the skill-loading code path and `skilllint` integration to determine if validation already runs at load time. |
| Version handshake for agent protocol | Low | No wire protocol exists in Claude Code. Pattern is architecturally incompatible with prompt-based delegation. |
| SSH-first remote agent deployment | Low | No remote agent execution exists. Pattern addresses a non-existent problem. |
| Binary distribution for skills | Low | Skills are markdown/Python, not compiled binaries. Distribution model is fundamentally different. |
| Pub/sub hub for streaming | Low | File-based state model is incompatible with in-memory pub/sub. Would require architectural rewrite. |
| Flat package structure | Medium | Python conventions differ from Go. Need to read sam_schema structure to confirm whether hierarchy is premature. |
| Remote log streaming | Low | Single-session model has no independent log streams to aggregate. |
| Container grouping by label | Low | Docker-specific pattern with only loose analogy to SAM task grouping. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Stall detection via LastActivity field | Already tracked in backlog as #87 "SAM: Timeout/Stall Detection" and #448 "Stall detection for subagent tasks" |
| Log tailing with regex search | Too abstract -- no concrete gap; Claude Code agents do not produce searchable log streams |
