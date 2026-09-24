# Baseline Agent Behavior Evaluation

Optional refinement for measuring which process instructions agents already infer reliably. This method is environment-independent; adapt execution to available isolated-agent, shell, harness, SDK, or API capabilities.

## Purpose

Measure what an otherwise capable agent naturally does, not whether it can reproduce the process being evaluated. Use results to identify candidate instruction compression. Consensus is evidence of likely inference, never correctness or safety.

## Scenario design

Create several realistic situations exercising the same capability under different incidental details. Give each agent only information naturally available at that point in real execution:

- situation, genuine resources/evidence/constraints, and observable desired outcome;
- a neutral request for the steps/actions it would take;
- varied names, ordering, context, and non-essential details so wording does not manufacture consensus;
- ordinary cases plus relevant boundary/failure cases;
- sufficiently stable outcomes that approaches remain comparable;
- independent, preferably single-response queries so samples do not anchor one another.

Do not expose target process steps, preferred ordering, expected safeguards, implementation vocabulary, or the tested hypothesis unless real execution would provide them. Avoid nudges such as "make sure to", "safely", "correctly", "without losing data", "following best practices", named techniques, or enumerated candidate actions.

Prefer:

```text
You are in <concrete situation>. You have <resources/evidence actually available>.
Your desired outcome is <observable outcome>.
What steps would you take?
```

Not:

```text
How would you safely perform <task> while ensuring you verify X, preserve Y,
and recover if Z fails?
```

The latter supplies much of the behavior whose spontaneous presence is being measured.

## Sampling and interpretation

1. Where practical, collect at least 10 isolated responses across available supported models/harnesses. Prefer model/harness diversity when measuring general inference.
2. Preserve raw responses before interpretation. Normalize into comparable semantic steps without erasing meaningful differences.
3. Identify consensus, variable decisions, omissions, ordering differences, unsafe variants, and scenario-wording sensitivity.
4. Compare observations with required contracts/invariants. Common behavior can still be wrong for this system.
5. Treat omission cautiously: concise prose may leave execution behavior implicit. When material, redesign the scenario so the decision becomes observable rather than asking a leading follow-up.
6. Compress high-consensus behavior only when invariant-compatible and inference-failure consequence is acceptable. Retain short confirmation where sequencing/contracts benefit from it.
7. Specify preferred behavior for high variance; consequential high-variance nodes should be locally expanded and validated.
8. Record scenarios/prompts, model/harness diversity, sample count, normalization decisions, variance/unsafe observations, and resulting instruction decision. Do not claim universality.

## Compression validation

Before examining results, record the contract-relevant invariants, unacceptable outcomes, and material decision points that compression must preserve.

For material compression where practical:

1. Compare full and compressed instructions on the same representative scenarios under comparable environments.
2. Include held-out scenarios not used to choose the compression.
3. Repeat selected scenario/model combinations to distinguish within-model stochasticity, consistent cross-model disagreement, and framing sensitivity.
4. Blind old/new identity during qualitative comparison where practical; judge against the predeclared contract.
5. Inspect execution traces when available: actions, navigation, tool use, omissions, recovery, and backtracking are stronger evidence than merely mentioning safeguards.
6. Observe relevant benefits and regressions: context/instruction reduction, task success, unsafe/contract-violating behavior, execution time, and unnecessary work/tool expansion. No fixed metric is required.
7. Restore/specify behavior when compression causes contract-relevant regression.

Cross-model evidence must reflect models the process is expected to support. Behavior inferred by stronger models but missed by a supported weaker model is not safely redundant for that deployment context.

## Bias checks

Before accepting evidence, ask:

- Does prompt vocabulary reveal the preferred process?
- Does framing imply a safeguard, ordering, tool, or failure mode?
- Are scenarios diverse enough to distinguish consensus from framing artifacts?
- Did normalization erase meaningful disagreement?
- Are common training patterns being mistaken for requirements of this system?
- Would omission remain acceptable if a future capable model chose a different contract-compatible path?

If not, redesign scenarios rather than treating the sample as evidence for compression.
