---
title: Orchestra
resource_name: orchestra
resource_url: https://github.com/carloluisito/orchestra
version: 1.0.0
created_date: 2026-04-20
last_updated: 2026-04-20
---

# Orchestra: Context-Optimized Task Orchestration for Claude Code

## Overview

Orchestra is a Claude Code plugin that decomposes complex work into a directed acyclic graph (DAG) of focused subtasks, dispatching each to sub-agents with curated, minimal-context prompts. It solves the problem of context degradation in multi-agent systems by ensuring each agent receives only the information relevant to its specific task, within a configurable token budget.

**Extracted from README**: "Context-optimized task orchestration for Claude Code. Keeps sub-agent output quality high by decomposing complex work into a DAG of focused subtasks, each dispatched with a curated, minimal-context prompt."

**Repository**: <https://github.com/carloluisito/orchestra> (created 2026-04-20, last updated 2026-04-20)
**License**: MIT (source: plugin.json)
**Version**: 1.0.0 (source: plugin.json, marketplace.json)
**Author**: Carlo (GitHub: carloluisito)

## Problem Addressed

Existing agent systems suffer from context bloat — large specs, plans, and codebases are passed to every sub-agent, most of it irrelevant to the specific task. This leads to:

1. **Quality degradation** — as context grows, output quality decreases
2. **Token waste** — irrelevant context consumes tokens that could be spent on focus
3. **Compounding failures** — poor agent output cascades to downstream tasks

**Extracted from README**: "As context grows larger, output degrades. Typical agent systems stuff full specs, plans, and codebases into every sub-agent — most of it irrelevant to the task at hand. Quality drops, tokens are wasted, and failures compound."

Orchestra addresses this by applying context curation: each agent receives exactly what it needs, within a configurable budget.

## Key Statistics

- **GitHub Stars**: 8 (as of 2026-04-20)
- **Forks**: 2 (as of 2026-04-20)
- **Primary Language**: HTML (repository metadata indicates HTML files present; no primary source code language specified in API response)
- **Created**: 2026-04-20 (very recent — first day of public availability)
- **Last Updated**: 2026-04-20

## Key Features

### 1. DAG-Based Task Decomposition

Orchestra breaks complex work into a directed acyclic graph (DAG) of atomic tasks with explicit dependencies.

**Extracted from README and SKILL.md**: "Orchestra breaks work into atomic tasks with explicit dependencies." Tasks are organized into **waves** based on dependency depth — independent tasks run in parallel, dependent tasks execute after their upstream tasks complete.

**Mechanism**: The Decomposer component classifies input richness (Rich/Medium/Lean) and applies the appropriate decomposition procedure:
- **Procedure A (Rich input)**: Parses numbered plan steps into candidate tasks, merges related steps, infers dependencies from file creation chains and concept references, and computes waves
- **Procedure B (Medium input)**: Analyzes spec structure, identifies natural components (data model, features, cross-cutting concerns), and orders by dependency
- **Procedure C (Lean input)**: Generates tasks from the brief prompt using heuristics

### 2. Context Curation and Token Budgeting

Each sub-agent receives a minimal, focused prompt assembled from only the context it needs.

**Extracted from SKILL.md**: "Context Curator — During dispatch — assembling focused prompts for sub-agents." Each task has a configurable token budget (default 80,000 tokens). The Context Curator:
- Extracts relevant spec sections based on task description
- Includes relevant files and upstream task summaries
- Respects the per-task token limit

**Token budget adjustment** (source: decomposer.md):
- Simple tasks: 50% of default budget
- Standard tasks: 100% of default budget
- Complex tasks: 150% of default budget

### 3. Parallel Execution with Configurable Autonomy

Independent tasks execute in parallel sub-agents. Autonomy level determines how much user review happens between waves.

**Extracted from README and SKILL.md**:
- `full_auto` — all tasks run without user intervention
- `checkpoint` (default) — user reviews after each wave of tasks completes
- `per_task` — user confirms each task individually

**Configuration**: `max_parallel` (default 3) controls maximum concurrent sub-agents.

### 4. Git Worktree Isolation

Each sub-agent runs in an isolated git worktree, preventing file conflicts during parallel execution.

**Extracted from README**: "Git worktree isolation is on by default." Configuration option `use_worktrees` (default true) enables this isolation. Worktrees are cleaned up automatically after task completion.

### 5. State Management and Resumability

