# Improvement Proposals: Tessera

**Research entry**: ./research/security-tools/tessera.md
**Generated**: 2026-06-29
**Patterns assessed**: 5
**Backlog items created**: 1 (local-only — GitHub offline at creation time, no issue number assigned; file: p1-add-exponential-backoff-with-jitter-to-kage-bunshin-spawn-la.yaml)
**Deferred (low confidence)**: 1
**Skipped (already covered, not applicable, or policy conflict)**: 3

---

## Improvement 1: Add exponential backoff with jitter to kage-bunshin spawn launcher

**Source pattern**: "Resilience: `RunWithBackoff()` method implements exponential backoff (1s–30s capped) with jitter to recover from Wi-Fi flaps and coordinator hiccups" (Architecture Overview → Agent; restated in Core Components → Agent → Resilience pattern)
**Local system**: ./plugins/development-harness/skills/kage-bunshin/scripts/spawn.py
**Confidence**: High
**Impact**: Medium
**Backlog**: Created — p1-add-exponential-backoff-with-jitter-to-kage-bunshin-spawn-la.yaml (P1, Feature; no GitHub issue number — backend was offline)

### Current state

`spawn.py` waits for the claude-owned tmux session to appear with a fixed-interval poll
(`while not _tmux_alive(claude_tmux_session): ... time.sleep(0.5)`, lines 753–758) followed by a
single fixed `time.sleep(_CLAUDE_INIT_WAIT_SECONDS)` (line 761). On the first transient failure —
`tmux new-session` returning non-zero (lines 749–750) or the claude session not appearing before
the deadline (lines 755–757) — the launcher calls `_die(...)` and the spawn aborts with no retry.
Grep of `plugins/development-harness/` for `backoff`, `jitter`, `exponential` returns zero matches;
every sleep in the spawn path is a fixed constant.

### Target state

The wait-for-claude-session block (and optionally the `tmux new-session` launch) is wrapped in a
bounded retry loop with exponential backoff and jitter: initial delay ~1s, doubling per attempt,
capped at ~30s, with per-attempt random jitter, and a maximum attempt/total-time budget after which
it `_die()`s with a clear message. Backoff parameters are module-level named constants
(e.g. `_BACKOFF_INITIAL_SECONDS`, `_BACKOFF_CAP_SECONDS`, `_BACKOFF_MAX_ATTEMPTS`).

### Measurable signal

Run: `grep -n backoff plugins/development-harness/skills/kage-bunshin/scripts/spawn.py` returns at
least one match. The wait block uses a delay that increases across attempts (not a constant
`time.sleep(0.5)`) and adds jitter via `random`. A unit test in
`plugins/development-harness/tests/` simulates a session that appears only on attempt N>1 and asserts
the spawn succeeds rather than dying on the first miss.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Append-only audit trail with `fsync()` per event and hashed sensitive tokens (`hex(sha256(canonical-code))` in the Token field, never raw) — audit.go | Low | The repo already maintains append-only JSONL exports (`backlog_core/jsonl_utils.py`, `.beads/issues.jsonl`) and artifact registration. No concrete local surface logs a secret/token that would benefit from the hash-before-write mechanism, and no observable failure mode (data loss, secret leak) was identified in a local file. Raising to actionable would require finding a specific local code path that writes a secret to a log in cleartext — none was found. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| User-controllable audit fields capped at 256 characters to prevent log-bloat attacks (audit.go) | Direct policy conflict with `.claude/CLAUDE.md` → "No Invented Limits" (no hard-coded truncation on content a consumer needs to read). Adopting a fixed 256-char cap would violate a standing repo rule, so it is not a valid improvement here. |
| Per-IP rate limiting on bootstrap HTTP endpoints (coordinator/ratelimit.go) | Not applicable to this repo's architecture — there is no public HTTP bootstrap endpoint surface in the dh tooling. Tessera's coordinator is a network broker; this repo's tooling is local MCP servers and CLIs with no untrusted inbound HTTP. |
| Two-layer TLS / mTLS and synchronous human-at-terminal consent approval flow (Security Model) | Tessera's core domain (remote-host access broker). No local system maps; the swarm plan-approval gate (swarm-operations) is an in-process orchestration mechanism, not a network-access consent flow. Incompatible with this repo's architecture — stated explicitly per gap rules. |
