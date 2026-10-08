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

## Check technical context

Apply these checks before accepting a source change. When a claim cannot be verified, record the missing fact and focused clarification as `clarification_required`; a request for direction does not replace the evidence or mutation-authority gates. Keep an input that conflicts with a prior user decision open until that conflict is resolved.

```text
BEFORE implementing:
  1. Check: Technically correct for THIS codebase?
  2. Check: Breaks existing functionality?
  3. Check: Reason for current implementation?
  4. Check: Works on all platforms/versions?
  5. Check: Does reviewer understand full context?

IF suggestion seems wrong:
  Push back with technical reasoning

IF can't easily verify:
  Say so: "I can't verify this without [X]. Should I [investigate/ask/proceed]?"

IF conflicts with your human partner's prior decisions:
  Stop and discuss with your human partner first
```

## Check necessity and usage

Apply the existing assessment evidence and mutation-authority requirements when choosing a branch below. A local search miss alone does not establish `unused`; record any unresolved usage question as `clarification_required`.

```text
IF reviewer suggests "implementing properly":
  grep codebase for actual usage

  IF unused: "This endpoint isn't called. Remove it (YAGNI)?"
  IF used: Then implement properly
```

## Order accepted independent clusters

After assessing and clustering the complete evidence set, apply this priority among accepted independent clusters. Preserve shared-cause cluster boundaries and dependency order.

- Blocking issues (breaks, security)
- Simple fixes (typos, imports)
- Complex fixes (refactoring, logic)

Verify no regressions

Use the cluster verification commands and repository-required gates.

## Push back with evidence

Push back when:

- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Legacy/compatibility reasons exist
- Conflicts with your human partner's architectural decisions

**How to push back:**

- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- Involve your human partner if architectural

**If you're uncomfortable pushing back out loud:** Name that tension, then tell your partner about the issue you've seen. They'll appreciate your honesty.

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

Use these concise statements after the cited change is implemented and verified. Include the exact input reference, supporting evidence, and inspectable revision required by the review-cycle contract.

When feedback IS correct:

```text
✅ "Fixed. [Brief description of what changed]"
✅ "Good catch - [specific issue]. Fixed in [location]."
```

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
