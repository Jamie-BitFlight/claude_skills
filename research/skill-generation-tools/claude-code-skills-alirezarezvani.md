---
title: "Claude Code Skills Library by Alireza Rezvani"
subtitle: "Production-ready modular skill packages for AI coding agents"
resource_name: "alirezarezvani/claude-skills"
resource_type: "GitHub Repository — Skill Package Library"
repository_url: "https://github.com/alirezarezvani/claude-skills"
license: "MIT"
version_at_research: "v2.9.0"
last_verified: "2026-08-11"
confidence_summary: "high — verified against primary sources with current API data"
---

## Overview

Claude Code Skills Library by Alireza Rezvani is a production-ready repository of **362 modular skill packages** for Claude AI and Claude Code. The library provides 644 stdlib-only Python CLI tools, 102 agent configurations, 116 slash commands, and expertise across **18 specialization domains** (Engineering Core, Engineering Advanced, Product, Marketing, Project Management, Regulatory & Quality, C-Level Advisory, Business & Growth, Finance, and others). Each skill is self-contained with SKILL.md (workflows + instructions), `scripts/` (Python CLI tools), `references/` (knowledge bases), and `assets/` (templates). Compatible with 13 AI coding tools including Claude Code, OpenAI Codex, Gemini CLI, Cursor, and others.

**Source**: GitHub repository README.md and API metadata (accessed 2026-08-11)

**Current Status**: Active development; v2.9.0 (Research Operations enhancement); 24,245 GitHub stars, 3,416 forks; last updated 2026-08-10 UTC.

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

| Domain | Skills | Highlights |
|--------|--------|-----------|
| Engineering Core | 26 | Architecture, frontend, backend, fullstack, QA, DevOps, Playwright Pro |
| Engineering Advanced | 30 | Agent designer, RAG architect, MCP builder, performance profiler |
| Product | 14 | Product manager, agile PO, UX researcher, landing page generator |
| Marketing | 43 | Content, SEO, CRO, channels, growth, intelligence, sales enablement |
| Project Management | 6 | Senior PM, scrum master, Jira, Confluence, Atlassian admin |
| Regulatory & QM | 12 | ISO standards, FDA, GDPR, CAPA, clinical evaluation |
| C-Level Advisory | 28 | C-suite roles (CEO, CTO, CFO, CMO, CISO, CHRO), strategic support |
| Business & Growth | 4 | Customer success, sales engineer, revenue ops, contracts |
| Finance | 2 | Financial analyst (DCF, budgeting, forecasting), SaaS metrics |

**Total**: 362 skills across 18 domains

**Source**: README.md skills overview table (accessed 2026-08-11)

### 3. Zero-Dependency Python Tools (644 scripts)

All Python CLI scripts use standard library only—no pip installs required. Tools verified to run with `--help` without errors.

**Examples**:
- `finance/saas-metrics-coach/scripts/metrics_calculator.py --mrr 80000 --customers 200`
- `marketing-skill/content-production/scripts/brand_voice_analyzer.py article.txt`
- `c-level-advisor/cto-advisor/scripts/tech_debt_analyzer.py /path/to/codebase`

**Source**: README.md Python Tools section and CHANGELOG.md v2.9.0 verification statements (accessed 2026-08-11)

### 4. Multi-Platform Skill Format

One repository, 13 AI coding tools. Skills convert natively via internal conversion system:
- Claude Code (primary)
- OpenAI Codex CLI and agents
- Gemini CLI
- Cursor
- Aider
- Windsurf
- Kilo Code
- OpenCode
- Augment
- Antigravity CLI
- And others

**Source**: README.md platform compatibility section (accessed 2026-08-11)

### 5. Security & Quality

- **Skill Security Auditor** — Scan any skill for vulnerabilities: command injection, code execution, data exfiltration, prompt injection, supply chain risks, privilege escalation
- **Production Quality Pipeline** — Linting, security review, and Tessl quality optimization (skills scored 0-100%)
- **No build/test framework** — Intentional design for portability across platforms

**Source**: README.md Security section and SKILL-AUTHORING-STANDARD.md (accessed 2026-08-11)

---

## Technical Architecture

### Skill-as-Module Pattern

Each skill is a self-contained directory (one level deep under a domain folder) with zero interdependencies. Folders nest only one level: `domain/skill-name/`, not nested subdirectories.

**Knowledge Flow**: Information flows from `references/` → `SKILL.md` workflows → executed via `scripts/` → applied using `assets/` templates.

**Source**: CLAUDE.md and SKILL-AUTHORING-STANDARD.md (accessed 2026-08-11)

### Marketplace Distribution

`.claude-plugin/marketplace.json` coordinates skill publication across multiple channels:
- Claude Code marketplace
- ClawHub registry
- Individual tool indexes

**Semantic Versioning**: Current v2.9.0; backward compatibility maintained within patch releases.

**Source**: `.claude-plugin/marketplace.json` registry structure (accessed 2026-08-11)

### Git Workflow & Maintenance

**Branch Strategy**: feature → dev → main (PR only)

**Version Management**: Semantic versioning; v2.9.0 current stable release with Research Operations enhancements

**Maintenance Cadence**: Last updated 2026-08-10 UTC; active development with regular feature additions and quality optimizations.

**Source**: GitHub repo metadata and CHANGELOG.md (accessed 2026-08-11)

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
/plugin install senior-architect@claude-code-skills
```

**Source**: README.md Installation section (accessed 2026-08-11)

### Manual Installation

```bash
git clone https://github.com/alirezarezvani/claude-skills.git
cd claude-skills

# Copy skill folder to local Claude Code directory
cp -r engineering-team/senior-architect ~/.claude/skills/
```

**Source**: README.md manual installation instructions (accessed 2026-08-11)

### Multi-Platform Deployment

Skills are compatible with 13 AI coding tools via standardized SKILL.md format. Each platform has its own setup instructions in the README.

**Source**: README.md platform compatibility and installation sections (accessed 2026-08-11)

### Python Tool Usage Example

```bash
# SaaS metrics analysis
python3 finance/saas-metrics-coach/scripts/metrics_calculator.py \
  --mrr 80000 --customers 200 --churned 3 --json

# Tech debt scoring
python3 c-level-advisor/cto-advisor/scripts/tech_debt_analyzer.py /path/to/codebase

# Skill security audit
python3 engineering/skill-security-auditor/scripts/skill_security_auditor.py /path/to/skill/
```

**Source**: README.md Python Tools examples (accessed 2026-08-11)

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

### 4. No Built-In Testing Framework

Skills have no automated testing (unit, integration, or E2E). Quality assurance relies on manual review and Tessl scoring.

**Source**: CLAUDE.md design rationale (accessed 2026-08-11)

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
- [GitHub API — Repository Metadata](https://api.github.com/repos/alirezarezvani/claude-skills) (24,245 stars, 3,416 forks, accessed 2026-08-11)

---
