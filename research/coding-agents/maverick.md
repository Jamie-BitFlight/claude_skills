# Maverick

> Claude Code plugin and CLI for autonomous AI-driven software development with enforced quality, security, and operational best practices.

**Repository**: <https://github.com/thermiteau/maverick>
**License**: Apache 2.0
**Current Version**: 0.5.5 (released 2026-03-19)
**Latest Commit**: e352bef (2026-03-19 14:47:56 +1100)
**Primary Language**: Python 3.10+
**Source**: README.md, docs/overview.md, docs/architecture.md, CHANGELOG.md

---

## Overview

Maverick is a dual-component system consisting of:

1. **Claude Code Plugin** — A collection of 28 markdown skills (best-practice standards and workflow automations) and 4 autonomous agents that load into Claude's context window
2. **Python CLI** — Local tooling for project initialization, skill generation, and remote worker infrastructure management
3. **Remote Workers Infrastructure** — AWS-based deployment system enabling scale autonomous development via GitHub webhooks and SQS queues

The core problem Maverick addresses: "LLMs generate code fast but don't come with any concept of quality, best practice or constraint" (README.md). Without guardrails, LLM-generated code lacks:

- Operational awareness (structured logging, alerting, monitoring)
- Security reasoning (vulnerable patterns go unnoticed)
- Testing discipline (bugs ship in untested code)
- Workflow discipline (untraced changes to main branch)
- Self-review (code that looks correct misses requirements)

Maverick enforces these practices through three mechanisms: **skills** (machine-readable guidance), **agents** (autonomous verifiers), and **hooks** (tool-call enforcement).

---

## Problem Addressed

### Failure Modes Without Guardrails

| Failure Mode | LLM Behavior | Maverick Solution |
|---|---|---|
| **Silent failures** | No structured logging added to code | Logging standard + project skill + linting verify format compliance |
| **Security vulnerabilities** | Reproduces vulnerable patterns from training data (SQL injection, XSS, secrets exposure) | Security review skill + code-reviewer agent catches them before merge |
| **Untested code** | Works on author's machine, breaks in production | Comprehensive testing standard + backend/frontend tester agents verify coverage |
| **Workflow chaos** | Commits to main, skips CI, produces untraceable changes | Git workflow skill + PR enforcement hook prevents direct main commits |
| **Missed requirements** | Code that looks correct violates project conventions | Code-reviewer agent validates spec compliance and convention adherence |
| **Unattended development scale** | Local Claude Code cannot parallelize work | Remote worker infrastructure triggers autonomous workers from GitHub issues via webhook→SQS→EC2 pipeline |

### Why Unattended Development Amplifies Risk

According to the architecture documentation: "These risks multiply enormously in unattended development when no human is watching the LLM work. There is no developer catching issues in real-time, no reviewer glancing at the diff, no operator noticing silent failures. Every quality gap becomes a production risk."

---

## Key Statistics

- **28 skills** organized across 7 categories (best practices, workflows, execution, Git/GitHub, CI/CD platforms, governance, project setup)
- **4 agents** (code-reviewer, backend-tester, frontend-tester, tech-docs-writer) run autonomously in isolated contexts
- **160 unit tests** covering models, names, config, registry, CLI, lambda handler, and session review modules (added in v0.5.1)
- **3 workflow entry points** for task execution: `do-issue-solo` (unattended), `do-issue-guided` (supervised checkpoints), `do-task-solo` (local task files)
- **1 day active development** (1 commit in shallow clone — rapid change rate stated in README as "under rapid change" until v1.0)
- **Platform support**: Python 3.10+, AWS EC2/SQS/Lambda infrastructure, GitHub Actions/GitLab CI/Azure DevOps via platform-specific skills

---

## Key Features

### 1. Best-Practice Skills (Knowledge Base)

Maverick ships 28 markdown skills organized by practice area. These define "what good looks like" — not project-specific implementations, but universal standards:

