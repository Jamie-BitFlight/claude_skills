---
name: LiteAgents - Multi-Tool AI Development Toolkit
description: LiteAgents is an npm-distributed AI development toolkit providing 11 specialized agents and 22 commands/skills for product management, agile development, and software engineering workflows. It...
license: MIT
metadata:
  topic: liteagents
  category: agent-frameworks
  source_url: https://github.com/liteagents
  github: hamr0/liteagents
  version: "2.5.3"
  verified: "2026-02-15"
  next_review: "2026-05-15"
---

## Overview

LiteAgents is an npm-distributed AI development toolkit providing 11 specialized agents and 22 commands/skills for product management, agile development, and software engineering workflows. It supports four AI coding tools (Claude Code, Opencode, Ampcode, Droid) through a unified interactive installer, with Claude Code receiving the richest integration via subagents, auto-triggering skills, and a session memory pipeline (`/stash` → `/friction` → `/remember`).

---

## Problem Addressed

| Problem | LiteAgents Solution |
|---------|---------------------|
| AI coding tools ship with generic capabilities; users lack domain-specific agents for product management, architecture, and QA workflows | 11 pre-built agents covering full product lifecycle: market research → PRD → task generation → implementation → QA |
| Each AI coding tool has different configuration formats (`.claude/`, `.opencode/`, `.amp/`, `.droid/`) | Interactive installer with tool detection, path resolution, and format translation across 4 tools |
| AI sessions lose context during compaction or between sessions | Hot Memory pipeline: `/stash` saves context, `/friction` analyzes failure patterns, `/remember` consolidates into persistent `MEMORY.md` |
| AI agents produce false completions and undetected failures | Session friction analysis with 14 weighted signals detecting `false_success`, `tool_loop`, `user_intervention`, and other behavioral antipatterns |
| Agent orchestration requires manual routing between specialists | Orchestrator agent with intent-to-agent routing table, predefined multi-agent workflows (Greenfield, Brownfield, Feature, Bug Fix, Sprint) |
| TDD discipline erodes when AI agents prioritize speed over correctness | Auto-triggering TDD skill that intercepts implementation attempts, enforces Red-Green-Refactor cycle |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| npm Package Name | `liteagents` | 2026-02-15 |
| Current Version | 2.5.3 | 2026-02-15 |
| Initial Release | 1.0.0 (2025-11-02) | 2026-02-15 |
| License | MIT | 2026-02-15 |
| Author | hamr0 (Amr Hassan) | 2026-02-15 |
| Supported AI Tools | 4 (Claude Code, Opencode, Ampcode, Droid) | 2026-02-15 |
| Agents | 11 | 2026-02-15 |
| Commands/Skills | 22 | 2026-02-15 |
| Dependencies | 0 (zero runtime dependencies) | 2026-02-15 |
| Node.js Requirement | >= 14.0.0 | 2026-02-15 |
| Total Files in Packages | 184 | 2026-02-15 |
| friction.js Lines | 2,168 | 2026-02-15 |
| Test Count (reported) | 263 passing | 2026-02-15 |

---

## Key Features

### Agent System (11 Agents)

**Workflow Agents (3-step pipeline):**

- **1-create-prd**: Define scope with structured Product Requirement Documents
- **2-generate-tasks**: Break PRDs into granular, actionable task lists
- **3-process-task-list**: Execute tasks iteratively with progress tracking and review checkpoints

**Specialist Agents (8):**

- **orchestrator**: Intent routing, workflow coordination, resource discovery from frontmatter
- **code-developer**: Implementation, debugging, refactoring
- **quality-assurance**: Test architecture, quality gates, requirements traceability, risk assessment
- **context-builder**: Project initialization, documentation discovery, knowledge base creation
- **feature-planner**: Epics, user stories, prioritization, backlog management, retrospectives
- **market-researcher**: Market analysis, competitive research, brainstorming
- **system-architect**: System design, technology selection, API design, scalability
- **ui-designer**: UI/UX design, wireframes, prototypes, accessibility, design systems

