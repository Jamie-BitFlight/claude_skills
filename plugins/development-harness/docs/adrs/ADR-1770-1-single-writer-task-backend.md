# ADR-1770-1: Single-Writer Contract for TaskBackend.append_task and finalize_plan

**Status:** Accepted
**Date:** 2026-04-13
**Issue:** [#1770](https://github.com/Jamie-BitFlight/claude_skills/issues/1770)

## Context

The `TaskBackend` Protocol defines two mutating operations that involve a
read-modify-write cycle on the same plan document:

- `append_task(plan_id, task)` — loads the plan, checks for duplicate IDs,
  appends the task, and writes back.
- `finalize_plan(plan_id)` — loads the plan, sets `state = "ready"`, writes back.

All three concrete backends (`InMemoryTaskProvider`, `LocalYamlTaskProvider`,
`GitHubTaskProvider`) implement these as non-atomic read-modify-write sequences.
Under concurrent writes from multiple callers, the last write wins and earlier
writes are silently lost.

## Decision

`TaskBackend.append_task` and `TaskBackend.finalize_plan` operate under a
**single-writer contract**: the caller is responsible for ensuring that at most
one writer operates on a given plan at any point in time. Backends are NOT
required to detect, reject, or recover from concurrent writes. Behavior under
concurrent writes to the same plan is **undefined**.

This is the correct trade-off for the current architecture because:

1. **SAM plans are authored sequentially.** The incremental build flow
   (`create → append_task × N → finalize`) is orchestrated by a single session.
   The orchestrator controls sequencing.

2. **The complexity cost of distributed locking is not justified.** Adding
   file-locking (`fcntl.flock`), YAML-level version fields, or optimistic
   concurrency control would triple the implementation complexity of
   `local_yaml.py` and require GitHub Issue etags for `github_task.py`. The
   defect this would prevent (two orchestrators appending to the same plan
   simultaneously) is not a realistic scenario in the current deployment model.

3. **Backends cannot reliably enumerate callers.** The memory backend has no
   IPC; the YAML backend has no process-safe advisory lock API across platforms;
   the GitHub backend relies on the GitHub API which has its own eventual
   consistency guarantees.

## Consequences

- **Callers must serialize writes.** Any code that calls `append_task` or
  `finalize_plan` on the same plan from multiple threads or processes must
  provide external coordination (e.g., process-level scheduling, task queue).
- **Docstrings must state the contract.** Every `append_task` and
  `finalize_plan` implementation must include the single-writer warning and
  reference this ADR.
- **The contract is centralized.** The `validate_appended_task` helper in
  `sam_schema.core.backends._utils` performs the duplicate-ID check that all
  three backends share, providing a single place to update if the contract
  changes.
- **Future backends must honour the contract.** Any new `TaskBackend`
  implementation must document whether it provides stronger guarantees. If it
  does not, it must state the single-writer assumption in its docstring and
  reference this ADR.

## Alternatives Considered

### File-level locking (fcntl.flock)

Rejected. Platform-specific (not available on Windows); does not protect against
concurrent writes from separate machines; requires cleanup on crash.

### Optimistic concurrency control (YAML version fields)

Rejected. Would require callers to catch `ConflictError` and retry, adding
significant complexity to the server layer. No current caller has a retry loop.

### GitHub API etags

Rejected. The GitHub REST API does not expose etags on Issue update responses in
a way that maps cleanly to our update flow. GraphQL mutations do not support
conditional updates.

## References

- Issue #1770: Incremental plan build pattern (create → append_task × N → finalize)
- `sam_schema.core.backends._utils.validate_appended_task` — shared duplicate-ID check
- `sam_schema.core.task_backend.TaskBackend.append_task` — Protocol docstring
- `sam_schema.core.task_backend.TaskBackend.finalize_plan` — Protocol docstring
