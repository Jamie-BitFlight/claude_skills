The purpose and explicit goals of the skill multi-perspective-review:

1. Orchestrate four independent, parallel perspective reviews (Security, Performance, Quality,
   Accessibility) of a diff by creating an ephemeral SAM plan and dispatching four
   `dh:task-worker` teammates via `TeamCreate`, without serializing them.
2. Synthesize the four verdicts into one deduplicated, cross-referenced punch list via a fifth
   synthesis worker, reconciling the synthesized output against each perspective's raw
   `Review Results` section to catch a silently altered or dropped verdict or finding.
3. Apply a gate (a missing verdict or any REJECT fails; SKIP is a passing outcome; all four
   SKIP passes with a warning) and print one canonical summary line per perspective, exiting
   non-zero when the gate fails.
4. Guarantee run isolation — every invocation creates a fresh ephemeral plan and team, keyed by a
   collision-resistant run stamp, so no run reads or is polluted by another run's state.
5. Keep the verdict/punch-list schema and dispatch mechanics owned by companion skills
   (`dh:review-verdict-contract`, `dh:dispatch-contract`) rather than duplicated in this file.
