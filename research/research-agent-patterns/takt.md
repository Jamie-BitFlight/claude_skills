# TAKT (TAKT Agent Koordination Topology)

**Research Date**: 2026-03-28
**Source URL**: <https://github.com/nrslib/takt>
**GitHub Repository**: <https://github.com/nrslib/takt>
**Version at Research**: 0.33.2
**License**: MIT

---

## Overview

TAKT is a multi-agent orchestration system that enables YAML-defined workflows to coordinate multiple AI agents (Claude Code, Codex, OpenCode, Cursor, GitHub Copilot CLI) through state machine transitions with rule-based routing. It provides structured review loops, managed prompts, and guardrails for code generation tasks, moving beyond simple prompt-response interactions to complex workflows with planning, implementation, review, and fix cycles—all governed by declarative "piece" files that define movement sequences and routing rules.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Ad-hoc AI coding workflows lack reproducibility and quality control | YAML-defined pieces ensure execution paths are declared, keeping results consistent and shareable across teams |
| Multiple AI agents require independent prompt management and permission rules | Faceted prompting system composes prompts from independent facets (persona, policy, knowledge, instruction) that compose freely across workflows |
| Code review and fix loops require manual orchestration and decision-making | Built-in state machine with rule evaluation (tag-based, AI judge, aggregate conditions) automatically routes agents through planning → implementation → review → fix cycles |
| Complex workflows (parallel reviewers, dynamic task decomposition) are difficult to express | Three specialized runners handle parallel movements, data-driven batch processing (Arpeggio), and dynamic task decomposition (Team Leader) |
| QA and security audits require manual code analysis | Audit pieces (audit-architecture, audit-e2e, audit-unit, audit-security) enumerate architecture issues and coverage gaps without code changes, producing actionable reports |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 866 | 2026-03-28 |
| Forks | 49 | 2026-03-28 |
| Contributors | Approximately 10+ | 2026-03-28 |
| Latest Release | 0.33.2 | 2026-03-26 |
| Node.js Requirement | >=18.0.0 | Per package.json |
| npm Package | `takt` | Global install |

---

## Key Features

### Core Piece Engine

- **State Machine Orchestration**: PieceEngine (`src/core/piece/engine/PieceEngine.ts`) manages movement transitions based on rule evaluation results, emitting events for `movement:start`, `movement:complete`, `movement:report`, and state transitions (advancing to `COMPLETE` or `ABORT`)
  - Source: `src/core/piece/engine/PieceEngine.ts — class PieceEngine` (code-read)
  - Supports loop detection and cycle detection with synthetic judge movements to prevent infinite loops
  - Maintains agent sessions per movement for conversation continuity across Phase 1 → Phase 2 → Phase 3

- **Three-Phase Movement Execution**: Each movement executes up to 3 phases, with the agent session resumed across phases to retain context:
  1. Phase 1 (Main work): Execute movement with allowed tools (Write excluded if report defined)
  2. Phase 2 (Report output): Write only, optional, when `output_contracts` defined
  3. Phase 3 (Status judgment): No tools, just status output for condition matching
  - Source: `src/core/piece/phase-runner.ts` (code-read)

### Rule Evaluation System

- **5-Stage Fallback Evaluation** (`src/core/piece/evaluation/RuleEvaluator.ts`):
  1. Aggregate (`all()`/`any()`) — For parallel parent movements
  2. Phase 3 tag (`[STEP:N]`) — From status judgment output
  3. Phase 1 tag (`[STEP:N]`) — Fallback from main execution
  4. AI judge (`ai("condition text")`) — AI evaluates condition
  5. AI judge fallback — AI evaluates all conditions if no match
  - When multiple `[STEP:N]` tags appear, **last match wins**
  - Fail-fast: throws if rules exist but no rule matches
  - Source: `src/core/piece/evaluation/RuleEvaluator.ts — class RuleEvaluator` (code-read)

### Multi-Movement Types

- **Normal Movement**: Single agent execution with instructions and optional report/status output
- **Parallel Movement** (`ParallelRunner`, `src/core/piece/engine/ParallelRunner.ts`): Sub-movements execute concurrently via `Promise.allSettled()`, with parent rules aggregating results using `all()` / `any()` conditions
  - Source: `src/core/piece/engine/ParallelRunner.ts — class ParallelRunner` (code-read)
- **Arpeggio Movement** (`ArpeggioRunner`, `src/core/piece/engine/ArpeggioRunner.ts`): Data-driven batch processing — reads CSV, expands templates per batch, calls LLM with concurrency control, supports retry logic and merge strategies (concat or custom)
  - Source: `src/core/piece/engine/ArpeggioRunner.ts — class ArpeggioRunner` (code-read)
