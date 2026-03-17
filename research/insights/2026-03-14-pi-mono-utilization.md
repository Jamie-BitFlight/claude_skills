# Utilization Assessment: Pi Monorepo

**Research entry**: ./research/agent-frameworks/pi-mono.md
**Generated**: 2026-03-14
**Assessment result**: No suitable local callers identified

---

## Integration Surfaces Found

Pi-mono documents **three callable surfaces**:

| Surface Type | Details | Examples |
|---|---|---|
| **NPM Packages** | Seven TypeScript packages in @mariozechner namespace | `@mariozechner/pi-ai`, `@mariozechner/pi-agent-core`, `@mariozechner/pi-coding-agent` |
| **TypeScript SDK** | Library API for Agent runtime, LLM abstraction, TUI/web components | `new Agent({ systemPrompt: "..." })`, `getModel("anthropic", "claude-sonnet-...")` |
| **CLI Tool** | Interactive coding agent CLI with extensibility | `npm install -g @mariozechner/pi-coding-agent && pi` |

---

## Candidate Local Systems Evaluated

### 1. Agent: `typescript-pro`

**File**: `./.claude/agents/typescript-pro.md`

**Role**: Senior TypeScript developer specializing in type-first development, tsconfig optimization, and build tooling.

**Potential fit**: ❌ No
- **Read scope**: Full agent file (150 lines sampled)
- **Current responsibilities**: Guides type patterns, build configuration, monorepo setup, migration strategies
- **Gap identified**: The agent advises on *how to write TypeScript code correctly*, not on *spawning agent frameworks or integrating external agent runtimes*
- **Why unsuitable**: Pi-mono is a framework that *other projects* instantiate to build agents. `typescript-pro` helps users understand TypeScript—it does not build agents, CLI tools, or TUI applications itself. Pi-mono would be a library that a *new* TypeScript project might adopt, but typescript-pro does not call libraries to create systems.

### 2. Plugin: `python3-development`

**File**: `./plugins/python3-development/`

**Role**: Primary Python implementation plugin with delegation framework for developers and agents.

**Potential fit**: ❌ No
- **Scope**: Python-focused (see .claude/rules/python-development.md). Routes all Python implementation tasks to specialist agents.
- **Why unsuitable**: Pi-mono is TypeScript-only. The Python development plugin has no TypeScript agent counterpart in this repository, and adding one is out of scope for utilization assessment.

### 3. Agents: `feature-researcher`, `codebase-analyzer`, `integration-checker`

**Files**: `./plugins/development-harness/agents/`

**Role**: Discovery, analysis, and verification agents in the SAM workflow.

**Potential fit**: ❌ No
- **Gap identified**: These agents perform goal-backward discovery and validate implemented features. They do not execute frameworks or integrate external tools as part of their analysis.
- **Why unsuitable**: Pi-mono is relevant for *architectural pattern research* (the research notes reference it for agent runtime design, tool execution, session management), not for *automated recommendation or invocation*.

### 4. Skills: `external-pattern-integrator`, `swarm-spawning`, `swarm-primitives`

**Files**: `./.claude/skills/{external-pattern-integrator,swarm-spawning,swarm-primitives}/`

**Potential fit**: ❌ No
- **Scope boundary**: These skills describe *how to recognize and adopt* patterns from external systems, not *how to call external libraries as services*.
- **Why unsuitable**: Pi-mono's integration surface is an npm package and CLI tool. Using these skills would tell users *"you could adopt pi-mono's agent architecture for your own TypeScript project"*, not *"Claude Code itself will call pi-mono to execute agents"*. That distinction matters: the former is pattern adoption (not utilization), the latter is service integration (utilization).

---

## Why No Utilization Exists

Pi-mono documents a framework for **other projects** to build agents, CLI tools, and LLM applications. Claude Code is itself an agent system with its own plugin architecture, skills, agents, and hooks. The two systems are **peer implementations**, not caller-callee.

Concrete mismatch:

| Aspect | Claude Code | Pi-mono | Compatibility |
|---|---|---|---|
| **Agent runtime** | MCP servers + prompt-based agents | `pi-agent-core` event-driven runtime | Different event models; Claude Code agents are prompt-based, not event-driven subscribers |
| **Tool system** | Skills and tool frontmatter in SKILL.md | TypeScript-based tool definitions | Claude Code tools are declared via frontmatter; Pi tools are TypeScript classes |
| **Extension mechanism** | Plugins with hooks | Pi Packages (npm bundles) | Orthogonal: plugins add skills to Claude Code; Pi Packages extend pi runtime |
| **User boundary** | Claude Code is the user-facing IDE | Pi CLI is the user-facing tool | Pi-mono is for building coding tools; Claude Code *is* the coding environment |

---

## Observations

1. **Pattern relevance**: The research correctly identifies architectural parallels (section "Relevance to Claude Code Development"). The `pi-agent-core` design for message transformation, tool execution, and event streaming informs *how Claude Code's agents could be improved*, not *what services Claude Code should call*.

2. **Research use case**: This research entry is valuable for **architectural benchmark and design inspiration**, not for direct integration. Future work might involve adopting pi-mono's patterns in Claude Code's own agent system, but that is refactoring, not utilization.

3. **Out of scope for this assessment**: Whether Claude Code *should* adopt pi-mono's architecture is a design question requiring human decision-making and extended experimentation. Utilization assessment only identifies when a callable service exists and local systems need it. Neither condition is true here.

---

## Result

**STATUS**: complete

**RESEARCH_ENTRY**: ./research/agent-frameworks/pi-mono.md

**SURFACES_FOUND**: 3 (SDK | CLI | NPM)

**PROPOSALS_WRITTEN**: 0

**SKIPPED**: 4 candidate systems
- `typescript-pro`: Advises on TypeScript, does not spawn frameworks or invoke runtimes
- `python3-development` plugin: Python-focused; no TypeScript agent framework exists to call pi-mono
- `feature-researcher`, `codebase-analyzer`: Analysis agents; not executors of framework integration
- `external-pattern-integrator`, `swarm-*` skills: Pattern adoption tools, not service integration tools

**NOTE**: Integration surface documented but no suitable local caller identified. Pi-mono is architecturally relevant for design patterns (reference value), not for direct service invocation (utilization value).
