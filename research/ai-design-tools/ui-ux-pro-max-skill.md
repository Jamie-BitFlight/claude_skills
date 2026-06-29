---
title: "UI UX Pro Max Skill"
research_date: "2026-02-26"
source_url: "https://www.uupm.cc/"
github_url: "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill"
version_at_research: "v2.2.1"
license: "MIT"
last_verified: "2026-02-26"
version_at_verification: "v2.2.1"
next_review: "2026-05-26"
---

## Overview

UI UX Pro Max is an AI skill that injects design intelligence into AI coding assistants (Claude Code, Cursor, Windsurf, Kiro, GitHub Copilot, and 12 others) by bundling a searchable design database covering 67 UI styles, 96 color palettes, 57 font pairings, 25 chart types, 29 landing page patterns, and 99 UX guidelines. When activated, the skill instructs the AI to query CSV-backed design databases via a BM25+regex search engine, then generate stack-specific production code aligned with the queried design system. It targets web and mobile stacks (React, Next.js, Vue, Nuxt, Svelte, Astro, SwiftUI, Jetpack Compose, React Native, Flutter, shadcn/ui, HTML+Tailwind, and Tailwind standalone) and is installed either via the Claude Code Marketplace or a Node.js/Python CLI.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding assistants generate visually inconsistent UI code because they lack curated design context | The skill activates automatically on UI/UX requests and queries a curated design database, injecting consistent style, color, and typography recommendations into the generation context |
| Developers must manually research typography pairings, color systems, and UX anti-patterns for each project | 57 font pairings, 96 color palettes, and 99 UX guidelines (including anti-patterns and accessibility standards) are bundled and searchable by domain and stack |
| Design decisions require industry-specific knowledge that generic LLMs generalize poorly | 100 industry-specific reasoning rules across Tech/SaaS, Finance, Healthcare, E-commerce, Services, Creative, and Emerging Tech categories constrain generation to domain-appropriate patterns |
| Maintaining design consistency across pages and sprints is difficult without a persistent design system file | The skill uses a hierarchical master design system file plus per-page override files as the source of truth across sessions |
| Installing AI design skills across 16 different AI assistants requires tool-specific manual steps | A single CLI command (`npx uipro-cli install`) generates the correct integration files for the detected or specified AI assistant |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 34,909 | 2026-02-26 |
| Forks | 3,433 | 2026-02-26 |
| Watchers | 195 | 2026-02-26 |
| Contributors | 27 | 2026-02-26 |
| Open Issues | 58 | 2026-02-26 |
| Latest Release | v2.2.1 | 2026-01-26 |
| Created | 2025-11-30 | 2026-02-26 |
| Primary Language | Python | 2026-02-26 |

