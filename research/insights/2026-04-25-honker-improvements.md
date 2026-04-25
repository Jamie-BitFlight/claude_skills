# Improvement Proposals: Honker

**Research entry**: ./research/data-infrastructure/honker.md
**Generated**: 2026-04-25
**Patterns assessed**: 4
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Reduce dispatch poll cadence (2s `asyncio.sleep` -> sub-second wake) | Low | The honker mechanism is SQLite-specific (`PRAGMA data_version`). Local `_poll_until_done` in `plugins/development-harness/backlog_core/server.py:4200` polls a filesystem result-file path written by a spawned `claude` subprocess, not a SQLite DB. To adopt the honker mechanism the dispatch state would have to migrate into SQLite first — architectural change, not extension. A degenerate "lower the sleep value" change is possible but is not what the research entry proposes and has independent trade-offs (CPU burn, fs syscall pressure on slow disks). To raise confidence: measure actual end-to-end dispatch latency under load and confirm the 2s sleep is the dominant factor rather than spawn cost or git-worktree setup. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Transactional outbox — enqueue side-effects in same tx as business write | Premise absent. `plugins/development-harness/backlog_core/backends/sqlite_backend.py` (1134 lines, 13 `conn.commit()` sites) has no async-dispatch / queue / outbox table at all. There is no "side-effect row" co-tx'd with "business write" because the backend writes only its own item/milestone state. Adopting an outbox requires first introducing an in-process queue table — that is architectural replacement, not extension. |
| Per-consumer offset tracking for stream replay | Premise absent. Local agent coordination is file-based (SAM task YAML files, dispatch result files, GitHub Issues as source of truth). There is no event stream and no consumer table. Adopting per-consumer offset tracking requires first introducing an event log — architectural addition, not gap-fill. The 2026-03-28 PocketBase improvements file already deferred a structurally identical SSE-notification proposal on the same grounds (`research/insights/2026-03-28-pocketbase-improvements.md` line 18). |
| Partial-index queue optimization (`WHERE state IN ('pending','processing')`) | Premise absent. No queue table exists in `sqlite_backend.py`. The backend's `items` table tracks issues, not work-items with a state machine of pending/processing/dead. There is nothing for the partial index to bound a scan over. |
| Honker as plugin event bus / cross-agent durable stream / migration from "custom JSON state" | Speculative recommendations from the entry's own "Integration Opportunities" section. The premise ("custom JSON state" in development-harness) is factually incorrect — the backend is SQLite-backed with GitHub Issues as source of truth. No actionable observable gap. |

---

## Assessment Summary

The research entry's "Relevance to Claude Code Development" section enumerates speculative future-state applications ("could serve as", "could migrate") rather than naming gaps in existing local systems. Each "Pattern Worth Adopting" presupposes architectural primitives the local systems do not have: an in-process async dispatch queue, an event stream, a consumer offset table, or SQLite-backed dispatch state. Adopting any of these would mean introducing the missing primitive first — that is architectural addition, not gap-filling.

The single observable difference (2s `asyncio.sleep` polling cadence in `_poll_until_done` vs honker's 1ms `PRAGMA data_version` cadence) is too weakly grounded to backlog: the local code does not poll SQLite, so the honker mechanism does not directly apply, and reducing the sleep value alone is not what the research entry proposes.

Per gap-rule 3 in the agent definition: "the gap can be described as a specific observable state in a file, script output, or command result." None of the four patterns satisfy this when measured against the actual local files.
