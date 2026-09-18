# Memory Index

- [DH MCP-vs-CLI Documentation Structure](dh-mcp-cli-docs.md) — canonical CLI-mapping source, which
  dh docs already pair MCP-reference sections with a dedicated CLI section, and the drift patterns
  found there (stale tool names, overstated parity, extraction-rule blind spots).
- [Unenforced map guarantee](unenforced-map-guarantee.md) — backlog_view map mode's "under 2,000
  tokens" claim is not enforced by disclosure_handler.py; other locations asserting the same false
  bound; tracking issue #3059.
- [skilllint token threshold](skilllint-token-threshold.md) — prek passing does not mean
  skilllint's 4400-token SKILL.md ceiling still passes; re-run skilllint directly after edits.
- Worktree isolation: when cwd is under `.claude/worktrees/<name>/`, Edit/Write reject the
  shared-checkout path (e.g. `/Users/.../repos/claude_skills/plugins/...`) with "session is
  isolated in the worktree" — retarget the identical relative path rooted at the worktree instead
  (`.claude/worktrees/<name>/plugins/...`). Read tolerates either path; Edit/Write do not.
- [Dispatch placeholder & shared-worktree gotchas](dispatch-placeholder-and-shared-worktree.md) —
  `{A}` is the canonical attempt-number placeholder across the dh dispatch-line contract (four
  files, no single source of truth); `close/start.md` handles both `close` and `resolve` routes,
  don't conflate them; the `agent-marketplace-versioner` prek hook failing can be a concurrent
  agent's edit in a shared worktree, not your own change — diff before reverting.
- [backlog_core connection-failure taxonomy](backlog-core-connection-failure-taxonomy.md) — two
  independent "provider unreachable" mechanisms (background `sync_engine`/`classify_sync_error`
  vs. per-call `FileCache`/`try_get_github()`), their exact cause sets, and which one
  ARCHITECTURE.md actually documents (only the per-call one, as of 2026-09-15) — check this before
  writing offline/unreachable/unavailable cause prose in any backlog_core doc.
- DH plugin has two separate copies of `evaluate-sdlc-layers/SKILL.md` (not a symlink):
  `plugins/development-harness/skills/evaluate-sdlc-layers/SKILL.md` and repo-root
  `.claude/skills/evaluate-sdlc-layers/SKILL.md`. They drift independently — check both when a
  retired term or deleted-file link touches either one.
- `work-backlog-item`'s `scripts/parser/parse.schema.json` documents the same argument vocabulary
  as its `SKILL.md` frontmatter/body (no Python code reads it — the agent parses `$ARGUMENTS`
  against it itself). Keep both in sync when a flag is added or retired; drift tests that scan
  only `*.md` never catch this JSON silently going stale.
- Deleting a "layer" or "profile" concept outright needs its own index doc's count/row claims
  updated too, not just the target files removed — e.g. "Layer 1: All 6 docs present" must shrink
  when a doc in that list is deleted, and "N-layer architecture" framing sentences at the top of
  index READMEs need the layer count fixed.
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
