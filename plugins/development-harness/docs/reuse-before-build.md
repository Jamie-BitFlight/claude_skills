# Reuse-before-build decision

Before committing to a new script, tool, utility, library, module, dependency, or bespoke
capability, determine whether a fit-for-purpose solution already exists. This is a
decision gate, not a required research report. Reuse an applicable prior decision.

## Fast path

1. **Define fit.** Name the required behavior and the requirement most likely to
   disqualify a candidate. Do not assume a custom implementation.
2. **Discover nearest first.** Check applicable prior decisions, platform/standard
   library, repository code and installed dependencies, available CLI/MCP/skills,
   then maintained ecosystem tools when the earlier sources do not establish fit.
3. **Verify the decisive fit.** Read authoritative documentation and, when it could
   change the decision, run a small safe proof of the hardest requirement.
4. **Decide and stop.** Prefer ADOPT (reuse/configure), then ADAPT (narrow adapter
   or upstream extension), then BUILD JUSTIFIED (evidence existing options fail or
   integration costs materially outweigh reuse). UNRESOLVED defers only the
   affected implementation choice. Stop searching once further evidence is
   unlikely to change the choice.

A candidate's existence is not proof of fit. Record decisive evidence and
unverified claims separately. Recheck a prior decision only when requirements,
environment, availability, or the selected implementation invalidate it.

## Escalate only when needed

- **Known fit:** apply the still-valid decision without repeating research.
- **Routine uncertainty:** inspect local facilities and a small number of plausible
  candidates, testing the decisive requirement first.
- **Novel, high-consequence, or unresolved:** compare credible external alternatives,
  supported versions, interfaces, compatibility, license, maintenance, supply-chain
  risk, and lifecycle cost; run a bounded proof where feasible.

Do not assign a research tier or produce a matrix for every helper. A trivial local
helper may need only repository and standard-library inspection. A new parser,
generator, test engine, or framework normally merits external comparison.

When a decisive check cannot run, label the claim unverified. Continue independent
design, tests, or other tasks; do not authorize a custom build simply because
discovery is incomplete. Ask for help only when the missing decision blocks the
next consequential implementation step.

## Record and review

Use existing task context, verification, and handoff fields for small decisions.
For architecture-significant decisions, use the repository's ADR convention and
record requirements, chosen option, decisive evidence, rejected alternatives,
consequences, and invalidation conditions. Preserve enough context for a future
agent to reuse the decision without replaying the search.

When reviewing bespoke mechanisms, challenge the evidence of fit and rejected
alternatives rather than requiring boilerplate. A missing standalone research
document is not itself a defect.

## Related guidance

- [Decision architecture and alternatives](adrs/20261008-adaptive-reuse-before-build.md)
- [Plugin Creator lifecycle](../../plugin-creator/skills/plugin-lifecycle/SKILL.md)
- [AWS ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
- [ECC search-first](https://github.com/affaan-m/ECC/blob/main/skills/search-first/SKILL.md)
