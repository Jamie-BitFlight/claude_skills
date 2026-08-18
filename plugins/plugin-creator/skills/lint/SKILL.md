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

@${CLAUDE_PLUGIN_ROOT}/references/ERROR_CODES.md
