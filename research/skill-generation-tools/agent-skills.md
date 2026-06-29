---
title: Agent Skills
subtitle: Production-grade engineering skills for AI coding agents following Google engineering practices
category: skill-generation-tools
resource_url: https://github.com/addyosmani/agent-skills
github_url: https://github.com/addyosmani/agent-skills
date_created: "2026-05-10"
date_last_reviewed: "2026-06-18"
status: published
---

# Agent Skills

**Production-grade engineering skills for AI coding agents** — a structured skills library that guides AI agents through software development workflows following senior engineer practices from Google's software engineering culture.

## Resource Identity

- **Name**: Agent Skills
- **Creator**: Addy Osmani
- **Repository**: <https://github.com/addyosmani/agent-skills>
- **Version**: 0.6.2 (released 2026-06-11, as of 2026-06-18)
- **License**: MIT License
- **GitHub Stars**: 62,349 (as of 2026-06-18)
- **Forks**: 6,761 (as of 2026-06-18)

## Problem Addressed

AI coding agents default to the shortest path when building software — often skipping specs, tests, security reviews, and the engineering discipline that produces reliable production code. Agent Skills solves this by encoding the workflows, quality gates, and best practices that senior engineers use, making them consistently executable by AI agents across every phase of development.

The repository explicitly states: "Skills encode the workflows, quality gates, and best practices that senior engineers use when building software. These ones are packaged so AI agents follow them consistently across every phase of development."

## Overview

Agent Skills is a collection of 24 skills organized by development phase (Define, Plan, Build, Verify, Review, Ship) plus a meta-skill for discovery. Each skill encodes a specific engineering process as a step-by-step workflow that agents follow, not abstract advice they might skip.

### Core Skills by Lifecycle Phase

**Meta/Discovery (1 skill):**
- `using-agent-skills` — Maps incoming work to the right skill and establishes core operating behaviors

**Define (3 skills):**
- `interview-me` — One-question-at-a-time interview extracting actual user needs to ~95% confidence
- `idea-refine` — Structured divergent/convergent thinking to turn vague ideas into concrete proposals
- `spec-driven-development` — PRD writing covering objectives, commands, structure, code style, testing, and boundaries before coding

**Plan (1 skill):**
- `planning-and-task-breakdown` — Decompose specs into small, verifiable tasks with acceptance criteria and dependency ordering

**Build (7 skills):**
- `incremental-implementation` — Thin vertical slices with feature flags and safe defaults
- `test-driven-development` — Red-Green-Refactor with test pyramid (80/15/5), DAMP over DRY, Beyonce Rule
- `context-engineering` — Feed agents the right information at the right time via rules files and MCP integrations
- `source-driven-development` — Ground every framework decision in official documentation with verification and source citations
- `doubt-driven-development` — Adversarial fresh-context review of high-stakes decisions (CLAIM → EXTRACT → DOUBT → RECONCILE → STOP)
- `frontend-ui-engineering` — Component architecture, design systems, state management, responsive design, WCAG 2.1 AA accessibility
- `api-and-interface-design` — Contract-first design, Hyrum's Law, One-Version Rule, error semantics, boundary validation

**Verify (2 skills):**
- `browser-testing-with-devtools` — Chrome DevTools MCP for live runtime data (DOM inspection, console logs, network traces, performance profiling)
- `debugging-and-error-recovery` — Five-step triage: reproduce, localize, reduce, fix, guard; stop-the-line rule; safe fallbacks

**Review (4 skills):**
- `code-review-and-quality` — Five-axis review, change sizing (~100 lines), severity labels (Nit/Optional/FYI), review speed norms
- `code-simplification` — Chesterton's Fence, Rule of 500, reduce complexity while preserving exact behavior
- `security-and-hardening` — OWASP Top 10 prevention, auth patterns, secrets management, dependency auditing, three-tier boundary system
- `performance-optimization` — Measure-first approach, Core Web Vitals targets, profiling workflows, bundle analysis

