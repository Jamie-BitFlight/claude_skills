---
title: Huashu Design — Design Skill for AI Agents
category: skill-generation-tools
resource_type: skill
author: alchaincyf (花叔 · 花生)
homepage: https://github.com/alchaincyf/huashu-design
repository: https://github.com/alchaincyf/huashu-design
license: Personal Use License (commercial use requires authorization)
---

# Huashu Design

**Huashu Design** (花叔Design) is a Claude Code skill that generates high-fidelity design deliverables directly from text prompts using HTML as the primary production tool. Users describe what they need in natural language, and the skill produces clickable prototypes, animated videos, presentation decks with editable PowerPoint export, data visualizations, and design direction recommendations—all without opening Figma, After Effects, or any GUI.

## Problem Addressed

Professional design tools require constant context-switching between GUI workflows and code. Designers and product managers spend time navigating menus, panels, and pixel-perfect adjustments rather than focusing on creative iteration. Commercial tools like Figma and Claude Design require expensive subscriptions or have quota limitations that don't scale with parallel agent execution.

Huashu Design inverts this: **design becomes conversational**. You describe intent once, receive multiple design direction options, select one, iterate via conversation, and export final deliverables (MP4 with synced sound design, editable PPTX, PDF, SVG). No buttons. No panels. No interface overhead.

## Key Statistics

- **Repository**: github.com/alchaincyf/huashu-design
- **SKILL.md size**: 801 lines
- **Starter components**: 8 reusable React/Babel components (animations.jsx, ios_frame.jsx, deck_stage.js, design_canvas.jsx, android_frame.jsx, macos_window.jsx, browser_window.jsx)
- **Reference documentation**: 12 deep-dive guides covering workflow, animation pitfalls, slide decks, video export, audio design, and critique methodology
- **Asset library**: 24 pre-baked showcase variations (8 scenes × 3 design philosophies), 37 preset sound effects, 6 scene-specific BGM tracks
- **Scripts**: 8 automation tools (HTML→MP4 renderer, format converter, music mixer, PDF/PPTX exporters, verification tools)
- **Multi-agent support**: Works across Claude Code, Cursor, Codex, OpenClaw, and any markdown-skill-compatible agent

## Key Features

### 1. Interactive Prototypes (10–15 min per deliverable)

Generates single-file HTML containing:
- **True device frames** with accurate bezel geometry (iPhone 15 Pro, Android, macOS, browser)
- **State-driven interactions**: tab bar switches, modal opens, form submissions—all clickable and testable via Playwright
- **Real image sourcing**: Wikimedia Commons (public domain), Met Museum API, Unsplash (free licensed) rather than placeholder gray boxes
- **Base64 data URL embedding**: Images inline as data URLs so the HTML double-clicks to open in browser without requiring a server

Extracted from README: "iPhone 15 Pro 精确机身（灵动岛 / 状态栏 / Home Indicator）· 状态驱动多屏切换 · 真图从 Wikimedia/Met/Unsplash 取 · Playwright 自动点击测试" — precise iPhone bezel (Dynamic Island / status bar / Home Indicator), state-driven multi-screen switching, real images from Wikimedia/Met/Unsplash, automated Playwright click testing.

### 2. Timeline Animation Engine (8–12 min per video)

**Motion design primitives**:
- `Stage`: time-slice based animation container
- `Sprite`: positioned element with lifecycle hooks
- `useTime`: frame-by-frame timestep accessor
- `Easing`: standard easing functions (Expo.easeOut, Back.easeInOut, etc.)
- `interpolate`: numeric tweening utility

Extracted from SKILL.md: "Stage + Sprite 时间片段模型 · `useTime` / `useSprite` / `interpolate` / `Easing` 四 API 覆盖所有动画需求" — Stage + Sprite time-slice model, four APIs (useTime, useSprite, interpolate, Easing) cover all animation requirements.

**Automated export pipeline**:
- 25fps baseline MP4 render via headless Chromium (playwright)
- 60fps interpolation via ffmpeg (frame blending)
- Palette-optimized GIF conversion (color quantization)
- **Dual-track audio synthesis**: background music (6 scene-specific compositions) + sound effects (37 preset inventory, pattern-based mixing rules)
- Automatic fade-in/fade-out detection

