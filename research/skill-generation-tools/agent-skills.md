---
name: agent-skills
description: Production-grade engineering skills for AI coding agents — structured workflows that encode senior engineering practices and quality gates across the full SDLC (spec → plan → build → verify → review → ship).
category: skill-generation-tools
resource_url: https://github.com/addyosmani/agent-skills
source_url: https://github.com/addyosmani/agent-skills
author: Addy Osmani
version: "1.0.0"
license: MIT
date_accessed: 2026-07-07
research_date: 2026-07-07
last_verified: 2026-07-07
version_at_verification: "1.0.0"
next_review: 2026-10-07
---

# Agent Skills

## Overview

Agent Skills is a collection of 24 production-grade engineering skills for AI coding agents that encode the workflows, quality gates, and best practices used by senior engineers. The project addresses a core problem: AI agents default to the shortest path, often skipping specs, tests, security reviews, and architectural decisions. Agent Skills provides structured workflows that enforce the same discipline senior engineers bring to production code.

**Key insight**: "Production-grade engineering skills for AI coding agents" (README.md line 3). "Skills encode the workflows, quality gates, and best practices that senior engineers use when building software. These ones are packaged so AI agents follow them consistently across every phase of development." (README.md lines 5)

## Problem Addressed

AI coding agents default to rapid implementation without sufficient planning or quality assurance. Agent Skills counters this by providing explicit, structured workflows:

"AI coding agents default to the shortest path - which often means skipping specs, tests, security reviews, and the practices that make software reliable. Agent Skills gives agents structured workflows that enforce the same discipline senior engineers bring to production code." (README.md lines 341-342)

The project embeds established engineering principles from Google's engineering culture, including Hyrum's Law (API design), the Beyonce Rule (testing), change sizing norms (code review), Chesterton's Fence (simplification), trunk-based development (git), Shift Left (CI/CD), and treating code as a liability (deprecation). (README.md line 346)

## Key Statistics

- **Skill count**: 24 skills total — 23 lifecycle skills plus the `using-agent-skills` meta-skill (README.md lines 172-174)
- **Installation reach**: The open skills CLI installs into "70+ agents" including Claude Code, Cursor, Codex, Copilot, Cline, and more (README.md line 45)
- **Supported IDEs/CLIs**: Claude Code (recommended), Cursor, Antigravity CLI, Gemini CLI, Windsurf, OpenCode, GitHub Copilot, Kiro IDE (README.md lines 62-159)
- **Development lifecycle phases**: 6 phases — DEFINE, PLAN, BUILD, VERIFY, REVIEW, SHIP (README.md lines 12-18)
- **Agent personas**: 4 pre-configured specialist personas (code-reviewer, security-auditor, test-engineer, web-performance-auditor) (README.md lines 239-247)
- **Slash commands**: 8 commands mapped to the development lifecycle (README.md lines 26-35)
- **Version**: 1.0.0 (plugin.json line 3)
- **License**: MIT (LICENSE line 1)
- **Author**: Addy Osmani (LICENSE line 3)

## Key Features

### Lifecycle-Driven Slash Commands

**8 slash commands map to the development lifecycle** (README.md lines 23-24):

1. `/spec` — Define what to build (Spec before code)
2. `/plan` — Plan how to build it (Small, atomic tasks)
3. `/build` — Build incrementally (One slice at a time)
4. `/test` — Prove it works (Tests are proof)
5. `/review` — Review before merge (Improve code health)
6. `/webperf` — Audit web performance (Measure before optimize)
7. `/code-simplify` — Simplify the code (Clarity over cleverness)
8. `/ship` — Ship to production (Faster is safer)

Each command activates the right skills automatically. Skills also activate based on context: "designing an API triggers `api-and-interface-design`, building UI triggers `frontend-ui-engineering`, and so on." (README.md line 39)

### Autonomous Build Mode

**`/build auto` generates and executes plans without manual stepping between tasks**: "generates the plan and implements every task in a single approved pass — you approve the plan once, then it runs autonomously. It removes the human stepping *between* tasks, not the verification: every task is still test-driven and committed individually, and it pauses on failures or risky steps." (README.md line 37)

### 24 Structured Skills Organized by Phase

**Define phase** (3 skills):
- interview-me: One-question-at-a-time requirements interrogation
- idea-refine: Structured divergent/convergent thinking for vague concepts
- spec-driven-development: PRD covering objectives, commands, structure, code style, testing, boundaries

**Plan phase** (1 skill):
- planning-and-task-breakdown: Decompose specs into small, verifiable tasks with acceptance criteria

**Build phase** (7 skills):
- incremental-implementation: Thin vertical slices with feature flags and safe rollback
- test-driven-development: Red-Green-Refactor cycle with test pyramid (80/15/5)
- context-engineering: Feed agents the right information at the right time
- source-driven-development: Ground every framework decision in official documentation
- doubt-driven-development: Adversarial fresh-context review of non-trivial decisions
- frontend-ui-engineering: Component architecture, design systems, WCAG 2.1 AA
- api-and-interface-design: Contract-first design, Hyrum's Law, error semantics

