---
title: "Compound Engineering Plugin — AI Agent Workflow Orchestration"
category: "skill-generation-tools"
source_url: "https://github.com/EveryInc/compound-engineering-plugin"
github_repository: "https://github.com/EveryInc/compound-engineering-plugin"
version_at_research: "1.8.2"
license: "MIT"
last_verified: "2026-08-10"
next_review: "2026-11-10"
---

## Overview

Compound Engineering Plugin is a Claude Code plugin that structurally inverts the engineering workflow to emphasize that "each unit of engineering work should make subsequent units easier, not harder." It implements a 80/20 planning-to-execution ratio with 50+ specialized agents and 38+ skills orchestrated through a /ce- command namespace. The plugin supports multi-platform deployment across Claude Code, Cursor, Codex, GitHub Copilot, and 7+ other AI coding tools.

**Source**: GitHub repository README and Compound Engineering philosophy statement (accessed 2026-08-10)

**Current Status**: Active production plugin with 18,451 GitHub stars and 1,393 forks as of May 30, 2026; TypeScript-based with recent growth from 26 agents (February 2026) to 50+ agents (August 2026).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Engineering work accumulates complexity (each feature makes subsequent ones harder) | Structured workflow that captures learnings and simplifies future work through knowledge compounding |
| Developers spend most time in unstructured problem-solving | 80% planning & review phases guide decisions, 20% execution follows clear specification |
| Code review happens after implementation (wastes refactoring effort) | Multi-domain code review (/ce-code-review) with specialized agents covering security, correctness, architecture before merge |
| Requirements discovery is informal and incomplete | /ce-brainstorm for interactive requirements, /ce-plan for structured implementation planning before writing code |
| Knowledge from completed work doesn't transfer to next project | /ce-compound skill captures learnings, team knowledge, patterns for reuse in future cycles |
| Distributed teams lack shared decision framework | war-room expert routing with Type 1/2 reversibility scoring for high-stakes decisions |

**Source**: Compound Engineering Plugin README and philosophy section (accessed 2026-08-10)

---

## Key Features

### Core Workflow Commands

- **/ce-ideate** — Idea generation and ranking with structured scoring
- **/ce-brainstorm** — Interactive requirements exploration to understand problems deeply
- **/ce-plan** — Structured implementation planning before writing code
- **/ce-work** — Plan execution with support for cross-model assistance (Claude, Gemini, Qwen, etc.)
- **/ce-code-review** — Multi-agent simultaneous code review (security, correctness, architecture, data integrity, performance, API design, math, Rust-specific, shell-specific, Makefile analysis)
- **/ce-compound** — Capture learnings and knowledge for future work cycles
- **/ce-debug** — Bug-focused investigation workflows
- **/ce-simplify-code** — Post-implementation code refinement
- **/lfg** — Fully autonomous end-to-end execution (plan through merge)

**Source**: GitHub README plugin commands overview (accessed 2026-08-10)

### Governance & Quality

- **TDD Enforcement**: PreToolUse hooks verify test files exist before implementation starts
- **Rigorous Reasoning**: Step-by-step logic validation at tool execution points
- **Multi-Domain Code Review**: Parallelized specialist reviewers (15+ review types) covering comprehensive correctness spectrum
- **Cross-Model Delegation**: Integrate Gemini, Qwen, and other models into workflows while maintaining Claude oversight
- **Session Persistence**: Cross-session state via Claude Code Tasks (v2.1.16+) for context continuity

**Source**: GitHub README governance section and capabilities reference (accessed 2026-08-10)

---

## Technical Architecture

### Plugin Structure

- **Root-native skills-only layout**: 32 total skills with no standalone plugin agents
- **Specialist subagent pattern**: On-demand subagents handle research, review, implementation seeded with skill-specific prompts
- **Portability across harnesses**: Design for Claude Code, Cursor, Codex, GitHub Copilot, Factory Droid, Qwen Code, OpenCode, Pi, Gemini, Ki

