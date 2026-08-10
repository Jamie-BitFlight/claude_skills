---
title: "Impeccable"
source_url: "https://github.com/pbakaus/impeccable"
license: "Apache 2.0 (based on Anthropic's frontend-design skill)"
version_at_research: "Latest (no formal version tag)"
research_date: "2026-08-10"
next_review: "2026-11-10"
---

# Impeccable

## Overview

Impeccable is a design skill system that enhances AI coding agents' ability to generate quality frontend interfaces. Created by Paul Bakaus, it provides structured design guidance through a unified command interface available across multiple AI development tools including Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, and others. The system includes twenty-three specialized design commands organized around quality assurance workflows.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI-generated interfaces produce repetitive, predictable designs using common templates and palettes | Provides deterministic detection rules (59+ rules) that identify design anti-patterns and enforce design principles |
| Generic "good design" advice without concrete examples of mistakes to avoid | Explicit anti-pattern taxonomy showing what to avoid (e.g., Inter typeface everywhere, purple-to-blue gradients, nested cards) |
| Designs lack project context and brand coherence | Mandatory context-gathering protocol (`/teach-impeccable` + `.impeccable.md`) ensuring AI has target audience, use cases, and brand personality before generating designs |
| Design validation requires human review with no structured quality checks | Audit commands automate technical quality checks without requiring API calls or LLM inference |

---

## Key Features

### Design Commands Suite

Twenty-three specialized commands for design iteration:
- **`/audit`**: Technical quality checks identifying design issues
- **`/critique`**: UX design review with accessibility and usability feedback
- **`/polish`**: Shipping readiness validation
- **`/shape`**: UX/UI planning and wireframing
- **`/bolder`, `/quieter`**: Visual emphasis adjustments
- **`/animate`**: Motion and interaction specifications
- **`/harden`**: Robustness and edge-case validation

Commands accept optional scope arguments (e.g., `/audit header`, `/polish checkout-form`) to focus feedback on specific components.

### Design Principles in Reference Files

The skill provides reference documentation covering foundational design concepts extracted from typographic and color theory sources:

**Vertical Rhythm** — "Your line-height should be the base unit for ALL vertical spacing." If body text has `line-height: 1.5` on `16px` type, spacing values should be multiples of 24px.

**Modular Scale** — Uses a 5-size system (xs, sm, base, lg, xl+) with ratios like 1.25 (major third), 1.333 (perfect fourth), or 1.5 (perfect fifth) to create contrast in hierarchy rather than subtle gradations.

**OKLCH Color Model** — Advocates for OKLCH over HSL: "As you move toward white or black, reduce chroma (saturation). High chroma at extreme lightness looks garish." Example: `oklch(60% 0.15 250)` for primary blue, `oklch(85% 0.08 250)` for lighter variant.

### Context Gathering Protocol

Mandatory pre-design workflow that ensures adequate project context:

Run `/impeccable init` once per project to establish design context. This writes configuration files to `.impeccable/` directory.

**Required context** (minimum):
- Target audience: Who uses this product and in what context?
- Use cases: What jobs are they trying to get done?
- Brand personality/tone: How should the interface feel?

---

## Technical Architecture

### System Components

**Universal Skill**: Provider-agnostic core skill payload distributed to multiple AI harnesses (Claude Code, GitHub Copilot, Cursor, Codex, etc.)

**Detection Engine**: "59 deterministic detector rules plus LLM-only critique checks" that identify design anti-patterns without requiring API calls or LLM inference, enabling fast feedback.

**Provider Hooks**: Native manifests for each supported platform (Claude Code, GitHub Copilot, Codex, Cursor, Grok Build) that integrate the detector into agent edit flows.

**CLI Tool**: Standalone `npx impeccable detect` command for scanning HTML files, directories, or URLs outside of AI agents.

**Live Mode**: Browser-based visual iteration framework with session state management for design experimentation and refinement.

**Configuration System**: Initial `/impeccable init` establishes project context through `PRODUCT.md` and `DESIGN.md`, defining audience, brand voice, colors, typography, and component specifications. Configuration is stored in `.impeccable/` directory.

---

## Installation & Usage

### Installation Methods

**Option 1: Website Download (Recommended)**

Visit impeccable.style and download ready-to-use bundles as ZIP files for your platform.

**Option 2: Command-Line Install**

```bash
npx impeccable install
```

This auto-detects AI tool folders and installs provider-specific configurations.

**Option 3: Copy from Repository**

**For Claude Code (project-specific):**

```bash
cp -r dist/claude-code/.claude your-project/
```

**For Claude Code (global):**

```bash
cp -r dist/claude-code/.claude/* ~/.claude/
```