### Orchestrator Workflows

| Workflow | Agent Sequence | Use Case |
|----------|---------------|----------|
| Greenfield | market-researcher → feature-planner → 1-create-prd → 2-generate-tasks → 3-process-task-list | New product from scratch |
| Brownfield | context-builder → system-architect → feature-planner | Understand existing codebase |
| Feature | feature-planner → 1-create-prd → 2-generate-tasks → 3-process-task-list | Add feature to existing product |
| Bug Fix | code-developer → quality-assurance | Fix and verify |
| Sprint | feature-planner → 2-generate-tasks | Plan sprint from backlog |

### Commands and Skills (22 Total)

**Auto-Triggering Skills (Claude Code only, 3):**

- **test-driven-development**: Enforces Red-Green-Refactor with deletion mandate for code-before-test violations
- **testing-anti-patterns**: Prevents mock-heavy testing and production pollution
- **verification-before-completion**: Requires running verification commands before success claims

**Manual Commands (19):**

- `/brainstorming` — Structured brainstorming sessions
- `/code-review` — Implementation review against requirements
- `/condition-based-waiting` — Replace timeouts with condition polling
- `/docs-builder` — Project documentation generation with reorganization detection
- `/root-cause-tracing` — Trace bugs backward through call stack
- `/skill-creator` — Guide for creating new skills
- `/systematic-debugging` — Four-phase debugging framework
- `/debug` — Systematic issue investigation
- `/explain` — Code explanation for newcomers
- `/friction` — Session log analysis for failure patterns (14 weighted signals)
- `/git-commit` — Intelligent commit creation
- `/optimize` — Performance analysis
- `/refactor` — Safe refactoring with behavior preservation
- `/remember` — Consolidate stashes and friction into project memory
- `/review` — Comprehensive code review
- `/security` — Vulnerability scanning
- `/ship` — Pre-deployment checklist
- `/stash` — Save session context for compaction recovery
- `/test-generate` — Generate test suites

### Hot Memory Pipeline

Lightweight session memory that learns from usage patterns, requiring no external dependencies:

<eg>
/stash → /friction → /remember
</eg>

1. **`/stash`**: Snapshot session context to `.claude/stash/`. Captures decisions, findings, active work.
2. **`/friction`**: Analyze session JSONL logs with 14 weighted signals. Classifies sessions as BAD/FRICTION/ROUGH/OK. Clusters failure patterns into antigen candidates. Bundled `friction.js` (2,168 lines) runs standalone or as CLI.
3. **`/remember`**: Extract facts and episodes from stashes via sonnet model. Distill friction clusters into behavioral preferences with confidence tiers (High/Medium/Low). Write unified `MEMORY.md` and inject reference into `CLAUDE.md`.

**Friction Signals (14):**

| Signal | Weight | Detection |
|--------|--------|-----------|
| `user_intervention` | 10 | User message contains `/stash` |
| `session_abandoned` | 10 | Last 3 turns have friction > 15, no success exit |
| `false_success` | 8 | LLM claims "done"/"fixed" but next tool result has error |
| `no_resolution` | 8 | Session has exit errors but no success after them |
| `tool_loop` | 6 | Same tool called 3+ times with identical arguments |
| `rapid_exit` | 6 | < 3 turns AND ends with error |
| `interrupt_cascade` | 5 | Multiple interrupts within 60 seconds |
| `user_curse` | 5 | Profanity in user message |
| `request_interrupted` | 2.5 | Turn has `is_interrupted: true` or ESC/Ctrl+C |
| `exit_error` | 1 | Tool result has non-zero exit code |
| `repeated_question` | 1 | User asks same question twice (fuzzy match) |
| `long_silence` | 0.5 | > 10 minute gap between turns |
| `user_negation` | 0.5 | User message starts with "no", "wrong", "didn't work" |
| `compaction` | 0.5 | System message indicates context compaction |

