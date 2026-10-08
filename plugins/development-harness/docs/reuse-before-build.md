# Reuse-before-build decision

Use this decision gate before choosing to author a new script, tool, utility, library, or
implementation of a capability that might already be available. Apply it in task planning and
recheck at execution when the implementation choice changes. Reuse an existing, still-applicable
decision rather than repeating discovery.

## Decide at the smallest useful scale

1. **Specify the capability.** State required behavior, inputs/outputs, environment, constraints,
   and how a candidate will be checked. Finish when the requirement is testable without assuming
   a custom implementation.
2. **Search nearest first.** Inspect platform/standard-library features, repository and installed
   dependencies, existing CLI/MCP/skills, then maintained ecosystem packages and upstream tools.
   Search external candidates when the capability is nontrivial or not locally solved. Finish when
   plausible existing candidates are identified or a bounded search with sources is documented.
3. **Understand viable candidates.** Read authoritative documentation and relevant implementation
   or examples. Compare capability, interoperability, maintenance, license, supply-chain risk,
   runtime/dependency cost, and replacement difficulty. Verify the package and version actually
   exist. Finish when suitability and important unknowns are explicit.
4. **Test the critical fit.** Prefer a minimal, safe, isolated proof against the hardest requirement.
   Documentation-only assessment is acceptable for a trivial choice when a proof would not change
   the decision; mark unverified claims. Finish when the decision is supported by evidence or
   blocked by a specific unknown.
5. **Choose the least new mechanism.** Prefer reuse/configuration; then a narrow adapter or
   upstream extension; then custom implementation only with demonstrated deficiencies or
   disproportionate integration cost. Finish with one of: ADOPT, ADAPT, BUILD JUSTIFIED,
   or UNRESOLVED. UNRESOLVED defers implementation choice.

## Proportional evidence

A trivial local helper can be resolved by inspecting existing code and standard-library APIs.
A new parser, generator, test engine, or framework needs ecosystem comparison and a proof of
the decisive behavior. Do not impose a new ADR or standalone artifact on every small change.
For significant choices, record alternatives, evidence, trade-offs, and consequences in an
existing design/decision record; for small tasks, use the task's existing context and handoff.

## Review check

When reviewing a new custom mechanism, ask which existing options were checked and why they
failed the requirement. Confirm the chosen option actually works at its intended boundary.
If a fit-for-purpose tool was overlooked, recommend reuse before expanding bespoke code.
Absence of a separate research document is not a defect when the decision is otherwise traceable.

## References

- [Plugin Creator lifecycle](../../plugin-creator/skills/plugin-lifecycle/SKILL.md):
  existing-solution research during new-plugin creation
- [AWS ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html):
  retain consequential technology-selection decisions
- [ECC search-first](https://github.com/affaan-m/ECC/blob/main/skills/search-first/SKILL.md):
  nearest-first discovery and proportional research
- [Agentic Developer Cookbook](https://agenticdevelopercookbook.com/guidelines/planning/code-quality/reuse-before-build):
  verify candidate availability and supply-chain suitability