- **Logging Standards** (`mav-bp-logging`) — Structured logging requirements, log levels, format specification
- **Alerting Standards** (`mav-bp-alerting`) — Alert taxonomy, threshold definitions, notification routing
- **Testing Standards** (`mav-bp-unit-testing`, `mav-bp-integration-testing`) — Test organization, coverage targets, assertion patterns
- **Code Review Standards** (`code-review.md`) — Review checklist, common issues, security focus areas
- **Security Standards** (`security-review.md`) — OWASP vulnerability patterns, secrets handling, input validation
- **Linting Standards** (`mav-bp-linting`) — Code style enforcement, consistency requirements
- **CI/CD Standards** (`mav-bp-cicd`) — Pipeline stages, artifact handling, deployment gates
- **Git Workflow** (`git-workflow.md`) — Branching model, commit message format, PR conventions

Each skill is machine-readable markdown with YAML frontmatter, enabling the LLM to reference them while working.

**Mechanism**: LLM loads these skills into context window at session start and references them when writing code, designing architecture, or reviewing work.

---

### 2. Project Skills (Auto-Generated Stack-Specific Implementation)

While best-practice skills define universal standards, every project has unique technology choices (Pino vs Bunyan for logging, Vitest vs Jest for testing, etc.). The **upskill system** bridges this:

From docs/architecture.md:
```
1. Scan codebase for each topic defined in `skills/upskill/topics.json`
2. If an implementation exists (e.g., Pino logger configured), document exactly what's there
3. If no implementation exists but a best-practice skill is available, generate a recommended implementation tailored to the project's stack
4. Project skills are version-controlled and editable - the team can review and adjust recommendations
```

**Topics scanned** (default): logging, alerting, unit-testing, integration-testing, linting, CI/CD

**Output location**: `docs/maverick/skills/<topic>/SKILL.md` (or per-package for monorepos at `<package>/docs/maverick/skills/<topic>/SKILL.md`)

**How it works**:
- `/upskill` is invoked on project initialization or manually
- Analyzes codebase for existing implementations
- Generates project skills that are both standards-compliant AND project-specific
- Project teams can review and modify the generated skills

---

### 3. Autonomous Agents (Verification & Review)

Four agents run in isolated context windows to verify compliance without sharing the main development context:

| Agent | Purpose | When Dispatched |
|---|---|---|
| **Code Reviewer** | Two-stage review: (1) spec compliance, (2) code quality | After implementation or before PR creation |
| **Backend Tester** | Write and verify backend tests (Vitest, Fastify stack) | After business logic implementation |
| **Frontend Tester** | Write and verify frontend tests (Vitest, Playwright, React Testing Library) | After component implementation |
| **Tech Docs Writer** | Generate technical documentation with Mermaid diagrams | After significant architecture changes |

Each agent:
- Operates in a fresh, isolated context window (avoids "marking your own homework" problem)
- References both best-practice and project skills
- Reports findings back to the main workflow
- Can block PR creation if issues are found

From architecture docs: "Code review in a separate context window avoids the 'marking your own homework' problem. The reviewer agent has no memory of writing the code."

---

### 4. Multi-Mode Workflows

Maverick provides three entry points accommodating different trust/autonomy models:

#### **do-issue-solo** — Unattended Autonomous Development
- No human checkpoints until final PR review
- Claude works end-to-end from GitHub issue to submitted PR
- Phases: Solution Design → Create Tasks → Execute Tasks → Verify + Review → Create PR
- Use case: Fully autonomous feature development; human reviews finished work

#### **do-issue-guided** — Supervised Development with Checkpoints
- Human approval gates at four decision points:
  1. After solution design (before task creation)
  2. After task breakdown (before execution)
  3. After implementation + agent review (before PR)
  4. After PR creation (before merge)
- All automation between checkpoints
- Use case: Trust the LLM's approach but want human sign-off at architecture/execution boundaries

#### **do-task-solo** — Local Autonomous Development (Non-GitHub)
- No GitHub issue required
- User describes the task interactively in the CLI
- Claude formalizes it as a structured task document
- All artifacts stored locally under `.maverick/do-task/<TASK-ID>/`
- Same phases as do-issue-solo (Design → Tasks → Execute → Verify → PR)
- Use case: Local development workflow without GitHub issue overhead

