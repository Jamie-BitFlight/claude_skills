---
name: project_agent_registry_hardcoded
description: Agent add/rename/remove also needs a code edit in populate-agent-descriptions.mjs, which hard-codes agent keys
metadata:
  type: project
---

`plugins/plugin-creator/skills/agent-capability-analyzer/scripts/populate-agent-descriptions.mjs` holds hard-coded agent registries as JS literals (`{ key: 'plugin-creator:<agent>', ... }`, plus user and project agent arrays). The script's SKILL.md describes it only as reading frontmatter, so the list is easy to miss.

**How to apply:** When a change adds, renames, or removes an agent in any plugin, list this script in the Impact Radius as a code change, and diff its keys against the plugin's `agents/` directory. The registry already lags `plugins/plugin-creator/agents/`, so report existing gaps too.
