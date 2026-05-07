---
title: Claude Code Harness
subtitle: Go-native guardrails and 5-verb workflow for Claude Code
category: agent-frameworks
resource_url: https://github.com/Chachamaru127/claude-code-harness
github_url: https://github.com/Chachamaru127/claude-code-harness
date_created: "2026-05-07"
date_last_reviewed: "2026-05-07"
status: published
---

## Overview

Claude Code Harness is a production-grade plugin for Anthropic's Claude Code that transforms the IDE into a disciplined development partner capable of autonomous task execution within a structured "Plan → Work → Review → Release" workflow. The project implements a Go-native guardrail engine (v4 "Hokage") with 13 declarative security rules, 5 verb skills (setup, plan, work, review, release), and 3 sub-agents (worker, reviewer, advisor) designed to enable solo developers, indie hackers, and teams to ship verified code with built-in quality gates.

**Key tagline** (from source): "Plan. Work. Review. Ship. Turn Claude Code into a disciplined development partner."

## Problem Addressed

The underlying problem is that Claude Code's raw capability—while powerful—lacks built-in structure and guardrails for production development workflows. Without deliberate constraints and a shared mental model (expressed in `Plans.md`), autonomous tool use becomes unpredictable and risky. Harness addresses this by:

1. **Enforcing workflow discipline** — Requires explicit planning before work, parallel review before commit, and traceable release steps.
2. **Protecting against accidental destructive operations** — 13 guardrail rules (R01–R13) block `sudo`, force-push, secret exposure, and writes outside the project, with sub-10ms response via native Go engine.
3. **Enabling rerunnable verification** — Work-All flow and validation scripts allow proof of correctness before shipping.
4. **Eliminating runtime latency** — v4 Hokage replaced bash + Node.js orchestration (~40-60ms per tool call) with a single Go binary (~10ms per hook).

**Stated benefit** (from README): "The 5 verb skills keep setup, plan, work, review, and release on one path. The Go-native guardrail engine protects execution with sub-10ms response, and validation can be rerun when you need proof."

## Key Statistics

- **Version**: 4.7.0 (released 2026-05-07, as of clone date)
- **License**: MIT (full commercial use permitted)
- **Repository stars**: Not extracted from source (README does not include badge link to live count)
- **Go runtime**: Go 1.25.0 (source: `go/go.mod`)
- **Language support**: English (default) + Japanese fully supported
- **Claude Code requirement**: v2.1+ (v2.1.105+ recommended for PreCompact hook; v2.1.111+ for xhigh effort)
- **Model recommendation**: Opus 4.7 for full v4.2 benefit (literal instruction following, vision 2576px, xhigh effort)
- **Code metrics** (v4.2): 9,176 total lines across Go cmd/harness package (including tests)
- **Agents**: 4 sub-agents (worker 14,711 chars, reviewer 6,365 chars, advisor 2,882 chars, scaffolder 2,757 chars)
- **Skills**: 20+ skill directories in primary `skills/` directory (harness-work, harness-plan, harness-review, harness-release, harness-setup, memory, breezing, etc.)

## Key Features

### 1. Guardrail Engine (Go-Native)
**Mechanism** (from source): 13 declarative rules (R01–R13) implemented in `go/internal/guardrail/` running on every tool call with sub-10ms response.

| Rule | Protected | Action |
|------|-----------|--------|
| R01 | `sudo` commands | **Deny** |
| R02 | `.git/`, `.env`, secrets | **Deny** write |
| R03 | Shell writes to protected files | **Deny** |
| R04 | Writes outside project | **Ask** |
| R05 | `rm -rf` | **Ask** |
| R06 | `git push --force` | **Deny** |
| R07–R09 | Mode-specific and secret-read guards | Context-aware |
| R10 | `--no-verify`, `--no-gpg-sign` | **Deny** |
| R11 | `git reset --hard main/master` | **Deny** |
| R12 | Direct push to `main`/`master` | **Ask** by default (configurable: ask/deny/allow) |
| R13 | Protected file edits | **Warn** |

