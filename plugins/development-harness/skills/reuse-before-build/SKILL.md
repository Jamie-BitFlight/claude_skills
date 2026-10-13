---
name: reuse-before-build
description: Decide whether to adopt, adapt, or justify building a new script, tool, utility, library, module, dependency, or bespoke capability. Use in task planning, worker execution (including tooling discovered after planning), or code review when an implementation choice may duplicate an existing solution.
user-invocable: true
---

# Reuse Before Build

Apply this decision gate to a proposed or newly implemented capability, not every
changed function. Skip unchanged mechanisms and incidental glue with no independent
capability. Select the caller's mode:

- **Planning:** apply the procedure before choosing an implementation. Carry the
  decision in the caller's existing task sections, not a new task field or stage.
- **Runner:** apply during `dh:start-task` execution, including late discovery.
  When the dispatch owns an attempt, read [Runner handoff](./references/runner-handoff.md)
  before research or closure; it binds lease ordering and durable evidence to that task and
  attempt. Without an attempt, make the decision but leave attempt-owned persistence and
  closure to the caller that owns them.
- **Review:** remain read-only. Recover the implementation's requirements and
  decision from its diff, consumers and task evidence, then assess the choice.

## Decision procedure

1. **Define fit.** Name the required behavior and the decisive requirement most
   capable of disqualifying a candidate. Do not assume a custom implementation.
2. **Recover or discover nearest first.** Inspect prior task context and decisions.
   Reuse a prior decision only while its requirements, environment, availability
   and implementation assumptions still hold. Recheck the affected evidence when
   any of these changes, including a different approach discovered by the worker.
   If no applicable decision establishes fit, inspect platform/standard-library
   facilities, repository code and installed dependencies, available CLI/MCP/skills,
   then maintained ecosystem candidates as justified by the remaining uncertainty.
3. **Verify decisive fit.** Read authoritative candidate documentation. Run a small
   safe proof of the hardest requirement when its result could change the choice.
   Mark claims unverified when that check cannot run. Compare integration,
   compatibility, supported versions/interfaces, licensing, maintenance,
   supply-chain/security risk and replacement/lifecycle cost only where they could
   change the decision. A candidate's existence is not proof of fit.
4. **Decide and stop.** Prefer **ADOPT** (reuse/configure), then **ADAPT** (minimal
   integration or upstream extension), then **BUILD JUSTIFIED** (demonstrated gaps
   or integration costs materially outweighing reuse). Use **UNRESOLVED** when the
   decisive evidence is missing, naming the cheapest check that would settle it.
   Stop searching when further evidence would not change the choice.

## Proportionality and blocked choices

For a known fit, reuse the still-applicable decision without repeating research.
For a trivial helper, repository and standard-library inspection may settle fit.
For routine uncertainty, inspect plausible local candidates and test the decisive
requirement. Escalate novel, high-consequence or unresolved choices to external
comparison and a bounded proof where feasible; a new parser, generator, test engine
or framework normally warrants that comparison. Do not require a research tier,
matrix or report for every helper.

Defer only the affected implementation choice while it is UNRESOLVED. Continue
independent design, verification, review or other tasks. Missing discovery does not
authorize a custom build. Ask for help only when the missing decision blocks the
next consequential step. In plan-level decomposition, make discovery a predecessor
only of the dependent implementation task; do not block unrelated tasks. A caller
generating one task cannot create that predecessor: preserve the UNRESOLVED decision
and its cheapest check in that task, and do not invent a dependency or task ID.

## Decision evidence

Preserve the capability and decisive requirement, chosen option and disposition,
candidate/source evidence actually checked, demonstrated gaps, unverified claims,
next decisive check if unresolved, and conditions that invalidate the decision.
Use the caller's existing task context and handoff. For an architecture-significant
choice, also follow the repository's decision-record convention; a standalone
research document is not required for small choices. The runner handoff defines
where execution evidence is persisted for later attempts.

## Review disposition

Report affected file/lines, candidate evidence, whether the present choice is
justified, and the minimum corrective action in the caller's existing review
format. Investigate missing design-time discovery against actual requirements.
A plausible alternative or missing standalone research document is not itself a
defect. Classify a finding as blocking only when a consequential requirement or
review acceptance criterion is violated; otherwise offer a nonblocking improvement.
Continue unrelated review work when the choice remains unresolved.