**For Cursor:**

```bash
cp -r dist/cursor/.cursor your-project/
```

Note: Cursor requires Nightly channel and "Agent Skills" enabled in settings.

**For Gemini CLI:**

```bash
cp -r dist/gemini/.gemini your-project/
```

Note: Requires `npm i -g @google/gemini-cli@preview` and manual skill enabling.

**For Codex CLI:**

```bash
cp -r dist/codex/.codex/* ~/.codex/
```

### Usage Workflow

1. Run `/impeccable init` once per project to establish design context
2. Use specific commands like `/impeccable audit` with optional targets
3. Pin frequently-used commands to create shortcuts for faster access

**Available Commands (23 total):**

Commands include: `audit`, `polish`, `shape`, `critique`, `craft`, `init`, `document`, `extract`, `bolder`, `quieter`, `distill`, `harden`, `onboard`, `animate`, `colorize`, `typeset`, `layout`, `delight`, `overdrive`, `clarify`, `adapt`, `optimize`, and `live`.

**Codex CLI exception**: Uses `/prompts:audit`, `/prompts:polish` syntax instead of `/audit`, `/polish`.

---

## Relevance to Claude Code Development

### Direct Applications

1. **Skill Distribution Architecture**: Impeccable's approach—maintaining rich source metadata and distributing provider-specific manifests—is a practical pattern for managing multi-tool skill deployment. Claude Code developers can adopt this architecture for cross-platform skills.

2. **Design Guidance Reference**: The skill provides a complete reference library for frontend design. Claude Code users creating UI components, web artifacts, or design systems can load and reference these skills to improve output quality.

3. **Anti-Pattern Taxonomy**: The explicit list of design anti-patterns provides a training model for how to teach AI systems to avoid predictable mistakes. Rather than generic "good design" advice, Impeccable uses concrete examples of what to avoid.

4. **Context Protocol**: The mandatory context-gathering protocol demonstrates a pattern for ensuring AI harnesses have adequate project context before generating content, preventing generic output.

5. **Command-Based Workflows**: The 23 specialized commands model a workflow-driven approach to design iteration (audit → normalize → polish) that aligns with multi-agent orchestration patterns used in Claude Code development.

---

## Limitations and Caveats

### No Programmatic API

Impeccable provides skills and commands but no programmatic API for integrating design validation into CI/CD pipelines or automated workflows. The `/audit` command is designed for human review, not machine-readable output.

### Tool Compatibility Varies

While skills are distributed for 8+ tools, feature parity is not guaranteed. Claude Code, OpenCode, and Gemini CLI receive full metadata support; Cursor and other tools receive basic frontmatter. Cursor requires Nightly channel + manual enabling.

### Codex CLI Syntax Differs

Codex CLI uses `/prompts:audit` instead of `/audit`, creating a non-standard invocation pattern compared to other tools.

### Context Dependency

Design output quality depends entirely on context provided by `/teach-impeccable` or `.impeccable.md`. The skill cannot infer context from code. Projects without context setup will receive generic output, defeating the purpose of the tool.

### No Benchmarking or Evaluation

The website includes "case studies" of before/after design improvements, but no public benchmarking data, metrics, or user studies. Results are presented as qualitative examples, not quantified.

---

## References

- GitHub Repository: <https://github.com/pbakaus/impeccable> (accessed 2026-08-10)
- Official Website: <https://impeccable.style> (accessed 2026-08-10)
- README.md: <https://github.com/pbakaus/impeccable/blob/main/README.md> (accessed 2026-08-10)
- DEVELOP.md: <https://github.com/pbakaus/impeccable/blob/main/DEVELOP.md> (accessed 2026-08-10)
- Typography Reference: <https://github.com/pbakaus/impeccable/blob/main/source/skills/frontend-design/reference/typography.md> (accessed 2026-08-10)
- Color & Contrast Reference: <https://github.com/pbakaus/impeccable/blob/main/source/skills/frontend-design/reference/color-and-contrast.md> (accessed 2026-08-10)
- License (Apache 2.0): <https://github.com/pbakaus/impeccable/blob/main/LICENSE> (accessed 2026-08-10)
- Anthropic Frontend-Design Skill (attribution): Referenced in Impeccable README as foundational inspiration

---

## Freshness Tracking

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | From official website and GitHub README |
| Problem Addressed | high | Directly cited from README's design anti-patterns section |
| Key Features | high | Extracted from command documentation and reference files |
| Technical Architecture | medium | Inferred from README and dist directory structure; live mode details unconfirmed |
| Installation & Usage | high | Commands directly from installation guide |
| Limitations | medium | Partially inferred from feature gaps; community engagement data from 2026-03-21 snapshot |

