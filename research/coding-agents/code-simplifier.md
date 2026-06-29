---
title: "Anthropic Code Simplifier Plugin"
research_date: "2026-02-23"
source_url: "https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md"
github_url: "https://github.com/anthropics/claude-plugins-official"
version_at_research: "1.0.0"
license: "Apache-2.0"
last_verified: "2026-02-23"
version_at_verification: "1.0.0"
next_review: "2026-05-23"
---

## Overview

The Code Simplifier is an official Anthropic Claude Code plugin that provides an autonomous agent (powered by Claude Opus) for simplifying and refining code for clarity, consistency, and maintainability. It operates proactively after code is written or modified — without requiring explicit user requests — applying project-specific standards from `CLAUDE.md` while preserving all original functionality. The plugin is distributed through Anthropic's official Claude Code plugin directory (`claude-plugins-official`, 8.1K stars).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Code clarity degrades over time as features accumulate | Autonomous agent proactively refines recently modified code after each change |
| Inconsistent coding standards across a project | Reads and enforces project-specific CLAUDE.md standards on every modification |
| Nested ternary operators and dense one-liners reduce readability | Explicit rule: prefer switch/if-else over nested ternaries; choose clarity over brevity |
| Redundant abstractions and unnecessary complexity accumulate | Consolidates related logic, eliminates redundant code, reduces nesting |
| Code review bottlenecks for style and clarity issues | Autonomous refinement loop catches style issues before human review |
| Over-simplification removing useful abstractions | Maintains balance: avoids combining too many concerns or removing helpful structure |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Parent Repo Stars (claude-plugins-official) | 8,107 | 2026-02-23 |
| Parent Repo Forks | 791 | 2026-02-23 |
| Parent Repo Open Issues | 207 | 2026-02-23 |
| Plugin Version | 1.0.0 | 2026-02-23 |
| Agent Model | claude-opus | 2026-02-23 |
| Repository Created | 2025-11-20 | 2026-02-23 |
| Last Repository Push | 2026-02-20 | 2026-02-23 |

---

## Key Features

### Autonomous Proactive Operation

- Runs automatically after code is written or modified — no explicit invocation required
- Focuses scope on recently modified code unless instructed otherwise
- Uses Claude Opus model for high-quality simplification reasoning
- Documents only significant changes that affect understanding

### Functionality Preservation

- Never changes what code does — only how it does it
- All original features, outputs, and behaviors remain intact
- Verifies the refined code is simpler and more maintainable before applying

### Project Standards Enforcement

- Reads and applies project-specific coding standards from `CLAUDE.md`
- ES modules with proper import sorting and file extensions
- Prefers `function` keyword over arrow functions for top-level declarations
- Explicit return type annotations for top-level functions
- Proper React component patterns with explicit Props types
- Consistent naming conventions across the codebase

### Clarity Enhancement Rules

- Reduces unnecessary complexity and nesting depth
- Eliminates redundant code and over-engineered abstractions
- Improves readability through clear variable and function naming
- Consolidates related logic into cohesive units
- Removes comments describing obvious code; keeps meaningful ones
- **Avoids nested ternary operators** — prefers switch or if/else chains for multiple conditions
- Chooses explicit code over overly compact solutions

### Balance Maintenance

- Avoids over-simplification that reduces maintainability
- Does not combine too many concerns into single functions or components
- Preserves helpful abstractions that improve code organization
- Does not prioritize "fewer lines" over readability (no nested ternaries, no dense one-liners)
- Ensures code remains easy to debug and extend

---

## Technical Architecture

### Plugin Structure

<eg>
plugins/code-simplifier/
├── .claude-plugin/
│   └── plugin.json      # Plugin metadata (name, version, author, description)
├── agents/
│   └── code-simplifier.md  # Agent definition with YAML frontmatter + system prompt
└── LICENSE              # Apache-2.0
</eg>

### Agent Definition Format

The agent is defined as a Markdown file with YAML frontmatter:

```yaml
---
name: code-simplifier
description: Simplifies and refines code for clarity, consistency, and maintainability
             while preserving all functionality. Focuses on recently modified code
             unless instructed otherwise.
model: opus
---
```

Followed by a detailed system prompt defining the agent's role, constraints, and
five-step refinement process.

### Five-Step Refinement Process

1. Identify recently modified code sections
2. Analyze for clarity, consistency, and elegance opportunities
3. Apply project-specific best practices from `CLAUDE.md`
4. Verify all functionality remains unchanged
5. Confirm the refined code is simpler and more maintainable

### Plugin Manifest (`plugin.json`)

```json
{
  "name": "code-simplifier",
  "version": "1.0.0",
  "description": "Agent that simplifies and refines code for clarity, consistency,
                  and maintainability while preserving functionality",
  "author": {
    "name": "Anthropic",
    "email": "support@anthropic.com"
  }
}
```

---

## Installation & Usage

```bash
# Install from the official Anthropic plugin directory
/plugin install code-simplifier@claude-plugin-directory

# Or browse in Claude Code plugin discovery
/plugin  # then select Discover
```

Once installed, the agent activates automatically when code is modified in a session —
no explicit invocation is required. To scope beyond recently modified code:

```
@code-simplifier Please review all files in src/components/
```

---

## Relevance to Claude Code Development

### Applications

- **Post-edit cleanup automation** — Eliminates the need for manual clarity passes after implementing features; the agent handles style refinement autonomously
- **Standards enforcement** — Demonstrates how a Claude Code agent can read and enforce CLAUDE.md standards without user prompting
- **Proactive agent pattern** — Shows how to build agents that activate after tool use rather than on explicit user request

### Patterns Worth Adopting

- **Scope-limited autonomous operation** — Agent defaults to recently modified code but can be expanded; prevents runaway refactoring of unrelated code
- **Functionality preservation as primary constraint** — Explicit rule hierarchy: preserve behavior first, simplify second
- **CLAUDE.md as agent config source** — Agent reads project's own CLAUDE.md for standards rather than hardcoding rules, making it universally applicable
- **Balance rules over absolute minimization** — Anti-patterns list (nested ternaries, dense one-liners) is explicit rather than implicit, reducing ambiguity
- **No-README plugin** — Minimal plugin structure: just `plugin.json` + agent definition; demonstrates simplest viable Claude Code plugin

### Integration Opportunities

- **Complement with code review hooks** — Pair with a PostToolUse hook to trigger the code-simplifier agent after file writes for fully automated cleanup pipeline
- **Reference for claude_skills plugin authoring** — The code-simplifier's agent definition is a clean reference implementation for writing autonomous Claude Code agents
- **Adopt CLAUDE.md-driven standards reading** — Skills in this repo could similarly read project CLAUDE.md rather than hardcoding project-specific rules
- **Official plugin directory as distribution channel** — The `claude-plugins-official` repository (8.1K stars) is the canonical marketplace for Anthropic-vetted plugins; relevant for distributing claude_skills plugins

### Competitive Analysis

- Compared to `claude-skillz` automatic-code-review plugin: code-simplifier focuses on clarity/simplicity, not semantic rule violations
- Compared to full coding agents (OpenHands, Cline): single-purpose, session-scoped, not a standalone agent platform
- Compared to linters (ruff, ESLint): operates at semantic/structural level, not syntactic; understands intent from CLAUDE.md

---

## References

- [Agent Definition (code-simplifier.md)](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md) (accessed 2026-02-23)
- [Plugin Manifest (plugin.json)](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/code-simplifier/.claude-plugin/plugin.json) (accessed 2026-02-23)
- [GitHub Repository: anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) (accessed 2026-02-23)
- [GitHub API: Repository Metadata](https://api.github.com/repos/anthropics/claude-plugins-official) (accessed 2026-02-23)
- [Official Claude Code Plugin Documentation](https://code.claude.com/docs/en/plugins) (accessed 2026-02-23)

---
