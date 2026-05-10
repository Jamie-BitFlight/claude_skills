---
title: brooks-lint
subtitle: AI code reviews grounded in twelve classic software engineering books
category: coding-agents
resource_url: https://github.com/hyhmrright/brooks-lint
github_url: https://github.com/hyhmrright/brooks-lint
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# brooks-lint — AI Code Reviews Grounded in Twelve Classic Engineering Books

## Identity & Key Metadata

**Name**: brooks-lint
**Version**: 1.2.2 (released 2026-04-29)
**Author**: hyhmrright
**Repository**: <https://github.com/hyhmrright/brooks-lint>
**License**: MIT (Copyright 2025)
**Language**: JavaScript/Node.js (skills in Markdown + JavaScript validation/CI scripts)
**Project Type**: Claude Code Plugin + Codex CLI Skill + Gemini CLI Extension

Source: README.md lines 20–24, package.json, plugin.json (accessed 2026-05-10).

---

## Problem Addressed

Most code quality tools count lines, cyclomatic complexity, and style violations. They cannot answer the fundamental questions that differentiate maintainable systems from fragile ones:

- **How many unrelated modules break when I change one thing?** (Change Propagation)
- **Does this code faithfully represent the business domain?** (Domain Model Distortion)
- **Are different people re-implementing the same decision in separate places?** (Knowledge Duplication)
- **Have we accidentally added more complexity than the problem required?** (Accidental Complexity)
- **Do dependencies flow in a consistent direction?** (Dependency Disorder)
- **Can a new maintainer understand this without reading implementation details?** (Cognitive Overload)

brooks-lint diagnoses code across these six decay risk dimensions, grounded in patterns from twelve classic software engineering books. Every finding traces back to a named principle (e.g., "Fowler — Refactoring — Shotgun Surgery") and includes a four-part diagnosis: **Symptom → Source → Consequence → Remedy**.

Source: README.md lines 33–34, 56–69, AGENTS.md lines 5–6, common.md lines 6–14 (accessed 2026-05-10).

---

## Key Statistics

- **12 foundational books** synthesized into 6 production decay risks (R1–R6) + 6 test decay risks (T1–T6)
- **6 analysis modes**: PR Review, Architecture Audit, Tech Debt Assessment, Test Quality Review, Health Dashboard, Full Sweep Auto-Fix
- **2,406 total skill guide lines** across all modes and shared framework
- **49 benchmark scenarios** covering all decay risks plus false-positive and tradeoff edge cases
- **Benchmark accuracy**: 94% pass rate vs. 16% for Claude alone (plain LLM without skill structure)
- **Latest release**: 1.2.2 (2026-04-29) — token reduction pass on all skill guides (~212 lines removed, no behavioral change)
- **Last commit**: 2026-05-01 (git log confirms recent activity)

Source: README.md lines 20, 153–166, CHANGELOG.md lines 1–26, package.json, AGENTS.md line 31, validate-repo.mjs reference in CLAUDE.md (accessed 2026-05-10).

---

## Technical Architecture

### Core Components

**1. Shared Framework** (`skills/_shared/`)
- `common.md` — Iron Law (Symptom → Source → Consequence → Remedy), report template, project config parsing, Health Score algorithm
- `decay-risks.md` — Detailed diagnostic criteria for 6 production decay risks (R1–R6) with symptoms, sources, severity guides, and "What Not to Flag" guards
- `test-decay-risks.md` — Diagnostic criteria for 6 test decay risks (T1–T6)
- `source-coverage.md` — 12-book coverage matrix, review discipline rules, justified tradeoffs, cited exceptions
- `remedy-guide.md` — Actionable remedies for `--fix` mode (auto-fix logic rules)
- `custom-risks-guide.md` — Template for project-specific risk codes (Cx format)

Source: README.md lines 388–396, CLAUDE.md lines 18–19, 27–32 (accessed 2026-05-10).

**2. Six Independent Skills** — each a self-contained analysis mode
- `brooks-review/` — PR-level code review, scans diff for decay risks
- `brooks-audit/` — Full architecture audit with Mermaid dependency graphs, module interdependencies
- `brooks-debt/` — Tech debt assessment, classifies findings by Pain × Spread priority
- `brooks-test/` — Test suite quality review across T1–T6 test decay risks
- `brooks-health/` — Composite health dashboard aggregating all four dimensions
- `brooks-sweep/` — Unified full-sweep scan + autonomous auto-fix pipeline (9-phase: consent → scope → review → test → debt → audit → iterate → residual → report)

