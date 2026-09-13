---
name: SkillKit - Universal Package Manager for AI Agent Skills
description: SkillKit is an open-source CLI package manager for AI coding agent skills. It aggregates 15,000+ skills from GitHub repositories, provides a `skillkit install` command to fetch them, and...
license: Apache-2.0
metadata:
  topic: skillkit
  category: skill-generation-tools
  source_url: https://github.com/skillkit
  github: rohitg00/skillkit
  version: "1.14.0"
  verified: "2026-02-08"
  next_review: "2026-05-08"
---

## Overview

SkillKit is an open-source CLI package manager for AI coding agent skills. It aggregates 15,000+ skills from GitHub repositories, provides a `skillkit install` command to fetch them, and auto-translates skill formats between 32 AI coding agents (Claude Code, Cursor, Codex, Windsurf, GitHub Copilot, and others). It also includes session memory, AI-powered skill generation, a REST/MCP server for runtime discovery, security scanning, and team collaboration via Git-based manifests.

---

## Problem Addressed

| Problem | SkillKit Solution |
|---------|-------------------|
| Every AI coding agent uses a different skill format (SKILL.md, .mdc, etc.) | Auto-translates skills between 32 agent formats with `skillkit translate` |
| No centralized discovery for skills across agent ecosystems | Aggregates 15,000+ skills from GitHub repositories; browse/search via CLI, REST API, or MCP |
| Installing skills requires manual file placement per agent | `skillkit install <source>` fetches and places skills in correct agent directories |
| AI agents forget session learnings | `skillkit memory compress` captures and persists learnings across sessions |
| No way to share skill configurations across a team | Git-based `.skills` manifest for team-wide skill consistency |
| Skills may contain prompt injection or malicious patterns | `skillkit scan` detects prompt injection, secrets, and malicious patterns |
| Generating quality skills requires manual authoring | `skillkit generate` uses multi-provider LLM with 4 context sources for AI skill generation |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 202 | 2026-02-08 |
| GitHub Forks | 16 | 2026-02-08 |
| GitHub Watchers | 202 | 2026-02-08 |
| Open Issues | 1 | 2026-02-08 |
| Contributors | 1 (rohitg00: 170 commits) | 2026-02-08 |
| Repository Created | 2026-01-20 | - |
| Last Push | 2026-02-08 | 2026-02-08 |
| NPM Downloads (lifetime, since 2026-01-20) | 4,129 | 2026-02-08 |
| NPM Downloads (last week) | 1,308 | 2026-02-08 |
| NPM Versions Published | 33 | 2026-02-08 |
| Supported AI Agents | 32 | 2026-02-08 |
| Aggregated Skills | 15,000+ (claimed) | 2026-02-08 |
| Total GitHub Releases | 2+ (v1.13.0, v1.14.0 observed) | 2026-02-08 |

---

## Key Features

### Skill Installation and Management

- **Multi-Source Install**: Install skills from GitHub repos, GitLab, or local paths via `skillkit install <source>`
- **Removal**: `skillkit remove <skills>` to uninstall
- **Sync**: `skillkit sync` deploys installed skills to all detected agent configuration directories
- **Manifest**: Git-committable `.skills` manifest for team-wide skill consistency

### Cross-Agent Translation

- **32 Agent Formats**: Translates between SKILL.md (Claude Code), .mdc (Cursor), Markdown (Copilot/Windsurf), and 28 other formats
- **Single Command**: `skillkit translate <skill> --to <agent>` or `--all` for bulk translation
- **Supported Agents**: Claude Code, Cursor, Codex, Gemini CLI, OpenCode, GitHub Copilot, Windsurf, Amp, Cline, Goose, Roo Code, Trae, Vercel, and 19 more

### Discovery and Recommendations

- **Marketplace Browse**: `skillkit marketplace` to browse 15,000+ aggregated skills across 12 categories
- **Smart Recommendations**: `skillkit recommend` analyzes project codebase and suggests relevant skills with match scores
- **Hierarchical Taxonomy**: `skillkit tree` for categorized skill browsing
- **Quick Search**: `skillkit find <query>` for keyword search

### AI Skill Generation (v1.14.0)

- **Multi-Provider LLM**: Supports Claude (Anthropic), GPT-4 (OpenAI), Gemini (Google), Ollama (local), OpenRouter (100+ models)
- **4 Context Sources**: Documentation (via Context7 MCP), codebase patterns, marketplace skills, and session memory
- **Agent Optimization**: Generates tailored output for target agents with trust scoring (0-10) and compatibility matrix
- **Skill Composition**: Natural language search to find and compose existing skills

### Session Memory

- **Memory Compress**: `skillkit memory compress` captures session learnings for persistence
- **Memory Search**: `skillkit memory search <query>` to find stored patterns
- **Memory Export**: `skillkit memory export <name>` to extract learnings as reusable skills

