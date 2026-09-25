# Contract-driven test architecture

Use this shared contract when designing tests or evaluating whether existing tests protect useful
behavior. Apply it at the smallest resolution that can change the testing decision. It is a
language-independent design policy, not a replacement for the target project's requirements,
framework conventions, safety controls, or established CI gates. The principles below synthesize
engineering guidance [1]-[9]; the design card and review dispositions operationalize them for DH.

## Entry points

Use [Test Designer](../skills/test-designer/SKILL.md) before writing tests, and
[Test Reviewer](../skills/test-reviewer/SKILL.md) to assess existing protection.
[Comprehensive Test Review](../skills/comprehensive-test-review/SKILL.md) remains an entry point
to the same review procedure. These skills
need no SAM plan for standalone use; language specialists retain framework-specific implementation.

```text
/dh:test-designer Plan the next TDD test for the approved retry contract; do not write code.
/dh:test-reviewer Review tests/ and its production boundaries; identify weak or redundant protection.
/dh:comprehensive-test-review tests/
```

During SAM planning the design accompanies acceptance criteria; the task worker loads the designer
before test authoring, and the S6 code reviewer loads the reviewer for test evidence. Test plans and
review findings stay in the caller's existing handoff instead of introducing new task-schema fields.

## Principles

### 1. Protect a stable behavioral contract

Name the required outcome, invariant, interface guarantee, or failure risk a test protects and its
source. Distinguish approved intent from observed behavior, derived interpretation, and proposals.
Existing output is useful characterization evidence, not automatically the desired answer. Test
behavior rather than mirroring the current implementation [1][9].

### 2. Discriminate against plausible defects

Name a realistic fault that must make the test fail. For changed regression protection, demonstrate
the original defect or a relevant safe negative control where practical. Check that execution reaches
the intended observation: an unrelated import, collection, or setup failure does not establish fault
detection. Coverage records execution; mutation testing challenges detection [3]. Neither a surviving
equivalent/unreachable mutant nor a failing test at the wrong stage establishes an oracle defect.
Mutation tooling is optional; fault sensitivity must remain an explicit evidence question.

### 3. Justify the oracle independently

The oracle is the reason an observation counts as correct. Use an authoritative requirement,
reviewed example, invariant, or independent reference. Do not calculate expected values with the
same production helper or copy its algorithm into the assertion. Shared mistakes can then agree [2].
Metamorphic relations need their own justification; a round trip alone can hide paired bugs.

### 4. Accept valid redesigns

Preserve contractual outcomes while allowing changes to private helpers, incidental call counts,
internal ordering, and noncontractual serialization [9]. Exact interactions are appropriate when
authorization, ordering, prohibited writes, or another interaction is itself the guarantee.
One coherent behavior may require several assertions. Even a crash/exit-code smoke check can be
valuable when that is its explicit contract; classify its limited scope instead of banning it.

### 5. Use the smallest faithful boundary

Choose the boundary from the failure mechanism, not a preferred test pyramid ratio. Pure logic may
need a function test; protocol, transaction, packaging, hardware, or startup guarantees need the
relevant real seam [4][5]. Inspect what fixtures, mocks, fakes, and bypassed adapters remove from
observation. Check a double's relevant assumptions against the real dependency where needed.
Architect controllable clocks, storage, network, and hardware seams without mocking away the very
mechanism the test must challenge.

### 6. Allocate rigor by consequence and uncertainty

Prioritize security, destructive operations, irreversible transitions, recovery, concurrency, and
high-variance behavior. A rare catastrophic failure can outweigh a frequent cosmetic defect.
Use focused examples for routine behavior and stronger boundary/fault evidence where warranted [5].
Honor established project coverage gates; do not invent universal percentages, test-per-symbol
quotas, one-assertion rules, or blanket bans on doubles. Report coverage and runtime separately
from correctness: neither compensates for a violated invariant.

### 7. Exercise transitions and forbidden effects

Derive success, rejection, boundary, retry, interruption, and recovery cases from the contract.
Stateful testing explores sequences of actions, not only isolated inputs [6]. For consequential
operations observe the resulting state and the absence of forbidden effects, not just an exception.
Include ownership races, duplicate requests, and partial completion when those are material risks.

### 8. Control the experiment

Control or record relevant time, randomness, versions, configuration, filesystem, shared state,
scheduling, and external dependencies. Preserve failing inputs, seeds, logs, and traces. Timing,
order dependence, shared state, and overly strict assertions can make tests flaky [7].
For nondeterministic behavior, predeclare permitted outcomes or justified statistical criteria and
report trials, failures, and uncertainty. Do not tighten tolerances or add retries to hide a defect.
A passing rerun does not explain a failure; unavailable, skipped, xfailed, or interrupted work is
not passing behavioral evidence. Account for cleanup of processes, threads, resources, and state.

### 9. Make failures interpretable

Keep scenario, action, expected behavior, and observation legible. Use behavior-oriented names and
helpers that expose rather than conceal the important input/state. Emit expected/actual differences
and enough context to reproduce the failure. Avoid a fixture framework that reproduces production
complexity or hides the oracle [2]. Follow the project's applicable typing and fixture conventions.

### 10. Maintain protection, not test count

