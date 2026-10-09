# #3223 architecture decision checkpoint — 2026-10-08

## Purpose

Preserve the current research and prevent an unverified implementation preference from becoming the product architecture. This checkpoint belongs to #3223 and draft #4101. It is not an approved architecture or an implementation acceptance report.

## Required outcome

Given a pinned repository revision and a workflow question/change, return an evidence-backed account of actors, transitions, conditions, handoffs, tools, artifacts, failures, terminal outcomes, and relevant consumers. Record investigated scope, unresolved relationships, contradictions, and verification evidence. Support impact analysis, change comparison, test design, and optionally graph projection. Never claim complete knowledge of arbitrary prose.

## Three configurations to compare

| Configuration | Primary approach | Key risk |
|---|---|---|
| A — scoped trace | Independently reconstruct affected paths from source each time | Hidden consumers, omissions, repeated cost |
| B — scoped trace + reusable evidence | Reuse revision-bound source spans, relationship claims, uncertainty and dependencies | Stale evidence, incorrect invalidation, unnecessary schema |
| C — broad extraction + graph | Pre-extract a repository-wide queryable workflow model | Expensive maintenance, stale or confidently incomplete graph |

Do not select B or C merely because a graph/store seems useful. Repeated-query benefit and graph-operation needs must be measured. Likewise, do not assume A discovers all implicit dependencies.

## Initial bounded observations (not a comparative benchmark)

Source inspected: `main` at `cd563c240ecaffa11d7eb749debdba8c669ede16`; multi-perspective review `SKILL.md`, `references/dispatch-flow.md`, `agents/review-synthesizer.md`, verdict schema and `docs/dh-workflow-graph.json`.

- Source defines T1–T4 parallel reviewer workers, then T5 synthesis that reads four Review Results sections and writes the Punch List. Source also defines schema/conservation checks and pass/fail terminals.
- Existing graph contains four named perspective worker nodes but no `review-synthesizer` node or `Punch List` node/handoff. It therefore cannot answer the inspected T5 questions.
- `SourceCheck` is a **proposed change in #4095**, not a behavior in this pinned `main` snapshot. Compare proposed source to a graph of that same proposed revision; do not count its absence on main as an existing-main defect.
- A human-assisted source inspection reconstructed the major review route. This does not prove an agent can autonomously find all paths or that evidence reuse saves cost.
- No live extraction, independent blind grading, comparative token/cost measurement, or persistent-cache reuse test has been run.

## Current assessment of the A6/#4101 architecture

The reviewed A6 plan's separation of agent-led semantic interpretation, deterministic evidence checks and single-writer publication remains a viable candidate. It is not yet proven end-to-end. Three agreeing workers can share a mistaken interpretation. Exact source quotations prove text presence, not an asserted relationship. Draft #4101's `rule/path/start/end/quote/kind` tuples cannot express typed cross-file relationships, multi-anchor evidence or omissions and should not be promoted as the final graph schema.

Deterministic Mermaid syntax parsing is not a viable replacement for understanding prose, implicit handoffs and nested execution. It may assist with explicit syntax and independent omission checks only if measured useful.

## Falsifiable evaluation plan

1. Freeze independently reviewed reference traces from at least three real workflows: multi-perspective review including T5 and proposed SourceCheck (at its PR revision), grooming with nested references, and a prose-heavy agent/profile handoff. Mark source revision and authoritative expected edges/terminals/unknowns.
2. Use the same pinned source and same questions for A, B and C. Keep gold labels out of candidate workers' inputs. Include normal and adversarial cases: same edge across different anchors, different edges at one span, omitted branch, conflicting instructions, implicit return, missing file, and changed upstream contract.
3. For B, actually reuse persisted evidence in a second independent query, then mutate an upstream dependency and test invalidation. For C, measure refresh/maintenance and freshness, not just initial extraction.
4. Score correct and missed relationships, false assertions, terminal/actor correctness, explicit uncertainty, changed/unchanged consumer accuracy, and source evidence. Track tokens, model calls, elapsed time and manual maintenance.
5. Decide using observed outcomes. Report which configuration wins for which task, where it fails, and whether a hybrid is justified. No invented numeric thresholds or savings.

## Work organization

- **#3223** remains the outcome owner.
- **#4101** remains draft research/experimental reducer. Keep existing assessments and process trace; do not merge the reducer as a production foundation before typed semantic contracts and the comparison.
- **#4095** owns review-method changes and its SourceCheck source change. The generated-graph drift must be explicitly assessed against graph consumers and governing gates; do not claim graph refresh happened.
- **#4097** depends on #4095 and should be rechecked after its parent is finalized.
- Create separate implementation issues/PRs only after the evaluation identifies verifiable producer, checker, and publication seams.

## Next agent handoff

Read this checkpoint plus `workflow-extraction-outcome-assessment.md` and `workflow-extraction-process-trace.md`. First build the independent gold traces and evaluation harness. Do **not** continue building the reducer just because it already exists. Produce an evaluation report with actual measurements and propose the smallest end-to-end architecture satisfying the outcome. Leave #4101 draft until the architecture is verified.
