---
name: Claude Code Templates
description: CLI and web platform for discovering, installing, and managing 100+ ready-to-use agents, commands, skills, MCPs, settings, and hooks for Claude Code via npx or the aitmpl.com web interface.
license: MIT
metadata:
  topic: claude-code-templates
  category: skill-generation-tools
  source_url: https://github.com/davila7/claude-code-templates
  github: davila7/claude-code-templates
  version: "1.28.16"
  verified: "2026-03-03"
  next_review: "2026-06-03"
---

# Claude Code Templates

**Research Date**: 2026-03-03
**Source URL**: <https://aitmpl.com>
**GitHub Repository**: <https://github.com/davila7/claude-code-templates>
**NPM Package**: <https://www.npmjs.com/package/claude-code-templates>
**Version at Research**: v1.28.16
**License**: MIT

---

## Overview

Claude Code Templates is a comprehensive collection of ready-to-use configurations for Anthropic's Claude Code, distributed via npm and a curated web interface at aitmpl.com. It provides 100+ agents, custom commands, skills, MCP integrations, settings, and hooks that can be installed into any Claude Code project with a single `npx` command. The project also ships standalone developer tools — analytics monitoring, a conversation viewer, a health check diagnostic, and a plugin dashboard — all accessible through the same CLI entrypoint.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Starting a Claude Code project requires manually writing agents, commands, and hooks from scratch | Pre-built catalog of 100+ components installable with one `npx` command or via the web UI |
| Discovering what Claude Code components the community has built is fragmented | Central registry at aitmpl.com with browse, search, and one-click installation |
| Installing multiple components across different types requires separate steps | Composable `npx` flags (`--agent`, `--command`, `--mcp`, `--hook`, `--setting`, `--skill`) allow stacking |
| Monitoring Claude Code session activity requires custom tooling | Built-in `--analytics` flag streams live session state and performance metrics |
| Remote inspection of Claude responses from mobile is not straightforward | `--chats` flag with optional `--tunnel` exposes a Cloudflare-tunnelled mobile-optimised viewer |
| Verifying Claude Code installation health requires expert knowledge | `--health-check` flag runs comprehensive diagnostics and reports actionable issues |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 21,851 | 2026-03-03 |
| Forks | 2,064 | 2026-03-03 |
| Contributors | 52 | 2026-03-03 |
| Latest GitHub Release Tag | v1.28.3 | 2025-11-15 |
| npm Package Version | v1.28.16 | 2026-03-03 |
| npm Downloads/month | 20,414 | 2026-03-03 |
| Created | 2025-07-04 | 2026-03-03 |
| Last Updated | 2026-03-03 | 2026-03-03 |

---

## Key Features

### Component Catalog (100+ components)

- **27 agent directories** — domain-specialist agents (security auditor, frontend developer, database architect, code reviewer, and more)
- **22 command directories** — slash commands (`/generate-tests`, `/optimize-bundle`, `/check-security`, etc.)
- **25 skill directories** — reusable Claude Code skills with progressive disclosure
- **11 MCP directories** — external service integrations (GitHub, PostgreSQL, Stripe, AWS, OpenAI)
- **11 hook directories** — lifecycle triggers (pre-commit validation, post-completion actions, desktop notifications)
- **12 settings directories** — Claude Code configuration presets (timeouts, memory, output styles)

### Installation CLI

- Zero-config: `npx claude-code-templates@latest` launches interactive selector
- Short alias: `cct` binary available after global install
- Composable flags: mix any component types in a single invocation
- `--yes` flag for non-interactive scripted installs
- Writes directly into the project's `.claude/` directory following Claude Code conventions

### Developer Monitoring Tools

- `--analytics` — real-time dashboard streaming Claude Code session state and performance metrics
- `--chats` — mobile-optimised conversation viewer (local or via Cloudflare tunnel with `--tunnel`)
- `--health-check` — comprehensive Claude Code installation diagnostics
- `--plugins` — unified plugin dashboard showing marketplaces, installed plugins, and permissions

### Web Interface