Extracted from SKILL.md workflow Step 9: "BGM + SFX 双轨制必须同时做——只做 BGM 是 ⅓ 分完成度" — BGM + SFX dual-track synthesis is mandatory; BGM-only is 1/3 completeness. "频段隔离见 audio-design-rules.md 的 ffmpeg 模板" — frequency isolation per audio-design-rules.md ffmpeg template.

### 3. Presentation Decks (15–25 min per deck)

**Dual architecture**:
- **Multi-file architecture** (default): each slide is independent HTML + `deck_index.html` iframe aggregator for keyboard navigation, full-screen presenter mode, and automatic page scaling
- **Single-file architecture** (≤10 slides): `deck-stage.js` web component with internal slide routing, localStorage persistence, speaker notes

**Editable PowerPoint export** (`html2pptx.js`):
- Reads computed CSS styles from DOM
- Translates each HTML element to PowerPoint native objects (text frames as editable boxes, shapes, embedded images)
- Preserves typography, layout, colors — users can edit text in PowerPoint after export by double-clicking
- "真文本框，PPT 里双击即可编辑" — true text boxes; double-click in PPT to edit.

**Real-time variations** via Tweaks system:
- localStorage-backed parameter switching (color/typography/density toggles)
- No server required; runs entirely client-side
- Persistent across browser refresh

Extracted from README: "HTML deck 浏览器演讲 · `html2pptx.js` 读 DOM 的 computedStyle 逐元素翻译成 PowerPoint 对象 · 导出的是**真文本框**，PPT 里双击即可编辑" — HTML deck browser presentation, html2pptx.js reads DOM computedStyle and translates element-by-element into PowerPoint objects, exports are true text boxes editable by double-click in PPT.

### 4. Design Direction Advisor (Fallback Mode, 5 min)

When requirements are vague ("make something beautiful", "I don't know what style"), the skill enters **Design Direction Advisor mode**:

- Recommends 3 design philosophies from a matrix of **5 schools × 20 design principles** (Pentagram information architecture, Field.io kinetic poetry, Kenya Hara minimalism, Sagmeister experimental avant-garde, Eastern philosophy)
- Each philosophy includes: design house/designer name, 50–100 word rationale, 3–4 signature visual traits, 3–5 mood keywords, optional seminal works
- Guarantees **cross-school diversity** (recommendations never come from same school twice)
- Displays **24 pre-built showcase variations** (8 scenarios × 3 design vocabularies) before generating 3 custom demo screenshots
- User selects one direction, optionally mixes traits ("A's color palette + C's layout"), or requests different directions

Extracted from SKILL.md §"设计方向顾问": "从 5 流派 × 20 种设计哲学里推荐 3 个**必须来自不同流派**的差异化方向" — recommends 3 must-be-from-different-schools philosophies from 5 schools × 20 design approaches. "每个方向配代表作、气质关键词、代表设计师" — each direction includes seminal work, mood keywords, representative designers.

### 5. Expert Design Critique (3 min, optional)

**5-dimensional scoring**:
- Philosophical consistency (design axioms coherent with brand/context)
- Visual hierarchy (size, position, contrast, depth relationships)
- Execution detail (typography, spacing, color precision, edge cases)
- Functional clarity (affordances, feedback, information scent)
- Innovation/novelty (vs. template/generic approaches)

Each dimension scored 0–10. Output includes radar chart visualization, Keep/Fix/Quick Wins actionable checklist, estimated effort per fix.

Extracted from SKILL.md §"异常处理": "5 维度评审——哲学一致性 / 视觉层级 / 细节执行 / 功能性 / 创新性各 0-10 分，输出总评 + Keep（做得好的）+ Fix（严重程度）+ Quick Wins" — 5-dimension review: philosophical consistency, visual hierarchy, execution detail, functionality, innovation, each 0–10 points, output summary + Keep + Fix + Quick Wins.

## Technical Architecture

### Core Design Principles (Hard Constraints)

