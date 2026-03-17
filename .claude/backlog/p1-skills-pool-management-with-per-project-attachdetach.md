---
name: Skills pool management with per-project attach/detach
description: "**Current state**: Skills in this repo are organized as plugin directories under `plugins/*/skills/` and symlinked into `.claude/skills/`. There is no concept of a 'skills pool' where skills can be dynamically attached or detached per project or per session. All skills from installed plugins are always available. The `sam` task system supports per-task `skills:` fields that instruct agents to load specific skills, but this is declarative metadata -- it does not prevent other skills from being available. The skill-creator skill creates skills but has no pool management or per-project scoping capability. Skills are either installed (present in `.claude/skills/`) or not -- there is no intermediate 'available but not active' state.\n\n**Target state**: A `skills.toml` or equivalent manifest at the project root or `~/.claude/` level that declares which skills are active for the current project/session. Skills in the pool but not in the manifest are available for attachment but not loaded by default. A command or MCP tool (`skill attach <name>`, `skill detach <name>`) manages the manifest and materializes/dematerializes symlinks. This enables project-specific skill scoping without modifying plugin directories.\n\n**Measurable signal**: File `skills.toml` exists at project root with a `[project.skills]` section listing active skill names. Running `skill attach <name>` adds an entry and creates the symlink in `.claude/skills/`. Running `skill detach <name>` removes the entry and symlink. `skill list --pool` shows all available skills; `skill list --active` shows only attached skills."
metadata:
  topic: skills-pool-management-with-per-project-attachdetach
  source: 'Research entry: ./research/developer-tools/agent-deck.md -- pattern: Skills pool management with per-session attach/detach'
  added: '2026-03-17'
  priority: P1
  type: Feature
  status: open
  issue: '#776'
  last_synced: '2026-03-17T23:46:20Z'
---