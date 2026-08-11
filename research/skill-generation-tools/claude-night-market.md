---
name: Claude Night Market
description: Claude Night Market is a Claude Code plugin marketplace providing 23 plugins with 201 skills, 163 commands, and 56 agents for software engineering workflows. The plugins are organized...
license: MIT
metadata:
  topic: claude-night-market
  category: skill-generation-tools
  source_url: https://github.com/athola/claude-night-market
  github: athola/claude-night-market
  version: "1.9.17"
  verified: "2026-08-11"
  next_review: "2026-11-11"
---

## Overview

Claude Night Market is a Claude Code plugin marketplace providing 23 plugins with 201 skills, 163 commands, and 56 agents for software engineering workflows. The plugins are organized in architectural layers (Foundation, Utility, Domain Specialists, Meta) covering git operations, code review, spec-driven development, issue management, multi-LLM delegation, TDD enforcement, and session management. The ecosystem adds approximately 14.8k characters to system prompts and includes cross-session state persistence via Claude Code Tasks (v2.1.16+).

---

## Installation & Usage

### Claude Code (Recommended Setup)

**Prerequisites**: Claude Code 2.1.16+ and Python 3.9+ for hooks to function properly.

**Quick Setup** (install all plugins at once):

```bash
/plugin marketplace add athola/claude-night-market
npx skills add athola/claude-night-market
```

**Or install by plugin category**:

```bash
/plugin install sanctum@claude-night-market    # Git operations & session management
/plugin install pensive@claude-night-market    # Multi-domain code review
/plugin install spec-kit@claude-night-market   # Spec-driven development
/plugin install imbue@claude-night-market      # TDD enforcement
/plugin install attune@claude-night-market     # Project detection & war-room
```

After installation, run once:

```bash
claude --init
```

**Source**: README.md "Install" section lines 18–34 (accessed 2026-08-11). The README documents `sanctum`, `pensive`, and `spec-kit` explicitly; `imbue` and `attune` are confirmed plugin names in `.claude-plugin/marketplace.json` and follow the same `<plugin>@claude-night-market` form.

### Common Workflow Commands

| Task | Command | Skill |
|------|---------|-------|
| Start a feature | `/attune:mission` | attune |
| Write specifications | `/speckit-specify` | spec-kit |
| Run code review | `/full-review` | pensive |
| Prepare PR | `/prepare-pr` | sanctum |
| Resume session | `/catchup` | sanctum |
| Clean codebase | `/unbloat` | conserve |
| Strategic decision | `/attune:war-room` | attune |

**Source**: README.md "The commands you reach for most" table lines 58–70 (accessed 2026-08-11)

### Targeted Installation (Smaller Footprint)

```bash
opkg i gh@athola/claude-night-market --plugins sanctum,pensive
```

**Source**: README.md line 32 (accessed 2026-08-11)

### Typical Feature Workflow

1. **Start a feature** — `/attune:mission` routes through brainstorm, specify, plan, and execute phases
2. **Write the code** — `imbue` enforces a failing test first, so implementation follows the test
3. **Review before you push** — `/full-review` runs a multi-discipline pass; `/refine-code` cleans up duplication and dead code
4. **Ship it** — `/prepare-pr` runs quality gates and leaves a clean git state ready for a pull request
5. **Pick up where you left off** — `/catchup` rebuilds context from recent git history after a break

**Source**: README.md "Everyday Use" section lines 39–54 (accessed 2026-08-11)

---

## Problem Addressed

| Problem                                              | Solution                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------- |
| Claude Code lacks specialized workflow automation    | 163 slash commands for PR prep, code review, issue resolution, cleanup    |
| No governance over AI behavior during development    | Hook-based governance (imbue TDD enforcement, pensive usage tracking)     |
| Multi-LLM workflows require manual orchestration     | conjure plugin delegates to Gemini/Qwen while retaining strategic oversight |
| Session context lost between conversations           | sanctum session management with checkpointing and resume strategies       |
| No spec-driven development enforcement               | spec-kit requires written specifications before code generation           |
| Inconsistent code review across domains              | pensive provides unified reviews (architecture, bugs, API, math, Rust, shell) |
| Quality gates scattered across workflows             | Centralized quality gates halt execution if tests fail                    |
| Project initialization lacks architecture awareness  | attune detects project types and scaffolds configuration files            |
| Strategic decisions lack expert consultation         | war-room uses Type 1/2 reversibility framework with expert subagent routing |

