---
name: claude-plugins-reference-2026
description: Claude Code plugin and marketplace router. Use when creating plugins, configuring component paths, resolving installed files, validating plugin roots, or distributing local, Git, and archive sources.
user-invocable: true
---

# Claude Code Plugins and Marketplaces

Load only the branch needed for the current task:

- **Manifest, component paths, default discovery, agents, skills, MCP, or LSP**: Read
  [manifest-and-components.md](./references/manifest-and-components.md).
- **Installed paths, source modes, scopes, runtime variables, writable state, or cache lifecycle**:
  Read [caching-and-runtime.md](./references/caching-and-runtime.md).
- **Marketplace schema, source types, enterprise restrictions, authentication, or distribution**:
  Read [marketplaces-and-distribution.md](./references/marketplaces-and-distribution.md).
- **Install, enable, list, validate, local-test, or debug commands**: Read
  [cli-and-debugging.md](./references/cli-and-debugging.md).
- **Hook events and handler types**: Read [hook-events.md](./references/hook-events.md), then load
  `plugin-creator:hooks-guide` for implementation guidance.
- **Monitors**: Read [monitors.md](./references/monitors.md).
- **Enable-time user configuration or channels**: Read
  [user-config.md](./references/user-config.md).

This skill documents Claude Code's host package. For portable Agent Plugins or another host's
overlay, read
[agent-plugin-ecosystem.md](../skill-creator/references/agent-plugin-ecosystem.md) before choosing
a manifest or component layout.

Primary sources: [Plugins reference](https://code.claude.com/docs/en/plugins-reference),
[Create plugins](https://code.claude.com/docs/en/plugins), and
[Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) (accessed 2026-09-24).
