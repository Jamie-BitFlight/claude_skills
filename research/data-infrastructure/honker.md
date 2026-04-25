# Honker

**Research Date**: 2026-04-25
**Source URL**: <https://github.com/russellromney/honker>
**Documentation**: <https://honker.dev>
**Primary Language**: Rust (core), Python/Node.js/Go/Ruby/Bun/Elixir/C++ (bindings)
**Version at Research**: 0.2.1
**License**: Apache 2.0

---

## Overview

Honker is a SQLite extension and multi-language binding library that adds PostgreSQL-style `NOTIFY`/`LISTEN` semantics, durable pub/sub, task queues, and event streams to SQLite — without client polling, daemon/broker overhead, or separate datastore. By replacing application-level polling with a single-digit-microsecond `PRAGMA data_version` read every 1ms, honker achieves push-like semantics and cross-process notifications with single-digit-millisecond delivery latency. The extension is language-agnostic; any SQLite 3.9+ client can load `libhonker_ext` and access the same queue, stream, and notification tables. Honker ships as a Rust crate on crates.io (`honker-core`, `honker-extension`) plus official bindings for Python, Node.js, Go, Ruby, Bun, Elixir, and C++.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| SQLite applications need pub/sub and task queues but don't want separate Redis/RabbitMQ infrastructure | Honker embeds all messaging primitives (notifications, streams, queues) in the `.db` file itself — no external broker required |
| Race conditions and atomicity issues when application writes and async queue writes are separate transactions | `queue.enqueue(..., tx=tx)` commits atomically with business logic; rollback drops both, eliminating dual-write problems |
| Client polling for job availability introduces latency and CPU overhead | Honker wakes workers via `PRAGMA data_version` change detection (~1ms poll cadence); idle cost is a single small query per millisecond per database |
| Queue implementations on SQLite don't scale to production workloads or lack retry/visibility/priority semantics | Honker provides at-least-once guarantees, exponential backoff, dead-letter tables, priority queues, visibility timeouts, and task result storage |
| No durable replay mechanism for lost pub/sub messages if a subscriber goes offline | `db.stream()` offers per-consumer offset tracking; each named consumer resumes from its last saved offset, providing at-least-once replay |
| Framework-specific integrations fragment the ecosystem across ORMs and web frameworks | Honker is framework-agnostic; works inside any ORM (SQLAlchemy, Django, Drizzle, Ecto, etc.) and any web framework by loading the extension on the ORM's connection |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Latest Release | v0.2.1 | 2026-04-25 |
| Repository Stars | Not publicly available from GitHub API without auth | 2026-04-25 |
| Contributors | Not publicly available | 2026-04-25 |
| Language Bindings | 8 (Python, Node.js, Rust, Go, Ruby, Bun, Elixir, C++) | 2026-04-25 |
| Published Crates | honker-core (0.2.1), honker-extension (0.2.1) | 2026-04-25 |

---

## Key Features

### Pub/Sub Primitives

- **Ephemeral notifications** (`db.notify(channel, payload)` / `db.listen(channel)`): Fire-and-forget messages; history not retained. Listeners attach at current `MAX(id)` without replay. Suitable for real-time alerts that don't require durability.
- **Durable streams** (`db.stream(name).publish()` / `.subscribe(consumer)`): Append-only event log with per-consumer offset tracking. Each named consumer tracks its own offset in `_honker_stream_consumers` table. Subscribers replay events past their last offset, then transition to live delivery on commit. Auto-saves offset every 1000 events or 1 second (configurable) to avoid thrashing the single-writer slot. At-least-once semantics: a crash re-delivers in-flight events up to the last flushed offset. Source: README.md lines 114–127.

### Work Queues

