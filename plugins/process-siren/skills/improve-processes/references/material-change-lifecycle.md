# Material-change lifecycle

Use for material behavior changes, reused evidence, or concurrently mutable targets. A routine local reversible edit needs only the checks material to its safety; no new database, script, or universal artifact format is required.

## Bind the comparison

Before generating a material candidate, retain:

- source identity: repository/ref/path or an equivalent content-bound snapshot;
- candidate identity, distinct from the source and updated after each relevant edit;
- the approved change contract and its revision, including invariants and unacceptable regressions;
- reviewing/validation method revision and material environment/tool identity;
- material dependency identities and the boundary/scenarios each observation covers.

Existing repository revisions, immutable artifacts, or content digests can carry these bindings. A path or timestamp alone is not content identity; a digest binds bytes but does not establish authority or correctness. Do not copy secrets into an evidence record.

Keep baseline and candidate observations tied to the same contract. If a consequential contract changes after candidate results are visible, retain the old comparison as historical, create a new contract revision, regenerate the affected candidate under it, and revalidate. Do not retroactively change the oracle to make an old candidate pass. If newly discovered dependencies change the boundary, expand the captured source/dependency set before accepting the affected comparison.

## Validate and apply conditionally

1. Validate the exact candidate and relevant boundary against the bound contract. Distinguish source/specification inspection, deterministic execution, CI evidence, and actual host behavior.
2. Before applying or reporting readiness, recheck the source and material dependencies against their captured identities, and confirm the candidate still matches the state validated. Reuse unaffected evidence only with an explicit applicability basis.
3. Apply through an available mechanism that prevents overwriting intervening changes: a conditional ref update, transaction, established exclusive-writer boundary, or equivalent host guarantee. A check followed by an unguarded write does not close a concurrent-write race.
4. If identity changed or the required guarantee is unavailable, preserve the candidate and evidence as a proposal/patch, leave the live target untouched, and report the affected gap as UNVALIDATED. Reconcile only with current source and revalidate affected claims; do not force an overwrite. A changed required goal remains an intent decision.
5. Verify the resulting state and affected interfaces after application. Record what actually changed and which evidence still applies. Never label a partially applied dependent change set coherent or ready.

For multi-file changes, establish one coherent dependent change set after cross-file synthesis. Use atomic publication where the host supports it. Otherwise define an authorized staged apply/recovery sequence and an isolation boundary that prevents consumers observing an invalid intermediate state. If neither is available, return the proposed set without applying it. Recovery may restore only this operation's known changes while preserving intervening user/worker edits; an unsafe rollback stays blocked rather than destroying another writer's work.

These safeguards block the affected mutation, not independent analysis or faithful representation. Report the requested work's completion separately from the target's INVALID, UNVALIDATED, or other assessment. Unavailable execution must not be replaced by a claimed successful test.

## Convergence

Use the core skill's visited-target and candidate-cycle rules. A new run identifier, refreshed timestamp, cosmetic change, or a repeated favorable opinion is not decision-changing evidence. On a repeated/no-progress state, retain the last known source/candidate identities, outstanding claims, attempted corrections, and the smallest missing observation or decision. Resource exhaustion and cycle detection are stop reasons, never successful validation.
