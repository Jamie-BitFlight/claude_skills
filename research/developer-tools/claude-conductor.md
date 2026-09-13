---
name: Claude Conductor - Context-Driven Development Plugin for Claude Code
description: Claude Conductor is a Claude Code plugin that implements Context-Driven Development (CDD), a structured lifecycle for software projects following a strict Context -> Spec & Plan -> Implement...
license: Apache-2.0
metadata:
  topic: claude-conductor
  category: developer-tools
  source_url: https://github.com/rbarcante/claude-conductor
  github: rbarcante/claude-conductor
  version: "v1.2.1"
  verified: "2026-02-17"
  next_review: "2026-05-17"
---

## Overview

Claude Conductor is a Claude Code plugin that implements Context-Driven Development (CDD), a structured lifecycle for software projects following a strict Context -> Spec & Plan -> Implement workflow. It acts as a proactive project manager layered on top of Claude Code, enforcing consistent artifact generation (product context, tech stack, specs, plans, Architecture Decision Records) before any code is written. The project is a derivative adaptation of the Conductor Extension for Gemini CLI, ported and extended for Claude Code's plugin architecture with additional skill ecosystems, quality intelligence, and pattern reference layers.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding agents write code without fully understanding project context, producing inconsistent output | `/conductor:setup` generates managed context artifacts (product.md, tech-stack.md, workflow.md) that persist as source of truth for all agent interactions |
| Features are implemented without upfront specification, leading to rework | `/conductor:newTrack` forces spec.md + plan.md generation before any implementation begins |
| Brownfield projects have undocumented conventions that AI agents miss | Codebase Pattern Analysis automatically detects and documents naming, architecture, testing, and API patterns with confidence scoring |
| AI agents cannot revert logical units of work cleanly | `/conductor:revert` understands tracks, phases, and tasks rather than raw commit hashes |
| Relevant best-practice patterns are not surfaced contextually during implementation | Pattern Reference Layer uses keyword activation to surface patterns (error handling, logging, validation) at task time |
| Architectural decisions are lost; the "why" is undocumented | ADR logging in `decisions.md` captures option tradeoffs and rationale per track |
| Code quality issues are found only at review time | Anti-pattern detection (god objects, mutable defaults, cyclomatic complexity, magic numbers) runs during `/conductor:implement` |
| Token overhead from eager skill loading slows workflows | Lazy skill loading and SKILL-SUMMARY files reduce token consumption by up to 74% in newTrack workflow |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 34 | 2026-02-17 |
| Forks | 2 | 2026-02-17 |
| Contributors | 1 (+ 2 bots) | 2026-02-17 |
| Open Issues | 0 | 2026-02-17 |
| Primary Language | Python | 2026-02-17 |
| Latest Release | v1.2.1 | 2026-02-17 |
| Repository Created | 2026-01-23 | 2026-02-17 |
| Last Push | 2026-02-17 | 2026-02-17 |
| Total Commits (main author) | 352 | 2026-02-17 |

---

## Key Features

### Context Management

- **Project setup command** (`/conductor:setup`): Scaffolds `conductor/` directory with product.md, product-guidelines.md, tech-stack.md, workflow.md, tracks.md, and index.md
- **Greenfield and brownfield support**: Separate initialization paths; brownfield path includes automatic stack detection and codebase pattern analysis
- **Universal File Resolution Protocol (UFRP)**: Navigation index files (`conductor/index.md`, `conductor/tracks/<id>/index.md`) decouple command logic from physical file layout, allowing custom directory structures
- **Technology detection**: Reads manifest files and file extensions to identify language, frameworks, build tools, testing frameworks, and package managers with HIGH/MEDIUM/LOW/UNCERTAIN confidence levels

### Track-Based Development Workflow

- **Track abstraction**: A track is a named unit of work (feature or bug) with its own `spec.md`, `plan.md`, `decisions.md`, `metadata.json`, and `index.md` under `conductor/tracks/<track_id>/`
- **Spec before plan**: The `newTrack` command generates requirements specification (what and why) before the actionable plan (phases, tasks, sub-tasks)
- **Phase-gated implementation**: `/conductor:implement` selects the next pending task, executes it following the configured workflow (e.g., TDD), and prompts manual verification at phase boundaries
- **Git-aware revert**: `/conductor:revert` analyzes git history to understand logical work units, allowing revert of a track, phase, or specific task rather than a commit hash

