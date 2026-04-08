# Arxitect

## Overview

Arxitect is an agentic coding plugin that enforces best-practice software design and architecture. Created by Andoni Michael Garcia, it is designed to address a fundamental limitation in modern coding agents: while they excel at implementing given tasks, their implementations often violate established software design principles and lack maintainability, extensibility, and adherence to quality standards.

The plugin adds implementation agents and specialized architecture reviewers to AI coding environments (Claude Code, Cursor, Codex, Gemini CLI), enabling agents to write better code through design-enforced feedback loops.

**Source:** README.md (accessed 2026-04-08); CLAUDE.md

## Problem Addressed

Coding agents "often burn context, waste tokens, implement partial solutions, or miss major components of coding tasks because they naturally implement repetitive, brittle, and tactical code." Most notably, agent implementations "doesn't adhere to the decades of software design best-practices that the community has established and is often myopic to broader software quality attributes including maintainability and extensibility."

Arxitect recognizes that "Software design principles weren't established specifically to help humans. They were designed to make code easier to read, understand, refactor, modify, extend, test, and maintain." This reasoning applies equally to agent-written code: reducing context needed to understand changes, improving testing efficacy, and enabling agents to implement feature requests more effectively.

**Source:** README.md, lines 9, 20-22 (accessed 2026-04-08)

## Key Statistics

| Metric | Value |
|--------|-------|
| Current version | 1.1.1 |
| GitHub stars | 32 (as of 2026-04-08) |
| Forks | 7 |
| Created | 2026-03-23 |
| Last updated | 2026-04-07 |
| License | MIT |
| Repository | <https://github.com/andonimichael/arxitect> |

**Source:** package.json; GitHub API repos/andonimichael/arxitect (accessed 2026-04-08)

## Key Features

### Three Specialized Architecture Reviewers

Arxitect dispatches three independent reviewers that examine code from different design perspectives:

**API Design Reviewer** — Assesses naming conventions, method signatures, parameter design, type safety, and REST endpoint design. Evaluates whether public interfaces are self-documenting and follow established conventions.

**Object Oriented Design Reviewer** — Checks compliance with SOLID principles, identifies DRY violations, evaluates composition vs. inheritance choices, and assesses applicability of Gang of Four design patterns.

**Clean Architecture Reviewer** — Evaluates component cohesion (REP, CRP, CCP), component coupling (ADP, SDP, SAP), and quality attributes including maintainability, extensibility, and testability.

**Source:** README.md, lines 28-30; skills/api-design-review/SKILL.md, lines 22-29; skills/oo-design-review/SKILL.md, lines 17-34; skills/clean-architecture-review/SKILL.md, lines 21-31 (accessed 2026-04-08)

### Architect Agent — Implementation with Feedback Loop

The `@architect` agent orchestrates an iterative implement-review-feedback cycle:

1. **Implement** — A code implementer writes or modifies code based on design guidelines
2. **Review** — All three design reviewers evaluate the implementation against their respective design principles
3. **Iterate** — The architect compiles feedback and instructs the implementer to revise code
4. **Safety valve** — After 3 iterations, if critical findings remain, the architect presents them to the user for decision

Each iteration preserves finding IDs to track fixes and detect regressions. Code only advances when all reviewers approve or only non-critical (warning/suggestion) findings remain.

**Source:** skills/architect/SKILL.md, lines 11-14, 99-134 (accessed 2026-04-08)

### Architecture Review Skill — Read-Only Review

The `/architecture-review` skill performs read-only code review by dispatching all three reviewers with read-only tool access. It produces a unified report with verdicts and structured findings, without modifying code.

**Source:** skills/architecture-review/SKILL.md, lines 1-93 (accessed 2026-04-08)

### Included Skills

- `/architect` — Plan and implement changes using best practices with iterative review
- `/architecture-review` — Review code without modification
- `/api-design-review` — Audit API design (naming, signatures, REST endpoints)
- `/oo-design-review` — Audit object-oriented design (SOLID, DRY, patterns)
- `/clean-architecture-review` — Audit architectural structure (cohesion, coupling, quality attributes)
- `/using-arxitect` — Bootstrap skill teaching when and how to use Arxitect

