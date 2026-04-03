---
title: oh-my-claudecode
subtitle: Multi-agent orchestration system for Claude Code
category: agent-orchestration
resource_type: plugin
primary_language: TypeScript
author: Yeachan Heo
license: MIT
---

## Overview

**oh-my-claudecode** (branded as **OMC**; published to npm as `oh-my-claude-sisyphus`) is a multi-agent orchestration system for Claude Code that enables coordinated execution of 32 specialized agents across different cognitive domains. The plugin provides a zero-configuration interface where users describe tasks in natural language, and OMC automatically routes work to appropriate agents, manages execution parallelism, and enforces completion guarantees.

**Purpose**: Eliminate learning curve for Claude Code orchestration by providing intelligent defaults, automatic agent selection, skill composition, and persistent execution modes that complete tasks fully.

**Core value**: "Zero learning curve. Maximum power." — abstracts away multi-agent complexity while preserving full control via explicit keywords and team syntax.

---

## Problem Addressed

Claude Code users face three coordination challenges:

1. **Agent Selection Friction** — Which agent suits this task? Manual routing overhead for each request.
2. **Execution Incompleteness** — Multi-step workflows stall when agents succeed partially. No built-in retry/verification loop.
3. **Knowledge Reuse Barriers** — Solutions to recurring problems (auth bugs, proxy crashes, performance tuning) must be rediscovered each session. No pattern capture mechanism.

OMC solves these by:

- **Automatic agent routing** via task classification and model tier selection (Haiku for simple, Opus for complex reasoning)
- **Persistent execution modes** (`ralph`) that loop verify-fix cycles until tasks complete
- **Skill learning system** that extracts reusable debugging patterns into portable files, auto-injected into future sessions matching trigger keywords

---

## Key Statistics

| Metric | Value | Date |
|--------|-------|------|
| GitHub Stars | 13,995 | 2026-03-28 |
| GitHub Forks | 905 | 2026-03-28 |
| Latest Release | v4.9.1 | (current) |
| Open Issues | 22 | 2026-03-28 |
| Repository Created | 2026-01-09 | (3 months old as of research date) |
| Last Updated | 2026-03-28 | (current) |
| NPM Package Name | `oh-my-claude-sisyphus` | (published as) |
| Primary Language | TypeScript | (100% type-safe) |
| License | MIT | (open source) |

**npm metrics**: `oh-my-claude-sisyphus` published to npm with automatic version bumping on each commit.

---

## Key Features

### 1. Team Mode (Canonical Orchestration Surface)

Starting in **v4.1.7**, Team is the primary multi-agent interface. Runs as a staged pipeline:

```
team-plan → team-prd → team-exec → team-verify → team-fix (loop)
```

**Activation:**
```bash
/team 3:executor "fix all TypeScript errors"
```