**Ship (6 skills):**
- `git-workflow-and-versioning` — Trunk-based development, atomic commits (~100 lines), commit-as-save-point pattern
- `ci-cd-and-automation` — Shift Left principle, Faster is Safer, feature flags, quality gate pipelines, failure feedback loops
- `deprecation-and-migration` — Code-as-liability mindset, compulsory vs advisory deprecation, migration patterns, zombie code removal
- `documentation-and-adrs` — Architecture Decision Records, API docs, inline documentation standards (document the *why*)
- `observability-and-instrumentation` — Structured logging, RED metrics, OpenTelemetry tracing, symptom-based alerting
- `shipping-and-launch` — Pre-launch checklists, feature flag lifecycle, staged rollouts, rollback procedures, monitoring setup

## Technical Architecture

**Entry Point**: Seven slash commands (`/spec`, `/plan`, `/build`, `/test`, `/review`, `/code-simplify`, `/ship`) that map to development lifecycle phases, automatically triggering relevant skills.

**Core Design Pattern**: Every skill follows the same anatomy:

1. **YAML frontmatter** — Defines `name` (kebab-case) and `description` (what it does + trigger conditions)
2. **Overview** — Elevator pitch explaining what the skill does and why it matters
3. **When to Use** — Positive triggers and negative exclusions (when NOT to apply)
4. **Process** — Step-by-step workflow with decision trees and code examples
5. **Common Rationalizations** — Table of excuses agents use to skip steps, paired with rebuttals
6. **Red Flags** — Observable behavioral patterns indicating the skill is being violated
7. **Verification** — Checklist of exit criteria with evidence requirements

**Progressive Disclosure**: The primary `SKILL.md` file in each skill directory is the entry point. Supporting references (checklists, testing patterns, security checklists, accessibility patterns) load only when needed, keeping token usage minimal.

**Specialist Personas**: Four agent personas provide targeted review perspectives:
- `code-reviewer.md` — Senior Staff Engineer (five-axis code review)
- `test-engineer.md` — QA Specialist (test strategy and coverage analysis)
- `security-auditor.md` — Security Engineer (vulnerability detection and threat modeling)
- `web-performance-auditor.md` — Web Performance Engineer (Core Web Vitals audit with `/webperf` command)

**Supporting References** (4 shared checklists):
- `testing-patterns.md` — Test structure, naming, mocking, React/API/E2E examples, anti-patterns
- `security-checklist.md` — Pre-commit checks, auth, input validation, headers, CORS, OWASP Top 10
- `performance-checklist.md` — Core Web Vitals targets, frontend/backend checklists, measurement commands
- `accessibility-checklist.md` — Keyboard navigation, screen readers, visual design, ARIA, testing tools

**Integration Points**:
- Claude Code: Native plugin via `.claude/commands/` for slash commands and `.claude/skills/` for skill discovery
- Cursor: Copy SKILL.md files into `.cursor/rules/` or reference the full `skills/` directory
- Antigravity CLI: Native plugin installation with dedicated `commands/` directory (8 slash commands)
- Gemini CLI: Native skill installation via `gemini skills install`
- Windsurf: Skill contents added to rules configuration
- Kiro IDE & CLI: Skills under `.kiro/skills/` at project or global level
- OpenCode: Agent-driven skill execution via AGENTS.md
- GitHub Copilot: Agent definitions as personas, skill content in `.github/copilot-instructions.md`
- Any agent system: Plain Markdown skills work with any system accepting system prompts or instruction files

**Session Lifecycle**: The `session-start.sh` hook injects the `using-agent-skills` meta-skill into every new Claude Code session via JSON payload (with fallback when `jq` is unavailable).

## Key Features

### 1. Anti-Rationalization Tables
Every skill includes a "Common Rationalizations" section — excuses agents use to skip important steps, paired with factual rebuttals. Examples:
- "I'll add tests later" → countered with evidence that up-front testing prevents rework
- "This is simple enough to skip the spec" → countered with cost of rework from missed requirements

### 2. Autonomous Skill Execution (`/build auto`)
The framework supports autonomous task execution where agents follow the plan without human stepping between tasks: `/build auto` generates the plan and implements every task in a single approved pass. Tasks are still test-driven and committed individually; execution pauses on failures or risky steps.