Each skill contains:
- `SKILL.md` — High-level process skeleton (3–6 items) citing guide step ranges; trigger description with "Do NOT trigger for:" boundary clause
- Guide file (e.g., `pr-review-guide.md`) — Detailed numbered steps (sub-steps like `2a`, `6b` allowed) with concrete procedures

Source: README.md lines 239–249, 274, AGENTS.md lines 25–32, CLAUDE.md lines 8–9, 19–20 (accessed 2026-05-10).

**3. Plugin Infrastructure**
- `.claude-plugin/plugin.json` — Claude Code Plugin manifest (name, version, description, commands, hooks)
- `commands/` — Short-form command wrappers (`/brooks-review`, `/brooks-audit`, etc.), auto-installed by session-start hook
- `hooks/session-start` — Injects skill list on session start for Claude Code users
- `.codex-plugin/` — Codex CLI plugin manifest
- GitHub Action (`.github/actions/brooks-lint/`) — CI/CD integration with cache, Health Score trend tracking

Source: README.md lines 187–199, 414–415, CLAUDE.md lines 29–31, 23–24 (accessed 2026-05-10).

**4. Evaluation & Validation** (`evals/`, `scripts/`)
- `evals.json` — 49 benchmark scenarios (R1–R6 production risks, T1–T6 test risks, false-positive guards, tradeoff cases)
- `validate-repo.mjs` — Repo consistency checks (manifest sync, README badge, CHANGELOG, source inventory, skill structure)
- `run-evals.mjs`, `run-evals-live.mjs` — Structural validation and live AI testing
- `history.mjs` — Health Score trend tracking (`.brooks-lint-history.json`)

Source: CLAUDE.md lines 36–41, package.json lines 5–10 (accessed 2026-05-10).

### Data Flow

```
User Query / Diff
    ↓
Skill Triggered (SKILL.md loaded)
    ↓
Auto-Scope Detection (PR diff / git diff / entire project)
    ↓
Project Config Read (.brooks-lint.yaml if present)
    ↓
Read Shared Framework
  - common.md (Iron Law, Config, Report Template)
  - decay-risks.md or test-decay-risks.md (diagnostic criteria)
  - source-coverage.md (book coverage, tradeoff discipline)
    ↓
Mode-Specific Guide Execution (Steps 1–N)
    ↓
Symptom Detection & Source Mapping
    ↓
Consequence Analysis
    ↓
Remedy Generation (if --fix mode)
    ↓
Health Score Calculation (base 100; deductions per finding)
    ↓
Report Output (Symptom → Source → Consequence → Remedy format)
```

Source: AGENTS.md lines 8–35, common.md lines 6–90 (accessed 2026-05-10).

### Health Score Algorithm

Base score: **100 points**

Deductions per finding:
- 🔴 **Critical** (severity level): −15 points
- 🟡 **Warning** (severity level): −5 points
- 🟢 **Suggestion** (severity level): −1 point

Floor: **0 points** (cannot go below zero)

Severity tiers are determined by the decay-risk diagnostic guide for each finding type. Project config (`.brooks-lint.yaml`) allows per-risk severity overrides.

Source: common.md lines 14–15, AGENTS.md lines 15–16 (accessed 2026-05-10).

---

## Key Features

### 1. **The Six Production Decay Risks (R1–R6)**

| Risk | Diagnostic Question | Example Symptom |
|------|---------------------|-----------------|
| R1: Cognitive Overload | How much mental effort to understand this? | Function > 50 lines with 3+ nesting levels and unclear names |
| R2: Change Propagation | How many unrelated things break on one change? | One method performs 4 unrelated business responsibilities |
| R3: Knowledge Duplication | Is the same decision expressed in multiple places? | Loyalty formula recalculated in 3 different files |
| R4: Accidental Complexity | Is code more complex than the problem? | Custom retry logic duplicating what stdlib provides |
| R5: Dependency Disorder | Do dependencies flow in a consistent direction? | Circular dependencies between UserService ↔ OrderService |
| R6: Domain Model Distortion | Does code faithfully represent the domain? | Email notification dead code; overwrites before comparison |

Source: README.md lines 56–69, decay-risks.md lines 1–10 and subsequent risk definitions (accessed 2026-05-10).

