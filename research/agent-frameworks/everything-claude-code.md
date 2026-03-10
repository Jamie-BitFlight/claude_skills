# Everything Claude Code

**Research Date**: 2026-03-10
**Source URL**: <https://github.com/affaan-m/everything-claude-code>
**GitHub Repository**: <https://github.com/affaan-m/everything-claude-code>
**Version at Research**: 1.8.0
**License**: MIT

---

## Overview

Everything Claude Code is a comprehensive performance optimization system for AI agent harnesses, particularly Claude Code. It is a complete production-ready toolkit consisting of specialized subagents, workflow skills, automation hooks, rules, and MCP configurations. Born from an Anthropic hackathon win and refined over 10+ months of intensive daily use, it provides battle-tested patterns and workflows for building intelligent development tools across Claude Code, Cursor, OpenCode, Codex, and other AI agent harnesses.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Inconsistent AI-driven development workflows across projects | 16 specialized agents and 65+ skills provide standardized, reusable workflows for planning, code review, testing, security, and documentation |
| Memory loss and context degradation across sessions | Hook-based session persistence automatically saves and loads context across sessions |
| Token waste and inefficient model usage | Token optimization guides and techniques (system prompt slimming, background process management, model selection strategies) |
| Lack of continuous learning from development sessions | Instinct-based learning system (v2) auto-extracts patterns from sessions and converts them into reusable skills with confidence scoring |
| Fragmented security review and vulnerability management | AgentShield integration provides comprehensive security scanning with 102 rules and 1282 tests |
| Multi-language development without language-specific guidance | 6 language support (TypeScript, Python, Go, Java, C++, and more) with language-specific agents, skills, and rules |
| Cross-platform incompatibilities in automation scripts | Node.js-based cross-platform scripts for Windows, macOS, and Linux with automatic package manager detection |
| Limited multi-service orchestration | PM2 and multi-agent orchestration commands for complex workflows involving multiple services and microservices |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 50,000+ | 2026-03-10 |
| GitHub Forks | 6,000+ | 2026-03-10 |
| Contributors | 30 | 2026-03-10 |
| Latest Release | v1.8.0 | 2026-03-09 |
| GitHub App Marketplace Installs | 150 | 2026-03-10 |
| Supported Languages | 6 (TypeScript, Python, Go, Java, C++, Shell) | 2026-03-10 |
| Agent Count | 16 specialized subagents | 2026-03-10 |
| Skill Count | 65+ workflow definitions | 2026-03-10 |
| Command Count | 40+ slash commands | 2026-03-10 |
| Rule Categories | Multi-language (common, TypeScript, Python, Go) | 2026-03-10 |

---

## Key Features

### Agent System

The repository includes 16 specialized subagents designed for delegation:

- **planner.md** — Feature implementation planning and scoping
- **architect.md** — System design decisions and architecture review
- **code-reviewer.md** — Code quality, consistency, and best practices
- **security-reviewer.md** — Vulnerability analysis and security audit
- **tdd-guide.md** — Test-driven development workflow orchestration
- **python-reviewer.md** — Python-specific code review and patterns
- **go-reviewer.md** — Go code review and idiom validation
- **go-build-resolver.md** — Go build error diagnosis and resolution
- **database-reviewer.md** — Database and Supabase-specific review
- **build-error-resolver.md** — Cross-platform build error resolution
- **e2e-runner.md** — Playwright-based end-to-end testing
- **refactor-cleaner.md** — Dead code removal and refactoring
- **doc-updater.md** — Automatic documentation synchronization
- **harness-optimizer.md** — Agent harness performance tuning
- **loop-operator.md** — Continuous execution loop orchestration
- **chief-of-staff.md** — High-level orchestration and delegation

### Skills and Workflow Definitions

69 comprehensive skill modules covering:

