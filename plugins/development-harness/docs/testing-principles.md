# Contract-driven test architecture

Use this shared contract when deciding whether a test should exist, designing justified tests, or
evaluating whether existing tests protect useful behavior. Apply it at the smallest resolution that
can change the testing decision. Optimize for maintenance-adjusted protection: the smallest
maintainable suite that gives strong confidence in consequential system behavior. It is a
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

During SAM planning the design accompanies acceptance criteria. On the primary feature route,
Swarm Task Planner's preloaded CLEAR + CoVe method loads the designer before composing test-based
acceptance and verification cases. Task Worker loads it before test authoring, and the S6 code
reviewer loads the reviewer for test evidence. Test plans and
review findings stay in the caller's existing handoff instead of introducing new task-schema fields.

## Validation and retention are separate decisions

Every claimed fix requires direct validation before closure. Validate the behavior the change was
intended to correct, not merely nearby code or the existence of the edit. Prefer the same
discriminating observation before and after the change when practical: establish the incorrect
baseline, apply the fix, and observe the corrected result. When the original failure cannot be
reproduced, state that limitation and report only what the available validation establishes.

Validation evidence may be temporary. A targeted command, one-off probe, isolated scenario,
existing system/contract test, static validator, parser, compiler, or direct inspection of the
relevant outcome can establish the change without creating a new permanent test. After validation is
defined, make the retention decision independently through the admission gate below. Do not convert
every piece of close evidence into recurring suite ownership.

## Test admission gate

Every maintained test has lifecycle cost. Do not create one merely because code, configuration, or
documentation changed. Admit a new test only when all of the following can be stated at useful
resolution:

- the meaningful behavior, invariant, interface, failure mode, or externally observable contract it
  protects, and the authority for that obligation;
- a plausible regression or failure that the test can independently distinguish;
- why existing protection does not already catch that failure adequately; and
- why a maintained automated test is better evidence than an existing lint/schema/static check,
  generated-artifact validation, behavioral evaluation, or one-time verification.

When those answers do not justify another maintained test, return `NO NEW TEST JUSTIFIED`. Validation
may still be required; refusing a regression test does not mean skipping appropriate checks.

Treat text assertions by what behavior they discriminate, not by whether the text is machine- or
human-facing. Exact text is a valid oracle when the observed value demonstrates a consequential path,
outcome, or authoritative externally observable contract. For example, an expected error message can
prove that the intended error path was reached for the scenario.

Do not retain assertions whose only claim is that prose, instructions, headings, examples, comments,
or phrases continue to exist. For agent instructions, phrase presence is not behavioral evidence:
require evidence that changing or removing the instruction adversely affects a desired agent outcome
before treating its presence as regression protection. Use behavioral evaluation for that causal
claim. Machine-readable frontmatter, schemas, manifests, and metadata remain eligible for structural
validation through their actual parser/consumer contract.

Admission question: **What undesirable behavior can occur if this assertion is removed while all
other tests remain green?** If the answer is only that someone could rewrite/remove a sentence or
implementation detail, the assertion has no demonstrated protection benefit.

## Contract altitude

Use contract altitude to choose what a maintained test should observe. Higher altitude means closer
to the durable goal and farther from incidental implementation:

```text
holistic/system outcome
  -> user/public/cross-component contract
    -> component/interface contract
      -> TDD-sized unit behavior
        -> private implementation detail
```

Prefer the highest stable altitude that still discriminates the consequential failure with acceptable
execution cost and diagnostics. Trace lower-level tests upward to the contract or holistic goal they
help protect. A test that only proves an implementation fact exists, without a supported behavioral
claim above it, has weak retention value.

Keep unit tests at TDD scale. Use the smallest executable example needed to drive or clarify one
behavioral slice; do not expand unit coverage to mirror every helper, branch, constant, call count,
internal ordering, or decomposition choice. A behavior-preserving refactor should normally leave the
unit test green. Retain lower-level tests when they protect a stable local contract or uniquely
distinguish an important fault that broader evidence cannot catch cheaply.

## Test economics

Treat every retained test as a recurring liability purchased for future protection. Use this decision
model qualitatively; do not manufacture numerical scores when the evidence does not support them:

```text
retained-test value = expected protection benefit - expected ownership cost
```

Retain or add the test when its expected protection benefit materially exceeds its recurring
ownership cost and no cheaper evidence provides equivalent protection. Consolidate, replace, or omit
it when the same important failures are protected more cheaply elsewhere. High cost never justifies
dropping a required guarantee without a surviving carrier.

Assess **expected protection benefit** from:

- **consequence avoided** — severity of the failure the test can prevent from escaping;
- **regression exposure** — how plausibly that failure can recur as the system changes;
- **detection effectiveness** — how reliably the test would fail for that relevant defect;
- **unique protection** — what important failure this test catches that surviving evidence does not;
- **contract durability** — whether the protected behavior is expected to remain stable through
  implementation redesign;
- **feedback value** — whether the failure arrives early enough and clearly enough to change action.

