---
name: test-failure-mindset
description: Investigate pytest failures without treating tests or implementation as automatic authority. Use when diagnosing regressions, debugging test errors, or deciding whether to fix a test or code; trace the contract, product, fixture, and observation before choosing an evidence-backed correction.
user-invocable: true
---

# Test Failure Analysis Mindset

Establish the governing contract before choosing a product or test correction.

Load [Python Development Standards](../standards-for-python-development/SKILL.md) for shared
rules, preserving the target repository's supported versions, configuration, and conventions.

## Core principle

Tests encode claims about expected behavior. Validate those claims against authoritative intent;
neither the test nor the current implementation is automatically correct. Documents can establish
intent without proving execution. Preserve requirements and established project gates while
investigating; do not invent policy to reconcile conflicting artifacts.

## Competing hypotheses

Consider an implementation defect, an incorrect or outdated expectation, a producer/consumer
contract mismatch, and a fixture, mock, observation, or CI/environment defect. More than one can
apply. Name a discriminating observation before changing either the test or the product.

## Investigation protocol

1. **Preserve and reproduce.** Record the tested revision, actual checkout, command, configuration,
   dependencies, complete failure output, and relevant ordering/parallelism before changing state.
   Reproduce safely under those conditions, then reduce without losing the mechanism. Distinguish
   your execution from supplied logs; report unavailable reproduction instead of claiming success.
2. **Establish authority.** Read the test's name, comments, assertions, and relevant history. State
   the purpose, consumer, observable guarantee, invariants, authoritative source, and falsifier.
   Resolve factual unknowns through available evidence; escalate only consequential intent/safety
   decisions that cannot be resolved that way.
3. **Trace both paths.** Follow the product from entry point to consumer and the test from fixture
   through observation to assertion. Cite the earliest demonstrated contract divergence, including
   setup, cleanup, side effects, and material caller/callee boundaries. A failing assertion is a
   symptom until its mechanism is established.
4. **Choose the correction.** Correct a product violation, an invalid oracle, or a misleading
   harness according to the evidence; record why an expectation changes. For an architectural
   change, identify the causal condition removed and why a smaller fix is insufficient. Preserve
   useful behavior; do not add abstractions or mock around the failing boundary just to pass.
5. **Validate and learn.** Before a material edit, record the expected improvement, baseline,
   protected invariants, and unacceptable regressions. Show the relevant fault is detected and
   the corrected behavior passes; verify the failure is at the intended assertion, not setup or
   collection. Cover related boundary cases proportionately and document residual uncertainty.

For intermittent failures, compare controlled conditions with a predeclared observation and
stopping rule. Report failures/trials and confounds; an effect need not cause failure on every
run. Neither a successful rerun nor insufficient evidence of an effect establishes a fix.

## Decision record

Return the violated contract and its authority, reproduction/evidence limits, causal mechanism,
correction category (product, architecture/interface, test oracle, harness/CI, or intent decision),
and claim-to-validation evidence. Keep trigger, mechanism, and structural contributors distinct.
State an unresolved cause explicitly rather than choosing whichever side is easier to change.

## Reject these shortcuts

- Changing expectations to match implementation, or assuming either side is authoritative.
- Bulk-updating snapshots or removing inconvenient cases without individual contract analysis.
- Using a mock/stub, skip, warning suppression, retry-until-green, or relaxed gate to hide the defect.
- Regenerating a stale artifact before a freshness assertion and calling the original state valid.
- Counting coverage, a mapped task, source inspection, or unexecuted scenarios as behavioral proof.

Name tests by observable behavior. Explain corrected expectations with the requirement evidence,
not a comment that merely says the code changed. Retain appropriate fakes/mocks at genuine seams;
the defect is masking the guarantee under investigation, not the existence of a test double.

## Related skills

Use [Analyze Test Failures](../analyze-test-failures/SKILL.md) for detailed failure analysis and
[Comprehensive Test Review](../comprehensive-test-review/SKILL.md) to assess the resulting tests.
When `dh:root-cause-tracing-process` is available, pass the existing evidence record to it for
expanded causal tracing. Otherwise use the protocol above; the Python plugin must remain usable
without DH or Process Siren. Do not assume an optional plugin is installed.