**Backend & API Patterns**
- `backend-patterns/` — REST API design, caching, database patterns
- `api-design/` — Pagination, error responses, versioning
- `database-migrations/` — Prisma, Drizzle, Django, and Go migration patterns
- `deployment-patterns/` — CI/CD, Docker, health checks, rollbacks

**Language-Specific**
- `coding-standards/` — Language best practices (multiple languages)
- `cpp-coding-standards/` — C++ Core Guidelines compliance
- `cpp-testing/` — GoogleTest, CMake/CTest patterns
- `golang-patterns/` + `golang-testing/` — Go idioms and benchmarking
- `django-patterns/`, `django-security/`, `django-tdd/`, `django-verification/` — Django framework guidance
- `springboot-patterns/`, `springboot-security/`, `springboot-tdd/`, `springboot-verification/` — Java Spring Boot patterns
- `python-patterns/` + `python-testing/` — Python idioms and pytest
- `java-coding-standards/` + `jpa-patterns/` — Java and Hibernate patterns

**Frontend & UI**
- `frontend-patterns/` — React and Next.js patterns
- `frontend-slides/` — Zero-dependency HTML presentation builder with PPTX conversion guidance

**Continuous Learning & Optimization**
- `continuous-learning/` — Auto-extract patterns from sessions (Longform Guide)
- `continuous-learning-v2/` — Instinct-based learning with confidence scoring
- `iterative-retrieval/` — Progressive context refinement for subagents
- `strategic-compact/` — Manual compaction and token optimization suggestions

**Testing & Verification**
- `tdd-workflow/` — Test-driven development methodology across languages
- `verification-loop/` — Continuous verification and evaluation (Longform Guide)
- `eval-harness/` — Checkpoint vs. continuous evals, grader types, pass@k metrics

**Security & Infrastructure**
- `security-review/` — Security checklist and vulnerability analysis
- `security-scan/` — AgentShield integration (102 rules, 1282 tests)
- `clickhouse-io/` — ClickHouse analytics and data engineering patterns
- `postgres-patterns/` — PostgreSQL optimization patterns
- `nutrient-document-processing/` — Document processing with Nutrient API

**Content & Business**
- `article-writing/` — Long-form writing in supplied voice without generic AI tone
- `content-engine/` — Multi-platform social content and repurposing
- `market-research/` — Source-attributed market and competitor research
- `investor-materials/` — Pitch decks, one-pagers, memos, and financial models
- `investor-outreach/` — Personalized fundraising and follow-up

**Agentic Engineering**
- `agentic-engineering/` — Patterns for building agentic systems
- `agent-harness-construction/` — Agent harness design and optimization
- `autonomous-loops/` — Continuous autonomous execution patterns
- `continuous-agent-loop/` — Multi-round agentic workflows
- `ai-first-engineering/` — AI-first development methodologies

### Commands (Slash Commands)

40+ commands accessible via `/command-name` syntax, including:

- `/plan` — Feature implementation planning
- `/tdd` — Test-driven development workflow
- `/code-review` — Quality review process
- `/e2e` — E2E test generation and execution
- `/build-fix` — Build error resolution
- `/security-scan` — AgentShield security audit
- `/learn` — Pattern extraction and learning
- `/skill-create` — Generate skills from git history
- `/harness-audit` — Performance auditing
- `/loop-start`, `/loop-status` — Autonomous loop management
- `/quality-gate` — Quality verification gates
- `/model-route` — Intelligent model selection
- `/pm2`, `/multi-plan`, `/multi-execute` — Multi-service orchestration
- `/setup-pm` — Package manager configuration
- `/sessions` — Session history and management

### Hooks System

Trigger-based automations including:

- **SessionStart** — Initialize sessions with rules, instincts, and context
- **PreToolUse** — Validate tool calls, apply linting, check security
- **PostToolUse** — Update context, save state, trigger verification
- **SubagentStop** — Capture results, update session summary, compress context
- **Root fallback** — SessionStart recovery for missing context

