---
name: verify-factual-claim
description: Verify one falsifiable factual claim against evidence appropriate to the claim. Use when a concrete assertion about software, documentation, configuration, releases, or repository behavior must be classified as VERIFIED, REFUTED, or INCONCLUSIVE.
---
# Verify a Factual Claim

Treat recall as a hypothesis, never evidence.

1. Rewrite the input as the narrowest falsifiable claim without changing its meaning.
2. Identify evidence that could confirm and evidence that could refute it.
3. Use the strongest practical source for the claim: authoritative specification/docs for public contracts; version-pinned source/tests for implementation behavior; runtime observation for environment behavior; maintainer records for intent.
4. Record version, revision, platform, configuration, or time boundaries that can change the result.
5. Challenge consequential conclusions with a plausible counter-hypothesis and an independent evidence path when it can discriminate between explanations.
6. Return VERIFIED only when evidence establishes the claim in scope; REFUTED only when evidence contradicts it; otherwise INCONCLUSIVE.

Return the exact claim, verdict, concise evidence citations, applicable conditions, explanation, and unresolved evidence. Preserve contradictory sources rather than silently choosing one. Do not require a fixed number of sources or quotes when one authoritative observation resolves the claim.