SOURCE: [GitHub API](https://api.github.com/repos/nextlevelbuilder/ui-ux-pro-max-skill) (accessed 2026-02-26)

---

## Key Features

### Design Database

- 67 UI styles spanning Minimalism, Glassmorphism, Neumorphism, Brutalism, Cyberpunk, Aurora UI, AI-Native UI, Spatial Computing interfaces, and 59 additional aesthetics
- 96 color palettes segmented by industry vertical: SaaS, Healthcare, Fintech, Beauty, E-commerce, and others
- 57 font pairings with Google Fonts integration providing curated typography combinations matched by personality (e.g., "tech/startup", "editorial", "luxury")
- 25 chart types with library recommendations for dashboard and analytics views
- 29 landing page patterns optimized for conversion across industry types
- 99 UX guidelines covering best practices, anti-patterns, and WCAG accessibility standards

SOURCE: [GitHub README v2.2.1](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.md) (accessed 2026-02-26)

### Design System Generation Engine (v2.0)

- Analyzes project requirements and generates a complete design system as a persistent master file
- BM25 ranking combined with regex matching selects the highest-relevance styles and patterns from CSV databases
- Outputs industry-appropriate color moods, typography personality matches, animation/interaction effect recommendations, and anti-pattern warnings
- Generates pre-delivery quality checklists specific to the target industry and stack

### Multi-Assistant Distribution

- Supports 16 AI coding assistants: Claude Code, Cursor, Windsurf, Kiro, GitHub Copilot, Gemini CLI, Continue, Roo Code, Trae, Qoder, and others
- Two activation modes: Skill Mode (auto-activate on natural language UI/UX requests in Claude Code, Cursor, Windsurf) and Workflow Mode (slash command `/ui-ux-pro-max [request]` in Kiro, Copilot, Roo Code)
- Single CLI installer (`npx uipro-cli install`) handles all 16 assistants by generating platform-specific integration files

### Stack Coverage

- Web: HTML + Tailwind CSS, React, Next.js, shadcn/ui, Vue, Nuxt.js, Svelte, Astro
- Mobile: SwiftUI (iOS), Jetpack Compose (Android), React Native, Flutter
- Stack-specific CSV data in `data/stacks/` provides framework-appropriate component patterns

---

## Technical Architecture

The skill is structured as a source tree that is symlinked into AI assistant configuration directories:

```text
src/ui-ux-pro-max/
├── data/           # CSV databases: styles, colors, typography, charts, landing, UX
│   └── stacks/     # Stack-specific variant data (react, nextjs, vue, flutter, etc.)
├── scripts/        # search.py (BM25+regex engine), design generation tools
└── templates/      # Output format templates per platform
.claude/            # Claude Code integration files (CLAUDE.md entry point)
.claude-plugin/     # Claude Code Marketplace plugin manifest
.shared/            # Shared configuration for cross-assistant compatibility
cli/                # Node.js CLI source (published as uipro-cli on npm)
```

Activation flow in Claude Code:

1. User writes a natural language UI/UX request
2. Claude detects the skill context from `.claude/CLAUDE.md` (injected via Claude Code's skill loading)
3. Claude calls `python3 src/ui-ux-pro-max/scripts/search.py "<query>" --domain <domain>` with the appropriate domain flag (`style`, `typography`, `color`, `landing`, `chart`, `ux`, or a stack name)
4. The search engine runs BM25 ranking with regex fallback over CSV databases and returns ranked recommendations
5. Claude generates stack-specific production code incorporating the returned design tokens and guidelines
6. A master design system file is created/updated as the persistent source of truth for the project

SOURCE: [CLAUDE.md raw](https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/main/CLAUDE.md) (accessed 2026-02-26)

---

## Installation & Usage

### Claude Code Marketplace (two commands)

```bash
# Install via Claude Code Marketplace
/install-skill nextlevelbuilder/ui-ux-pro-max-skill
```

### CLI Installer (supports all 16 assistants)

```bash
# Prerequisites: Node.js and Python 3.x
npx uipro-cli install
```

The CLI detects the active AI assistant environment or accepts an explicit `--assistant` flag and generates the correct integration files (e.g., `.claude/CLAUDE.md` entry, Kiro workflow YAML, Copilot instructions file).

### Skill Mode Usage (Claude Code, Cursor, Windsurf)

Once installed, the skill auto-activates on natural language requests:

```text
User: Build a SaaS dashboard landing page in Next.js with a modern glassmorphism style
Claude: [queries design database, applies BM25 ranking, generates Next.js + Tailwind code with glassmorphism tokens]
```

### Workflow Mode Usage (Kiro, GitHub Copilot, Roo Code)

```text
/ui-ux-pro-max Create a Flutter onboarding screen for a healthcare app with a calm, trustworthy color palette
```

### Direct Search CLI

```bash
python3 src/ui-ux-pro-max/scripts/search.py "healthcare app" --domain color
python3 src/ui-ux-pro-max/scripts/search.py "SaaS landing" --domain landing
python3 src/ui-ux-pro-max/scripts/search.py "dashboard" --domain chart --stack react
```

---

## Relevance to Claude Code Development

### Applications

- This is a Claude Code Marketplace plugin, making it a direct production example of how to structure skills for the marketplace with `.claude-plugin/` manifests, `CLAUDE.md` entry points, and shared cross-assistant configuration in `.shared/`
- The BM25+regex search engine over CSV databases is a practical pattern for injecting structured domain knowledge into AI context without relying on fine-tuning or embedding pipelines
- The multi-assistant distribution approach (single repo, 16 assistants via a CLI installer) demonstrates how to package a skill for maximum ecosystem reach

### Patterns Worth Adopting

- Separating design knowledge into domain-partitioned CSV databases (`styles.csv`, `colors.csv`, `typography.csv`) makes data independently updatable and searchable without altering the skill's reasoning logic
- Using BM25 ranking with regex fallback provides deterministic, reproducible retrieval that is simpler and more auditable than vector similarity search for structured tabular data
- Hierarchical design system persistence (master file + per-page overrides) is a reusable pattern for maintaining cross-session state in any domain where consistency across interactions matters
- The industry-specific reasoning rules (100 rules across 7 verticals) show how to encode domain constraints as structured data rather than embedding them in prompts, making them independently reviewable and updatable

### Integration Opportunities

- The skill's CSV database structure and search script could be studied when building skills that need to surface structured knowledge (e.g., API pattern catalogs, security checklists, performance budgets) to Claude Code
- The `.claude-plugin/` manifest format used here is directly relevant to the Claude Code plugin ecosystem that this repository (`claude_skills`) participates in
- The CLI installer pattern (detecting assistant type, generating integration files) could inform how multi-assistant skill distribution is handled in the claude_skills publishing workflow

---

## References

- [GitHub Repository](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (accessed 2026-02-26)
- [GitHub API: Repository Metadata](https://api.github.com/repos/nextlevelbuilder/ui-ux-pro-max-skill) (accessed 2026-02-26)
- [GitHub API: Latest Release v2.2.1](https://api.github.com/repos/nextlevelbuilder/ui-ux-pro-max-skill/releases/latest) (accessed 2026-02-26)
- [CLAUDE.md (raw)](https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/main/CLAUDE.md) (accessed 2026-02-26)
- [Product Website: uupm.cc](https://www.uupm.cc/) (accessed 2026-02-26)

---