Runtime controls:
- `ECC_HOOK_PROFILE` — Hook strictness (minimal, standard, strict)
- `ECC_DISABLED_HOOKS` — Disable specific hooks by ID

### Rules and Patterns

Multi-language rules architecture:

- `common/` — Shared rules (Git workflow, code organization, naming conventions)
- `typescript/` — TypeScript/Node.js specific rules
- `python/` — Python specific rules
- `golang/` — Go specific rules

### MCP Configurations

Integration with external Model Context Protocol servers for:

- Tool extension
- Custom integrations
- Third-party service access

---

## Technical Architecture

### Modular Plugin Architecture

Everything Claude Code is structured as a **Claude Code plugin** distributed via the GitHub Marketplace. Components are organized hierarchically:

```
agents/              — Specialized subagents (16 total)
skills/              — Workflow definitions (69+ organized by domain)
commands/            — Slash command definitions (40+)
hooks/               — Event-triggered automations (SessionStart, PreToolUse, PostToolUse, SubagentStop)
rules/               — Language-specific guidelines (common/, typescript/, python/, golang/)
mcp-configs/         — Model Context Protocol server configurations
scripts/             — Cross-platform Node.js utilities for hooks and setup
tests/               — Test suite (997 tests across agents, skills, commands, hooks)
.claude-plugin/      — Plugin metadata (plugin.json, marketplace.json)
```

### Component Interaction Model

1. **Agent Delegation** — Users invoke `/command-name` which routes to appropriate agent based on context
2. **Skill Application** — Agents load skills matching task domain using predefined skill-loading instructions
3. **Hook Execution** — SessionStart initializes context; Pre/PostToolUse hooks validate and track changes; SubagentStop captures results
4. **Context Management** — Hooks save/load context across sessions; iterative-retrieval pattern refines context for subagents
5. **Verification Loops** — Continuous or checkpoint-based evaluation against task acceptance criteria

### Package Manager Detection

Automatic detection with priority:
1. `CLAUDE_PACKAGE_MANAGER` environment variable
2. `.claude/package-manager.json` project config
3. `packageManager` field in package.json
4. Lock file detection (package-lock.json, yarn.lock, pnpm-lock.yaml, bun.lockb)
5. Global config `~/.claude/package-manager.json`
6. Fallback to first available (npm, pnpm, yarn, bun)

### Token Optimization Strategy

Documented patterns include:

- **Model Selection** — Route tasks to appropriate models based on complexity
- **System Prompt Slimming** — Remove unnecessary detail from system context
- **Background Process Management** — Offload non-critical operations
- **Context Compaction** — Strategic manual compression (strategic-compact skill)
- **Session Persistence** — Hooks maintain state across sessions reducing re-context overhead

---

## Installation & Usage

### Quick Start (Plugin Installation)

```bash
# Add marketplace
/plugin marketplace add affaan-m/everything-claude-code

# Install plugin
/plugin install everything-claude-code@everything-claude-code

# Verify installation
/plugin list everything-claude-code@everything-claude-code
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/affaan-m/everything-claude-code.git
cd everything-claude-code

# Install rules (required - plugins cannot distribute rules automatically)
./install.sh typescript    # or: python, golang, multiple languages supported
# Or for specific harness target:
# ./install.sh --target cursor typescript
```

### Usage Example

```bash
# Via plugin (namespaced form)
/everything-claude-code:plan "Add user authentication to REST API"

# Via manual install (shorter form)
/plan "Add user authentication to REST API"

# Other examples
/tdd "Build payment processing module"
/code-review "Check backend API for security"
/security-scan "Audit codebase"
/e2e "Generate Playwright tests for checkout flow"
/learn "Extract patterns from this session"
```

### Environment Configuration