### 3. Verification-First Design
No skill is complete until verification passes. Every skill ends with a checklist of evidence requirements (test output, build results, runtime data). "Seems right" is never sufficient.

### 4. Bounded Workflow Steps
Processes are concrete and measurable, not vague. Instead of "make sure the code is tested," a skill specifies "run `npm test` and verify all tests pass with coverage ≥80%."

### 5. Lifecycle-Aware Skill Discovery
The `using-agent-skills` meta-skill provides a decision tree that maps incoming work to the right skill based on development phase, requirements clarity, and task scope.

### 6. Operating Behaviors Across All Skills
Six core behaviors apply universally (Surface Assumptions, Manage Confusion Actively, Push Back When Warranted, Enforce Simplicity, Maintain Scope Discipline, Verify Don't Assume).

### 7. Google Engineering Culture Foundation
Skills explicitly incorporate patterns from:
- Hyrum's Law (API design skill)
- Beyonce Rule and test pyramid (TDD skill)
- Change sizing and review speed norms (code review skill)
- Chesterton's Fence (simplification skill)
- Trunk-based development (git workflow skill)
- Shift Left and feature flags (CI/CD skill)
- Code-as-liability mindset (deprecation skill)

### 8. Multi-Tool Integration Breadth
Skills work across 8+ platforms (Claude Code, Cursor, Antigravity, Gemini, Windsurf, Kiro, OpenCode, Copilot, and any agent system accepting Markdown instructions). Each platform gets targeted setup guides in `docs/`.

## Installation & Usage

### Claude Code (Recommended)

**Marketplace installation:**

```bash
/plugin marketplace add addyosmani/agent-skills
/plugin install agent-skills@addy-agent-skills
```

**Local development:**

```bash
git clone https://github.com/addyosmani/agent-skills.git
claude --plugin-dir /path/to/agent-skills
```

### Antigravity CLI

**From repository:**

```bash
agy plugin install https://github.com/addyosmani/agent-skills.git
```

**From local clone:**

```bash
git clone https://github.com/addyosmani/agent-skills.git
agy plugin install ./agent-skills
```

### Other Tools

- **Cursor**: Copy SKILL.md files to `.cursor/rules/` or reference `skills/` directory
- **Gemini CLI**: `gemini skills install https://github.com/addyosmani/agent-skills.git --path skills` or `gemini skills install ./agent-skills/skills/`
- **Windsurf**: Add skill contents to Windsurf rules configuration
- **Kiro IDE**: Skills under `.kiro/skills/` at project or global level
- **OpenCode**: Agent-driven execution via AGENTS.md and skill tool
- **GitHub Copilot**: Agent definitions in `agents/` directory and skill content in `.github/copilot-instructions.md`
- **Any agent system**: Skills are plain Markdown — add to system prompts or instruction files

### Using Skills in Sessions

Slash commands activate skills:
- `/spec` → `spec-driven-development`
- `/plan` → `planning-and-task-breakdown`
- `/build` → `incremental-implementation`
- `/test` → `test-driven-development`
- `/review` → `code-review-and-quality`
- `/code-simplify` → `code-simplification`
- `/ship` → `shipping-and-launch`

Or reference any skill directly in the `using-agent-skills` meta-skill discovery flow. The framework automatically routes to secondary skills based on context (e.g., UI work triggers `frontend-ui-engineering`, API work triggers `api-and-interface-design`).

## Limitations and Caveats

### Architectural Limitations

1. **Documentation project only** — Agent Skills is a pure documentation collection with no code execution engine, testing harness, or validation tooling. Integration with agent systems is manual or via plugin system (except for Claude Code and Antigravity which support native plugins).

2. **Skills assume English-first workflows** — All skills are written in English and assume command-line tools and development practices common to English-speaking software engineering communities. Cross-cultural workflows or non-English tooling are not addressed.

3. **No formalized metrics for skill effectiveness** — The repository does not publish data on skill adoption, success rates, or measurable improvements to code quality or development velocity. Effectiveness is asserted in the README but not quantified.

4. **Agent integration requires per-tool setup** — While 8 platforms are supported, each requires tool-specific installation (Claude Code plugin, Antigravity plugin, Cursor copy-paste, Gemini CLI command, etc.). No truly universal agent interface automatically loads skills across all platforms.

### Content Limitations

1. **Limited guidance on skill conflicts** — When multiple skills apply to the same task (e.g., both `context-engineering` and `source-driven-development` apply to API implementation), guidance on priority or sequencing is informal.

2. **No quantified thresholds for many checks** — Rules like "changes under 100 lines are safer" are stated but not justified with empirical data. The Rule of 500 in simplification is mentioned without citation.

3. **Documentation assumes modern web/SaaS development** — Deep guidance for systems programming, embedded development, or data science workflows is not covered.

4. **Session lifecycle hooks vary by platform** — The `session-start.sh` hook (Claude Code) and corresponding hooks for other platforms require integration at setup time. Automatic skill injection is platform-dependent.

5. **No off-line mode** — Skills require access to the GitHub repository or marketplace for discovery and updates. Offline skill execution is not documented.

### Process Limitations

1. **Skills assume sequential execution** — While the meta-skill allows parallel skill reference, the narrative assumes step-by-step progression. Concurrent streams (e.g., testing and documentation in parallel) are not formally addressed.

2. **Verification checklists are self-assessed** — No external oracle validates that verification steps have actually passed. Agents may claim verification without evidence.

3. **No escalation path for skill conflicts with user preferences** — If a user's style conflicts with a skill's guidance, the skill assumes the skill is correct. Documented pushback mechanisms exist but are asymmetric.

## Relevance to Claude Code Development

### Direct Relevance

1. **Skill Framework Pattern** — Agent Skills demonstrates a production-grade skill architecture pattern applicable to Claude Code's skill library. The anti-rationalization table, progressive disclosure, and verification-first design patterns are directly applicable.

2. **Quality Gate Model** — The five-phase gating workflow (Specify → Plan → Tasks → Implement with human review at each phase) provides a replicable model for Claude Code skill orchestration.

3. **Lifecycle-Aware Routing** — The `using-agent-skills` meta-skill's decision tree model (mapping incoming work to the right skill based on phase and requirements) is a reference for implementing smart skill discovery in Claude Code.

4. **Slash Command Entry Points** — The seven-command interface (`/spec`, `/plan`, `/build`, etc.) demonstrates a clean mental model for organizing skills by development phase — applicable to Claude Code's command architecture.

### Indirect Relevance

1. **Engineer Culture Embedding** — Agent Skills shows how to encode engineering practices (tests, reviews, specs, security) into non-optional skill steps. This pattern strengthens Claude Code's ability to enforce quality gates consistently.

2. **Specialist Personas** — Three agent personas (code-reviewer, test-engineer, security-auditor) provide a template for creating review-stage specialists in Claude Code that apply different review perspectives.

3. **Integration Breadth** — Supporting 8 platforms (Claude Code, Cursor, Antigravity, Gemini, Windsurf, Kiro, OpenCode, Copilot) with tool-specific plugins and installation guides demonstrates the market demand for portable, agent-agnostic engineering skills. Claude Code can leverage this as a distribution and compatibility model.

4. **Contributing Guidelines** — The CONTRIBUTING.md establishes clear quality bars (Specific, Verifiable, Battle-tested, Minimal) and skill format validation — directly applicable to Claude Code's skill governance.

## References

- **Official repository**: <https://github.com/addyosmani/agent-skills>
- **README.md** (accessed 2026-06-18): Overview, 24-skill list, installation guides for 8 platforms, supporting tools section
- **Skill anatomy documentation**: `docs/skill-anatomy.md` — Format specification for skills
- **Contributing guide**: `CONTRIBUTING.md` — Quality bars and skill validation
- **Plugin manifest**: `.claude-plugin/plugin.json` v1.0.0 — Claude Code plugin metadata
- **Antigravity plugin manifest**: `plugin.json` v1.0.0 — Antigravity CLI integration metadata
- **Project context**: `CLAUDE.md` — Development conventions and structure
- **Meta-skill**: `skills/using-agent-skills/SKILL.md` — Skill discovery and core operating behaviors
- **New Define skill**: `skills/interview-me/SKILL.md` — One-question interview process
- **New Ship skill**: `skills/observability-and-instrumentation/SKILL.md` — Logging, metrics, tracing, alerting
- **New agent persona**: `agents/web-performance-auditor.md` — Core Web Vitals auditing with `/webperf` command
- **GitHub repository metadata** (accessed 2026-06-18): 62,349 stars, 6,761 forks, created 2026-02-15, last updated 2026-06-18
- **Latest release**: v0.6.2 (published 2026-06-11)

## Freshness Tracking

| Section | Confidence | Evidence Source | Last Verified |
|---------|-----------|-----------------|---------------|
| Identity/Metadata | high | GitHub API + gh CLI (live query) | 2026-06-18 |
| Overview & Skills | high | README.md (line 152-213) + local skill directory listing | 2026-06-18 |
| Technical Architecture | high | README.md (§ How Skills Work) + plugin.json + skill anatomy | 2026-06-18 |
| Installation & Usage | high | README.md setup sections (8 platforms detailed) | 2026-06-18 |
| Key Features | high | README.md + new autonomous `/build auto` feature | 2026-06-18 |
| Integration Points | high | README.md § Quick Start (Antigravity CLI added) | 2026-06-18 |
| Agent Personas | high | README.md (§ Agent Personas, line 216-228) + local agents/ directory | 2026-06-18 |
| Limitations | medium | Absence of documented limitations + feature inspection | 2026-06-18 |
| Relevance to Claude Code | medium | Architectural pattern analysis + multi-platform integration breadth | 2026-06-18 |

**Next Review**: 2026-09-18 (3 months)

**Changes Since Last Review (2026-05-10 → 2026-06-18)**:
- **Skill count**: 22 → 24 (added `interview-me` in Define; `observability-and-instrumentation` in Ship)
- **Agent personas**: 3 → 4 (added `web-performance-auditor` with `/webperf` command)
- **GitHub metrics**: 37,441 → 62,349 stars (+66.4%); 4,182 → 6,761 forks (+61.7%)
- **Version**: Plugin manifest shows 1.0.0; latest release tag is v0.6.2 (released 2026-06-11)
- **Integrations**: Added Antigravity CLI as major platform (8 total now including Kiro and OpenCode)
- **New feature**: `/build auto` for autonomous task execution with approval gating
- **Update recency**: 2026-05-10 → 2026-06-18 (8 days ago)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Anthropics Skills](./anthropics-skills.md) | skill-generation-tools | official Anthropic skills with A/B eval harness and description-driven triggering (17 skills across 3 plugins) |
| [Claude Code Templates](./claude-code-templates.md) | skill-generation-tools | 100+ ready-to-use agents, commands, skills, MCPs, hooks for Claude Code via npx installer |
| [Compound Engineering Plugin](./compound-engineering-plugin.md) | skill-generation-tools | planning-first (80%) workflow plugin with 27 agents using same Plan/Work/Review/Compound lifecycle |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | comprehensive harness system: 65+ skills, 16 agents, 40+ commands, hook-based automation matching Agent Skills' skill ecosystem approach |
| [SkillKit](./skillkit.md) | skill-generation-tools | universal package manager for AI agent skills supporting 32+ agents with cross-format translation |
| [Superpowers](../agent-frameworks/superpowers.md) | agent-frameworks | agentic skills framework with 14 skills for TDD, debugging, subagent-driven development across Claude Code, Codex, OpenCode |
| [Vercel Labs Skills](./vercel-labs-skills.md) | skill-generation-tools | universal skill installer for 40+ AI coding agents with symlink-first design complementing Agent Skills' multi-platform strategy |
| [ClawHub](./clawhub.md) | skill-generation-tools | public skill registry for OpenClaw/Clawdbot agents with vector search and semver versioning as external discovery mechanism |
