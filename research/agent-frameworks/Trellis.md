---
title: Trellis — Multi-Platform AI Coding Framework
resource_url: https://github.com/mindfold-ai/Trellis
created: 2026-04-06
last_reviewed: 2026-04-06
category: agent-frameworks
---

## Overview

Trellis is a multi-platform AI coding framework designed as "scaffolding for AI," providing structured workflow management, context injection, and parallel agent execution across multiple AI coding platforms. The framework centralizes project conventions, task context, and developer memory in a `.trellis/` directory structure, enabling consistent workflow across Claude Code, Cursor, OpenCode, iFlow, Codex, Kilo, Kiro, Gemini CLI, Antigravity, Windsurf, Qoder, and CodeBuddy.

**Repository**: <https://github.com/mindfold-ai/Trellis>
**License**: GNU Affero General Public License v3.0 (AGPL-3.0)
**Primary Language**: Python (46.0%), TypeScript (26.6%), Shell (21.8%), JavaScript (5.7%)
**Created**: 2026-01-26
**Last Updated**: 2026-03-17

---

## Problem Addressed

Multi-tool AI development faces several friction points:

1. **Context Repetition**: Each AI coding session requires re-explaining project conventions, coding standards, and workflow preferences. Source: README.md — "Write conventions once in `.trellis/spec/`, then let Trellis inject the relevant context into each session instead of repeating yourself."

2. **Non-Portable Workflows**: Projects using multiple AI platforms (Claude Code, Cursor, OpenCode) rebuild workflow artifacts for each tool instead of sharing unified process. Source: README.md — "If your team uses more than one AI coding tool, Trellis gives you one shared structure for specs, tasks, and process. The platform-specific wiring changes, but the workflow stays recognizable."

3. **Sequential Branch Management**: Multiple AI agents working on the same repository create branch conflicts and state contention. Source: README.md — "Run multiple AI tasks side by side with git worktrees instead of turning one branch into a traffic jam."

4. **Session Continuity Loss**: Without persistent project memory, each new AI session starts from zero context. Source: README.md — "Task PRDs, checklists, and workspace journals make previous decisions available to the next session. Instead of starting from blank context, the next agent can pick up where the last one left off."

---

## Key Statistics

- **GitHub Stars**: 3,782 (as of 2026-03-17)
- **GitHub Forks**: 193
- **Open Issues**: 0
- **Contributors**: 6 (top: taosu0216, lapse12, jsfaint, SamCuipogobongo, Xintong120, Yjh-Rking)
- **npm Package**: @mindfoldhq/trellis
- **Latest npm Version**: 0.3.10 (released 2026-03-12)
- **Downloads**: Not specified in reviewed sources

---

## Key Features

### 1. Auto-Injected Specs
Trellis uses a `.trellis/spec/` directory to store reusable project specifications and standards. The framework automatically injects relevant specifications into each AI session based on task context. Source: README.md — "Write conventions once in `.trellis/spec/`, then let Trellis inject the relevant context into each session instead of repeating yourself."

Specs are intended to be customized per project and can be seeded from community templates. Source: README.md — "Specs ship as empty templates by default — they are meant to be customized for your project's stack and conventions. You can fill them from scratch, or start from a community template."

### 2. Task-Centered Workflow
Tasks are stored in `.trellis/tasks/` and include PRDs, implementation context, review context, and task status. This keeps AI work structured and traceable. Source: README.md — "Keep PRDs, implementation context, review context, and task status in `.trellis/tasks/` so AI work stays structured."

Tasks support a lifecycle management model with lifecycle hooks for custom automation. Source: What's New (v0.3.6) — "task lifecycle hooks."

### 3. Parallel Agent Execution
Git worktrees enable multiple AI agents to work on separate branches simultaneously without interfering with each other's state or branches. Source: README.md — "Run multiple AI tasks side by side with git worktrees instead of turning one branch into a traffic jam." Additionally, Trellis supports "parent-child subtasks" (v0.3.6).

