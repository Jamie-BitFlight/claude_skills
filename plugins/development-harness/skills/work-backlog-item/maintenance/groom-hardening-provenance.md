# Groom finalize hardening provenance

Two rules in `references/workflows/groom/finalize.md` were added in response to a real failure,
not designed speculatively — don't regress them when editing that file:

- The RT-ICA Final Pass citation requirement (no condition status may change to AVAILABLE without
  a pasted tool-output or user-message citation).
- The Diagnostic Gate (identify why a required section is absent or empty before retrying or
  writing directly).

Source: session observation, #1899 groom failure diagnosis, 2026-04-23.

## Output Validation Gate retry — same model only

The retry logic (Diagnostic Gate → 1st/2nd retry → BLOCKED after 3 attempts) never escalates to a
more capable model. The observed failure mode for a missing/malformed required section is an
interrupted agent (token exhaustion, network timeout, session terminated), not a model capability
gap — every model calls the same MCP tool fields, so a bigger model doesn't address an interrupted
write. Don't add a model-escalation branch to this retry logic without addressing that mismatch.

## Carried from the retired `groom-backlog-item` skill

`groom-backlog-item/SKILL.md` was reduced to a router forwarding to `/dh:work-backlog-item groom`
on 2026-04-06 (`567650d2`); its `references/` directory stopped being loaded by anything from that
date but was not deleted until later. An equivalence audit
(`.tmp/scratch/groom-ref-equivalence.md`) compared its four orphaned files against this skill's
runtime surface before the directory was removed. What was carried forward, and where:

- **Scope-gate ACs and repo hooks** (from `groomer-agent.md`) — a scope-limiting acceptance
  criterion (e.g. "no other file changes") must be scoped to changes the agent makes by hand;
  a repo's own hooks (pre-commit, husky, prek, lint-staged) rewriting files as an enforced side
  effect of committing is the hook doing its job, not a scope violation. Carried to
  `references/workflows/groom/swarm.md` "#### Scope-gate ACs and repo hooks". This rule was added
  to `groomer-agent.md` five months *after* the router commit made that file unreachable, so it
  had never taken effect at runtime before this carry-over — treat it as a first activation, not
  a restoration, and watch for the originally-observed failure shape (a scope-limiting AC failing
  a correct implementation because of hook-driven file changes) if it resurfaces.
- **Description / AC separation, final sentence** (from `groomer-agent.md`) — when the description
  already contains checkboxes or an Acceptance header, treat them as informal notes and write ACs
  that complement rather than duplicate them. The detection half of this rule already lived in
  `backlog_core/operations.py`'s `_check_ac_overlap` advisory warning; only the instruction for
  what to do about it was missing. Carried to `references/workflows/groom/swarm.md`
  "#### Description / AC separation".
- **Multi-item concurrency cap** (from `groomer-agent.md`) — cap concurrent grooming at 5 items,
  batching in waves of 5 for larger sets. Carried to `references/workflows/groom/start.md`
  "## Batch Grooming" — the one place in this skill's groom workflow that governs multi-item
  fan-out (the `(or next item if batch)` branch in the Checklist). Stated there only; do not
  restate the cap elsewhere.
- **Skipped-retry fallback** (from `groomer-output-validation.md`) — if the single
  `mark_groomed_skipped` retry also comes back skipped, stop retrying and tell the user the item
  may have been renamed or removed mid-session. Carried to
  `references/workflows/groom/finalize.md`, immediately after the `mark_groomed_skipped` retry
  block.

**Deliberately left behind, not carried:**

- `groomer-output-validation.md`'s haiku → haiku → sonnet retry ladder — superseded by the
  same-model-only retry documented above under "Output Validation Gate retry — same model only".
  Carrying the ladder back would reintroduce the model-escalation branch that section explains why
  the redesign dropped.
- `groomer-agent.md`'s human-override shortcut for recurring-pattern classification ("if the human
  has already identified the recurrence pattern, skip the search") — the audit judged the current
  behavior (`agents/classifier.md` always searches and treats a match count below 2 as a
  classification error) the safer default, so this was not carried.
- `drift-check.md`'s four verbose per-file output templates (`**Files checked**`,
  `**Commits since plan**`, etc.) and its explicit "no drift detected" text — `groom-drift.md`
  replaced these with one compact shared findings format; the audit judged this a deliberate
  format simplification, not a procedural loss.
- `issue-classification.md` had no unmatched content beyond the human-override shortcut above.
  `drift-check.md` had no unmatched content beyond the output-template simplification above.

Source: `.tmp/scratch/groom-ref-equivalence.md` (equivalence audit) and this carry-over pass,
2026-09-07.