### Runtime Discovery

- **REST API Server**: `skillkit serve` starts HTTP API on port 3737 with search, trending, and category endpoints
- **MCP Server**: `@skillkit/mcp` package for native agent integration via MCP protocol
- **Python Client**: `skillkit-client` pip package for programmatic access

### Security

- **Skill Scanning**: `skillkit scan <path>` detects prompt injection, secrets, and malicious patterns
- **Trust Scoring**: Generated skills receive trust scores (0-10) with grades

### Developer Experience

- **Agent Primer Generation**: `skillkit primer --all-agents` auto-generates CLAUDE.md, .cursorrules, etc. from codebase analysis
- **Interactive TUI**: `skillkit ui` provides a terminal UI for browsing, installing, and managing skills
- **CI/CD Integration**: `skillkit cicd init` generates GitHub Actions, GitLab CI, and pre-commit templates
- **Mesh Networking**: `skillkit mesh init` for encrypted P2P skill distribution across machines

---

## Technical Architecture

### Project Structure

<eg>
skillkit (monorepo)
├── packages/
│   ├── core/           # Core library (translation, recommendation, memory, AI)
│   │   └── src/
│   │       ├── ai/             # LLM providers, context sources, composition
│   │       ├── agents/         # Agent format definitions (32 agents)
│   │       ├── translate/      # Format translation engine
│   │       └── memory/         # Session memory persistence
│   ├── cli/            # CLI commands (skillkit <command>)
│   └── api/            # REST API server (@skillkit/api)
├── website/            # agenstskills.com (React SPA)
└── docs/               # Documentation
</eg>

### Skill Translation Pipeline

<eg>
Input Skill (any format)
       │
       ├── Parse source format (SKILL.md, .mdc, Markdown, etc.)
       │
       ├── Extract structured content (frontmatter, sections, rules)
       │
       ├── Apply agent-specific transformations
       │   ├── Directory placement (.claude/skills/, .cursor/skills/, etc.)
       │   ├── Format conversion (YAML frontmatter, MDC directives, etc.)
       │   └── Agent-specific optimizations
       │
       └── Output to target agent format(s)
</eg>

### Runtime Discovery Architecture

<eg>
┌─────────────────────────────────────────────────┐
│              skillkit serve (:3737)               │
│                                                   │
│  ┌───────────┐  ┌───────────┐  ┌─────────────┐  │
│  │ REST API  │  │ MCP Server│  │ Python      │  │
│  │ /search   │  │ @skillkit │  │ Client      │  │
│  │ /trending │  │ /mcp      │  │ skillkit-   │  │
│  │ /categories│ │           │  │ client      │  │
│  └─────┬─────┘  └─────┬─────┘  └──────┬──────┘  │
│        └──────────────┬┼───────────────┘          │
│                       v                           │
│  ┌────────────────────────────────────────────┐   │
│  │        Skill Index (15,000+ skills)        │   │
│  │   Aggregated from GitHub repositories      │   │
│  └────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
</eg>

### Key Dependencies

| Dependency | Purpose |
|------------|---------|
| TypeScript | Primary implementation language |
| Node.js | Runtime environment |
| React | Website SPA framework |
| @google/genai | Gemini AI provider integration |

---

## Installation and Usage

### Installation

```bash
npm install -g skillkit       # npm
pnpm add -g skillkit          # pnpm
yarn global add skillkit      # yarn
bun add -g skillkit           # bun
npx skillkit@latest <command> # no install
```

### Quick Start

```bash
npx skillkit@latest init         # Detect agents, create directories
skillkit recommend               # Get smart suggestions based on project
skillkit install anthropics/skills  # Install from marketplace
skillkit sync                    # Deploy to all detected agents
```

### Skill Translation

```bash
skillkit translate my-skill --to cursor    # Single agent
skillkit translate --all --to windsurf     # Bulk translation
```

### Runtime Discovery

```bash
# REST API
skillkit serve
curl "http://localhost:3737/search?q=react+performance"

# MCP Server (in Claude Desktop/Code config)
{
  "mcpServers": {
    "skillkit": { "command": "npx", "args": ["@skillkit/mcp"] }
  }
}
```

### AI Skill Generation

```bash
skillkit generate                              # Interactive wizard
skillkit generate --provider openai --model gpt-4o  # Specific provider
skillkit generate --agents claude-code,cursor  # Target agents
```

### Team Collaboration

```bash
skillkit manifest init                    # Create .skills manifest
skillkit manifest add anthropics/skills   # Add skills to manifest
git commit -m "add team skills"           # Commit manifest
# Teammates run:
skillkit manifest install                 # Install from manifest
```

---

## Relevance to Claude Code Development

### Applications

