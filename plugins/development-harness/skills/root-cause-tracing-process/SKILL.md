---
name: root-cause-tracing-process
description: Trace bugs, CI failures, and unexpected behavior from reproduced evidence to a causal mechanism and governing contract. Distinguish product, architecture, test-oracle, and harness defects; investigate intermittent failures with controlled experiments and report unresolved evidence explicitly.
argument-hint: <failure to trace>
---

<tracing_input>$ARGUMENTS</tracing_input>

# Root-Cause Tracing Process

## Inputs and completion contract

Record the question, affected scope, requested operation, and success criteria from the input
and conversation. An investigation-only request does not authorize product or test edits.

Success requires a reproduced failure, a cited mechanism, and an independently established
contract before declaring a defect and recommending its correction. When execution is unavailable
or prohibited, return a partial evidence assessment; do not invent reproduction or a root cause.

Use this causal statement only as far as the evidence supports it:

> Under conditions C, X produces Y through mechanism M, violating contract K.

Keep explanation of current behavior separate from the decision that the behavior is wrong.

## Evidence-chain protocol

Give each material claim an evidence entry:

```text
CLAIM: [one observation, interpretation, or causal claim]
EVIDENCE: [command + output/exit status, file:lines, or directly observed state]
KIND: [runtime observation / source observation / requirement authority / hypothesis]
VERIFIED: [yes/no, for this claim rather than its entire source]
DEPENDS ON: [prior claim IDs]
MISSING: [observation or decision needed, when unverified]
```

Command output, read source, and direct observations establish what was observed. A source read
establishes the code present at that revision, not that the path executed. Documents and explicit
owner decisions can establish requirement authority; they do not demonstrate runtime compliance.
Check which document is authoritative and current rather than treating any prose as a requirement.

Label derived interpretations and hypotheses; retain their supporting observations. Training recall,
analogy, absent documentation, and an untested explanation are not verified runtime evidence.
An unverified dependency leaves dependent conclusions unverified. Do not promote a coherent
interpretation into established intent.

## 0. Discover relevant capabilities

Identify the available shell, diagnostic tools, connected MCP tools, specialist agents, and
sandbox options needed for this incident. Use independent checks in parallel when supported.
Use native discovery rather than assuming Unix commands, an installed plugin, or a sub-agent API.
Record unavailable capabilities and their effect on verification. Do not install unrelated tools
or perform a broad inventory when it cannot change the next decision.

## 1. Preserve the signal and establish the contract

Before updating dependencies, regenerating files, or editing assertions, preserve the failing
revision, actual checkout SHA, workflow/job, command, complete output, exit status, and relevant
runtime versions, configuration, test selection, order, seeds, and parallelism. For a PR job,
distinguish its tested merge commit from the branch head. Keep logs as reported observations,
not as your own reproduction.

Separate assertion failures, collection/setup failures, lint failures, and downstream aggregate
failures. Group symptoms by demonstrated mechanism, not filenames or a shared red workflow.

Identify the smallest useful contract: purpose, consumer/entry point, observable guarantee,
invariants, authoritative source, and falsifier. Read applicable purpose, architecture, interface,
and requirement records. Keep goals stable; refine local detail only where it changes a decision.
The current architecture can itself conflict with higher-level intent. Neither an existing test
nor the current implementation wins a disagreement automatically.

For unknowns, record the cheapest discriminating observation. Resolve factual uncertainty with
available evidence; ask the owner only when choosing among legitimate behaviors would create or
alter intent, or when safe execution needs information only the owner can supply.

## 2. Establish reproduction safety

Classify constraints before executing the failing operation:

- **Bound:** inputs and side effects can be inspected. Read enough to assess risk; use an isolated
  directory, disposable data, dry run, or other appropriate containment before risky reproduction.
- **Unbound:** credentials, external state, side effects, or permissions cannot be evaluated.
  Complete safe read-only work, then batch the missing safety/input questions. Do not cross that
  boundary until the necessary information and authorization exist.

Respect the requested oversight and read-only scope. Reassess safety if a new external or
destructive boundary appears. A requirement to reproduce never authorizes production writes,
messages, deployments, or other irreversible operations.

## 3. Reproduce, then reduce

Run the same operation end-to-end under the preserved conditions when safe and permitted.
Capture all arguments and relevant environment, stdout/stderr, exit status, timing, and side
effects, including files, network activity, and child processes. Observe the mechanism as well as
the final failure. Inspect source or add bounded instrumentation where the mechanism is hidden.

Then reduce to the smallest reproducer that retains the mechanism. Preserve both the full-system
observation and the reduced case. Compare isolated/full-suite, serial/parallel, or clean/reused
state only when those contrasts can discriminate a hypothesis. Use a known-good revision or
bisection when a stable reproducer makes the comparison meaningful.

If results differ from the report, record the environmental/operational differences rather than
assuming the report is wrong. Use available CI commands and logs to recover missing steps before
asking the user. If reproduction remains unavailable, continue with explicit evidence limits.
A successful rerun is an observation, not a fix.

## 4. Challenge competing explanations

Consider implementation, producer/consumer contract, test expectation, fixture/mock, observation,
and CI/environment explanations. State what evidence would distinguish them before editing.
Choose one discriminating intervention at a time; record confounds and hold relevant conditions
fixed. Source inspection and controlled observations must support the mechanism, not just a
correlation with the most recent change.

### Intermittent or non-reproducing failures

Do not require a probabilistic cause to fail on every run. Choose the hypothesis form before
examining confirmatory results:

- **Deterministic:** under stated preconditions, setting X produces Z; specify the counterexample
  that would contradict this guarantee.
- **Probabilistic:** setting X changes the probability of Z under stated conditions. State a null
  of no effect and an alternative with the direction/effect relevant to the correction decision.

