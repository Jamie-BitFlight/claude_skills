---
title: "Frontend Slides"
research_date: "2026-02-26"
source_url: "https://github.com/zarazhangrui/frontend-slides"
github_url: "https://github.com/zarazhangrui/frontend-slides"
version_at_research: "No tagged releases — latest commit 2026-02-02"
license: "MIT"
last_verified: "2026-02-26"
version_at_verification: "No tagged releases — commit `2026-02-02`"
next_review: "2026-05-26"
---

## Overview

Frontend Slides is a Claude Code skill that generates zero-dependency, single-file HTML presentations using Claude's frontend capabilities. It targets non-designers who need visually polished web slideshows without CSS, JavaScript, or build toolchain knowledge. The skill covers new presentation creation from scratch and PowerPoint-to-HTML conversion via `python-pptx`.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Non-designers cannot express visual preferences in words | Skill generates 3 style preview files for visual selection, bypassing design jargon |
| HTML presentations require npm, build tools, and framework knowledge | All output is a single self-contained HTML file with inline CSS and JS — zero external dependencies |
| PowerPoint files lose fidelity when shared or converted | Extracts text, images, and speaker notes via `python-pptx`; re-renders as styled HTML |
| Slide content overflows viewport, requiring internal scroll | Mandatory CSS architecture with `height: 100dvh`, `clamp()` typography, and `overflow: hidden` enforces viewport fit |
| Generic AI-generated aesthetics are visually indistinct | 12 hand-crafted style presets with specific typeface pairings and color palettes avoid purple gradients and system fonts |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 4,499 | 2026-02-26 |
| Forks | 291 | 2026-02-26 |
| Contributors | 1 | 2026-02-26 |
| Watchers | 4,499 | 2026-02-26 |
| Open Issues | 9 | 2026-02-26 |
| Latest Tagged Release | None | 2026-02-26 |
| Last Commit | 2026-02-02 | 2026-02-26 |
| Repository Created | 2026-01-28 | 2026-02-26 |

