---
title: "Workflow-Continuity Risk Lens — Case Studies"
purpose: "Worked, mechanism-grounded examples of assessing backlog-grooming severity by pipeline data-continuity, not literal data deletion"
related:
  - agents/impact-analyst.md
  - agents/classifier.md
created: 2026-08-19
---

# Workflow-Continuity Risk Lens — Case Studies

The [S1-S7 pipeline](../AGENTS.md#sam-7-stage-pipeline) and the
[backlog grooming stages](./backlog-item-lifecycle.md) hand data forward through the configured
backend at every step — grooming writes a section, RT-ICA reads it, dispatch reads the plan,
sync reconciles provider state, verification reads the acceptance criteria. A byte can survive
that handoff on disk and still be lost to the workflow: written by one step, never consulted by
the step that needed it. That is the failure this lens targets. It is not a generic
infrastructure-engineering "will bytes be deleted" check — see `impact-analyst.md`'s Core
Principle for the directive itself; this file is the worked evidence for why the distinction
matters and how to verify it.

Each case below states the initial (wrong-lens) severity call, the corrected call, and the exact
function or file that settles the question — so the correction is reproducible, not asserted.

## Case 1 — `add_item()`'s missing `item_ref` (issue #2999)

**Wrong-lens call**: "No data loss — just a silent local/GitHub drift between the backlog record
and the created issue." Assessed and dismissed as cosmetic because no stored value is deleted or
corrupted.

**Mechanism**: `backlog_core/operations.py::add_item()` only sets `result["item_ref"]` inside
`if issue_ref:` — a caller that doesn't specifically check for the key's presence cannot tell a
degraded local-only create from a full success. That gap does self-heal eventually:
`sync_items()` (`operations.py:2926`) calls `sync_create_missing_issues()` (`operations.py:2851`)
first, which finds items lacking an issue and creates one. So the item is not lost.

**Corrected call**: the real risk is a **reconciliation gap**, not data loss. After
`sync_create_missing_issues()` runs, `sync_items()` re-lists only `items_with_issues()`
(`operations.py:2942`) and reconciles just that `references` set via
`backend.reconcile(ReconcileRequest(scope=ReconcileScope.LINKED, ...))`
(`operations.py:2944-2946`). Any item still lacking `issue_ref` at that point — a create that
failed, was skipped in `dry_run`, or hasn't run yet — receives **zero reconciliation** in that
pass: no drift detection, no remote-content merge, and no signal to any step reading the item
(grooming, RT-ICA, dispatch) that a retry is pending. Acceptance criteria should target *that*
gap — bound how long the item can sit in the unreconciled state and make the pending state
visible to readers — not a generic "prevent data loss" criterion, which the self-healing retry
already satisfies.

## Case 2 — split-brain agent-memory directory (issue #2998) — a rejected hypothesis

**Hypothesis under this lens**: two memory directories exist for the same conceptual agent —
`.claude/agent-memory/dh-service-docs-maintainer/` and
`.claude/agent-memory/service-docs-maintainer/`. If institutional knowledge gets written under
one name and a later session reads under the other, that knowledge is functionally lost —
written but never consulted, the same continuity-gap shape as Case 1.

**Verification**: read both directories and this repo's naming convention (every other memory
directory follows `{plugin-short-name}-{agent-name}`, e.g.
`python-engineering-python-cli-architect`). The correctly-prefixed directory
(`dh-service-docs-maintainer/`) is the one actively written and current; the bare, unprefixed
directory is stale, predates the naming convention, and nothing resolves to it.

**Corrected call**: zero workflow-continuity risk in this instance. The hypothesis was the right
*kind* of check but wrong for this pair — the live directory was already the one in use. Keep
this case as the standing caution: **the lens generates a hypothesis, not a verdict.** A
plausible continuity gap must still be checked against which path is actually read before it is
reported as a finding — grep for the consuming reference, or list both candidates and confirm
which one is live, the way this case was resolved.

## Case 3 — stale CI ruleset flag (issue #2997) and StatusLabel registry drift (issue #3004)

**#2997 — `strict_required_status_checks_policy: false`.** Wrong-lens framing: "could allow a
broken build to merge." Continuity framing: a green CI check is data every downstream agent
trusts without re-verifying — this repo's own `.claude/rules/commit-cadence-and-worktrees.md` has
worktree-isolated agents branch from `HEAD` on the assumption that `HEAD` passed CI. Without the
strict flag, a PR's displayed status can go stale relative to `main` and nothing re-checks it
before merge — the trusted signal silently stops being consulted by the process (auto-rebase,
worktree branching) that depends on it being current.

**#3004 — hardcoded `VERIFIED_LABEL` duplicate in `.github/workflows/quality-gate-audit.yml`
line 23.** Wrong-lens framing: "string duplication, a code-quality nit." Continuity framing: that
JS constant is a second, independent copy of `backlog_core/gh_client.py`'s `DH_LABELS` registry
with no shared source — an audit workflow whose job is catching improperly-closed issues reads
its own stale copy of the label name instead of the canonical one. A renamed or added status
label drifts silently past the audit that exists specifically to catch drift: the audit trust
boundary stops being consulted correctly, without any error surfacing.

## Case 4 — `claim_task` atomicity (issue #3002) — verify against existing decisions, not just code

**Wrong-lens framing**: "no compare-and-swap on `claim_task` — a race condition, should be
fixed." Filed as a P2 defect proposing a CAS rewrite.

**Verification finding**: `sam_schema/core/gist_task_layer.py` (`ADR-2509-3`, line ~859)
documents that this repo's architecture *already* made this decision deliberately —
`claim_task` delegates exactly-once claiming to caller-side serialization specifically because
GitHub's label API has no CAS primitive to build one on. The proposal doesn't identify a new
defect; it argues against a documented, accepted mitigation without first reading it.

**Corrected call**: before treating an apparent gap as an open defect (or, for classifier.md,
before applying the `defect` decision-tree branch), check whether an ADR or design doc already
addresses it. `grep -rn "ADR-" plugins/development-harness/sam_schema/` or the equivalent for the
subsystem in question is the concrete check — a "this looks broken" observation that skips it
risks re-litigating a decision the codebase already made for a documented reason.

## Applying this to a new finding

1. State the initial severity call using the literal-deletion instinct if that's what comes to
   mind first — it's a useful draft, not a mistake to suppress.
2. Identify the specific downstream step (by function or file, as in Cases 1 and 3) that is
   supposed to read this data next.
3. Verify — don't assume — whether that step's actual code path consults the data. Case 2 is the
   reminder that this step is not optional: a plausible gap can turn out to be already handled.
4. Re-state severity in terms of what the next step can or cannot do because of the gap, not in
   terms of whether bytes persist on disk.
5. Before filing a `defect`, check for an existing ADR or design decision that already accepted
   the behavior being flagged (Case 4).
