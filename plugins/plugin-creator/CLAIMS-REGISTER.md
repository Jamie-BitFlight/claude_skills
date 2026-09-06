# Claims register

Design-time. Each entry records a claim this plugin's structure or instructions rest on, where it
is relied on, how it was established, and the re-check that would overturn it. Runtime text states
the instruction only and never links here. Date every entry; a claim without a re-check is a note.

## 1. `references/*.md` are not substituted

**Claim**: `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` are substituted in a `SKILL.md` body
(plain prose and markdown link targets alike) and are not substituted inside `references/*.md`.

**Relied on by**: every skill here that ships `references/`; the `shared-content-references`
skill's Technique 1 and 2 forms; `rules/skill-substitution.md`.

**Warrant**: canary-tested in this repo on 2026-08-06, run twice, once with the plugin fully
reloaded, against a no-variable control line. Record:
`.claude/agent-memory/python-engineering-python-cli-architect/project_claude_plugin_root_bang_exec_vs_later_bash.md`
(repo-local; the same result is summarised in `rules/skill-substitution.md` and in
`skills/shared-content-references/references/verification.md`). Vendor documentation, as read on
2026-09-06 and recorded in `rules/skill-substitution.md`: `code.claude.com/docs/en/skills` lists the
variables under "Available string substitutions" and scopes substitution to the skill's markdown
content and `allowed-tools`; `code.claude.com/docs/en/plugins-reference` says "anywhere the
placeholder appears". Neither page names `references/`, and the two pages disagree with each
other, so the canary is what this plugin relies on.

**Re-check**: activate `/example-argument-substitution`, or put `${CLAUDE_SKILL_DIR}` in both a
skill body and one of its `references/*.md`, invoke the skill, read the reference file, and compare
the raw tool output — an expanded path in one and a literal token in the other. Run it after any
Claude Code release that changes the substitution table.

## 2. Substitution outside Claude Code

**Claim**: no harness other than Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` or
`${CLAUDE_SKILL_DIR}` in a `SKILL.md` body. **Status: reported, unconfirmed in this repo.**

**Relied on by**: the rule's part 2 preferring a relative path, and the
`shared-content-references` skill's choice of the relative link as Technique 1's primary form.
Neither depends on the claim being true — a relative path needs no substitution anywhere — so a
reversal would loosen the rule, not break the plugin.

**Warrant**: the only primary source in this repo is Codex passing the literal string through in a
plugin's `.mcp.json` — `openai/codex` issue 19582, cited in
`research/design-notes/2026-06-14-plugin-creator-packaging-assessment.md`; that is a different
surface from a `SKILL.md` body. Backlog item #3445 (2026-09-06) reports checking harness source
and vendor documentation for Codex, OpenCode, Crush, Cursor and Kimi and finding no substitution;
its sources are not reproduced in this repo. Search run 2026-09-06:
`grep -rniE 'opencode|\bcrush\b|cursor' rules/ docs/ research/ plugins/plugin-creator/` filtered
for `substitut|CLAUDE_PLUGIN_ROOT|CLAUDE_SKILL_DIR|interpolat|expand` matched only this plugin's
own maintenance notes.

**Re-check**: install this plugin under each harness, open a `SKILL.md` that carries the variable
in plain prose, and read what the agent receives. One harness at a time; record the version.

## 3. Agent bodies

**Claim**: whether an agent body (`agents/*.md`) substitutes `${CLAUDE_PLUGIN_ROOT}` is unknown.

**Relied on by**: nothing — the six agents state the rule inline, which needs no substitution.

**Warrant**: no test on record. Backlog item #3430 carries the canary procedure.

**Re-check**: the procedure in #3430 — a variable line plus a no-variable control line in an agent
body, dispatched, and the raw text compared.
