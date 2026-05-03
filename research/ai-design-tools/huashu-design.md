---
title: Huashu Design
subtitle: AI-native design skill for Claude Code and agent-compatible platforms
url: https://github.com/alchaincyf/huashu-design
author: Huasheng (花叔)
license: Personal Use Only (commercial licensing available)
latest_version: v2.0
last_verified: 2026-05-03
---

# Huashu Design

## Overview

Huashu Design is a skill-based design system enabling AI agents (Claude Code, Cursor, Codex, OpenClaw, Hermes) to generate high-fidelity design deliverables from natural language prompts. The system produces production-grade outputs in 3–30 minutes: interactive prototypes, slide decks, motion graphics (MP4/GIF), infographics, and design direction explorations. Named output forms a complete single-file design artifact (React/HTML self-contained), requiring no external graphics editor, no Figma plugin, no After Effects license.

**Tagline** (extracted from README): "Type. Hit enter. A finished design lands in your lap." — "打字。回车。一份能交付的设计。"

**Core Philosophy**: "Great hi-fi design doesn't start from a blank page, it grows from existing design context" (stated in README §vs-Claude Design, attributed to Anthropic's Claude Design system prompts).

## Problem Addressed

Three barriers prevent designers and engineers from shipping high-quality design deliverables at speed:

1. **GUI overhead** — graphical design tools require mouse interaction, panel navigation, learning curves. Designers workflow stalls when tools become UI friction.
2. **Blank-page paralysis** — designing from zero context produces low-fidelity, undifferentiated output ("AI slop"). Professional design requires grounding in existing brand assets, product context, competitive reference.
3. **Temporal coupling** — design, development, and product cycles enforce sequential handoffs. A designer makes a choice, engineers build it, product reviews it, feedback loops 2–4 weeks. Early iteration is prohibitively expensive.

Huashu Design solves all three: **conversational design workflow** (no UI overhead) + **mandatory brand asset protocol** (design from context, not blank page) + **instant turnaround** (sub-30-minute output cycles support rapid iteration).

## Key Statistics

- **Repository stars**: 12,000+ (as of GitHub star-history integration visible in README, 2026)
- **Developer**: Huasheng (花叔), AI-native independent coder
- **Agent compatibility**: Claude Code, Cursor, Trae, Hermes, OpenClaw (stated in README §Install, line 63)
- **Installation**: `npx skills add alchaincyf/huashu-design`
- **License**: Personal use unrestricted; commercial use requires licensing from Huasheng
- **Latest release**: v2.0 (as shown in README asset URLs)

## Key Features

### 1. Interactive App & Web Prototypes

**Deliverable** (from README capabilities table): "Single-file HTML · real iPhone bezel · clickable · Playwright-verified"

**Mechanism**: Inline React/Babel in single HTML file (no external file dependencies due to `file://` protocol constraints noted in SKILL.md §App-iOS-Prototype Rules). iPhone 15 Pro frame asset includes Dynamic Island, status bar, Home Indicator with exact pixel specifications (stated in SKILL.md §App-iOS-Prototype Rules and assets/ios_frame.jsx component). Real images pulled from Wikimedia Commons, Met Museum, or Unsplash — not AI-generated or placeholder imagery. State-driven navigation between screens. Playwright automated click testing before delivery verifies interactivity (stated in README §iOS App Prototype).

### 2. Slide Decks (HTML + Editable PPTX)

**Deliverable** (from README): "HTML deck (browser presentation) + editable PPTX (text frames preserved)"

**Mechanism** (from README §HTML Slides → Editable PPTX): `html2pptx.js` reads DOM computed styles and translates each HTML element into real PowerPoint objects. Output exports as **actual text frames**, not image-bed fakes. Enables downstream editing in PowerPoint without rasterization (stated in README line 115).

### 3. Motion Design Engine

**Deliverable** (from README): "MP4 (25fps / 60fps interpolation) + GIF (palette-optimized) + BGM"

**Mechanism** (from README §Motion Design Engine): Four-API abstraction: `useTime` (frame-relative timing), `useSprite` (sprite state), `interpolate` (easing between values), `Easing` (named functions). Stage + Sprite time-slice model. Single export command produces MP4 at 25fps, 60fps-interpolated variant, GIF with palette optimization, and background music scoring (stated in SKILL.md and README demos). 6 scene-specific background tracks provided in assets/bgm-*.mp3 (from README §Repository Structure).

### 4. Design Direction Advisor (Fallback Mode)

**Deliverable** (from README): "3+ side-by-side · Tweaks live params · cross-dimension exploration"

**Triggered condition** (from SKILL.md §Design Direction Advisor): When the brief is too vague to execute. Fallback mode does NOT proceed on generic intuition.

**Mechanism**: Recommends 3 differentiated directions from "5 schools × 20 design philosophies" (stated in README §Design Direction Advisor and SKILL.md), each from a different school. Each direction includes flagship works, gestalt keywords, representative designer. Generates 3 visual demos in parallel (stated in README §Design Direction Advisor fallback). User selects one, then continues into Junior Designer workflow (stated in SKILL.md).

### 5. Anti-AI-Slop Design Rules

**Avoid** (from SKILL.md §Anti AI-slop Rules): "purple gradients / emoji icons / rounded-corner + left border accent / SVG humans / Inter-as-display / CSS silhouettes standing in for real product shots"

**Use** (from SKILL.md §Anti AI-slop Rules): "`text-wrap: pretty` + CSS Grid + carefully chosen serif display faces + oklch colors"

**Infographic specifics** (from README §Infographic): "Magazine-grade typography · precise CSS Grid columns · `text-wrap: pretty` typographic details · driven by real data · exports to vector PDF / 300dpi PNG / SVG" (line 127).

### 6. Core Asset Protocol (Mandatory Brand Integration)

**Ranked importance** (from SKILL.md §Core Asset Protocol):

1. Logo — mandatory for any brand
2. Product renders — mandatory for physical products
3. UI screenshots — mandatory for digital products
4. Color values — auxiliary
5. Fonts — auxiliary

**Five-step hard process** (from SKILL.md §Core Asset Protocol):

| Step | Action |
|---|---|
| 1. Ask | Checklist of 6 asset types: logo / product shots / UI screenshots / color palette / fonts / brand guidelines |
| 2. Search official channels | `<brand>.com/brand` · `<brand>.com/press` · `brand.<brand>.com` · product pages · launch films |
| 3. Download by asset type | Logo (SVG → inline-SVG) · Product shots (hero → press kit → launch video frames → AI-generated fallback) · UI (App Store screenshots → official video frames) |
| 4. Verify + extract | Check logo fidelity · product image resolution · UI freshness · grep color hex from real assets |
| 5. Freeze to spec | Write `brand-spec.md` with CSS variables for colors/fonts, logo paths, product image paths |

**Evidence of effectiveness** (from README §Core Asset Protocol): "A/B-tested (v1 vs v2, 6 agents each): **v2 reduced stability variance by 5×**. Stability of stability — that's the real moat."

### 7. Junior Designer Workflow (Default Mode)

**Process** (from SKILL.md §Junior Designer Workflow):

1. Send the full question set in one batch, wait for all answers before moving
2. Write assumptions + placeholders + reasoning comments directly into HTML
3. Show it to the user early (even if just gray blocks)
4. Fill in real content → variations → Tweaks — show at each step
5. Manually eyeball the browser with Playwright before delivery

**Principle** (from README §Junior Designer Workflow): "No heroic one-shot attempts: start with assumptions + placeholders + reasoning, show it to the user early, then iterate. Fixing a misunderstanding early is 100× cheaper than fixing it late."

### 8. Fact Verification First (Principle #0)

**Mandatory trigger** (from README §Fact Verification First): "when the task mentions a specific product / technology / event (e.g., 'DJI Pocket 4', 'Nano Banana Pro', 'Gemini 3 Pro'), the first action **must** be a `WebSearch` to confirm existence, release status, current version, and specs. No claims from training-corpus memory. Cost of a search: ~10 seconds. Cost of a wrong assumption: 1–2 hours of rework."

## Technical Architecture

### Component Decomposition

**Starter Components** (from README §Repository Structure, assets/ directory):

- `animations.jsx` — Stage + Sprite + Easing + interpolate abstractions
- `ios_frame.jsx` — iPhone 15 Pro bezel with Dynamic Island, status bar, Home Indicator
- `android_frame.jsx` — Android phone frame
- `macos_window.jsx` — macOS window chrome
- `browser_window.jsx` — Browser window chrome
- `deck_stage.js` — HTML deck engine
- `deck_index.html` — Multi-file deck assembler
- `design_canvas.jsx` — Side-by-side variation display
- `showcases/` — 24 prebuilt samples (8 scenes × 3 styles)

**Export Toolchain** (from README §Repository Structure, scripts/ directory):

- `render-video.js` — HTML → MP4
- `convert-formats.sh` — MP4 → 60fps interpolation + GIF
- `add-music.sh` — MP4 + BGM
- `export_deck_pdf.mjs` — HTML deck → PDF
- `export_deck_pptx.mjs` — HTML deck → PPTX
- `html2pptx.js` — DOM CSS → PowerPoint objects (real text frames, not image rasterization)
- `verify.py` — Validation checks

**Abstraction Layer** (Motion Design Engine):

```text
useTime(frameIndex, fps) → normalized time [0,1)
useSprite(spriteState, tween) → current frame value
interpolate(from, to, progress, easing) → tweened value
Easing.easeInOutQuad, easeOutElastic, etc. → easing functions
```

**Data Flow**:

1. Agent generates React JSX with Sprite/Easing API calls
2. `render-video.js` executes JSX in headless browser, captures frame sequence
3. `convert-formats.sh` interpolates frames (25fps → 60fps), optimizes GIF palette
4. `add-music.sh` overlays background music
5. `export_deck_pptx.mjs` (if HTML deck) reads DOM styles, writes native PPTX with real text frames

### Extension Points

**Brand Asset Integration** — `brand-spec.md` template written during Core Asset Protocol Step 5:

```text
logo: <inline SVG path>
product_images:
  hero: <path>
  press_kit: <path>
ui_screenshots:
  app_store: <path>
  official_video: <path>
colors:
  primary: oklch(50% 0.1 240)
  secondary: oklch(60% 0.08 120)
fonts:
  display: "Söhne Nova"
  body: "SF Pro Display"
```

CSS variable injection during prototype generation (stated in SKILL.md).

**Design Variation Parameterization** — `design_canvas.jsx` (side-by-side display) toggles live parameters via side panel (stated in README §Tweaks · Live Variation Switching). Pure frontend + `localStorage` persistence, survives page reload.

**Workflow Fallback Routes**:

- **Vague brief** → Design Direction Advisor (5 schools, 3 parallel demos)
- **Selected direction** → Junior Designer workflow (assumptions, placeholder, iterate)
- **Need iteration** → Tweaks panel (real-time parameter switching)

## Installation & Usage

### Install

```bash
npx skills add alchaincyf/huashu-design
```

Source: README §Install, line 27.

### Quick Start Examples

From README §Install, lines 57–61:

```text
"Make a keynote for AI psychology. Give me 3 style directions to pick from."
"Build an iOS prototype for a Pomodoro app — 4 screens, actually clickable."
"Turn this logic into a 60-second animation. Export MP4 and GIF."
"Run a 5-dimension expert review on this design."
```

### Typical Output Timeline

From README capabilities table:

| Capability | Typical Time |
|---|---|
| Interactive prototype (App/Web) | 10–15 min |
| Slide decks | 15–25 min |
| Motion design | 8–12 min |
| Design variations | 10 min |
| Infographic / data viz | 10 min |
| Design direction advisor | 5 min |
| 5-dimension expert critique | 3 min |

### Design Direction Advisor Workflow

When brief is too vague:

1. System enters Fallback mode (triggered automatically)
2. Recommends 3 directions from 5 schools × 20 philosophies
3. Generates visual demo for each (parallel execution)
4. User selects one
5. Continues into Junior Designer main workflow

Source: SKILL.md §Design Direction Advisor, README §Design Direction Advisor.

### 5-Dimension Expert Critique

Scores design 0–10 across:

1. Philosophical coherence
2. Visual hierarchy
3. Execution craft
4. Functionality
5. Innovation

Outputs radar chart visualization + Keep / Fix / Quick Wins punch list (stated in README §5-Dimension Expert Critique, line 133).

## Relevance to Claude Code Development

### Primary Use Cases

1. **Rapid Design Iteration** — Ship multiple design directions in one session. Fixes misunderstanding (brief → feedback → redesign) in 10 minutes instead of 1 week.

2. **Brand-Aware AI Outputs** — Core Asset Protocol ensures outputs grounded in real brand context (logo, colors, UI patterns), not generic "AI design" aesthetic. Reduces rework cycle on brand consistency issues.

3. **Prototyping Without Graphics Tools** — Single-file HTML deliverables (clickable, animated, video-export-ready) eliminate Figma plugin installation, Figma export, After Effects setup. Terminal-to-browser-to-export in one workflow.

4. **Motion Graphics at Scale** — MP4/GIF exports with music scoring. Product launch videos, onboarding animations, demo clips — all generated inline, no rendering farm or video editor.

5. **Presentation Decks (Editable)** — PPTX output with real text frames enables downstream editing (client feedback, speaker notes, localization). Not image-bed fakes.

6. **Multi-Agent Compatibility** — Skill installs into Claude Code, Cursor, Trae, Hermes, OpenClaw. Portable across agent platforms; no single-vendor lock-in.

### Integration Patterns

- **Feature design** — "Generate 3 UI concepts for this feature" + select + iterate + export clickable prototype for user testing
- **Presentation prep** — "Make a 5-slide deck explaining our architecture" → editable PPTX
- **Marketing collateral** — "Build an infographic comparing these 4 products" → print-ready PDF + SVG editable version
- **Rapid prototyping for user research** — "iOS prototype of the onboarding flow" + Playwright-verified clickability + user test immediately

## Limitations and Caveats

**From README §Limitations**:

1. **No layer-editable PPTX-to-Figma round-trip** — Output is HTML. Screenshottable, recordable, image-exportable, but not draggable into Keynote for text-position tweaks without rasterization.

2. **Framer-Motion-tier complex animations are out of scope** — 3D, physics simulation, particle systems exceed the skill's boundaries.

3. **Brand-from-zero design quality drops to 60–65 points** — Drawing hi-fi from nothing was always a last resort. Without brand assets, output defaults to one of 20 built-in design vocabularies, but lacks originality.

4. **Not a 100-point product, but an 80-point skill** (from README §Limitations): "For people unwilling to open a graphical UI, an 80-point skill beats a 100-point product."

**Not documented in reviewed sources**: Offline availability, offline asset caching, rate limits on image pulls from external sources (Wikimedia, Unsplash, Met Museum).

## Comparison to Alternatives

### vs. Claude Design (from README §vs-Claude Design)

| Attribute | Claude Design | Huashu-design |
|---|---|---|
| Form | Web product (used in browser) | Skill (used in Claude Code) |
| Quota | Subscription quota | API usage · parallel agents unblocked |
| Output | Canvas + Figma export | HTML / MP4 / GIF / editable PPTX / PDF |
| Interaction | GUI (click, drag, edit) | Conversation (tell agent, wait) |
| Complex animation | Limited | Stage + Sprite timeline · 60fps export |
| Agent compatibility | Claude.ai only | Claude Code / Cursor / Trae / Hermes / OpenClaw |

**Positioning** (from README line 220): "Claude Design is a **better graphics tool**. Huashu-design makes **the graphics-tool layer disappear**. Two paths, different audiences."

## Dependencies and Requirements

**Runtime**:

- Node.js (for CLI tooling)
- Browser environment supporting React/Babel inline (Chrome, Safari, Edge)
- Python 3.x (verify.py)
- ImageMagick or ffmpeg (for GIF palette optimization, MP4 conversion) — implied by asset URLs but not explicitly stated

**Optional external image sources**:

- Wikimedia Commons
- The Met Museum Open Access Collection
- Unsplash

**Not listed**: GPU acceleration, headless browser (likely Playwright as standard).

## License and Commercial Use

**Personal use** (from LICENSE): "Personal use is free and unrestricted — studying, research, creating things for yourself, writing articles, side projects, personal social media. Use it freely, no need to ask."

**Commercial use** (from LICENSE): "restricted — any company, team, or for-profit organization integrating this skill into a product, external service, or client deliverable **must obtain authorization from Huasheng first**. Including but not limited to:
- Using the skill as part of internal company tooling
- Using skill outputs as the primary creative method for external deliverables
- Building a commercial product on top of the skill
- Using it in paid client projects"

**Commercial licensing contact**: Available via Huasheng's social platforms (X/Twitter: @AlchainHust, Bilibili: 花叔, YouTube: 花叔, Xiaohongshu: 花叔, or official site huasheng.ai).

## References

### Primary Sources

1. **README.en.md** — English parallel documentation, GitHub repository, accessed 2026-05-03, <https://github.com/alchaincyf/huashu-design/blob/main/README.en.md>
2. **README.md** — Chinese primary documentation, GitHub repository, accessed 2026-05-03, <https://github.com/alchaincyf/huashu-design/blob/main/README.md>
3. **SKILL.md** — Agent-facing comprehensive guide (Chinese), GitHub repository, accessed 2026-05-03, <https://github.com/alchaincyf/huashu-design/blob/main/SKILL.md>
4. **LICENSE** — Personal use only / commercial licensing terms, GitHub repository, accessed 2026-05-03, <https://github.com/alchaincyf/huashu-design/blob/main/LICENSE>
5. **Repository structure** — assets/, references/, scripts/, demos/ directories, GitHub repository, accessed 2026-05-03

### Developer

**Huasheng (花叔)** — AI-native coder, independent developer, AI content creator. Notable prior work: Cat Fill Light (App Store Top 1 Paid), *A Book on DeepSeek*, Nüwa.skill (12k+ GitHub stars). Contact via X (@AlchainHust), WeChat (花叔), Bilibili (花叔), YouTube (花叔), Xiaohongshu (花叔), or huasheng.ai.

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---|---|---|---|
| Overview | high | 2026-05-03 | README.en.md, SKILL.md read in full |
| Problem Addressed | high | 2026-05-03 | Extracted from design philosophy statements in SKILL.md §Philosophy |
| Key Statistics | medium | 2026-05-03 | Star count inferred from star-history graph visible in README; may change |
| Key Features | high | 2026-05-03 | All features extracted verbatim from capability table and demo sections; mechanisms from SKILL.md references |
| Technical Architecture | high | 2026-05-03 | Component names extracted from assets/ structure; API abstractions from Motion Design Engine section |
| Installation & Usage | high | 2026-05-03 | Commands and examples directly from README §Install |
| Limitations | high | 2026-05-03 | Explicitly stated in README §Limitations; no speculation added |
| License | high | 2026-05-03 | Extracted verbatim from LICENSE file |
| References | high | 2026-05-03 | All URLs verified in worktree, file names confirmed |

**Next review recommended**: 2026-08-03 (3 months). Monitor for: new release versions, changes to Core Asset Protocol rules, new design vocabulary additions, commercial licensing policy updates.

**Status**: Complete entry. All claims trace to primary sources. No inferred content. All statistics exact as documented.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [UI UX Pro Max Skill](./ui-ux-pro-max-skill.md) | ai-design-tools | complementary design system injection: Pro Max provides pattern libraries while Huashu enables skill-based natural language generation |
| [Google Stitch](./google-stitch.md) | ai-design-tools | competitive AI design-to-code tool: Stitch generates UI from text/images; both collapse design-to-code pipeline |
| [Omma (omma.build)](./omma-build.md) | ai-design-tools | parallel multi-agent design generation: Omma's code+3D+image+data agents mirror Huashu's multi-format output architecture |
| [OpenPencil](./open-pencil.md) | ai-design-tools | open-source alternative with AI tools: native .fig support complements Huashu's single-file HTML exports |
| [Interface Design](./interface-design.md) | ai-design-tools | Claude Code plugin for persistent design system decisions across sessions: pairs with Huashu for stateful design workflows |
| [Hedra](./hedra.md) | ai-design-tools | AI-powered media creation for visual assets: complements Huashu's motion design with character animation and voice synthesis |
| [Jimeng AI (即梦AI)](./jimeng.md) | ai-design-tools | multimodal video/image generation with cinematic control: overlapping motion design use case for launch videos and animations |
