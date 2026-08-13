# Work - backlog item - Scope boundary

The work stage bridges a groomed backlog item into the SAM planning pipeline. Its job is to answer:

- What is the architecture and task decomposition for this item?
- Which SAM profile and language stack apply?
- What is the implementation plan?

The work stage runs after grooming is complete (or re-grooms if stale) and produces a SAM plan
that the implementation workflow can execute. It covers item location, state validation, GitHub
sync, discovery, auto-grooming, RT-ICA gating, feasibility assessment, and SAM plan creation.

Work does NOT produce:

- grooming analysis (that belongs to the groom workflow)
- RT-ICA assessment beyond the gate check in prepare.md (RT-ICA is consumed, not generated here)
- problem framing or impact analysis (those are groom and discovery outputs)
- discovery artifacts (discovery is invoked if absent, but the artifact is owned by `dh:discovery`)

**Required outputs**

A completed work result must produce:

- a SAM plan created by `dh:add-new-feature` and discoverable via `sam_plan(config={"action": "list"})`
- a `plan` field on the backlog item set to the returned `plan_ref` via `backlog_update`
- item status transitioned to `in-progress` via `backlog_update(status="in-progress")`
