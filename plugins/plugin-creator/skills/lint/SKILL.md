---
name: lint
description: Use when checking skill quality, validating frontmatter before commit, or diagnosing validator warnings. Runs the plugin validator on a skill, agent, or plugin directory — reports token complexity, broken links, frontmatter issues, and structural problems. Pass the path as an argument.
argument-hint: <path-to-skill-or-plugin>
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.


!`uvx skilllint@latest check $ARGUMENTS`

@${CLAUDE_PLUGIN_ROOT}/references/ERROR_CODES.md
