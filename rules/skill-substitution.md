# SKILL.md String Substitution

Happens at load time, including inside fenced code blocks — backslash-escaping (`\$1`) does not
prevent it:

- `$ARGUMENTS`, `$ARGUMENTS[N]`, `$0`–`$9` — arguments passed at invocation
- `${CLAUDE_SESSION_ID}` — current session ID
- `${CLAUDE_SKILL_DIR}` — the skill's own directory (for plugin skills: the skill subdirectory,
  NOT the plugin root)
- `${CLAUDE_PLUGIN_ROOT}` — the plugin's root directory. Applies only when the loaded `SKILL.md`
  belongs to a plugin (not a project-level `.claude/skills/` skill). Substitutes throughout the
  entire rendered body — plain prose and markdown link targets, not only `` !`bash` `` injection
  lines — before the model sees the text. Now listed in `code.claude.com/docs/en/skills`'s own
  substitution table, under "Available string substitutions" (checked 2026-09-06); that page
  scopes it to the skill's markdown content and `allowed-tools` Bash rules, while
  `code.claude.com/docs/en/plugins-reference` says skill content substitutes "anywhere the
  placeholder appears" — the two pages disagree, and the canary result below is what this repo
  relies on. Verified live via `dh-meta-docs` and `implementation-manager`, and canary-tested against a
  no-variable control line (2026-08-06) — see
  `.claude/agent-memory/python-engineering-python-cli-architect/project_claude_plugin_root_bang_exec_vs_later_bash.md`.

Literal `$N` is only safe to document inside `references/*.md` files, which are not substituted —
a SKILL.md itself cannot explain this syntax without being corrupted by it. `${CLAUDE_PLUGIN_ROOT}`
and `${CLAUDE_SKILL_DIR}` are likewise NOT substituted inside `references/*.md` files — only the
`SKILL.md` body itself. Canary-test any new substitution-adjacent pattern
(`/example-argument-substitution`) before applying it across multiple files.

Hook/command scripts additionally receive these as real process env vars (a separate mechanism from
the load-time text substitution above): `CLAUDE_PROJECT_DIR` (project root, all hooks),
`CLAUDE_PLUGIN_ROOT` (plugin root, plugin hooks only — `CLAUDE_PLUGIN_DIR` does not exist),
`CLAUDE_ENV_FILE` (SessionStart hooks only), `CLAUDE_CODE_REMOTE`.

**Multi-mode workflow skills**: when a SKILL.md parses `$ARGUMENTS` into a structured `<input>`
JSON block, its `references/workflows/*.md` files use self-closing XML tags (e.g. `<item_ref/>`)
as **labels naming a key in that JSON** — not variables passed into the file. Reference them as
"the value from the `item_ref` key," never "the parser provides `item_ref`."

**Agent `tools:` frontmatter** requires exact, correctly-cased tool names
(`mcp__Ref__ref_search_documentation`, not `mcp__ref__...`). Separator format is free — comma,
comma-without-space, space, and a YAML list all parse identically; write comma-and-space. Verify
every MCP name against the running server, not against another agent file.

An entry that matches no live tool is dropped and the rest of the grant still resolves. When every
entry resolves to nothing the subagent refuses to launch, reporting that it "would be spawned with
zero tools" and naming the unresolved entries.

Grant a whole MCP server with `mcp__<server>__*` or `mcp__<server>` — both forms grant every tool
that server exposes and compose with named tools. A plugin-bundled server registers as
`mcp__plugin_<plugin-name>_<server-name>`. Either form grants nothing while that server is
disconnected, so an agent whose `tools:` list is MCP-only cannot be invoked at all until the server
returns. Give such an agent at least one non-MCP tool unless that runtime dependency is intended.

After editing any SKILL.md, invoke the skill and confirm it still renders correctly with no
unexpected prompts or extra steps.
