---
title: Agent Skills
subtitle: Production-grade engineering skills for AI coding agents following Google engineering practices
category: skill-generation-tools
resource_url: https://github.com/addyosmani/agent-skills
github_url: https://github.com/addyosmani/agent-skills
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# Agent Skills

**Production-grade engineering skills for AI coding agents** — a structured skills library that guides AI agents through software development workflows following senior engineer practices from Google's software engineering culture.

## Resource Identity

- **Name**: Agent Skills
- **Creator**: Addy Osmani
- **Repository**: <https://github.com/addyosmani/agent-skills>
- **Version**: 1.0.0 (as of 2026-05-10)
- **License**: MIT
- **GitHub Stars**: 37,441 (as of 2026-05-10)
- **Forks**: 4,182 (as of 2026-05-10)

## Problem Addressed

AI coding agents default to the shortest path when building software — often skipping specs, tests, security reviews, and the engineering discipline that produces reliable production code. Agent Skills solves this by encoding the workflows, quality gates, and best practices that senior engineers use, making them consistently executable by AI agents across every phase of development.

The repository explicitly states: "Skills encode the workflows, quality gates, and best practices that senior engineers use when building software. These ones are packaged so AI agents follow them consistently across every phase of development."

## Overview

Agent Skills is a collection of 22 skills organized by development phase (Define, Plan, Build, Verify, Review, Ship) plus a meta-skill for discovery. Each skill encodes a specific engineering process as a step-by-step workflow that agents follow, not abstract advice they might skip.

### Core Skills by Lifecycle Phase

**Meta/Discovery (1 skill):**
- `using-agent-skills` — Maps incoming work to the right skill and establishes core operating behaviors

**Define (2 skills):**
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

**Ship (5 skills):**
- `git-workflow-and-versioning` — Trunk-based development, atomic commits (~100 lines), commit-as-save-point pattern
- `ci-cd-and-automation` — Shift Left principle, Faster is Safer, feature flags, quality gate pipelines, failure feedback loops
- `deprecation-and-migration` — Code-as-liability mindset, compulsory vs advisory deprecation, migration patterns, zombie code removal
- `documentation-and-adrs` — Architecture Decision Records, API docs, inline documentation standards (document the *why*)
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

**Specialist Personas**: Three agent personas provide targeted review perspectives:
- `code-reviewer.md` — Senior Staff Engineer (five-axis code review)
- `test-engineer.md` — QA Specialist (test strategy and coverage analysis)
- `security-auditor.md` — Security Engineer (vulnerability detection and threat modeling)

**Supporting References** (4 shared checklists):
- `testing-patterns.md` — Test structure, naming, mocking, React/API/E2E examples, anti-patterns
- `security-checklist.md` — Pre-commit checks, auth, input validation, headers, CORS, OWASP Top 10
- `performance-checklist.md` — Core Web Vitals targets, frontend/backend checklists, measurement commands
- `accessibility-checklist.md` — Keyboard navigation, screen readers, visual design, ARIA, testing tools

**Integration Points**:
- Claude Code: Native plugin via `.claude/commands/` for slash commands and `.claude/skills/` for skill discovery
- Cursor: Copy SKILL.md files into `.cursor/rules/` or reference the full `skills/` directory
- Gemini CLI: Native skill installation via `gemini skills install`
- Windsurf, Kiro IDE, OpenCode: Integration via AGENTS.md and skill content inclusion
- GitHub Copilot: Agent definitions as personas, skill content in `.github/copilot-instructions.md`
- Any agent system: Plain Markdown skills work with any system accepting system prompts or instruction files

**Session Lifecycle**: The `session-start.sh` hook injects the `using-agent-skills` meta-skill into every new Claude Code session via JSON payload (with fallback when `jq` is unavailable).

## Key Features

### 1. Anti-Rationalization Tables
Every skill includes a "Common Rationalizations" section — excuses agents use to skip important steps, paired with factual rebuttals. Examples:
- "I'll add tests later" → countered with evidence that up-front testing prevents rework
- "This is simple enough to skip the spec" → countered with cost of rework from missed requirements

### 2. Verification-First Design
No skill is complete until verification passes. Every skill ends with a checklist of evidence requirements (test output, build results, runtime data). "Seems right" is never sufficient.

### 3. Bounded Workflow Steps
Processes are concrete and measurable, not vague. Instead of "make sure the code is tested," a skill specifies "run `npm test` and verify all tests pass with coverage ≥80%."

### 4. Lifecycle-Aware Skill Discovery
The `using-agent-skills` meta-skill provides a decision tree that maps incoming work to the right skill based on development phase, requirements clarity, and task scope.