- **Team Leader Movement** (`TeamLeaderRunner`, `src/core/piece/engine/TeamLeaderRunner.ts`): Decomposes task into sub-parts via AI, executes each part in parallel (max 3 parts), aggregates results
  - Source: `src/core/piece/engine/TeamLeaderRunner.ts — class TeamLeaderRunner` (code-read)

### Faceted Prompting

- Independent module composing prompts from 4 facets: persona (WHO), policy (HOW), knowledge (WHAT TO KNOW), instruction (WHAT TO DO NOW)
- Each facet is a standalone file; TAKT assembles them into complete system prompt
- Supports template rendering, context truncation, facet path resolution, scope references
- Personas are reusable across pieces; pieces assign facets via YAML
  - Source: `src/faceted-prompting/` module (code-read)

### Multi-Provider Support

- **Claude** (via `@anthropic-ai/claude-agent-sdk`): Supports session management, permission modes (readonly, edit, full), sandbox configuration
- **Codex** (via `@openai/codex-sdk`): In-memory sessions, retry with exponential backoff (3 attempts)
- **OpenCode** (via `@opencode-ai/sdk`): Shared server pooling, requires explicit model specification
- **Cursor Agent**: Direct agent execution
- **GitHub Copilot CLI**: CLI-based execution
- **Mock Provider**: Deterministic responses for testing
  - Provider resolution: 5-layer priority (CLI `--provider` → persona_providers → movement override → project config → global config)
  - Source: `src/infra/providers/` directory structure (code-read)

### VCS Integration (GitHub & GitLab)

- **GitHub Provider** (`src/infra/github/`): Via `gh` CLI, fetches issues, creates PRs, supports draft PRs and custom templates
- **GitLab Provider** (`src/infra/gitlab/`, added in v0.33.0): Via `glab` CLI, fetches issues, creates merge requests, fetches MR review comments
- Auto-detection from git remote URL; explicit `vcs_provider` config for self-hosted instances
  - Source: `src/infra/git/` and provider-specific subdirectories (code-read)

### Task Management