Orchestra persists run state in `.orchestra/` directory, enabling recovery from interruptions.

**Extracted from SKILL.md and state-manager.md**: State includes:
- `config.md` — run configuration and metadata
- `dag.md` — task DAG with wave structure
- `tasks/` directory — individual task files with status, artifacts, logs
- `history.md` — timeline of events
- `input/` — original input documents

State files are gitignored by convention. Runs can be resumed with `/orchestra resume` — the dispatcher reads state from disk and continues from the last checkpoint.

### 6. Dashboard Visualization (Optional)

A lightweight Node.js-based dashboard visualizes active runs and token usage.

**Extracted from README and SKILL.md**: Dashboard shows:
- Real-time task execution progress (wave structure)
- Per-task token consumption
- Sub-agent output and logs
- DAG visualization

Started automatically with `/orchestra run` (Step 3b) and stopped after completion (Step 6). Runs on a local port (URL provided in `.orchestra/dashboard-info.json`).

### 7. Cross-Repository Orchestration

Coordinate changes across sibling repositories from a single orchestration.

**Extracted from README and SKILL.md**:
- Pass `--repos repo-a,repo-b` to `/orchestra run` command
- Paths resolved relative to parent directory of primary repo (`../repo-name/`)
- Per-repo base branch configuration (Step 2b)
- Per-repo branch creation and cleanup
- Multi-repo summary on completion showing which repos received tasks

### 8. Fallback Recovery Engine

Tasks marked with `fallback: true` or failing after max retries trigger fallback recovery procedures.

**Extracted from SKILL.md and component reference**: Fallback Engine is invoked when:
- Task has `fallback: true` flag in its definition
- Task fails after `max_retries` attempts (default 2)

Recovery procedures include alternative decompositions, reduced scope, or manual intervention guidance.

### 9. Project Convention Extraction

Before dispatching, Orchestra extracts project coding standards from CLAUDE.md and settings files.

**Extracted from SKILL.md Step 2d**: Collects:
- Naming conventions, import patterns, testing frameworks
- Architectural constraints, code style rules
- Language/framework-specific conventions

Filters out session behavior rules (interaction preferences, tool permissions). Condensed to under 2000 characters and included in Context Curator input as `.orchestra/project-conventions.md`.

### 10. Dirty Repo Stashing

Before creating worktrees, Orchestra prompts to stash uncommitted changes, preventing interference.

**Extracted from SKILL.md Step 2c**: For each repository with uncommitted changes:
- Prompt user: "Stash them before proceeding?"
- If yes: `git stash push -m "orchestra-auto-stash: pre-run {branch_name}"`
- Records stashed repos so user is reminded to restore after run completion

## Technical Architecture

### Core Components

The system is modularized into seven primary skill files (source: SKILL.md component reference):

1. **State Manager** (`state-manager.md`)
   - Initializes `.orchestra/` directory structure
   - Generates config and history templates
   - Reads state for resume operations
   - Manages checkpoint persistence

2. **Decomposer** (`decomposer.md`)
   - Classifies input richness (Rich/Medium/Lean)
   - Applies appropriate decomposition procedure (A/B/C)
   - Generates task files with metadata
   - Computes wave structure for parallel execution

3. **Context Curator** (`context-curator.md`)
   - Extracts relevant spec sections per task
   - Assembles focused prompts within token budget
   - Includes relevant files, upstream summaries
   - Called during dispatch (Step 5)

4. **Dispatcher** (`dispatcher.md`)
   - Main execution loop
   - Reads state, finds ready tasks
   - Enforces autonomy gates (full_auto/checkpoint/per_task)
   - Dispatches sub-agents and collects results
   - Internally calls Context Curator and Result Collector

5. **Result Collector** (`result-collector.md`)
   - Processes sub-agent output after task completion
   - Records artifacts and logs
   - Updates task status
   - Produces summaries for downstream consumers

6. **Fallback Engine** (`fallback-engine.md`)
   - Triggered on task failure after max retries
   - Applies recovery procedures
   - Alternative decompositions or reduced scope
   - Notifies dispatcher of recovery outcome

7. **Refiner** (`refiner.md`)
   - Classifies input richness (Rich/Medium/Lean)
   - If Medium or Lean: enriches with analysis before decomposition
   - Runs conditionally based on autonomy setting
   - Output enriched spec/plan files to `.orchestra/input/`

### Execution Flow

**New Run (Step-by-step from SKILL.md)**:

1. **Validate Input** — Check file existence, parse `--repos` flag, scan directories for .md files
2. **Configure** — User selects settings (token_budget, autonomy, max_parallel, agent_model, use_worktrees)
3. **Branch Setup** — Create feature branch in primary and registered repos
4. **Dirty Repo Check** — Stash uncommitted changes with user confirmation
5. **Collect Conventions** — Extract project standards from CLAUDE.md and settings
6. **Initialize State** — Create `.orchestra/` structure, generate config and history
7. **Start Dashboard** — Optional Node.js server for visualization
8. **Refine Input** — Optionally enrich sparse inputs before decomposition
9. **Decompose** — Break input into task DAG with wave assignments
10. **Dispatch Loop** — Execute ready tasks in parallel, respecting token budgets and autonomy settings
11. **Completion** — Show summary, update history, stop dashboard

### Task Metadata Format

Each task file (`.orchestra/tasks/{id}.md`) contains:

```markdown
---
id: task-001
title: Implement authentication middleware
status: [pending | in-progress | done | failed]
depends_on: [task-000]
blocks: [task-002, task-003]
wave: 1
token_budget: 80000
spec_sections: [Auth, API Endpoints]
relevant_files: [src/middleware/auth.ts, src/routes/api.ts]
upstream_tasks: [task-000]
acceptance_criteria:
  - [ ] Middleware verifies JWT signatures
  - [ ] Invalid tokens return 401 status
  - [ ] Logged-in user context available in req.user
---

## Objective
[Task description from decomposer]

## Context
[Curated context from Context Curator, within token budget]

## Artifacts
[Generated files, logs, test results from sub-agent]
```

### Configuration Schema

**config.md template** (from SKILL.md Step 2):

```yaml
---
run_id: {uuid}
branch_name: feat/implement-user-auth
branch_base: main
registered_repos:
  - service-b
  - shared-types
token_budget: 80000
autonomy: checkpoint
max_parallel: 3
max_retries: 2
agent_model: sonnet
use_worktrees: true
status: [pending | running | completed | completed_with_failures | halted]
conventions_collected: true
stashed_repos:
  - service-a: "orchestra-auto-stash: pre-run feat/..."
---
```

## Installation & Usage

### Installation

**Extracted from README**:

```
/plugin marketplace add carloluisito/orchestra
/plugin install orchestra@orchestra-local
```

The plugin registers:
- One skill: `orchestra`
- One PostToolUse hook: token-tracking (Node.js-based)
- Command pattern: `/orchestra ...`

### Requirements

- Claude Code (latest)
- Node.js (for PostToolUse hook and optional dashboard)
- Git (for worktree isolation)

### Quick Start

**All examples from README**:

```bash
/orchestra run path/to/spec.md               # Run from a spec file
/orchestra run spec.md plan.md               # Spec + plan
/orchestra run "Build a REST API for ..."    # Raw prompt
/orchestra run ./docs/                       # Directory (scans .md files)
/orchestra run "Add auth" --repos service-b  # Cross-repo orchestration
/orchestra resume                            # Resume the last run
/orchestra status                            # Read-only view of progress
```

After `run`, Orchestra prompts interactively for configuration and branch setup.

### Configuration Defaults

**Source: README and SKILL.md**:

| Setting | Default | Options |
|---------|---------|---------|
| `token_budget` | 80000 | Any positive integer |
| `autonomy` | checkpoint | full_auto, checkpoint, per_task |
| `max_parallel` | 3 | Any positive integer |
| `max_retries` | 2 | Any non-negative integer |
| `agent_model` | sonnet | sonnet, opus, haiku |
| `use_worktrees` | true | true, false |

### Dashboard (Optional)

**Extracted from README and SKILL.md**:

```bash
./skills/orchestra/scripts/start-dashboard.sh
./skills/orchestra/scripts/stop-dashboard.sh
```

Lightweight Node.js-based visualization of:
- Real-time task execution (wave structure)
- Token consumption per task
- Sub-agent logs and output
- DAG structure

Automatically started on `run` (Step 3b) and stopped on completion.

## Relevance to Claude Code Development

### 1. Multi-Agent Orchestration Pattern

Orchestra implements a production-grade pattern for orchestrating multi-agent workflows. Key insights for Claude Code development:

- **Context curation as a core feature**: Demonstrates that sub-agents perform better with minimal, focused context rather than full project state
- **Token budgeting per task**: Shows explicit token management enables reliable cost prediction and prevents runaway context growth
- **Wave-based parallelism**: DAG-based task scheduling enables safe parallel execution without coordination overhead

### 2. State Persistence and Resumability

Orchestra's `.orchestra/` state directory and checkpoint mechanism provide a template for building resumable workflows:

- Checkpoint files in YAML/Markdown (human-readable, version-controllable)
- Separator between orchestration state and project state (gitignored `.orchestra/`)
- Resume capability from last checkpoint enables recovery from interruptions

### 3. Decomposition Heuristics

The three decomposition procedures (Rich/Medium/Lean) are reusable patterns for breaking user intent into sub-agent tasks:

- **Rich input**: Leverage explicit structure (numbered plans) to extract dependencies
- **Medium input**: Identify components and order by dependency
- **Lean input**: Generate tasks from brief prompts using heuristics

These patterns apply to any multi-step task, not just Orchestra runs.

### 4. Autonomy Levels and Checkpoints

Orchestra's three autonomy modes (full_auto/checkpoint/per_task) provide a framework for balancing automation with user control:

- `full_auto` — for high-confidence tasks and trusted workflows
- `checkpoint` (default) — review after each wave, good for discovery and debugging
- `per_task` — fine-grained control for sensitive or uncertain tasks

This model applies to any multi-step operation where user judgment is valuable at certain points.

### 5. Cross-Repository Coordination

The `--repos` flag demonstrates a pattern for coordinating changes across multiple code repositories from a single orchestration:

- Shared branch naming and base branch configuration
- Per-repo task dispatch and branch management
- Multi-repo summaries showing which repos received changes

Useful for monorepos, service-oriented architectures, and coordinated API/client updates.

## Limitations and Caveats

### 1. **Young Project — First Release**

Orchestra was released on 2026-04-20 (the same date as this research entry). The codebase has minimal history (5 commits), no prior releases, and no community validation yet. Breaking changes are possible in minor versions during the 1.x series.

**Source**: GitHub API metadata (`created_at`, `updated_at`), git log showing 5 commits total.

### 2. **Limited Testing Visibility**

The repository includes test scenario documents (`tests/scenarios/`) but no test automation framework or CI/CD pipeline is visible in the shallow clone. Manual verification of all features is recommended before production use.

**Source**: Directory listing shows scenario .md files but no test runner configuration in root or package.json.

### 3. **Node.js Dashboard is Optional but Requires Setup**

The dashboard requires Node.js installation and startup/shutdown scripts. If the dashboard server fails to start, orchestration continues without visualization. Node.js is not strictly required to use Orchestra, but the PostToolUse hook for token tracking requires Node.js environment availability during the session.

**Source**: README lists Node.js as requirement. SKILL.md Step 3b notes "If the server fails to start, warn the user but continue — the dashboard is optional."

### 4. **Worktree Cleanup Responsibility**

When `use_worktrees: true` (default), sub-agents run in isolated git worktrees created under `.git/worktrees/`. The documentation does not explicitly describe worktree cleanup on failure or explicit failure handling for orphaned worktrees. Manual cleanup may be necessary if a run is force-halted.

**Source**: README mentions "worktree isolation is on by default" but does not document cleanup procedures for orphaned worktrees.

### 5. **No Built-in Validation of Agent Output Quality**

Orchestra tracks task status (pending/in-progress/done/failed) but does not validate that sub-agent output meets acceptance criteria. Acceptance criteria are defined (Decomposer A7) but validation is manual — an agent must inspect output and mark the task done. No automatic gate prevents marking a task done if AC are unmet.

**Source**: SKILL.md Step 6 shows final summary with "failed tasks and their failure reasons" but does not describe an acceptance criteria validation gate.

### 6. **Cross-Repo Coordination Limited to Sibling Repositories**

The `--repos` flag resolves paths relative to the parent of the primary repo (`../repo-name/`), limiting cross-repo orchestration to siblings. Arbitrary remote repos or different directory structures are not supported.

**Source**: SKILL.md Step 1, "Verify each resolved path exists and is a git repository... resolve the path as `../{name}` relative to the current working directory's git root."

### 7. **Sub-Agent Model Selection is Global**

All sub-agents use the same model (`agent_model` from config). There is no per-task model selection, so complex tasks cannot be assigned Opus while simple tasks use Haiku. This may result in suboptimal token usage for heterogeneous task difficulty.

