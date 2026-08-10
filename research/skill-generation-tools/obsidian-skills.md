---
title: "Obsidian Skills Repository"
source_url: "https://github.com/kepano/obsidian-skills"
license: "MIT License"
version_at_research: "Latest"
research_date: "2026-03-12"
next_review: "2026-06-12"
---

# Obsidian Skills

## Overview

Obsidian Skills is a collection of agent tools designed to integrate AI agents with Obsidian, a popular note-taking and knowledge management platform. The repository provides five core skills that follow the Agent Skills specification, making them compatible with any skills-compatible AI agent platform. These skills enable AI agents to create, edit, and manage content within Obsidian vaults programmatically, bridging the gap between AI automation and personal knowledge management systems.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents cannot work directly with Obsidian's ecosystem or personal knowledge bases | Five integrated skills (Markdown, Bases, Canvas, CLI, Defuddle) teach agents how to interact with Obsidian's open formats |
| Knowledge management requires manual copying of AI outputs into Obsidian vaults | Skills enable programmatic creation, editing, and management of content within Obsidian vaults |
| Content from web sources often contains noise and formatting issues | Defuddle skill extracts clean markdown from web pages to reduce processing overhead |
| Agents lack understanding of Obsidian-specific syntax and features | Detailed SKILL.md documentation covers wikilinks, callouts, embeds, properties, and other Obsidian-flavored markdown features |

---

## Key Features

### Five Core Skills

**Obsidian Markdown** — Create and edit markdown files with Obsidian-specific syntax including:
- Wikilinks (`[[page-name]]` and `[[page#section]]` for internal linking)
- Callouts (custom highlighted blocks with titles like `> [!important]` for emphasis)
- Embeds (`![[file.png|600]]` for including images with sizing)
- LaTeX math expressions (`$O(n \log n)$` for inline and block formulas)
- Tables, lists, and other standard markdown features

**Obsidian Bases** — Work with Obsidian's database format (available in Obsidian Sync/Plus):
- Create databases with custom fields and types
- Define views, filters, and formulas for data manipulation
- Structure relationship fields linking between database records
- Extract data from vaults for analysis and reporting

**JSON Canvas** — Create visual node-and-edge diagrams using the Canvas format:
- Define text nodes with markdown content and positioning
- Create edge connections between nodes with directional anchors
- Generate interactive visual diagrams for planning, brainstorming, and documentation
- Export diagrams as structured JSON for programmatic processing

**Obsidian CLI** — Interact with vaults through command-line tools and plugin development:
- Programmatically reload plugins during development
- Check for errors in vault configuration and plugins
- Take screenshots of vault state for verification
- Extract DOM and console output for debugging

**Defuddle** — Extract clean markdown from web pages:
- Remove navigation, ads, and other boilerplate content
- Reduce processing overhead by delivering focused markdown instead of full HTML
- Support for multiple output formats and configuration options

---

## Technical Architecture

### Skill Organization and Distribution

Skills are stored in separate directories following Agent Skills specification, with each skill containing:

- **SKILL.md**: Agent-facing instructions with YAML frontmatter declaring name, description, triggers, and version
- **references/**: Supporting documentation (e.g., CALLOUTS.md, EMBEDS.md, PROPERTIES.md)
- **README.md**: User-facing documentation
- **examples/**: Usage examples and patterns

Distribution mechanisms:
- Plugin marketplace registration for automated discovery
- npm package manager support for programmatic installation
- GitHub-based installation for direct repository access
- Support for Claude Code, Codex, OpenCode, and other Agent Skills-compatible platforms

### Skill Composition Pattern

Skills are designed to be modular but work together on shared vault state:
- **Decomposition**: Application features map to atomic skills (Markdown, Bases, Canvas, CLI)
- **Shared State**: All skills operate on the same Obsidian vault, enabling workflows that chain skills together
- **Documentation Structure**: Each skill references external docs (Obsidian help, JSON Canvas spec, Agent Skills spec) and internal reference files for drill-down detail
- **Reference Pattern**: Subdirectories (CALLOUTS.md, EMBEDS.md, PROPERTIES.md, FUNCTIONS_REFERENCE.md, EXAMPLES.md) break out detailed specifications from main SKILL.md, allowing agents to load comprehensive references on-demand

---

## Installation & Usage

### Installation Methods

**Option 1: Plugin Marketplace**

```bash
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian-markdown@kepano-skills
```

Then browse and install individual skills via `/plugin` UI.

**Option 2: npm Package Manager**

```bash
npm install @kepano/obsidian-skills --global
```

**Option 3: Manual GitHub Installation**

```bash
git clone https://github.com/kepano/obsidian-skills.git
cp -r obsidian-skills/skills/* ~/.claude/skills/
```

### Usage Examples

**Example 1: Obsidian Markdown Syntax** (from official SKILL.md)

Creating a note with wikilinks, callouts, and embeds:

```markdown
---
title: Project Alpha
date: 2026-01-15
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

See [[Algorithm Notes#Sorting]] for details.

![[Architecture Diagram.png|600]]
```

This demonstrates: frontmatter properties, wikilinks (including section links), callouts with custom titles, inline highlight syntax, checklist items, and image embeds with sizing.

**Example 2: JSON Canvas** (from json-canvas EXAMPLES.md)

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

Demonstrates: node structure with unique IDs, positioned text nodes with markdown content, edge connections with directional anchors.

**Example 3: Obsidian CLI for Plugin Development** (from obsidian-cli SKILL.md)

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

---

## Relevance to Claude Code Development

### Direct Applications

1. **Skill Template for Domain-Specific Extensibility** — Obsidian Skills demonstrates the Agent Skills specification applied to a specific application domain (note-taking). Shows how to decompose application features into atomic skills that work together on shared state.

2. **Multi-Format Document Handling Pattern** — The five skills collectively cover multiple content formats: Markdown (text), YAML (structured data/Bases), JSON (Canvas), and CLI operations. Directly applicable to Claude Code workflows where agents must work with heterogeneous file formats in a project.

3. **Installation and Distribution Strategy** — The repository's multi-platform installation support (marketplace, npm, manual) demonstrates how to package agent skills for broad compatibility. Claude Code can adopt this strategy for distributing custom skills.

4. **Reference Documentation Pattern** — References subdirectories (CALLOUTS.md, EMBEDS.md, PROPERTIES.md, FUNCTIONS_REFERENCE.md, EXAMPLES.md) show how to break out detailed specifications from main SKILL.md instruction files. Agents can load comprehensive references on-demand without overwhelming the main skill instruction.

### Patterns Worth Adopting

1. **Atomic Skill Decomposition** — Break down complex workflows into narrowly-scoped skills that map to specific application features, enabling reuse and clear boundaries.

2. **Shared State Management** — Design skills to operate on shared resources (a vault, repository, project) rather than in isolation, enabling skill composition and workflow chaining.

3. **Example-Driven Documentation** — Each skill includes complete, working examples extracted verbatim from official documentation. Agents can copy and adapt these patterns without guessing syntax.

4. **External Reference Integration** — Skills cite and link to external authoritative sources (Obsidian help, JSON Canvas spec, Agent Skills spec) and maintain internal reference files, enabling drill-down when agents need detailed specifications.

---

## Limitations and Caveats

### Limited to Obsidian Ecosystem

Skills are tightly coupled to Obsidian's specific formats and CLI. Agents cannot use these skills to work with other note-taking platforms, databases, or knowledge management systems outside Obsidian.

### Obsidian Sync/Plus Required for Bases

The Obsidian Bases skill requires Obsidian Sync or Obsidian Plus subscription. Personal vaults without these subscriptions cannot use database functionality.

### Plugin Development Requires Local Installation

The Obsidian CLI skill requires a local Obsidian installation for plugin development workflows. Agents cannot test plugins in isolated or remote environments.

### No Official Benchmarking

No public benchmarking or user studies document the effectiveness or adoption of these skills. Results and usage patterns are not quantified in available sources.

---

## References

- [Obsidian Skills GitHub Repository](https://github.com/kepano/obsidian-skills) (accessed 2026-03-12)
- [Agent Skills Specification](https://agentskills.io/specification) (referenced 2026-03-12)
- [Obsidian Flavored Markdown Official Docs](https://help.obsidian.md/obsidian-flavored-markdown) (accessed 2026-03-12)
- [Obsidian Bases Official Docs](https://help.obsidian.md/bases/syntax) (accessed 2026-03-12)
- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/) (referenced 2026-03-12)
- [Obsidian CLI Official Docs](https://help.obsidian.md/cli) (accessed 2026-03-12)

---

## Freshness Tracking

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Verified from GitHub README and repository structure |
| Problem Addressed | high | Directly cited from project purposes and feature descriptions |
| Key Features | high | Examples verbatim from SKILL.md files and reference documentation |
| Technical Architecture | high | Based on actual file structure and Agent Skills specification |
| Installation & Usage | high | Commands directly from installation guides and examples |
| Relevance | medium | Patterns identified from structure and design; specific Claude Code integration not independently tested |

