---
name: project_agent_registry_hardcoded
description: Agent add/rename/remove also needs a code edit in populate-agent-descriptions.mjs, which hard-codes agent keys
metadata:
  type: project
---

`plugins/plugin-creator/skills/agent-capability-analyzer/scripts/populate-agent-descriptions.mjs` holds hard-coded agent registries as JS literals (`{ key: 'plugin-creator:<agent>', ... }`, plus user and project agent arrays). The skill's SKILL.md describes the script only as seeding `description` fields from frontmatter.

**How to apply:** When a change adds, renames, or removes an agent in any plugin, list this script in the Impact Radius as a code change, and diff its keys against the plugin's `agents/` directory. The registry already lags `plugins/plugin-creator/agents/`, so report existing gaps too.