### 4. Project Memory via Journals
Workspace journals in `.trellis/workspace/` preserve session history and project context. Developers can configure personal journals per workspace identity. Source: README.md — "Journals in `.trellis/workspace/` preserve what happened last time, so each new session starts with real context." Installation uses the `-u your-name` flag to create `.trellis/workspace/your-name/` for personal journals and session continuity.

### 5. Team-Shared Specifications
Specs are versioned in the repository, allowing teams to review, improve, and share best practices. Source: README.md — "Specs live in the repo, so one person's hard-won workflow or rule can benefit the whole team."

### 6. Multi-Platform Support
Trellis generates platform-specific integration files for 12 AI coding platforms. Source: README.md — "Depending on the platforms you enable, Trellis also creates tool-specific integration files such as `.claude/`, `.cursor/`, `AGENTS.md`, `.agents/`, `.codex/`, `.kilocode/`, and `.kiro/`."

Supported platforms explicitly listed: Claude Code, Cursor, OpenCode, iFlow, Codex, Kilo, Kiro, Gemini CLI, Antigravity, Windsurf, Qoder, CodeBuddy. Source: README.md section on supported platforms.

### 7. Custom Template Registries
Projects can fetch specs from custom registries instead of using defaults. Source: README.md — "Fetch templates from a custom registry: `trellis init --registry https://github.com/your-org/your-spec-templates`"

---

## Technical Architecture

### Core Directory Structure

Trellis organizes project artifacts in a `.trellis/` root directory with the following layout:

```
.trellis/
├── spec/                    # Project standards, patterns, and guides
├── tasks/                   # Task PRDs, context files, and status
├── workspace/               # Journals and developer-specific continuity
├── workflow.md              # Shared workflow rules
└── scripts/                 # Utilities that power the workflow
```

Source: README.md — "How It Works" section.

The framework generates platform-specific configuration directories at the repository root:
- `.claude/` for Claude Code integration
- `.cursor/` for Cursor integration
- `.agents/` for Codex platform agents
- `.codex/` for Codex configuration
- `.kilocode/`, `.kiro/` for other platform-specific wiring

Source: CONTRIBUTING.md — "Important: When modifying `.claude/`, `.trellis/`, or `.cursor/`, check if the same changes need to be applied to `src/templates/`. The project uses its own config files, but templates are what gets installed to user projects."

### Workflow Execution Model

The workflow follows a 4-step cycle:

1. **Define standards in specs** — Write conventions, patterns, and rules once into `.trellis/spec/`.
2. **Start or refine work from a task PRD** — Create or load task definitions from `.trellis/tasks/`.
3. **Let Trellis inject the right context for the current task** — The framework automatically includes relevant specs and task context in the AI session.
4. **Use checks, journals, and worktrees to keep quality and continuity intact** — Track progress, preserve session history, maintain separate branches.

Source: README.md — "At a high level, the workflow is simple: [4 steps listed]"

### Hook System

Trellis v0.3.6 introduced "task lifecycle hooks" and "PreToolUse hook for CC v2.1.63+" (Claude Code version 2.1.63 or later). This enables custom automation at specific points in task execution. Source: What's New (v0.3.6) — "task lifecycle hooks, custom template registries (`--registry`), parent-child subtasks, fix PreToolUse hook for CC v2.1.63+."

### Implementation Languages

The codebase is distributed across:
- **TypeScript** for the CLI core and command infrastructure
- **Python** for hooks and custom automation scripts
- **Shell** for build and utility scripts

Development setup requires Node.js 18.0.0+ and pnpm for TypeScript compilation, Python 3 for hooks, and Bash for scripts. Source: CONTRIBUTING.md — "Prerequisites: Node.js 18.0.0+, pnpm, Python 3 (for hooks), Bash (for scripts)."

---

## Installation & Usage

### Global Installation

```bash
npm install -g @mindfoldhq/trellis@latest
```

Source: README.md — "Quick Start" section; npm package page.

### Project Initialization

```bash
# Basic initialization
trellis init -u your-name

# With specific platforms
trellis init --cursor --opencode --codex -u your-name
```

