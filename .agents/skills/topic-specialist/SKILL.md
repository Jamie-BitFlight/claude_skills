---
name: topic-specialist
description: Research a specific technology, library, system, protocol, or tool to answer a concrete technical question with source-traceable evidence. Use when current implementation details, version behavior, configuration, compatibility, or authoritative technical facts must be verified rather than recalled. Also use when explicitly asked to incorporate verified findings into an existing skill.
---

# Topic Specialist

Answer the user's concrete technical question from evidence strong enough for the claim being made. Treat training-data recall as a hypothesis generator, not evidence.

## Resolve the research contract

Before researching, identify:

- **topic** — the technology, library, system, protocol, or tool;
- **question** — the decision or fact to resolve;
- **conditions** — version, platform, configuration, environment, or other constraints that could change the answer;
- **deliverable** — answer only, or an explicitly requested update to an existing skill.

Infer these from the request when unambiguous. Ask only for missing information that could materially change the research result.

If the user identifies relevant skills or repository guidance, read them as domain context. Treat their factual claims as leads unless their authority independently establishes the claim.

## Research

Choose the cheapest evidence capable of resolving the question. Do not mechanically inspect a repository README, entry point, and issue tracker when those sources cannot affect the answer.

Prefer evidence according to the claim:

| Claim | Strong evidence |
| --- | --- |
| Public API/configuration contract | Current official documentation/specification |
| Actual implementation behavior | Version-pinned source code and tests |
| Version/release behavior | Release notes/changelog plus version-pinned implementation when needed |
| Known defect or maintainer intent | Maintainer issue/discussion linked to the affected version |
| Runtime/environment behavior | Reproducible execution in the relevant environment |
| Historical rationale | Primary design/issue/commit evidence when available |

Use secondary sources for discovery, comparison, or when primary evidence is unavailable. Label the limitation rather than presenting weaker evidence as primary.

Keep the researched revision/version and environment explicit when they bound the finding.

## Build claim evidence

For each material conclusion:

1. Identify what observation would support or falsify it.
2. Read or execute the strongest practical source.
3. Record the source location and relevant version/date.
4. Distinguish what the source directly establishes from what is derived from it.
5. Preserve contradictory evidence instead of silently choosing the preferred source.

Quote only the minimum text needed when exact wording matters. Prefer concise paraphrase plus a precise citation for ordinary factual support.

## Challenge consequential findings

Scale verification to consequence and uncertainty.

For a finding that could materially change implementation, compatibility, security, data integrity, or architecture:

1. Form at least one plausible counter-hypothesis: version difference, feature flag, platform branch, configuration override, wrapper behavior, or stale documentation.
2. Test the counter-hypothesis with an independent evidence path where practical.
3. Narrow or revise the conclusion when the counterexample survives.

Do not add a second source merely to satisfy a count. Independent evidence is useful only when it can discriminate between competing explanations.

## Produce the answer

State:

- the verified answer/options;
- conditions under which each applies;
- evidence supporting material claims;
- contradictions or version/environment boundaries;
- unresolved gaps that could change the answer.

Make a recommendation only when the user's conditions and evidence distinguish among the options. Keep descriptive facts separate from judgment.

## Update an existing skill only when requested

When the user explicitly asks to persist the findings into an existing skill:

1. Read the complete target skill and its applicable governance.
2. Define the behavior the update must add or correct and the behavior that must remain unchanged.
3. Update the narrowest authoritative location; do not append a second copy of an existing meaning.
4. Prefer durable rules and runtime discovery over cached version facts that will become stale.
5. Cite external facts where the target's citation rules require it.
6. Run the target repository's required validation.

Creating a new skill is a separate skill-authoring task. Route it through the repository's skill-creation process rather than embedding scaffolding procedure here.

## Boundaries

- Do not claim verification from training-data recall.
- Do not require primary-source code inspection when an authoritative specification already resolves the claim.
- Do not treat README prose as stronger than contradictory version-pinned implementation evidence for implementation behavior.
- Do not infer author intent from implementation alone.
- Do not mutate files unless the user requested a persistent update.
- Do not manufacture certainty when relevant evidence is inaccessible or contradictory.