---

## Key Statistics

| Metric            | Value                     | Date Gathered | Source |
| ----------------- | ------------------------- | ------------- | ------ |
| GitHub Stars      | 327                       | 2026-08-11    | GitHub API |
| GitHub Forks      | 35                        | 2026-08-11    | GitHub API |
| Open Issues       | 14                        | 2026-08-11    | GitHub API |
| Primary Language  | Python                    | 2026-08-11    | GitHub API |
| License           | MIT                       | 2026-08-11    | GitHub API |
| Repository Age    | Since 2025-11-23          | 2026-08-11    | GitHub API `created_at` |
| Marketplace Version | 1.9.17                  | 2026-08-11    | `.claude-plugin/marketplace.json` |
| Total Plugins     | 23                        | 2026-08-11    | `.claude-plugin/marketplace.json` |
| Total Skills      | 201                       | 2026-08-11    | git tree, `plugins/*/skills/*/SKILL.md` |
| Total Commands    | 163                       | 2026-08-11    | git tree, `plugins/*/commands/*.md` |
| Total Agents      | 56                        | 2026-08-11    | git tree, `plugins/*/agents/*.md` |
| System Prompt     | ~14.8k characters         | 2026-01-31    | README (not re-verified) |

---

## Key Features

### Plugin Architecture Layers

| Layer               | Plugins                           | Purpose                                     |
| ------------------- | --------------------------------- | ------------------------------------------- |
| Foundation          | sanctum, leyline, imbue           | Git/sessions, auth/quotas, TDD cycles       |
| Utility             | conserve, hookify, conjure        | Resource optimization, rules engine, delegation |
| Domain Specialists  | pensive, spec-kit, minister, memory-palace, archetypes, parseltongue, attune, scribe, scry, cartograph, gauntlet, tome, phantom, oracle, herald, egregore | Task-specific logic |
| Meta                | abstract                          | Plugin/skill authoring, Makefile generation |

### Core Plugins

Counts derived from the repository git tree on 2026-08-11 (`plugins/{name}/skills/*/SKILL.md`, `plugins/{name}/commands/*.md`, `plugins/{name}/agents/*.md`); descriptions quoted from `.claude-plugin/marketplace.json`.

| Plugin          | Skills | Commands | Agents | Description                                                  |
| --------------- | ------ | -------- | ------ | ------------------------------------------------------------ |
| abstract        | 15     | 18       | 6      | Skill authoring, hook development, evaluation frameworks, escalation governance |
| archetypes      | 15     | 0        | 0      | Architecture paradigm selection: 14 paradigms from functional-core to hexagonal |
| attune          | 14     | 11       | 2      | Full-cycle project development: brainstorm, specify, plan, initialize, execute, polish, war-room |
| cartograph      | 7      | 1        | 1      | Codebase visualization: architecture, data flow, dependency, call chains, community detection |
| conjure         | 4      | 0        | 0      | Delegate tasks to external LLMs (Gemini, Qwen) with cheapest-capable model selection |
| conserve        | 15     | 6        | 5      | Context optimization, bloat detection, CPU/GPU monitoring, token conservation |
| egregore        | 4      | 5        | 2      | Autonomous agent orchestrator: parallel worktree execution, agent specialization |
| gauntlet        | 7      | 6        | 1      | Codebase learning via knowledge extraction, code knowledge graph, adaptive challenges |
| herald          | 0      | 0        | 0      | Standalone notification system: GitHub issue alerts, webhooks for Slack/Discord |
| hookify         | 2      | 6        | 0      | Behavioral rules engine: safety hooks through markdown configuration |
| imbue           | 16     | 5        | 1      | TDD enforcement, proof-of-work validation, scope guarding, rigorous reasoning |
| leyline         | 24     | 3        | 0      | Foundation infrastructure: auth flows, quota management, error patterns, trust |
| memory-palace   | 9      | 5        | 4      | Spatial knowledge organization: build, navigate, maintain virtual memory palaces |
| minister        | 3      | 3        | 0      | GitHub issue management, label taxonomy, initiative tracking                  |
| oracle          | 1      | 1        | 0      | ONNX Runtime inference daemon for ML-enhanced plugin capabilities            |
| parseltongue    | 4      | 3        | 4      | Python development suite: testing, performance, async patterns, packaging     |
| pensive         | 15     | 14       | 6      | Multi-discipline code review: architecture, bugs, APIs, blast radius, security |
| phantom         | 1      | 1        | 1      | Computer use toolkit for driving desktop environments via vision and action API |
| sanctum         | 19     | 49       | 9      | Git workflows: commit messages, PR prep, docs, version management, sessions   |
| scribe          | 11     | 9        | 5      | Documentation review, cleanup, generation with AI slop detection, style learning |
| scry            | 4      | 2        | 1      | Media generation: terminal recordings (VHS), browser recordings (Playwright)  |
| spec-kit        | 3      | 11       | 3      | Specification-driven development: structured specs, planning, task orchestration |
| tome            | 8      | 4        | 5      | Multi-source research: code archaeology, community discourse, academic literature |

