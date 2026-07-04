# Improvement Proposals: Flue — The Agent Harness Framework

**Research entry**: ./research/agent-frameworks/flue.md
**Generated**: 2026-07-03
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered, incompatible, or deliberately rejected)**: 6

---

## Summary

Flue's "Relevance to Claude Code Development" section is populated, so this entry was assessed
in full. However, the relevance is framed at the level of "production-grade reference
implementation for study" rather than concrete mechanisms this repo lacks. Every concrete
mechanism Flue documents falls into one of three buckets:

1. **Already implemented** in this repo (composable markdown skills, typed tool/task contracts).
2. **Architecturally incompatible** — Flue owns its agent tool/conversation loop and its durable
   persistence layer; this repo delegates the agent runtime to Claude Code and cannot add
   tool-outcome-level durable replay or in-process conversation resume to a runtime it does not
   own. The harness sits *on top of* the agent runtime.
3. **Deliberately rejected** — Flue's atomic tool-result-batch commit is the exact
   compare-and-swap pattern this repo evaluated and rejected in ADR-2509-3 (no CAS primitive
   exists in the GitHub API; the repo uses Serialized Dispatch instead).

No gap reached High confidence. Two feature-level absences (session schema versioning,
OpenTelemetry observability) are recorded as Deferred because the entry describes them as
features/caveats without a concrete observable mechanism, and confirming the gap would require
investigation the entry does not support.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Session schema versioning + migration for custom persistence adapters ("Custom persistence adapters must implement schema versioning and migration logic" — Limitations §Documented, line 223) | Low | Stated as a Flue *caveat*, not a mechanism to adopt. The repo has a `TaskBackend` Protocol with four backends (`sam_schema/core/task_backend.py`) but whether any schema-version field or migration path exists is not established. Raising to actionable would require reading `sam_schema/core/models.py` and each backend to confirm absence of a version field and a migration hook — the entry provides no observable before/after target. |
| OpenTelemetry observability for agent runs (Observability §, line 92; "Monitor agents and export telemetry via OpenTelemetry, Braintrust, Sentry") | Low | Listed as a framework *feature*, not a concrete mechanism with an observable target state. This repo emits no agent-run telemetry, so an absence exists, but adding a telemetry subsystem is a large architectural addition (not an extension of an existing file), and the entry gives no specific span/metric contract to implement. Would need a design decision on what to instrument before it could be expressed as a measurable gap. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Durable Execution — tool outcomes durably recorded before an atomic commit; "Recovery reuses known outcomes and materializes unknown interrupted outcomes" (Durable Execution §, lines 76–77) | Architecturally incompatible. This repo does not own the agent tool/conversation loop — Claude Code does. `task_status_hook.py` records only task-level status transitions (COMPLETE/FAILED) and `last-activity`/`completed` timestamps via SAM MCP; it cannot durably record or replay individual in-flight tool outcomes because those live inside the Claude Code runtime, not the harness. The gap rule "external approach is incompatible with this repo's architecture" applies. |
| Subagent in-process resume — "recovery resumes in-flight, model-invoked subagents in-process from their durable conversation" (Subagents §, line 80) | Architecturally incompatible. `swarm-operations/SKILL.md` §"Handling Crashed Teammates" (lines 311–318) documents the actual local model: crashed teammates are marked inactive after a 5-minute heartbeat timeout and their tasks are re-claimed and re-executed from scratch. Resuming "from durable conversation" requires durable conversation state owned by the Claude Code runtime, which the harness cannot access or replay. |
| Atomic tool-result batch commit — "one atomic commit publishes a complete tool-result batch" (Durable Execution §, line 77) | Deliberately rejected in this repo. `development-harness/CLAUDE.md` §"claim_task atomicity decision (ADR-2509-3)" records that GitHub REST/GraphQL provide no conditional/atomic mutation primitive and Gist read-modify-write has no compare-and-swap; the repo chose Serialized Dispatch (Option 3) instead. Proposing atomic commit would contradict an existing ADR. |
| Type-safe tool/task contracts with input/output schemas — "Tool definitions now use `input`, `output`, and `run` with optional Valibot input schemas" (Tools §, line 83; Key Design Decisions, line 139) | Already covered. This repo uses Pydantic models for all task/plan contracts (`sam_schema/core/models.py`, the authoritative `Task`/`Plan` models per `development-harness/CLAUDE.md`) and `@dh:contract-verification` verifies signatures against the architect spec. Equivalent-or-stronger local implementation exists. |
| Composable markdown skills loaded on demand — "Skills are loaded as markdown files with embedded expertise and can be packaged for distribution" (Skills §, line 86) | Already covered. This is the entire architecture of this repository — SKILL.md files with progressive disclosure, loaded on demand via the Skill tool. No gap. |
| Durable segment size limit — "Interrupted stream recovery rejects segments larger than 1.9 MB" (Limitations §, line 224) | Flue-internal implementation constant tied to its stream-recovery mechanism (itself incompatible, see rows 1–2). Maps to no local system and expresses no adoptable pattern. |

---

*No High-confidence actionable gap was found. This is a genuine no-actionable-improvements
outcome for a research entry whose value is as a reference implementation rather than a source
of extensions to this repo's existing systems. Per the confidence gate, Medium/Low-confidence
gaps are recorded as Deferred and produce no backlog items.*
