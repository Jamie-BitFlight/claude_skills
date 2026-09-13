---
name: Vercel Labs Skills
description: Vercel Labs Skills is an open-source CLI tool (`npx skills`) that enables developers to install, manage, and distribute reusable instruction sets (skills) across 40+ AI coding agents. It standardizes...
license: MIT
metadata:
  topic: vercel-labs-skills
  category: skill-generation-tools
  source_url: https://github.com/vercel-labs/skills
  github: vercel-labs/skills
  version: "v1.4.0"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

Vercel Labs Skills is an open-source CLI tool (`npx skills`) that enables developers to install, manage, and distribute reusable instruction sets (skills) across 40+ AI coding agents. It standardizes skill discovery, installation, and updates through a unified interface that works with Claude Code, Cursor, Cline, OpenCode, and dozens of other agent platforms, addressing the fragmentation in the agent skills ecosystem.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Fragmented skill installation across 40+ AI agents with different conventions | Unified CLI that auto-detects agents and installs skills to correct paths for each platform |
| No standardized way to discover and share agent skills | Centralized directory at skills.sh and support for GitHub-based skill repositories |
| Manual updates and version tracking across multiple agents | Automated update checking (`skills check`) and bulk updates (`skills update`) |
| Skills duplicated across projects and agents waste storage | Symlink installation mode creates canonical copy with references, reducing duplication |
| Incompatible skill formats between agent platforms | Adheres to Agent Skills specification (agentskills.io) for cross-platform compatibility |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 6,324 | 2026-02-20 |
| Forks | 533 | 2026-02-20 |
| Contributors | 70 | 2026-02-20 |
| Latest Release | v1.4.0 | 2026-02-17 |
| Supported Agents | 40+ | 2026-02-20 |

---

## Key Features

### Universal Agent Support

- Supports 40+ AI coding agents including Claude Code, Cursor, Cline, OpenCode, Windsurf, Goose, Codex, GitHub Copilot, Antigravity, and more
- Auto-detects installed agents on system and prompts for selection if none detected
- Maps correct installation paths for both project-scoped (`./{agent}/skills/`) and global (`~/{agent}/skills/`) installations
- Handles agent-specific quirks (e.g., Kiro CLI requires manual resource configuration after installation)

### Flexible Source Resolution

- GitHub shorthand: `npx skills add vercel-labs/agent-skills`
- Full URLs: `npx skills add https://github.com/vercel-labs/agent-skills`
- Direct skill paths: `npx skills add https://github.com/owner/repo/tree/main/skills/my-skill`
- GitLab and other git URLs
- Local filesystem paths: `npx skills add ./my-local-skills`
- Claude Code plugin manifest discovery (`.claude-plugin/marketplace.json`)

### Intelligent Skill Discovery

- Searches 30+ standard skill directory locations within repositories
- Recursive fallback search if no skills found in standard paths
- Supports Claude Code plugin marketplace manifest format for ecosystem compatibility
- Lists available skills without installation: `npx skills add repo --list`

### Installation Modes

- **Symlink mode** (recommended): Creates symlinks from each agent to canonical copy, enabling single-source updates
- **Copy mode**: Creates independent copies per agent for environments where symlinks unsupported
- **Scope control**: Project-scoped (default, committed with repo) or global (`-g` flag, user-wide availability)

### Batch Operations

- Install specific skills: `--skill frontend-design --skill skill-creator`
- Install all skills: `--skill '*'`
- Target specific agents: `--agent claude-code --agent cursor`
- Target all agents: `--agent '*'`
- Non-interactive mode for CI/CD: `--yes` flag
- Combined `--all` flag: installs all skills to all agents without prompts

### Update Management

- Check for updates: `npx skills check`
- Update all installed skills: `npx skills update`
- Tracks installation source to enable version comparison

### Skill Template Generation

- `npx skills init` creates SKILL.md template with required frontmatter
- `npx skills init my-skill` creates skill in subdirectory
- Supports `metadata.internal: true` for work-in-progress skills hidden from discovery unless `INSTALL_INTERNAL_SKILLS=1` set

### List and Search

- `npx skills list` (alias: `ls`) shows installed skills across project and global scopes
- `--global` flag filters to global-only
- `--agent` flag filters by specific agents
- `npx skills find` provides interactive skill search
- `npx skills find typescript` searches by keyword

### Removal Operations

- Interactive removal: `npx skills remove` (alias: `rm`)
- Remove by name: `npx skills remove web-design-guidelines`
- Scope control: `--global` for global-only removal
- Agent targeting: `--agent claude-code cursor`
- Batch removal: `--skill '*' --agent '*'` or `--all` shorthand

---

## Technical Architecture

### CLI Structure

- **Language**: TypeScript compiled to JavaScript (Node.js >=18)
- **Entry point**: `./bin/cli.mjs` (executable wrapper)
- **Source**: `src/cli.ts` with command routing
- **Package manager**: pnpm 10.17.1
- **Build system**: obuild for optimized bundling

### Core Components