### 2. **The Six Test Decay Risks (T1–T6)**

- **T1: Test Obscurity** — test code is harder to understand than the code it tests
- **T2: Test Brittleness** — tests fail on implementation refactors that should not affect behavior
- **T3: Test Duplication** — same test logic repeated with slight variations
- **T4: Mock Abuse** — mocks used in place of real dependencies, obscuring domain contracts
- **T5: Coverage Illusion** — high coverage numbers without adequate behavior verification
- **T6: Architecture Mismatch** — test structure does not mirror production architecture

Source: README.md line 316, test-decay-risks.md reference in AGENTS.md line 26 (accessed 2026-05-10).

### 3. **Structured Diagnosis Chain (Iron Law)**

Every finding follows: **Symptom → Source → Consequence → Remedy**

- **Symptom**: What pattern was observed in the code
- **Source**: Which book / principle identifies this pattern
- **Consequence**: Why this matters (business impact, maintenance risk, regression surface)
- **Remedy**: Concrete actionable fix

Example from README.md:
> "**Symptom:** `update_profile` performs profile field updates, email notifications, loyalty points, and cache invalidation all in one method.
> **Source:** Fowler — Refactoring — Divergent Change; Hunt & Thomas — The Pragmatic Programmer — Orthogonality.
> **Consequence:** Any change to loyalty logic risks breaking email notifications. Every edit carries cross-domain regression risk.
> **Remedy:** Extract `NotificationService`, `LoyaltyService`, `UserCacheInvalidator`. `UserService.update_profile` orchestrates by calling each."

Source: README.md lines 95–99, common.md lines 6–14 (accessed 2026-05-10).

### 4. **Twelve Foundational Books**

**Production Code Framework (8 books)**:
- Frederick P. Brooks Jr. — *The Mythical Man-Month* (1975, Anniversary Ed. 1995)
- Steve McConnell — *Code Complete* (1993, 2nd ed. 2004)
- Martin Fowler — *Refactoring* (1999, 2nd ed. 2018)
- Robert C. Martin — *Clean Architecture* (2017)
- Andrew Hunt & David Thomas — *The Pragmatic Programmer* (1999, 20th Anniversary Ed. 2019)
- Eric Evans — *Domain-Driven Design* (2003)
- John Ousterhout — *A Philosophy of Software Design* (2018)
- Titus Winters, Tom Manshreck, Hyrum Wright — *Software Engineering at Google* (2020)

**Test Quality Framework (4 books)**:
- Gerard Meszaros — *xUnit Test Patterns* (2007)
- Roy Osherove — *The Art of Unit Testing* (2009, 3rd ed. 2023)
- Google Engineering — *How Google Tests Software* (2012)
- Michael Feathers — *Working Effectively with Legacy Code* (2004)

Source: README.md lines 485–500, source-coverage.md lines 2–14 (accessed 2026-05-10).

### 5. **Architecture Audit with Mermaid Dependency Graph**

Mode 2 (Architecture Audit) generates a native Mermaid flowchart showing module dependencies with color-coded severity:
- 🔴 Red = Critical findings
- 🟡 Yellow = Warning findings
- 🟢 Green = Clean modules

The graph renders directly in GitHub, Notion, and Markdown without extra tools.

Source: README.md lines 109–145, architecture-guide.md reference in README.md line 399 (accessed 2026-05-10).

### 6. **Project Configuration (`.brooks-lint.yaml`)**

Customize review behavior per project:

```yaml
version: 1

# Disable specific decay risks
disable:
  - T5   # skip coverage metrics check

# Override severity per risk
severity:
  R1: suggestion   # downgrade Cognitive Overload for this domain

# Exclude files from analysis
ignore:
  - "**/*.generated.*"
  - "**/vendor/**"

# Evaluate only these risks (cannot combine with disable)
focus:
  - R1
  - R3
```

Source: README.md lines 340–364, common.md lines 21–70 (accessed 2026-05-10).

### 7. **Auto-Scope Detection**

Each mode auto-detects the scope when no files are explicitly provided:

- **PR Review**: `git diff --cached` → `git diff` → `git diff main...HEAD` → ask user
- **Architecture Audit / Tech Debt**: Entire project by default; `--since=<ref>` analyzes only modules touching changed files
- **Test Quality**: All test files; prioritizes co-located tests (`src/foo.ts` → `src/foo.test.ts`)
- **Health Dashboard**: Entire project; if user provides a path, scopes all sub-scans to it