```bash
# Set package manager preference
export CLAUDE_PACKAGE_MANAGER=pnpm

# Configure hook strictness
export ECC_HOOK_PROFILE=standard    # or: minimal, strict

# Disable specific hooks
export ECC_DISABLED_HOOKS="pre:bash:tmux-reminder,post:edit:typecheck"

# Detect current settings
node scripts/setup-package-manager.js --detect
```

---

## Relevance to Claude Code Development

### Applications

1. **Skill Architecture Patterns** — The 65+ skill organization by domain (coding-standards, backend-patterns, frontend-patterns, security-review, etc.) provides a scalable template for structuring Claude Code skills. The conditional activation and hook-based loading model directly applies to our skill system.

2. **Multi-Agent Orchestration** — ECC's agent delegation model (chief-of-staff coordinating 16 subagents, dependency tracking, progressive context refinement via iterative-retrieval) is a proven reference implementation for complex multi-step workflows in Claude Code.

3. **Hook System Design** — The SessionStart→PreToolUse→PostToolUse→SubagentStop execution model with runtime controls (`ECC_HOOK_PROFILE`, `ECC_DISABLED_HOOKS`) demonstrates how to build extensible, debuggable automation hooks without script fragility.

4. **Token Optimization** — ECC's documented strategies (model selection, system prompt slimming, context compaction, strategic session persistence) directly address the context window constraints we face in our skills.

5. **Cross-Platform Portability** — Node.js-based scripts and automatic package manager detection provide reusable patterns for supporting Windows, macOS, and Linux without conditional logic per platform.

6. **Continuous Learning** — Instinct-based learning (continuous-learning-v2 skill) with confidence scoring and import/export shows how to build knowledge extraction from sessions into reusable assets.

### Patterns Worth Adopting

1. **Language-Specific Rule Stratification** — Separate common/ + language/ directory structure allows users to install only rules relevant to their tech stack, reducing noise and improving performance.

2. **Modular Command Namespacing** — Commands like `/everything-claude-code:plan` when installed as plugins, or `/plan` when manually installed, allow graceful degradation and coexistence with other plugins.

3. **Skill Activation Instructions in Agent Prompts** — Instead of hard-coding skill loading in orchestration, ECC includes skill names in ready-task JSON, allowing agents to load skills explicitly. This prevents silent skill misses.

4. **Session Summaries in Hook SubagentStop Phase** — Rather than losing context when subagents complete, ECC's hooks capture a summary of what was done, allowing parent agents to make informed routing decisions.

5. **Verification Loop Taxonomy** — ECC distinguishes checkpoint (gate at end) vs. continuous (monitor throughout) evaluation, with grader types (unit, integration, E2E) and pass@k metrics. This provides a language for discussing evaluation strategy.

6. **Instinct-Based Pattern Extraction** — Instead of storing unstructured session logs, ECC extracts confidence-scored instincts (Action, Evidence, Examples) that can be merged, versioned, and fed back into future agent prompts.

### Integration Opportunities

1. **Research Entry Automation** — ECC's `/learn` command and instinct-based learning could feed into our research-curator agent, auto-generating research entry sections from extracted patterns and evidence.

2. **Hook Reuse** — SessionStart initialization, PreToolUse validation, and PostToolUse context capture can be adapted for our implementation-manager hooks (task_status_hook.py), reducing drift between ECC and claude_skills hook behavior.

3. **Skill Library Expansion** — Our research entries could be supplemented by ECC skill patterns, and ECC's continuous-learning-v2 could extract verified patterns from our implementation sessions.

4. **Multi-Language Rule Adoption** — Adopt ECC's common/ + language/ stratification for our rules/ directory, allowing users installing claude_skills to select only relevant rule sets.

5. **Agent Delegation Template** — ECC's chief-of-staff agent pattern (high-level orchestration coordinating multiple subagents) maps directly to our implementation-manager skill's ready-task query and loop orchestration.