### Pattern Reference Layer

- **Keyword-activated patterns**: During `/conductor:implement`, task descriptions are matched against pattern activation keywords; matched patterns are surfaced interactively before the task begins
- **Core patterns included**: Error Handling, Logging, Configuration, Validation, Testing
- **Stack-specific patterns**: Organized under `patterns/core/` and `patterns/stack/` directories
- **Dual-format standard**: Every pattern file includes an AI Quick Reference section (max 30-50 lines of tables and bullet lists) followed by full Human Documentation

### Skill Ecosystem

- **Skill registry**: `skills/skill-registry.json` tracks available skills with activation rules (keywords, file patterns, language, framework, tool matches)
- **Activation scoring**: Skills scored per task context; keyword match +1.0, file pattern +1.5, language match +2.0, framework match +1.5, tool match +1.0; threshold >= 1.5 activates (max 5 context-activated per task)
- **Always-active skills**: `conductor-methodology` skill loaded for every task regardless of scoring
- **Lazy loading protocol**: SKILL-SUMMARY lightweight files loaded first; full SKILL.md loaded only when needed; reduces token consumption by ~74% in newTrack workflow
- **Reference skills included**: `typescript-best-practices`, `api-design`, `testing-strategies`, each with domain-specific pattern sub-files
- **Skills management command** (`/conductor:skills`): list, info, enable, disable skills; per-project overrides stored in `conductor/settings.json`

### Quality Intelligence

- **Anti-pattern detection**: Scans modified files during implementation; severity levels Critical (blocks), High (warns + documented skip required), Medium (informational)
- **Detected anti-patterns**: God Object (classes >500 lines or >20 methods), Mutable Defaults (`def f(x=[])` patterns), Spaghetti Code (cyclomatic complexity >15), Magic Numbers, Deep Nesting (>4 levels)
- **Coverage intelligence**: Reads LCOV, Cobertura XML, Istanbul JSON, Coverage.py, and Go Cover formats to suggest prioritized tests based on business impact and coverage gain
- **Skip documentation**: Skipped quality gate warnings are documented in the track decisions log with reason and reviewer

### Decision Logging

- **ADR per track**: `conductor/tracks/<id>/decisions.md` captures Architecture Decision Records in standard ADR format (Context, Decision, Consequences, Alternatives Considered)
- **Interactive prompts**: During implementation, Conductor detects significant decision points (library selection, pattern choice, API design) and presents structured options with tradeoff analysis
- **Auto-skip trivial choices**: Choices dictated by spec, with only one viable option, or easily reversible are not prompted

### Code Review and Snippet Library

- **`/conductor:codeReview`**: Parallel sub-agents perform code quality analysis, security scanning (OWASP-aligned), and test coverage analysis against a base branch
- **Snippet library** (`/conductor:snippet`): Searchable, browsable library of reusable code snippets with AI headers (`USE:`, `REQUIRES:`, `PATTERN:` fields)
- **Snippet categories**: TypeScript (api-client, error-handler, type-guard, async-wrapper, config-loader), Python (api-client, error-handler, dependency-injection, config-loader, async-patterns), Patterns (repository-pattern, factory-pattern)

---

## Technical Architecture