**Common phases** across all three workflows:
1. **Solution Design** — Understand requirements and design an approach
2. **Create Tasks** — Decompose design into discrete, independently implementable tasks
   - Fewer than 5 tasks: posted as checklist comment
   - 5+ tasks: created as GitHub sub-issues with dependency ordering
3. **Execute Tasks** — Implement each task
4. **Verify + Review** — Run tests, apply agent review
5. **Create PR** — Submit changes for human review

---

### 5. Enforcement Chain (Defense in Depth)

The core innovation is layered enforcement. Each practice (logging, testing, security, etc.) is enforced at multiple checkpoints:

From docs/overview.md:
```
Enforcement Chain:
1. Best-practice skill — prevents anti-patterns (console.log vs structured logger)
2. Project skill — ensures project-specific implementation (Pino with CloudWatch)
3. Local verification — catches syntax, lint, test failures before push
4. CI pipeline — catches environment-specific, dependency, cross-platform issues
5. Agent review — catches spec violations, missing tests, security issues, convention drift
6. Human review — final gate for production-bound code
```

Example (logging):
- Best-practice skill defines: "all production logs must be structured JSON"
- Project skill specifies: "use Pino logger with CloudWatch transport"
- LLM writes code using Pino's structured format (guided by skills)
- Linting hook rejects console.log usage
- CI runs linting, blocks merge on violations
- Code-reviewer agent checks log format compliance
- Human reviewer approves final PR

---

### 6. Remote Worker Infrastructure (AWS)

For scaling autonomous development beyond local Claude Code, Maverick deploys workers to AWS:

**Architecture** (from claude-code-workers.md):
```
GitHub webhook → SQS message queue → EC2 worker → Claude Code
```

**Deployed resources**:
- 1 EC2 AMI (Ubuntu 24.04 LTS)
- 1 EC2 Instance with IAM policy and security group
- 1 SQS message queue with IAM policy
- 1 Lambda function to receive GitHub webhooks
- 1 Parameter Store entry for configuration

**Workflow**:
1. GitHub issue is created or labeled in the repo
2. GitHub webhook fires to Lambda function URL
3. Lambda writes message to SQS queue
4. EC2 worker polls queue, picks up task
5. Worker runs Claude Code autonomously via `/do-issue-solo` skill
6. Worker posts progress updates to GitHub issue comments
7. Output streams to CloudWatch Logs at `/maverick/worker`

**Commands** (from CLI):
```bash
maverick cloud init           # Initialize AWS infrastructure
maverick build-ami            # Bake Ubuntu 24.04 LTS AMI (~10-15 min)
maverick instance create      # Launch worker instance
maverick instance start|stop   # Manage instance lifecycle
maverick worker status        # Show systemd service status
maverick worker run-once      # Process one message (testing)
```

---

## Technical Architecture

### Component Relationships

**Plugin System**:
- Skills are markdown files with YAML frontmatter
- Agents are markdown files referencing skills
- All skills and agents are **templated with Jinja2** (v0.4.0+ change)
- Skills/agents reference each other via `{{ SKILLS.<CONSTANT> }}` and `{{ AGENTS.<CONSTANT> }}` built from `names.py`
- Plugin manifest at `.claude-plugin/plugin.json` (and `.cursor-plugin/plugin.json` for Cursor)

**CLI & Infrastructure**:
- Entry point: `maverick.cli:main` (from pyproject.toml)
- Module structure: `src/maverick/` with submodules for models, config, registry, lambda handler, session review
- Session review components: parser, analyzers, reporter, skills
- Cloud infrastructure: Boto3 for AWS API calls, Jinja2 for config templating

**Project Skill Generation**:
- Topic definitions: `skills/upskill/topics.json`
- Detection pattern matching: analyzes codebase for existing implementations
- Template-based generation: generates skill markdown files from Jinja2 templates
- Monorepo support: per-package skill generation at `<package>/docs/maverick/skills/<topic>/SKILL.md`