Predeclare comparable arms, measurement, reset/isolation procedure, repeat-count rationale, and
stopping rule. Use randomization or interleaving where time/order could confound results; record
seeds when applicable. Size the experiment for the observed frequency and decision-relevant
uncertainty, not an arbitrary universal retry count. Keep exploratory and confirmatory runs distinct.

Capture every run in both arms, including successes. Report failures/trials, effect estimates and
uncertainty where estimable, uncontrolled conditions, and the resulting evidence boundary.
Distinguish supported, contradicted, and inconclusive hypotheses. Failure to reject a null is not
proof of no effect; zero observed failures is not proof of impossibility. A nonzero failure rate
in both arms does not by itself falsify an effect hypothesis.

Return to source/mechanism tracing when the experiment isolates a relevant condition. Otherwise
record the remaining hypotheses and next discriminating experiment; do not loop until a desired
result or label an association a verified root cause.

## 5. Trace the product and the test

Read the complete relevant code paths, including setup and cleanup. Cite paths and line ranges
and quote the lines needed to support each claim. Reuse the capability matrix for runtime
instrumentation or specialist analysis when source alone cannot resolve the mechanism.

Trace both paths where a test is involved:

```text
Product: intent -> entry point -> routing -> inputs/state -> execution -> output -> consumer
Test:    claimed contract -> fixture/setup -> invoked boundary -> observation -> assertion -> verdict
```

Include recovery and terminal behavior where relevant. At each material boundary record producer,
consumer, state crossing it, caller assumptions, callee guarantees, and partial-failure/recovery
ownership. Compare expected and observed behavior to locate the earliest demonstrated divergence,
not merely the assertion or exception that finally reports it.

Do not derive the test's expected answer from the same implementation logic being tested.
Distinguish a valid requirement with weak observation from an incorrect requirement. Locally
correct components can still compose incorrectly; a product defect and a test defect can coexist.

## 6. Build the causal chain

Connect symptom -> observed mechanism -> triggering condition -> supported structural contributors.
For each link retain evidence and dependencies. Distinguish:

- **Trigger:** what exposed the incident now.
- **Mechanism:** how the incorrect behavior occurred.
- **Structural contributor:** ownership, lifecycle, dependency, or boundary design that permits it.

Do not force several contributing conditions into one unsupported root cause. Trace only as deep
as needed to choose a correction and preserve relevant parent invariants. Stop expanding when finer
resolution cannot change that decision, evidence is unavailable, or an intent decision is needed.

## 7. Adjudicate the correction and hand off

Classify independently of which file is easiest to edit:

| Evidence-backed finding | Correction |
| --- | --- |
| Implementation violates a valid contract | Correct the product and add fault-sensitive regression protection. |
| Local contracts conflict at a handoff | Correct ownership/interface/composition and test the boundary. |
| Test expectation is unsupported or superseded | Correct the test and record the authoritative reason. |
| Fixture, mock, observation, or CI conditions misrepresent the contract | Correct the harness without weakening the product guarantee. |
| Intent remains contradictory or undefined | State alternatives and obtain the consequential decision. |

Several rows may apply. For an architectural proposal, name the causal condition it removes and
why a smaller local correction is insufficient. Do not require a redesign merely because a test
failed, or dismiss a recurring structural defect with a symptom patch.

When `process-siren:improve-processes` is available, pass the same contract, evidence chain,
counterexample, and uncertainty record into its CHALLENGE/IMPROVE/VALIDATE loop. Do not restart
investigation or create a parallel model. When it is unavailable, use this standalone handoff:

1. Declare the targeted claim, expected improvement, preserved invariants, unacceptable regressions,
   and smallest useful baseline before examining the candidate result.
2. Apply only authorized corrections determined by established intent. Record each affected original
   behavior as preserved, relocated, automated, proven redundant, uncertain, or lost. Required lost
   behavior blocks acceptance; behavior-affecting uncertainty remains unresolved.
3. Validate the delta using comparable before/after cases and affected interfaces. For substantial
   redesign, add independent/held-out cases where practical and record any unavailable evaluation.
4. Feed counterexamples back to the nearest affected claim. Revalidate evidence invalidated by later
   edits. Report actual execution and remaining uncertainty, not only green CI.

For test changes, use [Comprehensive Test Review](../comprehensive-test-review/SKILL.md) to assess
the oracle, relevant fault detection, refactor tolerance, and boundary fidelity. Keep inventory
freshness, generator correctness, and actual skill/consumer execution as separate claims. Never
regenerate a stale artifact before its freshness check and call that evidence the original state
was current.

## 8. Present findings

```text
QUESTION:
SCOPE / REQUESTED MODE:
SUCCESS CRITERIA MET: yes | partial | no
CONTRACT: purpose, guarantee, authority, invariants, falsifier
REPRODUCTION: exact revision/command/conditions, result, or why unavailable
EVIDENCE CHAIN: claim IDs with evidence, kind, verification, and dependencies
FIRST DIVERGENCE: product boundary and/or test-observation boundary
ROOT CAUSE: supported statement, or not established
TRIGGER / MECHANISM / STRUCTURAL CONTRIBUTORS:
CORRECTION: product | architecture/interface | test oracle | harness/CI | intent decision
CHANGE CONTRACT / HANDOFF: proposal, or authorized work actually performed
VALIDATION: claim -> test/experiment -> observed result -> evidence boundary
UNVERIFIED ITEMS: missing evidence, residual risk, next observation/decision
```

Do not call reported logs your reproduction, source review a behavioral run, or an unexecuted
scenario a passing test. Do not suppress warnings, skip inconvenient assertions, or loosen gates
to manufacture success. State unsupported hypotheses as hypotheses, never as diagnoses.
