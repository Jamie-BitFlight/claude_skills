---
title: "Claude Code Skills Library by Alireza Rezvani"
subtitle: "Production-ready modular skill packages for AI coding agents"
resource_name: "alirezarezvani/claude-skills"
resource_type: "GitHub Repository — Skill Package Library"
repository_url: "https://github.com/alirezarezvani/claude-skills"
license: "MIT"
version_at_research: "v2.9.0 (latest tagged release); main branch at v2.11.2 per CLAUDE.md"
last_verified: "2026-08-11"
confidence_summary: "high — verified against primary sources with current API data"
---

## Overview

Claude Code Skills Library by Alireza Rezvani is a production-ready repository of **362 modular skill packages** for Claude AI and Claude Code. The library provides 644 stdlib-only Python CLI tools, 102 agent configurations, 116 slash commands, and expertise across **18 specialization domains** (Engineering Core, Engineering Advanced, Product, Marketing, Project Management, Regulatory & Quality, C-Level Advisory, Business & Growth, Finance, and others). Each skill is self-contained with SKILL.md (workflows + instructions), `scripts/` (Python CLI tools), `references/` (knowledge bases), and `assets/` (templates). Compatible with 13 AI coding tools including Claude Code, OpenAI Codex, Gemini CLI, Cursor, and others.

**Source**: GitHub repository README.md and API metadata (accessed 2026-08-11)

**Current Status**: Active development. Latest tagged GitHub release is **v2.9.0** (published 2026-05-28, added the `research-ops/` Research Operations domain); the `main` branch is further ahead — `CLAUDE.md` describes **v2.11.2** as current with post-v2.11.2 work unreleased. 24,252 GitHub stars, 3,416 forks; last push 2026-08-09 UTC.

**Source**: GitHub API repository metadata, `/releases`, and CLAUDE.md line 9 (accessed 2026-08-11)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents ship with general-purpose capabilities but lack domain expertise | 362 skill packages that give agents specialized knowledge for engineering, product, marketing, compliance, and executive roles |
| Replicating expertise across different AI platforms requires multiple implementations | One repository, 13 platforms; conversion scripts output platform-native formats |
| Skill development imposes dependency management overhead | Zero pip dependencies; all 644 Python scripts use stdlib only—portable anywhere Python runs |
| No standard for packaging reusable agent expertise | Standardized SKILL.md frontmatter (YAML metadata), folder structure (scripts/, references/, assets/), and marketplace registry (`.claude-plugin/marketplace.json`) |
| Large skill libraries lack quality assurance | Production pipeline with linting, security audit, and Tessl quality optimization |

**Source**: GitHub README.md lines 1-50, CHANGELOG.md, CLAUDE.md (accessed 2026-08-11)

---

## Key Features

### 1. Modular Skill Architecture