**Example**: R06 (git push --force) is blocked entirely — force-push to any branch is refused. R12 (direct main push) is configurable but defaults to **Ask**, creating a deliberate checkpoint before mainline changes.

### 2. Workflow Verbs (5 Skills)
**Commands and scope** (from README and IMPLEMENTATION_GUIDE.md):

- **`/harness-setup`** — Project initialization; creates Plans.md, config files, hooks configuration, and skill surfaces
- **`/harness-plan`** — Transforms ideas into `Plans.md` with clear acceptance criteria and task breakdown
- **`/harness-work`** — Parallel implementation from Plans.md with preflight self-check; supports `--parallel N` workers and `breezing` agent-team mode
- **`/harness-work all`** — Full loop: approved plan → implement → review → commit (experimental; see evidence pack)
- **`/harness-review`** — 4-perspective code review (Security, Performance, Quality, Accessibility) with optional Codex second opinion
- **`/harness-release`** — CHANGELOG generation, git tag, and GitHub Release handoff

**Example workflow**: User calls `/harness-plan "add login form with email validation"` → Harness creates `Plans.md` with 3-5 subtasks. User approves. User calls `/harness-work all` → workers implement in parallel → reviewer scores each → harness commits. User calls `/harness-release` → tag + release notes published.

### 3. Sub-Agents (3 Core)
**Architecture** (from `agents/` directory and README):

- **Worker** — Implements individual tasks from Plans.md; runs preflight self-check; awaits independent review verdict. Bound by contract in v4.3+: `worker-report.v1` requires 5 self-review entries (source: CLAUDE.md).
- **Reviewer** — Performs 4-angle review (Security, Performance, Quality, Accessibility); reports verdict per perspective. Effort level: `xhigh` (CC v2.1.111, Opus 4.7) with fallback to `high` for other models.
- **Advisor** (Weak-Supervision Layer) — Optional consultative agent triggered on high-risk tasks, repeated failures, or plateau detection. Does not own final verdict; reports `PLAN`/`CORRECTION`/`STOP` signals to executor.
- **Scaffolder** — Project-generation agent (first rollout in v4.2+).

### 4. Parallel Execution with Breezing
**Feature** (from README): Agent teams running entire task lists autonomously.

```bash
/harness-work breezing all                    # Plan review + parallel implementation
/harness-work breezing --no-discuss all       # Skip plan review, implement directly
```

**Mechanism**: Phase 0 (Planning Discussion) runs by default — Planner analyzes task quality, Critic challenges the plan, then you approve before coding starts. Tasks 8+ auto-split into batches. Each batch is assigned to a parallel worker.