Assess **expected ownership cost** across the test's remaining lifetime, not only its runtime:

- **comprehension/context cost** — human and agent tokens/time needed to understand the test,
  fixtures, helpers, and its relationship to the product;
- **change-coupling cost** — expected churn when private helpers, constants, branches, ordering,
  file layout, prose, generated text, or other noncontractual implementation details change;
- **fixture/data upkeep** — maintaining builders, snapshots, golden files, mocks, seeds, test data,
  environment setup, and cleanup;
- **execution cost** — CI latency, compute, external resources, hardware, services, and local feedback
  time;
- **diagnostic cost** — effort to determine whether a failure is product, test, fixture, environment,
  or expectation drift;
- **flakiness/noise cost** — reruns, false alarms, quarantines, intermittent failures, and lost trust
  in the suite;
- **dependency/environment cost** — toolchain, service, platform, version, credential, and
  compatibility maintenance required only by the test;
- **refactor drag** — valid redesign constrained or slowed because the test encodes implementation
  rather than behavior;
- **duplication cost** — repeated protection whose maintenance and failures add little information
  beyond a stronger surviving test;
- **review/coordination cost** — extra diff, merge-conflict, review, and update burden every time
  related code or documentation changes.

Do not use cheap execution as evidence of cheap ownership: a millisecond assertion over a hard-coded
constant can cost more over its lifetime than a slower black-box contract test if it churns on every
valid refactor. Conversely, an expensive end-to-end test still needs enough unique protection to
justify its infrastructure and diagnostic burden.

## Principles

### 1. Protect a stable behavioral contract

Name the required outcome, invariant, interface guarantee, or failure risk a test protects and its
source. Distinguish approved intent from observed behavior, derived interpretation, and proposals.
Existing output is useful characterization evidence, not automatically the desired answer. Test
behavior rather than mirroring the current implementation [1], [9].

### 2. Discriminate against plausible defects

For each material test, name a realistic fault that its observation should distinguish. For changed
regression protection, demonstrate the original defect or a relevant safe negative control when that
evidence can materially change confidence. Do not manufacture mutations or fault-injection ceremony
for trivial behavior merely to satisfy a template. Check that execution reaches the intended
observation: an unrelated import, collection, or setup failure does not establish fault detection.
Coverage records execution; mutation testing challenges detection [3]. Neither a surviving
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

### 5. Prefer the highest-value faithful boundary

Choose the boundary from contract altitude, consequential behavior, and failure mechanism, not from a
testing-pyramid quota or a preference for isolated functions. When one system, integration, contract,
or lifecycle test can protect the same meaningful behavior as many implementation-level tests,
prefer the broader stable boundary if it remains discriminating, diagnosable, and maintainable.
Exercise real component composition when cross-component behavior is the guarantee.

Use a function/unit boundary for a TDD-sized behavioral slice when that boundary is itself stable,
when broader tests cannot cheaply distinguish an important fault, or when the smaller test materially
improves diagnosis without duplicating the same protection. A private helper's edge cases, constants,
or current branches do not earn tests merely because they exist. Protocol, transaction, packaging,
hardware, startup, persistence, authorization, and recovery guarantees need the relevant real seam
[4], [5].

Inspect what fixtures, mocks, fakes, and bypassed adapters remove from observation. Check a double's
relevant assumptions against the real dependency where needed. Architect controllable clocks,
storage, network, and hardware seams without mocking away the mechanism the test must challenge.

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

### 8. Select interactions systematically

Use combinatorial selection only after the protected contract, consequence, boundary, and oracle are
known. It is a case-selection technique, not a source of requirements or expected results.

When several independent factors can jointly affect an admitted obligation, identify behaviorally
distinct values with equivalence partitioning and justified boundaries. Model relevant input, state,
configuration, environment, and capability factors; omit incidental implementation dimensions.
Distinguish impossible configurations from reachable invalid requests: constrain away only states the
test environment cannot meaningfully exercise. Rejections, authorization failures, forbidden effects,
and other negative behavior remain test obligations when the interface can receive those requests.

Choose interaction strength from the failure mechanism and consequence. Pairwise coverage is a useful
default candidate for broad low-cost interaction sampling, not a completeness claim. Use higher-order
coverage, explicit scenarios, stateful sequences, or exhaustive coverage where a consequential fault
requires them. Always preserve known regression-inducing and high-consequence combinations explicitly;
a covering-array generator may pack other combinations around those cases when supported.

A generated matrix establishes only its verified combination-selection claim. It does not establish
that execution reached the intended mechanism, that an oracle is correct, or that temporal behavior
was exercised. Earlier rejection can mask later factors. For every generated family, verify feasible
t-way coverage independently of merely producing a model or invoking a tool, and state exclusions and
uncovered interactions. Record generator/version/options/seed when they affect reproducibility. If the
generator is unavailable, report the model as proposed rather than generated evidence.

