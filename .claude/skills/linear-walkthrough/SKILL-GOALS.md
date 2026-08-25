The purpose and explicit goals of the skill `linear-walkthrough`:

1. `Produce a single navigable, end-to-end explanation of how an unfamiliar codebase works, from entry points through major execution paths, suitable for onboarding a new engineer to real understanding.`
2. `Achieve full, non-overlapping coverage of a repository by partitioning it into parallel discovery/tracing assignments bounded by a token budget, rather than one agent skimming everything shallowly.`
3. `Fact-check every generated explanation against actual source (file:line references) through an independent validation pass, correcting incorrect sequencing, invented behavior, and broken references before the walkthrough is finalized.`
4. `Distinguish verified facts from inference — every claim in the output is tagged Verified, [INFERENCE], or [UNCERTAIN] so a reader knows what to trust.`
5. `Surface both linear execution flow (entry point → downstream systems, with predecessor/successor navigation) and cross-cutting/process concerns (architecture, deployment, testing, CI/CD, security, observability) so no operationally important dimension of the codebase is silently omitted.`
6. `Track and report what was not covered or resolved (open-questions.md, uncovered areas, partial coverage) instead of presenting a confidently incomplete picture.`
