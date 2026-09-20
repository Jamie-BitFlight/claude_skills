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
  lines — before the model sees the text.

Literal `$N` is only safe to document inside `references/*.md` files, which are not substituted —
a SKILL.md itself cannot explain this syntax without being corrupted by it. `${CLAUDE_PLUGIN_ROOT}`
and `${CLAUDE_SKILL_DIR}` are likewise NOT substituted inside `references/*.md` files — only the
`SKILL.md` body itself. Canary-test any new substitution-adjacent pattern
(`/example-argument-substitution`) before applying it across multiple files.

**Multi-mode workflow skills**: when a SKILL.md parses `$ARGUMENTS` into a structured `<input>`
JSON block, its `references/workflows/*.md` files use self-closing XML tags (e.g. `<item_ref/>`)
as **labels naming a key in that JSON** — not variables passed into the file. Reference them as
"the value from the `item_ref` key," never "the parser provides `item_ref`."

After editing any SKILL.md, invoke the skill and confirm it still renders correctly with no
unexpected prompts or extra steps.
