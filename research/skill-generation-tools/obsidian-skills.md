---
title: "Obsidian Skills Repository"
license: "MIT License (Copyright 2026)"
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

## References

- [obsidian-skills GitHub Repository](https://github.com/kepano/obsidian-skills) — Official source (accessed 2026-03-12)
- [Agent Skills Specification](https://agentskills.io/specification) — Standard that obsidian-skills follows (accessed 2026-03-12)
- [Obsidian Flavored Markdown Official Docs](https://help.obsidian.md/obsidian-flavored-markdown) (referenced in SKILL.md)
- [Obsidian Bases Official Docs](https://help.obsidian.md/bases/syntax) (referenced in SKILL.md)
- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/) (referenced in SKILL.md)
- [Obsidian CLI Official Docs](https://help.obsidian.md/cli) (referenced in SKILL.md)
- [Defuddle GitHub Repository](https://github.com/kepano/defuddle-cli) (referenced in SKILL.md)