Reports always state detected scope explicitly.

Source: common.md lines 81–94 (accessed 2026-05-10).

### 8. **Six Analysis Modes**

| Mode | Command | Action |
|------|---------|--------|
| **1. PR Review** | `/brooks-review` | Diagnoses each decay risk per diff; Symptom → Source → Consequence → Remedy |
| **2. Architecture Audit** | `/brooks-audit` | Maps module dependencies, identifies circular deps, checks Conway's Law alignment; includes Mermaid graph |
| **3. Tech Debt Assessment** | `/brooks-debt` | Classifies findings by Pain × Spread priority; produces repayment roadmap (Critical / Scheduled / Monitored) |
| **4. Test Quality Review** | `/brooks-test` | Audits test suite against T1–T6 test decay risks; PR reviews include lightweight Step 7 Quick Test Check automatically |
| **5. Health Dashboard** | `/brooks-health` | Abbreviated scans across all four dimensions; produces weighted composite Health Score (0–100) |
| **6. Full Sweep** | `/brooks-sweep` | Unified scan across R1–R6 + T1–T6 + architecture; applies fixes autonomously (Safe fixes auto-apply, Extended-Safe fixes with test coverage apply without prompt, complex changes flagged as manual items) |

Source: README.md lines 239–249, 276–336 (accessed 2026-05-10).

### 9. **CI/CD Integration**

GitHub Action automates reviews on every PR:

```yaml
# .github/workflows/brooks-lint.yml
name: Brooks-Lint PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  brooks-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: hyhmrright/brooks-lint/.github/actions/brooks-lint@main
        with:
          mode: review
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          fail-below: 70
```

Features:
- Posts review as PR comment
- Health Score trend tracking (if `.brooks-lint-history.json` is committed)
- Optional fail-on-threshold check
- Cost: ~$0.05–0.15 per PR run

Source: README.md lines 426–453 (accessed 2026-05-10).

---

## Installation & Usage

### Claude Code (Recommended)

**Via Plugin Marketplace**:
```bash
/plugin marketplace add hyhmrright/brooks-lint
/plugin install brooks-lint@brooks-lint-marketplace
```

Short-form commands are auto-installed on first session start.

**Manual Install**:
```bash
mkdir -p ~/.claude/skills/brooks-lint
cp -r skills/* ~/.claude/skills/brooks-lint/
```

### Gemini CLI

**Via Extension**:
```bash
/extensions install https://github.com/hyhmrright/brooks-lint
```

**Manual Install**:
```bash
mkdir -p ~/.gemini/skills/brooks-lint
cp -r skills/* ~/.gemini/skills/brooks-lint/
```

### Codex CLI

**Via Skill Installer** (in Codex session):
```
Install the brooks-lint skill from hyhmrright/brooks-lint
```

**Manual Install**:
```bash
git clone https://github.com/hyhmrright/brooks-lint.git /tmp/brooks-lint
mkdir -p ~/.codex/skills/brooks-lint
cp -r /tmp/brooks-lint/skills/* ~/.codex/skills/brooks-lint/
```

### Basic Usage Examples

```bash
# PR Review (paste diff or point at changed files)
/brooks-review

# Full architecture audit
/brooks-audit

# Tech debt assessment
/brooks-debt

# Test suite health check
/brooks-test

# Composite health dashboard
/brooks-health

# Full sweep with auto-fix
/brooks-sweep
```

Source: README.md lines 185–237 (accessed 2026-05-10).

---

## Benchmark Results

Tested across 3 real-world scenarios (PR review, architecture audit, tech debt assessment):

| Criterion | brooks-lint | Claude alone |
|-----------|:-----------:|:------------:|
| Structured findings (Symptom → Source → Consequence → Remedy) | ✅ 100% | ❌ 0% |
| Book citations per finding | ✅ 100% | ❌ 0% |
| Severity labels (🔴/🟡/🟢) | ✅ 100% | ❌ 0% |
| Health Score (0–100) | ✅ 100% | ❌ 0% |
| Detects Change Propagation | ✅ 100% | ✅ 100% |
| **Overall pass rate** | **94%** | **16%** |

The gap is not what Claude *can* find — it is what it *consistently* finds with traceable evidence and actionable remedies every time.

