# Improvement Proposals: Foreman

**Research entry**: ./research/agent-frameworks/foreman.md
**Generated**: 2026-10-03
**Patterns assessed**: 13
**Backlog items created**: 0. The backlog duplicate check failed (`mcp__plugin_dh_backlog__backlog_list` returned "GraphQL is unavailable in this environment"), so no item was created. Improvement 1 qualifies for P1 and is still waiting for a backlog item.
**Deferred (confidence too low to backlog)**: 3
**Skipped (already covered or tracked)**: 9

The entry's own "Relevance to Claude Code Development" section marks all four of its mappings `Change: none`. I assessed the patterns in its Key Features and Technical Architecture sections directly against the dh work ledger. That ledger is the local system that runs the role Foreman's Factory and policy arbiter run.

---

## Improvement 1: Bound an open attempt's total duration so that a runner which keeps renewing its lease cannot hold a task in-progress indefinitely

**Source pattern**: Technical Architecture > Core Components > Factory: "Manages worker lifecycle, event queues, observation bounds ..., iteration/retry/timeout limits". Policy Directives: "A worker crossing off-track/stuck/drift thresholds is steered once ...; repeated high scores trigger stop/retry". Foreman bounds how long a live worker may run, not only how many times it may be retried.
**Local system**: `plugins/development-harness/dh_core/ledger_spec.py` (the `renew` transition, the `_renew_effects`, `CONFIG`), `plugins/development-harness/dh_core/ledger/derive.py` (`stale_row`), `plugins/development-harness/docs/work-ledger/work-loop.md` (judge rows J5, J7, J8)
**Absence evidence**: `git grep -n -c "first_renewed" -- plugins/development-harness/dh_core/ledger/derive.py plugins/development-harness/dh_core/ledger/queries.py` returns 0 matches (exit 1). Every remaining non-test reference to `first_renewed` writes it or resets it: `ledger_spec.py:957,1011`, `transitions.py:753,828,1764`, `store.py:1156,1226,1240-1241`. None reads it to make a decision. `ledger_spec.py` `CONFIG` declares only `lease.ttl_seconds` (1800) and `loop.max_attempts` (3).
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created. Priority P1 per the matrix. The duplicate check could not run because `backlog_list` failed with "GraphQL is unavailable in this environment". Create the item once the backlog server is reachable and the duplicate check passes.

### Current state

- `derive.stale_row` returns true only when the attempt is open and `now > expires + ttl_seconds`. Staleness therefore measures liveness, meaning time since the last renew. It does not measure total attempt duration.
- The `renew` transition (`ledger_spec.py` lines 1082-1092) checks only `stale-attempt`, `attempt-closed` and `unmatched-path`. It has no check that refuses a renew once an attempt has run past some ceiling. Each renew sets `expires = now + ttl_seconds`. `read --attempt N` and `update --attempt N` also renew.
- `first_renewed` is written on the first renew (`COALESCE(first_renewed, :now)`) and cleared on reclaim, but no derived column, query or judge row reads it.
- In `work-loop.md`, J5 (`in-progress`, launch still running) says `wait` and J7 says `wait until stale`. As long as a runner issues any `read`, `update` or `renew` with its attempt number at least every 30 minutes, the task stays in-progress with no limit. No row reports how long the attempt has been open. `loop.max_attempts` bounds reclaims, which only happen after an attempt ends, so it never triggers for an attempt that never ends.

### Target state

- `ledger_spec.CONFIG` gains a key (for example `lease.max_attempt_seconds`) with a documented default and `used_by` text.
- `ledger_spec.COLUMNS` gains a derived task column (for example `overrun`). It is true when the attempt is open and `now - started` (or `now - first_renewed`, whichever the spec chooses and states) exceeds that ceiling. It is computed in `derive.py` next to `stale_row`, and `status --plan-address P` returns it with the other derived columns.
- One of the following is in place:
  - `renew` refuses with a new reason code (registered in `ledger_spec.REASONS`) once the attempt is overrun.
  - Or `work-loop.md` gains a judge row for `in-progress` with `overrun` true, which routes to `reclaim --reason overrun` or to the user. That reason is added to `reclaim`'s accepted reasons.
- `runner-contract.md` states what a runner does when its renew is refused for overrun.

### Measurable signal