Each skill is self-contained:
- **SKILL.md** — Master documentation with workflows and instructions
- **scripts/** — Python CLI tools for automation (stdlib-only, zero pip dependencies)
- **references/** — Expert knowledge bases (templates, checklists, frameworks)
- **assets/** — User-facing templates ready to customize

Design intent: "Skills are products. Each skill deployable as standalone package." Skills can be extracted and used immediately without dependencies on other skills or the main repository.

**Source**: CLAUDE.md and SKILL-AUTHORING-STANDARD.md (accessed 2026-08-11)

### 2. Multi-Domain Expertise: 18 Specialization Areas

| Domain | Skills | Directory | Highlights |
|--------|--------|-----------|-----------|
| Engineering — Core | 52 | `engineering-team/` | Architecture, frontend, backend, fullstack, QA, DevOps, SecOps, AI/ML, data, Playwright Pro, self-improving agent, a11y audit |
| Engineering — POWERFUL | 84 | `engineering/` | Agent designer, RAG architect, database designer, CI/CD builder, security auditor, MCP builder, Helm, Terraform, zero-hallucination-coder, skillopt-sleep |
| Product | 17 | `product-team/` | Product manager, agile PO, strategist, UX researcher, UI design, landing pages, code-to-prd, apple-hig-expert |
| Marketing | 48 | `marketing-skill/` | 8 pods: Content, SEO + AEO + local SEO, CRO, Channels, Growth, Intelligence, Sales |
| Productivity | 11 | `productivity/` | capture, email pair, reflect, handoff, andreessen, roast, fable-goal, weekly-review, deep-work, meetings |
| Marketing (top-level) | 1 | `marketing/` | `landing` — single-file HTML landing-page generator |
| Research (academic) | 9 | `research/` | Orchestrator + pulse, litreview, grants, dossier, patent, syllabus, notebooklm, deep-research |
| Research Operations | 5 | `research-ops/` | Orchestrator + clinical-research, research-finance, market-research, product-research (added v2.9.0) |
| Project Management | 9 | `project-management/` | Senior PM, scrum master, Jira, Confluence, Atlassian admin + bundled Atlassian Remote MCP |
| Regulatory & QM | 19 | `ra-qm-team/` | ISO 13505, MDR 2017/745, FDA, ISO 27001, GDPR, SOC 2, CAPA, risk management |
| Compliance OS | 9 | `compliance-os/` | Controls, evidence, audit-readiness workflows |
| C-Level Advisory | 68 | `c-level-advisor/` | Full C-suite (CEO/CTO/CFO/CMO/CRO/CPO/COO/CHRO/CISO/GC/CDO/CAIO/CCO/VPE) + founder-mode agents |
| Business & Growth | 5 | `business-growth/` | Customer success, sales engineer, revenue ops, contracts & proposals, BizDev toolkit |
| Business Operations | 7 | `business-operations/` | Orchestrator + process-mapper, vendor-management, capacity-planner, internal-comms, knowledge-ops, procurement-optimizer |
| Commercial | 8 | `commercial/` | Orchestrator + pricing-strategist, deal-desk, partnerships-architect, channel-economics, commercial-policy, rfp-responder, commercial-forecaster |
| Finance | 4 | `finance/` | Financial analyst (DCF, budgeting, forecasting), SaaS metrics coach, business investment advisor |
| Loop Library | 1 | `loop-library/` | `loop-library` — bounded AI-agent loop catalog, vendored from Forward-Future/loop-library |
| Markdown → HTML | 5 | `markdown-html/` | Orchestrator + design-system, md-document, md-review, md-slides |

Per-domain counts are as published in the README's "Skills Overview" table, which states **362 skills across 18 domains**. Upstream derives these counters from the repository tree via `scripts/derive_counters.py --check`.

**Source**: README.md "Skills Overview" table lines 151–175 (accessed 2026-08-11)

### 3. Zero-Dependency Python Tools (644 scripts)

All Python CLI scripts use standard library only—no pip installs required. Tools verified to run with `--help` without errors.

Scripts live at `{domain}/skills/{skill-name}/scripts/`. **Examples** (paths verified against the repository tree):
- `finance/skills/saas-metrics-coach/scripts/metrics_calculator.py`
- `marketing-skill/skills/content-production/scripts/brand_voice_analyzer.py`
- `c-level-advisor/skills/cto-advisor/scripts/tech_debt_analyzer.py`
- `engineering/skills/skill-security-auditor/scripts/skill_security_auditor.py`

**Source**: README.md "What Are Claude Code Skills" section (644 CLI scripts, stdlib-only) and repository git tree (accessed 2026-08-11)

### 4. Multi-Platform Skill Format

One repository, 13 AI coding tools, listed in the README's "Works with" line: Claude Code, OpenAI Codex, Gemini CLI, OpenClaw, Hermes Agent, Mistral Vibe, Cursor, Aider, Windsurf, Kilo Code, OpenCode, Augment, Antigravity.

Claude Code, Codex, Gemini CLI, Hermes Agent, and Mistral Vibe consume the `SKILL.md` standard natively; the remaining tools are served by `scripts/convert.sh` / `scripts/install.sh --tool {name}`, which emits platform-native formats (Cursor `.mdc` rules, Aider `CONVENTIONS.md`, `.kilocode/rules/`, `.windsurf/skills/`, `.opencode/skills/`, `.augment/rules/`). Hermes Agent and Mistral Vibe are documented as **BYO-sync tier** — the repo ships a pre-generated tree, but a local sync script must be run once to install it.

**Source**: README.md header "Works with" line, footnotes on Hermes/Vibe, and "Multi-Tool Support" table (accessed 2026-08-11)

### 5. Security & Quality

- **Skill Security Auditor** — Scan any skill for vulnerabilities: command injection, code execution, data exfiltration, prompt injection, supply chain risks, privilege escalation
- **Production Quality Pipeline** — Linting, security review, and Tessl quality optimization (skills scored 0-100%)
- **No CI test gate** — The repository includes a local pytest suite, but it is not run in CI

**Source**: README.md Security section and SKILL-AUTHORING-STANDARD.md (accessed 2026-08-11)

---

## Technical Architecture

### Skill-as-Module Pattern

Each skill is a self-contained directory under its domain's `skills/` folder — `{domain}/skills/{skill-name}/` — containing `SKILL.md`, `scripts/`, `references/`, and `assets/`, with zero interdependencies between skills.

**Knowledge Flow**: Information flows from `references/` → `SKILL.md` workflows → executed via `scripts/` → applied using `assets/` templates.

**Source**: CLAUDE.md and SKILL-AUTHORING-STANDARD.md (accessed 2026-08-11)

### Marketplace Distribution

`.claude-plugin/marketplace.json` is the Claude Code plugin registry and declares **88 plugins** (domain bundles such as `marketing-skills` and `c-level-skills`, plus individual-skill plugins).

ClawHub (clawhub.com) is a separate distribution registry with its own publishing constraints documented in CLAUDE.md: a `cs-` prefix is used only when a slug is already taken on ClawHub, repo folder names are never renamed to match ClawHub slugs, and publishing is rate-limited to 5 new skills per hour.

**Semantic Versioning**: latest tagged release v2.9.0; `main` documents v2.11.2.

**Source**: `.claude-plugin/marketplace.json` (88 plugin entries) and CLAUDE.md "ClawHub Publishing Constraints" lines 520–544 (accessed 2026-08-11)

### Git Workflow & Maintenance

**Branch Strategy**: feature → dev → main (PR only)

The rule is stated as a hard constraint in CLAUDE.md: every PR targets `dev`, never `main`; `main` only receives periodic `dev → main` promotion PRs opened by the maintainer.

**Version Management**: Semantic versioning. GitHub's release list tops out at v2.9.0 (2026-05-28), while CHANGELOG.md's most recent dated section is `[2.8.2]` (2026-05-23) followed by several `[Unreleased]` sections — the three sources are not in sync, so treat CLAUDE.md's v2.11.2 as the state of `main` rather than a published release.

**Maintenance Cadence**: Last push 2026-08-09 UTC; active development with regular feature additions and quality optimizations.

**Source**: CLAUDE.md lines 103–112, CHANGELOG.md section headers, GitHub `/releases` and repo metadata (accessed 2026-08-11)

---

## Installation & Usage

### Claude Code (Recommended)

```bash
# Add marketplace
/plugin marketplace add alirezarezvani/claude-skills

# Install skill bundles by domain
/plugin install engineering-skills@claude-code-skills
/plugin install marketing-skills@claude-code-skills
/plugin install c-level-skills@claude-code-skills
```

**Or install individual skills**:

```bash
/plugin install skill-security-auditor@claude-code-skills
/plugin install playwright-pro@claude-code-skills
/plugin install self-improving-agent@claude-code-skills
/plugin install content-creator@claude-code-skills
```

**Source**: README.md Installation section (accessed 2026-08-11)

### Manual Installation

```bash
git clone https://github.com/alirezarezvani/claude-skills.git
cd claude-skills

# Copy any skill folder to ~/.claude/skills/ (Claude Code) or ~/.codex/skills/ (Codex)
cp -r engineering-team/skills/senior-architect ~/.claude/skills/
```

**Source**: README.md manual installation instructions (accessed 2026-08-11)

### Multi-Platform Deployment

Skills are compatible with 13 AI coding tools via standardized SKILL.md format. Each platform has its own setup instructions in the README.

**Source**: README.md platform compatibility and installation sections (accessed 2026-08-11)

### Python Tool Usage Example

```bash
# SaaS metrics analysis — flags verified in metrics_calculator.py argparse block
python3 finance/skills/saas-metrics-coach/scripts/metrics_calculator.py \
  --mrr 80000 --customers 200 --churned 3 --json

# Brand voice analysis — positional file argument, optional --format json|text
python3 marketing-skill/skills/content-production/scripts/brand_voice_analyzer.py article.txt

# Skill security audit — positional path (directory or git URL), optional --strict/--json
python3 engineering/skills/skill-security-auditor/scripts/skill_security_auditor.py /path/to/skill/
```

Not every script exposes a CLI. `c-level-advisor/skills/cto-advisor/scripts/tech_debt_analyzer.py`, for example, has no `argparse` block — its `__main__` guard runs a hard-coded example system dict and prints the result, so it is imported as a module rather than invoked with a path argument.

**Source**: argparse blocks read directly from `metrics_calculator.py` (lines 158–172), `brand_voice_analyzer.py` (lines 176–190), `skill_security_auditor.py` (lines 997–1024), and `tech_debt_analyzer.py` (accessed 2026-08-11)

---

## Limitations and Caveats

### 1. Skills Are Not Complete AI Systems

Skills provide workflows, reference materials, and CLI tools — but require a Claude agent or human to orchestrate outputs and make final decisions. They are expertise packages, not autonomous systems.

**Source**: CLAUDE.md project scope statement (accessed 2026-08-11)

### 2. Python Scripts: No ML/LLM Calls

All scripts use standard library only and make no ML/LLM calls. This ensures portability but limits semantic analysis to deterministic logic.

**Source**: CLAUDE.md tooling constraints (accessed 2026-08-11)

### 3. No Skill Interdependencies

Skills are intentionally designed as standalone packages — no direct dependencies between skills. Orchestration is manual via personas or skill chains.

**Source**: CLAUDE.md anti-patterns section (accessed 2026-08-11)

### 4. No Test Framework in CI

CLAUDE.md states "No build system or test frameworks — intentional design choice for portability," and lists "adding complex build systems or test frameworks" as an explicit anti-goal. A `tests/` pytest suite does exist but is documented as "run locally; not in CI," so nothing gates a change on test results. Quality assurance relies on linting, security audit, and Tessl scoring instead.

**Source**: CLAUDE.md lines 20, 147, and 549 (accessed 2026-08-11)

---

## Relevance to Claude Code Development

### High Relevance

1. **Reference Architecture for Skill Design**: The repository documents the Claude Code skill package standard (SKILL.md format, scripts structure, references separation). Directly applicable to the `/research-curator` agent work and other skill development in claude_skills.

2. **Multi-Domain Organization at Scale**: 362 skills across 18 domains with minimal coupling demonstrate patterns for organizing large skill libraries. Replicable.

3. **Practical Tool Patterns**: 644 Python CLI tools using standard library only provide examples of portable, dependency-free automation applicable to skills in claude_skills.

4. **Documentation-Driven Approach**: Emphasizes documentation as the primary interface (SKILL.md, references, templates) rather than code libraries — aligns with Claude Code philosophy.

### Medium Relevance

5. **Security Patterns**: The skill-security-auditor provides reusable pattern for scanning AI agent code. Adaptable for skill validation in claude_skills marketplace.

6. **Quality Standards**: SKILL-AUTHORING-STANDARD.md and production pipeline define production quality for AI agent skills. Applicable when setting quality expectations for contributed skills.

---

## Relevance to Claude Code Development (Extended)

### Integration Opportunities

- Extend `/audit-skill-completeness` with multi-domain review taxonomy from this library if building comprehensive review tooling
- Reference the production quality pipeline when defining validation workflows for plugin marketplaces
- Use the zero-dependency Python tool pattern for portable automation across different environments

---

## References

- [Claude Code Skills Library GitHub Repository](https://github.com/alirezarezvani/claude-skills) (accessed 2026-08-11)
- [GitHub README.md](https://github.com/alirezarezvani/claude-skills/blob/main/README.md) (accessed 2026-08-11)
- [SKILL-AUTHORING-STANDARD.md](https://github.com/alirezarezvani/claude-skills/blob/main/SKILL-AUTHORING-STANDARD.md) (accessed 2026-08-11)
- [CHANGELOG.md — v2.9.0](https://github.com/alirezarezvani/claude-skills/blob/main/CHANGELOG.md) (accessed 2026-08-11)
- [CLAUDE.md — Project Guidance](https://github.com/alirezarezvani/claude-skills/blob/main/CLAUDE.md) (accessed 2026-08-11)
- [.claude-plugin/marketplace.json](https://github.com/alirezarezvani/claude-skills/blob/main/.claude-plugin/marketplace.json) (accessed 2026-08-11)
- [GitHub API — Repository Metadata](https://api.github.com/repos/alirezarezvani/claude-skills) (24,252 stars, 3,416 forks, MIT, accessed 2026-08-11)
- [GitHub API — Releases](https://api.github.com/repos/alirezarezvani/claude-skills/releases) (latest tag v2.9.0, published 2026-05-28, accessed 2026-08-11)

---