**Workflow Coordination**:
- GitHub Issue Planner agent → decomposes solution into task list
- Task Planner agent → creates implementation plan for local tasks
- Status tracked via GitHub issue comments (solo/guided) or `.maverick/do-task/<TASK-ID>/` (local)

---

## Installation & Usage

### Prerequisites

From README.md:
- Python 3.10+
- `uv` (Python package manager from Astral)
- Claude Code CLI
- Claude Code API Key

### Plugin Installation

```bash
claude plugin marketplace add https://github.com/thermiteau/maverick
claude plugin install maverick@thermite
```

After installation, skills become available as `/maverick:skill-name` within Claude Code.

### CLI Installation (System-wide)

```bash
# From repository
uv tool install .

# Or in development mode
uv tool install -e .
```

Makes the `maverick` command available globally.

### Initialize a Project

Within Claude Code:
```
/maverick:init
```

This:
1. Scans the codebase
2. Detects tech stack
3. Invokes `/upskill` to generate project skills
4. Stores skills in `.claude/skills/` or `docs/maverick/skills/`

### Run a Development Task

**Autonomous (no human involvement until PR review)**:
```
/maverick:do-issue-solo 42
```

**Supervised (human checkpoints)**:
```
/maverick:do-issue-guided 42
```

**Local task without GitHub**:
```
/maverick:do-task-solo
# User describes the task, Claude handles design → execution → PR
```

**Audit codebase against Maverick standards**:
```
/maverick:codebase-audit
```

### CLI Commands (Remote Infrastructure)

```bash
# Initialize AWS infrastructure
maverick cloud init

# Build an AMI
maverick build-ami

# Manage instances
maverick instance create
maverick instance start
maverick instance stop
maverick instance terminate

# On a worker instance
maverick worker status
maverick worker run-once
maverick worker uninstall
```

---

## Relevance to Claude Code Development

### Direct Application

1. **Enforced Code Quality in AI-Driven Development** — Maverick solves the core problem of unattended AI code generation: how to maintain quality without human oversight. The enforcement chain (skills → agents → hooks) is applicable to any Claude Code workflow where autonomous LLM development is desired.

2. **Skill Architecture Pattern** — The separation of best-practice skills (universal standards) from project skills (stack-specific implementations) is directly applicable to Claude Code skill design. The upskill system demonstrates automated skill generation and project customization.

3. **Agent-Based Review Architecture** — Maverick's agent design (isolated context windows, role-specific verification) prevents "marking your own homework" and is a reusable pattern for autonomous code review in Claude Code workflows.

4. **Workflow Decomposition** — The three-layer task decomposition (solution design → create tasks → execute) with checkpoint gating is a reference pattern for implementing supervised and autonomous workflows in Claude Code.

5. **Multi-Platform Support** — Maverick's platform-agnostic practice areas (logging, testing, CI/CD) with platform-specific implementations (GitHub Actions, GitLab CI, Azure DevOps skills) demonstrates how to scale Claude Code guidance across different tech stacks.

### For Plugin Developers

- Demonstrates Jinja2-templated skill generation for dynamic project customization
- Shows how to structure 28+ skills into composable categories
- Illustrates integration with GitHub webhooks and AWS infrastructure for remote Claude Code workers
- Reference implementation for autonomous agent design and context isolation

### For Teams Using Claude Code

- Provides a complete enforcement framework for safety-critical features
- Demonstrates how to combine best practices (skills) with project customization (upskill generation)
- Shows patterns for scaling from single-developer interactive workflows to team-based autonomous development
- Addresses operational concerns (logging, alerting, monitoring) that typical code generation tools ignore

---

## Limitations and Caveats

### Project Maturity

From README.md: "This project is still in Alpha and under rapid change" with these explicit caveats:

- **Claude plugin skills and agents**: "solid and work well"
- **CLI tools and Cloud infrastructure deploy**: "still brittle and need a lot of work. That's my next issue to fix/build."

This means cloud infrastructure features (remote workers, AMI building, instance management) should be considered experimental. Use case for local plugin development is mature.

### Architectural Constraints