SOURCE: [GitHub API](https://api.github.com/repos/zarazhangrui/frontend-slides) (accessed 2026-02-26)

---

## Key Features

### Zero-Dependency Output Architecture

- Generates single HTML files with all CSS and JavaScript inline
- No npm, no build tools, no CDN references, no frameworks required
- Files are portable and longevity-safe — open in any browser indefinitely

### Visual-First Style Selection

- Skill generates 3 style preview HTML files before producing the full presentation
- Users react to visuals rather than describing aesthetics in words
- Eliminates the "show don't tell" design communication barrier

### 12 Curated Style Presets (STYLE_PRESETS.md)

- **Dark themes**: Bold Signal (`Archivo Black` + `Space Grotesk`, `#FF5722`), Electric Studio (`Manrope`, `#4361ee`), Creative Voltage (`Syne` + `Space Mono`, neon yellow `#d4ff00`), Dark Botanical (`Cormorant` serif + `IBM Plex Sans`)
- **Light themes**: Notebook Tabs (`Bodoni Moda` + `DM Sans`, colorful vertical tab indicators), Pastel Geometry (`Plus Jakarta Sans`, vertical pill accents), Split Pastel (peach/lavender vertical split, `Outfit`), Vintage Editorial (`Fraunces` + `Work Sans` on cream `#f5f3ee`)
- **Specialty themes**: Neon Cyber (cyan/magenta on deep navy, `Clash Display`), Terminal Green (`JetBrains Mono`, developer-focused), Swiss Modern (Bauhaus grid, `Archivo 800`), Paper & Ink (`Cormorant Garamond` + `Source Serif 4`, literary)

### Strict Viewport Fitting Enforcement

- Every `.slide` element: `height: 100vh; height: 100dvh; overflow: hidden`
- Typography scaled exclusively with `clamp(min, preferred, max)` functions
- Content density limits enforced: title slides (1 heading + subtitle), content slides (max 6 bullets or 2 paragraphs), code slides (max 10 lines), quote slides (max 3 lines)
- Responsive breakpoints target viewport heights of 700px, 600px, 500px
- When content exceeds density limits, skill splits into multiple slides

### PowerPoint Conversion (Phase 4)

- Extracts text, images, and speaker notes from `.pptx` files using `python-pptx`
- Presents extracted content for user review and confirmation before rendering
- Applies selected style preset to generate HTML with preserved assets

### JavaScript Interactivity

- `SlidePresentation` class handles keyboard navigation, touch swipe, and mouse wheel scrolling
- Intersection Observer drives scroll-triggered entrance animations
- Progress bar and navigation dots included by default
- Optional enhancements: particle systems, custom cursors, parallax effects

### Animation and Accessibility

- Entrance animations: fade+slide, scale-in, blur-in
- Background effects: gradient meshes, noise textures, CSS grid patterns
- Interactive effects: 3D tilt on hover, magnetic buttons
- All animations respect `prefers-reduced-motion` via CSS media queries
- Performance-safe: animations use `transform` and `opacity` only, avoiding layout-triggering properties

---

## Technical Architecture

The skill operates as a five-phase workflow defined in `SKILL.md`:

**Phase 0 — Intent Detection**: Determines whether the user wants a new presentation, PowerPoint conversion, or enhancement of an existing HTML file.

**Phase 1 — Content Discovery**: Collects presentation purpose (pitch, teaching, conference, internal), desired slide count, and whether source content exists.

**Phase 2 — Style Discovery**: Either accepts a preset name directly or asks mood/tone questions, then generates 3 style preview HTML files for side-by-side comparison.

**Phase 3 — Full Presentation Generation**: Renders the complete single-file HTML presentation matching content structure and chosen style.

**Phase 4 — PPT Conversion (conditional)**: Uses `python-pptx` to extract content, confirms structure with the user, then applies Phase 2 style selection.

**Phase 5 — Delivery**: Cleans temporary preview files, launches the presentation, and provides targeted customization guidance.

The repository contains exactly four files: `README.md`, `SKILL.md` (32 KB — the full skill definition), `STYLE_PRESETS.md` (13 KB — all 12 preset CSS/typography specifications), and `LICENSE`. There is no build system, no package manifest, and no runtime code — the skill itself is the product.

---

## Installation & Usage

```bash
# Clone or copy skill files to Claude Code skills directory
mkdir -p ~/.claude/skills/frontend-slides
# Copy SKILL.md and STYLE_PRESETS.md to that directory
```

Activate in Claude Code:

<eg>
/frontend-slides
</eg>

Example invocations:

<eg>
/frontend-slides Create a 10-slide pitch deck for a SaaS product with a professional dark theme

/frontend-slides Convert my presentation.pptx to HTML using the Terminal Green preset

/frontend-slides Enhance my existing slides.html with better animations
</eg>

PowerPoint conversion requires `python-pptx` installed in the environment:

```bash
pip install python-pptx
```

---

## Relevance to Claude Code Development

### Applications

- Demonstrates Claude Code skill authoring at production quality — `SKILL.md` at 32 KB is a reference example of detailed phase-based workflow specification
- Shows how to structure multi-phase AI workflows with explicit branching (Phase 0 intent detection) and user confirmation gates (Phase 1 content review, Phase 4 PPT extraction review)
- The visual-first selection pattern (generate 3 previews, user reacts) is a reusable UX strategy for any skill requiring subjective choice

### Patterns Worth Adopting

- **Phase-numbered workflow sections** in `SKILL.md` make execution order unambiguous for the model — each phase has a clear name, trigger condition, and output artifact
- **Content density constraints as explicit rules** (max bullets, max lines) prevent the model from generating slides that overflow — translatable to any output format with layout constraints
- **Preset library as a separate reference file** (`STYLE_PRESETS.md`) keeps the main skill file from becoming a data dump; the skill references the presets file rather than embedding all 12 CSS blocks inline
- **"Show, don't tell" selection UX** — generating preview artifacts for user choice rather than asking users to describe abstractions applies to theme selection, code style selection, diagram type selection, etc.

### Integration Opportunities

- The viewport-fitting CSS architecture (`clamp()` typography, `100dvh` slide height) can be extracted as a standalone reference for any skill generating HTML output
- The PowerPoint extraction workflow (extract → confirm → render) is reusable for any document-conversion skill pattern
- Style preset structure (typeface pair + primary color + signature CSS element) could seed a general design token system for Claude Code HTML generation tasks
- The single-file HTML output constraint is a deployability pattern applicable to other frontend generation skills (dashboards, reports, landing pages)

---

## References

- [GitHub Repository — zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) (accessed 2026-02-26)
- [README.md — raw content](https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/README.md) (accessed 2026-02-26)
- [SKILL.md — raw content](https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/SKILL.md) (accessed 2026-02-26)
- [STYLE_PRESETS.md — raw content](https://raw.githubusercontent.com/zarazhangrui/frontend-slides/main/STYLE_PRESETS.md) (accessed 2026-02-26)
- [GitHub API — repository metadata](https://api.github.com/repos/zarazhangrui/frontend-slides) (accessed 2026-02-26)

---
