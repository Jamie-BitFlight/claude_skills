# Memory Index

- [skilllint token threshold](skilllint-token-threshold.md) — after editing a SKILL.md: a
  green prek run can hide skilllint's SK006 token warning; run skilllint directly and read its warnings.
- [backlog_core connection-failure taxonomy](backlog-core-connection-failure-taxonomy.md) —
  writing offline/unreachable/unavailable cause prose in a backlog_core doc: first pick the path,
  background sync (OFFLINE vs ERROR) or per-call cache fallback.
- `evaluate-sdlc-layers/SKILL.md` exists as two regular-file copies that have drifted apart:
  `plugins/development-harness/skills/evaluate-sdlc-layers/` and `.claude/skills/evaluate-sdlc-layers/`.
  Apply every edit to both.
- `plugins/development-harness/tests/test_retired_terms.py` guards the plugin's runtime-read docs
  against retired mechanisms; its module docstring states the scan scope. Run it after any edit that
  renames or deletes a mechanism the plugin's docs describe — it prints each `file:line` hit. Retire
  a new term by appending one `RetiredTerm(...)` to `_RETIRED_TERMS`. Turn a red row green by
  editing the prose it names.
- Rewriting stale "language manifest" prose: roles and quality gates resolve live through
  `mcp__plugin_dh_backlog__profile_list()`, with no manifest file. The quality-gate discovery order
  lives only in Step 4 of `skills/dh-meta-docs/references/role-resolution-protocol.md`. Point at it
  with the sentence `skills/execution/SKILL.md` already uses ("Activate `dh:dh-meta-docs` for the
  Role Resolution Protocol's quality-gate discovery sequence") instead of restating the order.
