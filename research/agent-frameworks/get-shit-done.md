# Get Shit Done (GSD)

**Research Date**: 2026-02-01
**Source URL**: https://github.com/glittercowboy/get-shit-done
**npm Package**: https://www.npmjs.com/package/get-shit-done-cc
**Version at Research**: v1.11.1
**License**: MIT

---

## Overview

Get Shit Done (GSD) is a lightweight meta-prompting, context engineering, and spec-driven development system for Claude Code, OpenCode, and Gemini CLI. It solves "context rot" - the quality degradation that occurs as Claude fills its context window - by implementing multi-agent orchestration with fresh context per task.

Created by solo developer TACHES, GSD provides a structured workflow that transforms vibe coding into reliable, production-quality development. The system handles context engineering, XML prompt formatting, subagent orchestration, and state management behind a simple command interface.

---

## Problem Addressed

| Problem | GSD Solution |
|---------|--------------|
| Context rot degrades quality as context fills | Fresh 200k token context per execution plan |
| Vibecoding produces inconsistent, fragile code | Spec-driven development with verification loops |
| Enterprise tools add ceremony (sprints, Jira, retrospectives) | Minimal commands, no enterprise roleplay |
| No persistent state across sessions | File-based state management (STATE.md, ROADMAP.md) |
| Plans too large for reliable execution | Atomic task plans with XML structure |
| Unclear git history from AI-generated code | One surgical commit per completed task |
| Manual context loading per session | Auto-loaded project files (PROJECT.md, research/) |
| Quality varies with context window fullness | Parallel subagent execution preserves main context |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 10,193 | 2026-02-01 |
| GitHub Forks | 989 | 2026-02-01 |
| Open Issues | 192 | 2026-02-01 |
| npm Package | get-shit-done-cc | - |
| npm Latest Version | 1.11.1 | 2026-02-01 |
| Contributors | 10+ | 2026-02-01 |
| Primary Language | JavaScript | - |
| Repository Created | 2025-12-14 | - |
| Last Updated | 2026-02-01 | - |

---

## Key Features

### Core Workflow Commands

| Command | Purpose |
|---------|---------|
| `/gsd:new-project` | Full initialization: questions, research, requirements, roadmap |
| `/gsd:discuss-phase [N]` | Capture implementation decisions before planning |
| `/gsd:plan-phase [N]` | Research + plan + verify for a phase |
| `/gsd:execute-phase <N>` | Execute all plans in parallel waves, verify when complete |
| `/gsd:verify-work [N]` | Manual user acceptance testing |
| `/gsd:complete-milestone` | Archive milestone, tag release |
| `/gsd:new-milestone [name]` | Start next version cycle |

### Multi-Agent Architecture

GSD implements 11 specialized agents:

| Agent | Responsibility |
|-------|---------------|
| gsd-codebase-mapper | Analyze existing codebase architecture |
| gsd-project-researcher | Research domain before project planning |
| gsd-phase-researcher | Research specific phase implementation |
| gsd-research-synthesizer | Aggregate research findings |
| gsd-planner | Create atomic XML task plans |
| gsd-plan-checker | Verify plans achieve phase goals |
| gsd-executor | Implement tasks in fresh context |
| gsd-verifier | Confirm deliverables match goals |
| gsd-debugger | Systematic debugging with state persistence |
| gsd-integration-checker | Check cross-module integration |
| gsd-roadmapper | Generate phase roadmaps |

### Context Engineering Files

| File | Purpose | Size Limits |
|------|---------|-------------|
| PROJECT.md | Project vision, always loaded | Core context |
| research/ | Ecosystem knowledge (stack, features, architecture) | Reference |
| REQUIREMENTS.md | Scoped v1/v2 requirements with phase traceability | Planning |
| ROADMAP.md | Progress tracking, completed phases | State |
| STATE.md | Decisions, blockers, position across sessions | Memory |
| PLAN.md | Atomic task with XML structure and verification | Execution |
| SUMMARY.md | Execution results committed to history | Archive |
| CONTEXT.md | Phase-specific implementation preferences | Per-phase |

### XML Task Format

Every plan uses structured XML optimized for Claude:

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>
    Use jose for JWT (not jsonwebtoken - CommonJS issues).
    Validate credentials against users table.
    Return httpOnly cookie on success.
  </action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200 + Set-Cookie</verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</task>
```

### Model Profiles

Three configurable profiles for quality vs cost tradeoffs:

| Profile | Planning | Execution | Verification |
|---------|----------|-----------|--------------|
| quality | Opus | Opus | Sonnet |
| balanced (default) | Opus | Sonnet | Sonnet |
| budget | Sonnet | Sonnet | Haiku |

### Multi-Runtime Support

| Runtime | Install Location |
|---------|-----------------|
| Claude Code | `~/.claude/` (global) or `./.claude/` (local) |
| OpenCode | `~/.config/opencode/` |
| Gemini CLI | `~/.gemini/` |

---

## Technical Architecture

### Orchestration Pattern

Every stage uses the same pattern: a thin orchestrator spawns specialized agents, collects results, and routes to the next step.

```text
ORCHESTRATOR (Main Context ~30-40%)
    |
    +-- Spawns --> RESEARCHER agents (parallel, fresh context)
    |
    +-- Collects results
    |
    +-- Spawns --> PLANNER agent (fresh context)
    |
    +-- Validates --> CHECKER agent (verification loop)
    |
    +-- Spawns --> EXECUTOR agents (parallel waves, fresh 200k each)
    |
    +-- Spawns --> VERIFIER agent (goal confirmation)
