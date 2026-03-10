---
title: "Claude Code Skills Library by Alireza Rezvani"
subtitle: "Production-ready modular skill packages for AI coding agents"
resource_name: "alirezarezvani/claude-skills"
resource_type: "GitHub Repository — Skill Package Library"
repository_url: "https://github.com/alirezarezvani/claude-skills"
license: "MIT"
last_updated: "2026-03-10"
confidence_summary: "high — primary sources read in full; recent maintenance confirmed"
---

## Identity & Metadata

**Name:** Claude Code Skills Library (also: claude-code-skills)
**Author:** Alireza Rezvani
**Repository URL:** <https://github.com/alirezarezvani/claude-skills>
**License:** MIT (copyright 2025 Alireza Rezvani)
**Latest Version:** 2.1.1 (released 2026-03-07)
**Last Commit:** 2026-03-10 (feat: add seek-and-analyze-video skill #300)
**GitHub Stars:** 2,500+ (claimed in README as of latest access)
**Repository Type:** Production-ready open-source skill package library

**Keywords:** Claude Code, AI skills, modular agents, plugin architecture, skill packages, OpenAI Codex, Gemini CLI

---

## What It Is

A comprehensive, **production-ready library of 170 modular skill packages** for Claude AI and Claude Code. Skills are reusable instruction bundles that give AI coding agents domain-specific expertise they don't have out of the box.

**Source:** "170 production-ready skills and plugins for Claude Code, OpenAI Codex, and OpenClaw — reusable expertise bundles that transform AI coding agents into specialized professionals across engineering, product, marketing, compliance, and more." (README.md, line 3)

**Key Design Principle:** "Skills are modular instruction packages (plugins) that give AI coding agents domain expertise they don't have out of the box. Each skill includes a SKILL.md (instructions + workflows), Python CLI tools, and reference documentation — everything the agent needs to perform like a specialist." (README.md, line 18)

**Confidence:** high — directly quoted from primary documentation

---

## Core Features

### 1. Modular Skill Architecture

Each skill follows a standardized package structure:

```text
skill-name/
├── SKILL.md              # Master documentation with workflows
├── scripts/              # Python CLI tools (no ML/LLM calls)
├── references/           # Expert knowledge bases (markdown)
└── assets/               # User templates
```

**Source:** CLAUDE.md, lines 60-66: "Each skill follows this structure: SKILL.md (master documentation), scripts/ (Python CLI tools), references/ (expert knowledge bases), assets/ (user templates). Knowledge flows from `references/` → into `SKILL.md` workflows → executed via `scripts/` → applied using `assets/` templates."

**Mechanism:** Skills are self-contained packages. Teams can extract any skill folder and use it immediately without dependencies on other skills or the main repository.

**Confidence:** high — architecture documented in primary authoring standard

### 2. Multi-Platform Compatibility

Works natively across four AI platforms without modification:

- **Claude Code** (primary platform)
- **OpenAI Codex** CLI and agents
- **Gemini CLI** (added in v2.1.1)
- **OpenClaw** (open-source alternative)

**Source:** README.md, line 20: "Works natively as Claude Code plugins, OpenAI Codex CLI and agents, Gemini CLI, and OpenClaw skills. One repo, four platforms."

**Installation examples across platforms:**

```bash
# Claude Code (recommended)
/plugin marketplace add alirezarezvani/claude-skills
/plugin install engineering-skills@claude-code-skills

# Gemini CLI (new in v2.1.1)
./scripts/gemini-install.sh
activate_skill(name="senior-architect")

# OpenAI Codex
npx agent-skills-cli add alirezarezvani/claude-skills --agent codex

# Manual
git clone https://github.com/alirezarezvani/claude-skills.git
# Copy any skill folder to ~/.claude/skills/ or ~/.codex/skills/
```

**Source:** README.md, lines 25-82 (Installation section)

**Confidence:** high — installation commands extracted from official documentation

### 3. Domain Coverage: 9 Specialization Areas

**Engineering:**

- **Core (23 skills):** Architecture, frontend, backend, fullstack, QA, DevOps, SecOps, AI/ML, data engineering, Playwright Pro (9+3 sub-skills), Self-Improving Agent (5+2 sub-skills)
- **POWERFUL Tier (25 skills):** Agent designer, RAG architect, database designer, CI/CD builder, security auditor, MCP builder, performance profiler, incident commander, tech debt tracker, and 15 more advanced specializations

**Non-Engineering Domains (130 skills):**

- **Product (8 skills):** Product manager, agile PO, UX researcher, UI design, landing page generator, SaaS scaffolder
- **Marketing (42 skills):** Content, SEO, CRO, channels, growth, intelligence, sales enablement (7 pods, 27 Python tools)
- **Project Management (6 skills):** Senior PM, scrum master, Jira, Confluence, Atlassian admin, templates
- **C-Level Advisory (28 skills):** Full C-suite (CEO, CTO, COO, CPO, CMO, CFO, CRO, CISO, CHRO), executive mentor, founder coach, board meetings, strategic decision support
- **Regulatory & Quality (12 skills):** ISO 13485, MDR 2017/745, FDA 510(k)/PMA, GDPR, ISO 27001, CAPA, clinical evaluation (focused on HealthTech/MedTech)
- **Business & Growth (4 skills):** Customer success manager, sales engineer, revenue operations, contract/proposal writer
- **Finance (1 skill):** Financial analyst (DCF, budgeting, forecasting, ratio analysis)

**Source:** README.md, lines 88-102 (Skills Overview table); CLAUDE.md, lines 40-55 (detailed breakdown)

**Confidence:** high — directly extracted from primary documentation with clear structure

### 4. Execution Tools: 210+ Python CLI Scripts

**Zero-dependency design:** "All 210+ Python CLI tools use the standard library only — zero pip installs required." (README.md, line 229)

**Examples of automation tools:**

- Brand voice analyzer (marketing)
- Tech debt scorer (C-level)
- RICE prioritizer (product)
- Skill security auditor (engineering)

**Source:** README.md, lines 192-206 (Python Analysis Tools section): Code examples show tools like `brand_voice_analyzer.py`, `tech_debt_analyzer.py`, `rice_prioritizer.py`, `skill_security_auditor.py`

**Execution pattern:** "Each skill ships with `scripts/`, extracted `references/`, and a usage-focused `README.md`." (README.md, line 164)

**Confidence:** high — tools and patterns documented with code paths

### 5. Recent Quality Enhancements (v2.1.1)

**Tessl Quality Optimization:** "18 skills optimized from 66-83% to 85-100% via `tessl skill review --optimize`" (CHANGELOG.md, line 11)

Upgraded skills include:

- Jira Expert: 77% → 97%
- Confluence Expert: 66% → 94%
- Playwright Pro: 82% → 100%
- Senior Backend: 83% → 100%
- CTO Advisor: 82% → 99%

**Documentation site:** "MkDocs Material documentation site at alirezarezvani.github.io/claude-skills" (CLAUDE.md, line 135)

**Recently Enhanced Skills with New Capabilities:**

- `git-worktree-manager`: Worktree lifecycle + cleanup automation scripts
- `mcp-server-builder`: OpenAPI → MCP scaffold + manifest validator
- `changelog-generator`: Release note generator + conventional commit linter
- `ci-cd-pipeline-builder`: Stack detector + pipeline generator
- `prompt-engineer-toolkit`: Prompt A/B tester + version manager

**Source:** CHANGELOG.md, lines 10-80; README.md, lines 154-164

**Confidence:** high — extracted directly from official changelog with version numbers and quality metrics

---

## Architecture & Design Philosophy

### Skill Package Pattern

Every skill is a **self-contained, deployable unit** with:

1. **SKILL.md** — Master instruction document (workflow-first, typically <500 lines per compliance standard)
2. **scripts/** — Deterministic Python CLI tools (no LLM calls, standard library only)
3. **references/** — Expert knowledge bases (extracted markdown, 50-100 pages per major skill)
4. **assets/** — User-facing templates (frameworks, checklists, sample data)

**Design intent:** "Skills are products. Each skill deployable as standalone package." (CLAUDE.md, line 154)

**Knowledge flow:** "Knowledge flows from `references/` → into `SKILL.md` workflows → executed via `scripts/` → applied using `assets/` templates." (CLAUDE.md, line 71)

**Source:** CLAUDE.md, lines 58-71; SKILL-AUTHORING-STANDARD.md (accessed)

**Confidence:** high — architecture standardized and documented

### No Build/Test Framework — Intentional Portability

**Design choice:** "No build system or test frameworks — intentional design choice for portability." (CLAUDE.md, line 112)

**Rationale:** Keeps skills lightweight, dependency-free, and immediately runnable in any AI agent context (Claude Code, Codex, Gemini CLI, OpenClaw).

**Python tool guidelines:** "Use standard library only (minimal dependencies), CLI-first design for easy automation, support both JSON and human-readable output, no ML/LLM calls (keeps skills portable and fast)" (CLAUDE.md, lines 115-118)

**Source:** CLAUDE.md, lines 112-118

**Confidence:** high — explicit design philosophy stated in project guidance

### Git Workflow & Maintenance

**Branch Strategy:** feature → dev → main (PR only)

**Version Management:** Semantic versioning with v2.1.1 as current production release

**Maintenance Cadence:**

- Last commit: 2026-03-10 (feat: add seek-and-analyze-video skill #300)
- Active development: Feature additions in marketing domain (video analysis skill added recently)
- Quality focus: Tessl optimization cycle ongoing (18 skills updated in v2.1.1)

**Source:** Git log (head commit, accessed 2026-03-10); CHANGELOG.md

**Confidence:** high — maintenance status verified via git metadata and recent changelog entry

---

## Relationship to Claude Code Ecosystem

**Marketplace Integration:** The library is registered as a Claude Code plugin marketplace with 18 bundled plugins:

1. **marketing-skills** (42 skills)
2. **c-level-skills** (28 skills)
3. **engineering-advanced-skills** (25 POWERFUL-tier skills)
4. **engineering-skills** (23 core skills)
5. **ra-qm-skills** (12 compliance skills)
6. **product-skills** (8 skills)
7. **pm-skills** (6 project management skills)
8. **business-growth-skills** (4 skills)
9. **finance-skills** (1 skill)
10. **pw** (Playwright Pro — 9+3 sub-skills, 55 templates)
11. **self-improving-agent** (5+2 sub-skills, auto-memory curation)
12. **content-creator** (individual skill)
13. **demand-gen** (individual skill)
14. **fullstack-engineer** (individual skill)
15. **aws-architect** (individual skill)
16. **product-manager** (individual skill)
17. **scrum-master** (individual skill)
18. **skill-security-auditor** (security audit skill)

**Source:** .claude-plugin/marketplace.json, lines 14-340

**Installation pattern:** Users can add the marketplace and install skills individually or as bundled plugin sets:

```bash
/plugin marketplace add alirezarezvani/claude-skills
/plugin install engineering-skills@claude-code-skills  # 23 core engineering
/plugin install engineering-advanced-skills@claude-code-skills  # 25 POWERFUL-tier
# ... install other skill bundles as needed
```

**Confidence:** high — marketplace integration extracted from official registry

---

## Usage & Capabilities

### Example Use Cases (from README)

1. **Architecture Review:** "Using the senior-architect skill, review our microservices architecture and identify the top 3 scalability risks."

2. **Content Creation:** "Using the content-creator skill, write a blog post about AI-augmented development. Optimize for SEO targeting 'Claude Code tutorial'."

3. **Compliance Audit:** "Using the mdr-745-specialist skill, review our technical documentation for MDR Annex II compliance gaps."

**Source:** README.md, lines 170-186

**Confidence:** high — extracted verbatim from primary documentation

### Security Feature: Skill Security Auditor (v2.0.0+)

**Purpose:** Audit any skill for vulnerabilities before installation.

**Command:**

```bash
python3 engineering/skill-security-auditor/scripts/skill_security_auditor.py /path/to/skill/
```

**Scans for:**

- Command injection
- Code execution vulnerabilities
- Data exfiltration risks
- Prompt injection
- Dependency supply chain risks
- Privilege escalation

**Verdict levels:** PASS / WARN / FAIL with remediation guidance

**Source:** README.md, lines 140-151: "Scans for: command injection, code execution, data exfiltration, prompt injection, dependency supply chain risks, privilege escalation. Returns **PASS / WARN / FAIL** with remediation guidance. Zero dependencies. Works anywhere Python runs."

**Confidence:** high — security auditor is documented with specific capabilities

---

## Limitations & Caveats

### 1. Agent Scope vs. Full AI System

Skills are **expertise packages**, not complete autonomous AI systems. They provide workflows, reference materials, and CLI tools — but require a Claude agent (or human) to orchestrate the outputs and make final decisions.

**Source:** CLAUDE.md, line 11: "This is NOT a traditional application. It's a library of skill packages meant to be extracted and deployed by users into their own Claude workflows."

**Confidence:** high — explicitly stated in project purpose

### 2. Python Script Limitations

Scripts use standard library only and make **no ML/LLM calls**. This means:

- No fine-tuning or model-specific optimizations
- No integration with proprietary model capabilities (beyond what Claude provides)
- Deterministic analysis only — no probabilistic reasoning in the scripts themselves

**Source:** CLAUDE.md, lines 117-118: "No ML/LLM calls (keeps skills portable and fast)"

**Confidence:** high — design constraint stated explicitly

### 3. Platform-Specific Features Not Guaranteed Across All Platforms

While skills work natively on Claude Code, Codex, Gemini CLI, and OpenClaw, **platform-specific features** (e.g., Atlassian MCP integration for project management skills) may require additional setup on non-Claude-Code platforms.

**Source:** README.md, line 20 (compatibility claim); project-management/CLAUDE.md references Atlassian-specific integration

**Confidence:** medium — compatibility claimed broadly, but platform-specific integration patterns not fully detailed in primary sources reviewed

### 4. Documentation Maintenance Burden

With 170+ skills, 310+ reference documents, and 210+ scripts, keeping all documentation current is a significant maintenance task. README indicates recent quality optimization (v2.1.1), but broader documentation freshness for all skills is not tracked.

**Source:** Inferred from scale (170 skills) vs. maintenance capacity; recent optimization (Tessl review) partially mitigates this

**Confidence:** medium — observation based on scale and effort required, not explicit documentation of limitations

### 5. No Documented Limitations in Primary Sources

Most skills do not document explicit limitations or known constraints. The README and CLAUDE.md do not provide a comprehensive caveats section for individual skills.

**Source:** Reviewed README.md (260 lines), CLAUDE.md (191 lines), CHANGELOG.md (80+ lines) — no explicit "Limitations" sections per skill

**Confidence:** low — absence of documented limitations does not confirm absence of limitations

---

## Relevance to Claude Code Development

### High Relevance

1. **Reference Architecture for Skill Design:** The repository documents the Claude Code skill package standard (SKILL.md format, scripts structure, references separation). This is directly applicable to the `/research-curator` agent work and other skill development in the claude_skills repository.

   **Source:** SKILL-AUTHORING-STANDARD.md (comprehensive template and patterns)

2. **Multi-Domain Example:** Demonstrates how to organize 170+ skills across 9 domains with minimal coupling. Patterns (marketplace.json, CLAUDE.md per domain, consistent SKILL.md format) are replicable.

3. **Practical Tool Patterns:** 210+ Python CLI tools using standard library only provide examples of portable, dependency-free automation that applies to tools like backlog managers, task hooks, and documentation generators in the claude_skills project.

4. **Documentation-Driven Approach:** The library emphasizes documentation as the primary interface (SKILL.md, references, templates) rather than code libraries — aligns with the Claude Code philosophy.

### Medium Relevance

5. **Security Patterns:** The skill-security-auditor provides a reusable pattern for scanning AI agent code and configurations before activation. This pattern could be adapted for skill validation in the claude_skills marketplace.

6. **Agent Design Patterns:** The cs-* agent files (12 agents documented in agents/ directory) demonstrate how to design specialized agents for specific domains (engineering, marketing, C-level, etc.). Applicable to orchestration patterns.

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---------------|-------|
| **Identity/Metadata** | high | 2026-03-10 | Repository accessed, commit history verified, version 2.1.1 confirmed |
| **Features** | high | 2026-03-10 | All features extracted from README and CLAUDE.md; recent enhancements from CHANGELOG v2.1.1 |
| **Architecture** | high | 2026-03-10 | Design philosophy extracted from CLAUDE.md and SKILL-AUTHORING-STANDARD.md |
| **Usage Examples** | high | 2026-03-10 | Examples directly quoted from README usage section |
| **Limitations** | medium | 2026-03-10 | Primary sources document some constraints; full limitation inventory not available |
| **Ecosystem Integration** | high | 2026-03-10 | Marketplace metadata extracted from .claude-plugin/marketplace.json |
| **Maintenance Status** | high | 2026-03-10 | Last commit 2026-03-10; active development confirmed |

**Next Review Date:** 2026-06-10 (90 days)

**Trigger Points for Earlier Review:**

- Major version release (v3.0.0)
- Significant domain addition (new 10+ skill domain)
- Marketplace restructure or registry change
- Security audit findings affecting skill validation

---

## References

### Primary Sources (All Accessed 2026-03-10)

1. **Repository README.md** — <https://github.com/alirezarezvani/claude-skills/blob/main/README.md> (260 lines, comprehensive overview)

2. **CLAUDE.md Project Guidance** — <https://github.com/alirezarezvani/claude-skills/blob/main/CLAUDE.md> (191 lines, architecture and navigation)

3. **SKILL-AUTHORING-STANDARD.md** — <https://github.com/alirezarezvani/claude-skills/blob/main/SKILL-AUTHORING-STANDARD.md> (skill design patterns and templates)

4. **CHANGELOG.md** — <https://github.com/alirezarezvani/claude-skills/blob/main/CHANGELOG.md> (version history, v2.1.1 release notes)

5. **Marketplace Registry** — <https://github.com/alirezarezvani/claude-skills/blob/main/.claude-plugin/marketplace.json> (18 plugin definitions, v2.1.1 metadata)

6. **LICENSE** — <https://github.com/alirezarezvani/claude-skills/blob/main/LICENSE> (MIT license, copyright 2025)

7. **Git Repository Metadata** — <https://github.com/alirezarezvani/claude-skills> (last commit: 2026-03-10; star count sourced from README claim of 2,500+)

### Related Documentation Referenced

- [Documentation/delivery/](https://github.com/alirezarezvani/claude-skills/tree/main/documentation/delivery/) — Delivery and sprint history
- [Documentation/WORKFLOW.md](https://github.com/alirezarezvani/claude-skills/blob/main/documentation/WORKFLOW.md) — Git workflow guide
- [standards/git/](https://github.com/alirezarezvani/claude-skills/tree/main/standards/) — Commit standards

### External References

- **Documentation Site:** alirezarezvani.github.io/claude-skills (MkDocs Material site, v2.1.1)
- **Author Website:** <https://alirezarezvani.com>
- **Related Project:** [Claude Code Skills & Agents Factory](https://github.com/alirezarezvani/claude-code-skills-agents-factory) (methodology for building skills at scale)
- **Companion Project:** [Claude Code Tresor](https://github.com/alirezarezvani/claude-code-tresor) (60+ prompt templates)

---

## Summary

The **Claude Code Skills Library by Alireza Rezvani** is a mature, production-grade open-source project that delivers **170 modular, reusable skill packages** across engineering, product, marketing, compliance, and executive domains. It demonstrates a sophisticated approach to organizing large-scale AI expertise: self-contained skill packages, standardized SKILL.md format, dependency-free Python tools, and marketplace-ready distribution. The library is actively maintained (commits as recent as 2026-03-10), quality-optimized (v2.1.1 Tessl enhancements), and widely adopted (2,500+ stars). It serves as both a practical resource for Claude Code users and a reference architecture for skill design patterns applicable to the claude_skills project.

---

## Integration Opportunities

Assessed 2026-03-10 by `@research-insight-extractor`. 6 proposals across 3 priority levels.

### P1 — High Priority

1. **Skill Security Scanning** — Their `skill_security_auditor.py` scans 6 vulnerability categories (command injection, code execution, data exfiltration, prompt injection, supply chain risks, privilege escalation) with PASS/WARN/FAIL verdicts. Our `plugin_validator.py` validates structure but has no security-specific scanning. Action: extend plugin validator or create dedicated security scanner.

2. **Multi-Platform Skill Distribution** — They package 18 plugin bundles distributable across 4 platforms (Claude Code, Codex, Gemini CLI, OpenClaw) via marketplace.json. Our distribution is Claude-Code-only. Action: evaluate cross-platform packaging standards.

### P2 — Medium Priority

3. **Quality Scoring System** — They use `tessl skill review --optimize` to score skills 0-100% and systematically improve them (18 skills upgraded from 66-83% to 85-100%). Our `/audit-skill-completeness` evaluates 8 categories but doesn't produce a single aggregate score. Action: add aggregate scoring to existing audit-skill-completeness skill.

4. **Zero-Dependency Python Tool Pattern** — All 210+ of their scripts use stdlib only. Our scripts use typer, ruamel.yaml, rich, etc. Action: evaluate for portability-critical scripts only (design philosophy difference — their portability vs. our feature richness).

### P3 — Low Priority

5. **Domain-Scoped CLAUDE.md Files** — They use per-domain CLAUDE.md files for navigation within large skill collections. We use a single root CLAUDE.md. Action: reference pattern if adding non-engineering domains.

6. **Self-Improving Agent Pattern** — Their 5+2 sub-skill "self-improving agent" with auto-memory curation is a pattern our kaizen/self-improvement workflows could reference. Action: compare with existing kaizen process.

---

**Entry Created:** 2026-03-10
**Research Agent:** Research Curator Agent
**Session Reference:** <https://claude.ai/code/session_013vLUvHbxt8PPK38qcNsYQx>
