# Memory Index

- [skilllint token threshold](skilllint-token-threshold.md) — after editing a SKILL.md: a
  green prek run can hide skilllint's SK006 token warning; run skilllint directly and read its warnings.
- [backlog_core connection-failure taxonomy](backlog-core-connection-failure-taxonomy.md) —
  writing offline/unreachable/unavailable cause prose in a backlog_core doc: first pick the path,
  background sync (OFFLINE vs ERROR) or per-call cache fallback.
- `evaluate-sdlc-layers/SKILL.md` exists as two regular-file copies that have drifted apart:
  `plugins/development-harness/skills/evaluate-sdlc-layers/` and `.claude/skills/evaluate-sdlc-layers/`.
  Apply every edit to both.
- `plugins/development-harness/tests/test_retired_terms.py` is a live regression guard: one
  parametrized row per retired mechanism (regex over `.md/.json/.yaml/.yml/.py/.cjs/.mjs` under
  `skills/`, `agents/`, `hooks/`, `templates/`, `docs/`, plus `AGENTS.md`/`README.md` and repo-root
  `.claude/skills/evaluate-sdlc-layers/`), scoped to
  files an installed agent actually reads at runtime (excludes `docs/audits`, `docs/plans`,
  `docs/workflow-layers`, `tests/`, generated graphs). Run it after any edit that renames or
  deletes a mechanism this plugin's docs describe — it lists exact file:line hits to fix. Adding a
  newly-retired term is a one-line `RetiredTerm(...)` append to `_RETIRED_TERMS`. Edit the prose,
  never the test, to turn a row green.
- Specialist/quality-gate resolution vocabulary to reuse verbatim when rewriting stale
  "language manifest" prose: roles and gates resolve live via
  `mcp__plugin_dh_backlog__profile_list()` (enumerates every installed agent's `name`/`plugin`/
  `description`, no manifest/config file to maintain); `skills/dh-meta-docs/references/
  role-resolution-protocol.md` Step 4 is the single canonical source for the quality-gate
  discovery order (pre-commit config → CI workflow → build config → file-type fallback) — other
  docs should point at it with "Activate `dh:dh-meta-docs` for the Role Resolution Protocol's
  quality-gate discovery sequence" (front-load "Activate", matches the wording already used in
  `execution/SKILL.md`, `final-verification/SKILL.md`, `comprehensive-test-review/SKILL.md`)
  rather than restating the lookup order themselves.