1. **Skills are context-window dependent** — All 28 skills must load into Claude's context at session start. Very large projects with extensive custom skills may exceed context windows.

2. **Agent isolation vs cost** — Running separate agents (code-reviewer, backend-tester, frontend-tester) incurs multiple Claude Code API calls. Projects with tight cost constraints may need to batch or skip certain verification agents.

3. **GitHub webhook dependency for scaling** — Remote worker model requires GitHub issues as the task intake mechanism. Local-first teams must either adopt GitHub issues or use `do-task-solo` workflow.

4. **Upskill generation is pattern-matching based** — The skill generation system scans for existing implementations. If a project uses non-standard patterns (e.g., custom logging wrapper), upskill may not detect it and will generate "recommended" skills instead of documenting reality.

5. **AWS-only for remote infrastructure** — Cloud infrastructure provisioning is hardcoded for AWS. Organizations using GCP, Azure, or other cloud providers must either adapt the Terraform/CloudFormation, or stick to local Claude Code usage.

### Operational Gaps

1. **Mono-repo support is recent** (v0.4.0) — Mono-repo test coverage and edge cases may exist. Workspace detection uses standard `[tool.uv.workspace]` format; alternative mono-repo tools (Yarn workspaces, Lerna) are not mentioned.

2. **Limited platform testing** — Tests added in v0.5.1 (160 unit tests) but integration/E2E test coverage is not documented. Cloud infrastructure (AMI building, Lambda handler, SQS polling) is marked "brittle."

3. **Hook enforcement coverage unclear** — Documentation mentions "hooks" enforce rules at tool-call boundaries but does not enumerate which hooks exist or which LLM behaviors they block.

4. **Session recovery** (`claude-code-error-handling-and-recovery.md`) exists but is not detailed in reviewed sources. How recovery state is tracked and what happens if workers crash mid-task is not documented.

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---|---|
| Identity/Metadata | high | 2026-03-23 | Version 0.5.5 confirmed in pyproject.toml; commit date verified from git log |
| Problem Addressed | high | 2026-03-23 | Extracted from docs/overview.md and README.md; failure modes align with stated design goals |
| Key Features | high | 2026-03-23 | Skills, agents, workflows all extracted from docs/architecture.md; specific skill names verified from skills/ directory listing |
| Technical Architecture | medium | 2026-03-23 | Component relationships extracted from architecture docs; cloud infrastructure details from claude-code-workers.md; CLI structure from pyproject.toml. Hook enforcement mechanism not deeply documented in reviewed sources. |
| Installation & Usage | high | 2026-03-23 | Installation commands and workflow usage extracted from README.md and documentation; CLI commands verified from claude-code-workers.md |
| Relevance to Claude Code | medium | 2026-03-23 | Determined from direct examination of skill/agent design and workflow patterns. No explicit documentation of relevance claims; assessment based on architectural fit. |
| Limitations | medium | 2026-03-23 | Maturity warnings from README.md and architecture docs are explicit; infrastructure brittleness noted in README. AWS-only constraint confirmed from cloud-init docs. Upskill edge cases inferred from documented pattern-matching approach. Mono-repo support recent (v0.4.0); extent of testing not documented. |

### Next Review

2026-06-23 (3 months) — By this date, v0.5.5 may be superseded. Recommend re-checking:
- Current version (may be v0.6+ or v1.0 by June)
- Cloud infrastructure stability improvements (stated as priority in README)
- Hook enforcement documentation completeness
- Remote worker production deployment reports (if any)

---

## References

1. **README.md** — Project overview, problem statement, installation instructions, usage examples. Accessed 2026-03-23 via shallow clone e352bef.

2. **docs/overview.md** — Problem analysis, solution architecture (skills/agents/hooks), enforcement chain, project structure, design decisions. Accessed 2026-03-23. Last verified in file: 2026-03-02.

3. **docs/architecture.md** — Detailed skill taxonomy, upskill system, agent descriptions, workflow entry points. Accessed 2026-03-23. Last verified in file: 2026-03-02.

4. **docs/claude-code-workers.md** — Remote worker infrastructure, AWS resource deployment, instance management, GitHub webhook integration. Accessed 2026-03-23. Last verified in file: 2026-03-02.