### Governance and Quality

| Feature                   | Plugin/Mechanism           | Description                                       |
| ------------------------- | -------------------------- | ------------------------------------------------- |
| TDD Enforcement           | imbue PreToolUse hook      | Verifies test files exist before implementation   |
| Rigorous Reasoning        | imbue:rigorous-reasoning   | Step-by-step logic checks before tool execution   |
| Usage Tracking            | pensive                    | Tracks skill usage frequency and failure rates    |
| Permission Checks         | conserve                   | Auto-approves safe commands, blocks risky ops     |
| Quality Gates             | /create-skill, /create-command | Halts if project has failing tests           |
| Expert Routing            | attune:war-room            | Type 1/2 reversibility framework for decisions    |

### Installation Methods

```bash
# Plugin marketplace
/plugin marketplace add athola/claude-night-market

# Install specific plugins
/plugin install sanctum@claude-night-market
/plugin install pensive@claude-night-market
/plugin install spec-kit@claude-night-market

# npx (alternative)
npx skills add athola/claude-night-market
npx skills add athola/claude-night-market/sanctum
```

### Notable Workflows

| Workflow              | Command/Skill                    | Description                                  |
| --------------------- | -------------------------------- | -------------------------------------------- |
| PR Preparation        | `/prepare-pr`                    | Validates branch, runs linters, verifies git state |
| Unified Code Review   | `/full-review`                   | Multi-discipline (syntax, logic, security)   |
| Issue Resolution      | `/do-issue`                      | Progressive GitHub issue implementation      |
| Context Recovery      | `/catchup`                       | Reads recent git history for context         |
| Codebase Cleanup      | `/cleanup`                       | Bloat removal, quality audit, hygiene scan   |
| CI/CD Update          | `/update-ci`                     | Reconciles hooks/workflows with code changes |
| Strategic Decisions   | `/attune:war-room`               | Expert routing with reversibility scoring    |
| Spec-First Dev        | `/speckit-specify`               | Written spec required before code            |
| Safety Review         | `Skill(pensive:safety-critical-patterns)` | NASA Power of 10 guidelines         |

---

## Technical Architecture

### Directory Structure

```text
plugins/
  <plugin-name>/
    skills/
      <skill-name>/
        SKILL.md          # Agent-facing instructions
    commands/
      <command-name>.md   # Slash command definitions
    agents/
      <agent-name>.md     # Agent configurations
    hooks/
      <hook-name>.md      # Behavioral hooks
```

### Cross-Session State (Claude Code 2.1.16+)

- attune, spec-kit, sanctum integrate with native Claude Code Tasks system
- Task creation on-demand with persistence via `CLAUDE_CODE_TASK_LIST_ID`
- `war-room-checkpoint` enables embedded escalation at decision points
- Fallback to file-based state for versions prior to 2.1.16

### LSP Integration (v2.0.74+)

- Symbol search in ~50ms (faster than text search)
- Requires `ENABLE_LSP_TOOL: "1"` in `~/.claude/settings.json`
- Compatible with language servers like pyright

### Prompt Context Management

- ~14.8k character system prompt budget (limit: 15k)
- Enforced by pre-commit hook
- Modular designs and progressive loading to stay within limits

---

## Relevance to Claude Code Development