Source: README.md lines 154–166 (accessed 2026-05-10).

---

## Limitations & Caveats

### Documented Limitations

1. **Requires explicit project code access**: Cannot review code without access to the codebase or diffs. Auto-scope detection helps but requires git history.

2. **Depends on user expertise for architectural context**: Health scoring requires understanding domain and intent. False positives possible if domain is misunderstood.

3. **Test Decay risks require test file visibility**: Cannot assess T1–T6 without test code. PR reviews include lightweight Step 7 Quick Test Check but require actual test files for full Mode 4.

4. **Configuration complexity**: Project teams may need to customize decay-risk definitions via custom risk codes (Cx format) if standard 12-book framework does not match their domain.

5. **Performance**: Full architecture audits on very large codebases may require scoping via `--since=<ref>` to analyze only changed modules.

6. **Not a linter replacement**: Does not catch syntax errors, style violations, or security issues that linters handle. Designed for architectural and domain-level decay, not lint rules.

Source: README.md lines 183–184 ("doesn't replace your linter"), CLAUDE.md lines 12–21 (configuration complexity notes) (accessed 2026-05-10).

### Explicitly Unscoped

- **VS Code extension**: Out of scope per CLAUDE.md (accessed 2026-05-10)
- **Language-specific modes**: Tool claims "works with any language" (README.md line 179) — framework is language-agnostic, but decay-risk symptom patterns are general principles applicable across Python, TypeScript, Go, Java

Source: CLAUDE.md lines 12–13, README.md line 179 (accessed 2026-05-10).

---

## Relevance to Claude Code Development

### Direct Application

1. **Code review automation at scale**: brooks-lint's Iron Law (Symptom → Source → Consequence → Remedy) and structured findings map directly to Claude Code's `/code-review` workflow. Can serve as a reference for producing consistent, traceable code review findings.

2. **Skill framework & modularity pattern**: Brooks-lint's architecture — shared framework + six independent skills with dedicated guides — exemplifies best practices for skill composition, reuse, and maintainability. The `.claude-plugin/` structure and hook-based command auto-installation are portable patterns for Claude Code plugin development.

3. **Configuration & project customization**: `.brooks-lint.yaml` parsing and per-project risk overrides provide a model for how Claude Code skills can adapt to project conventions without hard-coding domain knowledge.

4. **Book-grounded principles**: The explicit grounding of every finding in named books and principles (Fowler, Brooks, McConnell, Martin, etc.) models how Claude Code skills can cite authoritative sources and avoid hallucination through evidence-based diagnosis.

5. **Eval suite best practices**: The 49 benchmark scenarios (including false-positive guards and tradeoff cases) and live eval infrastructure (`run-evals-live.mjs`) demonstrate structured evaluation methodology for AI-powered tools.

### Integration Opportunities

1. **Extend `/code-review` skill**: Brooks-lint's decay-risk framework could supplement Claude Code's existing code review tool with book-grounded architectural analysis.

2. **Plugin marketplace reference**: Well-structured Claude Code plugin with clear skill modularity, documentation, and CI/CD integration; exemplifies marketplace-ready plugin patterns.

3. **Health scoring for projects**: The composite Health Score (0–100) aggregating multiple decay dimensions could inform project health dashboards or sprint retrospectives in development workflows.

Source: README.md, CLAUDE.md, AGENTS.md, plugin.json (accessed 2026-05-10).

