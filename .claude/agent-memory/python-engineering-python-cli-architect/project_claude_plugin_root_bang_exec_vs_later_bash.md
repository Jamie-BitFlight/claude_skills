---
name: project-claude-plugin-root-bang-exec-vs-later-bash
description: CLAUDE_PLUGIN_ROOT resolves in SKILL.md bang-exec (!`...`) lines but NOT in plain prose/code-fence text the agent runs later via the Bash tool — two different execution contexts, easy to conflate
metadata:
  type: project
---

Two genuinely different execution contexts get confused under one name. Distinguish them before
touching any `${CLAUDE_PLUGIN_ROOT}` reference in a SKILL.md:

1. **`!`-prefixed bang-exec lines** (e.g. `` !`find ${CLAUDE_PLUGIN_ROOT}/docs -name '*.md'` ``) —
   Claude Code itself spawns this subprocess at skill-*load* time and exports `CLAUDE_PLUGIN_ROOT`
   as a real env var on that one process, same class as a hook handler. **Works.** Verified twice
   empirically in this session by invoking `dh:dh-meta-docs` (line 11, unedited — resolved to real
   `.../plugins/development-harness/docs/*.md` paths) and `dh:implementation-manager` (line 13,
   edited to `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"` — returned real plan JSON, not an
   error). Independently corroborated the same session by a concurrent agent on PR #2781 who
   fixed this exact line and falsification-tested it from `/tmp` and the repo root.

2. **Plain prose or fenced code-block text** documenting a command the agent is meant to read,
   then run *later* via the Bash tool (e.g. a `### list` section showing
   `uv run plugins/development-harness/sam_schema/cli.py plan list` as a copyable example) —
   this is NOT bang-exec. The agent's later Bash tool call is a separate, unrelated subprocess;
   Claude Code injects nothing into it. Verified empirically: `echo $CLAUDE_PLUGIN_ROOT` in a
   plain Bash tool call in this session returned empty, despite development-harness clearly being
   an active plugin (other plugins' `bin/` dirs were on `$PATH`). **Does not work** — writing
   `${CLAUDE_PLUGIN_ROOT}` into this kind of content produces a literal unexpanded token that the
   later shell resolves to an empty string, breaking the path silently.

**How to apply**: before writing `${CLAUDE_PLUGIN_ROOT}` into any SKILL.md content, check whether
the line starts with `!` (bang-exec, safe) or is documentation text (not bang-exec, broken). The
same distinction applies to `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}`, EXCEPT those two are
also officially documented as substituted directly into a skill's *rendered body text* (not just
bang-exec) per code.claude.com/docs/en/skills.md "Available string substitutions" — `CLAUDE_PLUGIN_ROOT`
is conspicuously absent from that same table, which is consistent with case 2 above.

**Contamination note**: an earlier version of this file
(`project_skillmd_bang_exec_plugin_root.md`, correctly documenting case 1) was deleted in commit
`aab00913` under the label "false claim," citing this session's commits `81d4c29a`/`bb9468af` as
the disproof. Those two commits were actually case 2 (plain prose, genuinely broken) — the
deletion conflated the two contexts and threw out a true, independently-corroborated finding along
with the false one. Re-tested both cases directly in this session before writing this file; case 1
re-confirmed true, case 2 re-confirmed broken. See [[project_sam_console_script_cwd_dependence]] for
the related bare-`sam`-console-script gotcha. This file was deleted a second time by the same
concurrent session (`cf384837`) before that session accepted the evidence and stood down; restored
here unchanged from its pre-deletion content, plus this update.

**Update — final, broader confirmation**: substitution isn't specific to bang-exec lines — it
applies to a `SKILL.md`'s entire rendered body (bang-exec lines and plain prose alike), consistent
with how `${CLAUDE_SKILL_DIR}`/`${CLAUDE_PROJECT_DIR}` are documented to work skill-body-wide.
`code.claude.com/docs/en/skills.md` simply doesn't list `CLAUDE_PLUGIN_ROOT` in its substitution
table — a documentation gap, not evidence of the runtime behavior. Separately confirmed:
`references/*.md` files (loaded as supporting material, not the primary skill body) do **not** get
any substitution, tested twice including with the plugin fully reloaded. The actual dividing line
is "is this the `SKILL.md` body" vs "is this a `references/*.md` file it links to" — not
"bang-exec vs later Bash-tool prose" as this file originally framed it. Fix landed in
`plugins/development-harness/skills/*.md` (14 files, commit `c8cd67c5`): `${CLAUDE_PLUGIN_ROOT}`-relative
paths in `SKILL.md` bodies; `references/*.md` files carry no invocation prefix at all, deferring to
a `<sam_cli>` block in the owning `SKILL.md` as the single resolved source (commit `e2703d13`).