### Direct Applications

1. **Plugin Architecture Patterns**: Layered architecture (Foundation, Utility, Domain, Meta) provides clear separation of concerns for plugin ecosystem design.

2. **Hook Governance**: PreToolUse hooks for TDD enforcement and rigorous reasoning demonstrate behavioral guardrails without code changes.

3. **Multi-LLM Delegation**: conjure plugin patterns for routing tasks to Gemini/Qwen while retaining oversight show hybrid AI workflow design.

4. **Session Management**: sanctum's checkpointing and resume strategies address context loss between conversations.

5. **Expert Routing**: war-room's Type 1/2 reversibility framework provides structured approach to decision escalation.

6. **Code Review Taxonomy**: pensive's domain-specific reviews (architecture, bugs, API, math, Rust, shell, Makefile) show comprehensive review coverage.

### Patterns Worth Adopting

1. **Layer-Based Organization**: Foundation (core utilities), Utility (resource management), Domain (task-specific), Meta (authoring tools) provides clear mental model.

2. **Quality Gate Enforcement**: Halting execution on failing tests before allowing skill/command creation enforces quality.

3. **Stability Metrics**: pensive's usage frequency and failure rate tracking identifies unstable workflows.

4. **Progressive Depth Levels**: `/cleanup` command with configurable depth levels allows graduated thoroughness.

5. **War Room Pattern**: Multi-expert consultation with reversibility scoring for high-stakes decisions.

6. **Slop Detection**: scribe's AI slop detector identifies AI-generated content markers for quality control.

7. **Memory Palace Technique**: Spatial knowledge organization for skill execution memory and PR review context.

### Integration Opportunities

1. **Skill Import**: Compatible plugin format allows cross-marketplace skill sharing.

2. **Hook Patterns**: imbue's TDD enforcement hooks could inform this repository's quality gates.

3. **Review Domains**: pensive's review taxonomy (15 skills across architecture, bugs, APIs, blast radius, security, tests) could expand coverage.

4. **Delegation Framework**: conjure's delegation-core skill provides patterns for external LLM integration.

5. **Session Persistence**: sanctum's cross-session state patterns address conversation continuity.

### Comparison with This Repository

| Aspect              | Claude Night Market                | This Repository (claude_skills)     |
| ------------------- | ---------------------------------- | ------------------------------------ |
| Plugins             | 23 plugins                         | Plugin marketplace                   |
| Skills              | 201 skills                         | Skill collection                     |
| Commands            | 163 commands                       | Command collection                   |
| Agents              | 56 agents                          | Agent collection                     |
| Architecture        | 4-layer (Foundation/Utility/Domain/Meta) | Category-based                 |
| Hook Governance     | TDD enforcement, rigorous reasoning | Skill-based instructions            |
| Multi-LLM           | Gemini/Qwen delegation             | Single-model focus                   |
| Session State       | Cross-session persistence          | Per-session                          |
| Primary Author      | @athola                            | Community                            |

---

## References

| Source                    | URL                                                                        | Accessed   |
| ------------------------- | -------------------------------------------------------------------------- | ---------- |
| GitHub Repository         | <https://github.com/athola/claude-night-market>                            | 2026-08-11 |
| GitHub README             | <https://raw.githubusercontent.com/athola/claude-night-market/master/README.md> | 2026-08-11 |
| GitHub API (Metadata)     | <https://api.github.com/repos/athola/claude-night-market>                  | 2026-08-11 |
| Marketplace JSON          | <https://raw.githubusercontent.com/athola/claude-night-market/master/.claude-plugin/marketplace.json> | 2026-08-11 |
| Capabilities Reference    | <https://raw.githubusercontent.com/athola/claude-night-market/master/book/src/reference/capabilities-reference.md> | 2026-01-31 |
| Homepage                  | <https://athola.github.io/claude-night-market>                             | 2026-01-31 |

**Research Method**: Information gathered from GitHub repository README, GitHub API for repository metadata (stars, forks, license, dates), marketplace.json for plugin details, and capabilities reference for skill/command/agent counts. Statistics re-verified via direct GitHub API calls and git-tree enumeration on 2026-08-11; the earlier 2026-01-31 figures (16 plugins / 126 skills / 114 commands / 41 agents, v1.3.7) were superseded.