1. **Skill Distribution Channel**: SkillKit aggregates and indexes skills from multiple GitHub repositories. Skills authored for Claude Code in this repository could be distributed via SkillKit to reach users of 32 AI coding agents.

2. **Cross-Agent Portability Reference**: The translation engine demonstrates how to map Claude Code's SKILL.md format to other agent formats (.mdc for Cursor, etc.). This mapping logic is a reference for understanding structural differences between agent skill systems.

3. **Marketplace Aggregation Pattern**: SkillKit's approach of indexing GitHub repositories and presenting them through a unified search/install interface is an emerging pattern for AI skill ecosystems.

4. **Session Memory Pattern**: The `skillkit memory` subsystem for persisting learnings across sessions addresses the same problem space as Local Memory MCP, using a different approach (file-based, integrated into the skill workflow).

### Patterns Worth Adopting

1. **Git-Based Manifest**: The `.skills` manifest pattern for team skill consistency is applicable to this repository's plugin/marketplace system.

2. **Agent Format Mapping Table**: SkillKit maintains a structured mapping of 32 agents with their format, directory, and configuration conventions. This is a useful reference dataset.

3. **Smart Recommendations**: Project analysis to suggest relevant skills based on detected tech stack is a pattern that could enhance skill discovery in Claude Code.

4. **Security Scanning**: Prompt injection and malicious pattern detection in skills is a relevant concern for any skill marketplace.

### Integration Opportunities

1. **Skill Publishing**: Skills from this repository could be submitted to SkillKit's marketplace via their [add-source template](https://github.com/rohitg00/skillkit/issues/new?template=add-source.md).

2. **Format Translation Testing**: Use SkillKit's translation engine to verify that skills authored in SKILL.md format translate correctly to other agent formats.

3. **MCP Server Integration**: The `@skillkit/mcp` server could be used alongside Claude Code to provide runtime skill discovery from the 15,000+ aggregated skills.

### Considerations

1. **Single Maintainer**: The repository has only one contributor (rohitg00) with 170 commits. All development appears to be from a single individual.

2. **Rapid Version Churn**: 33 NPM versions published in approximately 19 days (2026-01-20 to 2026-02-08), averaging nearly 2 versions per day. This pace suggests the project is in active early development and the API may not be stable.

3. **Skills Aggregation Claims**: The "15,000+ skills" claim appears to be derived from aggregating existing GitHub repositories (Anthropic, Vercel Labs, Expo, Supabase, community repos). SkillKit does not host original skills; it indexes and redistributes skills from other sources.

4. **Website Domain**: The domain `agenstskills.com` contains a typo ("agenst" instead of "agents"), which may affect discoverability and professionalism perception.

5. **Unverified Feature Claims**: Several features listed (mesh networking, inter-agent messaging, workflow runner) could not be independently verified beyond the README and website claims. The actual implementation depth of these features is unclear.

6. **Apache-2.0 License**: Permissive license with no copyleft requirements. Suitable for integration and modification.

---

## References

1. **SkillKit Website** - <https://agenstskills.com> (accessed 2026-02-08)
2. **SkillKit GitHub Repository** - <https://github.com/rohitg00/skillkit> (accessed 2026-02-08)
3. **SkillKit README** - <https://raw.githubusercontent.com/rohitg00/skillkit/main/README.md> (accessed 2026-02-08)
4. **GitHub API - Repository Metadata** - <https://api.github.com/repos/rohitg00/skillkit> (accessed 2026-02-08)
5. **GitHub API - Contributors** - <https://api.github.com/repos/rohitg00/skillkit/contributors> (accessed 2026-02-08)
6. **GitHub API - Languages** - <https://api.github.com/repos/rohitg00/skillkit/languages> (accessed 2026-02-08)
7. **GitHub Release v1.14.0** - <https://github.com/rohitg00/skillkit/releases/tag/v1.14.0> (accessed 2026-02-08)
8. **NPM Package Registry** - <https://registry.npmjs.org/skillkit> (accessed 2026-02-08)
9. **NPM Download Statistics** - <https://api.npmjs.org/downloads/> endpoints (accessed 2026-02-08)
10. **Website HTML Source / JS Bundle** - <https://agenstskills.com/assets/index-BDs2-uIT.js> (accessed 2026-02-08, for feature strings and collection names)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [mcpskills-cli](../mcp-ecosystem/mcpskills-cli.md) | mcp-ecosystem | referenced by mcpskills-cli (mcp-ecosystem) |
| [claude-scientific-skills](./claude-scientific-skills.md) | skill-generation-tools | referenced by claude-scientific-skills (skill-generation-tools) |
| [graphify](./graphify.md) | skill-generation-tools | referenced by graphify (skill-generation-tools) |
| [mattpocock-skills](./mattpocock-skills.md) | skill-generation-tools | referenced by mattpocock-skills (skill-generation-tools) |