- Browse all components at [aitmpl.com](https://aitmpl.com) — filterable by type, category, and keyword
- Beta management dashboard at [app.aitmpl.com](https://app.aitmpl.com) — track installed components and collections
- Full documentation at [docs.aitmpl.com](https://docs.aitmpl.com)

### Community Aggregation

Aggregates components from multiple attributed open-source sources:
- Anthropic official skills and Claude Code dev guides
- K-Dense-AI scientific skills (139 biology/chemistry/medicine skills)
- obra/superpowers workflow skills (14 skills)
- wshobson/agents (48 agents)
- awesome-claude-code slash commands (21 commands)
- VoltAgent/awesome-claude-code-subagents (119 agents added in v1.28.14)
- Community contributions under original licenses (MIT, Apache 2.0, CC0)

---

## Technical Architecture

### Repository Structure

```text
claude-code-templates/
├── cli-tool/
│   ├── bin/create-claude-config.js   # CLI entrypoint (cct / claude-code-templates)
│   ├── src/                          # Core CLI logic
│   ├── components/
│   │   ├── agents/                   # 27 agent template directories
│   │   ├── commands/                 # 22 command template directories
│   │   ├── skills/                   # 25 skill template directories
│   │   ├── mcps/                     # 11 MCP config directories
│   │   ├── hooks/                    # 11 hook template directories
│   │   └── settings/                 # 12 settings template directories
│   └── templates/                    # Project scaffolding templates
├── dashboard/                        # app.aitmpl.com (Astro + React + Tailwind)
├── api/                              # Vercel serverless API routes
├── docs/                             # docs.aitmpl.com source
└── .claude-plugin/                   # Claude Code plugin marketplace manifest
```

### CLI Flow

1. `npx claude-code-templates@latest` reads flags or opens interactive inquirer menu
2. Selected components are copied into the target project's `.claude/` directory
3. MCP configs are merged into `.mcp.json`; settings are written into `settings.json`
4. Agents and commands are placed under `.claude/agents/` and `.claude/commands/`

### Marketplace Integration

The repository exposes a `.claude-plugin/marketplace.json`, making it usable as a Claude Code plugin marketplace:

```bash
/plugin marketplace add davila7/claude-code-templates
/plugin install <component>@claude-code-templates
```

### Monitoring Architecture

The `--analytics` and `--chats` tools use:
- **chokidar** for filesystem event watching of Claude Code session directories
- **WebSocket (ws)** for real-time streaming to the browser dashboard
- **Cloudflare Tunnel** (via `cloudflared`) for secure remote access without port forwarding

---

## Installation & Usage

```bash
# Interactive installation (recommended)
npx claude-code-templates@latest

# Install a full development stack in one command
npx claude-code-templates@latest \
  --agent development-team/frontend-developer \
  --command testing/generate-tests \
  --mcp development/github-integration \
  --yes

# Install individual components
npx claude-code-templates@latest --agent development-tools/code-reviewer --yes
npx claude-code-templates@latest --command performance/optimize-bundle --yes
npx claude-code-templates@latest --hook git/pre-commit-validation --yes
npx claude-code-templates@latest --mcp database/postgresql-integration --yes

# Developer tools
npx claude-code-templates@latest --analytics       # Real-time session monitoring
npx claude-code-templates@latest --chats           # Local conversation viewer
npx claude-code-templates@latest --chats --tunnel  # Remote viewer via Cloudflare
npx claude-code-templates@latest --health-check    # Diagnostics
npx claude-code-templates@latest --plugins         # Plugin dashboard
```

---

## Relevance to Claude Code Development

### Applications

- **Bootstrap new projects** — install a curated set of agents, commands, and hooks with a single command rather than authoring them manually
- **Discover community patterns** — the 100+ templates serve as a reference library of what the Claude Code community has found useful
- **Study component structure** — every template follows Claude Code conventions, making the repo a practical guide to correct `.claude/` directory layout
- **Complement claude_skills** — claude_skills focuses on the plugin/skill authoring workflow; claude-code-templates focuses on end-user discovery and installation

### Patterns Worth Adopting

- **Composable CLI flags per component type** — separating `--agent`, `--command`, `--skill`, `--hook`, `--mcp`, `--setting` maps cleanly to the Claude Code directory structure
- **`--yes` non-interactive flag** — enables scripted CI-style installs, good pattern for any config distribution tool
- **Cloudflare Tunnel for remote monitoring** — zero-config remote access to local dashboards without server setup
- **Aggregating community contributions with attribution** — explicit attribution table in README with license links for every source
- **Dual marketplace distribution** (npm + `.claude-plugin/marketplace.json`) — reaches users via package manager and via Claude Code's native plugin system

### Integration Opportunities

- **Cross-list in claude_skills README** — claude-code-templates is a top discovery point (21K+ stars); linking from claude_skills could drive mutual discoverability
- **Reference as source for new skill ideas** — the 100+ components reveal what Claude Code use-cases the community values most
- **Study the `.claude-plugin/marketplace.json`** — the repository's marketplace manifest is another real-world reference for the marketplace format alongside claude_skills
- **Adopt `--health-check` pattern** — a diagnostic command that verifies correct installation could benefit claude_skills CLI tooling
- **Analytics as a skill evaluation harness** — the session monitoring architecture (filesystem watch + WebSocket stream) could inform harness engineering approaches

---

## References

- [GitHub Repository](https://github.com/davila7/claude-code-templates) (accessed 2026-03-03)
- [aitmpl.com — Web Template Browser](https://aitmpl.com) (accessed 2026-03-03)
- [npm Package — claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (accessed 2026-03-03)
- [GitHub API — Repository Metadata](https://api.github.com/repos/davila7/claude-code-templates) (accessed 2026-03-03)
- [GitHub API — Latest Release](https://api.github.com/repos/davila7/claude-code-templates/releases/latest) (accessed 2026-03-03)
- [GitHub API — Contributors](https://api.github.com/repos/davila7/claude-code-templates/contributors) (accessed 2026-03-03)
- [npm Download Stats — last-month](https://api.npmjs.org/downloads/point/last-month/claude-code-templates) (accessed 2026-03-03)
- [Repository README](https://raw.githubusercontent.com/davila7/claude-code-templates/main/README.md) (accessed 2026-03-03)
- [CHANGELOG.md](https://raw.githubusercontent.com/davila7/claude-code-templates/main/CHANGELOG.md) (accessed 2026-03-03)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-03 |
| Version at Verification | v1.28.16 |
| Next Review Recommended | 2026-06-03 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [composure](../agent-frameworks/composure.md) | agent-frameworks | referenced by composure (agent-frameworks) |
| [dark-design](../ai-design-tools/dark-design.md) | ai-design-tools | referenced by dark-design (ai-design-tools) |
| [maverick](../coding-agents/maverick.md) | coding-agents | referenced by maverick (coding-agents) |
| [anything_about_game_ai_resources](../developer-tools/anything_about_game_ai_resources.md) | developer-tools | referenced by anything_about_game_ai_resources (developer-tools) |
| [TheAlgorithms-Python](../learning-resources/TheAlgorithms-Python.md) | learning-resources | referenced by TheAlgorithms-Python (learning-resources) |
