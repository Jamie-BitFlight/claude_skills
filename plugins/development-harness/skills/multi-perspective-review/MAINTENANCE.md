# Skill maintenance

## Regression provenance

- Plan reuse cannot be made safe by resetting task status alone.
  - Observed in: SKILL.md Step 3 authoring history (plan-reuse rationale, removed from runtime
    prose during a tightening pass — the bounded instruction "always create a new plan" survives
    in SKILL.md, this is why).
  - Required behavior: every run must create a brand-new ephemeral plan, never reuse an existing
    one by resetting task status.
  - Why: resetting a task's status makes it claimable again, but the task body still names the
    previous run's `changed_files` (workers would review the wrong file set), and the task's
    `Review Results` section already exists — the next `append_section` call lands inside that
    heading instead of creating a new one, leaving the section holding two concatenated JSON
    documents that no longer parse.
  - Protected by: none (no automated eval covers this; a regression would surface as a corrupted
    `Review Results` section on a reused plan).

## Review method provenance

The shared review preparation and investigation guidance in `docs/review-methods.md` adapts
questions about reach, consequences, failure controls and history from
[NeoLabHQ context-engineering-kit review](https://github.com/NeoLabHQ/context-engineering-kit/tree/23e2428e809d77717f8acc9659c374a3a1fcb93e/plugins/review),
especially `change-impact-agent.md`, `change-failure-agent.md`, `change-expectation-agent.md`,
`contracts-reviewer.md` and `historical-context-reviewer.md`. The guidance is independently written
and uses DH's existing impact-analysis, root-cause and test-review contracts. Risk prioritization
does not narrow changed-file coverage or alter the raw-verdict conservation and gate contracts.