<eg>
Claude Code Plugin Architecture
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                  Claude Conductor                    │
│                                                     │
│  Commands (.claude-plugin/commands/)                │
│  ┌────────────┬──────────────┬──────────────────┐   │
│  │  /setup    │  /newTrack   │  /implement       │   │
│  │  /status   │  /revert     │  /codeReview      │   │
│  │  /patterns │  /skills     │  /snippet         │   │
│  └─────┬──────┴──────────────┴──────────┬────────┘   │
│        │                                │            │
│        ▼                                ▼            │
│  ┌──────────────────┐    ┌────────────────────────┐  │
│  │  Context Layer   │    │  Skill Ecosystem        │  │
│  │  conductor/      │    │  skills/                │  │
│  │  ├ product.md    │    │  ├ conductor-methodology │  │
│  │  ├ tech-stack.md │    │  ├ typescript-best-prac  │  │
│  │  ├ workflow.md   │    │  ├ api-design            │  │
│  │  └ tracks/       │    │  └ testing-strategies    │  │
│  │    └ <id>/       │    │  skill-registry.json     │  │
│  │      ├ spec.md   │    │  (keyword activation     │  │
│  │      ├ plan.md   │    │   scoring engine)        │  │
│  │      ├ decisions │    └────────────────────────┘  │
│  │      └ index.md  │                                │
│  └──────────────────┘                                │
│                                                     │
│  ┌──────────────────┐    ┌────────────────────────┐  │
│  │  Pattern Layer   │    │  Quality Intelligence   │  │
│  │  patterns/       │    │  Anti-pattern detection │  │
│  │  ├ core/         │    │  Coverage analysis      │  │
│  │  ├ stack/        │    │  (LCOV, Cobertura,      │  │
│  │  └ anti-patterns │    │   Istanbul, Coverage.py) │  │
│  └──────────────────┘    └────────────────────────┘  │
│                                                     │
│  Parallel Sub-Agents (v1.1.0+)                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  code-quality-analyzer  │  security-scanner    │  │
│  │  test-coverage-analyzer │  git-history-analyst │  │
│  │  codebase-pattern-detector                     │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
        │
        ▼
  conductor/ directory in user's project (managed artifacts)
</eg>

**Key design decisions**:

- All conductor artifacts are committed alongside code; the `conductor/` directory is the single source of truth
- The UFRP (`index.md` navigation files) decouples command logic from physical file layout, enabling project-specific directory customization without breaking any commands
- Lazy skill loading (SKILL-SUMMARY pattern) reduces token overhead from skill context; full SKILL.md loaded on demand
- Parallel sub-agents in codeReview, implement, revert, and setup commands (added in v1.1.0) run analysis concurrently rather than sequentially

---

## Installation & Usage

### Installation via Marketplace

```bash
# Add the conductor marketplace
/plugin marketplace add rbarcante/claude-conductor

# Install the plugin
/plugin install conductor@claude-conductor
```

### Manual Installation

```bash
# Project-specific: copy plugin to Claude plugins directory
cp -r claude-conductor ~/.claude/plugins/conductor

# Or use plugin-dir flag for a session
claude --plugin-dir /path/to/claude-conductor
```

### Development Setup

```bash
git clone https://github.com/rbarcante/claude-conductor.git
cd claude-conductor

python3 -m venv .venv
source .venv/bin/activate

pip install -r scripts/requirements-dev.txt

# Run tests
pytest scripts/tests/ -v

# Run with coverage
pytest scripts/tests/ --cov=scripts --cov-report=html
```

### Typical Workflow

```bash
# 1. One-time project setup (run in your project root)
/conductor:setup

# 2. Start a new feature track
/conductor:newTrack "Add dark mode toggle to settings page"

# 3. Review generated spec.md and plan.md, then implement
/conductor:implement

# 4. Check progress
/conductor:status

# 5. Browse patterns relevant to current work
/conductor:patterns search "error handling"

# 6. Run code review against main branch
/conductor:codeReview

# 7. Revert a track if needed
/conductor:revert
```

### Commands Reference

| Command | Purpose |
|---------|---------|
| `/conductor:setup` | Scaffold project context artifacts; detect stack for brownfield projects |
| `/conductor:newTrack [description]` | Create spec.md and plan.md for a new feature or bug |
| `/conductor:implement` | Execute tasks from the current track's plan with quality gates |
| `/conductor:status` | Display progress across all tracks |
| `/conductor:revert` | Undo a track, phase, or task using git history analysis |
| `/conductor:codeReview` | Run parallel sub-agents for code quality, security, and coverage review |
| `/conductor:patterns [list\|search\|show]` | Browse the Pattern Reference Layer |
| `/conductor:skills [list\|info\|enable\|disable]` | Manage skill ecosystem |
| `/conductor:snippet [list\|search\|show]` | Browse the snippet library |

---

## Relevance to Claude Code Development

### Direct Applications

