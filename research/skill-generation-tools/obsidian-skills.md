# Obsidian Skills Repository

## Identity

**Resource Name**: obsidian-skills

**Maintainer**: Steph Ango (@kepano)

**Repository**: <https://github.com/kepano/obsidian-skills>

**License**: MIT License (Copyright 2026)

**Official Specification**: Follows the [Agent Skills specification](https://agentskills.io/specification) — an open format for creating modular, reusable capabilities for AI agents.

## Current Metrics (as of 2026-03-12)

- **GitHub Stars**: 13,343
- **GitHub Forks**: 730
- **Watchers**: 13,343
- **Repository Created**: January 2, 2026
- **Last Commit**: March 2, 2026 (10 days ago)
- **Collaborators**: 12

**Confidence**: high — metrics from official GitHub API

## Purpose and Overview

Obsidian Skills is a curated collection of AI agent skills for the Obsidian note-taking application. The repository provides reusable, agent-compatible instructions and utilities that enable AI agents to create, read, modify, and interact with Obsidian-specific file formats and vault functionality.

The skills enable agents to work with Obsidian's ecosystem without direct user mediation — agents can independently create and modify notes using Obsidian Flavored Markdown syntax, construct database-like views using Obsidian Bases, design visual content in JSON Canvas format, automate vault operations via CLI, and extract clean content from web pages.

**Extracted Evidence**: README states "Agent Skills for use with Obsidian. These skills follow the [Agent Skills specification](https://agentskills.io/specification) so they can be used by any skills-compatible agent, including Claude Code and Codex CLI."

**Confidence**: high — primary source (README.md)

## Architecture

The repository follows the Agent Skills specification directory structure:

```
obsidian-skills/
├── skills/
│   ├── obsidian-markdown/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── CALLOUTS.md
│   │       ├── EMBEDS.md
│   │       └── PROPERTIES.md
│   ├── obsidian-bases/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── FUNCTIONS_REFERENCE.md
│   ├── json-canvas/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── EXAMPLES.md
│   ├── obsidian-cli/
│   │   └── SKILL.md
│   └── defuddle/
│       └── SKILL.md
├── .claude-plugin/
├── README.md
└── LICENSE
```

### Core Design Pattern

Each skill is a self-contained directory containing:

1. **SKILL.md** — Frontmatter with metadata (name, description) followed by detailed instructions for the agent on how to perform the skill. Instructions include syntax rules, workflows, examples, and reference links to official documentation.

2. **references/** (optional) — Supporting documentation files that provide detailed reference material, formulas, callout types, embed syntax, property definitions, and complete examples. These files are linked from SKILL.md and read by agents as needed.

3. **Agent-compatible instruction format** — SKILL.md content uses imperative language and structured sections (e.g., "## Workflow", "## Syntax", "## Complete Example") that agents can parse and follow.

### Skill Interaction Model

Skills are **non-interactive modules** — agents load and follow the instructions they contain. There is no runtime coupling between skills; each skill operates independently on vault content using standard file formats (Markdown, YAML-based Bases, JSON Canvas). Communication between skills occurs only through shared file modifications in the Obsidian vault.

**Extracted Evidence**: obsidian-markdown SKILL.md states "This skill covers only Obsidian-specific extensions -- standard Markdown (headings, bold, italic, lists, quotes, code blocks, tables) is assumed knowledge." This design allows agents to compose skills by understanding the file format overlap.

**Confidence**: high — derived from source code structure and documented skill boundaries

## Features

### 1. Obsidian Markdown Skill

Creates and edits Obsidian Flavored Markdown files with agent-readable syntax for:

- **Wikilinks**: `[[Note Name]]`, `[[Note Name|Display Text]]`, `[[Note Name#Heading]]` for internal vault linking with automatic rename tracking
- **Embeds**: `![[Note Name]]`, `![[image.png|300]]`, `![[document.pdf#page=3]]` to include content inline
- **Callouts**: `> [!type]` with 10+ types (note, tip, warning, info, example, quote, bug, danger, success, failure, question, abstract, todo) — collapsible with `-` or `+` prefix
- **Properties (Frontmatter)**: YAML metadata with `title`, `date`, `tags`, `aliases`, `cssclasses` for structured note metadata
- **Block IDs**: `^block-id` syntax for linking to specific paragraphs or blocks within notes
- **Comments**: `%%hidden text%%` for author notes invisible in reading view
- **Math**: LaTeX expressions in `$...$` (inline) and `$$...$$` (block) delimiters
- **Diagrams**: Mermaid syntax with optional Obsidian-specific `class NodeName internal-link;` for wikilink anchors
- **Footnotes**: `[^1]` citations and inline footnotes `^[inline content]`
- **Tags**: Inline `#tag` and hierarchical `#nested/tag` with auto-indexing in Obsidian

**Workflow documented in source**: Step 1: add frontmatter with properties, Step 2: write content, Step 3: link notes, Step 4: embed content, Step 5: add callouts, Step 6: verify in Obsidian.

**Extracted Evidence**: SKILL.md includes complete working example with properties, wikilinks, callouts, embeds, and formulas.

**Confidence**: high — full SKILL.md read; frontmatter and inline examples verified

### 2. Obsidian Bases Skill

Creates database-like views of notes using YAML-based `.base` files with:

- **Filter expressions**: String-based (e.g., `'status == "done"'`) or recursive objects (`and`, `or`, `not`) for filtering notes by property, tag, date, or link presence
- **Formula properties**: Custom computed properties using expression language (e.g., `'values.mean().round(3)'` for summaries)
- **Multiple view types**: `table`, `cards`, `list`, or `map` views of the same filtered dataset
- **Property configuration**: Custom display names, grouping direction (ASC/DESC), limiting results
- **Summary calculations**: Aggregate functions per view (mean, sum, count, etc.) with custom names
- **Global and per-view filters**: Apply filters to all views or override per view

**Schema documented in SKILL.md**: YAML structure with top-level `filters`, `formulas`, `properties`, `summaries`, `views` arrays.

**Extracted Evidence**: Complete schema definition with example filter syntax (`'file.hasTag("book")'`, `'file.hasLink("Textbook")'`, nested AND/OR/NOT expressions).

**Confidence**: high — full SKILL.md schema read; filter syntax verified against source

### 3. JSON Canvas Skill

Edits visual canvases following the JSON Canvas Spec 1.0 with:

- **Node types**: `text` (plain text or Markdown), `file` (links to files), `link` (external links), `group` (visual grouping)
- **Node attributes**: Unique 16-char hex `id`, position (`x`, `y`), dimensions (`width`, `height`), color (presets `"1"`-`"6"` or hex), text content
- **Edge connections**: `fromNode` and `toNode` IDs, optional directional anchors (`fromSide`/`toSide`: top, right, bottom, left), optional `label` text
- **Z-index ordering**: Array order determines layer (first node = bottom)
- **ID generation and uniqueness validation**: Agents must generate collision-free IDs and verify all edge references before writing

**Workflow documented in source**: 1. Create file with base structure, 2. Generate IDs, 3. Add nodes, 4. Add edges, 5. Validate JSON and references.

**Extracted Evidence**: Complete JSON Canvas Spec 1.0 structure with node and edge tables, example with 3 nodes and 2 edges connecting them.

**Confidence**: high — full SKILL.md read; examples and schema verified

### 4. Obsidian CLI Skill

Provides agent interface to Obsidian command-line operations:

- **Note operations**: `create`, `read`, `append`, `search`, with file targeting via `file=name` (wikilink-like) or `path=exact/path`
- **Property management**: `property:set` to modify note metadata
- **Vault navigation**: `backlinks`, `daily:read`, `daily:append` for daily notes, `tags` with sorting options
- **Task querying**: `tasks` command with daily filter and todo status
- **Plugin development**: `plugin:reload id=name` to hot-reload after code changes, `dev:errors` to check for exceptions, `dev:screenshot` for visual verification, `dev:dom selector=path` for DOM inspection, `dev:console level=error` for console logs
- **JavaScript evaluation**: `eval code="..."` to execute code in app context
- **CSS inspection**: `dev:css selector=... prop=...` to read computed styles
- **Parameter syntax**: Values with `=` (e.g., `name="My Note"`), flags as boolean switches (e.g., `silent` flag)

**Command reference**: "Run `obsidian help` to see all available commands. This is always up to date. Full docs: <https://help.obsidian.md/cli>"

**Extracted Evidence**: SKILL.md documents syntax, file targeting, vault targeting, common patterns (8 example commands), and plugin development workflow with 4-step develop/test cycle.

**Confidence**: high — full SKILL.md read; plugin development workflow documented with examples

### 5. Defuddle Skill

Extracts clean, agent-optimized markdown from web pages:

- **Token reduction**: Removes navigation, ads, and clutter from web content, reducing input tokens for downstream processing
- **Output formats**: Markdown (`--md`), JSON (with both HTML and markdown), plain HTML, or specific metadata (`-p title`, `-p description`, `--domain`)
- **File output**: `-o content.md` to save directly to disk
- **Installation**: `npm install -g defuddle` (global npm package)
- **Usage pattern**: `defuddle parse <url> --md` as primary command

**Extracted Evidence**: SKILL.md documents 4 usage examples: basic markdown extraction, file save, metadata extraction for title/description/domain, and output format reference table.

**Confidence**: medium — defuddle is an external npm package; SKILL.md documents its interface but defers to the package for full behavior

## Limitations and Caveats

1. **Obsidian Installation Requirement**: All skills except Defuddle require a running Obsidian instance to be available locally. The obsidian-cli skill explicitly states "Requires Obsidian to be open" and targets vaults by most-recently-focused instance or explicit `vault=` parameter. This creates a dependency on local Obsidian state that may not be available in headless or CI/CD environments.

   **Extracted Evidence**: obsidian-cli SKILL.md section "Vault targeting" states "Commands target the most recently focused vault by default."

2. **Bases Formula Language Scope**: The formula language documentation in obsidian-bases SKILL.md references a `FUNCTIONS_REFERENCE.md` file but does not inline the complete list of available functions, operators, or type constraints. Agents must consult the reference file to understand all available formula capabilities, and if that reference is incomplete, agents may not be aware of all supported operations.

   **Extracted Evidence**: obsidian-bases SKILL.md shows example formulas (`'values.mean().round(3)'`, `'status == "done"'`) but defers to references/FUNCTIONS_REFERENCE.md for comprehensive list.

3. **JSON Canvas Spec Version Lock**: The json-canvas skill implements JSON Canvas Spec 1.0 only. If Obsidian releases a newer spec version with breaking changes to node/edge structure, this skill would require updates. No version negotiation or compatibility fallback is documented.

   **Extracted Evidence**: json-canvas SKILL.md line 10: "A canvas file (`.canvas`) contains two top-level arrays following the [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)"

4. **Defuddle Token Efficiency Claims Not Validated**: The Defuddle skill claims to reduce token usage by removing clutter, but provides no benchmarks or specific token reduction percentages. Token savings depend on source page structure (navigation-heavy pages vs. content-heavy pages).

   **Extracted Evidence**: defuddle SKILL.md states "removes navigation, ads, and clutter, reducing token usage" without quantification or benchmarks.

5. **Multi-Agent Coordination Not Addressed**: When multiple agents or skill combinations are used on the same vault, there is no documented locking, conflict resolution, or transaction isolation mechanism. Concurrent modifications to the same note file could lead to data loss.

   **Not mentioned in sources** — absence of documented limitations does not confirm absence of limitations.

6. **Obsidian CLI Version Pinning**: The obsidian-cli skill references Obsidian CLI command interface but does not specify minimum or maximum version compatibility. CLI syntax and available commands may vary across Obsidian versions.

   **Extracted Evidence**: obsidian-cli SKILL.md states "Run `obsidian help` to see all available commands. This is always up to date." — defers version handling to runtime invocation.

## Installation and Setup

The repository provides multiple installation methods for different agent environments:

### 1. Plugin Marketplace (Claude Code)

```bash
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian@obsidian-skills
```

Uses the Claude Code marketplace system to discover and install skills as a bundled plugin.

**Extracted Evidence**: README.md Installation section

### 2. npm-based Installation (Skills CLI / Codex)

```bash
npx skills add git@github.com:kepano/obsidian-skills.git
```

Installs via the npm-based `skills` CLI tool (used by Codex CLI and other Agent Skills–compatible tools).

**Extracted Evidence**: README.md Installation section

### 3. Manual Installation — Claude Code

Copy the contents of this repository to a `/.claude` folder in the root of your Obsidian vault (or whichever folder you're using with Claude Code). Follows the [official Claude Skills documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

**Extracted Evidence**: README.md — "Add the contents of this repo to a `/.claude` folder in the root of your Obsidian vault"

### 4. Manual Installation — Codex CLI

Copy the `skills/` directory into your Codex skills path (typically `~/.codex/skills`). See the Agent Skills specification for the standard skill format.

**Extracted Evidence**: README.md

### 5. Manual Installation — OpenCode

Clone the entire repository into the OpenCode skills directory (`~/.opencode/skills/obsidian-skills`):

```bash
git clone https://github.com/kepano/obsidian-skills.git ~/.opencode/skills/obsidian-skills
```

Do NOT copy only the inner `skills/` folder — OpenCode expects the full repo structure so the directory hierarchy becomes `~/.opencode/skills/obsidian-skills/skills/<skill-name>/SKILL.md`. OpenCode auto-discovers all `SKILL.md` files; no configuration changes needed. Skills become available after restarting OpenCode.

**Extracted Evidence**: README.md — "Do not copy only the inner `skills/` folder — clone the full repo so the directory structure is `~/.opencode/skills/obsidian-skills/skills/<skill-name>/SKILL.md`."

## Usage Examples

### Example 1: Creating a Project Note with Obsidian Markdown Skill

Extracted directly from obsidian-markdown SKILL.md "Complete Example" section:

```markdown
---
title: Project Alpha
date: 2024-01-15
tags:
  - project
  - active
status: in-progress
---

# Project Alpha

This project aims to [[improve workflow]] using modern techniques.

> [!important] Key Deadline
> The first milestone is due on ==January 30th==.

## Tasks

- [x] Initial planning
- [ ] Development phase
  - [ ] Backend implementation
  - [ ] Frontend design

## Notes

The algorithm uses $O(n \log n)$ sorting. See [[Algorithm Notes#Sorting]] for details.

![[Architecture Diagram.png|600]]

Reviewed in [[Meeting Notes 2024-01-10#Decisions]].
```

This example demonstrates: frontmatter properties, wikilinks (`[[improve workflow]]`, `[[Algorithm Notes#Sorting]]`), callouts with custom titles, inline LaTeX math, embeds with sizing (`![[Architecture Diagram.png|600]]`), and block-level links (`[[Meeting Notes 2024-01-10#Decisions]]`).

**Confidence**: high — verbatim from source SKILL.md

### Example 2: Creating a Canvas with JSON Canvas Skill

Extracted directly from json-canvas references/EXAMPLES.md:

```json
{
  "nodes": [
    {
      "id": "8a9b0c1d2e3f4a5b",
      "type": "text",
      "x": 0,
      "y": 0,
      "width": 300,
      "height": 150,
      "text": "# Main Idea\n\nThis is the central concept."
    },
    {
      "id": "1a2b3c4d5e6f7a8b",
      "type": "text",
      "x": 400,
      "y": -100,
      "width": 250,
      "height": 100,
      "text": "## Supporting Point A\n\nDetails here."
    }
  ],
  "edges": [
    {
      "id": "3c4d5e6f7a8b9c0d",
      "fromNode": "8a9b0c1d2e3f4a5b",
      "fromSide": "right",
      "toNode": "1a2b3c4d5e6f7a8b",
      "toSide": "left"
    }
  ]
}
```

Demonstrates: node structure with unique hex IDs, positioned text nodes, edges with directional anchors (`fromSide`, `toSide`).

**Confidence**: high — verbatim from source examples file

### Example 3: Using Obsidian CLI for Plugin Development

Extracted from obsidian-cli SKILL.md "Plugin development" section:

```bash
# After making code changes:
obsidian plugin:reload id=my-plugin

# Check for errors
obsidian dev:errors

# Verify visually
obsidian dev:screenshot path=screenshot.png
obsidian dev:dom selector=".workspace-leaf" text

# Check console output
obsidian dev:console level=error
```

This 4-step workflow (reload → check errors → verify visually → check console) allows agents to iterate on plugin code with immediate feedback.

**Confidence**: high — verbatim from source SKILL.md

## Relevance to Claude Code and AI Agent Development

### 1. Skill Template for Domain-Specific Extensibility

Obsidian Skills demonstrates the Agent Skills specification applied to a specific application domain (note-taking). The repository serves as a reference implementation showing how to:

- **Decompose application features into atomic skills** — Obsidian Markdown, Bases, CLI, and Canvas are conceptually separate but work together on shared vault state
- **Document syntax and workflows in agent-readable format** — SKILL.md files use structured sections (Workflow, Syntax, Examples, References) that enable agents to parse and follow instructions
- **Reference supporting documentation** — Each skill references external docs (official Obsidian help, JSON Canvas spec, Agent Skills spec) and internal reference files, allowing agents to drill down on specific questions

### 2. Multi-Format Document Handling Pattern

The five skills collectively cover multiple content formats: Markdown (text), YAML (structured data/Bases), JSON (Canvas), and CLI operations. This pattern is directly applicable to Claude Code workflows where agents must work with heterogeneous file formats in a project.

### 3. Installation and Distribution Strategy

The repository's multi-platform installation support (marketplace, npm, manual) demonstrates how to package agent skills for broad compatibility. Claude Code can adopt this strategy for distributing custom skills across different deployment contexts.

### 4. Reference Documentation Pattern

The references/ subdirectories (CALLOUTS.md, EMBEDS.md, PROPERTIES.md, FUNCTIONS_REFERENCE.md, EXAMPLES.md) show how to break out detailed specifications from main SKILL.md instruction files. This allows agents to load comprehensive references on-demand without overwhelming the main skill instruction.

## Freshness Tracking

**Last Reviewed**: 2026-03-12 (today)

**Sources Accessed**:
- GitHub API: repository metadata current as of 2026-03-12
- Shallow clone commit: bb9ec95 (2026-03-02)
- README.md: verified 2026-03-12
- All SKILL.md files: verified 2026-03-12
- references/ subdirectories: verified 2026-03-12

**Next Review Due**: 2026-06-12 (3 months)

**Confidence Summary**:

| Section | Confidence | Notes |
|---------|------------|-------|
| Identity/Metadata | high | GitHub API, official README, copyright statement |
| Current Metrics | high | Real-time GitHub API at time of research |
| Architecture | high | Full repository structure and SKILL.md files read |
| Features | high | All five skill SKILL.md files read in full or sufficient depth |
| Limitations | medium | Some limitations inferred from absence of documented features; defuddle confidence reduced due to external dependency |
| Installation | high | README.md provides verbatim instructions for 5 methods |
| Usage Examples | high | Examples extracted verbatim from SKILL.md and references/ files |
| Relevance | medium | Relevance assessment based on derived use cases; not explicitly stated by maintainer |

**Confidence Factors**:

- Full README.md read ✓
- All 5 skill SKILL.md files read ✓
- Reference files spot-checked (obsidian-markdown PROPERTIES.md, json-canvas EXAMPLES.md) ✓
- GitHub API and repository metadata verified ✓
- Source is official GitHub repository with active maintenance (commit 10 days old) ✓

## References

- [obsidian-skills GitHub Repository](https://github.com/kepano/obsidian-skills) — Official source (accessed 2026-03-12)
- [Agent Skills Specification](https://agentskills.io/specification) — Standard that obsidian-skills follows (accessed 2026-03-12)
- [Obsidian Flavored Markdown Official Docs](https://help.obsidian.md/obsidian-flavored-markdown) (referenced in SKILL.md)
- [Obsidian Bases Official Docs](https://help.obsidian.md/bases/syntax) (referenced in SKILL.md)
- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/) (referenced in SKILL.md)
- [Obsidian CLI Official Docs](https://help.obsidian.md/cli) (referenced in SKILL.md)
- [Defuddle GitHub Repository](https://github.com/kepano/defuddle-cli) (referenced in SKILL.md)