**Source:** README.md, lines 42-48 (accessed 2026-04-08)

## Technical Architecture

### Core Components

**Reviewer Agents** — Three specialized review agents (`oo-design-reviewer`, `clean-architecture-reviewer`, `api-design-reviewer`) each operate with isolated context and precise instructions. They receive read-only tool access and pre-loaded skill content enabling focused evaluation.

**Architect Orchestrator** — Coordinates the implement-review feedback loop. It maintains finding IDs across iterations, compiles feedback documents, tracks regressions, and enforces the safety valve at iteration 3.

**Code Implementer** — Spawned by the architect to write or modify code. It receives design guidelines from `skills/architect/implementer-prompt.md`, the current task description, and feedback from prior review iterations.

**Review Output Format** — A structured schema (defined in `skills/architect/review-output-format.md`) that all reviewers follow, enabling downstream orchestration to parse, deduplicate, and present findings.

**Source:** skills/architect/SKILL.md, lines 18-88; agents/architecture-review.md, lines 31-67 (accessed 2026-04-08)

### Architecture Integration Patterns

Arxitect supports three implementation strategies ordered by preference:

**Strategy A: Superpowers Integration** — If the Superpowers plugin is installed, the architect delegates to its planning and execution workflow, combining Superpowers' task decomposition with Arxitect's design enforcement.

**Strategy B: Native Agent** — Uses the Agent tool to fork a Code Implementer with full tool access, providing an implementation plan and design guidelines.

**Strategy C: Direct Implementation** — Fallback for environments without Agent tool support; the orchestrator implements changes directly.

**Source:** skills/architect/SKILL.md, lines 34-76 (accessed 2026-04-08)

### Data Flow

1. User request → Architect orchestrator
2. Architect reads design guidelines and approval criteria
3. Architect spawns Code Implementer (via available strategy)
4. Implementer writes code; returns file list and design decisions
5. Architect invokes architecture-review skill with file list
6. architecture-review skill spawns three reviewers with read-only access
7. Reviewers return structured findings with severity levels
8. Architect evaluates verdicts:
   - All APPROVED → complete
   - CHANGES_REQUESTED → compile feedback, loop to step 3 (max 3 iterations)
   - Iteration 3 complete → present critical findings to user or auto-approve warnings

**Source:** skills/architect/SKILL.md, lines 17-135; skills/architecture-review/SKILL.md, lines 14-93 (accessed 2026-04-08)

### Runtime Dependencies

"This plugin is pure Markdown and shell scripts with zero runtime dependencies." The plugin integrates with AI environments (Claude Code, Cursor, Codex, Gemini CLI) through their native skill and agent mechanisms.

**Source:** CLAUDE.md (accessed 2026-04-08)

## Installation and Usage

### Claude Code (Recommended)

Register the marketplace and install:

```bash
/plugin marketplace add andonimichael/arxitect
/plugin install arxitect@arxitect
/reload-plugins
```

Enable auto-updates in plugin settings to keep Arxitect current.

**Source:** README.md, lines 52-72 (accessed 2026-04-08)

### Cursor

Clone into local plugin directory:

```bash
git clone https://github.com/andonimichael/arxitect.git ~/.cursor/plugins/local/arxitect
```

Then reload Cursor.

**Source:** README.md, lines 74-82 (accessed 2026-04-08)

### Codex

Clone and symlink skills:

```bash
git clone https://github.com/andonimichael/arxitect.git ~/.codex/arxitect
ln -s ~/.codex/arxitect/skills ~/.agents/skills/arxitect
```

Then restart Codex.

**Source:** README.md, lines 84-98 (accessed 2026-04-08)

### Gemini CLI

```bash
gemini extensions install https://github.com/andonimichael/arxitect
```

**Source:** README.md, lines 100-103 (accessed 2026-04-08)

### Common Use Patterns

1. Run an architecture review for a specific module
2. Design and implement a new feature with design enforcement
3. Review code changes for adherence to design principles
4. Evaluate whether a specific class follows object-oriented design
5. Build new API routes with API design review

