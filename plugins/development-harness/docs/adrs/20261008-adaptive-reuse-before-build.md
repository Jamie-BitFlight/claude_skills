# ADR: Adaptive reuse-before-build decision gate

## Status

Proposed — PR #4099.

## Context

Plugin Creator already researches existing solutions for new plugins. Development
Harness planning and execution can nevertheless introduce custom scripts, utilities,
modules, or frameworks without an equivalent decision. Requiring full research for
every helper would waste agent tokens and block unrelated work. A one-line reminder
alone is easy to miss and does not establish whether a discovered option actually
satisfies the requirement.

The design must favor reuse, preserve verifiable decisions, keep normal-path
context small, and avoid new task-schema fields or mandatory orchestration machinery.

## Decision

Use an adaptive gate: define decisive fit, search nearest first, verify the
disqualifying requirement, then choose ADOPT, ADAPT, BUILD JUSTIFIED, or UNRESOLVED.
Stop when further research is unlikely to change the decision. An unresolved choice
blocks only that implementation, not independent work.

Keep the common trigger in CLEAR task design, task generation, and Task Worker.
Put the detailed procedure in one shared reference. Reuse existing decision records
when their requirements, environment, and selected implementation still match.
Use existing task fields for ordinary choices and ADRs only for significant ones.
Review bespoke mechanisms for evidence of rejected alternatives.

## Alternatives and when to choose them

| Alternative | Why not default | When appropriate |
| --- | --- | --- |
| Inline one-line reminder only | Minimal tokens but no decisive-fit or stopping contract | Trivial, low-risk changes already covered by local conventions |
| Always load a full research skill | Repeated token/tool cost and ceremony | Major greenfield architecture or broad market survey |
| Mandatory research document or ADR per script | Artifact churn exceeds value for small helpers | Auditable, high-impact or difficult-to-reverse technology decisions |
| Fixed search/token/time budget | Predictable cost but can miss the decisive option | Bounded exploratory surveys where uncertainty is acceptable |
| Numeric confidence threshold | Apparent precision without calibrated evidence | A separately evaluated probabilistic decision system |
| Precomputed dependency/tool inventory | Fast discovery but can become stale | Repositories with generated, versioned inventory and invalidation |
| Dedicated MCP discovery agent | Extra invocation and coordination overhead | Large multi-repository ecosystems with measured discovery benefit |
| Automated review-only check | Catches mistakes after code has been written | Defense in depth, not primary planning gate |
| Hard-block all unresolved research | Stops independent work unnecessarily | Security/compliance or irreversible actions where uncertainty itself is disqualifying |
| Build a new discovery/search utility | Duplicates existing repository, package and MCP discovery tools | Only after those tools demonstrably cannot meet a verified requirement |

## Consequences

- Common-path instructions stay small; deeper research is conditional.
- Agents can adopt proven tools without generating unnecessary documentation.
- Decisions remain reusable, with explicit invalidation conditions.
- Custom builds require demonstrated gaps rather than absence of awareness.
- Incorrect risk classification or skipped discovery remains possible; review
  and fresh-agent behavioral evaluation are required to assess effectiveness.
- Tool availability and ecosystem claims can become stale, so decisions are
  revisited when relevant assumptions change.

## Verification

Run contrasting fresh-agent cases: known local tool, external tool meeting a
hard requirement, unsuitable package, trivial helper, changed prior decision,
and an unresolved tool choice with independent work available. Record decision
quality, tool calls, tokens, elapsed time, and unnecessary blocking. Compare
against the previous instructions; do not infer behavior from Markdown checks.

## References

- [Nygard ADR format](https://github.com/architecture-decision-record/architecture-decision-record/blob/main/architecture-decision-record.github.io/src/content/templates/decision-record-template-by-michael-nygard.md)
- [MADR trade-off guidance](https://adr.github.io/adr-templates/)
- [ECC search-first](https://github.com/affaan-m/ECC/blob/main/skills/search-first/SKILL.md)
- [AWS ADR guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
