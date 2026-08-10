---
title: "Compound Engineering Plugin — AI Agent Workflow Orchestration"
category: "skill-generation-tools"
source_url: "https://github.com/EveryInc/compound-engineering-plugin"
github_repository: "https://github.com/EveryInc/compound-engineering-plugin"
version_at_research: "3.21.4"
license: "MIT"
last_verified: "2026-08-11"
next_review: "2026-11-11"
---

## Overview

Compound Engineering Plugin is a Claude Code plugin that structurally inverts the engineering workflow to emphasize that "each unit of engineering work should make subsequent units easier, not harder." The plugin currently ships **32 skills** with no standalone plugin agents — instead spawning specialist subagents on-demand for research, review, planning, and implementation. It implements an 80/20 planning-to-execution ratio orchestrated through a /ce- command namespace. The plugin supports 14 platforms: Claude Code, Cursor, Codex App, Codex CLI, Kimi Code CLI, Cline, Grok Build CLI, Devin CLI, GitHub Copilot, Factory Droid, Qwen Code, OpenCode, Pi, and Antigravity CLI.

**Source**: GitHub repository README.md and .claude-plugin/plugin.json (accessed 2026-08-11)

**Current Status**: Active production plugin (version 3.21.4); TypeScript-based.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Engineering work accumulates complexity (each feature makes subsequent ones harder) | Structured workflow that captures learnings and simplifies future work through knowledge compounding |
| Developers spend most time in unstructured problem-solving | 80% planning & review phases guide decisions, 20% execution follows clear specification |
| Code review happens after implementation (wastes refactoring effort) | Code review workflows (/ce-code-review) with structured feedback before merge |
| Requirements discovery is informal and incomplete | /ce-brainstorm for interactive requirements, /ce-plan for structured implementation planning before writing code |
| Knowledge from completed work doesn't transfer to next project | /ce-compound skill captures learnings, team knowledge, patterns for reuse in future cycles |

**Source**: Compound Engineering Plugin README.md "Brainstorm, plan, debug, review, and compound learnings with AI agents" section (accessed 2026-08-11)

---

## Key Features

### Core Workflow Commands

- **/ce-ideate** — Idea generation and ranking with structured scoring
- **/ce-brainstorm** — Interactive requirements exploration to understand problems deeply
- **/ce-plan** — Structured implementation planning before writing code
- **/ce-work** — Plan execution with specialist subagent support
- **/ce-code-review** — Code review workflow
- **/ce-compound** — Capture learnings and knowledge for future work cycles
- **/ce-debug** — Bug-focused investigation workflows
- **/ce-simplify-code** — Post-implementation code refinement
- **/lfg** — Fully autonomous end-to-end execution (plan through merge)

**Source**: GitHub README.md skills section (accessed 2026-08-11)

### Governance Model

The plugin emphasizes the principle: **"Each unit of engineering work should make subsequent units easier — not harder."** Effort allocation is **80% planning/review and 20% execution** to maximize leverage.

**Source**: GitHub README.md philosophy section (accessed 2026-08-11)

---

## Technical Architecture

### Plugin Structure

- **Skills-only layout**: 32 total skills; zero standalone plugin agents
- **Specialist subagent pattern**: Core workflows spawn specialist subagents on-demand for research, review, planning, and implementation
- **Portability across harnesses**: Designed for deployment on Claude Code, Cursor, Codex CLI, Kimi Code CLI, Cline, Grok Build CLI, Devin CLI, GitHub Copilot, Factory Droid, Qwen Code, OpenCode, Pi, and Antigravity CLI

**Source**: GitHub README.md "Plugin Architecture" and "Supported Platforms" sections (accessed 2026-08-11)

### Command Namespace & Routing

All user-facing commands follow the `/ce-{operation}` pattern, mapping to:
1. Specific skill for workflow guidance
2. Specialist subagents for execution (research, review, implementation)

**Source**: GitHub README.md command reference (accessed 2026-08-11)

---

## Installation & Usage

### Claude Code (Recommended)

```bash
/plugin marketplace add EveryInc/compound-engineering-plugin
/plugin install compound-engineering
```

Then activate workflows via slash commands:

```bash
/ce-ideate feature-name              # Generate and rank ideas
/ce-brainstorm feature-name          # Explore requirements
/ce-plan feature-name                # Create implementation spec
/ce-work feature-name                # Execute with AI guidance
/ce-code-review                      # Run code review
/ce-compound                         # Capture learnings
```

**Source**: GitHub README.md Installation section (accessed 2026-08-11)

### Other Platforms

Each platform has dedicated installation documentation in the README:

- **Cursor** — Install via Cursor's native plugin marketplace
- **Codex, GitHub Copilot, and other platforms** — Follow platform-specific setup instructions documented in the README

**Source**: GitHub README.md (accessed 2026-08-11)

### Quick Workflow Example

```bash
# 1. Brainstorm requirements
/ce-brainstorm auth-system

# 2. Create implementation plan
/ce-plan auth-system

# 3. Execute (developer writes code, agent provides guidance)
/ce-work auth-system

# 4. Review before merge
/ce-code-review

# 5. Capture for next iteration
/ce-compound auth-system
```

**Source**: GitHub README.md Quick Start (accessed 2026-08-11)

---

## Relevance to Claude Code Development

### Direct Applications

1. **Structured Workflow Automation**: The 80/20 planning-execution ratio and /ce- command namespace provide reference patterns for skill-based workflow design in claude_skills.

2. **Code Review Patterns**: The /ce-code-review workflow demonstrates structured code review guidance applicable to the claude_skills codebase.

3. **Knowledge Compounding**: The /ce-compound skill captures team learnings for reuse — applicable to the research curator and skill authoring workflows in this repository.

### Patterns Worth Adopting

- **80/20 Planning-First Approach**: Shift focus to requirements and planning before implementation—applicable to skill development.
- **Specialist Subagent Coordination**: Spawning domain-specific subagents on-demand shows patterns for multi-agent workflows.

### Integration Opportunities

- Reference the Compound Engineering workflow philosophy in skills designed for structured engineering work.
- Extend code review skills with the /ce-code-review pattern if building comprehensive review tooling.

---

## References

- [Compound Engineering Plugin GitHub Repository](https://github.com/EveryInc/compound-engineering-plugin) (accessed 2026-08-11)
- [GitHub README](https://github.com/EveryInc/compound-engineering-plugin/blob/main/README.md) (accessed 2026-08-11)
- [plugin.json — Plugin Manifest](https://github.com/EveryInc/compound-engineering-plugin/blob/main/.claude-plugin/plugin.json) (version 3.21.4, accessed 2026-08-11)

---