Requires Claude Code native teams enabled in `~/.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### 2. CLI Worker Runtime (v4.4.0+)

Spawns real tmux worker panes running local provider CLIs (Claude, Codex, Gemini):

```bash
omc team 2:codex "review auth module for security"
omc team 2:gemini "redesign UI for accessibility"
omc team 1:claude "implement payment flow"
```

Workers spawn on-demand and terminate when tasks complete (no idle resource usage). Supports mixed-model coordination via `/ccg` skill:

```bash
/ccg Review this PR — architecture (Codex) and UI components (Gemini)
```

### 3. 32 Specialized Agents

Organized by complexity tier and cognitive domain:

| Tier | Model | Use For |
|------|-------|---------|
| **LOW** | Haiku | Quick lookups, simple operations, cross-checks |
| **MEDIUM** | Sonnet | Standard implementations, code editing |
| **HIGH** | Opus | Complex reasoning, architecture, design |

Domains include: architecture, research, design, testing, data science, code review, documentation.

### 4. Smart Model Routing

Automatic tier selection based on task classification:

- **Simple tasks** → Haiku (cost optimization)
- **Standard implementations** → Sonnet (reliability)
- **Complex reasoning** → Opus (architectural/design work)

Saves 30-50% on tokens through intelligent model assignment.

### 5. Skill System

**Three-layer skill composition** with scoped priority:

#### Project Scope (`.omc/skills/`)
- Shared with team
- Version-controlled
- **Higher priority** (overrides user scope)

#### User Scope (`~/.omc/skills/`)
- Applies to all projects
- Persistent across sessions
- **Lower priority** (fallback)

**Example project-scoped skill:**
```yaml
---
name: Fix Proxy Crash
description: aiohttp proxy crashes on ClientDisconnectedError
triggers: ["proxy", "aiohttp", "disconnected"]
source: extracted
---
Wrap handler at server.py:42 in try/except ClientDisconnectedError...
```

#### Skill Learning (`/learner`)
Auto-extracts reusable patterns with strict quality gates. Matching skills auto-inject into context when relevant keywords detected — no manual recall needed.

### 6. Execution Modes

| Mode | Pipeline | Use For |
|------|----------|---------|
| **Team** | team-plan → team-prd → team-exec → team-verify → team-fix | Coordinated agents on shared task list |
| **omc team (CLI)** | tmux CLI workers (real claude/codex/gemini processes) | Codex/Gemini tasks; on-demand spawn |
| **ccg** | `/ask codex` + `/ask gemini` + Claude synthesis | Mixed backend+UI work |
| **Autopilot** | Single lead agent orchestration | End-to-end feature work, minimal ceremony |
| **Ultrawork** | Maximum parallelism (non-team) | Burst parallel fixes/refactors |
| **Ralph** | Persistent mode with verify-fix loops | Tasks that must complete fully (no silent partials) |
| **Pipeline** | Sequential, staged processing | Multi-step transformations with strict ordering |
| **Ultrapilot** | Deprecated (autopilot alias) | Backward compatibility |

### 7. Magic Keywords (Power User Shortcuts)

Optional natural-language triggers:

| Keyword | Effect | Example |
|---------|--------|---------|
| `team` | Team orchestration (explicit) | `/team 3:executor "fix errors"` |
| `omc team` | tmux CLI workers | `omc team 2:codex "security review"` |
| `ccg` | Codex + Gemini synthesis | `/ccg review PR` |
| `autopilot` | Autonomous execution | `autopilot: build todo app` |
| `ralph` | Persistence mode | `ralph: refactor auth` |
| `ulw` | Maximum parallelism | `ulw fix all errors` |
| `ralplan` | Iterative planning consensus | `ralplan this feature` |
| `deep-interview` | Socratic requirements clarification | `deep-interview "vague idea"` |
| `deepsearch` | Codebase-focused search | `deepsearch for auth middleware` |
| `ultrathink` | Deep reasoning mode | `ultrathink about architecture` |
| `cancelomc`, `stopomc` | Stop active OMC modes | `stopomc` |

**Notes:**
- `ralph` automatically includes `ultrawork` parallelism
- `swarm` keyword removed; migrate to `/team` syntax
- `plan this` / `plan the` triggers removed; use `ralplan` or explicit `/oh-my-claudecode:omc-plan`

### 8. Skills Learning & Extraction

The `/learner` command extracts hard-won debugging knowledge into portable skill files:

- Auto-injects when trigger keywords match
- Strict quality gates to prevent noise
- Reusable across projects

**Manage skills via:** `/skill list | add | remove | edit | search`

### 9. Utilities & Integrations

#### Provider Advisor (`omc ask`)
Run local provider CLIs and save markdown artifacts:
```bash
omc ask claude "review migration plan"
omc ask codex --prompt "identify architecture risks"
omc ask gemini --prompt "propose UI ideas"
```

#### Rate Limit Wait
Auto-resume Claude Code when rate limits reset:
```bash
omc wait               # Check status
omc wait --start       # Enable auto-resume daemon
omc wait --stop        # Disable daemon
```

#### Monitoring & Observability
- HUD statusline showing orchestration metrics in real-time
- Session summaries at `.omc/sessions/*.json`
- Replay logs at `.omc/state/agent-replay-*.jsonl`

#### Notification Tags (Telegram/Discord/Slack)
Configure team notifications when sessions stop:
```bash
omc config-stop-callback telegram --enable --token <bot_token> --chat <id> --tag-list "@alice,bob"
omc config-stop-callback discord --enable --webhook <url> --tag-list "@here,role:987654321098765432"
```

#### OpenClaw Integration
Forward Claude Code events to OpenClaw gateway for automated responses:
```bash
/oh-my-claudecode:configure-notifications
# → Type "openclaw" → select "OpenClaw Gateway"
```

Supports hooks: `session-start`, `stop`, `keyword-detector`, `ask-user-question`, `pre-tool-use`, `post-tool-use`.

---

## Technical Architecture

### Core Components

#### 1. Skill Activation System

Input → Skill Detection → Execution

The orchestrator detects task types from user input via `CLAUDE.md` auto-routing rules:

```
User Input: "ultrawork refactor the API"
      ↓
Skill Detection: Task Type = Implementation + Multi-file + Parallel OK
      ↓
Skills Activated: ultrawork + default + git-master
      ↓
Execution: Parallel agents launched with atomic commits
```

#### 2. Agent Routing

Task classification determines model tier and agent selection:

```typescript
Task(
  subagent_type="oh-my-claudecode:executor",
  model="sonnet",
  prompt="Implement feature..."
)
```

Categories auto-select: model tier, temperature, thinking budget.

#### 3. Skill Composition (Layered)

**Guarantee Layer** (optional)
↓
**Enhancement Layer** (0-N skills)
- ultrawork (parallel execution)
- git-master (commit semantics)
- frontend-ui-ux (visual polish)
↓
**Execution Layer** (primary skill)
- default (build/implement)
- orchestrate (coordinate)
- planner (plan)

#### 4. Team Pipeline Stages

1. **team-plan** — Initial task decomposition and planning
2. **team-prd** — Product requirements/design phase
3. **team-exec** — Agent execution and implementation
4. **team-verify** — Verification and testing
5. **team-fix** — Loop on failures until completion

#### 5. State Management

- **Project scope**: `.omc/` directory (local to worktree)
- **Centralized state** (optional): `OMC_STATE_DIR` env var preserves state across worktree deletions
- **Session artifacts**: `.omc/sessions/*.json`, `.omc/state/agent-replay-*.jsonl`

#### 6. Hook System

OMC registers Node.js hooks in Claude Code settings to intercept:
- Skill activation patterns (keyword detection)
- Task execution (model routing, parallelism)
- Completion verification (ralph persistent mode)
- Skill learning triggers (pattern extraction)

---

## Installation & Usage

### Installation (Plugin Method — Required)

The only supported installation method is via Claude Code plugin system:

```bash
# Step 1: Add marketplace
/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode

# Step 2: Install plugin
/plugin install oh-my-claudecode
```

Integrates directly with Claude Code's plugin system via Node.js hooks.

**Note**: Direct npm/bun global installs are **not supported**. The plugin system handles all installation and setup.

### Setup (Project or Global Scope)

#### Project-Scoped Configuration (Recommended)
```bash
/oh-my-claudecode:omc-setup --local
```
Creates `./.claude/CLAUDE.md` in current project. Configuration applies only to this project.

#### Global Configuration
```bash
/oh-my-claudecode:omc-setup
```
Creates `~/.claude/CLAUDE.md` globally. Configuration applies to all projects. **Warning**: Overwrites existing `~/.claude/CLAUDE.md`.

### Requirements

- **Claude Code** CLI installed
- **One of**:
  - Claude Max/Pro subscription (recommended for individuals)
  - Anthropic API key (`ANTHROPIC_API_KEY` environment variable)
- **Node.js** >=20.0.0
- **tmux** (for `omc team` and rate-limit detection features)

### Platform & tmux Support

| Platform | tmux Provider | Install |
|----------|---------------|---------|
| macOS | tmux | `brew install tmux` |
| Ubuntu/Debian | tmux | `sudo apt install tmux` |
| Fedora | tmux | `sudo dnf install tmux` |
| Arch | tmux | `sudo pacman -S tmux` |
| Windows | psmux (native) | `winget install psmux` |
| Windows (WSL2) | tmux (inside WSL) | `sudo apt install tmux` |

### Quick Start

```bash
# Step 1: Install plugin
/plugin install oh-my-claudecode

# Step 2: Setup (choose project or global)
/omc-setup

# Step 3: Use Team (canonical interface)
/team 3:executor "build a REST API for tasks"

# Or use magic keywords (power users)
autopilot: build a REST API for tasks
ralph: refactor authentication module
ulw fix all TypeScript errors
```

### Basic Examples

#### Team-Based Orchestration (Recommended)
```bash
/team 3:executor "implement user authentication"
/team 2:codex "security audit of payment module"
/team 1:claude --agent-prompt planner "design database schema"
```

#### Magic Keywords
```bash
autopilot: build a task management app
ralph: refactor legacy auth system
ulw fix all linting errors
deep-interview "I want to build a note-taking app"
deepsearch for auth middleware
ultrathink about this architecture
```

#### CLI Worker Runtime
```bash
omc team 2:codex "architecture review"
omc team 2:gemini "UI/UX redesign"
omc team status auth-review
omc team shutdown auth-review
```

#### Provider Advisor
```bash
omc ask claude "review this migration"
omc ask codex --prompt "identify risks"
omc ask gemini --prompt "design ideas"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OMC_STATE_DIR` | _(unset)_ | Centralized state directory (preserves across worktree deletions) |
| `OMC_BRIDGE_SCRIPT` | _(auto-detect)_ | Python bridge script path |
| `OMC_PARALLEL_EXECUTION` | `true` | Enable/disable parallel agent execution |
| `OMC_CODEX_DEFAULT_MODEL` | _(provider default)_ | Default model for Codex workers |
| `OMC_GEMINI_DEFAULT_MODEL` | _(provider default)_ | Default model for Gemini workers |
| `OMC_LSP_TIMEOUT_MS` | `15000` | LSP request timeout (ms) |
| `DISABLE_OMC` | _(unset)_ | Set to any value to disable all hooks |
| `OMC_SKIP_HOOKS` | _(unset)_ | Comma-separated list of hook names to skip |
| `OMC_OPENCLAW` | `0` | Enable OpenClaw integration |
| `OMC_OPENCLAW_DEBUG` | `0` | Enable OpenClaw debug logging |

### Configuration Precedence

```
./.claude/CLAUDE.md (project)  →  Overrides  →  ~/.claude/CLAUDE.md (global)
```

Project-scoped configuration takes precedence over global.

### Updating

**Via marketplace (recommended):**
```bash
/plugin marketplace update omc
/omc-setup
```

**Via npm (legacy):**
```bash
npm i -g oh-my-claude-sisyphus@latest
```

### Troubleshooting

**Check plugin health:**
```bash
/omc-doctor
```

Clears old plugin cache and validates installation.

---

## Relevance to Claude Code Development

### 1. Multi-Agent Coordination Patterns
OMC demonstrates production-grade orchestration for 32 agents across distinct cognitive domains (architecture, code review, testing, data science). The skill composition system shows how to layer capabilities without combinatorial explosion. Directly applicable to Claude Code development workflows requiring coordination across specialized agents.

### 2. Model Routing & Cost Optimization
The smart tier selection (Haiku/Sonnet/Opus) by task complexity achieves 30-50% token savings. This pattern is essential for sustainable multi-agent systems at scale. OMC's implementation shows routing rules, model selection heuristics, and cost tracking infrastructure.

### 3. Persistent Execution & Verification Loops
Ralph mode and the team-verify-fix pipeline address a core failure mode: partial task completion. Rather than hoping agents succeed, OMC implements explicit verify-fix loops. Applicable to any long-running Claude Code workflow requiring guaranteed completion.

### 4. Skill Reuse & Pattern Learning
The `/learner` command auto-extracts debugging patterns into reusable skills, solving the "how do I remember this fix next time?" problem. Shows how to build knowledge capture into orchestration systems without heavyweight knowledge management infrastructure.

### 5. Hooks & Plugin Integration
OMC's Node.js hook system integrates deeply with Claude Code, intercepting task execution, keyword detection, and completion verification. Exemplifies production plugin patterns for tool use, state management, and multi-agent coordination.

### 6. Real-Time Observability
HUD statusline, session summaries, and replay logs enable post-hoc debugging of multi-agent workflows. Critical for understanding what went wrong in complex orchestration.

### 7. Cross-Provider Orchestration
The CLI worker runtime (tmux-based Codex/Gemini integration) and `/ccg` skill show patterns for coordinating across different LLM providers without tight coupling.

---

## Limitations and Caveats

### 1. Claude Code Dependency
OMC requires Claude Code CLI and either a Claude Max/Pro subscription or Anthropic API key. Cannot work with other IDE integrations or standalone agent frameworks.

### 2. Node.js 20+ Requirement
Plugin system requires Node.js >=20.0.0. Older Node environments will fail installation. No fallback to pure Python or Go implementations.

### 3. tmux Dependency for Advanced Features
`omc team`, rate-limit detection, and CLI worker runtime require tmux. Windows users must use psmux (native Windows tmux) or WSL2. Systems without tmux support cannot access these features.

### 4. Plugin-Only Installation
Direct npm/bun global installs are **not supported**. All users must install via Claude Code plugin marketplace. This prevents standalone CLI usage or integration into non-Claude Code environments.

### 5. Configuration Overwrite Risk
Global setup with `/omc-setup` completely overwrites `~/.claude/CLAUDE.md` without backup. Users with existing global CLAUDE.md configuration must use project-scoped setup (`--local`) to avoid data loss.

### 6. Skill Learning Quality Gates
The `/learner` command uses "strict quality gates" to prevent noisy skill extraction, but documentation does not detail what constitutes "strict" or how to configure thresholds. May miss valid patterns or extract overly specific ones.

### 7. Legacy Compatibility
Removed keywords (`swarm`, `plan this`, `plan the`) break existing prompts. Migration guide recommends replacing with `/team` syntax, but existing scripts/automation must be updated manually.

### 8. LSP Timeout Hardcoding
Default `OMC_LSP_TIMEOUT_MS` of 15 seconds may be insufficient for large repositories or slow language servers. Requires manual environment variable tuning — no adaptive timeout logic.

### 9. State Directory Complexity
Centralized state via `OMC_STATE_DIR` introduces complexity: two possible locations (legacy `.omc/` and centralized), project identification via git remote hash, and fallback to directory path hash. Migration path unclear for users with accumulated state.

### 10. Incomplete Documentation on Architecture
The ARCHITECTURE.md file covers overview and skill composition but does not detail:
- Internal agent selection heuristics
- Model routing decision tree
- Skill priority resolution when conflicts occur
- Error handling and retry strategies in verify-fix loops

**Not documented in reviewed sources:**
- Cost per execution (number of agent calls, typical token usage)
- Latency profiles for different execution modes (Team vs. Autopilot)
- Failure modes and recovery guarantees in ralph persistent mode
- Performance impact of skill learning on session latency

---

## References

- **Official Repository**: <https://github.com/Yeachan-Heo/oh-my-claudecode> (accessed 2026-03-28)
- **Main README**: <https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/README.md> (accessed 2026-03-28)
- **Architecture Documentation**: <https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/docs/ARCHITECTURE.md> (accessed 2026-03-28)
- **Reference Documentation**: <https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/docs/REFERENCE.md> (accessed 2026-03-28)
- **Website**: <https://yeachan-heo.github.io/oh-my-claudecode-website> (accessed 2026-03-28)
- **npm Package**: <https://www.npmjs.com/package/oh-my-claude-sisyphus> (published as `oh-my-claude-sisyphus`, branded as `oh-my-claudecode`)
- **GitHub API Response** (retrieved 2026-03-28): stars=13,995, forks=905, language=TypeScript, created=2026-01-09, updated=2026-03-28, open_issues=22
- **License File**: MIT License, Copyright (c) 2025 Yeachan Heo
- **NPM Badge**: v4.9.1 current release

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale Claude Code orchestration with category-based model routing and Sisyphus/Atlas/Prometheus multi-agent architecture; OMC shares identical goal and model switching strategy |
| [compound-engineering-plugin.md](../research-agent-patterns/compound-engineering-plugin.md) | research-agent-patterns | Claude Code plugin with 27 agents and Plan/Work/Review/Compound workflow; parallel pattern to OMC's team mode pipeline |
| [gastown.md](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent workspace manager for coordinating 20-50+ Claude Code sessions; overlapping execution model with OMC's team and CLI worker modes |
| [everything-claude-code.md](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Comprehensive 16-agent harness with 65+ skills and hook-based automation; shares OMC's skill layering and execution parallelism patterns |
| [claw-loop.md](../research-agent-patterns/claw-loop.md) | research-agent-patterns | Autonomous orchestration via tmux + cron with supervisor-worker pattern; foundational pattern for OMC's Ralph mode and persistent execution loops |
| [ollama-subagents-web-search-claude-code.md](../research-agent-patterns/ollama-subagents-web-search-claude-code.md) | research-agent-patterns | Ollama native subagents for Claude Code with parallel task isolation; shares OMC's model-agnostic agent spawning and context isolation approach |

---

## Freshness Tracking

**Last Researched**: 2026-03-28
**Next Review**: 2026-06-28 (3 months)

### Confidence Summary

| Section | Level | Rationale |
|---------|-------|-----------|
| **Identity/Metadata** | high | Official repo, package.json, LICENSE all accessed; version and dates from primary sources |
| **Key Statistics** | high | GitHub API response (2026-03-28); star count, forks, language, creation date, last update all verified |
| **Key Features** | high | Extracted from official README, ARCHITECTURE.md, REFERENCE.md; all feature descriptions have source quotes |
| **Technical Architecture** | high | ARCHITECTURE.md provides explicit component descriptions, data flow diagrams (ASCII), and skill composition model |
| **Installation & Usage** | high | Installation steps, requirements, and configuration from official docs; command examples verified against README |
| **Limitations** | medium | Identified from documentation gaps (what is NOT documented) and explicit caveats in README; no user-reported issues consulted |

### Changes from Previous Entry

(First entry for this resource — no previous version exists.)

### Known Gaps

1. **Internal Agent Selection Algorithm**: Documentation does not expose the decision tree for routing tasks to specific agents. Black box from user perspective.
2. **Cost Analysis**: No published token usage metrics, cost per execution, or benchmarks comparing execution modes.
3. **Failure Mode Taxonomy**: Ralph mode and verify-fix loops are described but failure conditions and recovery strategies not detailed.
4. **Scalability Limits**: No documented limits on number of concurrent agents, state directory size, or skill repository size.
5. **Community Patterns**: No examples of how users integrate OMC with existing CI/CD systems, version control workflows, or team development practices.