Adjudicate failures as product, requirement, oracle, or harness/environment defects before editing
expectations. Compare a material rewrite against its original protection and unacceptable regressions.
Account for every meaningful guarantee when deleting or consolidating tests. Overlap across unit,
contract, and integration boundaries is not automatically redundancy [1][5]. Place fast high-signal
checks early; schedule expensive fidelity checks where their evidence is needed. Moving a check
later changes the detection window, not the need for the guarantee.

## Compact test card

Use a small note for a simple test or a table for a family. Reuse an existing design instead of
requiring a separate artifact for every assertion. Fill these fields only to the resolution needed
for an implementer and reviewer to agree on what the test demonstrates:

```text
Claim and authority: required behavior, source, unresolved interpretation
Consequence: important failure and impact if undetected
Scenario: inputs, prior state, environment, action
Oracle: independently justified expected result / permitted outcomes
Boundary: production path exercised; real dependencies and justified doubles
Observations: outputs, state transitions, required and forbidden side effects
Controls: plausible fault and intended failure; acceptable implementation variation
Execution: isolation, cleanup, CI lane, diagnostics, prerequisites
Evidence: proposed / observed; revision, command, selected cases, result, limitations
```

A proposed control is not an observed pass. Resolve consequential ambiguity before encoding a new
product policy as an assertion; continue independent design work with the gap visible.

## TDD use

Design the next meaningful test from the contract before writing it; no complete production
implementation or exhaustive upfront test plan is required. Follow red, green, refactor [8].
Record why red is expected. A missing API may be an initial compilation failure, but it does not
yet demonstrate the intended behavioral check. Once the necessary interface/scaffold exists,
distinguish the deliberate missing behavior from broken setup, then establish green and preserve
protected behavior during refactoring. Never manufacture red through unrelated harness failure.

## Evidence execution boundary

Discover commands from the target project's testing guidance, configuration, build, and CI.
Preserve strict configuration, warning policy, configured plugins, supported runtimes, and test
selection. Record collected/selected cases, skips/xfails, unavailable environments, and the
revision tested. Do not imply that a subset covers the whole suite.

Run probes only within an authorized isolated test environment. Inspect commands for external or
destructive effects before execution. Temporary fault injection requires safe isolation and cleanup;
never modify production resources, credentials, tracked source, or the user's live state merely to
obtain a counterexample. If execution is unavailable or unsafe, return the proposed probe and mark
its result unvalidated. Do not weaken project gates to make verification convenient.

## Generated artifacts and agent instructions

Keep the following evidence separate:

| Claim | Independent observation |
| --- | --- |
| Checked-in freshness | Compare the preserved artifact with its declared inputs/generation rule; report missing, extra, and changed identities. Do not regenerate first and thereby erase the discrepancy. |
| Generator correctness | Use deliberately constructed fixtures with independently specified values and invalid/boundary cases. Canonical bytes matter when deterministic serialization is contractual. |
| Consumer compatibility | Exercise the actual consumer and the interface it reads. |
| Agent behavior | Run representative tasks and inspect consequential actions, routing, side effects, and completion evidence. |

A valid file, matched phrase, unexecuted scenario, or mapped activation entry cannot establish
runtime behavior. Predeclare permitted outcomes and critical invariants for agent evaluations;
keep repeated-run uncertainty visible.

## Review dispositions

Assess a test's **purpose and importance** separately from its **effectiveness and evidence**.
A weak assertion can protect an important intended guarantee; an effective assertion can enforce
an obsolete requirement. Name both dimensions before proposing a disposition.

| Disposition | Evidence required |
| --- | --- |
| KEEP | A justified claim and useful protection at this boundary; disclose unmeasured sensitivity. |
| STRENGTHEN | Useful claim but a demonstrated weak oracle, missing observation, fault insensitivity, isolation problem, or diagnostic gap. |
| REPLACE | A valid obligation needs a different test boundary or design; identify the replacement's protection. |
| CONSOLIDATE | Compared cases protect the same claim, variants, and relevant failure mechanism; preserve their distinct obligations and diagnostics. |
| REMOVAL-CANDIDATE | Evidence that the enforced requirement is obsolete or the protection is genuinely subsumed; identify surviving carriers and residual risks. This is not deletion authorization. |
| UNRESOLVED | Intent, dependency fidelity, behavior, or evidence is insufficient to decide; state the cheapest discriminating next check. |

Missing requirement documentation is a discovery gap, not proof that a test has no purpose.
Do not remove characterization tests, cheap smoke checks, or overlap across boundaries merely
because they do not resemble unit tests. Report uncovered important claims separately from
findings about existing tests. No aggregate score or coverage percentage substitutes for these
judgments.

## Sources

Accessed 2026-09-25. These sources inform the principles; project-specific authority still governs
the expected behavior and any local thresholds.

1. [Software Engineering at Google: Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)
2. [Software Engineering at Google: Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)
3. [PIT: mutation testing](https://pitest.org/)
4. [Software Engineering at Google: Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)
5. [Software Engineering at Google: Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)
6. [Hypothesis: Stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
7. [pytest: Flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html)
8. [Martin Fowler: Test Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
9. [Google Testing Blog: Test Behavior, Not Implementation](https://testing.googleblog.com/2013/08/testing-on-toilet-test-behavior-not.html)