- **At-least-once delivery** with configurable `max_attempts` (default 3): Jobs are rows in `_honker_live` with state tracking (pending, processing, dead). Claim is one `UPDATE … RETURNING` via a partial index on `(queue, priority DESC, run_at, id) WHERE state IN ('pending','processing')`. Ack is one `DELETE`. If a worker crashes mid-job, the claim expires after `visibility_timeout_s` (default 300s) and another worker reclaims. After `max_attempts`, the row moves to `_honker_dead`. Source: README.md lines 229–235.
- **Priority queues** with delayed jobs and expiration: Partial index prioritizes by `(priority DESC, run_at, id)`, allowing high-priority jobs to jump the queue. `run_at` field gates delayed execution (tasks don't become claimable until `run_at <= now()`). Job expiration (`task_expires_at`) auto-moves expired rows to dead-letter on claim/sweep. Source: README.md lines 49.
- **Retry with exponential backoff**: `job.retry(delay_s=60, error=str(e))` increments `attempts` and sets next `run_at` via `delay_s` multiplier. Exponential backoff specified as `backoff=2.0` in task decorator. Declarative retries via `@queue.task(retries=3, timeout_s=30)` decorator pattern. Source: README.md lines 85–86, 96.
- **Task result storage** (opt-in): `Queue.save_result(job_id, value, ttl=None, tx=None)` persists job return values in `_honker_results` table. `Queue.wait_result(job_id, timeout=None)` blocks until a worker saves the result; wakes on WAL commit so cross-process job completion is detected within the stat-poll cadence. TTL-based expiration. Source: CHANGELOG.md "Unreleased — task result storage", lines 26–37.
- **Batch claiming and acking**: `claim_batch(worker_id, n)` returns up to `n` jobs at once. `queue.ack_batch(ids, worker_id)` deletes multiple ids in one transaction, reducing per-job overhead for high-throughput consumers. Iterator-based claiming via `async for job in q.claim(id)` calls `claim_batch(..., 1)` under the hood; batching hidden behind iterator for simplicity. Source: README.md lines 88–89, 244–245.
- **Declarative periodic tasks** with crontab scheduling: `@queue.periodic_task(crontab("0 3 * * *"))` registers recurring tasks. Leader-elected scheduler ensures one instance fires per period. Scheduler queries `SELECT honker_scheduler_tick(unixepoch())` to get due fires, updates `next_fire_at` to next cron boundary. `honker_cron_next_after(pattern, unixepoch())` computes next fire timestamp. Source: README.md line 54.

### Transactional Coupling

- **Outbox pattern built-in**: `queue.enqueue(..., tx=tx)`, `stream.publish(..., tx=tx)`, and `tx.notify(channel, payload)` insert rows into the caller's open transaction. Rollback drops the job/event/notification with the rest; no separate dispatch table. Enables atomic business write + side-effect enqueue in one commit. Source: README.md lines 38–42, 249–254.

### Lock and Rate Limiting

- **Named locks** with TTL: `Database.lock(name, owner, ttl_s)` context manager. Extension SQL: `jl_lock_acquire(name, owner, ttl_s)` returns 1 if acquired, 0 if held by another owner. `jl_lock_release(name, owner)` releases. Useful for mutual exclusion of scheduled tasks (one backup at a time). Source: README.md line 53, CHANGELOG.md "Batch 2 + scheduler" lines 85–86.
- **Rate limiting** with sliding windows: `Database.try_rate_limit(name, limit, per_s)` returns 1 if under limit, 0 if at limit. Tracks attempts in `_honker_rate_limits` with window-based bucketing. `Database.sweep_rate_limits(older_than_s)` prunes expired windows. Source: README.md line 53, CHANGELOG.md lines 88.

### SQLite Extension (Any Language)

- **Loadable extension** compatible with SQLite 3.9+: `SELECT load_extension('/path/to/libhonker_ext')` makes all `honker_*` SQL functions available. No language binding required; any SQLite client (C, Go, Java via JDBC, shell, etc.) gains access to queuing, streaming, locking, and cron functions as raw SQL. Schema is shared (`_honker_live`, `_honker_dead`, `_honker_notifications`, `_honker_streams`, `_honker_scheduler`, `_honker_results`); Python workers and Node.js enqueuers operate on the same tables. Source: README.md lines 160–187, 189.

### Language Bindings

- **Supported languages**: Python (PyO3), Node.js (napi-rs), Rust (in-tree), Go, Ruby, Bun, Elixir, C++ (all as git submodules pinned in main repo). Each binding is published independently (PyPI, npm, crates.io, Hex, RubyGems). Each language uses the same WAL-based wake mechanism and schema. Source: README.md lines 7, 59, 336–342.

### ORM Integration

- **No framework plugins**: Honker intentionally ships no FastAPI/Django/Flask-specific middleware. Instead, users load `libhonker_ext` on the ORM's connection (SQLAlchemy via `@event.listens_for(engine, "connect")`, Django via connection init) and call SQL functions inside the ORM's transaction. Workers run as a separate process using `honker.open("app.db")`. Source: README.md lines 60, 304–322.

---

## Technical Architecture

### Wake Mechanism

Honker replaces polling with a low-cost counter read:

- **Polling thread**: One per `Database` instance queries `PRAGMA data_version` every 1ms. This SQLite counter increments on every commit (by any connection, any journal mode) and is visible across processes.
- **Fan-out**: Counter change triggers a broadcast to all subscribers (listeners, queue claimers, stream readers) via bounded `SyncSender<()>` channels keyed by subscriber id.
- **Idle cost**: ~3.5 µs per query, ~3.5 ms/sec total at 1 kHz polling rate. Scales to 100+ subscribers for free because the wake signal is a counter read, not a per-listener query.
- **Fallback**: 5s paranoia poll if commit watcher can't fire; ensures liveness even if kernel notification delivery fails.

Source: README.md lines 217–227, honker-core architecture patterns.

### Queue Schema & Claim Path

```
_honker_live (id PRIMARY KEY, queue, payload, state, priority, run_at, attempts, max_attempts, visibility_expires_at, task_expires_at)
Partial index: (queue, priority DESC, run_at, id) WHERE state IN ('pending','processing')

Claim: UPDATE _honker_live SET state='processing', worker_id=?, visibility_expires_at=?
       WHERE queue=? AND state='pending' AND run_at <= now() AND id IN (
         SELECT id FROM _honker_live WHERE queue=? AND state='pending'
         ORDER BY priority DESC, run_at, id LIMIT 1
       ) RETURNING *;

Ack: DELETE FROM _honker_live WHERE id=? AND worker_id=?;

Retry-exhausted: UPDATE _honker_live SET state='dead' WHERE id=? AND attempts >= max_attempts;
```

Partial index bounds claim scan to working set (pending + processing rows only), not all history. Dead rows are never scanned by claim path. Source: README.md lines 229–245.

### Stream Consumer Offsets

```
_honker_streams (id AUTOINCREMENT, name, payload, created_at)
_honker_stream_consumers (id PRIMARY KEY, name, consumer, offset, last_saved_at)

Subscribe:
  1. SELECT offset FROM _honker_stream_consumers WHERE name=? AND consumer=?
  2. SELECT id, payload FROM _honker_streams WHERE name=? AND id > offset
  3. Iterator yields rows, auto-saves offset every 1000 events or 1 second

At-least-once: Crash before save → next subscribe() replays last unsaved batch
```

Per-consumer offset prevents one slow reader from blocking another. Auto-save batching amortizes flushing. Source: README.md lines 114–127.

### Transactional Outbox

Jobs, events, and notifications are INSERTs into caller's open transaction:

```python
with db.transaction() as tx:
    tx.execute("INSERT INTO orders (user_id) VALUES (?)", [42])           # business write
    queue.enqueue({"to": "alice@example.com"}, tx=tx)                     # enqueue in same tx
    # COMMIT: both rows committed, or neither
    # ROLLBACK: both dropped
```

No separate `_outbox` table or dispatcher process. The side-effect row *is* the committed row, and any process watching `PRAGMA data_version` picks it up within ~1ms. Source: README.md lines 38–42, 199–211.

### WAL as Recommended Default

Journal mode is configurable, but WAL is the default:

- **WAL benefits**: Concurrent readers while one writer is active. Efficient fsync batching (`wal_autocheckpoint = 10000`). More writes fit per disk I/O.
- **Data version**: Increments on every commit in every journal mode (DELETE, TRUNCATE, WAL). What you lose in non-WAL is concurrent-read-while-writing; correctness and wake do not depend on WAL. Source: README.md lines 203–213.

---

## Installation & Usage

### Python

```bash
pip install honker
```

```python
import honker

db = honker.open("app.db")
emails = db.queue("emails")

# Enqueue atomically with business write
with db.transaction() as tx:
    tx.execute("INSERT INTO orders (user_id) VALUES (?)", [42])
    emails.enqueue({"to": "alice@example.com"}, tx=tx)

# Consume (worker process)
async for job in emails.claim("worker-1"):
    try:
        send(job.payload)
        job.ack()
    except Exception as e:
        job.retry(delay_s=60, error=str(e))
```

Task decorators:

```python
@emails.task(retries=3, timeout_s=30)
def send_email(to: str, subject: str) -> dict:
    ...
    return {"sent_at": time.time()}

# Caller
r = send_email("alice@example.com", "Hi")
print(r.get(timeout=10))  # blocks until worker runs it

# Worker
# python -m honker worker myapp.tasks:db --queue=emails --concurrency=4
```

Streams:

```python
stream = db.stream("user-events")

with db.transaction() as tx:
    tx.execute("UPDATE users SET name=? WHERE id=?", [name, uid])
    stream.publish({"user_id": uid, "change": "name"}, tx=tx)

async for event in stream.subscribe(consumer="dashboard"):
    await push_to_browser(event)
```

Source: README.md lines 19–34, 64–127.

### Node.js

```bash
npm install @russellthehippo/honker-node
```

```javascript
const { open } = require('@russellthehippo/honker-node');
const db = open('app.db');

const tx = db.transaction();
tx.execute('INSERT INTO orders (id) VALUES (?)', [42]);
tx.notify('orders', { id: 42 });
tx.commit();

for await (const n of db.listen('orders')) {
  handle(n.payload);
}
```

Source: README.md lines 142–158.

### SQLite Extension (Any Client)

```sql
.load ./libhonker_ext
SELECT honker_bootstrap();

-- Enqueue
INSERT INTO _honker_live (queue, payload) VALUES ('emails', '{"to":"alice"}');

-- Claim
SELECT honker_claim_batch('emails', 'worker-1', 32, 300);    -- JSON array

-- Ack
SELECT honker_ack_batch('[1,2,3]', 'worker-1');              -- DELETEs; returns count

-- Sweep expired
SELECT honker_sweep_expired('emails');                       -- count moved to dead

-- Locks
SELECT honker_lock_acquire('backup', 'me', 60);              -- 1 = got it, 0 = held
SELECT honker_lock_release('backup', 'me');                  -- 1 = released

-- Rate limiting
SELECT honker_rate_limit_try('api', 10, 60);                 -- 1 = under, 0 = at limit

-- Cron
SELECT honker_cron_next_after('0 3 * * *', unixepoch());     -- unix ts of next fire

-- Scheduler
SELECT honker_scheduler_register('nightly', 'backups', '0 3 * * *', '"go"', 0, NULL);
SELECT honker_scheduler_tick(unixepoch());                   -- JSON: fires due

-- Streams
SELECT honker_stream_publish('orders', 'k', '{"id":42}');    -- returns offset
SELECT honker_stream_read_since('orders', 0, 1000);          -- JSON array

-- Results
SELECT honker_result_save(42, '{"ok":true}', 3600);          -- save w/ 1h TTL
SELECT honker_result_get(42);                                -- value or NULL
```

Source: README.md lines 160–187.

### ORM Integration (SQLAlchemy Example)

```python
from sqlalchemy import event, create_engine, text

engine = create_engine("sqlite:///app.db")

@event.listens_for(engine, "connect")
def _load_honker(conn, _):
    conn.enable_load_extension(True)
    conn.load_extension("/path/to/libhonker_ext")
    conn.execute("SELECT honker_bootstrap()")

with Session(engine) as s, s.begin():
    s.add(Order(user_id=42))
    s.execute(text("SELECT honker_enqueue(:q, :p, NULL, NULL, 0, 3, NULL)"),
              {"q": "emails", "p": '{"to":"alice@example.com"}'})

# Workers run as separate process
# honker.open("app.db")
```

Source: README.md lines 308–320.

---

## Performance Characteristics

- **Cross-process wake latency**: Single-digit to low double-digit milliseconds (1–2ms median on M-series hardware). Bounded by 1ms poll cadence on `PRAGMA data_version`. Source: README.md line 9, 326.
- **Throughput**: Thousands of messages per second on a modern laptop. Exact throughput depends on message size, claim batch size, and disk I/O. Benchmarks available via `bench/wake_latency_bench.py` and `bench/real_bench.py`. Source: README.md lines 324–327.
- **Idle cost**: ~3.5 µs per `PRAGMA data_version` query, ~3.5 ms/sec total at 1 kHz. Negligible CPU impact for idle listeners. Source: README.md line 212.

---

## Crash Recovery

- **ACID semantics**: Rollback drops jobs/events/notifications with business write (standard SQLite ACID). SIGKILL mid-transaction is safe; SQLite's atomic-commit on next open leaves no stale state (verified in `tests/test_crash_recovery.py`). Source: README.md lines 273–277.
- **Worker crash**: Claim expires after `visibility_timeout_s` (default 300s); another worker reclaims. `attempts` increments. After `max_attempts`, row moves to `_honker_dead`. Source: README.md line 276.
- **Listener offline during prune**: Listeners offline during notification pruning miss pruned rows. For durable replay, use `db.stream()` which tracks per-consumer offsets. Source: README.md line 277.

---

## Limitations and Caveats

- **Single machine, single writer**: SQLite locking is designed for a single host. Two servers writing one `.db` over NFS will corrupt it. Shard by file or switch to Postgres. Source: README.md line 213.
- **Notification auto-pruning**: Notifications table is not auto-pruned. Call `db.prune_notifications(older_than_s=…, max_keep=…)` from a scheduled task if your application generates high-volume notifications. Source: README.md line 140.
- **Experimental API**: Version 0.2.1 is marked experimental; API may change. Source: README.md line 11.
- **No task pipelines/chains/DAGs**: Honker deliberately omits Celery-style task chaining, grouping, or DAG orchestration. It is a task queue, not a workflow orchestrator. Source: README.md line 62.
- **Framework integration requires manual setup**: No FastAPI/Django/Flask plugins provided. Integrations are a few lines of glue code, but are not packaged. Source: README.md lines 60, 280.
- **No replication or multi-writer support**: Single-file, single-writer model rules out built-in multi-host replication. Backup and restore are standard SQLite backup tools; there is no cluster-aware replication. Source: README.md line 213.

---

## Relevance to Claude Code Development

### Applications

- **Async task orchestration for code generation**: Claude Code agents often spawn long-lived tasks (linting, testing, code generation). Honker provides at-least-once job queues with retries and priority — ideal for modeling task dependencies and worker pools without Redis.
- **Cross-agent communication via durable streams**: Multi-agent workflows need reliable event broadcast. Honker's stream primitive with per-consumer offset tracking enables agents to subscribe to domain events (e.g., "code generated", "test passed") and resume from their last offset after restart.
- **Embedded in Claude Code plugins**: Plugins that need internal pub/sub (e.g., skill creation workflows, plugin lifecycle events) can use honker as the in-process event bus — same file, same transaction as plugin state.
- **Task result storage for RPC-like patterns**: Some agent tasks need to return values to callers (e.g., "run linter, wait for results"). Honker's opt-in result storage enables `job_id = enqueue(...); result = wait_result(job_id, timeout)` patterns.

### Patterns Worth Adopting

- **Transactional coupling**: Honker's outbox pattern — enqueue side effects in the same transaction as business logic — is applicable anywhere state and messaging interact. Eliminates dual-write race conditions and simplifies crash recovery.
- **Per-consumer offset tracking for replay**: For event streaming (skill lifecycle, code generation steps, test results), per-consumer offsets enable each agent or plugin to resume from its last offset without losing events.
- **Partial-index queue optimization**: The technique of using a partial index to bound scan to active rows (not all history) is transferable to any SQLite-backed queue or similar pattern.
- **Single-digit-millisecond wake via counter polling**: The `PRAGMA data_version` polling pattern achieves sub-second latency without kernel watchers or broker overhead. Applicable to SQLite-based coordination in any Python/Node agent.

### Integration Opportunities

- **Claude Code plugin event bus**: Honker could serve as the internal event bus for plugin lifecycle, skill registration, and inter-plugin coordination. Plugins load the extension once on the shared `.db`, and all plugins can publish/subscribe to a unified event stream.
- **Agent task queue for distributed skill execution**: Multi-machine Claude Code deployments (future) could use honker as a durable task queue, with agents pulling work from a central `.db` and reporting results back without separate Redis.
- **Development-harness task tracking**: The existing development-harness backlog could migrate from custom JSON state to honker streams for more robust crash recovery and per-consumer offset tracking.

---

## References

- [Honker Repository](https://github.com/russellromney/honker) (accessed 2026-04-25)
- [Honker Documentation](https://honker.dev) (accessed 2026-04-25)
- [Honker README](https://github.com/russellromney/honker/blob/main/README.md) (accessed 2026-04-25)
- [Honker CHANGELOG](https://github.com/russellromney/honker/blob/main/CHANGELOG.md) (accessed 2026-04-25)
- [Honker CONTRIBUTING](https://github.com/russellromney/honker/blob/main/CONTRIBUTING.md) (accessed 2026-04-25)
- [honker-core Cargo.toml](https://github.com/russellromney/honker/blob/main/honker-core/Cargo.toml) (accessed 2026-04-25)
- [honker-extension Cargo.toml](https://github.com/russellromney/honker/blob/main/honker-extension/Cargo.toml) (accessed 2026-04-25)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [PocketBase](./pocketbase.md) | data-infrastructure | Shared: embedded SQLite backend, realtime subscriptions, multi-language bindings (Go+Python/Node.js/Dart), single-file deployment model |
| [Saga-mcp](../mcp-ecosystem/saga-mcp.md) | mcp-ecosystem | Shared: SQLite-backed task tracking, dependency graphs, per-consumer offset patterns, immutable activity logs |
| [Dolt](./dolt.md) | data-infrastructure | Version-controlled alternative to embedded SQLite; competing approach for distributed agent workflows with Git-like semantics |
| [Beads (bd)](../task-management/beads.md) | task-management | Hash-based distributed task graphs for multi-agent coordination; honker's queue/stream patterns complement Beads' dependency resolution |
| [Trigger.dev](../agent-infrastructure/trigger-dev.md) | agent-infrastructure | Task orchestration and durable job execution; honker's at-least-once queue provides an embedded SQLite alternative to Trigger's cloud broker model |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-25 |
| Version at Verification | 0.2.1 (honker-core, honker-extension) |
| Next Review Recommended | 2026-07-25 |
| Confidence Map | Overview: high (README), Problem Addressed: high (README + design rationale), Key Statistics: low (version only; star count not accessible), Key Features: high (README + CHANGELOG code examples), Technical Architecture: high (README architecture section + in-code patterns), Installation & Usage: high (README code examples verbatim), Performance Characteristics: medium (benchmarks exist but not run; latency claims from README design section), Crash Recovery: high (documented in README + test references), Limitations: high (explicitly stated in README + source constraints), Relevance to Claude Code: medium (speculative application; not yet integrated) |
