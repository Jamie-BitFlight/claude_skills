---
title: Codebase Recon Skill
subtitle: Git history analysis for pre-read codebase understanding across seven dimensions
category: skill-generation-tools
resource_url: https://github.com/yujiachen-y/codebase-recon-skill
github_url: https://github.com/yujiachen-y/codebase-recon-skill
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# Codebase Recon Skill

## Overview

Codebase Recon is a multi-agent compatible skill that analyzes git history to understand a codebase before reading any code. It reveals project health, risk areas, team structure, and development momentum through structured analysis of seven codebase dimensions. The skill is designed for developers onboarding to new projects, technical leads auditing codebases, and consultants evaluating code repositories.

**Problem Addressed**: When entering an unfamiliar codebase, developers typically dive directly into reading code without understanding project patterns, risk areas, or team dynamics. This skill provides structured reconnaissance before code review, enabling more targeted and informed analysis.

**Key Innovation**: Unlike ad-hoc manual git commands, this skill auto-scales analysis parameters based on repository size (small: <500 commits, medium: 500–10k commits, large: >10k commits) and cross-references hotspots with bug magnets to identify high-risk files that warrant immediate attention.

## Key Statistics

| Metric | Value |
|--------|-------|
| Version | 1.0.0 (as of 2026-04-26) |
| License | MIT |
| Repository | <https://github.com/yujiachen-y/codebase-recon-skill> |
| Author | Jiachen Yu (@yujiachen-y) |
| First Commit | 2026-04-26 |
| Total Commits | 1 (initial release) |
| Contributors | 1 (Jiachen Yu) |
| Multi-Agent Support | Yes — supports 20+ agents via Agent Skills Specification |

## Key Features

### 1. Auto-Scaling Analysis

The skill runs a **Probe phase** to determine repository size and calibrates analysis parameters:

```
Small repos (<500 commits):  analyze entire history, return 10 results
Medium repos (500–10k):     analyze last 1 year, return 20 results
Large repos (>10k):         analyze last 6 months, return 30 results
```

SOURCE: Lines 33-40 of `skills/codebase-recon/SKILL.md` — calibration table mapping commit count ranges to time windows and result counts.

### 2. Seven-Dimension Parallel Analysis

The skill analyzes these dimensions independently and in parallel:

1. **Code Hotspots**: Most-changed files in the analysis window (`git log --name-only | sort | uniq -c`)
2. **Bus Factor**: All-time contributor ranking by commit count (`git shortlog -sn --no-merges`)
3. **Bug Magnets**: Files most associated with fix/bug/broken commits (`git log --grep="fix|bug|broken"`)
4. **Team Momentum**: Commit frequency by month across all time (`git log --format='%Y-%m'`)
5. **Firefighting Frequency**: Emergency/revert/hotfix/rollback commits in the window
6. **Recently Added Files**: New files created in the analysis window (`--diff-filter=A`)
7. **Active Contributors**: Count of contributors in the last 3 months vs. total contributors

SOURCE: Lines 52-106 of `skills/codebase-recon/SKILL.md` — 7 analysis dimensions with exact git commands for each.

### 3. Cross-Referencing and Risk Identification

After collecting all analysis results, the skill performs intelligent cross-references:

- **High-Risk Files**: Intersects code hotspots with bug magnets to identify files that are both frequently changed AND bug-prone
- **Risk Ownership**: For each high-risk file, runs `git shortlog -sn -- <file>` to identify the primary owner
- **Bus Factor Risk**: Flags knowledge concentration if active contributors are less than 30% of total contributors
- **Momentum Trend**: Compares last 3 months vs. prior 3 months to classify trend as rising, declining, stable, or erratic

SOURCE: Lines 110-122 of `skills/codebase-recon/SKILL.md` — cross-referencing logic and trend analysis methods.

### 4. Structured Terminal Report

The skill outputs findings in a consistent format:

```
═══ Codebase Recon Report ═══

Repo Vitals: Age | Commits | Branches | Analysis window
1. Code Hotspots (ranked list)
2. Bug Magnets (ranked list)
3. High-Risk Files (intersection of 1 and 2, with ownership)
4. Bus Factor (contributor ranking + active ratio)
5. Team Momentum (monthly frequency + trend)
6. Firefighting Frequency (revert/hotfix rate)
7. Recently Added Files (ranked list)
8. Recommendations (start reading, talk to, watch out)
```