The `-u your-name` flag creates `.trellis/workspace/your-name/` for personal journals and session continuity. Platform flags can be mixed and matched. Current options include `--cursor`, `--opencode`, `--iflow`, `--codex`, `--kilo`, `--kiro`, `--gemini`, `--antigravity`, `--windsurf`, `--qoder`, and `--codebuddy`.

Source: README.md — "Quick Start" section explicitly listing platform flags.

### Slash Command Activation

When using Trellis with AI coding platforms, the `/trellis:start` command initializes a session by:
- Initializing developer identity
- Reading current project context
- Loading relevant guidelines

Source: AGENTS.md — "Use the `/trellis:start` command when starting a new session to: Initialize your developer identity, Understand current project context, Read relevant guidelines."

### Spec Templates and Marketplace

Teams can initialize with templates from community spec registries:

```bash
trellis init --registry https://github.com/your-org/your-spec-templates
```

Source: README.md — "Specs Templates & Marketplace" section. "Browse available templates and learn how to publish your own on the Spec Templates page."

---

## Relevance to Claude Code Development

### 1. Cross-Tool Workflow Consistency
Trellis aligns with Claude Code's context injection philosophy but extends it across 12 AI coding platforms. For Claude Code projects, Trellis can consolidate `.claude/` setup, CLAUDE.md specifications, and session memory into a standardized structure. Source: FAQ — "Those files [CLAUDE.md, AGENTS.md, .cursorrules] are useful, but they tend to become monolithic. Trellis adds structure around them: layered specs, task context, workspace memory, and platform-aware workflow wiring."

### 2. Agent Parallel Execution Pattern
Git worktree-based parallel execution directly addresses Claude Code's limitation of single-session-per-branch. Developers can run multiple independent Claude Code sessions in separate worktrees, enabling true parallel agent workflows. This is particularly relevant for implementing the kage-bunshin (shadow clone) or swarm patterns in Claude Code. Source: README.md — "Run multiple AI tasks side by side with git worktrees instead of turning one branch into a traffic jam."

### 3. Task and Plan Integration
Trellis's task PRD structure aligns with SAM (Structured Agent-Managed) task planning patterns. Teams can use `.trellis/tasks/` to define task structures equivalent to SAM task YAML, enabling seamless integration with task-centric workflows. Source: README.md — "Keep PRDs, implementation context, review context, and task status in `.trellis/tasks/` so AI work stays structured."

### 4. Multi-Agent Memory and Continuity
The workspace journal system in `.trellis/workspace/` solves the context continuity problem for teams running multiple Claude Code agents serially or in parallel. Previous session outcomes, blockers, and decisions are preserved and automatically loaded for the next agent. Source: README.md — "Journals in `.trellis/workspace/` preserve what happened last time, so each new session starts with real context."

### 5. Hook-Based Context Injection
The PreToolUse hook (v0.3.6) aligns with Claude Code's hook system and can automate context injection at critical points in tool execution. This enables sophisticated workflows without manual context management. Source: What's New (v0.3.6) — "fix PreToolUse hook for CC v2.1.63+."

---

## Limitations and Caveats

1. **Manual Spec Authoring**: Trellis provides empty spec templates by default. Teams must author or generate specs to derive benefit from the framework. Source: README.md — "Specs ship as empty templates by default — they are meant to be customized for your project's stack and conventions."

2. **Git Worktree Complexity**: While parallel execution via git worktrees solves branch contention, it introduces operational complexity around worktree lifecycle management (creation, cleanup, state tracking). This is not documented in the reviewed sources as a mitigation or automated feature.

3. **Multi-Platform Synchronization**: Supporting 12 platforms requires careful coordination of spec injection and hook behavior across platform-specific entry points. Inconsistencies in hook behavior or timing between platforms are not documented in reviewed sources.

4. **TypeScript/Node.js Dependency**: The CLI is written in TypeScript and requires Node.js 18.0.0+. Projects using Python-only or other runtime environments must maintain a Node.js installation for Trellis CLI operations. Source: CONTRIBUTING.md — "Prerequisites: Node.js 18.0.0+"

