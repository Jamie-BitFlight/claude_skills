---
name: Compound Engineering Plugin - AI-Powered Development Workflow
description: The Compound Engineering Plugin is a Claude Code plugin marketplace featuring a comprehensive collection of AI agents, commands, and skills designed to make each unit of engineering work easier than...
license: MIT
metadata:
  topic: compound-engineering-plugin
  category: research-agent-patterns
  source_url: https://github.com/EveryInc/compound-engineering-plugin
  version: "v2.28.0"
  verified: "2026-01-31"
  next_review: "2026-04-30"
---

## Overview

The Compound Engineering Plugin is a Claude Code plugin marketplace featuring a comprehensive collection of AI agents, commands, and skills designed to make each unit of engineering work easier than the last. Developed by Every Inc., it implements a "compounding engineering" philosophy where planning and review comprise 80% of the workflow, with execution at 20%.

**Core Value Proposition**: Invert the traditional development cycle where features accumulate technical debt. Instead, each development cycle documents learnings, improves patterns, and makes future work easier.

---

## Problem Addressed

| Problem                                                             | How Compound Engineering Solves It                                                      |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Development work accumulates technical debt over time               | Compounding cycle documents solutions and patterns for reuse                            |
| Code reviews catch issues too late in the development cycle         | 14 specialized review agents run in parallel before code is merged                      |
| Knowledge silos form when only one developer knows a solution       | `/workflows:compound` command captures solutions in searchable `docs/solutions/`        |
| Planning is often rushed, leading to rework                         | `/workflows:plan` includes research decision logic and Q&A refinement                   |
| Inconsistent code review quality across team members                | Multi-agent review with domain specialists (security, performance, architecture)        |
| Context loss when switching between tasks                           | Git worktree integration for parallel development without context switching             |
| External framework documentation changes faster than team knowledge | Context7 MCP server provides real-time framework documentation lookup (100+ frameworks) |

---

## Key Statistics (as of January 31, 2026)

| Metric              | Value      |
| ------------------- | ---------- |
| GitHub Stars        | 6,830      |
| Forks               | 546        |
| Open Issues         | 48         |
| Primary Language    | TypeScript |
| Agents              | 27         |
| Commands            | 20         |
| Skills              | 14         |
| MCP Servers         | 1          |
| Contributors        | 10+        |
| npm Package Version | 0.1.1      |

---

## Core Workflow

<eg>
Plan  -->  Work  -->  Review  -->  Compound  -->  Repeat
 |          |           |              |
 v          v           v              v
80%      20%         80%           Knowledge
Planning  Execution  Review        Compounding
</eg>

| Command                 | Purpose                                               |
| ----------------------- | ----------------------------------------------------- |
| `/workflows:brainstorm` | Explore requirements and approaches before planning   |
| `/workflows:plan`       | Turn feature ideas into detailed implementation plans |
| `/workflows:work`       | Execute plans with worktrees and task tracking        |
| `/workflows:review`     | Multi-agent code review before merging                |
| `/workflows:compound`   | Document learnings to make future work easier         |

---

## Key Features

### 1. Multi-Agent Review System

14 specialized review agents run in parallel:

**Review Agents:**

- `kieran-rails-reviewer` - Rails code review with strict conventions
- `kieran-python-reviewer` - Python code review with strict conventions
- `kieran-typescript-reviewer` - TypeScript code review with strict conventions
- `dhh-rails-reviewer` - Rails review from DHH's perspective
- `security-sentinel` - Security audits and vulnerability assessments
- `performance-oracle` - Performance analysis and optimization
- `architecture-strategist` - Architectural decisions and compliance
- `pattern-recognition-specialist` - Code patterns and anti-patterns
- `data-integrity-guardian` - Database migrations and data integrity
- `agent-native-reviewer` - Verify features are agent-native (action + context parity)
- `code-simplicity-reviewer` - Final pass for simplicity and minimalism
- `data-migration-expert` - Validate ID mappings match production
- `deployment-verification-agent` - Go/No-Go deployment checklists
- `julik-frontend-races-reviewer` - JavaScript/Stimulus race conditions

### 2. Research Agents

4 agents for gathering context and best practices:

- `best-practices-researcher` - Gather external best practices and examples
- `framework-docs-researcher` - Research framework documentation
- `git-history-analyzer` - Analyze git history and code evolution
- `repo-research-analyst` - Research repository structure and conventions

### 3. Design Agents

3 agents for UI/UX implementation:

- `design-implementation-reviewer` - Verify UI matches Figma designs
- `design-iterator` - Iteratively refine UI through systematic iterations
- `figma-design-sync` - Synchronize web implementations with Figma designs

### 4. Smart Planning with Research Decision Logic

The `/workflows:plan` command includes intelligent research decisions:

- **High-risk topics** (security, payments, external APIs) always trigger external research
- **Strong local context** (good patterns, CLAUDE.md guidance) skips external research
- **Uncertainty or unfamiliar territory** triggers external perspective
- Interactive Q&A refinement phase with targeted questions

### 5. Knowledge Compounding

The `/workflows:compound` command uses 7 parallel subagents:

1. **Context Analyzer** - Extracts problem type, symptoms, YAML frontmatter
2. **Solution Extractor** - Identifies root cause and working solution
3. **Related Docs Finder** - Cross-references existing documentation
4. **Prevention Strategist** - Develops prevention strategies
5. **Category Classifier** - Determines optimal `docs/solutions/` category
6. **Documentation Writer** - Assembles complete markdown file
7. **Specialized Agent Invocation** - Post-documentation expert review

### 6. Utility Commands

| Command                | Purpose                                       |
| ---------------------- | --------------------------------------------- |
| `/deepen-plan`         | Enhance plans with parallel research agents   |
| `/changelog`           | Create engaging changelogs for recent merges  |
| `/create-agent-skill`  | Create or edit Claude Code skills             |
| `/heal-skill`          | Fix skill documentation issues                |
| `/plan_review`         | Multi-agent plan review in parallel           |
| `/reproduce-bug`       | Reproduce bugs using logs and console         |
| `/resolve_parallel`    | Resolve TODO comments in parallel             |
| `/resolve_pr_parallel` | Resolve PR comments in parallel               |
| `/test-browser`        | Run browser tests on PR-affected pages        |
| `/xcode-test`          | Build and test iOS apps on simulator          |
| `/feature-video`       | Record video walkthroughs for PR descriptions |

### 7. Skills Library

14 skills for specialized tasks:

| Skill                       | Purpose                                          |
| --------------------------- | ------------------------------------------------ |
| `agent-native-architecture` | Build AI agents using prompt-native architecture |
| `andrew-kane-gem-writer`    | Write Ruby gems following Andrew Kane's patterns |
| `compound-docs`             | Capture solved problems as documentation         |
| `create-agent-skills`       | Expert guidance for creating Claude Code skills  |
| `dhh-rails-style`           | Write Ruby/Rails code in DHH's 37signals style   |
| `dspy-ruby`                 | Build type-safe LLM applications with DSPy.rb    |
| `frontend-design`           | Create production-grade frontend interfaces      |
| `every-style-editor`        | Review copy for Every's style guide compliance   |
| `file-todos`                | File-based todo tracking system                  |
| `git-worktree`              | Manage Git worktrees for parallel development    |
| `rclone`                    | Upload files to S3, Cloudflare R2, Backblaze B2  |
| `agent-browser`             | CLI-based browser automation via agent-browser   |
| `gemini-imagegen`           | Generate and edit images using Gemini API        |
| `brainstorming`             | Guided ideation before planning                  |

### 8. MCP Server Integration

**Context7** - Framework documentation lookup:

- `resolve-library-id` - Find library ID for a framework/package
- `get-library-docs` - Get documentation for a specific library
- Supports 100+ frameworks (Rails, React, Next.js, Vue, Django, Laravel, etc.)

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────────────┐
│                      Compound Engineering Plugin                      │
├─────────────────────────────────────────────────────────────────────┤
│  Marketplace Layer (.claude-plugin/marketplace.json)                 │
│  └── Plugin distribution, version management                         │
├─────────────────────────────────────────────────────────────────────┤
│  Plugin Core (plugins/compound-engineering/)                         │
│  ├── agents/        27 specialized AI agents                         │
│  ├── commands/      20 slash commands (5 workflow + 15 utility)      │
│  ├── skills/        14 skill packages with SKILL.md + scripts        │
│  └── mcp-servers/   Context7 framework docs server                   │
├─────────────────────────────────────────────────────────────────────┤
│  CLI Converter (src/)                                                │
│  ├── Bun/TypeScript CLI                                              │
│  ├── Converts plugins to OpenCode format                             │
│  └── Converts plugins to Codex format (experimental)                 │
├─────────────────────────────────────────────────────────────────────┤
│  Documentation Site (docs/)                                          │
│  └── Static HTML/CSS/JS (LaunchKit-based, no build step)             │
└─────────────────────────────────────────────────────────────────────┘
</eg>

