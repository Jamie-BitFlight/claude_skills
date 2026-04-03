# Claude Skills Library — 205 Production-Ready AI Agent Skills & Plugins

## Identity and Metadata

**Official Name:** Claude Code Skills & Plugins (alirezarezvani/claude-skills)
**Repository:** <https://github.com/alirezarezvani/claude-skills>
**Latest Version:** 2.1.2 (released March 10, 2026)
**License:** MIT (source: LICENSE file)
**GitHub Statistics:** 7,452 stars, 900 forks (as of March 28, 2026)
**Author:** Alireza Rezvani (<https://alirezarezvani.com>)
**Created:** October 19, 2025
**Last Updated:** March 28, 2026

---

## Problem Addressed

AI coding agents (Claude Code, Codex, Cursor, Aider, Windsurf) ship with general-purpose capabilities but lack domain-specific expertise that engineering teams, product managers, marketers, and executives need to execute specialized work. Each skill in this repository addresses a specific problem: "How does an AI agent guide me through [architectural decision / compliance audit / content strategy / security review]?"

**Specific gaps filled:**
1. Architectural decision frameworks for scaling systems (source: `engineering/agent-designer/SKILL.md`)
2. Regulatory compliance templates (MDR 2017/745, FDA, ISO 27001, GDPR) (source: `ra-qm-team/` folder)
3. Production-grade testing and debugging for flaky tests (source: `engineering-team/playwright-pro/`)
4. Marketing strategy and content creation at scale (source: `marketing-skill/` with 43 skills)
5. Executive decision-making frameworks for C-suite roles (source: `c-level-advisor/` with 28 skills)

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Total Skills** | 205 | README.md line 3 |
| **Python Tools** | 268 | README.md line 26; line 299 states "254 CLI tools" (discrepancy noted; primary source is line 26 "268") |
| **Reference Documents** | 384 | README.md line 26 |
| **Agents** | 16 | README.md badge on line 11 |
| **Slash Commands** | 19 | README.md badge on line 13 |
| **Skill Domains** | 9 | README.md line 148 |
| **CLI Tools Verified** | 237/237 passing `--help` | CHANGELOG.md v2.1.2 section |
| **GitHub Stars** | 7,452 | GitHub API (accessed 2026-03-28) |
| **GitHub Forks** | 900 | GitHub API (accessed 2026-03-28) |

**Skill Distribution by Domain** (source: README.md, lines 150-163):

| Domain | Count | Highlights |
|--------|-------|-----------|
| Engineering — Core | 26 | Architecture, frontend, backend, fullstack, QA, DevOps, Playwright Pro (9+3), Self-Improving Agent (5+2) |
| Engineering — POWERFUL | 30 | Agent designer, RAG architect, database designer, CI/CD builder, MCP server builder |
| Product | 14 | Product manager, agile PO, strategist, UX researcher, UI design, landing pages, SaaS scaffolder |
| Marketing | 43 | 7 pods: Content (8), SEO (5), CRO (6), Channels (6), Growth (4), Intelligence (4), Sales (2) |
| Project Management | 6 | Senior PM, scrum master, Jira, Confluence, Atlassian admin |
| Regulatory & QM | 12 | ISO 13485, MDR, FDA, ISO 27001, GDPR, CAPA, risk management |
| C-Level Advisory | 28 | 10 C-suite roles + orchestration + board meetings + strategic capabilities |
| Business & Growth | 4 | Customer success, sales engineer, revenue ops, contracts |
| Finance | 2 | Financial analyst (DCF, budgeting), SaaS metrics coach |

---

## Key Features

### 1. Multi-Platform Skill Format

**Feature:** One repository, eleven AI coding tools. Skills convert natively to multiple platforms via `scripts/convert.sh`.

**Mechanism:** Each skill is self-contained as a folder with `SKILL.md` (instructions), `scripts/` (Python tools), `references/` (knowledge bases), and `assets/` (templates). A conversion script reads this format and outputs platform-specific versions:

- Claude Code: native plugin format (`.claude-plugin/marketplace.json` registry)
- Codex: agent skill format
- Gemini CLI: skill index format (`.gemini/skills-index.json`)
- Cursor: `.mdc` rules format
- Aider: `CONVENTIONS.md` format
- Kilo Code: `.kilocode/rules/` directory format
- Windsurf, OpenCode, Augment, Antigravity: native format conversions

**Example from README:** "Convert all 156 skills to all tools (takes ~15 seconds)" via `./scripts/convert.sh --tool all` (line 124).

**Confidence:** High. Conversion system documented in README.md lines 105-142 and verified by multiple tool-specific setup scripts (`gemini-install.sh`, `codex-install.sh`, `openclaw-install.sh`).

### 2. Zero-Dependency Python Tools

**Feature:** All 268 Python CLI scripts use standard library only — no pip installs required.

**Mechanism:** Every tool is designed as a standalone CLI accepting arguments, producing JSON or human-readable output. Tools are verified to run with `--help` without errors.

**Examples from README (lines 300-319):**
- `finance/saas-metrics-coach/scripts/metrics_calculator.py --mrr 80000 --customers 200 --churned 3 --json`
- `marketing-skill/content-production/scripts/brand_voice_analyzer.py article.txt`
- `c-level-advisor/cto-advisor/scripts/tech_debt_analyzer.py /path/to/codebase`
- `product-team/product-manager-toolkit/scripts/rice_prioritizer.py features.csv`

**Verification:** CHANGELOG.md v2.1.2 states "237 Python scripts verified — All pass `--help` without errors (previous session fixed 25 scripts across all domains)".

**Confidence:** High. Explicit verification statement in official changelog.

### 3. Skill Security Auditor (POWERFUL Tier)

**Feature:** Audit any skill for security risks before installation. Scans for malicious code, prompt injection, data exfiltration, and supply chain risks. Returns PASS/WARN/FAIL verdict.

**Mechanism:** `python3 engineering/skill-security-auditor/scripts/skill_security_auditor.py /path/to/skill/` runs a static analyzer on the skill directory without executing code.

**Scanning Targets:** Command injection, code execution, data exfiltration, prompt injection, dependency supply chain risks, privilege escalation.

**Zero Dependencies:** Works anywhere Python runs — a core design principle stated in README.md lines 252-257.

**Confidence:** High. Documented as "New in v2.0.0" in README, included in POWERFUL tier list (line 247).

### 4. Modular Skill Structure — Self-Contained Packages

**Feature:** Each skill is a folder with documentation, tools, and templates. Teams extract a skill and use it immediately without additional setup.

**Anatomy of a Skill** (source: SKILL-AUTHORING-STANDARD.md):
- `SKILL.md` — Master documentation with YAML frontmatter (name, description, license, metadata)
- `scripts/` — Python CLI tools for automation
- `references/` — Expert knowledge bases (templates, checklists, frameworks)
- `assets/` — User-facing templates

**Information Flow:** Knowledge from `references/` → Workflows in `SKILL.md` → Execution via `scripts/` → Applied using `assets/` templates (source: CLAUDE.md in worktree).

**Confidence:** High. Pattern documented in multiple locations (README, SKILL-AUTHORING-STANDARD.md, CLAUDE.md).

### 5. Persona-Based Agent Orchestration

**Feature:** Three pre-configured agent identities with curated skill loadouts, workflows, and distinct communication styles. Personas define how an agent thinks, prioritizes, and communicates — beyond just "use these skills."

**Personas** (source: README.md, lines 170-185):
1. **Startup CTO** — Engineering + Strategy; best for architecture decisions, tech stack selection, team building, technical due diligence
2. **Growth Marketer** — Marketing + Growth; best for content-led growth, launch strategy, channel optimization, bootstrapped marketing
3. **Solo Founder** — Cross-domain; best for one-person startups, side projects, MVP building

**Implementation:** Stored in `agents/personas/` as YAML-frontmatter-driven agent files. Custom personas can be created using `agents/personas/TEMPLATE.md`.

**Orchestration Pattern:** Lightweight protocol for coordinating personas, skills, and agents across domain boundaries without requiring a framework. Four patterns described in README (lines 192-209): Solo Sprint, Domain Deep-Dive, Multi-Agent Handoff, Skill Chain.

**Confidence:** High. Section explicitly titled "Personas" in README with usage examples and template reference.

### 6. Marketplace-Based Distribution

**Feature:** Skills published to ClawHub marketplace and Claude Code plugin marketplace. Plugin registry in `.claude-plugin/marketplace.json` coordinates distribution across multiple tools.

**Registry Format** (source: `.claude-plugin/marketplace.json` excerpt):
```json
{
  "name": "claude-code-skills",
  "metadata": {
    "description": "205 production-ready skill packages...",
    "version": "2.1.2"
  },
  "plugins": [
    {
      "name": "marketing-skills",
      "source": "./marketing-skill",
      "description": "43 marketing skills across 7 pods..."
    },
    ...
  ]
}
```

**Installation Examples from README (lines 62-81):**
- Claude Code: `/plugin marketplace add alirezarezvani/claude-skills` then `/plugin install engineering-skills@claude-code-skills`
- Manual: `git clone + ./scripts/install.sh --tool <name>`

**Confidence:** High. Registry file directly examined; installation commands documented in README.

### 7. Quality Standards and Production Pipeline

**Feature:** SKILL_PIPELINE.md defines a mandatory 9-phase production pipeline for all skill work. SKILL-AUTHORING-STANDARD.md enforces consistent frontmatter, naming, and structure.

**Pipeline Phases** (source: SKILL_PIPELINE.md, referenced in CHANGELOG.md v2.1.1):
1. Discovery (user research, market scan)
2. Design (information architecture, workflows)
3. Development (SKILL.md writing, Python tools)
4. Testing (execution on sample inputs, edge cases)
5. Documentation (API docs, examples, troubleshooting)
6. Quality Gate (linting, security audit, clarity review)
7. Optimization (Tessl review for 85%+ quality score)
8. Publishing (marketplace prep, metadata validation)
9. Deprecation (sunset process for obsolete skills)

**Quality Results** (source: CHANGELOG.md v2.1.1, lines 17-35):
18 skills optimized from 66-83% to 85-100% via `tessl skill review --optimize`. Example: `project-management/confluence-expert` improved from 66% to 94%, `engineering-team/playwright-pro` reached 100%.

**Confidence:** High. Explicit pipeline documentation and published quality metrics.

---

## Technical Architecture

### Core Design Patterns

**1. Skill-as-Module Pattern**
Each skill is a self-contained module with zero external dependencies. Folders nest only one level deep under domain directories (`domain/skill-name/`). Subdirectory namespacing is explicitly forbidden — all skills sit directly under a domain folder (source: CLAUDE.md, "Subdirectory Namespaces — Skills Do NOT Support This").

**2. Knowledge Hierarchy**
Information flows from structured references → into SKILL.md workflows → implemented via scripts → applied using templates. Example from source (CLAUDE.md): "Knowledge flows from `references/` → into `SKILL.md` workflows → executed via `scripts/` → applied using `assets/` templates."

**3. Persona + Skill Orchestration**
Personas coordinate multiple skills across domain boundaries without a centralized framework. Four orchestration patterns (Solo Sprint, Domain Deep-Dive, Multi-Agent Handoff, Skill Chain) are documented in `orchestration/ORCHESTRATION.md` (referenced in README line 209).

**4. Platform Adapter Pattern**
A single skill format (folder with SKILL.md, scripts, references) converts to platform-native formats via `scripts/convert.sh`. Input: skill folder → Output: `.mdc` (Cursor), `CONVENTIONS.md` (Aider), `.kilocode/rules/` (Kilo Code), etc. (source: README lines 105-142).

### Named Components and Data Flow

**Entrypoints:**
- `README.md` — User entry point (installation, skill overview)
- `.claude-plugin/marketplace.json` — Plugin registry for Claude Code distribution
- `.gemini/skills-index.json` — Index for Gemini CLI (source: directory listing)
- `.codex/skills-index.json` — Index for Codex CLI
- `scripts/install.sh`, `scripts/convert.sh` — Tool conversion and installation orchestrators

**Core Components:**
- **SKILL.md** — Machine-readable skill definition with YAML frontmatter (name, description, license, metadata, version, author, category, updated date). Contains workflows, checklists, decision trees, and communication standards (source: SKILL-AUTHORING-STANDARD.md template, lines 1-150).
- **Python Scripts** (`scripts/` directories) — Standalone CLI tools. No LLM calls (by design), all stdlib. Each script accepts arguments and produces JSON or human-readable output.
- **References** (`references/` directories) — Knowledge bases: templates, checklists, frameworks, domain-specific guides. Examples: `references/data-collection-guide.md`, `references/analysis-templates.md` (source: CHANGELOG.md v2.1.2).
- **Assets** (`assets/` directories) — User-facing templates (DOCX, TSX, CSS, YAML) ready to customize. Example: Landing page generator outputs Next.js TSX + Tailwind CSS with 4 design styles (source: CHANGELOG.md v2.1.2).

**Data Flow in Feature Execution:**
1. User provides context (current state, goals, constraints)
2. SKILL.md workflow determines mode (Build from Scratch, Optimize Existing, situation-specific)
3. Mode-specific sections guide user through decision points
4. Python scripts automate analysis (e.g., `brand_voice_analyzer.py` analyzes content tone)
5. References provide knowledge scaffolds (frameworks, checklists)
6. Assets output ready-to-customize templates

**Example — Landing Page Generator Flow** (source: CHANGELOG.md v2.1.2, lines 14-21):
- Input: Landing page config (target audience, value prop)
- Step 1: User defines brand voice using content-production skill
- Step 2: `brand_voice_analyzer.py` extracts voice profile
- Step 3: `landing_page_scaffolder.py --format tsx` outputs Next.js/TSX with design style matching voice
- Output: TSX component + Tailwind CSS classes ready to customize

### Extension Points

**1. Skill Creation via SKILL-AUTHORING-STANDARD.md**
New skills follow the standard template (name, description, license metadata, mode-based workflows). No plugins or hook systems — each skill is a directory following naming conventions. Create skill folder, add SKILL.md + scripts + references, commit to repo, register in marketplace.json (source: SKILL-AUTHORING-STANDARD.md, README line 348).

**2. Persona Customization**
Users create custom personas by copying `agents/personas/TEMPLATE.md` and defining skill loadouts, workflows, and communication voice. Personas are YAML files that reference multiple skills via `dependencies` array (source: README lines 175-184).

**3. Python Tool Extension**
Contributors add Python scripts to any skill's `scripts/` directory. Convention: one script per major operation (e.g., `metrics_calculator.py`, `brand_voice_analyzer.py`). All stdlib only; zero pip installs. Scripts must pass `--help` verification (source: CHANGELOG.md v2.1.2: "237 Python scripts verified").

**4. Platform Adapter Extension**
`scripts/convert.sh --tool <toolname>` generates platform-specific outputs. Adding a new tool requires a conversion function in the script that reads the skill folder structure and outputs tool-native format (e.g., `.mdc` for Cursor). Source templates exist for each tool in tool-specific directories.

---

## Installation & Usage

### Quick Install — Claude Code

```bash
# Add marketplace
/plugin marketplace add alirezarezvani/claude-skills

# Install skill bundles by domain
/plugin install engineering-skills@claude-code-skills
/plugin install marketing-skills@claude-code-skills
/plugin install c-level-skills@claude-code-skills

# Or install individual skills
/plugin install skill-security-auditor@claude-code-skills
```

*Source: README.md lines 62-81*

### Manual Installation

```bash
# Clone repository
git clone https://github.com/alirezarezvani/claude-skills.git
cd claude-skills

# Copy skill folder to Claude Code skills directory
cp -r engineering-team/senior-architect ~/.claude/skills/
```

*Source: README.md line 100*

### Convert for Other Tools

```bash
# Convert all skills to all tools
./scripts/convert.sh --tool all

# Install for specific tool
./scripts/install.sh --tool cursor --target /path/to/project

# Verify installation
find .cursor/rules -name "*.mdc" | wc -l
```

*Source: README.md lines 123-134*

### Python Tool Usage Examples

```bash
# SaaS metrics analysis
python3 finance/saas-metrics-coach/scripts/metrics_calculator.py \
  --mrr 80000 --customers 200 --churned 3 --json

# Tech debt analysis
python3 c-level-advisor/cto-advisor/scripts/tech_debt_analyzer.py /path/to/codebase

# Security audit on a skill
python3 engineering/skill-security-auditor/scripts/skill_security_auditor.py /path/to/skill/
```

*Source: README.md lines 300-315*

### Using a Persona

```bash
# Copy persona to Claude Code
cp agents/personas/startup-cto.md ~/.claude/agents/

# Or convert to your tool
./scripts/convert.sh --tool cursor  # Converts personas too
```

*Source: README.md lines 179-183*

---

## Limitations and Caveats

**1. No Built-In Feedback Loop for Skills**
The library provides skill authoring guidelines (SKILL_PIPELINE.md, SKILL-AUTHORING-STANDARD.md) but no integrated system for collecting user feedback or rating individual skills. Quality relies on manual Tessl reviews (source: CHANGELOG.md v2.1.1) and contributor discipline (source: SKILL_PIPELINE.md phase 7 "Quality Gate").

**2. Python Tool Scope Limited to Deterministic Analysis**
All Python scripts use standard library only and perform no machine learning or LLM calls. This keeps tools fast and portable but limits their ability to perform semantic analysis. Tools focus on syntactic parsing, configuration analysis, and deterministic scoring (e.g., RICE scoring, tech debt calculation) (source: README.md line 26: "Python tools... all stdlib-only, zero pip installs"; CONTRIBUTING.md implied constraint: "No LLM calls in scripts").

**3. No Real-Time Synchronization Between Copies**
When users copy skills to their local `.claude/skills/` directory, subsequent repository updates are not automatically pulled into local copies. Users must manually re-pull the repository and copy updated skills. Repository recommends semantic versioning for backward compatibility (source: FAQ, line 341: "We follow semantic versioning and maintain backward compatibility within patch releases").

**4. Marketplace Slug Conflicts Require cs- Prefix**
When a skill slug is already taken on ClawHub, publication requires the `cs-` prefix (e.g., `cs-copywriting`). This applies only to ClawHub registry — repo folder names and local skill names remain unchanged. Complicates cross-platform discoverability (source: CLAUDE.md, "ClawHub Publishing Constraints").

**5. Skill Interdependencies Discouraged**
Anti-pattern explicitly stated: "Creating dependencies between skills (keep each self-contained)" (source: CLAUDE.md, "Anti-Patterns to Avoid"). This means skills cannot build directly on each other's outputs — orchestration must be manual via personas or skill chains. No dependency resolution system.

**6. No Test Framework for Skills**
Skills have no built-in testing (unit, integration, end-to-end). Quality assurance relies on manual code review, linting, and Tessl scoring (source: CLAUDE.md: "No build system or test frameworks — intentional design choice for portability"). Large or complex skills have no automated validation.

---

## Relevance to Claude Code Development

This repository is directly relevant to Claude Code development in four ways:

### 1. Skill Library Model — Extensibility Reference
The modular skill format (SKILL.md + scripts + references + assets) is a concrete realization of how Claude Code plugins can package domain expertise. The zero-dependency Python tool pattern is transferable to other AI coding tools and demonstrates that complex automation can be achieved without external dependencies. Relevant for: extending Claude Code's skill ecosystem, designing plugin distribution formats, understanding multi-platform skill portability constraints.

### 2. Production-Grade Quality Standards
SKILL_PIPELINE.md (9-phase pipeline) and SKILL-AUTHORING-STANDARD.md define production quality for AI agent skills. The 237-script verification and Tessl 85%+ optimization benchmarks demonstrate measurable quality standards for agent guidance content. Relevant for: setting quality expectations for contributed skills, designing validation workflows for plugin marketplaces, establishing authoring guidelines for agent instruction content.

### 3. Multi-Platform Skill Conversion Patterns
The conversion system (one skill format → 11 tool-native formats via `scripts/convert.sh`) solves the fragmentation problem of AI coding tools. Platform adapters exist for Claude Code, Codex, Cursor, Aider, Windsurf, and others. Relevant for: designing portable skill formats, understanding tool-specific distribution constraints (.mdc vs CONVENTIONS.md vs skill directories), reducing authoring overhead for multi-platform skill libraries.

### 4. Marketplace Distribution Infrastructure
`.claude-plugin/marketplace.json` registry coordinate skill publication across multiple distribution channels (Claude Code marketplace, ClawHub, individual tool indexes). Slug conflicts, version tracking, and metadata standardization are solved via YAML registry. Relevant for: designing plugin marketplace infrastructure, understanding plugin versioning and deprecation, coordinating multi-platform skill releases.

---

## References

**Official Sources:**

1. GitHub Repository
   - URL: <https://github.com/alirezarezvani/claude-skills>
   - Latest Commit: 110348f (Merge PR #429, March 28, 2026)
   - Accessed: 2026-03-28

2. README.md
   - 377 lines, comprehensive overview of all 9 domains
   - Covers installation, features, usage examples, FAQ
   - Accessed: 2026-03-28

3. CHANGELOG.md
   - Version history from v2.0.0 (2026-02-16) through v2.1.2 (2026-03-10)
   - Tracks skill additions, Python tool fixes, quality improvements
   - Latest section: v2.1.2 quality and cross-domain integration updates
   - Accessed: 2026-03-28

4. SKILL-AUTHORING-STANDARD.md
   - Defines SKILL.md template, YAML frontmatter, folder structure
   - Accessed: 2026-03-28

5. SKILL_PIPELINE.md
   - 9-phase production pipeline referenced in CHANGELOG.md v2.1.1
   - Accessed: 2026-03-28

6. CLAUDE.md (in repository)
   - Project-specific instructions for development
   - Describes repository purpose, navigation map, git workflow
   - Version: v2.1.2, Last Updated: March 11, 2026
   - Accessed: 2026-03-28

7. LICENSE
   - MIT License, Copyright (c) 2025 Alireza Rezvani
   - Accessed: 2026-03-28

8. .claude-plugin/marketplace.json
   - Plugin registry with 28+ plugins and metadata
   - Accessed: 2026-03-28

9. GitHub API Data
   - Star count: 7,452
   - Fork count: 900
   - Created: 2025-10-19T04:04:05Z
   - Updated: 2026-03-28T01:42:27Z
   - Accessed: 2026-03-28 via GitHub API

**Related Projects:**

10. Claude Code Skills & Agents Factory
    - URL: <https://github.com/alirezarezvani/claude-code-skills-agents-factory>
    - Referenced in README.md line 327
    - Purpose: Methodology for building skills at scale

11. Claude Code Tresor
    - URL: <https://github.com/alirezarezvani/claude-code-tresor>
    - Referenced in README.md line 328
    - Scope: Productivity toolkit with 60+ prompt templates

12. Product Manager Skills
    - URL: <https://github.com/Digidai/product-manager-skills>
    - Referenced in README.md line 329
    - Scope: Senior PM agent with 6 knowledge domains, 30+ frameworks

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Everything Claude Code](./everything-claude-code.md) | skill-generation-tools | Parallel harness system: 65+ skills, 16 agents, production quality gates and marketplace distribution approach |
| [SkillKit](./skillkit.md) | skill-generation-tools | Cross-platform skill translator: handles 32-agent format conversion like this library's script/convert.sh approach |
| [Anthropic Agent Skills](./anthropics-skills.md) | skill-generation-tools | Official SKILL.md specification reference and 17-skill collection matching this library's format and quality standards |
| [ClawHub](./clawhub.md) | skill-generation-tools | Public marketplace registry solving the skill discovery and versioning problem this library addresses |
| [Claude Code Templates](./claude-code-templates.md) | skill-generation-tools | 100+ ready-to-use components distribution model shares marketplace and CLI install pattern |
| [Skill Seekers](./skill-seekers.md) | skill-generation-tools | Documentation-to-skill automation complementing this library's manual authoring approach |
| [mcpskills-cli](./mcpskills-cli.md) | skill-generation-tools | MCP-to-skill conversion pattern extending this library's Python tool generation methodology to protocol tools |
| [HumanCompiler](./human-compiler.md) | skill-generation-tools | Interview-driven plugin generation from behavioral profiles parallels skill authoring as knowledge codification |

---

## Freshness Tracking

**Content Last Verified:** March 28, 2026
**Next Review Recommended:** June 28, 2026 (3 months)

### Confidence by Section

| Section | Confidence | Basis |
|---------|-----------|-------|
| **Identity/Metadata** | high | Official README, GitHub API, CHANGELOG, license file read directly |
| **Problem Addressed** | high | README.md Problem Addressed section (lines 2-7); specific gaps documented with folder references |
| **Key Statistics** | high | README.md line counts; CHANGELOG.md v2.1.2 script verification statement; GitHub API for stars/forks |
| **Key Features** | high | README.md feature descriptions lines 105-257; CHANGELOG.md feature additions; marketplace.json registry examined |
| **Technical Architecture** | high | CLAUDE.md, SKILL-AUTHORING-STANDARD.md, SKILL_PIPELINE.md read directly; component names verified in folder structure |
| **Installation & Usage** | high | README.md installation sections (lines 44-102) and examples (lines 275-319); scripts examined |
| **Limitations** | medium | Inferred from documentation (CLAUDE.md anti-patterns, SKILL_PIPELINE.md phases, CONTRIBUTING.md absence of test framework). No explicit "Limitations" section in README. Confidence reduced because limitations are implied rather than explicitly stated. |
| **Relevance to Claude Code** | high | Direct architectural and quality standard relevance; multi-platform portability and marketplace patterns documented |

**Changes Since Last Review:** This is the initial research entry.

**Known Data Gaps:**
- Individual skill quality scores (only aggregate metrics from Tessl review available)
- User adoption metrics beyond star/fork counts
- Failure modes or support issues (no issues.md or known issues documented)
- Detailed performance benchmarks for Python tools
