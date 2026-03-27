---
name: lint
description: Use when checking skill quality, validating frontmatter before commit, or diagnosing validator warnings. Runs the plugin validator on a skill, agent, or plugin directory — reports token complexity, broken links, frontmatter issues, and structural problems. Pass the path as an argument.
argument-hint: <path-to-skill-or-plugin>
user-invocable: true
---

!`uvx skilllint@latest check $ARGUMENTS`

@${CLAUDE_PLUGIN_ROOT}/references/ERROR_CODES.md
