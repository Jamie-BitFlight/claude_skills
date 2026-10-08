# Technical review guidelines

Apply these guidelines to every human, bot, reviewer, and stakeholder input during assessment. Record the conclusions in the assessment and cluster plan. Use the response guidance when planning and authoring communication under the [review-cycle contract](./review-cycle-contract.md).

## Assess the claim

1. Restate the requested technical outcome and identify the established requirements. The requesting user owns intended outcomes and architectural decisions; evaluate technical claims from every source against evidence.
2. Inspect the affected implementation, existing rationale, compatibility, supported platforms, tests, and regression risk. Check whether the feedback accounts for relevant context.
3. Record validity, relevance, evidence, and the proposed disposition. If a fact remains unresolved, use `clarification_required` with one focused question. Escalate conflicts with established user decisions for direction.

## Check necessity and usage

For requests to expand or complete functionality, inspect the relevant consumer boundary: call sites, exposed entry points, and documented requirements. Base the decision on observed usage and requirements; unresolved usage becomes `clarification_required`.

## Implement accepted clusters

Schedule accepted clusters by dependency. Run independent ready clusters concurrently when resources permit. When capacity is constrained, prioritize blockers, then simple changes, then complex changes. Verify each cluster before dependent work proceeds, using planned commands and repository gates. Pause only work dependent on unresolved clarification.

## Communicate the decision

Example: A reviewer requests removal of a compatibility branch. The build configuration still targets an older platform, and tests exercise that branch. Cite those facts and ask whether dropping older-platform support is intended before accepting the removal.

For accepted changes, lead with the observed change, verification result, and inspectable revision. For a disputed finding, state the relevant evidence, consequence, and focused question or disposition. If new evidence changes an earlier assessment, correct the conclusion and cluster plan before responding.

For PR/MR reviews, bind each disposition to its stable provider reference and follow the review-cycle communication gate. For conversational feedback, return the assessed findings directly. Distinguish provisional clarification from a verified fix: the current provider validator requires implementation readiness, so early clarification takes place in the user conversation until a validated provider clarification route exists.

## Source and license

SOURCE: [obra/superpowers receiving-code-review](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/receiving-code-review/SKILL.md).
The excerpts are licensed under the [MIT license](./superpowers-license.txt), Copyright (c) 2025 Jesse Vincent.