5. **Maturity and Stability**: Current version is 0.3.10, indicating active development. The API and file format are not yet at 1.0 stability. Source: npm package — latest version 0.3.10; GitHub repository shows frequent updates to patch versions (v0.3.5, v0.3.6 released recently).

6. **Task Lifecycle Hook Documentation**: While task lifecycle hooks are listed as available (v0.3.6), specific hook names, signatures, and execution timing are not documented in reviewed sources. Custom hook implementation requires consultation with project documentation or source code.

---

## References

1. GitHub Repository: <https://github.com/mindfold-ai/Trellis> — README.md (accessed 2026-04-06)
2. GitHub Repository: <https://github.com/mindfold-ai/Trellis/blob/main/CONTRIBUTING.md> — Development guidelines and project structure (accessed 2026-04-06)
3. GitHub Repository: <https://github.com/mindfold-ai/Trellis/blob/main/AGENTS.md> — AI assistant instructions (accessed 2026-04-06)
4. Official Documentation: <https://docs.trytrellis.app> — Architecture and task management sections (accessed 2026-04-06)
5. npm Package: @mindfoldhq/trellis — Version 0.3.10 released 2026-03-12 (accessed 2026-04-06)
6. GitHub Releases: <https://github.com/mindfold-ai/Trellis/releases> — Release history (accessed 2026-04-06)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [oh-my-claudecode.md](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | 32-agent TypeScript orchestration framework sharing Claude Code platform and multi-agent session management |
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | production-scale multi-agent orchestration with Sisyphus/Atlas/Prometheus architecture and demand-scoped MCP |
| [superpowers.md](./superpowers.md) | agent-frameworks | agentic skills framework and methodology with context injection and agent coordination patterns |
| [everything-claude-code.md](./everything-claude-code.md) | agent-frameworks | comprehensive harness with 16 agents, 65+ skills, and hook-based automation across multiple platforms |
| [worktrunk.md](../developer-tools/worktrunk.md) | developer-tools | git worktree management CLI enabling parallel AI agent workflows without branch contention |
| [gastown.md](../research-agent-patterns/gastown.md) | research-agent-patterns | multi-agent workspace manager using tmux transport and Dolt ledger for coordinating 20-50+ Claude Code sessions |
| [takt.md](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined multi-agent workflow engine with state machine transitions and faceted prompting for agent coordination |
| [claude-codex-settings.md](../claude-code-plugins/claude-codex-settings.md) | claude-code-plugins | battle-tested Claude Code plugin ecosystem with 17 plugins and multi-LLM backend configuration |
| [omnigent](./omnigent.md) | agent-frameworks | referenced by omnigent (agent-frameworks) |

---

## Freshness Tracking

**Last Review**: 2026-04-06
**Next Review**: 2026-07-06 (3 months)

### Confidence Assessment

| Section | Confidence | Notes |
|---------|------------|-------|
| Identity/Metadata | high | GitHub repository metadata and npm package verified; version 0.3.10 confirmed. |
| Features | high | All features extracted from official README.md and What's New release notes. |
| Technical Architecture | high | Directory structure and workflow model extracted verbatim from README.md; hook system from release notes. |
| Installation & Usage | high | Installation commands and initialization process verified against README.md and npm package. |
| Relevance to Claude Code | medium | Relevance assessment based on feature alignment with Claude Code patterns; not explicitly confirmed by Trellis documentation. |
| Limitations | medium | Limitations extracted from README.md and inferred from maturity level (0.3.10); additional caveats not documented in reviewed sources. |

**Confidence Rationale**: All primary claims trace to official documentation (README.md, CONTRIBUTING.md, AGENTS.md, docs.trytrellis.app). Release notes confirm feature presence and timing. The "Relevance to Claude Code" section is medium-confidence because it represents reasoned assessment of feature alignment rather than explicit Trellis documentation about Claude Code integration. Limitations section is medium-confidence where sourced from README.md but includes inferences about undocumented complexity (e.g., git worktree lifecycle management).