**Source:** README.md, lines 110-116 (accessed 2026-04-08)

## Limitations and Caveats

### Iteration Safety Valve

The architect enforces a 3-iteration maximum to prevent infinite feedback loops. If critical findings remain after 3 complete implement-review cycles, the architect presents them to the user for manual decision rather than continuing to iterate.

**Source:** skills/architect/SKILL.md, lines 119-134 (accessed 2026-04-08)

### No Dynamic Extension Points Documented

While the plugin targets multiple platforms (Claude Code, Cursor, Codex, Gemini), formal extension or plugin APIs are not documented. Integration occurs through platform-native skill and agent registration mechanisms.

**Source:** Reviewed all SKILL.md and agent files; no explicit API documentation found (accessed 2026-04-08)

### Early Project Stage

The project is newly created (2026-03-23) with limited adoption (32 stars, 7 forks as of 2026-04-08). Long-term stability and maintainability patterns are not yet established.

**Source:** GitHub metadata (accessed 2026-04-08)

## Relevance to Claude Code Development

Arxitect directly supports Claude Code development workflows by:

1. **Enforcing design quality in agent-generated code** — The architect ensures code produced by implementation agents adheres to design principles, reducing technical debt accumulation across multiple agent tasks.

2. **Providing read-only reviews** — The `/architecture-review` skill enables code review without modification, supporting verification workflows where human review precedes acceptance.

3. **Multi-platform portability** — The plugin targets Claude Code, Cursor, Codex, and Gemini CLI, making design enforcement portable across agent environments.

4. **Composable with Superpowers** — Strategy A integration with Superpowers enables combining task decomposition (Superpowers) with architectural enforcement (Arxitect) in structured workflows.

**Source:** README.md, agents/architect.md, skills/architect/SKILL.md (accessed 2026-04-08)

## References

- GitHub repository: <https://github.com/andonimichael/arxitect> (accessed 2026-04-08)
- GitHub releases: <https://github.com/andonimichael/arxitect/releases> (accessed 2026-04-08)
- Claude Code plugin marketplace: <https://code.claude.com/docs/en/discover-plugins> (referenced in installation docs, not directly accessed)

## Freshness Tracking

| Section | Confidence | Last Verified |
|---------|-----------|----------------|
| Identity/Metadata | high | 2026-04-08 |
| Problem Addressed | high | 2026-04-08 |
| Key Features | high | 2026-04-08 |
| Technical Architecture | high | 2026-04-08 |
| Installation & Usage | high | 2026-04-08 |
| Limitations | medium | 2026-04-08 |
| Relevance to Claude Code | high | 2026-04-08 |

**Next review:** 2026-07-08 (3 months)

**Confidence rationale:**
- High confidence sections: Based on official README, SKILL.md files, agent definitions, and GitHub API — all primary sources fully read
- Medium confidence on limitations: Early-stage project with few users; long-term stability patterns cannot be assessed yet

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Superpowers](../superpowers.md) | agent-frameworks | Shared methodology: design validation and review enforcement in agent-driven workflows |
| [Everything Claude Code](../everything-claude-code.md) | agent-frameworks | 16-agent orchestration with architect agent enforcing code quality via specialized reviewers |
| [Compound Engineering Plugin](../../skill-generation-tools/compound-engineering-plugin.md) | skill-generation-tools | 35+ agents including architecture-strategist reviewer; Plan/Review/Work workflow mirrors Arxitect's implement-review-iterate cycle |
| [SoulForge](../../coding-agents/soulforge.md) | coding-agents | Multi-agent orchestration with task-specific model routing and code quality validation through post-dispatch passes |
| [Oh My OpenCode](../../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Multi-agent architecture with Oracle agent for code quality decisions; category-based routing for specialized review agents |
| [Google Agent Development Kit](../google-adk.md) | agent-frameworks | Evaluation and quality assurance framework; structured agent design principles for reliability and compliance testing |
| [Empirica](../../agent-infrastructure/empirica.md) | agent-infrastructure | Epistemic readiness gating and pre-action validation layer; measurement framework for AI agent code quality and understanding |