SOURCE: Lines 124-164 of `skills/codebase-recon/SKILL.md` — report template with all 8 sections.

### 5. Post-Report Markdown Export

After displaying the terminal report, the skill offers to save findings to a markdown file (e.g., `docs/codebase-recon-report.md`) for persistent documentation. No automatic commit — user decides whether to version the report.

SOURCE: Lines 166-170 of `skills/codebase-recon/SKILL.md` — post-report interaction flow.

## Technical Architecture

### Execution Model: Two-Phase Design

**Phase 1 — Probe** (Single Command):
Gathers repository vitals in one call:
- Total commit count (`git rev-list --count HEAD`)
- First and latest commit dates
- Branch count (`git branch -a | wc -l`)

**Phase 2 — Parallel Analysis** (7 Independent Commands):
All commands are independent and can execute in parallel. Each command uses parameters calibrated from Phase 1.

SOURCE: Lines 21-47 of `skills/codebase-recon/SKILL.md` — two-phase design with probe command and parallel analysis structure.

### Multi-Ecosystem Compatibility

The skill follows the [Agent Skills Specification](https://agentskills.io/specification) and is packaged for three distributions:

1. **Claude Code Plugin System**: Installable via `/plugin marketplace` or manual `skills add`
2. **skills.sh Registry**: Available via `npx skills add yujiachen-y/codebase-recon-skill` — makes it discoverable to 20+ coding agents (Cline, Cursor, GitHub Copilot, Gemini CLI, etc.)
3. **Codex Plugin System**: Installable via `codex plugin marketplace add yujiachen-y/codebase-recon-skill`

The SKILL.md uses **generic instruction language** (not Claude-specific tool names) to ensure any agent can interpret and execute it via its own tool set.

SOURCE: Lines 9-17 of `docs/specs/2026-04-09-codebase-recon-design.md` — multi-ecosystem distribution and Agent Skills Spec compliance.

### Skill Invocation

Activated via `/codebase-recon` slash command in any supported agent. Requires only `git` and a git repository with commit history.

SOURCE: README.md lines 33-40 — usage instructions and slash command syntax.

### Repository Structure

```
codebase-recon-skill/
├── .claude-plugin/
│   ├── plugin.json           # Claude Code plugin metadata
│   └── marketplace.json      # Self-hosted marketplace config
├── .codex-plugin/
│   └── plugin.json           # Codex plugin metadata
├── skills/
│   └── codebase-recon/
│       └── SKILL.md          # Main skill implementation
├── docs/
│   ├── specs/
│   │   └── 2026-04-09-codebase-recon-design.md
│   └── plans/
│       └── 2026-04-09-codebase-recon-plan.md
├── README.md
└── LICENSE
```

SOURCE: Lines 133-148 of `docs/specs/2026-04-09-codebase-recon-design.md` — repository structure.

## Installation & Usage

### Install via Claude Code

```bash
/plugin marketplace add yujiachen-y/codebase-recon-skill
```

Then invoke:

```bash
/codebase-recon
```

### Install via skills.sh (Multi-Agent)

```bash
npx skills add yujiachen-y/codebase-recon-skill
```

### Install via Codex Plugin System

```bash
codex plugin marketplace add yujiachen-y/codebase-recon-skill
```

SOURCE: README.md lines 7-31 — installation instructions for all three distribution channels.

### Usage Flow

1. Navigate to the repository to analyze
2. Invoke `/codebase-recon`
3. Skill probes the repository to determine size
4. Skill runs 7 parallel analysis commands
5. Skill generates and displays terminal report with 8 sections
6. Skill offers to save report to markdown file

SOURCE: README.md lines 33-45 — step-by-step usage flow.

## Relevance to Claude Code Development

This skill is relevant to the claude_skills repository in these ways:

1. **Cross-Agent Skill Distribution**: Demonstrates how a skill can be packaged and distributed across multiple coding agent platforms using the Agent Skills Specification — a pattern applicable to other reusable skills in claude_skills.

2. **Onboarding Tool**: When developers join the claude_skills project or work with large codebases, this skill enables rapid understanding of project structure, risk areas, and team dynamics without reading all code first.

3. **Codebase Intelligence Before Code Review**: Provides structured input for code review agents, architects, and analyzers by identifying hotspots and high-risk files beforehand.

4. **Reference Implementation for Skills**: The skill's SKILL.md, design document, and implementation plan serve as a reference for creating similar cross-agent skills in claude_skills.

5. **Git-Based Analysis Pattern**: Introduces a pattern of using git history as a primary source for codebase intelligence — applicable to other skills that need to understand project health or team dynamics.

## Limitations and Caveats

### Documented Limitations

The skill has no explicit limitations section in its documentation. However, several implicit limitations are evident from the design:

1. **Requires Git Repository**: Only works on codebases with git history. No support for other VCS or codebases without version control.

2. **Grep-Based Bug Detection**: Bug magnets are identified by regex patterns (`fix|bug|broken` in commit messages). False positives/negatives depend on team commit message conventions. Not all bug-fix commits will mention these keywords.

3. **Author Name Ambiguity**: `git shortlog` shows author names as they appear in commits. If a contributor uses multiple email addresses or name formats, they may be counted as multiple contributors.

4. **Analysis Window Calibration**: The commit-count thresholds (500, 10k) are fixed and may not suit all workflows. High-traffic branches or multiple remotes may skew commit counts.

5. **No File Content Analysis**: The skill analyzes only git metadata (file changes, commit messages, dates). It does not analyze code content, complexity, test coverage, or dependencies.

6. **Terminal Rendering Assumption**: Report is designed for terminal output. No structured JSON or programmatic API for consuming results downstream.

7. **Single Active-Contributor Window**: The 3-month window for "active contributors" is fixed regardless of repo size, which may not accurately reflect "currently active" in high-velocity projects with seasonal variations.

SOURCE: Absence of documented limitations in README.md and SKILL.md files. Above limitations are inferred from design constraints.

## References

- **Official Repository**: <https://github.com/yujiachen-y/codebase-recon-skill> (accessed 2026-05-10)
- **Inspiration Article**: "The Git Commands I Run Before Reading Any Code" by Ally Piechowski, <https://piechowski.io/post/git-commands-before-reading-code/> (referenced in docs, accessed 2026-05-10)
- **Agent Skills Specification**: <https://agentskills.io/specification> (referenced in design doc, standard for cross-agent skills)
- **License**: MIT License (full text in repository LICENSE file, accessed 2026-05-10)

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|-----------|---------------|-------------|
| Identity & Metadata | high | 2026-05-10 | 2026-08-10 |
| Features & Analysis | high | 2026-05-10 | 2026-08-10 |
| Technical Architecture | high | 2026-05-10 | 2026-08-10 |
| Installation & Usage | high | 2026-05-10 | 2026-08-10 |
| Limitations | medium | 2026-05-10 | 2026-08-10 |

**Confidence Summary**:
- **high**: All features, architecture, and installation steps verified against source files (plugin.json, SKILL.md, design spec, README.md)
- **medium**: Limitations inferred from design constraints rather than explicitly documented

**Staleness Risk**: Version 1.0.0 is very recent (2026-04-26). Next review recommended in 3 months to check for bug fixes, new features, or calibration adjustments to the Phase 1 thresholds.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [GitNexus](../mcp-ecosystem/gitnexus.md) | mcp-ecosystem | graph-based code intelligence MCP server with repository queries and impact analysis; complements Codebase Recon's git-history findings with live code graph navigation |
| [CodeGraphContext](../mcp-ecosystem/codegraphcontext.md) | mcp-ecosystem | repository-to-graph tool with Tree-Sitter AST parsing and caller/callee analysis; extends Codebase Recon's hotspot identification with code-level dependencies and dead code detection |
| [grepai](../developer-tools/grepai.md) | developer-tools | semantic code search and call graph analysis for AI agents; provides deep code-level intelligence to interpret the developers identified by Codebase Recon's bus factor analysis |
| [graphify](./graphify.md) | skill-generation-tools | AST+LLM extraction pipeline for code structure visualization; transforms Codebase Recon's metadata findings into navigable code architecture diagrams and knowledge graphs |
| [agent-skills](./agent-skills.md) | skill-generation-tools | production-grade skills library by Addy Osmani with structured workflows; demonstrates canonical skill packaging pattern (Agent Skills Spec) that Codebase Recon follows for multi-agent distribution |
| [everything-claude-code](./everything-claude-code.md) | skill-generation-tools | comprehensive agent harness with 65+ skills including codebase analysis workflows; shows how Codebase Recon insights integrate into larger multi-agent orchestration systems |
| [Kythe](../developer-tools/kythe.md) | developer-tools | Google's language-agnostic code intelligence platform; alternative to git-based analysis offering static semantic indexing of hotspots, contributors, and risk areas |
