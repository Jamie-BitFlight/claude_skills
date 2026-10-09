# Technical review judgment

Use while assessing review findings or drafting responses. This is guidance for deciding what should change, not a substitute for the available provider tools.

## Assess impact and cause

1. Establish the intended runtime user and the behavior they experience today. Verify the finding against code, tests, requirements, and observed usage. The requesting user owns intended outcomes; technical claims from every source require evidence.
2. Determine whether the proposed change would improve that experience. Check for existing runtime handling, compatibility obligations, and regressions. A valid symptom may already be addressed by another mechanism.
3. Look across related findings for a shared cause. Repeated exception handling, expanding regex patterns, or recurring fixes around one seam can signal that the chosen mechanism is unsuitable. Compare reuse of existing tools, structured APIs, programmatic validation, and LLM/subagent judgment before extending the mechanism.
4. Choose a proportionate disposition: local fix, shared-cause fix, redesign, no change, superseded, or clarification. Record why the chosen level is sufficient and how to verify its runtime effect.

For proposed functionality expansion, inspect known call sites, external entry points, and documented requirements before concluding it is needed or unused. Escalate conflicts with prior user decisions.

## Communicate technical conclusions

For accepted findings, explain the observed change, verification, and inspectable revision. For disputed findings, explain the evidence and consequence, then give a focused question or disposition. Correct an earlier conclusion when new evidence warrants it.

Example: A reviewer proposes removing compatibility code. The current build target and tests still exercise the older platform. Establish the consumer impact and ask whether support is intentionally being dropped before accepting the removal.

## Source and license

Adapted from [obra/superpowers receiving-code-review](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/receiving-code-review/SKILL.md). Upstream source is MIT-licensed; the [license notice](./superpowers-license.txt) is retained, Copyright (c) 2025 Jesse Vincent. This reference contains adapted guidance rather than verbatim upstream procedures.