```

The orchestrator never does heavy lifting. Work happens in fresh subagent contexts, keeping the main session fast and responsive.

### Parallel Execution Waves

Plans are grouped into waves based on dependencies:

1. Wave 1: Independent tasks run in parallel
2. Wave 2: Tasks depending on Wave 1 outputs
3. Wave N: Sequential chains resolved

Each executor gets a fresh 200k token context purely for implementation.

### Atomic Git Commits

Each task produces its own commit immediately after completion:

```text
abc123f docs(08-02): complete user registration plan
def456g feat(08-02): add email confirmation flow
hij789k feat(08-02): implement password hashing
lmn012o feat(08-02): create registration endpoint
```

Benefits: git bisect locates failures, tasks are independently revertable, clear history for future Claude sessions.

### Git Branching Strategies

| Strategy | Behavior |
|----------|----------|
| none (default) | Commits to current branch |
| phase | Creates branch per phase, merges at completion |
| milestone | Creates branch for entire milestone |

---

## Installation and Usage

### Quick Start

```bash
# Interactive install
npx get-shit-done-cc

# Non-interactive options
npx get-shit-done-cc --claude --global   # Claude Code, global
npx get-shit-done-cc --opencode --global # OpenCode, global
npx get-shit-done-cc --gemini --global   # Gemini CLI, global
npx get-shit-done-cc --all --global      # All runtimes
```

### Verify Installation

```text
/gsd:help
```

### Update to Latest

```bash
npx get-shit-done-cc@latest
```

### Recommended Usage

```bash
claude --dangerously-skip-permissions
```

Stopping to approve `date` and `git commit` 50 times defeats the purpose of automation.

### Workflow Example

```text
# New project
/gsd:new-project

# For each phase
/gsd:discuss-phase 1      # Capture implementation preferences
/gsd:plan-phase 1         # Research + create verified plans
/gsd:execute-phase 1      # Parallel execution with fresh contexts
/gsd:verify-work 1        # User acceptance testing

# Complete milestone
/gsd:complete-milestone
/gsd:new-milestone        # Start next version
```

### Brownfield Projects

```text
/gsd:map-codebase         # Analyze existing codebase first
/gsd:new-project          # Then initialize with awareness
```

---

## Relevance to Claude Code Development

### Applicable Patterns

1. **Fresh Context per Task**: Spawning subagents with isolated 200k context prevents quality degradation from context pollution - directly applicable to skill execution patterns

2. **File-Based State Management**: Using markdown files (STATE.md, ROADMAP.md) for persistent state across sessions provides a reliable pattern for long-running workflows

3. **XML Task Structures**: Structured XML with explicit `<action>`, `<verify>`, `<done>` fields improves Claude's task comprehension and completion accuracy

4. **Orchestrator-Worker Separation**: Thin orchestrators that spawn specialized workers preserves main context while enabling complex workflows

5. **Model Profile Configuration**: Quality/balanced/budget profiles demonstrate practical cost/quality tradeoff management for multi-agent systems

6. **Atomic Commits per Task**: One commit per completed task creates traceable, revertable git history ideal for AI-generated code

7. **Verification Loops**: Plan-checker and verifier agents create feedback loops that catch errors before they compound

### Integration Opportunities

| Feature | Integration Path |
|---------|-----------------|
| Agent definitions | Study `agents/*.md` for specialized agent prompt patterns |
| Command structure | `commands/gsd/*.md` demonstrates slash command organization |
| Context files | Adopt PROJECT.md, STATE.md patterns for skill workflows |
| XML task format | Standardize task specifications across claude_skills plugins |
| Model profiles | Implement configurable quality levels in agent orchestration |

### Key Differentiators from Similar Tools

| Feature | GSD | Compound Engineering | Task Master |
|---------|-----|---------------------|-------------|
| Primary Focus | Context engineering | Plan/Work/Review cycle | PRD parsing |
| Agent Count | 11 specialized | 27 agents | MCP tools |
| Parallel Execution | Yes, wave-based | Yes, 14 review agents | Sequential |
| Context Management | Fresh per task | Unknown | Selective tool loading |
| File State | STATE.md + ROADMAP.md | docs/solutions/ | Task JSON |

---

## References

1. **GitHub Repository** - https://github.com/glittercowboy/get-shit-done (accessed 2026-02-01)
2. **npm Package** - https://www.npmjs.com/package/get-shit-done-cc (accessed 2026-02-01)
3. **README Documentation** - https://raw.githubusercontent.com/glittercowboy/get-shit-done/main/README.md (accessed 2026-02-01)
4. **Agent Definitions** - https://github.com/glittercowboy/get-shit-done/tree/main/agents (accessed 2026-02-01)
5. **Command Definitions** - https://github.com/glittercowboy/get-shit-done/tree/main/commands/gsd (accessed 2026-02-01)
6. **Discord Community** - https://discord.gg/5JJgD5svVS (referenced in README)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-02-01 |
| Version at Verification | v1.11.1 |
| Stars at Verification | 10,193 |
| Forks at Verification | 989 |
| Next Review Recommended | 2026-05-01 |