1. **Asset Protocol (§1.a "核心资产协议")**
   - When task involves a specific brand/product (DJI Pocket 4, Anthropic, Linear, etc.), mandatory 5-step flow:
     - **Step 1 (Ask)**: Request logo, product imagery, UI screenshots, color values, typography, brand guidelines in prioritized checklist
     - **Step 2 (Search)**: Crawl official sources (`<brand>.com/brand`, `brand.<brand>.com`, press kits) for assets
     - **Step 3 (Download)**: Retrieve assets via 3-fallback strategy — independent SVG/PNG files, then HTML inline SVG extraction, then social media avatars
     - **Step 4 (Extract)**: Verify (SVG/PNG valid, ≥2000px resolution, transparent background), extract colors via grep (`#[0-9A-Fa-f]{6}`)
     - **Step 5 (Codify)**: Write `brand-spec.md` containing logo paths, product/UI image paths, color HEX variables, typography stack, design constraints
   - **5-10-2-8 quality threshold**: Search 5 rounds across channels, collect 10 candidates, select 2 with ≥8/10 quality per dimension (resolution, copyright clarity, brand fit, consistency, narrative independence)
   - **Logo exception**: Logo is non-negotiable (must exist); other assets follow 5-10-2-8 threshold. Missing logo → stop and ask user, do not substitute with SVG sketch

2. **Junior Designer Workflow**
   - Before execution: vocalize assumptions + reasoning + placeholder structure in HTML comments
   - Show early (even gray boxes + labels) for user validation before filling components
   - Show again after variations + tweaks before final delivery
   - Test in real browser (Playwright) before shipping
   - Goal: catch misunderstandings at 10x cheaper cost than discovering them post-delivery

3. **Anti-AI Slop Rules** (see `references/content-guidelines.md`)
   - **Prohibited**: Purple gradients, emoji icons, rounded cards + left border accents, SVG-drawn faces, Inter/Roboto as display font, Deep Blue `#0D1717` (GitHub dark mode), data/quote filler content
   - **Required**: `text-wrap: pretty` + CSS Grid for typography depth, oklch() or spec-provided colors (never invent new colors), real/AI-generated imagery over SVG sketches, serif display fonts (Newsreader/Source Serif/EB Garamond), intentional whitespace
   - **Principle**: One detail at 120%, others at 80% — brands are recognized by specific signifiers, not generic visual averaging

### Execution Model

**Component basis**: React + Babel inline (no external imports; inline JSX directly in HTML `<script type="text/babel">` tags to avoid CORS issues with `file://` protocol).

**Starter components** (in `assets/`):
- `animations.jsx`: Stage/Sprite/useTime/interpolate/Easing API for timeline motion
- `ios_frame.jsx`: iPhone 15 Pro frame (124×36 Dynamic Island, status bar, home indicator, precise bezel geometry)
- `android_frame.jsx`: Android device frame
- `deck_stage.js`: Web component for single-file slide decks (auto-scale, keyboard nav, speaker notes, localStorage persistence)
- `deck_index.html`: Multi-file deck aggregator (iframe-based, CSS isolation, print merge support)
- `design_canvas.jsx`: Grid layout for side-by-side design variations with labels
- `browser_window.jsx`, `macos_window.jsx`: Mockup frames

**Scale handling**: Fixed-size content (slides, animations) must implement JavaScript letterboxing (`auto-scale + aspect ratio preservation`); responsive content uses CSS Grid/flexbox.

**Data sourcing** (App prototypes):
- **First choice**: Real images from Wikimedia Commons (public domain), Met Museum Open Access API, Unsplash (free license)
- **Fallback**: Base64 data URL embedding (users can provide local images)
- **Last resort**: Honest placeholder (gray box + text label) or AI-generated via nano-banana-pro (secondary skill) with real brand image as reference

**Fact verification** (see SKILL.md "核心原则 #0"):
- Any claim about product existence, release date, version, specs must be WebSearch-verified before proceeding, not assumed from training data
- Example: DJI Pocket 4 released 2026-04-16 (not yet announced as of 2025 knowledge cutoff) → must search before designing announcement animation
- Trigger conditions: product names unfamiliar, 2024+ timelines, sentences like "I remember X was…" or "probably not released yet"

### Reference Documentation Structure (12 guides in `references/`)