### 5. Session Memory Integration (harness-mem)
**Mechanism** (from README): Harness treats [harness-mem](https://github.com/Chachamaru127/harness-mem) as a managed companion.

- **Without harness-mem**: Events logged locally to `.claude/state/memory-bridge-events.jsonl`
- **With harness-mem**: Events forwarded to memory server for cross-session search and retrieval
- **Auto-setup**: Enabled by default (`CLAUDE_CODE_HARNESS_MEM_AUTO_SETUP=0` to disable)
- **Commands**: `harness mem status`, `harness mem setup`, `harness mem doctor --json`, `harness mem off`, `harness mem purge --confirm-purge`

### 6. Codex Integration
**Feature** (from README): Delegate implementation tasks to OpenAI Codex in parallel.

```bash
/harness-work --codex implement these 5 API endpoints
/harness-review --codex  # 4 perspectives + Codex second opinion
```

Requires [Codex CLI](https://github.com/openai/codex) and API key configuration.

### 7. Cursor Integration (2-Agent Mode)
**Feature** (from README): Use Cursor as PM, Claude Code as implementer. Plans.md syncs between both tools.

```bash
/harness-release handoff  # Report to Cursor PM
```

## Technical Architecture

### Core Component Hierarchy
**Source**: `go/internal/` directory structure and IMPLEMENTATION_GUIDE.md.

1. **Hook Handler Engine** (`go/internal/hookhandler/`)
   - Processes PreToolUse, SessionStart, PostToolUse, PreCompact hooks from Claude Code
   - Routes each hook to guardrail engine (R01–R13) and state manager
   - Returns permit/deny/ask verdict to Claude Code in <10ms

2. **Guardrail Engine** (`go/internal/guardrail/`)
   - 13 rules (R01–R13) evaluating command patterns, file paths, secret patterns
   - Pattern-based rule evaluation; rules are stateless (evaluate inputs at call time)
   - State-aware rules (e.g., R12 checks prior permission grants) query the state manager for session context

3. **State Manager** (`go/internal/state/`)
   - Tracks session state: active worktrees, Plans.md hash, memory events, permission history
   - Enables idempotency checks for sync operations (shell test + Go struct validation)
   - Supplies context to guardrail rules when needed (e.g., R12 checks if user has asked before)

4. **Lifecycle Manager** (`go/internal/lifecycle/`)
   - Handles PreCompact hook (blocks compaction if worker is active or Plans.md dirty)
   - Manages session init/cleanup
   - Coordinates with harness-mem on startup

5. **Breezing Engine** (`go/internal/breezing/`)
   - Task batching and parallel worker spawning
   - Plan review phase coordination (Planner + Critic)
   - Worker status monitoring and aggregation

### Data Flow
**Example: /harness-work all flow**

1. User approves Plans.md
2. Worker agent reads Plans.md, spawns 3-5 parallel workers (configurable via `--parallel`)
3. Each worker implements one task; PreToolUse hook evaluates each `curl`, `git`, `rm`, `npm install` call
4. Hook engine queries guardrail rules against command + file path + session state
5. If rule permits: command executes; PostToolUse hook logs outcome to `.claude/state/events.jsonl`
6. If rule denies: hook returns `PermissionDenied` to Claude Code; Claude Code raises permission request
7. After all workers finish: Reviewer agent reads implementation artifacts and produces 4-angle review
8. Harness commits only if all 4 review perspectives approve (configurable threshold)

### Extension Points

**Skill System**: New verbs and workflows added as directories in `skills/` with mirror sync (`bash scripts/sync-skill-mirrors.sh`).

**Hook Customization**: `hooks/hooks.json` (main) and `.claude-plugin/hooks.json` (plugin manifest) declare hook handlers; pre/post conditions are editable.

**Agent Prompt Tuning**: Agent frontmatter in `agents/*.md` includes effort level, model override, and context directives. Re-tuned in v4.2 for Opus 4.7 literal instruction following.

## Installation & Usage

### Quick Start
```bash
# Start Claude Code in your project
claude

# Add the marketplace & install
/plugin marketplace add Chachamaru127/claude-code-harness
/plugin install claude-code-harness@claude-code-harness-marketplace

# Initialize your project
/harness-setup
```

Then: `/harness-plan "your task idea"` → user approves → `/harness-work` or `/harness-work all`.

### Full Loop (Work-All)
```bash
/harness-work all
```

**Result**: Automatic Plan → Parallel Implementation → Review → Commit. (Experimental workflow; see [docs/evidence/work-all.md](docs/evidence/work-all.md) for success/failure contract.)

### Language Selection
```bash
# Default English
/harness-setup

# Or opt-in Japanese
CLAUDE_CODE_HARNESS_LANG=ja claude
```

Then `/harness-setup` bootstraps with Japanese prompts and templates.

### Session Memory (Optional)
```bash
# Enable cross-session memory
harness mem setup

# Check status
harness mem status

# Disable if not needed
harness mem off
```

### Breezing (Agent Teams)
```bash
# Full autonomous loop with Planner + Critic approval, then parallel workers
/harness-work breezing all

# Skip plan review, go straight to coding
/harness-work breezing --no-discuss all
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Command not found | Run `/harness-setup` first |
| Plugin not loading | Clear cache: `rm -rf ~/.claude/plugins/cache/claude-code-harness-marketplace/` and restart |
| Hooks not working | Run `bin/harness doctor` to diagnose (Go binary, no Node.js needed) |
| Stale v3 references after migration | Run `bin/harness doctor --residue` — auto-detects leftover references to deleted code |
| Breezing falls back to Solo mode on Windows | Update to latest build; Windows (git Bash/MSYS/Cygwin) now resolves `bin/harness-windows-amd64.exe` automatically |

## Relevance to Claude Code Development

Claude Code Harness is directly relevant to Claude Code development in these areas:

1. **Plugin Architecture Pattern** — Demonstrates complete plugin lifecycle (hooks, agents, skills, validation, versioning) conforming to Claude Code v2.1.110+ plugin schema. Serves as reference implementation for plugin structure and agent frontmatter policy.

2. **Guardrail Patterns** — Go-native implementation of declarative security rules provides a template for constraint-based execution gates. Approach of stateless rule evaluation + state tracking for permission history is generalizable to other plugin contexts.

3. **Workflow Automation** — The 5-verb skill design and Breezing agent-team coordination demonstrate practical multi-agent orchestration within Claude Code's constraint model (worktree isolation, permission model, effort tiers).

4. **Hook Integration Examples** — Comprehensive use of PreToolUse, PostToolUse, PreCompact, SessionStart hooks shows integration patterns for different lifecycle stages.

5. **Testing and Validation** — Includes 9,176 lines of Go tests across hook handlers, guardrail rules, sync idempotency checks, and template registry validation. Demonstrates best practices for plugin structural validation.

## Limitations and Caveats

1. **Experimental workflows** — The `/harness-work all` feature is documented as experimental. Source states: "Once you approve the plan, Claude runs to completion. Validate the success/failure contract in [docs/evidence/work-all.md](docs/evidence/work-all.md) before depending on it in production."

2. **Guardrail latency trade-off** — While Go engine achieves sub-10ms response, rules are declarative and stateless. Complex contextual decisions (e.g., "is this file truly outside the project?") may require path normalization or may miss edge cases with symlinks.

3. **Plan.md as Single Source of Truth** — Workflow assumes user-written Plans.md remains synchronized with git state. No automatic sync; stale plans can lead to work diverging from stated intentions. `harness sync` and `harness doctor` are provided to detect but not auto-resolve drift.

4. **Agent effort scaling** — Worker, Reviewer, and Advisor agents are tuned for Opus 4.7 with xhigh effort (v2.1.111+). Fallback to `high` on other models; performance/quality implications not documented in reviewed sources.

5. **Node.js eliminated, but Go required** — v4 removed Node.js dependency by adopting Go native engine. Users must have Go 1.25.0 or later installed to build binaries from source. Pre-built binaries (darwin-arm64/amd64, linux-amd64) ship with the plugin, reducing adoption friction, but custom builds require Go toolchain.

6. **Codex integration requires external setup** — Codex engine requires separate [Codex CLI](https://github.com/openai/codex) installation and OpenAI API key. Not documented in primary sources how to migrate existing Codex projects or costs/latency trade-offs.

7. **harness-mem is separate project** — Session memory integration points to external dependency ([harness-mem](https://github.com/Chachamaru127/harness-mem)). Auto-setup provided, but long-term maintenance and cross-session context sharing depends on external project's stability.

8. **Windows support — Breezing limitation** — Breezing agent teams require resolution of `bin/harness-windows-amd64.exe` on Windows. Git Bash/MSYS/Cygwin now support this; WSL2 users use Linux binary. Native Windows Command Prompt/PowerShell support not mentioned.

9. **Language lock-in** — Once initialized with `CLAUDE_CODE_HARNESS_LANG=ja`, project is bound to Japanese templates and prompts. Switching languages mid-project requires manual re-setup. No documented migration path.

## References

- **Repository**: <https://github.com/Chachamaru127/claude-code-harness> (accessed 2026-05-07)
- **README.md**: Full feature list, workflow examples, 5-verb diagram, benchmarks (accessed 2026-05-07)
- **License**: MIT (LICENSE.md, accessed 2026-05-07)
- **IMPLEMENTATION_GUIDE.md**: Architecture overview, Go structure, skill mirrors, validation commands (accessed 2026-05-07)
- **CLAUDE.md**: Development rules, feature utilization, permission boundaries (accessed 2026-05-07)
- **go/go.mod**: Go 1.25.0 requirement, dependencies (sqlite3, toml, uuid, humanize, strftime) (accessed 2026-05-07)
- **go/cmd/harness/**: Main entry point (651 lines), doctor (794 test lines), sync (316 + 374 test lines), validate (554 + 592 test lines) (accessed 2026-05-07)
- **agents/ directory**: worker.md (14,711 chars), reviewer.md (6,365 chars), advisor.md (2,882 chars), scaffolder.md (2,757 chars) (accessed 2026-05-07)
- **skills/ directory**: 20+ skill directories including harness-plan, harness-work, harness-review, harness-release, harness-setup, memory, breezing (accessed 2026-05-07)
- **Plugin manifest**: `.claude-plugin/plugin.json` version 4.7.0 (accessed 2026-05-07)

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|------------|---------------|-------------|
| Overview & Problem | high | 2026-05-07 | 2026-08-07 |
| Key Statistics | high | 2026-05-07 | 2026-08-07 |
| Key Features | high | 2026-05-07 | 2026-08-07 |
| Technical Architecture | high | 2026-05-07 | 2026-08-07 |
| Installation & Usage | high | 2026-05-07 | 2026-08-07 |
| Relevance to Claude Code | medium | 2026-05-07 | 2026-08-07 |
| Limitations | medium | 2026-05-07 | 2026-08-07 |

**Overall Confidence**: High (full README read, implementation guide read, Go source structure examined, agent and skill files surveyed, plugin manifest inspected). Sources are current (latest clone as of session date) and detailed.

**Data Freshness**: Version 4.7.0 released 2026-05-07 (latest commit: `d2f968c chore: mark v4.7.0 release complete`). Corresponds to Claude Code v2.1.99-2.1.110 + Opus 4.7 compatibility.

**Next Review**: 2026-08-07 (3 months). Priority topics for re-check: v4.2+ guardrail regression test count (17 mentioned for R01–R13), harness-mem integration stability, Windows Breezing support rollout completion, Codex integration examples.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | Comprehensive alternative harness: 16 agents, 65+ skills, 40+ commands, hook-based automation |
| [oh-my-claudecode](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | Multi-agent orchestration with 32 agents, natural language routing, Sisyphus persistent mode |
| [Compound Engineering Plugin](../research-agent-patterns/compound-engineering-plugin.md) | research-agent-patterns | Competing workflow plugin with Plan/Work/Review/Compound model, 27 agents |
| [Gas Town](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent workspace manager orchestrating 20-50+ Claude Code sessions via tmux |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale multi-agent orchestration with hash-anchored editing and demand-scoped MCP |
| [Orchestrator Agent Creation Guide](../research-agent-patterns/orchestrator-agent-creation-guide.md) | research-agent-patterns | Multi-agent routing, chaining, and delegation patterns applicable to harness design |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined multi-agent workflows with state machines and AI judge routing |
| [Mission Control](./mission-control.md) | agent-frameworks | 24/7 autonomous product engine: research → ideation → build → PR workflow automation |