- **Context-Driven Development methodology**: The CDD pattern (context artifacts committed alongside code, spec before implementation, managed track lifecycle) is directly applicable to any Claude Code plugin or skill development workflow
- **Skill ecosystem design**: Conductor's skill activation scoring (keyword, file pattern, language, framework, tool match weights) is a concrete implementation pattern for context-aware skill loading - directly applicable to how this skills repository structures context delivery
- **SKILL-SUMMARY lazy loading pattern**: The two-tier skill loading (summary file loaded by default, full file loaded on demand) is a validated technique for managing token budgets in large skill ecosystems
- **Parallel sub-agent architecture**: Conductor's use of specialist sub-agents (code-quality-analyzer, security-scanner, test-coverage-analyzer) running concurrently during codeReview demonstrates an effective multi-agent decomposition pattern for code analysis tasks

### Patterns Worth Adopting

- **Dual-format documentation standard**: AI Quick Reference section (max 30-50 lines, tables and bullets) followed by full human documentation - this pattern maps directly to the skill documentation philosophy in this repository
- **UFRP index files**: Decoupling command logic from physical file paths via navigation index files prevents file organization changes from breaking automation - applicable to how research entries or skill manifests are resolved
- **Activation scoring with threshold**: Weighted scoring across multiple signal types (keyword, file, language, framework, tool) with a minimum activation threshold provides controllable, context-sensitive behavior without hard-coded rules
- **ADR-per-track**: Capturing decision rationale as a first-class artifact alongside spec and plan prevents knowledge loss; applicable to skill development decisions and agent design choices
- **Anti-pattern YAML frontmatter**: Defining anti-patterns with severity, detection patterns (regex), file extensions, and activation keywords in structured YAML is reusable for any code quality tooling

### Integration Opportunities

- **Conductor as a reference implementation**: Study Conductor's plugin structure (commands/, agents/, skills/, patterns/, protocols/, snippets/, templates/) as a mature example of Claude Code plugin organization
- **Pattern Reference Layer**: The patterns included (`patterns/core/error-handling.md`, `patterns/core/logging.md`, etc.) could serve as reference material for quality standards in this repository's skills
- **Codebase Pattern Analysis agent**: The `codebase-pattern-detector` sub-agent's approach to detecting naming conventions, architecture layers, and testing patterns with confidence scoring is a reusable pattern for any agent that needs to understand an unfamiliar codebase
- **Token optimization techniques**: Conductor's 74% reduction in token consumption for the newTrack workflow (lazy skill loading, SKILL-SUMMARY files, fast-path branch checks) documents concrete techniques applicable to any skill that loads significant context

### Relationship to This Repository

Conductor is a direct peer to the claude_skills repository: both are Claude Code plugin ecosystems. Conductor focuses on project management lifecycle (spec, plan, implement, review), while claude_skills focuses on skill/agent creation and knowledge management. The two are complementary rather than overlapping. Conductor's marketplace.json format, plugin structure, and command naming conventions follow the same Claude Code plugin architecture used here.

---

## References

1. **GitHub Repository**: <https://github.com/rbarcante/claude-conductor> (accessed 2026-02-17)
2. **README.md (master branch)**: <https://raw.githubusercontent.com/rbarcante/claude-conductor/master/README.md> (accessed 2026-02-17)
3. **CHANGELOG.md**: <https://raw.githubusercontent.com/rbarcante/claude-conductor/master/CHANGELOG.md> (accessed 2026-02-17)
4. **Marketplace manifest (.claude-plugin/marketplace.json)**: <https://raw.githubusercontent.com/rbarcante/claude-conductor/master/.claude-plugin/marketplace.json> (accessed 2026-02-17)
5. **GitHub API - Repository metadata**: <https://api.github.com/repos/rbarcante/claude-conductor> (accessed 2026-02-17)
6. **GitHub API - Contributors**: <https://api.github.com/repos/rbarcante/claude-conductor/contributors> (accessed 2026-02-17)
7. **Original upstream project (Gemini CLI)**: <https://github.com/gemini-cli-extensions/conductor> (referenced in README NOTICE section)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [stop-slop](../ai-writing-tools/stop-slop.md) | ai-writing-tools | referenced by stop-slop (ai-writing-tools) |
| [claude-replay](../coding-agents/claude-replay.md) | coding-agents | referenced by claude-replay (coding-agents) |
| [agent-deck](./agent-deck.md) | developer-tools | referenced by agent-deck (developer-tools) |
| [ghost-desk](./ghost-desk.md) | developer-tools | referenced by ghost-desk (developer-tools) |
