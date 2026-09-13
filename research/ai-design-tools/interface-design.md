---
name: interface-design
description: Claude Code plugin that brings craft, memory, and consistency to AI-generated UI. Principle-based design system for dashboards, apps, and tools — saves design decisions to system.md and loads them automatically each session.
license: MIT
metadata:
  topic: interface-design
  category: ai-design-tools
  source_url: https://github.com/Dammyjay93/interface-design
  version: "2026.2.9.1212"
  verified: "2026-02-26"
  next_review: "2026-05-26"
---

## Overview

interface-design is a Claude Code marketplace plugin that provides principle-based design engineering for AI-generated UI. Rather than letting design decisions drift between sessions, it persists chosen tokens, patterns, and rationales in a `.interface-design/system.md` file that loads automatically on each session start. The plugin ships with a SKILL.md containing crafted design principles, six pre-defined design directions (Precision & Density, Warmth & Approachability, etc.), four slash commands, and a structured workflow that requires the AI to state intent before touching code.

The repository was originally named `claude-design-skill` and was renamed after launching on the Vercel Claude Code skills marketplace.

SOURCE: [GitHub repository](https://github.com/Dammyjay93/interface-design) (accessed 2026-02-26), [README.md](https://raw.githubusercontent.com/Dammyjay93/interface-design/main/README.md) (accessed 2026-02-26)

---

## Problem Addressed

| Problem                                                       | Solution                                                                               |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Design decisions drift or reset each Claude session           | `.interface-design/system.md` loaded automatically at session start                   |
| AI defaults to generic UI templates regardless of context     | Product domain exploration step required before any visual or structural thinking      |
| Spacing, color, and depth values become inconsistent over time | System audit command (`/interface-design:audit`) checks code against defined tokens   |
| No structured way to extract patterns from existing code      | `/interface-design:extract` command reverse-engineers patterns from existing source    |
| Design rationale is lost between iterations                   | system.md stores decisions with explicit rationale alongside token values              |

---

## Key Statistics

| Metric              | Value                           | Date Gathered |
| ------------------- | ------------------------------- | ------------- |
| GitHub Stars        | 3,579                           | 2026-02-26    |
| GitHub Forks        | 242                             | 2026-02-26    |
| Open Issues         | 6                               | 2026-02-26    |
| Contributors        | 1 (Damola Akinleye)             | 2026-02-26    |
| Watchers            | 26                              | 2026-02-26    |
| Latest Release      | v2026.2.8 (2026-02-08)         | 2026-02-26    |
| Plugin Version      | 2026.2.9.1212                   | 2026-02-26    |
| Repo Created        | 2026-01-05                      | 2026-02-26    |
| Primary Language    | Shell                           | 2026-02-26    |
| License             | MIT                             | 2026-02-26    |

---

## Key Features

### Session Memory via system.md

The plugin saves established design decisions to `.interface-design/system.md` after the first session. On subsequent sessions, Claude reads this file and applies established patterns automatically — button heights, spacing scales, depth strategy, color tokens — without starting from scratch.

```markdown
# Design System

## Direction
Personality: Precision & Density
Foundation: Cool (slate)
Depth: Borders-only

## Tokens
### Spacing
Base: 4px
Scale: 4, 8, 12, 16, 24, 32
```

### Principle-Based SKILL.md

The SKILL.md (20 KB) is fully self-contained and inlines all reference content — token architecture, surface elevation, border progression, control tokens, dark mode, navigation context, card layouts, iconography, and validation checks. The inline design ensures the skill works across all agent runtimes without path resolution dependencies.

Key principle sections in SKILL.md include:

- "Where Defaults Hide" — explains how typography, navigation, and data presentation disguise default choices as infrastructure
- "Product Domain Exploration" — requires five domain concepts, five domain-native colors, one signature element, and three explicit defaults before any proposal
- "The Checks" — four tests (swap test, squint test, signature test, token test) to run before showing output

### Slash Commands

| Command                        | Purpose                                                               |
| ------------------------------ | --------------------------------------------------------------------- |
| `/interface-design:init`       | Start building UI — reads skill, loads system.md if present          |
| `/interface-design:status`     | Show current design system state                                      |
| `/interface-design:audit`      | Check code against system.md for spacing, depth, and color violations |
| `/interface-design:extract`    | Reverse-engineer design patterns from existing source files           |

### Design Directions

The plugin defines six pre-built design directions with distinct feel and recommended use cases:

| Direction              | Feel                         | Best For                         |
| ---------------------- | ---------------------------- | -------------------------------- |
| Precision & Density    | Tight, technical, monochrome | Developer tools, admin dashboards |
| Warmth & Approachability | Generous spacing, soft shadows | Collaborative tools, consumer apps |
| Sophistication & Trust | Cool tones, layered depth    | Finance, enterprise B2B          |
| Boldness & Clarity     | High contrast, dramatic space | Modern dashboards, data-heavy apps |
| Utility & Function     | Muted, functional density    | GitHub-style tools               |
| Data & Analysis        | Chart-optimized, numbers-first | Analytics, BI tools              |

### Marketplace Integration

Ships as a Claude Code marketplace plugin with a `marketplace.json` and `plugin.json`. Install via:

```bash
/plugin marketplace add Dammyjay93/interface-design
/plugin menu
```

---

## Technical Architecture

### Repository Structure

<eg>
.claude-plugin/
  marketplace.json       # Marketplace metadata (version, tags, author)
  plugin.json            # Plugin manifest (commands path, skills path)
.claude/
  commands/
    init.md              # /interface-design:init command logic
    audit.md             # /interface-design:audit command logic
    extract.md           # /interface-design:extract command logic
    status.md            # /interface-design:status command logic
    critique.md          # Design critique command
  skills/
    interface-design/
      SKILL.md            # 20 KB self-contained design principles file
      references/         # Additional reference materials
reference/
  system-template.md      # Blank system.md template with all sections
  examples/
    system-precision.md   # Example system for dashboard/admin interfaces
    system-warmth.md      # Example system for collaborative/consumer apps
website/                  # Source for interface-design.dev
</eg>

### Plugin Execution Flow

1. User invokes `/interface-design:init`
2. Command reads `.claude/skills/interface-design/SKILL.md` (always — even if system.md exists)
3. Command checks if `.interface-design/system.md` exists in the user's project
4. If system.md exists: load established tokens and patterns, apply consistently
5. If no system.md: explore product domain, suggest direction, confirm with user, build
6. After each UI task: offer to save patterns to system.md
7. Audit command (`/interface-design:audit`) parses system.md rules and checks target files for violations

### system.md Schema

The system file is free-form Markdown with defined sections: Direction (personality, foundation, depth), Tokens (spacing, colors, radius, typography), Patterns (button, card, input per component), and Decisions (table with rationale and date).

### Version Scheme

Releases use calendar versioning: `vYYYY.M.D` for tagged releases, `YYYY.M.D.HHMM` for plugin versions.

SOURCE: [GitHub API contents](https://api.github.com/repos/Dammyjay93/interface-design/contents/) (accessed 2026-02-26), [plugin.json](https://raw.githubusercontent.com/Dammyjay93/interface-design/main/.claude-plugin/plugin.json) (accessed 2026-02-26), [SKILL.md raw](https://raw.githubusercontent.com/Dammyjay93/interface-design/main/.claude/skills/interface-design/SKILL.md) (accessed 2026-02-26)

---

## Installation and Usage

### Plugin Install (Recommended)

```bash
/plugin marketplace add Dammyjay93/interface-design
/plugin menu
```

Select `interface-design` from the menu. Restart Claude Code after install.

### Manual Install

```bash
git clone https://github.com/Dammyjay93/interface-design.git
cd interface-design
cp -r .claude/* ~/.claude/
cp -r .claude-plugin/* ~/.claude-plugin/
```

### First Session Workflow

<eg>
You: "Build a user dashboard with metrics cards"

Claude (with interface-design):
  Domain: [explores product's world — 5 concepts minimum]
  Color world: [5+ domain-native colors]
  Signature: [one element unique to this product]
  Defaults: [3 patterns being deliberately avoided]

  Direction suggestion: ...
  [Confirms with user]

  Intent: [who, what task, desired feel]
  Palette: [choice + why]
  Depth: borders-only [why]
  Spacing: 8px base

  [Builds UI]
  "Want me to save these patterns to .interface-design/system.md?"
</eg>

### Subsequent Session Workflow

<eg>
You: "Add a settings page"

Claude:
  [Reads SKILL.md, loads .interface-design/system.md]
  Depth: borders-only
  Surfaces: established scale
  Spacing: 8px base
  [Builds matching settings page]
</eg>

### Audit Usage

```bash
/interface-design:audit src/components/
```

Reports violations with file/line references:

<eg>
Audit Results: src/components/

Violations:
  Button.tsx:12 - Height 38px (pattern: 36px)
  Card.tsx:8 - Shadow used (system: borders-only)
  Input.tsx:20 - Spacing 14px (grid: 4px, nearest: 12px or 16px)
</eg>

---

## Comparison with Similar Tools

| Feature                      | interface-design   | v0 (Vercel)    | Bolt.new       | Cursor         |
| ---------------------------- | ------------------ | -------------- | -------------- | -------------- |
| Session memory/persistence   | Yes (system.md)    | No             | No             | No             |
| Design principle enforcement | Yes (SKILL.md)     | No             | No             | No             |
| Works inside Claude Code     | Yes (native)       | No             | No             | No (separate)  |
| Audit against design system  | Yes                | No             | No             | No             |
| Extract patterns from code   | Yes                | No             | No             | No             |
| UI generation scope          | Dashboards/apps    | Full UI        | Full UI        | Full code      |
| Framework-agnostic           | Yes                | React/Next.js  | Multiple       | Multiple       |
| Open source                  | Yes (MIT)          | No             | No             | No             |
| Marketplace install          | Yes (Claude)       | Yes (Vercel)   | N/A            | N/A            |

---

## Relevance to Claude Code Development

### Direct Applications

1. **Plugin architecture reference**: Demonstrates a complete `marketplace.json` + `plugin.json` + `.claude/commands/` + `.claude/skills/` structure. This is a working example of the Claude Code plugin format.

2. **SKILL.md design patterns**: The self-contained SKILL.md approach (all reference content inlined, no external file reads) resolves path resolution failures when plugins are installed via marketplace. This pattern directly applies to any skill in this repository.

3. **Persistent memory via project files**: The system.md approach (project-local markdown file loaded each session) is a reusable pattern for any agent needing persistent cross-session state without external storage.

4. **Command-skill architecture**: Separating commands (user-invokable via slash) from skills (AI knowledge loaded on demand) is the core plugin pattern this repo should understand thoroughly.

### Patterns Worth Adopting

1. **Version guard in release naming**: Calendar-based versioning (`v2026.2.8`) ties releases to real dates, making freshness immediately visible — applicable to this research knowledge base.

2. **Inline reference content in SKILL.md**: The v2026.2.8 release notes explicitly mention inlining all references to remove path dependencies. Skills in this repository should follow the same principle.

3. **The "mandate" pattern**: Requiring the AI to run self-checks (swap test, squint test, signature test, token test) before presenting output is a generalizable quality gate pattern for any skill with quality-sensitive output.

4. **Scope boundary in skill description**: The explicit "Use for: dashboards; Not for: landing pages" scoping prevents skill misfire. This pattern should be applied to all skills in this repository.

### Integration Opportunities

1. **Research skill cross-reference**: When building frontend/UI agents for this repository, interface-design is the directly applicable plugin to recommend or integrate.

2. **Plugin format validation**: interface-design can be used as a canonical reference when validating that new Claude Code plugins in this repository follow correct manifest structure.

---

## References

| Source                             | URL                                                                                           | Accessed   |
| ---------------------------------- | --------------------------------------------------------------------------------------------- | ---------- |
| GitHub Repository                  | <https://github.com/Dammyjay93/interface-design>                                              | 2026-02-26 |
| README.md (raw)                    | <https://raw.githubusercontent.com/Dammyjay93/interface-design/main/README.md>                | 2026-02-26 |
| SKILL.md (raw)                     | <https://raw.githubusercontent.com/Dammyjay93/interface-design/main/.claude/skills/interface-design/SKILL.md> | 2026-02-26 |
| marketplace.json (raw)             | <https://raw.githubusercontent.com/Dammyjay93/interface-design/main/.claude-plugin/marketplace.json> | 2026-02-26 |
| plugin.json (raw)                  | <https://raw.githubusercontent.com/Dammyjay93/interface-design/main/.claude-plugin/plugin.json> | 2026-02-26 |
| Latest Release (v2026.2.8)         | <https://github.com/Dammyjay93/interface-design/releases/tag/v2026.2.8>                       | 2026-02-26 |
| GitHub API Repo Metadata           | <https://api.github.com/repos/Dammyjay93/interface-design>                                    | 2026-02-26 |
| system-template.md (raw)           | <https://raw.githubusercontent.com/Dammyjay93/interface-design/main/reference/system-template.md> | 2026-02-26 |
| Project Homepage                   | <https://interface-design.dev>                                                                 | 2026-02-26 |

**Research Method**: All data gathered from GitHub API (repository metadata, releases, directory contents, file contents via base64 decode) and raw file reads. No web scraping. Statistics reflect live API responses at the time of research.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [dark-design](./dark-design.md) | ai-design-tools | referenced by dark-design (ai-design-tools) |
| [huashu-design](./huashu-design.md) | ai-design-tools | referenced by huashu-design (ai-design-tools) |
| [minimal-gallery](../documentation-tools/minimal-gallery.md) | documentation-tools | referenced by minimal-gallery (documentation-tools) |
