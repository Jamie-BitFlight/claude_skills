# Anthropic Agent Skills Repository

**Research Date**: 2026-03-06
**Source URL**: <https://github.com/anthropics/skills>
**GitHub Repository**: <https://github.com/anthropics/skills>
**Version at Research**: 1.0.0 (marketplace metadata version; no tagged releases)
**License**: Apache 2.0 (example skills); source-available only (document skills: docx, pdf, pptx, xlsx)

---

## Overview

The official Anthropic repository of Agent Skills for Claude — a curated collection of production and demonstration skills spanning creative design, developer tooling, document processing, and enterprise workflows. Each skill is a self-contained directory with a `SKILL.md` file that Claude loads dynamically to specialize its behavior on a defined task. The repository also hosts the Agent Skills specification reference and a skill template for authors building their own skills.

SOURCE: [anthropics/skills README](https://github.com/anthropics/skills/blob/main/README.md) (accessed 2026-03-06)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Claude has no built-in specialization for domain-specific workflows | Skills teach Claude repeatable task patterns loaded on demand |
| Authors lack authoritative examples of well-structured skills | 17 skills across diverse domains serve as copy-paste-ready references |
| Document creation capabilities (Word, PDF, Excel, PowerPoint) are opaque | Four production document skills published source-available for inspection |
| Developers building Claude integrations lack a bootstrapping tool | `skill-creator` skill guides Claude through interviewing, writing, testing, and optimizing new skills |
| MCP server creation has no guided workflow | `mcp-builder` skill provides a 4-phase research-to-evaluation workflow for building MCP servers |
| Web app testing via Playwright requires complex setup | `webapp-testing` skill encapsulates Playwright reconnaisance-then-action patterns |

SOURCE: [anthropics/skills README](https://github.com/anthropics/skills/blob/main/README.md) (accessed 2026-03-06)

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 84,951 | 2026-03-06 |
| GitHub Forks | 8,951 | 2026-03-06 |
| Open Issues | 391 | 2026-03-06 |
| Contributors | 30 (API page 1 result) | 2026-03-06 |
| Latest Release | No tagged releases | 2026-03-06 |
| Marketplace Version | 1.0.0 | 2026-03-06 |
| Repository Created | 2025-09-22 | 2026-03-06 |
| Last Push | 2026-03-04 | 2026-03-06 |
| Primary Language | Python | 2026-03-06 |

SOURCE: `gh api repos/anthropics/skills` (accessed 2026-03-06)

---

## Key Features

### Skill Catalog — 17 Skills in Two Installable Plugins

**document-skills plugin** (source-available, powers Claude.ai document features):

- `docx` — Word document creation and editing
- `pdf` — PDF extraction and form field interaction
- `pptx` — PowerPoint presentation generation
- `xlsx` — Excel spreadsheet creation and data manipulation

**example-skills plugin** (Apache 2.0):

- `skill-creator` — full lifecycle skill authoring: intent capture, interview, write, test with A/B evaluation harness, optimize description for triggering accuracy
- `mcp-builder` — 4-phase guided workflow (research → implement → test → evaluate) for building MCP servers in Python (FastMCP) or TypeScript (MCP SDK)
- `webapp-testing` — Playwright-based web app interaction and testing using reconnaisance-then-action pattern with `with_server.py` helper
- `frontend-design` — production-grade frontend UI generation emphasizing distinctive typography and non-generic aesthetics
- `algorithmic-art` — p5.js generative art using seeded randomness, flow fields, and particle systems; outputs `.md` (philosophy), `.html`, and `.js` files
- `canvas-design` — design-focused canvas output
- `brand-guidelines` — brand identity and style guide creation
- `doc-coauthoring` — collaborative document co-authoring workflows
- `internal-comms` — enterprise internal communications drafting
- `slack-gif-creator` — animated GIF generation for Slack
- `theme-factory` — theme and style system generation
- `web-artifacts-builder` — web artifact (interactive HTML) construction
- `claude-api` — Claude API and Anthropic SDK usage guidance; triggers on `import anthropic` / `@anthropic-ai/sdk`

**claude-api plugin** (separate third plugin entry):

- Provides SDK documentation and patterns for building LLM-powered applications with language detection

SOURCE: [.claude-plugin/marketplace.json](https://github.com/anthropics/skills/blob/main/.claude-plugin/marketplace.json) (accessed 2026-03-06); [skills/ directory listing](https://github.com/anthropics/skills/tree/main/skills) (accessed 2026-03-06)

### Skill File Format

Every skill requires exactly one `SKILL.md` with YAML frontmatter:

```yaml
name: skill-name          # lowercase, hyphens for spaces; unique identifier
description: ...          # primary trigger mechanism — drives whether Claude invokes the skill
license: ...              # license reference
```

Supported optional directories alongside `SKILL.md`:

- `scripts/` — executable code for deterministic or repetitive tasks
- `references/` — documentation loaded into context on demand
- `assets/` — files used in output (templates, icons, fonts)
- `agents/` — sub-agent definitions (used by skill-creator)
- `eval-viewer/` — evaluation result viewer (used by skill-creator)

SOURCE: [skill-creator SKILL.md anatomy section](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) (accessed 2026-03-06)

### Marketplace / Plugin Distribution

The repository exposes a Claude Code Plugin marketplace via `.claude-plugin/marketplace.json`. Three plugins are defined:

- `document-skills` — the four document processing skills
- `example-skills` — the eleven example and developer skills
- `claude-api` — the Claude API documentation skill

Skills within a plugin are listed as paths. The `strict: false` field allows partial skill matching.

SOURCE: [.claude-plugin/marketplace.json](https://github.com/anthropics/skills/blob/main/.claude-plugin/marketplace.json) (accessed 2026-03-06)

### Description-Driven Triggering

The `description` field in SKILL.md frontmatter is the primary mechanism controlling skill invocation. The `skill-creator` skill includes a full description optimization loop: generate trigger evaluation queries, score candidate descriptions, apply the best-scoring description, and present before/after scores. The `claude-api` skill demonstrates explicit trigger/no-trigger conditions in its description field.

SOURCE: [skill-creator SKILL.md description optimization section](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) (accessed 2026-03-06)

### Evaluation Harness (skill-creator)

The `skill-creator` skill includes a structured A/B evaluation workflow:

1. Spawn parallel runs: `with-skill` and `without-skill` (baseline) in the same turn
2. Draft assertions while runs are in progress
3. Capture timing data as runs complete
4. Grade results, aggregate scores, launch a local eval viewer
5. Read feedback from the viewer, iterate on the skill

SOURCE: [skill-creator SKILL.md evaluation section](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) (accessed 2026-03-06)

---

## Technical Architecture

```text
anthropics/skills/
├── .claude-plugin/
│   └── marketplace.json       # Plugin registry: 3 plugins, 17 skills
├── skills/                    # Individual skill directories
│   ├── {skill-name}/
│   │   ├── SKILL.md           # Required: frontmatter + instructions
│   │   ├── LICENSE.txt        # Per-skill license
│   │   ├── scripts/           # Executable helpers (optional)
│   │   ├── references/        # Context documents (optional)
│   │   ├── assets/            # Output templates (optional)
│   │   └── agents/            # Sub-agent definitions (optional)
├── spec/
│   └── agent-skills-spec.md   # Redirects to agentskills.io/specification
└── template/
    └── SKILL.md               # Minimal starter template
```

**Skill loading**: Claude loads `SKILL.md` content dynamically when the description matches user intent. Reference files in `references/` are loaded on demand; scripts in `scripts/` are executed by Claude when the skill instructs it to do so.

**Agent Skills standard**: The canonical specification has moved to [agentskills.io/specification](https://agentskills.io/specification). This repository is Anthropic's reference implementation, not the specification host.

SOURCE: [spec/agent-skills-spec.md](https://github.com/anthropics/skills/blob/main/spec/agent-skills-spec.md) (accessed 2026-03-06); repository structure inspection via GitHub API (accessed 2026-03-06)

---

## Installation & Usage

**Claude Code — install via marketplace:**

```bash
# Register the Anthropic marketplace
/plugin marketplace add anthropics/skills

# Then browse and install interactively, or install directly:
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```

**Claude.ai**: Upload the skill folder directly through the Claude.ai interface.

**Claude API**: Pass `SKILL.md` content in the system prompt or as a tool definition when calling the Anthropic API directly.

**Creating a new skill from the template:**

```yaml
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Instructions Claude will follow when this skill is active]

## Examples
- Example usage 1

## Guidelines
- Guideline 1
```

**Using skill-creator to build a new skill:**

1. Activate skill-creator
2. Describe the capability you want to encode
3. Claude conducts an interview to capture intent and edge cases
4. Claude writes the SKILL.md and runs A/B evaluations
5. Claude optimizes the description for triggering accuracy

SOURCE: [anthropics/skills README](https://github.com/anthropics/skills/blob/main/README.md) (accessed 2026-03-06)

---

## Relevance to Claude Code Development

### Applications

- This repository is the canonical reference for how Anthropic structures production skills — our own `claude_skills` repository follows the same `SKILL.md` + `references/` + `scripts/` convention
- The `skill-creator` skill can be installed and used directly in Claude Code to bootstrap new skills for this project
- The `mcp-builder` skill provides a template for creating new MCP servers to extend agent tooling
- The `webapp-testing` skill's Playwright patterns are applicable to testing any web-based tooling we build

### Patterns Worth Adopting

- **Description-first triggering**: The description field in SKILL.md frontmatter controls invocation — writing precise, trigger-conditional descriptions (including explicit "DO NOT TRIGGER when" clauses as in `claude-api`) improves reliability
- **A/B evaluation loop**: The `skill-creator` parallel `with-skill` / `without-skill` evaluation pattern is directly applicable for validating skills in this repository
- **Progressive disclosure in skill writing**: Skills should front-load the most common cases; edge cases and advanced options go at the end — mirrors the progressive disclosure principle documented in skill-creator's Skill Writing Guide
- **Principle of Lack of Surprise**: Skills should behave predictably — no hidden state changes, output formats declared explicitly in the skill
- **Imperative form instructions**: Skill instructions use imperative mood ("Create", "Output", "Return") not descriptive mood

### Integration Opportunities

- Install `example-skills@anthropic-agent-skills` to bring `skill-creator` into Claude Code sessions for iterating on skills in this project
- The `claude-api` skill's trigger pattern (detecting `import anthropic` in code) is a reusable pattern for context-aware skill activation in developer tool skills
- The evaluation harness architecture (spawn parallel runs, draft assertions, grade, view results) could be adapted for regression testing of skill changes in CI

SOURCE: Analysis of repository contents (2026-03-06); [Equipping agents for the real world with Agent Skills](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (referenced in README)

---

## References

- [anthropics/skills GitHub repository](https://github.com/anthropics/skills) (accessed 2026-03-06)
- [anthropics/skills README](https://github.com/anthropics/skills/blob/main/README.md) (accessed 2026-03-06)
- [.claude-plugin/marketplace.json](https://github.com/anthropics/skills/blob/main/.claude-plugin/marketplace.json) (accessed 2026-03-06)
- [skill-creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) (accessed 2026-03-06)
- [mcp-builder SKILL.md](https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md) (accessed 2026-03-06)
- [webapp-testing SKILL.md](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md) (accessed 2026-03-06)
- [Agent Skills specification](https://agentskills.io/specification) (canonical spec host; not fetched directly)
- [What are skills? — Anthropic support](https://support.claude.com/en/articles/12512176-what-are-skills) (referenced in README)
- [How to create custom skills — Anthropic support](https://support.claude.com/en/articles/12512198-creating-custom-skills) (referenced in README)
- [Equipping agents for the real world with Agent Skills — Anthropic engineering blog](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (referenced in README)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Agent Skills Eval](../evaluation-testing/agent-skills-eval.md) | evaluation-testing | referenced by Agent Skills Eval (evaluation-testing) |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-06 |
| Version at Verification | 1.0.0 (marketplace metadata) |
| Next Review Recommended | 2026-06-06 |