- **Queue and Execute**: Tasks saved to `.takt/tasks/`, executed serially via `takt run` or watched continuously via `takt watch`
- **Interactive Mode**: Supports 4 conversation modes: `assistant` (default, AI asks clarifying questions), `passthrough` (direct task input), `quiet` (generates instructions without questions), `persona` (uses first movement's persona for conversation)
- **Pipeline Mode**: Non-interactive mode for CI/CD, auto-creates branch, commits, pushes, optionally creates PR
- **GitHub Issue Integration**: `takt #N` fetches issue and executes as task
  - Source: `src/features/tasks/` and `src/features/interactive/` (code-read)

### Analytics and Reporting

- **NDJSON Session Logging**: All piece executions logged to `.takt/logs/{sessionId}.jsonl` with record types: `piece_start`, `movement_start`, `movement_complete`, `piece_complete`, `piece_abort`
- **Analytics Events**: Tracked as `MovementResultEvent`, `ReviewFindingEvent`, `FixActionEvent`, `RebuttalEvent` stored in `.takt/events/`
- **Execution Reports**: Per-piece execution reports in `.takt/runs/{slug}/reports/` with optional Phase 2 report files
  - Source: `src/features/analytics/` and session logging in piece engine (code-read)

### Configuration and Customization

- **Global config** (`~/.takt/config.yaml`): Provider, model, language, logging level, permission mode
- **Project config** (`.takt/config.yaml`): Project-specific overrides
- **Piece Categories**: Organize pieces into nested categories with builtin filtering and "Others" category
- **Ejection System**: `takt eject [type] [name]` copies builtin piece/facet to user directory for customization
  - Source: `src/infra/config/` (code-read)

### Repertoire Packages

- Package management for external facet/piece collections
- Install from GitHub: `github:{owner}/{repo}@{ref}`
- Lock file for resolved dependencies; packages installed to `~/.takt/repertoire/@{owner}/{repo}/`
  - Source: `src/features/repertoire/` (code-read)

### Built-in Pieces

**Recommended pieces from README**:
- `default` — Standard development with test-first approach, AI antipattern review, parallel reviewers
- `frontend-mini` — Frontend-focused minimal configuration
- `backend-mini` — Backend-focused minimal configuration
- `dual-mini` — Frontend + backend minimal configuration

**Audit pieces** (added in v0.33.2, read-only, no code changes):
- `audit-architecture`, `audit-architecture-frontend`, `audit-architecture-backend`, `audit-architecture-dual` — Module boundary and architecture issues
- `audit-e2e`, `audit-unit` — Test coverage gaps
- `audit-security` — Security anti-patterns

---

## Technical Architecture

### High-Level Flow

```
CLI (cli.ts → routing.ts)
  → Interactive mode / Pipeline mode / Direct task execution
    → PieceEngine (piece/engine/PieceEngine.ts)
      → Per movement, delegates to one of 4 runners:
        ├─ MovementExecutor  — Normal movements (3-phase execution)
        ├─ ParallelRunner    — Parallel sub-movements
        ├─ ArpeggioRunner    — Data-driven batch processing
        └─ TeamLeaderRunner  — Dynamic task decomposition
      → detectMatchedRule() → determineNextMovementByRules()
```

### Core Components

**PieceEngine** — State machine that orchestrates agent execution via EventEmitter. Manages movement transitions based on rule evaluation results, emits lifecycle events, supports loop/cycle detection, maintains agent sessions per movement.

**MovementExecutor** — Executes a single piece movement through the 3-phase model. Builds instructions via `InstructionBuilder`, detects matched rules via `RuleEvaluator`, writes facet snapshots per iteration.
  - Source: `src/core/piece/engine/MovementExecutor.ts — class MovementExecutor` (code-read)

**InstructionBuilder** — Auto-injects standard sections into every instruction (no need for explicit placeholders):
  1. Execution context (working dir, edit permission rules)
  2. Piece context (iteration counts, report dir)
  3. User request (task — auto-injected unless placeholder present)
  4. Previous response (auto-injected if `pass_previous_response: true`)
  5. User inputs (auto-injected unless placeholder present)
  6. `instruction` content
  7. Status output rules (auto-injected for tag-based rules)
  - Localized for `en` and `ja`
  - Source: `src/core/piece/instruction/InstructionBuilder.ts` (code-read)

**Agent Runner** — Resolves agent specs (name or path) to agent configurations. 5-layer resolution for provider/model: CLI → persona_providers → movement override → project config → global config. Custom personas via `~/.takt/personas/<name>.md`. Inline system prompts: if agent file doesn't exist, agent string is used as inline system prompt.
  - Source: `src/agents/runner.ts` (code-read)

**Configuration System**:
- `loaders/pieceParser.ts` — YAML parsing with Zod validation
- `loaders/pieceResolver.ts` — 3-layer resolution (project → user → builtin)
- `loaders/agentLoader.ts` — Agent prompt file loading
- `paths.ts` — Directory structure and session management
- `global/globalConfig.ts` — Global configuration
- `project/projectConfig.ts` — Project-level configuration

**VCS Integration**:
- `src/infra/git/` — Unified VCS interface; auto-detects provider from remote URL
- `src/infra/github/` — GitHub provider (gh CLI delegation)
- `src/infra/gitlab/` — GitLab provider (glab CLI delegation)

**Isolated Execution**:
- Worktrees use `git clone --shared` (lightweight clone with independent `.git`) instead of `git worktree` to prevent Claude Code session traversal
- Clones created before task execution, auto-committed + pushed after success, then deleted
- Sessions not resumed in clones (session stored per-cwd in `~/.claude/projects/{encoded-path}/`)
  - Source: CLAUDE.md section "Isolated Execution (Shared Clone)" and `src/core/worktree/` implementation (code-read)

### Data Flow

1. User provides task (text or `#N` issue reference) → CLI
2. CLI loads piece with priority: project `.takt/pieces/` → user `~/.takt/pieces/` → builtin `builtins/{lang}/pieces/`
3. PieceEngine starts at `initial_movement`
4. Each movement: delegate to appropriate runner → 3-phase execution → rule evaluation → next movement
5. Rule evaluation determines next movement name (uses **last match** when multiple `[STEP:N]` tags appear)
6. Special transitions: `COMPLETE` ends piece successfully, `ABORT` ends with failure

### Directory Structure

```
~/.takt/                  # Global user config
  config.yaml             # Language, provider, model, logging, etc.
  pieces/                 # User piece YAML files
  facets/                 # User facets (personas, policies, knowledge, instructions, output-contracts)
  repertoire/             # Installed repertoire packages

.takt/                    # Project-level config
  config.yaml             # Project configuration
  facets/                 # Project-level facets
  tasks/                  # Task files for takt run
  runs/                   # Execution reports (runs/{slug}/reports/)
  logs/                   # Session logs in NDJSON format
  events/                 # Analytics event files (NDJSON)

builtins/                 # Bundled defaults (embedded in npm package)
  en/
    facets/               # Facets (personas, policies, knowledge, instructions)
    pieces/               # Piece YAML files
  ja/                     # Japanese (same structure)
```

---

## Installation & Usage

### Installation

```bash
npm install -g takt
```

Requires Node.js >= 18.0.0.

### Quick Start

#### Interactive Task Creation

```bash
$ takt

Select piece:
  ❯ 🎼 default (current)
    📁 🚀 Quick Start/
    📁 🎨 Frontend/
    📁 ⚙️ Backend/

> Add user authentication with JWT

[AI clarifies requirements and organizes the task]

> /go

Proposed task: ...

What would you like to do?
  Execute now
  Create GitHub Issue
❯ Queue as task          # ← normal flow
  Continue conversation
```

"Queue as task" saves to `.takt/tasks/`. Run `takt run` to execute.

#### Configuration

Minimal `~/.takt/config.yaml`:

```yaml
provider: claude    # claude, codex, opencode, cursor, or copilot
model: sonnet       # passed directly to provider
language: en        # en or ja
```

Or use API keys directly:

```bash
export TAKT_ANTHROPIC_API_KEY=sk-ant-...   # Anthropic (Claude)
export TAKT_OPENAI_API_KEY=sk-...          # OpenAI (Codex)
export TAKT_OPENCODE_API_KEY=...           # OpenCode
export TAKT_CURSOR_API_KEY=...             # Cursor Agent (optional)
export TAKT_COPILOT_GITHUB_TOKEN=ghp_...   # GitHub Copilot CLI
```

#### Task Execution

```bash
# Execute queued tasks
takt run

# Queue from GitHub Issues
takt add #6
takt add #12

# Execute all pending tasks
takt run

# List completed/failed task branches — merge, retry, or delete
takt list

# Watch for task files and auto-execute
takt watch

# Execute GitHub Issue directly
takt #6

# Manage results
takt list
```

### Programmatic API Usage

```typescript
import { PieceEngine, loadPiece } from 'takt';

const config = loadPiece('default');
if (!config) throw new Error('Piece not found');

const engine = new PieceEngine(config, process.cwd(), 'My task');
engine.on('movement:complete', (movement, response) => {
  console.log(`${movement.name}: ${response.status}`);
});

await engine.run();
```

### Piece YAML Schema

```yaml
name: piece-name
max_movements: 10
initial_movement: plan    # First movement to execute

movements:
  - name: movement-name
    persona: coder        # Persona key
    policy: coding        # Coding standards
    knowledge: architecture  # Domain knowledge
    instruction: plan     # Movement-specific instructions
    edit: true            # Can edit files
    rules:
      - condition: "Human-readable condition"
        next: next-movement-name
      - condition: ai("AI evaluates this condition")
        next: other-movement
      - condition: blocked
        next: ABORT
```

---

## Relevance to Claude Code Development

### Applications

- **Multi-Agent Code Review Workflows**: TAKT's parallel movement runner enables simultaneous architecture + security + style review, with aggregate rules determining next action (approve vs. fix loop)
- **Structured Task Decomposition**: Team Leader runner automatically breaks down complex features (e.g., "add user auth") into independent subtasks, each executed as a sub-agent with separate context and permissions
- **Reproducible Piece Definitions**: YAML-based pieces replace ad-hoc prompt engineering, enabling teams to define once and share across all developers
- **Orchestration for Claude Code Skills**: TAKT's faceted prompting methodology (persona, policy, knowledge, instruction) aligns with skill content organization; pieces could be generated from SAM task files
- **Audit and Compliance**: Read-only audit pieces (audit-architecture, audit-security, audit-e2e) provide actionable reports without code changes, enabling compliance workflows without breaking implementation flow
- **Loop Detection and Cycle Management**: TAKT's cycle detector with synthetic judge movements prevents infinite review-fix-review loops, a pattern applicable to skill error recovery

### Patterns Worth Adopting

- **Faceted Prompting**: Decompose agent instructions into independent facets (role, policies, domain knowledge, procedure) that compose freely. This enables high reusability and maintainability compared to monolithic prompts
- **Explicit Rule Evaluation**: 5-stage fallback rule evaluation (aggregate → tag-based → AI judge) provides deterministic routing with graceful fallbacks, applicable to skill workflow decisions
- **Session Continuity Across Phases**: Agent sessions resumed across Phase 1 → Phase 2 → Phase 3 maintains context without token waste; useful for skills requiring multi-step validation
- **Worktree Isolation**: `git clone --shared` enables isolated execution without affecting main branch; pattern applicable to skill testing and sandboxing
- **NDJSON Logging**: Append-only session logs support real-time streaming and analysis; applicable to skill execution tracing and analytics

### Integration Opportunities

- **SAM Task to TAKT Piece Generation**: Automated conversion from SAM task files (P{N}/T{M}) to TAKT pieces, enabling orchestration inheritance
- **Claude Code Skill as TAKT Facet**: Skill system could generate persona + policy + knowledge facets, automatically composing into piece definitions
- **Skill Repertoire Packages**: Package custom facets as repertoire packages (`github:{owner}/{repo}@{ref}`), enabling public sharing of domain-specific orchestration patterns
- **Quality Gate Automation**: Integrate TAKT audit pieces (audit-architecture, audit-security, audit-e2e) into skill quality gates, replacing manual review steps with automated analysis
- **Skill Permission Management**: TAKT's permission mode system (readonly, edit, full) aligns with Claude Code sandbox configurations; standardize permission requirements across skills using TAKT's provider_options schema

---

## References

- [TAKT GitHub Repository](https://github.com/nrslib/takt) (accessed 2026-03-28)
- [TAKT README](https://raw.githubusercontent.com/nrslib/takt/main/README.md) (accessed 2026-03-28)
- [TAKT CLAUDE.md (Project Instructions)](https://raw.githubusercontent.com/nrslib/takt/main/CLAUDE.md) (accessed 2026-03-28)
- [TAKT CHANGELOG](https://raw.githubusercontent.com/nrslib/takt/main/CHANGELOG.md) (accessed 2026-03-28)
- [TAKT package.json](https://raw.githubusercontent.com/nrslib/takt/main/package.json) (accessed 2026-03-28)
- [TAKT LICENSE (MIT)](https://raw.githubusercontent.com/nrslib/takt/main/LICENSE) (accessed 2026-03-28)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-28 |
| Version at Verification | 0.33.2 |
| Next Review Recommended | 2026-06-28 |
| Confidence Map | Overview: high (doc read) • Problem Addressed: high (doc + README) • Key Statistics: high (GitHub API) • Key Features: high (doc + code-read) • Technical Architecture: high (CLAUDE.md + code-read) • Installation & Usage: high (README + code read) • Relevance: medium (inferred from architecture) |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Orchestrator Agent Creation Guide](./orchestrator-agent-creation-guide.md) | research-agent-patterns | shared core pattern: declarative routing, parallel delegation, agent chaining |
| [Compound Engineering Plugin](./compound-engineering-plugin.md) | research-agent-patterns | overlapping workflow model: Plan→Work→Review→Compound with multi-agent coordination |
| [Gastown](./gastown.md) | research-agent-patterns | similar orchestration architecture: multi-agent workspace manager with DAG workflows and transport layer |
| [Oh-My-OpenCode](./oh-my-opencode.md) | research-agent-patterns | comparable scale and complexity: 100+ agent orchestration with Sisyphus/Atlas routing layers |
| [Claw Loop](./claw-loop.md) | research-agent-patterns | shared automation pattern: supervisor-worker orchestration with cron-driven task cycles |
| [The Delegation](./the-delegation.md) | research-agent-patterns | overlapping orchestration model: spatial multi-agent coordination with PM orchestrator |
| [Ruflo](../agent-frameworks/ruflo.md) | agent-frameworks | production-scale multi-agent orchestration: 100+ specialized agents, 215+ MCP tools, fault-tolerant consensus |
| [Solace Agent Mesh](../agent-frameworks/solace-agent-mesh.md) | agent-frameworks | event-driven agent delegation: scalable peer-to-peer agent collaboration via message-broker architecture |
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | referenced by Claude Code Harness (agent-frameworks) |

---

## Notes on Research Methodology

This entry derives core architectural information from two primary sources:

1. **CLAUDE.md** (Project internal documentation): Provides comprehensive architecture overview, component descriptions, data flow, configuration system, and testing methodology written by project maintainers for internal code navigation.

2. **Source code inspection** (Tier 1-3 files): Read PieceEngine, MovementExecutor, RuleEvaluator, ParallelRunner, ArpeggioRunner, TeamLeaderRunner, and configuration/infrastructure modules to verify architectural claims and identify specific component responsibilities.

Architecture depth requirements were satisfied via documentation; source code reading confirmed and extended claims with specific class/function names and file paths. All architectural assertions trace to either CLAUDE.md (marked as doc read) or verified code inspection (marked as code-read).
