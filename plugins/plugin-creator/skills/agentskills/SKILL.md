---
name: agentskills
description: Agent Skills portable format router. Use when creating cross-client skills, validating portable frontmatter, packaging skills for upload or API use, or implementing skill discovery and activation.
user-invocable: true
---

# Agent Skills Portable Format

Use this skill for the portable Agent Skills boundary. Use
`plugin-creator:claude-skills-overview-2026` instead for Claude Code runtime extensions such as
hooks, context forks, model selection, and invocation controls.

Load the reference that matches the current branch:

- **Schema or validation**: Read [specification.md](./references/specification.md) for the portable
  directory shape, frontmatter fields, name rules, resources, and `skills-ref` behavior.
- **Authoring**: Read [best-practices.md](./references/best-practices.md) for description design,
  workflow structure, scripts, references, assets, and evaluation guidance.
- **Client implementation**: Read [integration.md](./references/integration.md) for discovery,
  metadata loading, activation, security boundaries, and reference-library usage.

Portable upload and package boundaries accept `name`, `description`, `license`, `compatibility`,
`metadata`, and experimental `allowed-tools`. Host extensions are outside this schema and may be
rejected rather than ignored.

Primary sources: [Agent Skills specification](https://agentskills.io/specification) and
[live client showcase](https://agentskills.io) (accessed 2026-09-24).
