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
