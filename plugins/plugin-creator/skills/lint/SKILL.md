---
name: lint
description: Use when checking skill quality, validating frontmatter before commit, or diagnosing validator warnings. Runs the plugin validator on a skill, agent, or plugin directory — reports token complexity, broken links, frontmatter issues, and structural problems. Pass the path as an argument.
argument-hint: <path-to-skill-or-plugin>
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.

<provided_path>
$ARGUMENTS
</provided_path>

Run `uvx skilllint@latest check <path>` via Bash, using the exact literal path in <provided_path/>. Never splice <provided_path/> directly into a `` !`...` `` injection line or any other shell-interpreted string — it is caller-supplied text and may contain characters (`;`, `` ` ``, `$()`, `|`) that corrupt shell parsing on contact.

Read the findings straight from the command output. Each one carries its error code, severity, the
field or path it applies to, and the suggested fix. Report those to the user and act on them; do
not look up a code anywhere else. Re-run with `--fix` to apply the auto-fixable ones.

## Runtime escapes

When <provided_path/> is a plugin directory, also run:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/lint/scripts/audit_runtime_escapes.py" --plugin-dir <path>
```

It reports every path, markdown link, and cross-plugin reference in the plugin's runtime files
that resolves only in the authoring repo, with file:line for each. Exit 0 means clean; exit 1
means findings. Pass `--all` instead of `--plugin-dir` to sweep every plugin and get one count
each.

A finding is real when the text tells the runtime agent to act on something an installed
consumer does not have. Fenced blocks are exempt, because an anti-pattern shown in a fence is an
illustration rather than an instruction; angle-bracket placeholders are exempt for the same
reason. Move an illustrative real path into a fence, and write a generic one as
`<plugin>/skills/<name>/SKILL.md`.

`${CLAUDE_PLUGIN_ROOT}/docs/runtime-environment.md` contains the
three-part test each finding is measured against.