5. **CHANGELOG.md** — Version history, feature timeline (v0.1.0-alpha through v0.5.5). Accessed 2026-03-23. Version 0.5.5 released 2026-03-19.

6. **pyproject.toml** — Project metadata, dependencies (boto3, jinja2, pyright, ruff), Python version requirement (3.10+), CLI entry point. Accessed 2026-03-23.

7. **License** — Apache License 2.0 confirmed in LICENSE file. Accessed 2026-03-23.

8. **Repository Metadata**:
   - Latest commit: e352bef (2026-03-19 14:47:56 +1100)
   - Shallow clone depth: 1 commit
   - GitHub URL: <https://github.com/thermiteau/maverick>
   - Accessed 2026-03-23

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Pilot](./pilot.md) | coding-agents | Parallel quality-enforcement approach with 15 lifecycle hooks, TDD enforcement, and spec-driven development (`/spec` workflow) |
| [Cline](./cline.md) | coding-agents | Alternative autonomous coding agent with human-in-the-loop approval; shares skill-based extensibility and MCP server support |
| [OpenAI Codex CLI](./openai-codex-cli.md) | coding-agents | Competing autonomous agent platform with OS sandbox; shares multi-provider support and workspace isolation patterns |
| [OpenAI Symphony](./openai-symphony.md) | coding-agents | Elixir-based autonomous agent with 8-component architecture; similar workflow decomposition and issue-tracker-driven development |
| [Tembo](./tembo.md) | coding-agents | Cloud-based AI coding agent orchestration supporting multiple providers; overlaps on multi-repo workflows and GitHub integration |
| [Everything Claude Code](../skill-generation-tools/everything-claude-code.md) | skill-generation-tools | Comprehensive skill framework with 16 specialized agents and 65+ skills; shares skill architecture patterns and multi-agent orchestration approach |
| [Superpowers](../agent-frameworks/superpowers.md) | agent-frameworks | Agentic skills framework with 14 composable skills for TDD and subagent-driven development; shares enforced workflow discipline and skill-based extensibility |
| [Get Shit Done](../agent-frameworks/get-shit-done.md) | agent-frameworks | Spec-driven development system with 11 agents and multi-agent orchestration; overlaps on context engineering and atomic task decomposition |
| [Softaworks Agent Toolkit](../skill-generation-tools/softaworks-agent-toolkit.md) | skill-generation-tools | 43-skill catalog with agent extensibility patterns; demonstrates portable Agent Skills format applicable to Maverick's skill architecture |
| [Anthropic's Skills](../skill-generation-tools/anthropics-skills.md) | skill-generation-tools | Official Anthropic skill repository with multi-plugin structure; provides reference implementation for skill organization and marketplace distribution |
| [Claude Code Skills (AlirezaRezvanI)](../skill-generation-tools/claude-code-skills-alirezarezvani.md) | skill-generation-tools | 170+ production-ready modular skills across 9 domains; demonstrates large-scale skill library pattern and cross-CLI portability |
| [Claude Code Templates](../skill-generation-tools/claude-code-templates.md) | skill-generation-tools | 100+ ready-to-use agents, skills, and MCPs with browser installer; shares skill templating and community marketplace patterns |
| [SkillsMP](../skill-generation-tools/skillsmp.md) | skill-generation-tools | Open marketplace for 66,500+ AI agent skills with SKILL.md standard; represents decentralized skill distribution alternative to Maverick's integrated approach |
| [Claude Pilot](../developer-tools/claude-pilot.md) | developer-tools | Quality enforcement layer with hooks pipeline, /spec workflow, persistent memory, and smart model routing; direct parallel to Maverick's multi-mode workflow architecture |
| [Claude CodePro](./claude-codepro.md) | coding-agents | referenced by Claude CodePro (coding-agents) |

---

**Entry Created**: 2026-03-23
**Entry Status**: Complete
**Confidence Level**: High overall; medium for architectural details and limitations (AWS-specific, hook enforcement not fully documented)
