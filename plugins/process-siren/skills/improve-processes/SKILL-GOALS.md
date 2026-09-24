The purpose and explicit goals of the skill improve-processes:

1. Establish enough purpose, scope, evidence, constraints, and system context at the current useful resolution to judge a process without requiring unnecessary detail.
2. Build one explicit semantic ProcessModel that exposes contracts, behavior, ownership, state, boundaries, assumptions, failure modes, uncertainty, and inherited constraints without inventing intent.
3. Select process altitude and local instruction resolution proportionate to consequence and behavioral uncertainty: compress safe routine behavior, preserve critical contracts and safeguards, and locally expand consequential or variable behavior rather than increasing detail everywhere.
4. Identify falsifiable correctness claims and select the least-formal sufficient validation for each claim, including executable checks, structural fidelity checks, state-space/model checking, theorem proving, or human/environmental evidence where appropriate.
5. Improve demonstrated gaps when established intent determines the correction; escalate only decisions that would create or alter goals, policy, or intent.
6. Use failures and counterexamples as diagnostic evidence, distinguish process, requirement, model, validator, and implementation defects, and revalidate only affected claims and interfaces at the necessary resolution.
7. Optionally measure baseline agent behavior to determine which instructions are genuinely needed, using neutral representative scenarios, diverse/isolated samples, predeclared contracts, variance analysis, and compression validation without treating model consensus as correctness.
8. Keep recursive analysis bounded by descending only to materially useful narrower resolution, preserving parent contracts and stopping when additional detail cannot change a correctness decision.
9. Finish with explicit evidence, assumptions, residual risks, validation boundaries, instruction-resolution decisions, and a stable readiness status.
