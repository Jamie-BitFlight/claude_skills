# Claude Night Market

| Field         | Value                                                      |
| ------------- | ---------------------------------------------------------- |
| Research Date | 2026-01-31                                                 |
| Primary URL   | <https://github.com/athola/claude-night-market>            |
| Homepage      | <https://athola.github.io/claude-night-market>             |
| GitHub        | <https://github.com/athola/claude-night-market>            |
| Installation  | `/plugin marketplace add athola/claude-night-market`       |
| Version       | 1.3.7                                                      |
| License       | MIT                                                        |
| Author        | [@athola](https://github.com/athola)                       |

---

## Overview

Claude Night Market is a comprehensive Claude Code plugin marketplace providing 16 plugins with 126 skills, 114 commands, and 41 agents for software engineering workflows. The plugins are organized in architectural layers (Foundation, Utility, Domain Specialists, Meta) covering git operations, code review, spec-driven development, issue management, multi-LLM delegation, TDD enforcement, and session management. The ecosystem adds approximately 14.8k characters to system prompts and includes cross-session state persistence via Claude Code Tasks (v2.1.16+).

---

## Problem Addressed

| Problem                                              | Solution                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------- |
| Claude Code lacks specialized workflow automation    | 114 slash commands for PR prep, code review, issue resolution, cleanup    |
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

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 158                       | 2026-01-31    |
| GitHub Forks      | 19                        | 2026-01-31    |
| Open Issues       | 61                        | 2026-01-31    |
| Contributors      | 2                         | 2026-01-31    |
| Primary Language  | Python                    | 2026-01-31    |
| Repository Age    | Since 2025-11-23          | 2026-01-31    |
| Total Plugins     | 16                        | 2026-01-31    |
| Total Skills      | 126                       | 2026-01-31    |
| Total Commands    | 114                       | 2026-01-31    |
| Total Agents      | 41                        | 2026-01-31    |
| System Prompt     | ~14.8k characters         | 2026-01-31    |

---

## Key Features

### Plugin Architecture Layers

| Layer               | Plugins                           | Purpose                                     |
| ------------------- | --------------------------------- | ------------------------------------------- |
| Foundation          | sanctum, leyline, imbue           | Git/sessions, auth/quotas, TDD cycles       |
| Utility             | conserve, hookify, conjure        | Resource optimization, rules engine, delegation |
| Domain Specialists  | pensive, spec-kit, minister, memory-palace, archetypes, parseltongue, attune, scribe, scry | Task-specific logic |
| Meta                | abstract                          | Plugin/skill authoring, Makefile generation |

### Core Plugins

| Plugin          | Skills | Commands | Description                                                  |
| --------------- | ------ | -------- | ------------------------------------------------------------ |
| abstract        | 13     | 16       | Meta-skills infrastructure, hook development, evaluation     |
| attune          | 13     | 11       | Full-cycle project development with war-room expert routing  |
| archetypes      | 15     | 0        | 14 architecture paradigms from functional-core to microservices |
| conjure         | 3      | 0        | Intelligent delegation to Gemini/Qwen with strategic oversight |
| conserve        | 12     | 6        | Context optimization, bloat detection, token conservation    |
| hookify         | 2      | 5        | Zero-code behavioral rule authoring via markdown             |
| imbue           | 11     | 3        | Review scaffolding, diff analysis, TDD enforcement           |
| leyline         | 12     | 1        | OAuth flows, storage patterns, quotas                        |
| memory-palace   | 7      | 4        | Spatial knowledge organization, skill execution memory       |
| minister        | 2      | 5        | GitHub issue/project alignment and status dashboards         |
| parseltongue    | 5      | 3        | Multi-language detection, testing guidance                   |
| pensive         | 15     | 12       | Multi-domain code review with NASA Power of 10 patterns      |
| sanctum         | 18     | 18       | Git operations, PR prep, session management                  |
| scribe          | 3      | 3        | Documentation with AI slop detection, style learning         |
| scry            | 4      | 3        | Terminal recordings (VHS), browser recordings (Playwright)   |
| spec-kit        | 3      | 2        | Spec-driven development orchestration                        |

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

3. **Review Domains**: pensive's review taxonomy (15 specialized reviews) could expand coverage.

4. **Delegation Framework**: conjure's delegation-core skill provides patterns for external LLM integration.

5. **Session Persistence**: sanctum's cross-session state patterns address conversation continuity.

### Comparison with This Repository

| Aspect              | Claude Night Market                | This Repository (claude_skills)     |
| ------------------- | ---------------------------------- | ------------------------------------ |
| Plugins             | 16 plugins                         | Plugin marketplace                   |
| Skills              | 126 skills                         | Skill collection                     |
| Commands            | 114 commands                       | Command collection                   |
| Agents              | 41 agents                          | Agent collection                     |
| Architecture        | 4-layer (Foundation/Utility/Domain/Meta) | Category-based                 |
| Hook Governance     | TDD enforcement, rigorous reasoning | Skill-based instructions            |
| Multi-LLM           | Gemini/Qwen delegation             | Single-model focus                   |
| Session State       | Cross-session persistence          | Per-session                          |
| Primary Author      | @athola                            | Community                            |

---

## References

| Source                    | URL                                                                        | Accessed   |
| ------------------------- | -------------------------------------------------------------------------- | ---------- |
| GitHub Repository         | <https://github.com/athola/claude-night-market>                            | 2026-01-31 |
| GitHub README             | <https://raw.githubusercontent.com/athola/claude-night-market/master/README.md> | 2026-01-31 |
| GitHub API (Metadata)     | <https://api.github.com/repos/athola/claude-night-market>                  | 2026-01-31 |
| Marketplace JSON          | <https://raw.githubusercontent.com/athola/claude-night-market/master/.claude-plugin/marketplace.json> | 2026-01-31 |
| Capabilities Reference    | <https://raw.githubusercontent.com/athola/claude-night-market/master/book/src/reference/capabilities-reference.md> | 2026-01-31 |
| Homepage                  | <https://athola.github.io/claude-night-market>                             | 2026-01-31 |

**Research Method**: Information gathered from GitHub repository README, GitHub API for repository metadata (stars, forks, license, dates), marketplace.json for plugin details, and capabilities reference for skill/command/agent counts. Statistics verified via direct API calls on 2026-01-31.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | 1.3.7                               |
| Last Pushed        | 2026-01-31                          |
| GitHub Stars       | 158 (as of 2026-01-31)              |
| Total Plugins      | 16 (as of 2026-01-31)               |
| Total Skills       | 126 (as of 2026-01-31)              |
| Next Review Date   | 2026-05-01                          |

**Review Triggers**:

- GitHub stars milestone (250, 500, 1K)
- Major version bump (2.x.x release)
- New plugin layer additions
- Cross-session state API changes
- War-room framework updates
- New LLM delegation targets added
- Significant skill additions (20+ new skills)