### Multi-Tool Installer

Interactive CLI installer supporting four AI coding tools with:

- **Tool detection**: Resolves correct paths per tool (`~/.claude/`, `.opencode/`, `.amp/`, `.droid/`)
- **Variant system**: Lite/Standard/Pro tiers (simplified to Pro-only in v2.5)
- **Silent mode**: CI/CD compatible (`--silent --variant=standard --tools=claude`)
- **Rollback**: Atomic operations with full rollback on failure
- **Resume**: State management for interrupted installations
- **Uninstall**: Clean removal via `--uninstall --tools=claude`
- **Multi-tool**: Install all 4 tools simultaneously

---

## Technical Architecture

<eg>
┌──────────────────────────────────────────────────────────────┐
│                     liteagents (npm)                          │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Interactive Installer (cli.js)              │ │
│  │  Tool Selection → Variant → Path Config → Installation  │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                  │
│  ┌─────────────────────────v───────────────────────────────┐ │
│  │                  packages/ (4 tools)                     │ │
│  │                                                          │ │
│  │  claude/          opencode/      ampcode/      droid/   │ │
│  │  ├── agents/      ├── agent/     ├── agent/    ├── agent│ │
│  │  ├── skills/      ├── command/   ├── command/  ├── cmd/ │ │
│  │  ├── commands/    ├── AGENTS.md  ├── AGENTS.md ├── AGT  │ │
│  │  ├── CLAUDE.md    └── opencode   └── amp.yml   └── AGT  │ │
│  │  └── variants.json    .jsonc                    .md     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Hot Memory Pipeline                         │ │
│  │                                                          │ │
│  │  /stash ──> .claude/stash/*.md                          │ │
│  │  /friction ──> friction.js ──> .claude/friction/        │ │
│  │  /remember ──> sonnet extraction ──> .claude/memory/    │ │
│  │                                      MEMORY.md          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Agent Orchestration                         │ │
│  │                                                          │ │
│  │  Intent ──> Orchestrator ──> Agent Routing               │ │
│  │                │                                          │ │
│  │                ├── Predefined Workflows (5)              │ │
│  │                ├── Intent-to-Agent Table                 │ │
│  │                └── Lazy Discovery (frontmatter parsing)  │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
</eg>

### Tool-Specific Differences

| Feature | Claude Code | Opencode / Ampcode / Droid |
|---------|-------------|---------------------------|
| Agents | Full subagents with `@agent` invocation | Agent reference docs only |
| Skills | SKILL.md with auto-trigger support | Commands only (manual invocation) |
| Auto-triggering | 3 skills (TDD, anti-patterns, verification) | Not supported |
| Memory pipeline | Full `/stash` → `/friction` → `/remember` | Commands available, paths adapted |
| Configuration | `.claude/` directory, `CLAUDE.md` | Tool-specific dirs and config files |

### File Structure Per Tool (Claude)

<eg>
packages/claude/
├── agents/              # 11 agent markdown files
│   ├── orchestrator.md
│   ├── 1-create-prd.md
│   ├── 2-generate-tasks.md
│   ├── 3-process-task-list.md
│   ├── code-developer.md
│   ├── quality-assurance.md
│   ├── context-builder.md
│   ├── feature-planner.md
│   ├── market-researcher.md
│   ├── system-architect.md
│   └── ui-designer.md
├── skills/              # Auto-triggering skills with SKILL.md
│   ├── test-driven-development/
│   ├── testing-anti-patterns/
│   ├── verification-before-completion/
│   ├── brainstorming/
│   ├── code-review/
│   ├── condition-based-waiting/
│   ├── docs-builder/
│   ├── root-cause-tracing/
│   ├── skill-creator/
│   └── systematic-debugging/
├── commands/            # Slash commands
│   ├── friction.md
│   ├── friction/friction.js
│   ├── remember.md
│   ├── stash.md
│   └── ... (12 total)
├── CLAUDE.md            # Reference document listing all resources
└── variants.json        # Variant configuration
</eg>

---

## Installation and Usage

### Installation

```bash
# NPX (recommended, no global install)
npx liteagents

# Global install
npm install -g liteagents
liteagents

# Silent mode for CI/CD
npx liteagents --silent --tools=claude
```

### Usage (Claude Code)

```bash
# Agent invocation
@orchestrator help
@1-create-prd Create a PRD for a task management app
@code-developer Implement the authentication module

# Skill/command invocation
/brainstorming Explore authentication approaches
/test-driven-development Implement user login
/friction ~/.claude/projects/-home-user-myproject/

# Hot Memory pipeline
/stash "auth-investigation"
/friction ~/.claude/projects/-home-user-myproject/
/remember

# Standalone CLI friction analysis
liteagents friction ~/.claude/projects
```

### Usage (Opencode / Ampcode / Droid)

```bash
# Commands only (no subagent system)
/1-create-prd Create a PRD for a task management app
/brainstorming Explore authentication approaches
/test-driven-development Implement user login
```

---

## Relevance to Claude Code Development

### Applications

1. **Session Memory Pattern**: The Hot Memory pipeline (`/stash` → `/friction` → `/remember`) is a production implementation of markdown-based session persistence without external databases. Facts, episodes, and behavioral preferences are extracted from session logs and consolidated into a single `MEMORY.md` file referenced via `@MEMORY.md` in `CLAUDE.md`. This pattern directly addresses context loss during compaction.

2. **Friction Analysis as Quality Signal**: The 14-signal friction scoring system provides a quantitative framework for evaluating AI session quality. The signals (especially `false_success`, `tool_loop`, `user_intervention`) map directly to common failure modes in AI coding sessions. The antigen clustering approach groups related failures for pattern recognition.

3. **Multi-Agent Orchestration Reference**: The orchestrator agent demonstrates intent-based routing with lazy discovery (reading agent frontmatter on-demand rather than pre-loading). The predefined workflow sequences (Greenfield, Brownfield, Feature, Bug Fix, Sprint) show how to compose multi-agent pipelines for different development scenarios.

4. **Auto-Triggering Skill Design**: The TDD skill's auto-trigger mechanism (`auto_trigger: true` in frontmatter) with detailed activation/deactivation conditions is a reference implementation for skills that should intercept agent behavior based on context rather than explicit invocation.

5. **Cross-Tool Portability**: The four-package structure demonstrates how to maintain consistent agent/command content across tools with different configuration formats, directory conventions, and capability levels.

### Patterns Worth Adopting

1. **Friction Signal Taxonomy**: The weighted signal system for scoring session quality could be adapted for evaluating our own agent/skill effectiveness. The specific signals (false_success detection, tool_loop detection) are directly applicable.

2. **Stash-Then-Consolidate Memory**: The two-phase approach (capture raw context with `/stash`, then extract structured knowledge with `/remember`) separates collection from curation, avoiding the problem of trying to do both in real-time during a session.

3. **Agent Frontmatter Discovery**: The orchestrator's lazy discovery pattern (reading `name`, `description`, `when_to_use` from frontmatter at routing time rather than pre-loading) reduces context pollution and scales to large agent collections.

4. **Enforcement Through Deletion**: The TDD skill's mandate to delete code written before tests ("Delete means delete") demonstrates how to write skills that enforce process discipline rather than merely suggesting it.

### Integration Opportunities

1. **Friction Analysis on Our Sessions**: The standalone `liteagents friction` CLI could be run against Claude Code session logs to identify recurring failure patterns in our own development workflows.

2. **Memory Pipeline Comparison**: Compare the `/stash` → `/friction` → `/remember` pipeline with our existing session documentation approach to identify gaps in session context preservation.

3. **Agent Design Patterns**: The agent markdown format (frontmatter with `name`, `description`, `when_to_use`, `model`, `color`) and the orchestrator's routing table provide templates for designing new agents.

### Considerations

1. **Claude Code Exclusivity for Rich Features**: Auto-triggering skills and the subagent system only work with Claude Code. Other tools get commands only, making the toolkit less valuable outside the Claude ecosystem.

2. **Zero Dependencies but Node.js Required**: While the package has zero npm dependencies, it requires Node.js >= 14.0.0 for installation and the friction analysis script.

3. **Variant Simplification**: The variant system (Lite/Standard/Pro) documented in v1.2.0 appears simplified to Pro-only in current Claude package (`variants.json` has only a `pro` entry), suggesting the tiered approach may not have been adopted by users.

4. **Session Log Format Coupling**: The friction analysis is tightly coupled to Claude Code's JSONL session log format. Changes to that format would break the analysis pipeline.

5. **Sonnet Model Dependency**: The `/remember` command explicitly uses sonnet for extraction, which may not be available in all environments or may incur costs.

---

## References

1. **LiteAgents GitHub Repository** - <https://github.com/hamr0/liteagents> (accessed 2026-02-15)
2. **LiteAgents npm Package** - <https://www.npmjs.com/package/liteagents> (accessed 2026-02-15)
3. **LiteAgents README.md** - Repository root README (cloned and read 2026-02-15)
4. **LiteAgents CHANGELOG.md** - Full version history from 1.0.0 to 2.5.3 (cloned and read 2026-02-15)
5. **LiteAgents package.json** - Package metadata, version 2.5.3 (cloned and read 2026-02-15)
6. **LiteAgents LICENSE** - MIT, Copyright (c) 2025 Amr Hassan (cloned and read 2026-02-15)
7. **Claude Package CLAUDE.md** - `packages/claude/CLAUDE.md` listing all agents, skills, commands (cloned and read 2026-02-15)
8. **Orchestrator Agent** - `packages/claude/agents/orchestrator.md` with routing table and workflow definitions (cloned and read 2026-02-15)
9. **TDD Skill** - `packages/claude/skills/test-driven-development/SKILL.md` with auto-trigger and enforcement rules (cloned and read 2026-02-15)
10. **Friction Command** - `packages/claude/commands/friction.md` with 14-signal taxonomy (cloned and read 2026-02-15)
11. **Remember Command** - `packages/claude/commands/remember.md` with memory consolidation pipeline (cloned and read 2026-02-15)
12. **Stash Command** - `packages/claude/commands/stash.md` with context capture design (cloned and read 2026-02-15)
13. **Subagentic Manual** - `packages/subagentic-manual.md` complete agent/command reference (file exists, 13,204 bytes)
14. **Variants Configuration** - `packages/claude/variants.json` showing Pro-only config (cloned and read 2026-02-15)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [flue](./flue.md) | agent-frameworks | referenced by flue (agent-frameworks) |
| [orchestra](./orchestra.md) | agent-frameworks | 11-agent toolkit with orchestrator agent and session memory pipeline; shares Orchestra's intent-based agent routing and multi-step workflow coordination (bidirectional) |
| [ponytail](./ponytail.md) | agent-frameworks | referenced by ponytail (agent-frameworks) |
| [solace-agent-mesh](./solace-agent-mesh.md) | agent-frameworks | Multi-agent toolkit with 11 specialized agents and orchestrator agent; shares task delegation and agent-to-agent workflow patterns (bidirectional) |
| [AutoResearchClaw](../agent-infrastructure/AutoResearchClaw.md) | agent-infrastructure | referenced by AutoResearchClaw (agent-infrastructure) |
| [empirica](../agent-infrastructure/empirica.md) | agent-infrastructure | referenced by empirica (agent-infrastructure) |
| [simplemem-cross](../context-management/simplemem-cross.md) | context-management | referenced by simplemem-cross (context-management) |
