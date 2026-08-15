---
title: "SkillsMP"
research_date: "2026-02-23"
source_url: "https://skillsmp.com/docs"
github_url: "https://github.com/yan-labs/skillsmp"
version_at_research: "npm `skillsmp` (JavaScript, no explicit version tag)"
license: "MIT"
last_verified: "2026-02-23"
version_at_verification: "npm `skillsmp` (no explicit version tag; platform version not published)"
next_review: "2026-05-23"
---

## Overview

SkillsMP is an open, independent marketplace hosting 66,500+ AI agent skills compatible with Claude Code, OpenAI Codex CLI, and ChatGPT. All skills use the unified SKILL.md format — a Markdown file with YAML frontmatter — ensuring cross-platform compatibility. The platform provides search, REST API access, MCP server integration, and a quality filter requiring a minimum 2-star GitHub reputation to appear in the index.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding assistants have limited built-in capabilities | Open marketplace of 66,500+ specialized skills that extend any supported AI tool |
| Skills are scattered across GitHub repositories with no central discovery | Centralized web catalog with keyword search, category browsing, and semantic AI search |
| Different AI tools use incompatible skill formats | Single SKILL.md standard (YAML frontmatter + instructions + optional scripts/templates) works across Claude Code, Codex CLI, and ChatGPT |
| No programmatic access to skill catalog | REST API (`/api/skills`) and an MCP server for agent-native discovery and install |
| Installing skills requires manual curl + mv commands | `npm install skillsmp` package plus one-command install pattern via `marketplace.json` |
| Untrusted community-submitted content | Minimum 2-star GitHub rating filter; open-source auditability requirement |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Skills indexed | 66,500+ | 2026-01-21 |
| GitHub Stars (yan-labs/skillsmp) | 5 | 2026-02-23 |
| GitHub Forks | 1 | 2026-02-23 |
| MCP server stars (anilcancakir/skillsmp-mcp-server) | 2 | 2026-02-23 |
| Primary language (npm package) | JavaScript | 2026-02-23 |
| Skill categories | 13 | 2026-02-23 |
| Compatible AI tools | 3 (Claude Code, Codex CLI, ChatGPT) | 2026-02-23 |

---

## Key Features

### Unified SKILL.md Standard

- Skills defined as Markdown files with YAML frontmatter (`name`, `description`, optional `author`, `version`)
- Optional `scripts` section for executable supporting code
- Optional `templates` section for pre-built output structures
- Model-invoked design: the AI activates skills by context, not explicit user commands
- Compatible directory paths: `~/.claude/skills/` (Claude Code personal), `.claude/skills/` (project), `~/.codex/skills/` (Codex CLI)

### Marketplace Catalog

- 13 categories: Tools, Development, Data & AI, Business, DevOps, Testing & Security, Documentation, Content & Media, Lifestyle, Research, Databases, Blockchain, and other emerging categories
- Search by keyword, filter by category, sort by popularity or recency
- Minimum 2-star GitHub rating quality gate; all skills must be open-source
- Skills Timeline tool for visualizing skill publication growth over time

### REST API

- Base: `https://skillsmp.com/docs/api`
- Key endpoint: `GET /api/skills?query=<keyword>&category=<category>`
- API key obtained from account settings; passed via `SKILLSMP_API_KEY` environment variable or `Authorization` header
- Supports keyword search and AI-powered semantic search
- Python helper scripts: `search.py`, `ai_search.py`, `install_helper.py`

### MCP Server Integration

- Community MCP server at `anilcancakir/skillsmp-mcp-server` (TypeScript, MIT)
- Integrates with Claude Code, Cursor, Roo Code, and other MCP-compatible agents
- Enables "search, discover, install" workflow natively within the AI assistant session

### Installation Patterns

- Manual: `curl -O https://skillsmp.com/skills/<name>/SKILL.md && mv SKILL.md ~/.claude/skills/<name>/`
- npm package: `npm install skillsmp`
- Bulk install: `marketplace.json` configuration for one-command multi-skill setup
- Multiple skills can run simultaneously; Claude Code intelligently selects which to activate

---

## Technical Architecture

SkillsMP is a web application (JavaScript front-end, REST API back-end) that crawls and indexes GitHub repositories containing valid SKILL.md files. The indexing pipeline applies quality filtering (≥2 GitHub stars, open-source license) before making entries searchable.

**Skill format** (SKILL.md):

```markdown
---
name: my-skill
description: What this skill does and when to use it
author: github-username
version: 1.0.0
---

# My Skill

## When to Use
Use this skill when the user requests...

## Instructions
1. First, do this...
2. Then, do that...
```

**API integration** uses REST with optional `SKILLSMP_API_KEY`:

```python
import requests

headers = {"Authorization": f"Bearer {api_key}"}
resp = requests.get(
    "https://skillsmp.com/api/skills", params={"query": "code review", "category": "development"}, headers=headers
)
skills = resp.json()
```

---

## Installation & Usage

```bash
# Install the npm package
npm install skillsmp

# Manual single skill install (Claude Code)
curl -O https://skillsmp.com/skills/skill-name/SKILL.md
mkdir -p ~/.claude/skills/skill-name/
mv SKILL.md ~/.claude/skills/skill-name/

# Or for a project-scoped install
mkdir -p .claude/skills/skill-name/
mv SKILL.md .claude/skills/skill-name/
```

**MCP server setup** (add to Claude Code or Cursor config):

```json
{
  "mcpServers": {
    "skillsmp": {
      "command": "npx",
      "args": ["-y", "skillsmp-mcp-server"],
      "env": {
        "SKILLSMP_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

**Publishing a skill** to SkillsMP:

1. Create a GitHub repository with a `SKILL.md` at the root
2. Add a `marketplace.json` for one-command installation
3. Submit the repository URL to SkillsMP for indexing
4. Repository needs ≥2 GitHub stars to appear in results

---

## Relevance to Claude Code Development

### Applications

- **Skill Discovery**: SkillsMP is the largest public registry of SKILL.md-format skills. It is the primary external source for finding skills to import into this repository's `.claude/skills/` directory or reference as inspiration for new plugins.
- **Cross-Platform Benchmarking**: Skills published here work across Claude Code, Codex CLI, and ChatGPT — examining top-rated skills reveals what patterns are considered best practice across the community.
- **Distribution Channel**: Publishing claude_skills plugins to SkillsMP would expose them to a large audience already searching for Claude Code skills.

### Patterns Worth Adopting

- **Model-Invoked Design Principle**: SkillsMP's stance that skills should activate by AI context rather than explicit commands aligns with how SKILL.md descriptions should be written (trigger-phrase-driven descriptions).
- **marketplace.json for Bulk Install**: The concept of a `marketplace.json` for multi-skill one-command installs directly parallels this repo's `.claude-plugin/marketplace.json` approach.
- **Quality Gate via Community Stars**: Requiring a minimum star count before indexing is a lightweight signal for trust that could inform curation decisions.

### Integration Opportunities

- **MCP Server**: Install the `skillsmp-mcp-server` to give Claude Code native search-and-install access to 66,500+ community skills without leaving the agent session.
- **API-Driven Skill Scouting**: Use the REST API (`/api/skills`) in a research or scout agent to periodically poll for new high-quality skills relevant to repository categories.
- **Cross-Publish claude_skills Plugins**: The `.claude-plugin/marketplace.json` format already produces SKILL.md-compatible artifacts; submitting selected plugins to SkillsMP for indexing would increase discoverability.

### Competitive Analysis

| Feature | SkillsMP | claude_skills marketplace |
|---------|----------|--------------------------|
| Skill count | 66,500+ | ~22 plugins (this repo) |
| Public registry | ✅ hosted at skillsmp.com | ❌ local `.claude-plugin/marketplace.json` only |
| REST API | ✅ full REST API | ❌ not implemented |
| MCP server | ✅ community MCP at anilcancakir/skillsmp-mcp-server | ❌ not implemented |
| Keyword search | ✅ + AI semantic search | ❌ not implemented |
| Cross-platform | ✅ Claude Code + Codex CLI + ChatGPT | ✅ Claude Code focused |
| Quality gate | ✅ 2-star GitHub minimum | ✅ manually curated |
| Open source | ✅ MIT (platform repo) | ✅ public repository |
| SKILL.md format | ✅ primary standard | ✅ supported |

---

## References

- [SkillsMP Documentation](https://skillsmp.com/docs) (accessed 2026-02-23)
- [SkillsMP API Documentation](https://skillsmp.com/docs/api) (accessed 2026-02-23)
- [SkillsMP Homepage](https://skillsmp.com/) (accessed 2026-02-23)
- [GitHub: yan-labs/skillsmp](https://github.com/yan-labs/skillsmp) (accessed 2026-02-23)
- [GitHub: anilcancakir/skillsmp-mcp-server](https://github.com/anilcancakir/skillsmp-mcp-server) (accessed 2026-02-23)
- [SkillsMP: The Open Marketplace for AI Agent Skills — VibeSparking](https://www.vibesparking.com/en/blog/ai/skillsmp/2025-12-24-skillsmp-agent-skills-marketplace/) (accessed 2026-02-23)
- [SkillsMP Complete Guide 2026 — SmartScope](https://smartscope.blog/en/blog/skillsmp-marketplace-guide/) (accessed 2026-02-23)

---
