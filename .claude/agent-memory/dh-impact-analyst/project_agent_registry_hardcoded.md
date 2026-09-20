---
name: project_agent_registry_hardcoded
description: Agent add/rename/remove also needs a code edit in populate-agent-descriptions.mjs, which hard-codes agent keys
metadata:
  type: project
---

`plugins/plugin-creator/skills/agent-capability-analyzer/scripts/populate-agent-descriptions.mjs` holds hard-coded agent registries as JS literals (`{ key: 'plugin-creator:<agent>', ... }`, plus user and project agent arrays). Its SKILL.md mentions only frontmatter seeding, so read the script itself for the key lists.

**How to apply:** When a change adds, renames, or removes an agent in any plugin, list this script in the Impact Radius as a code change, and diff its keys against the plugin's `agents/` directory. Report every gap that diff shows, including gaps that predate the change.
