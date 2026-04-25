# Utilization Proposals: Honker

**Research entry**: ./research/data-infrastructure/honker.md
**Generated**: 2026-04-25
**Integration surfaces found**: 3 (Python SDK | SQLite extension | Pub/Sub primitives)
**Proposals written**: 2
**Skipped**: 2 — dispatch system already uses custom SQLite schema (optimization, not replacement); backlog MCP uses GitHub Issues (different scope; honker unsuitable)

---

## Utilization 1: development-harness dispatch orchestration → honker work queues

**Research entry**: ./research/data-infrastructure/honker.md
**Caller**: `plugins/development-harness/backlog_core/dispatch_state.py`
**Integration mechanism**: Python SDK (`pip install honker`)
**Replaces or adds**: At-least-once job delivery with retry, priority queuing, and exponential backoff for wave item execution
**Setup cost**: Medium (schema migration from custom tables to honker `_honker_live` table; PID tracking reused)
**Integration surface**: Python bindings (`honker.open()`, `db.queue()`, `.claim()`, `.ack()`, `.retry()`)

### Why this caller

The dispatch orchestration system in `dispatch_state.py` manages wave execution by tracking item state (`pending`, `in-progress`, `complete`, `failed`) in a custom SQLite schema. Currently, item failures are manual (`set_item_failed()`). Honker's at-least-once queue with exponential backoff, dead-letter tables, and declarative `max_attempts` would replace the custom state machine with a durable, production-proven primitive. The current dispatch system reads PIDs and marks items failed if a process dies (`check_stale_pids()`); honker replaces this with visibility timeout expiration and automatic retry. For multi-machine dispatch (future), honker's transactional coupling (enqueue in same transaction as dispatch record) eliminates dual-write race conditions.

### Integration sketch

```python
import honker

db = honker.open("~/.dh/projects/{slug}/dispatch.db")
queue = db.queue("dispatch-items")

# Current: INSERT into custom items table
# Proposed: enqueue as honker job
@queue.task(retries=3, timeout_s=3600)
def execute_dispatch_item(milestone: int, wave_num: int, issue: int):
    # Spawn claude session for this item
    pid = spawn_claude_worker(...)
    return {"pid": pid, "started_at": now_iso()}

# Caller: task_id = execute_dispatch_item(5, 1, 42)
# result = task_id.get(timeout=10)  # blocks until worker runs it

# Worker (separate process):
async for job in queue.claim("worker-1"):
    try:
        pid = spawn_claude(...)
        monitor_pid(pid)
        job.ack()
    except ProcessError as e:
        job.retry(delay_s=60, error=str(e))
```

**Current state tracking code** (dispatch_state.py:229–259): explicit `UPDATE items SET status='in-progress'` and manual `set_item_failed()`. **Proposed**: replace with honker queue claim/ack/retry pattern, which is atomic and language-agnostic. The `pid` field remains in the schema for process monitoring.

---

## Utilization 2: development-harness multi-agent event stream → honker streams

**Research entry**: ./research/data-infrastructure/honker.md
**Caller**: `plugins/development-harness/backlog_core/server.py` (MCP server providing S1-S7 pipeline coordination)
**Integration mechanism**: Python SDK (`db.stream()`)
**Replaces or adds**: Durable event broadcast for pipeline stage transitions (S1→S2, S2→S3, etc.) with per-agent offset replay
**Setup cost**: Low (append-only log only; no schema migration)
**Integration surface**: Python bindings (`db.stream(name).publish(event, tx=tx)`, `.subscribe(consumer)`)

### Why this caller

The development harness coordinates seven stages across multiple agent dispatches. Currently, stage completion is detected via artifact presence (reading plan files). For multi-agent orchestration with cross-stage coordination (e.g., "notify all dependent agents when S3 context validation completes"), honker's durable streams with per-consumer offset tracking would provide a cleaner, replay-safe event bus than polling file timestamps. Each agent (architect, code-reviewer, verifier) subscribes to a named consumer (e.g., `"architect-consumer"`) and resumes from its last offset after restart. Transactional coupling (`stream.publish(..., tx=tx)` in same transaction as artifact creation) ensures no event is lost across crashes.

### Integration sketch

```python
import honker
from contextlib import contextmanager

db = honker.open("~/.dh/projects/{slug}/events.db")
pipeline_stream = db.stream("pipeline-lifecycle")

# Publish stage transition event atomically with artifact
with db.transaction() as tx:
    artifact_registry.register(issue, "architect", path, tx=tx)
    pipeline_stream.publish({
        "stage": "S2",
        "event": "architect-complete",
        "issue": issue,
        "timestamp": now_iso()
    }, tx=tx)

# Consumer: code-reviewer agent subscribes
async for event in pipeline_stream.subscribe(consumer="code-reviewer"):
    if event["stage"] == "S2" and event["event"] == "architect-complete":
        # Trigger code-review workflow for this issue
        await review_flow(issue_number=event["issue"])
```

**Current mechanism** (server.py dispatch loop): artifact presence check via `artifact_list()`. **Proposed**: publish structured events on transactional commit, allowing agents to subscribe and react. Offset tracking ensures agents resuming from crashes do not miss events.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `/dh:backlog-tools-administrator` skill (backlog management) | Backlog operations are anchored to GitHub Issues as the source of truth. Honker's single-machine constraint rules it out for multi-repo, multi-organization backlog coordination. Scope mismatch: backlog is cross-system; honker is intra-process |
| Backlog MCP server task queue for artifact dispatch | SAM MCP (`sam_schema/`) already provides task planning and status updates via GitHub sub-issues. Adding a separate honker queue would create dual state (GitHub Issues + honker tables). SAM's GitHub backend is the source of truth; honker would be a redundant cache |

---
