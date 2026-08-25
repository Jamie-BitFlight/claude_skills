# Skill load-time substitution

Apply these rules when checking a tightened skill through Claude Code:

- Claude substitutes `$ARGUMENTS`, `$ARGUMENTS[N]`, `$0` through `$9`,
  `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`, and `${CLAUDE_PLUGIN_ROOT}` throughout
  `SKILL.md`, including fenced code blocks, before the model receives it.
- Backslash escaping does not prevent substitution.
- `${CLAUDE_SKILL_DIR}` resolves to the skill directory. `${CLAUDE_PLUGIN_ROOT}` resolves to the
  plugin root for plugin skills.
- Files outside `SKILL.md`, including `references/*.md`, are not substituted when read. Put literal
  substitution examples there instead of inline in `SKILL.md`.
- Hook and command environment variables are a separate runtime mechanism; their existence does
  not prove how `SKILL.md` rendered.

Invoke the tightened skill through its supported harness and inspect the rendered behavior. When a
change touches argument substitution, compare no-argument and representative-argument invocations.
Do not infer preservation from source text alone.

Source: [Claude Code skills documentation](https://code.claude.com/docs/en/skills), accessed
2026-08-25. `${CLAUDE_PLUGIN_ROOT}` prose/link substitution and the lack of substitution in
reference files are additional behavior verified by this project because the upstream substitution
table does not document them.
