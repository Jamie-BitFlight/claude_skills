# Technical review guidelines

Apply these guidelines to every human, bot, reviewer, and stakeholder input during assessment. Record the conclusions in the assessment and cluster plan. Use the response guidance when planning and authoring communication under the [review-cycle contract](./review-cycle-contract.md).

## Assess the claim

Interpret the requested outcome, inspect the implementation and requirements, and record validity, relevance, evidence, and any missing fact.

## Source authority

Treat the requesting user as authoritative on intended outcomes and architectural decisions, while verifying technical claims from every source, including the user. When feedback conflicts with a prior decision, identify the conflict and request direction rather than silently overriding it.

## Check technical context

Before accepting a change, check compatibility, regression risk, implementation rationale, supported platforms, and whether feedback accounts for established context. When evidence is insufficient, record `clarification_required` with a focused question. Surface conflicts with prior user decisions for direction.

## Check necessity and usage

For requests to expand or complete functionality, inspect the relevant consumer boundary: call sites, exposed entry points, and documented requirements. Base the decision on observed usage and requirements; unresolved usage becomes `clarification_required`.

## Order accepted independent clusters

Schedule accepted clusters by dependency. Run independent ready clusters concurrently when resources permit. When capacity is constrained, prioritize blockers, then simple changes, then complex changes. Verify each cluster before dependent work proceeds, using planned commands and repository gates. Pause only work dependent on unresolved clarification.

## Push back with evidence

When feedback conflicts with code, tests, requirements, compatibility, or prior decisions, state the evidence, consequence, and specific question or disposition. Escalate unresolved technical uncertainty or architectural conflicts to the user.

## Acknowledge verified feedback

Lead with the observed change, verification result, and inspectable revision. For PR/MR reviews, communicate each disposition through the provider with its stable reference; for conversational feedback, report the assessment directly.

## Early discussion versus final disposition

Separate provisional clarification from verified final disposition. Report a fix as completed after implementation and verification. The current provider-action validator requires implementation readiness; use the user conversation for early clarification until a validated provider clarification route exists.

## Correct mistaken pushback

If new evidence overturns an earlier assessment, state the corrected conclusion and evidence, update the cluster plan, and follow the verification and communication gates.

## Source and license

SOURCE: [obra/superpowers receiving-code-review](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/receiving-code-review/SKILL.md).
The excerpts are licensed under the [MIT license](./superpowers-license.txt), Copyright (c) 2025 Jesse Vincent.
