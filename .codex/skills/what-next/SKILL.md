---
name: what-next
description: Use when the user asks what to do next, asks for a plan under uncertainty, challenges stalled or low-trust work, requests multiple possible approaches before action, or needs an evidence-first loop that uses RT-ICA-style prerequisite checks, adversarial review, subagent coordination, real validation, and durable concern tracking.
---

# What Next

Use this skill to choose and execute the next move when the path is uncertain, trust is damaged, or the work needs more than the first plausible idea.

The core loop is:

```text
reconstruct goal -> reverse prerequisites -> classify completeness -> discover before asking
-> generate approach options -> adversarially eliminate -> synthesize
-> execution gate -> delegate/implement -> validate real behavior -> record concerns -> repeat
```

## Operating Rules

- Treat agreement, apology, and polished restatement as zero progress unless they produce an observable next action or decision.
- Generate multiple materially different approaches before choosing one. Five is a useful forcing function, not a required task count.
- Separate generation from evaluation. Do not critique options while brainstorming them.
- Use evidence before asking the user. If a question can be answered by reading source, docs, tests, runtime behavior, official documentation, or internet research, do that first.
- Use subagents for adversarial critique and independent work when available. If subagents are unavailable, perform the same critique directly and record that limitation as a validation or process concern.
- Do not execute implementation work until required execution inputs are available, evidence-derived, or safely defaulted.
- Validate through the actual mechanism the user depends on. Manual inspection can support diagnosis, but it is not proof of product behavior.

## Step 1: Reconstruct The Goal

Write a compact goal frame before planning:

```text
Goal:
- [One sentence describing the desired outcome]

Success output:
- [Observable artifact, behavior, test result, deployment state, or decision]

Scope:
- In scope: [known]
- Out of scope: [known]

Current evidence:
- [Facts already known, with sources when available]

Current risks:
- [Unproven assumptions, unknown changes, failed validations, or trust gaps]
```

If the goal cannot be stated as an observable result, classify that as an unresolved input and route it through discovery or a batched user question.

## Step 2: Reverse Prerequisites

Work backward from the success output. List conditions that must be true for success.

Include relevant categories:

- Functional behavior
- Interfaces, APIs, CLIs, schemas, files, or protocols
- Runtime and environment
- Packaging, install, distribution, or deployment
- Permissions, credentials, external systems, or side effects
- Verification, tests, observability, and rollback
- User intent, product meaning, policy, security, or compatibility
- Known risks and failure modes

For each condition, record:

```text
[Condition] | Requires: [specific information] | Why it matters: [failure if wrong]
```

## Step 3: Classify Completeness

Classify each prerequisite before using it in a plan:

- `AVAILABLE`: Explicitly present in the request, repo, docs, runtime output, tests, official docs, or another cited source.
- `EVIDENCE-DERIVED`: Forced by cited evidence. Record the inference basis and contradiction check.
- `PARTIAL`: Some evidence exists, but a material detail remains unresolved.
- `MISSING`: Required information is absent.
- `HARD-BLOCKED`: Proceeding risks destructive, irreversible, external, credential, production-data, compliance, security, authority, or user-meaning harm.
- `SAFE-DEFAULTED`: A bounded local default was chosen because every Safe Default Gate check passed.

Use this reflection checkpoint for every unresolved condition:

```text
Is this present, evidence-derived, partial, missing, or hard-blocked?
If unresolved, is the correct route discovery, validation spike, user decision, or safe default?
```

## Step 4: Route Unknowns

Route each `PARTIAL`, `MISSING`, or `HARD-BLOCKED` item:

- `DISCOVERY`: Source, docs, runtime behavior, tests, official docs, or internet research can answer it.
- `VALIDATION-SPIKE`: Only a targeted experiment can reduce the uncertainty.
- `ASK-USER`: The remaining choice is about intent, policy, scope, ownership, risk acceptance, product meaning, or user-visible behavior.
- `HARD-BLOCK`: The action is unsafe without authority, rollback, security clarity, compliance clarity, or destructive-risk resolution.
- `SAFE-DEFAULT`: The choice is narrow, reversible, local, non-user-visible, convention-backed, evidence-constrained, and verifiable before external impact.

Do discovery and validation spikes before asking the user. Batch any remaining `ASK-USER` items into one compact decision packet with options, constraints, risk, and a recommendation.

## Step 5: Generate Approach Options

For the immediate next decision, generate several distinct approaches. Each option must say what kind of movement it creates:

- `discovery`
- `specification`
- `planning`
- `implementation`
- `validation`
- `trust`
- `packaging`
- `deployment`
- `documentation`

Use this format:

```text
Decision:
- [The next unresolved choice]

Options:
1. [Approach] | Movement: [category] | Evidence needed: [source/test] | Main risk: [risk]
2. [Approach] | Movement: [category] | Evidence needed: [source/test] | Main risk: [risk]
...
```

The options must be materially different. Variants of the same action with different wording do not count.

## Step 6: Adversarial Review

Before selecting an option, run an adversarial review. Prefer a subagent with this brief:

```text
Review this next-step plan adversarially. Reject weak options and challenge assumptions.
Look for invented facts, missing evidence, local-only reasoning, unsupported safe defaults,
validation that does not exercise the real user path, unnecessary complexity, scope drift,
Claude/Codex or source/package mismatch, and anything that makes the product harder to
understand, less safe, or less efficient. Return rejected options with reasons, surviving
options with caveats, and required amendments.
```

If no subagent facility is available, perform the review directly and explicitly mark:

```text
Adversarial review mode:
- Direct, because subagents were unavailable.
```

## Step 7: Eliminate And Synthesize

Reject options that:

- Rely on speculation that can be researched.
- Depend on missing execution inputs.
- Cannot be validated through the real mechanism.
- Preserve local convenience while weakening user distribution, packaging, or runtime behavior.
- Break a required compatibility surface.
- Increase complexity without reducing real risk.
- Solve diagnosis while leaving product behavior unproven.

Select one option or synthesize a better option from survivors. Record why rejected options were rejected.

## Step 8: Execution Gate

Planning may continue with localized gaps if the plan includes discovery tasks, validation spikes, dependencies, and blocked execution gates.

Execution must block when required inputs remain `MISSING`, `PARTIAL`, or `HARD-BLOCKED`.

Before implementation or delegation, produce:

```text
Execution gate:
- Approved: [yes/no]
- Blocking inputs: [none or list]
- Safe defaults applied: [none or list with validation method]
- First validation that can prove this wrong: [command/test/runtime check]
```

## Step 9: Delegate Or Implement

Delegate by knowledge boundary, not by arbitrary task count:

- Combine tasks that require the same project-specific context.
- Split tasks that require distinct large context sets.
- Give each subagent a bounded deliverable, evidence requirements, and validation expectations.
- Do not pass the intended answer to validation subagents.
- Do not let a worker claim completion from self-report alone.

## Step 10: Validate Real Behavior

Validation must match the success output and the user's actual path.

Examples:

- If testing a plugin, install and load it through the harness rather than manually reading `SKILL.md`.
- If testing MCP behavior, start the MCP through the harness-installed config rather than invoking a script path by hand.
- If testing packaging, use the package/install path users will use.
- If testing a CLI, run the command and inspect output, exit code, and side effects.
- If validating docs or instructions, use a fresh agent or clean context to see whether the instructions produce the intended behavior.

If validation cannot run, record the exact blocker and do not claim the goal is complete.

## Step 11: Record Concerns

Emit a concern whenever work exposes:

- Tool failure or unreliable tooling
- Environment or configuration failure
- Verification gap
- Workaround or compatibility shim
- Partial success
- Stale or misleading documentation
- Suspicious complexity
- Ambiguous ownership
- Manual intervention requirement
- Risk accepted locally

Use this format:

```text
<concerns>
[Issue category]
  Observation: [what was found]
  Why it matters: [impact]
  Blocks current work: [yes/no]
  Recommended owner/destination: [owner, backlog, task stream, or user decision]
  Recommended follow-up: [specific action]
</concerns>
```

## Output Contract

When using this skill, produce a compact artifact with:

```text
WHAT NEXT

Goal:
- ...

Success output:
- ...

Prerequisites:
- [condition] | Status: [AVAILABLE/EVIDENCE-DERIVED/PARTIAL/MISSING/HARD-BLOCKED/SAFE-DEFAULTED] | Route: [N/A/DISCOVERY/VALIDATION-SPIKE/ASK-USER/HARD-BLOCK/SAFE-DEFAULT]

Immediate decision:
- ...

Candidate approaches:
1. ...
2. ...
3. ...

Adversarial review:
- Rejected: [option + reason]
- Survived: [option + caveat]
- Amendments: [...]

Selected next move:
- ...

Execution gate:
- Approved: [yes/no]
- Blocking inputs: [...]

Validation plan:
- ...

Concerns:
- [none or concern block]
```
