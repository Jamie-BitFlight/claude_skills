# Technical review guidelines

Apply these guidelines to every human, bot, reviewer, and stakeholder input during assessment. Record the conclusions in the assessment and cluster plan. Use the response guidance when planning and authoring communication under the [review-cycle contract](./review-cycle-contract.md).

## Contents

- [Understand and verify](#understand-and-verify)
- [Check technical context](#check-technical-context)
- [Check necessity and usage](#check-necessity-and-usage)
- [Order accepted independent clusters](#order-accepted-independent-clusters)
- [Push back with evidence](#push-back-with-evidence)
- [Avoid premature agreement](#avoid-premature-agreement)
- [Acknowledge verified feedback](#acknowledge-verified-feedback)
- [Correct mistaken pushback](#correct-mistaken-pushback)
- [Worked examples](#worked-examples)
- [Source and license](#source-and-license)

## Understand and verify

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

```text
1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
```

## Source authority

Treat the requesting user as authoritative on intended outcomes and architectural decisions, while verifying technical claims from every source, including the user. When feedback conflicts with a prior decision, identify the conflict and request direction rather than silently overriding it.

## Check technical context

Apply these checks before accepting a source change. When a claim cannot be verified, record the missing fact and focused clarification as `clarification_required`; a request for direction does not replace the evidence or mutation-authority gates. Keep an input that conflicts with a prior user decision open until that conflict is resolved.

```text
BEFORE implementing:
  1. Check: Technically correct for THIS codebase?
  2. Check: Breaks existing functionality?
  3. Check: Reason for current implementation?
  4. Check: Works on all platforms/versions?
  5. Check: Does feedback account for context established by code, tests, requirements, and prior decisions?

IF suggestion seems wrong:
  Push back with technical reasoning

IF can't easily verify:
  Say so: "I can't verify this without [X]. Should I [investigate/ask/proceed]?"

IF conflicts with your human partner's prior decisions:
  Stop and discuss with your human partner first
```

## Check necessity and usage

Investigate the relevant consumer boundary before declaring something unused: inspect known call sites, externally exposed entry points, and documented requirements proportionately. A local search miss is not proof that external consumers do not exist. Do not expand implementation merely because a reviewer proposes additional functionality.

Apply the existing assessment evidence and mutation-authority requirements when choosing a branch below. A local search miss alone does not establish `unused`; record any unresolved usage question as `clarification_required`.

```text
IF reviewer suggests "implementing properly":
  grep codebase for actual usage

  IF unused: "This endpoint isn't called. Remove it (YAGNI)?"
  IF used: Then implement properly
```

## Order accepted independent clusters

After assessing and clustering the complete evidence set, apply this priority among accepted independent clusters. Verify each coherent cluster before dependent work continues. Preserve shared-cause cluster boundaries and dependency order. If a clarification is required, pause only changes dependent on the missing fact; continue demonstrably independent work after complete assessment. Run independent clusters concurrently when resources allow; use the following priority only to select among ready clusters when capacity is constrained.

- Blocking issues (breaks, security)
- Simple fixes (typos, imports)
- Complex fixes (refactoring, logic)

Verify no regressions

Use the cluster verification commands and repository-required gates.

## Push back with evidence

Push back when:

- Suggestion breaks existing functionality
- Feedback omits or contradicts context established by the code, tests, requirements, or prior decisions
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Legacy/compatibility reasons exist
- Conflicts with your human partner's architectural decisions

**How to push back:**

- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- Involve your human partner if architectural

**If evidence remains insufficient or feedback conflicts with an architectural decision:** Identify the missing fact or conflicting requirement and ask the user a focused question.

## Avoid premature agreement

**NEVER:**

- "You're absolutely right!" (explicit instruction-file violation)
- "Great point!" / "Excellent feedback!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**

- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong

## Acknowledge verified feedback

Lead with the observable change and its verification rather than lengthy agreement. A concise code reference is useful evidence, but does not replace the provider-backed reply required for PR/MR completion. For conversational reviews, report the assessed disposition directly without fabricating provider state.

Use these concise statements after the cited change is implemented and verified. Include the exact input reference, supporting evidence, and inspectable revision required by the review-cycle contract.

When feedback IS correct:

```text
✅ "Fixed. [Brief description of what changed]"
✅ "Good catch - [specific issue]. Fixed in [location]."
```

## Early discussion versus final disposition

When a review question or disputed claim needs discussion before implementation, distinguish a provisional question from a verified final disposition. Do not promise or report a fix as completed until it is implemented and tested. The current PR/MR command validator requires completed implementation states before provider mutation; until an independently validated clarification-only command exists, raise early questions in the user conversation rather than bypassing that gate.

## Correct mistaken pushback

If you pushed back and were wrong:

```text
✅ "You were right - I checked [X] and it does [Y]."
✅ "Verified this and you're correct. My initial understanding was wrong because [reason]."

❌ Long apology
❌ Defending why you pushed back
❌ Over-explaining
```

State the correction factually and move on.

Update the assessment and cluster plan with the corrected evidence. Follow the implementation, validation, and provider-communication gates before posting the disposition.

## Worked examples

Use these examples to guide technical reasoning and response wording. Apply the usage-evidence rule above to the YAGNI example and the review-cycle gates to every provider response.

**Performative Agreement (Bad):**

```text
Reviewer: "Remove legacy code"
❌ "You're absolutely right! Let me remove that..."
```

**Technical Verification (Good):**

```text
Reviewer: "Remove legacy code"
✅ "Checking... build target is 10.15+, this API needs 13+. Need legacy for backward compat. Current impl has wrong bundle ID - fix it or drop pre-13 support?"
```

**YAGNI (Good):**

```text
Reviewer: "Implement proper metrics tracking with database, date filters, CSV export"
✅ "Grepped codebase - nothing calls this endpoint. Remove it (YAGNI)? Or is there usage I'm missing?"
```

## Source and license

SOURCE: [obra/superpowers receiving-code-review](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/receiving-code-review/SKILL.md).
The excerpts are licensed under the [MIT license](./superpowers-license.txt), Copyright (c) 2025 Jesse Vincent.