| Guide | Purpose |
|-------|---------|
| `workflow.md` | Problem-clarification question templates, design direction decision tree, phase checkpoints |
| `react-setup.md` | Babel pinned versions, multi-component scoping via Object.assign(window, ...), CSS naming rules |
| `animation-pitfalls.md` | 14 patterns from real accidents (tick sync, recording flag, sprite lifecycle, frame rate, DOM scroll, shadow DOM, etc.) |
| `animations.md` + best-practices.md | Stage/Sprite API reference, easing function selection, Anthropic-grade narrative language (5-beat structure, Expo easing, 8 motion principles) |
| `slide-decks.md` | Multi-file vs single-file architecture trade-offs, CSS specificity pitfalls, speaker notes, `deck_stage.js` hard constraints (2 rules about slot display/section flexbox) |
| `editable-pptx.md` | 4 hard constraints for html2pptx translation (no nested containers, inline styles only, computed font size must be pixel, etc.) |
| `tweaks-system.md` | Parameter UI patterns (color picker, toggle, slider), localStorage persistence, live preview re-render |
| `design-styles.md` | 20 design philosophies with AI prompt templates (Kenya Hara, Pentagram, Sagmeister, Field.io, etc.) |
| `design-context.md` | Thin fallback: taste anchors (serif display + rust accent, low info density default, 1 hero detail at 120%) |
| `content-guidelines.md` | Anti-slop checklist, density balancing (AI/data/dashboard products exempt from minimalism), sourcing rules |
| `video-export.md` | Full pipeline: Playwright HTML→MP4 (25fps), ffmpeg frame interpolation (60fps), palette optimization, watermark placement |
| `audio-design-rules.md` | SFX + BGM dual-track synthesis, frequency isolation (SFX high-freq, BGM low-freq), ffmpeg mixing template, 4 scenario density patterns |
| `critique-guide.md` | 5-dimension scoring methodology, Keep/Fix/Quick Wins template |
| `scene-templates.md` | Pre-built mockups for common scenarios (WeChat article cover, PPT data slide, vertical infographic, personal homepage, SaaS landing, dev docs) |
| `verification.md` | Playwright screenshot automation, console error checking, interactive flow validation |

## Installation & Usage

**Installation**:
```bash
npx skills add alchaincyf/huashu-design
```

**In Claude Code or compatible agent**, describe what you need:
```
「做一份 AI 心理学的演讲 PPT，推荐 3 个风格方向让我选」
(Make a psychology-of-AI presentation deck, recommend 3 style directions for me to pick)

「做个 AI 番茄钟 iOS 原型，4 个核心屏幕要真能点击」
(Make a Pomodoro-timer iOS prototype for AI, 4 core screens must be genuinely clickable)

「把这段逻辑做成 60 秒动画，导出 MP4 和 GIF」
(Turn this logic into a 60-second animation, export MP4 and GIF)
```

**Workflow** (from SKILL.md):
1. Fact verification (if product name or timeline involved)
2. Problem clarification (one-time batch question checklist)
3. Asset protocol execution (logo + product/UI images + colors)
4. Four-question framing (narrative role, viewing distance, visual temperature, capacity estimation)
5. Junior Designer pass (assumptions + placeholders shown early)
6. Full pass (components filled, variations generated, tweaks added)
7. Browser verification + Playwright testing
8. Export (MP4 with sound, editable PPTX, PDF, HTML)

## Limitations and Caveats

**Documented limitations** (from README):
- **No layer-editable PPTX→Figma round-trip**: Output is HTML-sourced; can screenshot/record/export images but cannot drag text in Keynote after PPTX import. Screenshots and video recording are full-fidelity; direct editing within PowerPoint after import is text-box-only (no shape repositioning)
- **No Framer Motion–grade complexity**: 3D transforms, physics simulation, particle systems exceed skill boundary. Stage+Sprite model handles 2D timeline keyframe animation, not generative/procedural effects
- **Blank-slate design quality drops to 60–65 score**: When no brand context, no design system, no imagery reference exist, the output ceiling is 60–65 out of 100. High-fidelity design inherently requires existing context to hang on; from-scratch is a last resort
- **No live collaborative editing**: Design is one-off generation per request, not persistent canvas with real-time co-editing
- **HTML → video export assumes Chromium availability**: Playwright headless Chromium required; environments without it (e.g., iOS) cannot export video

**Acknowledged trade-off** (from SKILL.md): "这是一个 80 分的 skill，不是 100 分的产品。对不愿意打开图形界面的人，80 分的 skill 比 100 分的产品好用" — "This is an 80-point skill, not a 100-point product. For people unwilling to open a GUI, an 80-point skill is more usable than a 100-point product."

**Factual assumptions in SKILL.md** (verified):
- iPhone 15 Pro Dynamic Island: 124×36 pixels, top 12px, center-aligned — source: Apple Technical Specifications
- Webapp → headless Chromium video capture requires no local FFmpeg dependency for frame sequencing; ffmpeg called only for post-processing (interpolation, palette optimization, audio mixing)