**Source**: SKILL.md configuration table shows `agent_model: sonnet` as global setting with no per-task override visible in task metadata schema.

### 8. **Context Curator Budget Enforcement Method Unclear**

The Context Curator is documented as assembling prompts "within a configurable token budget," but the exact truncation/selection strategy if context exceeds the budget is not visible in the shallow clone's SKILL.md descriptions. The actual curated prompt format and fallback behavior (e.g., what gets cut) are implementation details not documented in primary sources.

**Source**: SKILL.md describes "Context Curator — assembling focused prompts for sub-agents" but the context-curator.md file was not fully read (file size and token constraints).

## References

- **README.md** — Primary user documentation, feature overview, installation, quick start, configuration table, cross-repo usage
- **plugin.json** — Plugin manifest with version, license, keywords, author, repository URL
- **marketplace.json** — Distribution metadata and plugin listing
- **SKILL.md** — Complete orchestration workflow, all command flows (New Run, Resume, Status), component lifecycle, configuration schema
- **decomposer.md** (excerpt) — Task decomposition procedures (A/B/C), input richness classification, dependency inference, wave computation, token budgeting
- **GitHub Repository Metadata** (via API) — Stars (8), forks (2), created date (2026-04-20), license (MIT), language distribution
- **Repository Structure** — bin/, hooks/, skills/, tests/ directories visible in shallow clone; skills/orchestra/ contains SKILL.md and component files

**Sources accessed**:
- <https://github.com/carloluisito/orchestra> (shallow clone, depth=1)
- <https://api.github.com/repos/carloluisito/orchestra> (GitHub REST API)
- All source files read from local worktree at `/tmp/.worktrees/orchestra/`

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [oh-my-claudecode.md](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | 32-agent orchestration for Claude Code with smart model routing and skill composition; shares Orchestra's automatic agent dispatch and token budgeting approach |
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale orchestration with Sisyphus/Atlas/Prometheus multi-agent architecture and category-based model routing; parallel pattern to Orchestra's task decomposition |
| [gastown.md](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent workspace manager coordinating 20-50+ Claude Code sessions via tmux and git worktrees; analogous DAG-based execution model with wave-structured parallelism |
| [google-adk.md](./google-adk.md) | agent-frameworks | Agent framework with sub_agents hierarchy, LLM-driven routing, and token-threshold context compaction; same category with overlapping multi-agent orchestration patterns |
| [liteagents.md](./liteagents.md) | agent-frameworks | 11-agent toolkit with orchestrator agent and session memory pipeline; shares Orchestra's intent-based agent routing and multi-step workflow coordination |
| [superpowers.md](./superpowers.md) | agent-frameworks | Composable skills framework with subagent-driven development and two-stage code review; analogous to Orchestra's context curation and task-specific agent dispatch |
| [Cursor Cookbook](cursor-cookbook.md) | agent-frameworks | shares DAG task decomposition with Kahn's algorithm, parallel sub-agent execution, and context curation patterns (bidirectional) |

---

## Freshness Tracking

**Last researched**: 2026-04-20 (same day as project creation)
**Confidence Summary**:
- **Identity/Metadata** (name, version, license, author, repository): high — extracted from plugin.json, marketplace.json, and GitHub API
- **Features (user-facing capabilities and configuration)**: high — extracted from README.md and SKILL.md, direct quotes
- **Architecture (components, data flow, extension points)**: medium — based on skill file headers and component descriptions. Full implementation not visible in shallow clone (decomposer.md, context-curator.md, dispatcher.md, state-manager.md partially visible due to file size); confidence increased by explicit cross-references in SKILL.md component table
- **Installation & Usage (commands, requirements, setup steps)**: high — extracted directly from README.md
- **Limitations and Caveats**: medium — some limitations inferred from documentation absence (e.g., worktree cleanup, output validation) rather than explicit statements

**Next review date**: 2026-07-20 (3 months from creation)

**Notes for future reviews**:
- Project is brand new (released 2026-04-20); expect rapid iteration and possible breaking changes during 1.x series
- No upstream users or community feedback yet — monitor for bug reports and feature requests as adoption increases
- Dashboard and token-tracking features are Node.js-based; may require environment-specific handling
- When project reaches 1.1.0 or later, re-read full component files (context-curator.md, dispatcher.md, fallback-engine.md) to validate architectural claims and extent of parameterization