### Multi-Platform Support

```bash
# Claude Code (native)
/plugin marketplace add https://github.com/EveryInc/compound-engineering-plugin
/plugin install compound-engineering

# OpenCode (experimental)
bunx @every-env/compound-plugin install compound-engineering --to opencode

# Codex (experimental)
bunx @every-env/compound-plugin install compound-engineering --to codex
```

---

## Installation & Usage

### Basic Installation

```bash
# Add marketplace
/plugin marketplace add https://github.com/EveryInc/compound-engineering-plugin

# Install plugin
/plugin install compound-engineering
```

### Workflow Example

```bash
# 1. Plan a feature
/workflows:plan Add user authentication with OAuth2

# 2. Execute the plan
/workflows:work

# 3. Review before merge
/workflows:review PR-123

# 4. Document learnings
/workflows:compound
```

### MCP Server Setup (if not auto-loading)

```json
{
  "mcpServers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Plugin Architecture Reference**: The plugin structure (agents/, commands/, skills/, mcp-servers/) demonstrates best practices for Claude Code plugin development
2. **Multi-Agent Orchestration**: The parallel agent execution pattern in `/workflows:review` shows effective orchestration strategies
3. **Knowledge Management**: The `docs/solutions/` pattern with YAML frontmatter provides a reusable knowledge base architecture
4. **Cross-Platform Conversion**: The CLI tool for converting plugins to OpenCode/Codex demonstrates portable skill formats

### Patterns Worth Adopting

1. **80/20 Planning-Execution Split**: Heavy investment in planning and review, minimal execution time
2. **Parallel Agent Execution**: Run 14 review agents simultaneously for comprehensive coverage
3. **Smart Research Decision Logic**: Context-aware research triggering based on risk and familiarity
4. **Compound Documentation**: Structured `docs/solutions/` with YAML frontmatter for searchability
5. **Worktree Integration**: Git worktrees for parallel development without context switching
6. **Category-Based Agent Organization**: Agents grouped by domain (Review, Research, Design, Workflow, Docs)
7. **Interactive Q&A Refinement**: Iterative clarification before plan generation

### Integration Opportunities

1. **Agent Patterns**: Review and research agent implementations could inform custom agent development
2. **Skill Templates**: The `create-agent-skills` and `skill-creator` skills provide guidance for skill authoring
3. **MCP Server Model**: Context7 integration demonstrates MCP server bundling in plugins
4. **Documentation Patterns**: The `compound-docs` skill shows structured knowledge capture
5. **Workflow Commands**: The `workflows:` namespace pattern avoids collisions with built-in commands

---

## References

1. **GitHub Repository**: <https://github.com/EveryInc/compound-engineering-plugin> (accessed 2026-01-31)
2. **npm Package**: <https://www.npmjs.com/package/@every-env/compound-plugin> (accessed 2026-01-31)
3. **Documentation Site**: <https://everyinc.github.io/compound-engineering-plugin/> (accessed 2026-01-31)
4. **Compound Engineering Philosophy**: <https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents> (accessed 2026-01-31)
5. **Story Behind Compound Engineering**: <https://every.to/source-code/my-ai-had-already-fixed-the-code-before-i-saw-it> (accessed 2026-01-31)
6. **Plugin README**: <https://github.com/EveryInc/compound-engineering-plugin/blob/main/plugins/compound-engineering/README.md> (accessed 2026-01-31)
7. **CHANGELOG**: <https://github.com/EveryInc/compound-engineering-plugin/blob/main/plugins/compound-engineering/CHANGELOG.md> (accessed 2026-01-31)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | referenced by Claude Code Harness (agent-frameworks) |