**Source**: Plugin architecture documentation (accessed 2026-08-10)

### Command Namespace & Routing

All user-facing commands follow the `/ce-{operation}` pattern, mapping to:
1. Specific skill for workflow guidance
2. Specialist subagents for execution (research, review, implementation)
3. Cross-session state management via Claude Code Tasks

**Source**: GitHub README commands architecture (accessed 2026-08-10)

### Data Flow: Workflow Cycle

1. **Ideate** → rank ideas by business value and complexity
2. **Brainstorm** → extract requirements interactively (WHO, WHAT, WHY, constraints, edge cases)
3. **Plan** → structured spec (data model, API endpoints, error handling, configuration)
4. **Work** → execution guided by plan with optional cross-model assistance
5. **Code Review** → 15+ specialist reviewers in parallel (security, correctness, architecture, math, etc.)
6. **Compound** → capture patterns, decisions, learnings for next cycle

**Source**: Compound Engineering workflow documentation (accessed 2026-08-10)

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
/ce-code-review                      # Run multi-domain review
/ce-compound                         # Capture learnings
```

**Source**: GitHub README Installation section (accessed 2026-08-10)

### Other Platforms

**Cursor** (via native `.mdc` rules):

```bash
./scripts/convert.sh --tool cursor
./scripts/install.sh --tool cursor --target /path/to/project
```

**Codex, GitHub Copilot, Factory Droid, Qwen, OpenCode, Pi, Antigravity** — each has platform-specific installation script documented in README.

**Source**: GitHub README platform compatibility section (accessed 2026-08-10)

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

**Source**: GitHub README Quick Start (accessed 2026-08-10)

---

## Relevance to Claude Code Development

### Direct Applications

1. **Structured Workflow Automation**: The 80/20 planning-execution ratio and /ce- command namespace provide reference patterns for skill-based workflow design in claude_skills.

2. **Multi-Domain Code Review**: The 15+ specialist review types (/ce-code-review with security, correctness, architecture, math, Rust, shell, Makefile reviews) demonstrate comprehensive review coverage applicable to the claude_skills codebase.

3. **Cross-Model Agent Orchestration**: Compound Engineering's delegation to Gemini/Qwen while retaining Claude oversight shows patterns for multi-LLM workflows relevant to agent orchestration skills.

4. **Knowledge Compounding**: The /ce-compound skill captures team learnings for reuse — applicable to the research curator and skill authoring workflows in this repository.

### Patterns Worth Adopting

- **80/20 Planning-First Approach**: Shift focus to requirements and planning before implementation—applicable to skill development.
- **Parallel Code Review by Specialty**: Multi-agent simultaneous review (security, logic, architecture) reduces review bottlenecks.
- **Reversibility Scoring for Decisions**: Type 1 (reversible) vs Type 2 (irreversible) decision framework guides escalation and deliberation depth.
- **Cross-Session State via Tasks**: Use Claude Code Tasks API (v2.1.16+) to maintain workflow state across conversations.

### Integration Opportunities

- Extend `/audit-skill-completeness` with Compound Engineering's multi-domain review taxonomy (security, correctness, architecture).
- Reference the Compound Engineering decision framework in skills designed for strategic choices (like `/attune:war-room`).

---

## References

- [Compound Engineering Plugin GitHub Repository](https://github.com/EveryInc/compound-engineering-plugin) (accessed 2026-08-10)
- [GitHub README](https://github.com/EveryInc/compound-engineering-plugin/blob/main/README.md) (accessed 2026-08-10)
- [Installation Guide](https://github.com/EveryInc/compound-engineering-plugin/blob/main/INSTALL.md) (accessed 2026-08-10)
- [GitHub API Repository Metadata](https://api.github.com/repos/EveryInc/compound-engineering-plugin) (accessed 2026-08-10; stars: 18,451, forks: 1,393 as of May 30, 2026)
