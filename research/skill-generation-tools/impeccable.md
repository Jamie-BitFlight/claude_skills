---
title: "Impeccable"
license: "Apache 2.0 (based on Anthropic's frontend-design skill; see NOTICE.md for attribution)"
next_review: "2026-06-21 (3 months)"
---

name: skill-name
description: What this skill provides
license: License info (optional)
compatibility: Environment requirements (optional)
user-invocable: Boolean (optional)
args: Array of argument objects (optional)
allowed-tools: Pre-approved tools list (optional, experimental)
---
Skill instructions for the LLM...

```

### Design Principles in Reference Files

The typography reference (typography.md) introduces three foundational concepts:

1. **Vertical rhythm**: "Your line-height should be the base unit for ALL vertical spacing." If body text has `line-height: 1.5` on `16px` type, spacing values should be multiples of 24px.

2. **Modular scale**: Uses a 5-size system (xs, sm, base, lg, xl+) with ratios like 1.25 (major third), 1.333 (perfect fourth), or 1.5 (perfect fifth) to create contrast in hierarchy rather than subtle gradations.

3. **Measure**: "Use `ch` units for character-based measure (`max-width: 65ch`). Line-height scales inversely with line length—narrow columns need tighter leading, wide columns need more."

The color-and-contrast reference (color-and-contrast.md) advocates for OKLCH over HSL:

```css

/* OKLCH: lightness (0-100%), chroma (0-0.4+), hue (0-360) */
--color-primary: oklch(60% 0.15 250);      /* Blue */
--color-primary-light: oklch(85% 0.08 250); /* Same hue, lighter */
--color-primary-dark: oklch(35% 0.12 250);  /* Same hue, darker */

```

The key insight: "As you move toward white or black, reduce chroma (saturation). High chroma at extreme lightness looks garish."

### Context Gathering Protocol

The frontend-design skill implements a mandatory context-gathering protocol before design work:

> "Design skills produce generic output without project context. You MUST have confirmed design context before doing any design work."

**Required context** (minimum):
- Target audience: Who uses this product and in what context?
- Use cases: What jobs are they trying to get done?
- Brand personality/tone: How should the interface feel?

The protocol enforces a 3-step gathering order:
1. Check current instructions for a **Design Context** section
2. Check `.impeccable.md` in project root for required context
3. If neither exists, run `/teach-impeccable` skill (REQUIRED—do not infer context from code)

## Installation & Usage

### Installation Methods

**Option 1: Website Download (Recommended)**

Visit impeccable.style and download ready-to-use bundles as ZIP files.

**Option 2: Copy from Repository**

**For Cursor:**

```bash

cp -r dist/cursor/.cursor your-project/

```

Note: Cursor requires Nightly channel and "Agent Skills" enabled in settings.

**For Claude Code:**

```bash
# Project-specific
cp -r dist/claude-code/.claude your-project/

# Or global
cp -r dist/claude-code/.claude/* ~/.claude/

```

**For Gemini CLI:**

```bash

cp -r dist/gemini/.gemini your-project/

```

Note: Requires `npm i -g @google/gemini-cli@preview` and manual skill enabling.

**For Codex CLI:**

```bash

cp -r dist/codex/.codex/* ~/.codex/

```

### Usage

After installation, commands are available in the AI harness:

```bash

/audit           # Find issues
/normalize       # Fix inconsistencies
/polish          # Final cleanup
/distill         # Remove complexity

```

Commands accept optional scope arguments:

```bash

/audit header
/polish checkout-form

```

**Codex CLI exception**: Uses `/prompts:audit`, `/prompts:polish` syntax instead.

## Relevance to Claude Code Development

Impeccable is directly applicable to Claude Code as both a skill platform model and a content reference for design guidance:

1. **Skill Distribution Architecture**: Impeccable's "Option A" approach—maintaining rich source metadata and downgrading for limited providers—is a practical pattern for managing multi-tool skill deployment. Claude Code developers building cross-platform skills can adopt this architecture.

2. **Design Guidance System**: The skill provides a complete reference library for frontend design. Claude Code users creating UI components, web artifacts, or design systems can load and reference these skills to improve output quality.

3. **Anti-Pattern Taxonomy**: The explicit list of design anti-patterns provides a training model for how to teach AI systems to avoid predictable mistakes. Rather than generic "good design" advice, Impeccable uses concrete examples of what to avoid.

4. **Context Protocol**: The mandatory context-gathering protocol (`/teach-impeccable` + `.impeccable.md` fallback) demonstrates a pattern for ensuring AI harnesses have adequate project context before generating content.

5. **Command-Based Workflows**: The 20 specialized commands model a workflow-driven approach to design iteration (audit → normalize → polish) that aligns with multi-agent orchestration patterns used in Claude Code development.

## Limitations and Caveats

### No Programmatic API

Impeccable provides skills and commands but no programmatic API for integrating design validation into CI/CD pipelines or automated workflows. The `/audit` command is designed for human review, not machine-readable output.

### Tool Compatibility Varies

While skills are distributed for 8 tools, feature parity is not guaranteed. Claude Code, OpenCode, and Gemini CLI receive full metadata support; Cursor and Kiro receive basic frontmatter. The README notes: "Cursor skills require setup" (Nightly channel + manual enabling).

### Codex CLI Syntax Differs

Codex CLI uses `/prompts:audit` instead of `/audit`, creating a non-standard invocation pattern compared to other tools.

### Context Dependency

Design output quality depends entirely on context provided by `/teach-impeccable` or `.impeccable.md`. The skill cannot infer context from code. Projects without context setup will receive generic output, defeating the purpose of the tool.

### No Benchmarking or Evaluation

The website includes "case studies" of before/after design improvements, but no public benchmarking data, metrics, or user studies. Results are presented as qualitative examples, not quantified.

### Limited Community Engagement

While the project has 11,915 stars, there are only 11 open issues and no visible discussion forums or community channels. Feedback mechanisms are not documented.

## References

- GitHub Repository: <https://github.com/pbakaus/impeccable> (accessed 2026-03-21)
- Official Website: <https://impeccable.style> (accessed 2026-03-21)
- Repository API metadata: GitHub REST API `/repos/pbakaus/impeccable` (accessed 2026-03-21)
- README.md: <https://github.com/pbakaus/impeccable/blob/main/README.md> (accessed 2026-03-21)
- DEVELOP.md: <https://github.com/pbakaus/impeccable/blob/main/DEVELOP.md> (accessed 2026-03-21)
- package.json v1.5.1: <https://github.com/pbakaus/impeccable/blob/main/package.json> (accessed 2026-03-21)
- Typography reference: <https://github.com/pbakaus/impeccable/blob/main/source/skills/frontend-design/reference/typography.md> (accessed 2026-03-21)
- Color & Contrast reference: <https://github.com/pbakaus/impeccable/blob/main/source/skills/frontend-design/reference/color-and-contrast.md> (accessed 2026-03-21)
- Frontmatter-design skill SKILL.md: <https://github.com/pbakaus/impeccable/blob/main/source/skills/frontend-design/SKILL.md> (accessed 2026-03-21)
- License file (Apache 2.0): <https://github.com/pbakaus/impeccable/blob/main/LICENSE> (accessed 2026-03-21)
- NOTICE.md (attribution): <https://github.com/pbakaus/impeccable/blob/main/NOTICE.md> (referenced 2026-03-21)
- Agent Skills Specification: <https://agentskills.io/specification> (cited in DEVELOP.md)