## Relevance to Claude Code Development

1. **Multi-Agent Design Generation**: Huashu-Design enables parallel agent spawning for design variants (3 agents each generating one design direction in parallel, final selection logic remains with orchestrator). Skill demonstrates scalable agent specialization pattern.

2. **HTML-as-Deliverable Philosophy**: Inverts conventional "GUI tool → export → file" paradigm. All intermediates are HTML; final exports (MP4, PPTX, PDF) are derivatives. Aligns with "code-first design" ethos of Claude Code.

3. **Asset Protocol as Institutional Guardrail**: The mandatory 5-step brand asset flow (ask → search → download → validate → codify) is a replicable pattern for preventing AI slop in branded contexts. Transferable to other domains (marketing copy generation, brand voice guidelines, identity systems).

4. **Playwright as Verification Layer**: Uses headless browser testing (Playwright) not for CI/CD alone but as design quality gate. Shows how AI-generated interactive assets can be mechanically validated (click flow tests, console error detection) before delivery.

5. **Dual-Track Audio Synthesis**: BGM + SFX frequency-separated mixing is a pattern for other generative media (voiceover + background music in educational videos, dialogue + ambient sound in simulations). Extracted rule: "only 1/3 complete without dual-track audio".

6. **Design Direction Advisor as Graceful Degradation**: When user intent is ambiguous, skill auto-escalates to structured recommendation (3 cross-school options) rather than guessing. Useful pattern for orchestrators managing vague user requests across domains.

7. **React+Babel Constraint Enforcement**: Strict rules (no shared CSS scopes between `<script>` blocks, unique object names, no scrollIntoView) are anti-patterns discovered via real agent failures. Helps Claude Code's Babel sandboxing avoid silent runtime breaks.

## Confidence Summary

- **Identity/Metadata**: high — verified from GitHub README, SKILL.md frontmatter, LICENSE, version counting
- **Features**: high — extracted verbatim from README feature table + SKILL.md "能做什么" section + reference guide descriptions
- **Architecture**: high — deep-read SKILL.md entire codebase structure, component inventory, workflow phases, hard constraints
- **Limitations**: high — README "Limitations" section explicit; SKILL.md "异常处理" table; constraints marked with 🛑 checkpoints
- **Usage patterns**: high — extracted from SKILL.md "工作流程" section (10 numbered phases), workflow.md template referenced, fact-check rule ("核心原则 #0") explicit
- **Design philosophy**: high — quoting directly from SKILL.md "核心哲学" sections (5 numbered principles), "反AI slop" rules, brand asset protocol details

## References

- **Official Repository**: <https://github.com/alchaincyf/huashu-design> (accessed 2026-05-03)
- **README.md** (main documentation): <https://github.com/alchaincyf/huashu-design/blob/main/README.md> (accessed 2026-05-03)
- **SKILL.md** (801-line skill instruction document): Local read from shallow clone (accessed 2026-05-03)
- **LICENSE** (Personal Use License): <https://github.com/alchaincyf/huashu-design/blob/main/LICENSE> (accessed 2026-05-03)
- **Apple iPhone 15 Pro Technical Specifications**: Dynamic Island dimensions 124×36 pixels (verified via Apple's public spec, referenced in SKILL.md ios_frame.jsx comments)
- **Author**: alchaincyf (花叔 · 花生) — independent AI-native developer, verified via README social contact links

## Freshness Tracking

**Last reviewed**: 2026-05-03
**Next review**: 2026-08-03 (3 months)

**Data sources state**:
- GitHub repository shallow clone: fully accessible, all files readable
- Official documentation (README, SKILL.md, LICENSE): fully accessible
- External references (Apple specs, social links): not verified in detail (assumed accurate per README citations)

**Confidence by section**:

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Direct quote from README |
| Problem Addressed | high | Explicitly stated in README, SKILL.md "起源" section |
| Key Statistics | high | Counted from local file inventory and SKILL.md line count |
| Features | high | Extracted from README feature table + SKILL.md capability descriptions |
| Architecture | high | Full SKILL.md read + component inventory check |
| Limitations | high | README "Limitations" section + SKILL.md "异常处理" section |
| Installation | high | `npx skills add` command from README |
| Relevance | medium | Inferred from architectural patterns; Claude Code integration assumed but not independently tested |