### 5. Operating Behaviors Across All Skills
Six core behaviors apply universally (Surface Assumptions, Manage Confusion Actively, Push Back When Warranted, Enforce Simplicity, Maintain Scope Discipline, Verify Don't Assume).

### 6. Google Engineering Culture Foundation
Skills explicitly incorporate patterns from:
- Hyrum's Law (API design skill)
- Beyonce Rule and test pyramid (TDD skill)
- Change sizing and review speed norms (code review skill)
- Chesterton's Fence (simplification skill)
- Trunk-based development (git workflow skill)
- Shift Left and feature flags (CI/CD skill)
- Code-as-liability mindset (deprecation skill)

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

### Other Tools

- **Cursor**: Copy SKILL.md files to `.cursor/rules/` or reference `skills/` directory
- **Gemini CLI**: `gemini skills install https://github.com/addyosmani/agent-skills.git --path skills`
- **Windsurf, Kiro, OpenCode**: See setup guides in `docs/`
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

1. **Single-author codebase** — Only Addy Osmani appears in git commit history; community contributions are not yet integrated into commits. Contributing workflow details are documented but implementation is early.

2. **Documentation project only** — Agent Skills is a pure documentation collection with no code execution engine, testing harness, or validation tooling. Integration with agent systems is manual or via plugin system.

3. **Skills assume English-first workflows** — All skills are written in English and assume command-line tools and development practices common to English-speaking software engineering communities. Cross-cultural workflows or non-English tooling are not addressed.

4. **No formalized metrics for skill effectiveness** — The repository does not publish data on skill adoption, success rates, or measurable improvements to code quality or development velocity. Effectiveness is asserted in the README but not quantified.

5. **Agent integration is framework-specific** — Each integration point (Claude Code, Cursor, Gemini CLI, etc.) requires separate setup. No universal agent interface exists that automatically discovers and loads these skills.

### Content Limitations

1. **Limited guidance on skill conflicts** — When multiple skills apply to the same task (e.g., both `context-engineering` and `source-driven-development` apply to API implementation), guidance on priority or sequencing is informal.

2. **No quantified thresholds for many checks** — Rules like "changes under 100 lines are safer" are stated but not justified with empirical data. The Rule of 500 in simplification is mentioned without citation.

3. **Documentation assumes modern web/SaaS development** — Deep guidance for systems programming, embedded development, or data science workflows is not covered.

4. **Session lifecycle hooks are Claude Code-specific** — The `session-start.sh` hook injects skills only into Claude Code sessions. Other tools must manually load skills on startup.

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

3. **Integration Breadth** — Supporting multiple editors (Claude Code, Cursor, Gemini, Windsurf, Kiro, Copilot) demonstrates the market demand for portable, agent-agnostic engineering skills. Claude Code can leverage this as a distribution model.

4. **Contributing Guidelines** — The CONTRIBUTING.md establishes clear quality bars (Specific, Verifiable, Battle-tested, Minimal) and skill format validation — directly applicable to Claude Code's skill governance.

## References

- **Official repository**: <https://github.com/addyosmani/agent-skills>
- **README.md** (accessed 2026-05-10): Overview, skills list, installation, contributing guidelines
- **Skill anatomy documentation**: `docs/skill-anatomy.md` — Format specification for skills
- **Contributing guide**: `CONTRIBUTING.md` — Quality bars and skill validation
- **Plugin manifest**: `.claude-plugin/plugin.json` v1.0.0 — Integration metadata
- **Project context**: `CLAUDE.md` — Development conventions and structure
- **Meta-skill**: `skills/using-agent-skills/SKILL.md` — Skill discovery and core operating behaviors
- **Example skill**: `skills/spec-driven-development/SKILL.md` — Spec writing process
- **Git repository metadata** (accessed 2026-05-10): 37,441 stars, 4,182 forks, created 2026-02-15, last updated 2026-05-10

## Freshness Tracking

| Section | Confidence | Evidence Source | Last Verified |
|---------|-----------|-----------------|---------------|
| Identity/Metadata | high | plugin.json + GitHub API | 2026-05-10 |
| Overview & Features | high | README.md + skill list inspection | 2026-05-10 |
| Technical Architecture | high | SKILL.md anatomy + skill examples + .claude-plugin manifest | 2026-05-10 |
| Installation & Usage | high | README.md setup sections | 2026-05-10 |
| Key Features | high | Skills inspection + CONTRIBUTING.md | 2026-05-10 |
| Limitations | medium | Absence of content + feature/tool list inspection | 2026-05-10 |
| Relevance to Claude Code | medium | Architectural pattern analysis against Claude Code skill model | 2026-05-10 |

**Next Review**: 2026-08-10 (3 months)

**Notes**:
- Single-author git history confirmed; community contribution process is documented but not yet visible in commits
- All 22 skills follow consistent SKILL.md anatomy; verified sampling of 3 skills (using-agent-skills, spec-driven-development, examples)
- Integration breadth verified: Claude Code, Cursor, Gemini CLI, Windsurf, Kiro, OpenCode, GitHub Copilot documented in README
- Limitations are inferred from absent content rather than documented limitations; confidence reflects this distinction
