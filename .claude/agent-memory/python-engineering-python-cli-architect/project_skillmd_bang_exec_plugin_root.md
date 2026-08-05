---
name: project-skillmd-bang-exec-plugin-root
description: SKILL.md `!`-prefixed bang-exec body commands receive CLAUDE_PLUGIN_ROOT as a real shell env var, expanded by the spawned shell (not Claude's own $ARGUMENTS-style text substitution) — verified empirically via dh-meta-docs precedent and a live fix
metadata:
  type: project
---

AGENTS.md's "Markdown (Skills/Commands/Agents)" section lists two *separate* substitution
mechanisms and is easy to misread as excluding `${CLAUDE_PLUGIN_ROOT}` from SKILL.md bodies:

- "SKILL.md string substitution" (Claude's own load-time text replace, works even inside single
  quotes / fenced code blocks): `$ARGUMENTS`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`.
- "Separate from SKILL.md substitution, hook/command scripts receive env vars": `CLAUDE_PROJECT_DIR`,
  `CLAUDE_PLUGIN_ROOT`, `CLAUDE_ENV_FILE`, `CLAUDE_CODE_REMOTE`.

A `!`-prefixed bang-exec line in a SKILL.md body (e.g. `!\`uv run "${CLAUDE_PLUGIN_ROOT}/x.py"\``)
is executed as a subprocess by the harness at load time — the same execution class as a hook/command
script — so it receives `CLAUDE_PLUGIN_ROOT` as a genuine environment variable, expanded by the
spawned shell. This means: use it **unquoted or double-quoted** (`"${CLAUDE_PLUGIN_ROOT}/path"`),
never single-quoted (`'${CLAUDE_PLUGIN_ROOT}/path'` will NOT expand — single quotes are literal in
bash and this var is not part of Claude's own text-substitution pass).

Prior art confirming this works in a plain bang-exec (not just `hooks:` frontmatter):
`plugins/development-harness/skills/dh-meta-docs/SKILL.md` line 11 —
`` !`find ${CLAUDE_PLUGIN_ROOT}/docs -name '*.md' -type f | sort` ``.

Fixed [[project_auto_sync_manifests.md]]-adjacent bug in
`plugins/development-harness/skills/implementation-manager/SKILL.md` (Codex PR #2781 finding):
the "Available features" bang-exec hardcoded `plugins/development-harness/sam_schema/cli.py`
(monorepo-cwd-relative) — replaced with `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"`.
Verified by reproducing the old failure (`uv run <relative-path>` from a non-repo cwd → "Failed
to spawn ... No such file or directory", silently masked by the line's `2>/dev/null || echo
<fallback>`), then confirming the `${CLAUDE_PLUGIN_ROOT}`-based path resolves the script correctly
regardless of cwd (from `/tmp`, execution reached the real business logic — a "not inside a git
repository" error from `dh_paths.infer_project_root`, not a path/spawn error).

**How to apply**: when a SKILL.md needs to reference its own plugin's files (scripts, docs) inside
a bang-exec command or a documented CLI invocation example, use `${CLAUDE_PLUGIN_ROOT}` — never a
path hardcoded relative to the monorepo checkout root. This is the established, working convention
in this repo (also used in `start-task/SKILL.md`'s `hooks:` block), not a new pattern to invent.