| File | Purpose |
|------|---------|
| `src/add.ts` | Installation logic, source resolution, symlink/copy operations (71KB) |
| `src/agents.ts` | Agent platform definitions, path mappings, capability matrix |
| `src/cli.ts` | Command routing, argument parsing, help text |
| `src/constants.ts` | Shared constants, skill discovery paths |

### Skill Discovery Algorithm

1. Check for `.claude-plugin/marketplace.json` or `plugin.json` and extract declared skills
2. Search standard skill directory locations (30+ paths)
3. If no skills found, perform recursive search from repository root
4. Parse `SKILL.md` YAML frontmatter for `name` and `description` (required fields)
5. Filter internal skills unless `INSTALL_INTERNAL_SKILLS=1`

### Installation Workflow

<eg>
Source URL → Clone/Download → Discover Skills → Prompt Selection
→ Detect Agents → Choose Mode (symlink/copy) → Install to Paths
→ Track Installation Metadata
</eg>

### Agent Capability Detection

Tool tracks agent-specific feature support:

- `allowed-tools` frontmatter: Yes for most agents, No for Kiro CLI and Zencoder
- `context: fork` frontmatter: Yes only for Claude Code
- Hooks: Yes for Claude Code and Cline only

### Telemetry

- Anonymous usage data collection (opt-out via `DISABLE_TELEMETRY` or `DO_NOT_TRACK`)
- Automatically disabled in CI environments

---

## Installation & Usage

### Basic Installation

```bash
# Install skills from repository
npx skills add vercel-labs/agent-skills

# List available skills without installing
npx skills add vercel-labs/agent-skills --list

# Install specific skills
npx skills add vercel-labs/agent-skills --skill frontend-design

# Install to specific agents
npx skills add vercel-labs/agent-skills -a claude-code -a cursor

# Non-interactive installation (CI/CD)
npx skills add vercel-labs/agent-skills --skill frontend-design -g -a claude-code -y
```

### Management Commands

```bash
# List installed skills
npx skills list

# Check for updates
npx skills check

# Update all skills
npx skills update

# Remove skills
npx skills remove web-design-guidelines

# Search for skills
npx skills find typescript
```

### Creating Skills

```bash
# Create SKILL.md template
npx skills init

# Create skill in subdirectory
npx skills init my-skill
```

**SKILL.md structure**:

```markdown
---
name: my-skill
description: What this skill does and when to use it
metadata:
  internal: false  # Optional: hide from discovery unless INSTALL_INTERNAL_SKILLS=1
---

# My Skill

Instructions for the agent to follow when this skill is activated.

## When to Use

Describe the scenarios where this skill should be used.

## Steps

1. First, do this
2. Then, do that
```

---

## Relevance to Claude Code Development

### Applications

- **Unified skill distribution**: Enables claude_skills repository to publish skills consumable by Claude Code users via `npx skills add Jamie-BitFlight/claude_skills`
- **Cross-agent compatibility testing**: Validates skill portability across agent platforms to ensure broader ecosystem adoption
- **Installation automation**: Integrates into setup scripts for reproducible Claude Code environments
- **Version management**: Tracks skill versions and enables automated update workflows

### Patterns Worth Adopting

- **Multi-path discovery**: Search standard locations first, then recursive fallback—balances performance with flexibility
- **Symlink-first installation**: Reduces duplication while maintaining compatibility with copy mode for restrictive environments
- **Scope separation**: Project vs. global installation mirrors npm/pip patterns developers expect
- **Non-interactive mode**: `--yes` flag enables CI/CD integration without hanging on prompts
- **Internal skill filtering**: `metadata.internal` allows work-in-progress skills in repo without exposing to users
- **Agent capability matrix**: Explicitly documents which features work on which agents to set correct user expectations

### Integration Opportunities

- **Claude Code plugin marketplace compatibility**: Skills CLI already supports `.claude-plugin/marketplace.json` format used by this repository
- **Automated skill publishing**: GitHub Actions workflow could use `npx skills add` to test skill installation during CI
- **Skill validation**: Extract and reuse skill discovery/parsing logic to validate SKILL.md frontmatter in pre-commit hooks
- **Documentation generation**: Use agent capability matrix pattern to document which Claude Code features work with which skills
- **Installation testing**: Add integration tests that use Skills CLI to verify skill installation paths and discovery
- **Migration tool**: Create workflow to convert existing claude_skills to Skills CLI-compatible format for broader distribution

---

## References

- [GitHub Repository](https://github.com/vercel-labs/skills) (accessed 2026-02-20)
- [Skills Directory](https://skills.sh) (accessed 2026-02-20)
- [Agent Skills Specification](https://agentskills.io) (accessed 2026-02-20)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills) (accessed 2026-02-20)
- [Vercel Agent Skills Repository](https://github.com/vercel-labs/agent-skills) (accessed 2026-02-20)
- [npm Package](https://www.npmjs.com/package/skills) (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [composio-codebase-migrate](./composio-codebase-migrate.md) | skill-generation-tools | referenced by composio-codebase-migrate (skill-generation-tools) |
