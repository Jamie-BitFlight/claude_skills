# Improvement Proposals: gentle-ai

**Research entry**: ./research/agent-frameworks/gentle-ai.md
**Generated**: 2026-10-03
**Patterns assessed**: 6
**Backlog items created**: 0 (issues: none)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 4

Note: `mcp__plugin_dh_backlog__backlog_list` returned a GraphQL-unavailable error in this environment, so the duplicate check could not run. No backlog items were created. Neither proposal below reached High confidence, so none would have qualified regardless.

---

## Improvement 1: Project-level decision/rationale store searchable across sessions

**Source pattern**: "Integration Opportunities" — "extend dh's backlog_core to store architectural decisions and design rationale alongside task tracking" (Engram: SQLite + FTS5 observations typed decision|bug|pattern, queried via mem_search at session start).
**Local system**: `plugins/development-harness/backlog_core/ARCHITECTURE.md`, `plugins/plugin-creator/skills/memory-and-rules/SKILL.md`
**Absence evidence**: `git grep -ilE "engram" -- plugins/ .claude/skills/ .claude/agents/ rules/` -> 0 matches. `git grep -ilE "mem_save|session_summary" -- plugins/ .claude/skills/ .claude/agents/ rules/` -> 1 match (`plugins/frustration-analyzer/mcp/server.py`, not opened; relevance unverified). No search was run for a decision-record store (ADRs exist under `plugins/development-harness/docs/adrs/` and `rules/adr-lifecycle.md`), so absence of a queryable decision store is not established.
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred — confidence Medium: the entry gives only a "could complement" suggestion; Claude Code auto memory and ADRs already cover part of this need

### Current state

`memory-and-rules/SKILL.md` documents two persistent memory kinds (auto memory at `~/.claude/projects/<project>/memory/`, loaded to the first 200 lines of `MEMORY.md`, and CLAUDE.md files). Decisions are recorded as ADRs under `plugins/development-harness/docs/adrs/`. No FTS-queryable cross-session store of typed observations was found by the searches above.

### Target state

To be defined only after verifying (a) what auto memory plus ADRs fail to recall in practice and (b) whether `backlog_core` is the right owner. Candidate: a decision-record query tool exposed by the backlog MCP server.

### Measurable signal

Not yet definable. Would require a documented session where a prior decision was not recovered despite ADR and auto memory availability.

---

## Improvement 2: Frozen-candidate (revision-pinned) review evidence

**Source pattern**: "RDD (Receipt-Driven Development)" — "Change is locked to a lineage, revision, and target before any lens is applied"; risk-based review depth with bounded correction.
**Local system**: `plugins/development-harness/skills/complete-implementation/SKILL.md` (not opened this session; path is the system-map default and its content is unverified)
**Absence evidence**: `git grep -ilE "frozen candidate|receipt-driven|lineage" -- plugins/ .claude/skills/ .claude/agents/ rules/` -> 3 matches, none a review skill (`harness-kilo-code.md`, `hook-creator.md`, `prefect.md`). Not searched: how `complete-implementation`, `rules/review-and-correction-discipline.md`, or the review-verdict-contract skill bind review evidence to a commit SHA.
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence Low: local review skills were not read, so it is unknown whether verdicts are already pinned to a revision

### Current state

Unverified. The local review contract files were not examined.

### Target state

If review verdicts are not currently tied to a specific commit SHA, add a required `reviewed_revision` field to the review verdict contract and have the gate reject verdicts whose revision differs from HEAD.

### Measurable signal

Verdict artifact contains `reviewed_revision`; gate output reports a mismatch when the tree changes after review. Verify by reading the verdict contract and running the gate against a modified tree.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Project-level decision/rationale store (Engram) | medium | Verify what auto memory and ADRs fail to recall, and read `plugins/frustration-analyzer/mcp/server.py` match |
| Frozen-candidate review (RDD) | low | Read `complete-implementation/SKILL.md`, `rules/review-and-correction-discipline.md`, and the review-verdict-contract skill |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| GGA pre-commit validation against AGENTS.md | The entry's Change is an edit to `.pre-commit-config.yaml` adding an AI-review hook, with the GGA invocation unconfirmed; tracked as Utilization 1 in the utilization file rather than backlogged here |
| ODD authorization gate and task artifact | Entry records "none — out of scope": `plugins/development-harness/docs/backlog-lifecycle.md` already gates stage transitions, and the entry documents no transition API dh could call |
| Cross-agent skill/config synchronization | Entry records "none": `scripts/generate_harness_compatibility.py` and `AGENTS.md` line 94 already cover cross-harness generation |
| Installer-style config backup, doctor, sync --dry-run | Entry names these but proposes no local change; Relevance section does not tie them to a local file, so no grounded gap |