**Verify phase** (2 skills):
- browser-testing-with-devtools: Chrome DevTools MCP for live runtime data
- debugging-and-error-recovery: Five-step triage: reproduce, localize, reduce, fix, guard

**Review phase** (4 skills):
- code-review-and-quality: Five-axis review with severity labels and change sizing
- code-simplification: Preserve exact behavior while reducing complexity
- security-and-hardening: OWASP Top 10 prevention, auth patterns, secrets management
- performance-optimization: Measure-first with Core Web Vitals targets

**Ship phase** (6 skills):
- git-workflow-and-versioning: Trunk-based development, atomic commits
- ci-cd-and-automation: Shift Left, feature flags, quality gate pipelines
- deprecation-and-migration: Code-as-liability mindset, migration patterns
- documentation-and-adrs: Architecture Decision Records, API docs
- observability-and-instrumentation: Structured logging, RED metrics, OpenTelemetry
- shipping-and-launch: Pre-launch checklists, staged rollouts, rollback procedures

**Meta** (1 skill):
- using-agent-skills: Maps incoming work to the right skill and defines shared operating rules

(README.md lines 172-233)

### Specialist Agent Personas

**4 pre-configured personas for targeted reviews** (README.md lines 239-247):
- code-reviewer: Senior Staff Engineer — five-axis code review standard
- test-engineer: QA Specialist — test strategy and coverage analysis
- security-auditor: Security Engineer — vulnerability detection and OWASP assessment
- web-performance-auditor: Performance Engineer — Core Web Vitals audit with metric-honesty rule

### Consistent Skill Anatomy

Every skill follows a standardized structure emphasizing process over prose:

"Process, not prose. Skills are workflows agents follow, not reference docs they read. Each has steps, checkpoints, and exit criteria." (README.md line 292)

Skill structure (README.md lines 270-286):
- YAML frontmatter with name and description
- Overview — what the skill does
- When to Use — triggering conditions
- Process — step-by-step workflow
- Common Rationalizations — excuses agents use to skip steps with counter-arguments
- Red Flags — signs something's wrong
- Verification — evidence requirements (tests passing, build output, runtime data)

"Anti-rationalization. Every skill includes a table of common excuses agents use to skip steps (e.g., 'I'll add tests later') with documented counter-arguments." (README.md line 293)

## Technical Architecture

### Component Structure

The project consists of:

1. **Skills directory** (./skills/): 24 SKILL.md files, one per skill, containing workflow definitions
2. **Agents directory** (./agents/): 4 specialist personas in markdown format
3. **Commands** (./.claude/commands/, ./commands/, ./.gemini/commands/): 8 slash command definitions
4. **Hooks** (./hooks/): Session lifecycle hooks
5. **References** (./references/): 5 supplementary checklists and documentation patterns
6. **Evals** (./evals/): Skill evaluation cases and testing framework
7. **Plugin manifests** (plugin.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json): Multi-ecosystem registration

(README.md line 301-336; CLAUDE.md lines 5-20)

### Design Philosophy

**Progressive disclosure**: The SKILL.md is the entry point. Supporting references load only when needed, keeping token usage minimal. (README.md line 295)

**Verification is non-negotiable**: Every skill ends with evidence requirements. "Seems right" is never sufficient. (README.md line 294)

### Lifecycle Orchestration

Skills are triggered by commands, context, or explicit user invocation. The orchestration model:

1. User invokes a command (e.g., `/build`) or describes a task
2. The `using-agent-skills` meta-skill maps incoming work to the right skill workflow
3. Appropriate skills load automatically based on phase or context
4. Skills execute step-by-step workflows with verification gates
5. Each skill's output feeds into downstream skills

This creates a full-lifecycle DAG where skills orchestrate based on development phase and context.

### Multi-Ecosystem Support

The project targets 8+ agent ecosystems with tailored integration:
- Claude Code: Native marketplace, .claude-plugin/plugin.json
- Cursor: .cursor/rules/ directory integration
- Antigravity CLI: plugin.json manifests with skill/command paths
- Gemini CLI: Native skill discovery
- Windsurf: Rules file integration
- OpenCode: MCP-style AGENTS.md integration
- GitHub Copilot: Persona definitions via .github/copilot-instructions.md
- Kiro IDE: .kiro/skills/ project/global storage

## Installation & Usage

### Quick Start (Any Agent)

**Fastest path — NPM skills CLI**:

```bash
npx skills add addyosmani/agent-skills            # install all 24 skills
npx skills add addyosmani/agent-skills --list     # browse before installing
npx skills add addyosmani/agent-skills --skill code-review-and-quality  # single skill
```

(README.md lines 45-58)

### Claude Code Installation

**Via Marketplace (recommended)**:

```
/plugin marketplace add addyosmani/agent-skills
/plugin install agent-skills@addy-agent-skills
```

**Note on SSH errors**: "The marketplace clones repos via SSH. If you don't have SSH keys set up on GitHub, either add your SSH key or use the full HTTPS URL to force HTTPS cloning" (README.md lines 71-76):

```bash
/plugin marketplace add https://github.com/addyosmani/agent-skills.git
```

**Local/Development**:

```bash
git clone https://github.com/addyosmani/agent-skills.git
claude --plugin-dir /path/to/agent-skills
```

(README.md lines 69-83)

### Usage After Installation

Invoke skills via slash commands:
- `/spec` to enter spec-driven development workflow
- `/build auto` to auto-generate and execute a plan
- `/test` to run test-driven development cycle
- `/review` to perform code review
- `/ship` to prepare deployment

Or invoke individual skills by name (e.g., "use the interview-me skill to grill me on requirements").

## Relevance to Claude Code Development

Agent Skills directly addresses the Claude Code ecosystem's need for agent discipline and structured workflows. Relevance includes:

1. **Agent Behavior Standardization**: Provides standardized workflows that agents follow consistently, reducing ad-hoc decision-making
2. **Quality Gate Enforcement**: Embeds verification steps into every phase, preventing agents from skipping critical checks
3. **Multi-Agent Orchestration**: Enables coordination between specialist agents (code-reviewer, security-auditor, test-engineer) via structured personas and slash commands
4. **Claude Code Plugin Development**: Offers a production-ready plugin that demonstrates best practices for packaging skills, agents, and commands for the Claude Code marketplace
5. **Skill Ecosystem Growth**: Provides a reference implementation for the skill format, frontmatter schema, and progressive disclosure pattern that Claude Code skill creators can learn from

## Limitations and Caveats

### Documented Limitations

**Scope**: Agent Skills focuses on the full development lifecycle (DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP). It is not a project management tool or a bug tracker; it assumes a development environment (local or CI/CD) where agents can write, test, and verify code.

**Skill Triggering**: Skills activate based on commands or explicit invocation. Automatic context detection (e.g., detecting that code is security-sensitive without user indication) is limited to the examples documented (API design detection, UI detection).

**Agent Coordination**: The four specialist personas (code-reviewer, security-auditor, test-engineer, web-performance-auditor) are pre-configured but not automatically orchestrated. Orchestration patterns must be explicit (documented in orchestration-patterns.md).

### Undocumented Limitations

**Scale constraints**: No documented limits on skill complexity, agent coordination depth, or maximum number of parallel skills. Untested at scale.

**Customization**: Limited guidance on modifying or extending skills for domain-specific workflows; the project assumes skills apply broadly across software projects.

**Async workflow support**: Skills are designed for synchronous development workflows; asynchronous patterns (e.g., multi-day feature development with external approvals) are not addressed.

**Rollback procedures**: The shipping-and-launch skill documents staged rollouts but does not provide recipes for rollback automation for specific platforms (Kubernetes, Lambda, traditional servers).

## References

- **Repository**: <https://github.com/addyosmani/agent-skills> (accessed 2026-07-07)
- **README.md**: Full feature documentation and lifecycle overview
- **CLAUDE.md**: Project structure and contribution guidelines
- **CONTRIBUTING.md**: Pre-flight checks and PR workflow
- **LICENSE**: MIT License, Copyright (c) 2025 Addy Osmani
- **Related frameworks**: [Superpowers](https://github.com/obra/superpowers), [Matt Pocock's skills](https://github.com/mattpocock/skills) (accessed 2026-07-07) — comparison in docs/comparison.md
- **Embedded principles**: Software Engineering at Google (abseil.io/resources/swe-book), Google engineering practices guide (google.github.io/eng-practices/)

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|--------------|-------|
| Overview | high | 2026-07-07 | Full README read, primary source |
| Problem Addressed | high | 2026-07-07 | Direct quotes from README |
| Key Statistics | high | 2026-07-07 | Exact skill count verified from README and skills/ directory listing |
| Key Features | high | 2026-07-07 | Feature list extracted from README table and skill descriptions |
| Technical Architecture | high | 2026-07-07 | Verified against actual directory structure and plugin.json files |
| Installation & Usage | high | 2026-07-07 | Exact commands from README; tested path verification |
| Limitations | medium | 2026-07-07 | Documented limitations extracted; undocumented limitations inferred from scope |

**Next Review**: 2026-10-07 (3 months)

**Archive Date**: 2026-07-07

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Maverick](../coding-agents/maverick.md) | coding-agents | autonomous coding agent using skill-based execution model |
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | multi-skill orchestration framework for Claude Code agents |
| [Pi Mono](../coding-agents/pi-mono.md) | coding-agents | monolithic coding agent with modular skill composition |
| [Compound Engineering Plugin](../research-agent-patterns/compound-engineering-plugin.md) | research-agent-patterns | multi-agent coordination workflow with skill-based task decomposition |
| [Claude Night Market](./claude-night-market.md) | skill-generation-tools | skill marketplace and registry for Claude Code agents |
| [Orchestra](../agent-frameworks/orchestra.md) | agent-frameworks | agent orchestration framework enabling skill composition and coordination |
| [Anthropic Agent Skills](./anthropics-skills.md) | skill-generation-tools | official Anthropic skills library with lifecycle-driven architecture |
| [Orchestrator Agent Creation Guide](../research-agent-patterns/orchestrator-agent-creation-guide.md) | research-agent-patterns | patterns for building orchestrator agents that route across skill domains |