---

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Maverick](./maverick.md) | coding-agents | Enforcement chain for multi-stage code review with best-practice → verify → CI → agent review progression |
| [Cline](./cline.md) | coding-agents | Human-in-the-loop approval gates for autonomous code agent output |
| [OpenHands](./openhands.md) | coding-agents | Cloud-based platform generating code that requires quality review and assessment |
| [Hound](../code-auditing/hound.md) | code-auditing | Autonomous code auditor using knowledge graphs and pattern analysis for structural decay detection |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Comprehensive system with 65+ skills, 16 agents, and AgentShield security scanner for code quality |
| [Narsil-MCP](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | Code intelligence infrastructure with 90 tools for symbol analysis and architectural pattern detection |
| [Rope](../code-auditing/rope.md) | code-auditing | AST-based refactoring library enabling automated fixes for decay patterns identified in code reviews |

---

## Freshness Tracking

- **Last Content Update**: 2026-04-29 (CHANGELOG.md v1.2.2 — aggressive token reduction pass)
- **Last Commit**: 2026-05-01 (verified via git log)
- **Latest Release**: v1.2.2 (2026-04-29)
- **Access Date**: 2026-05-10
- **Cross-References Added**: 2026-05-10

### Confidence Summary

| Section | Confidence | Notes |
|---------|------------|-------|
| **Identity & Metadata** | high | Version, author, license verified in package.json, plugin.json, LICENSE file (accessed 2026-05-10) |
| **Problem Addressed** | high | Extracted from README.md lines 33–34, clearly stated in intro; supported by all skill guides |
| **Key Statistics** | high | Book count (12), decay-risk counts (R1–R6, T1–T6), skill guide totals (2,406 lines), benchmark data (94% vs 16%), eval scenarios (49) extracted from README and CHANGELOG |
| **Technical Architecture** | high | Core components documented in CLAUDE.md, README.md project-structure section, and skill directory structure verified by local inspection |
| **Key Features** | high | All features extracted from README.md, AGENTS.md, skill SKILL.md files, and configuration examples (.brooks-lint.example.yaml analogs) |
| **Installation & Usage** | high | Multi-platform install paths and command examples verified in README.md lines 185–237 |
| **Benchmark Results** | high | Table at README.md lines 154–166 with exact percentages (100%, 0%, 94%, 16%) |
| **Limitations** | medium | Documented limitations are explicit where stated; absence of documented limitations in some areas may not reflect absence of actual limitations |
| **Relevance to Claude Code** | high | Assessed from CLAUDE.md, plugin structure, and alignment with Claude Code plugin standards |

### Next Review

**Recommended next review**: 2026-08-10 (3 months from today)

Focus areas for refresh:
- Check for major version releases beyond 1.2.2
- Re-verify benchmark methodology and results
- Confirm GitHub Action integration remains current
- Review any new custom-risk code examples

---

## References

- **README.md** — Project overview, six decay risks, six analysis modes, installation, benchmarks, CI/CD integration
  <https://github.com/hyhmrright/brooks-lint/blob/main/README.md> (accessed 2026-05-10)

- **CHANGELOG.md** — Version history, v1.2.2 release notes (2026-04-29)
  <https://github.com/hyhmrright/brooks-lint/blob/main/CHANGELOG.md> (accessed 2026-05-10)

- **package.json** — Version (1.2.2), dependencies (@anthropic-ai/sdk), development scripts
  <https://github.com/hyhmrright/brooks-lint/blob/main/package.json> (accessed 2026-05-10)

- **.claude-plugin/plugin.json** — Plugin manifest, description, version
  <https://github.com/hyhmrright/brooks-lint/blob/main/.claude-plugin/plugin.json> (accessed 2026-05-10)

- **CLAUDE.md** — Developer guide, workflow conventions, critical gotchas, skill architecture, eval suite
  <https://github.com/hyhmrright/brooks-lint/blob/main/CLAUDE.md> (accessed 2026-05-10)

- **AGENTS.md** — Core purpose, skill integration, engineering standards, project structure (Codex CLI perspective)
  <https://github.com/hyhmrright/brooks-lint/blob/main/AGENTS.md> (accessed 2026-05-10)

- **skills/_shared/common.md** — Iron Law, report template, project config parsing, Health Score algorithm
  <https://github.com/hyhmrright/brooks-lint/blob/main/skills/_shared/common.md> (accessed 2026-05-10)

- **skills/_shared/decay-risks.md** — Detailed diagnostic criteria for R1–R6 with symptoms, sources, severity guides, guards
  <https://github.com/hyhmrright/brooks-lint/blob/main/skills/_shared/decay-risks.md> (accessed 2026-05-10)

- **skills/_shared/source-coverage.md** — 12-book coverage matrix, review discipline, tradeoffs, exceptions
  <https://github.com/hyhmrright/brooks-lint/blob/main/skills/_shared/source-coverage.md> (accessed 2026-05-10)

- **LICENSE** — MIT License, Copyright 2025 hyhmrright
  <https://github.com/hyhmrright/brooks-lint/blob/main/LICENSE> (accessed 2026-05-10)

- **Git repository metadata** — Last commit (2026-05-01), version tag v1.2.2, contributor history
  <https://github.com/hyhmrright/brooks-lint> (accessed 2026-05-10)