6. **GitHub App Marketplace Model** — ECC's dual distribution (direct plugin install + GitHub Marketplace app) with free/pro/enterprise tiers demonstrates a viable monetization model for Claude Code plugins.

---

## Limitations and Caveats

1. **Plugin Dependency for Rules** — "Claude Code plugins cannot distribute `rules` automatically" (stated in Quick Start). Users must manually run `./install.sh` to install rules, which is a friction point for adoption. Automation of rule installation to `.claude/rules` via plugin hooks is currently not supported by Claude Code.

2. **Hook Reliability Edge Cases** — While v1.8.0 adds "SessionStart root fallback" and "Stop-phase session summaries," complex hook interactions across pre-commit, post-edit, and tool-use phases may conflict with user-defined hooks or third-party plugins. The `ECC_HOOK_PROFILE` runtime control is a workaround, not a solution.

3. **Package Manager Detection Overhead** — The 6-step package manager detection process (env var → project config → package.json → lock file → global config → fallback) adds latency on every tool invocation. No caching of detection results is mentioned.

4. **Cross-Harness Parity Declared but Not Verified** — Documentation states "Cross-harness parity — behavior tightened across Claude Code, Cursor, OpenCode, and Codex app/CLI" but no compatibility matrix, version skew testing, or regression test data is provided. Harness API differences (e.g., hook event types) may still cause breakage.

5. **Skill Hot-Load Failure Modes Undocumented** — v1.8.0 mentions "NanoClaw v2 — model routing, skill hot-load" but skill loading errors, timing constraints (cold starts), and recovery from partial loads are not documented.

6. **No Offline Mode** — All agent dispatch, skill routing, and hook execution appear to require Claude Code connectivity. Offline skill caching or edge execution is not mentioned.

7. **Test Coverage Limited to Script/Utility Layers** — "997 internal tests passing" refers to agents, skills, commands, and hooks; however, integration tests between agents (orchestration correctness) and end-to-end plugin installation tests are not itemized.

8. **Context Refinement Strategy Conflicts with Model Window** — ECC's iterative-retrieval and continuous-learning-v2 skills aim to reduce context bloat, but both operate through hook accumulation. Long sessions may still exceed token budgets before compaction runs.

---

## References

- [Everything Claude Code GitHub Repository](https://github.com/affaan-m/everything-claude-code) (accessed 2026-03-10)
- [Everything Claude Code README](https://github.com/affaan-m/everything-claude-code/blob/main/README.md) (accessed 2026-03-10)
- [CLAUDE.md — Project Guidance](https://github.com/affaan-m/everything-claude-code/blob/main/CLAUDE.md) (accessed 2026-03-10)
- [Plugin Manifest](https://github.com/affaan-m/everything-claude-code/blob/main/.claude-plugin/plugin.json) (accessed 2026-03-10)
- [GitHub Marketplace — ECC Tools](https://github.com/marketplace/ecc-tools) (accessed 2026-03-10)
- [MIT License](https://github.com/affaan-m/everything-claude-code/blob/main/LICENSE) (accessed 2026-03-10)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-10 |
| Version at Verification | 1.8.0 (released 2026-03-09) |
| Next Review Recommended | 2026-06-10 |

**Confidence Summary**

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Official plugin.json, LICENSE, and GitHub stats directly extracted |
| Features | high | 16 agents and 69 skills enumerated from directory listing and README |
| Architecture | medium | Hook and orchestration model inferred from documentation; no source code examination of hook script implementation |
| Usage Examples | medium | Installation and command examples from Quick Start section; no end-to-end testing performed |
| Limitations | low | Constraints inferred from documentation (e.g., "plugins cannot distribute rules") without testing; hook edge cases and cross-harness parity claims not independently verified |

**Calibration**: High-activity repository (50K+ stars, 6K+ forks, 30 contributors, recent v1.8.0 release on 2026-03-09). Recommend 4-week review cycle for tracking breaking API changes, new skill additions, and hook reliability improvements.