- `git grep -n "first_renewed\|overrun" -- plugins/development-harness/dh_core/ledger/derive.py` returns at least one match that reads the value.
- `uv run "plugins/development-harness/sam_schema/cli.py" plan status --plan-address P` on a ledger plan includes the new derived column for each task row.
- A test under `plugins/development-harness/dh_core/` covers this sequence: dispatch a task, renew repeatedly with a frozen clock advanced past the ceiling while staying inside `ttl_seconds` between renews, then assert that the new column is true (or that the renew is refused with the new reason code), while `stale` stays false.
- `work-loop.md`'s judge table has a row whose `observed` cell names the new column or reason code.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Steer a running worker once, then stop/retry if it stays off-track (Policy Directives; Worker Backend Abstraction `turn/steer`) | Medium | `work-loop.md` J5 tells the orchestrator only to `wait` while a launch runs, and the ledger has no `steer` command. Whether in-flight steering is possible depends on the harness: `plugins/development-harness/docs/work-ledger/measurements/harness-hermes.md` records a Hermes `steer` action, and the other harnesses are not established here. AGENTS.md requires checking `plugins/development-harness/CLAIMS-REGISTER.md` and the per-harness measurements before planning an agent or harness change. To raise confidence, establish which harnesses can deliver a message to a running sub-agent, and whether a semantic "off-track" signal can be produced without an external scoring service. |
| Queryable run timeline, like `foreman inspect <run-id>` (Persistent State and Inspection) | Medium | `dh_core/ledger/store.py` keeps an append-only `events` table, and `events_of()` (line 885) reads it. `git grep -n "events_of" -- plugins/development-harness` finds no caller outside tests and `graphify-out/graph.json`, and `sam_plan.py` has no `history`/`events` command. However, per-attempt report sections are already returned by `read` (`transitions.sections_of`, ordered by attempt). `tasks.response` holds only the latest reclaim response, so earlier reclaim reasons and responses are reachable only through `events`. To raise confidence, confirm whether `work-loop.md` J15 ("put the attempt history to the user") can be met from `read` output alone, or whether it needs the reclaim events. |
| Deterministic demo mode: full runtime with a mock worker and model, no network or API key (Deterministic Demo Mode) | Low | Not checked. I did not search the ledger's tests for an end-to-end simulated work loop (dispatch, runner, settle, judge). To raise confidence, run `git grep -il "fake.*runner\|simulat" -- plugins/development-harness/dh_core plugins/development-harness/sam_schema/tests` and read any hits before claiming the capability is absent. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Liveness-based stuck-worker detection (`worker_stuck` as no-activity) | Already covered: `dh_core/ledger/derive.py` `stale_row` together with `work-loop.md` J8 (`reclaim --reason stale`). The duration gap that remains is Improvement 1. |
| Retry bound with escalation to a human (iteration bounds; `ESCALATE`) | Already covered: `ledger_spec.CONFIG` `loop.max_attempts` (default 3), the `reclaim` refusal `attempts-exhausted` (`transitions.py:1622-1623`), and `work-loop.md` J15, which puts the attempt history to the user. |
| Atomic state plus append-only event log (`state.json` / `events.jsonl`) | Already covered, in a stronger form: `dh_core/ledger/store.py` derives every materialised table as a fold over the `events` table (`fold_events`, `rebuild`), and each transition writes its state and its events in one transaction. |
| Safety-first deterministic policy arbiter over scored proposals | Already covered in spirit: `work-loop.md`'s judge table (J1-J20) is a deterministic mapping from observed state to a single command. There is no probability input to arbitrate, because the local system does not score anything. |
| Jev probabilistic checks (`implementation_complete`, `tests_sufficient`, `needs_human`, and others) | Incompatible: they depend on TypeSafe AI's external authenticated service (`TYPESAFE_API_KEY`). The research entry's Integration Opportunities marks it out of scope, and its Limitations section says Jev's accuracy for this use is "unproven". |
| `agents_md_drift` check | Covered by a different mechanism: `plugins/development-harness/agents/doc-drift-auditor.md` and `plugins/development-harness/skills/audit-documentation-drift/SKILL.md`. Foreman runs its check during a run; the local equivalents run on demand. A live check needs the scoring service already ruled out above. |
| Size-bounded observations (20,000-char diff, 12,000-char output tails) | Incompatible: AGENTS.md "No Invented Limits" forbids truncating content a consumer needs to read. |
| Trusted evidence commands declared in central user config rather than repository code | Incompatible by design: the dh harness deliberately discovers quality-gate commands from the repository's own pre-commit config, CI workflow or build config (`plugins/development-harness/AGENTS.md`, Voltron-Style Composition). |
| Hook session storage keyed by a SHA256 of client and session ID, to prevent path injection | No local instance to harden: `git grep -n -i "session_id" -- '.claude/hooks/*' 'plugins/*/hooks/*' plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py` filtered to path, join, mkdir and open usages found no hook that builds a filesystem path from `session_id`. The only path built from it is an HTTP route in `plugins/dot-dash/hooks/prompt-injector.cjs:19`, which is wrapped in `encodeURIComponent`. |
| Tolerating consecutive transient assessment failures (`FOREMAN_MAX_CONSECUTIVE_ASSESSMENT_FAILURES`) | Not applicable: there is no periodic assessment loop locally, so there is nothing for this tolerance to apply to. |