Credit existing tests that already satisfy required interactions before adding cases. Apply the normal
admission gate and test economics to the family as a whole and to uniquely valuable explicit cases.
When rows are removed or consolidated, recompute any claimed covering property for the surviving
suite. Combinatorial selection may be temporary close-validation evidence; it does not automatically
justify permanent retention.

### 9. Control the experiment

Control or record relevant time, randomness, versions, configuration, filesystem, shared state,
scheduling, and external dependencies. Preserve failing inputs, seeds, logs, and traces. Timing,
order dependence, shared state, and overly strict assertions can make tests flaky [7].
For nondeterministic behavior, predeclare permitted outcomes or justified statistical criteria and
report trials, failures, and uncertainty. Do not tighten tolerances or add retries to hide a defect.
A passing rerun does not explain a failure; unavailable, skipped, xfailed, or interrupted work is
not passing behavioral evidence. Account for cleanup of processes, threads, resources, and state.

### 10. Make failures interpretable

Keep scenario, action, expected behavior, and observation legible. Use behavior-oriented names and
helpers that expose rather than conceal the important input/state. Emit expected/actual differences
and enough context to reproduce the failure. Avoid a fixture framework that reproduces production
complexity or hides the oracle [2]. Follow the project's applicable typing and fixture conventions.

### 11. Maintain protection, not test count

Adjudicate failures as product, requirement, oracle, or harness/environment defects before editing
expectations. Compare a material rewrite against its original protection and unacceptable regressions.
Account for every meaningful guarantee when deleting or consolidating tests. Overlap across unit,
contract, and integration boundaries is not automatically redundancy [1], [5], but neither does each
boundary deserve its own copy of the same assertion.

Apply the test-economics model above: compare expected protection benefit with expected ownership
cost over the test's remaining lifetime. Do not collapse that decision to runtime, coverage, or test
count. High cost alone never removes a required guarantee. It matters when the same important failure
is already caught by a cheaper surviving carrier, or when the test protects no justified contract at
all. Ask explicitly: if this test disappeared, which plausible important regression could now pass
undetected, and what recurring ownership cost disappears with it?

When valuable externally observable behavior remains correct through a refactor, prefer deleting or
generalizing a brittle implementation-coupled test over teaching it the new internals. Place
high-signal checks where their evidence is useful; moving a check later changes the detection window,
not the need for the guarantee.

## Compact test card

Use a small note for a simple test or a table for a family. Reuse an existing design instead of
requiring a separate artifact for every assertion. Fill these fields only to the resolution needed
for an implementer and reviewer to agree on what the test demonstrates:

```text
Claim and authority: required behavior, source, unresolved interpretation
Protection benefit: consequence, recurrence exposure, unique detection, durability, feedback value
Ownership cost: context/churn/fixtures/execution/diagnosis/flakiness/dependencies/refactor drag/duplication
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
destructive effects before execution. Preserve the original target and the user's working tree,
production resources, credentials, and live state. An authorized disposable copy or isolated worktree
may contain temporary seeded faults, including edits to its tracked source; do not publish or merge
those faults. Record the baseline revision, verify isolation from live services, and clean up only
the experiment-owned resources. The reviewer never changes the original target. If execution is
unavailable or unsafe, return the proposed probe with an unvalidated result. Do not weaken project
gates to make verification convenient.

## Coverage policy

Coverage is diagnostic evidence, not a universal quality target. Use it to locate unexercised code
for consequence review, not to create work mechanically. Do not infer value from a percentage and do
not add tests solely to raise it.

When reviewing another repository, obey its active merge gate while separately identifying whether
that gate has an evidence-backed purpose. When auditing testing policy, recommend removing a
repository-wide threshold that has no documented relationship to a demonstrated risk; a genuinely
useful threshold should be scoped to the subsystem and rationale it protects.

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

## Review at protection-family resolution

Do not make large-suite review cost proportional to raw test count. First group tests that appear to
protect the same claim at the same boundary against the same relevant failure mechanism. Deep-trace
individual tests only where the disposition can change: high-consequence guarantees, suspicious or
circular oracles, uncertain family equivalence, implementation/prose coupling, high lifecycle cost,
flaky or expensive execution, or uncovered behavior.

A family is an analysis convenience, not evidence of redundancy. Split it whenever variants,
boundaries, forbidden effects, diagnostics, or fault mechanisms differ materially. Report the
unexamined remainder when sampling or representative tracing leaves uncertainty.

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

[1]: https://abseil.io/resources/swe-book/html/ch11.html
[2]: https://abseil.io/resources/swe-book/html/ch12.html
[3]: https://pitest.org/
[4]: https://abseil.io/resources/swe-book/html/ch13.html
[5]: https://abseil.io/resources/swe-book/html/ch14.html
[6]: https://hypothesis.readthedocs.io/en/latest/stateful.html
[7]: https://docs.pytest.org/en/stable/explanation/flaky.html
[8]: https://martinfowler.com/bliki/TestDrivenDevelopment.html
[9]: https://testing.googleblog.com/2013/08/testing-on-toilet-test-behavior-not.html
