---
title: Pretext
slug: pretext
category: developer-tools
resource_url: https://github.com/chenglou/pretext
npm_package: "@chenglou/pretext"
version: "0.0.3"
license: MIT
created_date: 2026-03-29
---

## Overview

Pretext is a pure JavaScript/TypeScript library for multiline text measurement and layout. It provides DOM-free text measurement and layout capabilities, supporting all languages including emojis and mixed bidirectional text. The library allows rendering to DOM, Canvas, SVG, and server-side targets.

The core value proposition is avoiding layout reflow—a notoriously expensive browser operation. By implementing custom text measurement using the browser's font engine, Pretext enables text height calculation without triggering synchronous layout reflows that would impact UI performance.

## Problem Addressed

DOM-based text measurement methods (such as `getBoundingClientRect`, `offsetHeight`) force synchronous layout reflow—one of the most expensive operations in the browser. When multiple components independently measure text, each measurement triggers a document-wide reflow. This read/write interleaving pattern can cost 30ms+ per frame for 500 text blocks. Pretext eliminates this by moving text measurement to canvas-based arithmetic using the browser's font engine as ground truth.

## Key Statistics

- **8,029 GitHub stars** (as of 2026-03-29)
- **301 GitHub forks** (as of 2026-03-29)
- **Current version**: v0.0.3 (released 2026-03-29)
- **Performance**: `prepare()` ~19ms for 500-text batch; `layout()` ~0.09ms per batch (per STATUS.md benchmark snapshot from 2026-03-28)
- **Browser coverage**: Chrome 100%, Safari 100%, Firefox 100% (per STATUS.md: 7,680/7,680 test cases pass)

## Key Features

### 1. Two-Phase Measurement Pattern

**`prepare(text, font, options?)`** — One-time text analysis and measurement pass that normalizes whitespace, segments text using `Intl.Segmenter`, applies glue rules (punctuation merging), measures segment widths via canvas, and returns an opaque handle. When emoji correction is needed (Chrome/Firefox on macOS), performs one cached DOM calibration read per font family.

**`layout(prepared, maxWidth, lineHeight)`** — Hot path for layout calculation: pure arithmetic over cached segment widths and line-breaking rules. Returns `{ height, lineCount }`. No DOM access, no layout reflow.

### 2. Language and Script Support

- Full Unicode support via `Intl.Segmenter` for text segmentation
- Per-character breaking for CJK (Chinese, Japanese, Korean)
- Thai script support with correct breaking rules
- Arabic and mixed bidirectional text with simplified rich-path metadata for custom rendering
- Emoji support with platform-specific emoji width correction (Chrome/Firefox macOS quirk detection)
- Trailing whitespace handling (hangs past line edge without triggering breaks, matching CSS behavior)

### 3. Text Mode Options

- **`{ whiteSpace: 'normal' }`** (default) — Collapses consecutive whitespace, trims leading/trailing spaces, applies standard word-breaking rules
- **`{ whiteSpace: 'pre-wrap' }`** — Preserves ordinary spaces, tabs (`\t`), and hard line breaks (`\n`), useful for textarea-like text input

### 4. Rich Layout APIs (via `prepareWithSegments()`)

- **`layoutWithLines(prepared, maxWidth, lineHeight)`** — Returns all lines at fixed width with full text content for each line
- **`walkLineRanges(prepared, maxWidth, onLine)`** — Low-level iterator: calls callback per line with width and cursor position, without materializing line text strings (enables "shrink wrap" multiline width calculation)
- **`layoutNextLine(prepared, cursor, maxWidth)`** — Single-line iterator for dynamic width layouts (e.g., text flowing around floated images)

### 5. Cache Management

- **`clearCache()`** — Clears internal segment width caches; useful when cycling through many fonts
- **`setLocale(locale?)`** — Sets locale for future prepare operations; also calls `clearCache()`

## Technical Architecture

### Core Components

**Text Analysis** (`src/analysis.ts`):
- Whitespace normalization (different rules for 'normal' vs 'pre-wrap' modes)
- Segmentation via `Intl.Segmenter` (word-level for normal mode; grapheme-level for character-level breaking)
- Punctuation merging (certain punctuation pairs measured as one unit, matching CSS behavior)
- Kinsoku rules (Japanese line-breaking constraints)
- Hard break and soft hyphen detection

**Measurement** (`src/measurement.ts`):
- Canvas-based segment width measurement via `CanvasRenderingContext2D.measureText()`
- Emoji width correction: detects when canvas measurements differ from DOM (Chrome/Firefox on macOS only), caches correction factor per grapheme
- Supports both DOM canvas and OffscreenCanvas
- Font metric caching per font family (e.g., `"16px Inter"`)

**Bidirectional Text** (`src/bidi.ts`):
- Computes segment-level bidi levels from Unicode Bidirectional Algorithm
- Returns metadata for custom rendering without enforcing visual order (consumers decide rendering strategy)

**Line Breaking** (`src/line-break.ts`):
- Implements CSS line-breaking semantics:
  - `white-space: normal` (default) with `word-break: normal`, `overflow-wrap: break-word`
  - `white-space: pre-wrap` with grapheme-level breaking for very narrow widths
- Fast path for simple LTR text (no bidi metadata)
- Browser-specific policies for soft hyphens and breakable runs (Firefox/Safari variations)

**Layout** (`src/layout.ts`):
- Main public API surface
- Manages shared grapheme segmenter and line text caches
- Opaque `PreparedText` / `PreparedTextWithSegments` types to prevent API calcification
- Internal parallel-array representation (widths, break kinds, bidi levels, etc.)

### Data Flow

1. User calls `prepare(text, font, options)` with text and CSS font declaration (e.g., `"16px Inter"`)
2. Pretext normalizes whitespace per `whiteSpace` mode
3. Text is segmented via `Intl.Segmenter` → produces segment array
4. Each segment width is measured via canvas `measureText()` and cached
5. Bidi metadata computed if text contains RTL characters
6. One-time DOM read performs emoji correction if needed
7. Opaque handle returned to caller
8. Caller invokes `layout(prepared, maxWidth, lineHeight)` on resize
9. Layout walks cached widths with line-breaking rules → pure arithmetic, no DOM access

### Extension Points

- **Custom rendering**: `prepareWithSegments()` + `layoutWithLines()` exposes cursor positions and line boundaries for DOM, Canvas, SVG, or server-side rendering
- **Dynamic widths**: `layoutNextLine()` enables variable-width text flows (e.g., around floated images)
- **Width optimization**: `walkLineRanges()` enables binary search for optimal container width (tight text wrapping)

## Installation & Usage

### Installation

```bash
npm install @chenglou/pretext
```

Or with Bun (used by project):

```bash
bun add @chenglou/pretext
```

### Basic Usage

**Measure text height without DOM access:**

```typescript
import { prepare, layout } from '@chenglou/pretext'

// One-time preparation (19ms for 500 texts in benchmark)
const prepared = prepare('AGI 春天到了. بدأت الرحلة 🚀', '16px Inter')

// Fast layout on resize (0.09ms per call)
const { height, lineCount } = layout(prepared, 320, 20) // 320px width, 20px line height
console.log(`Text requires ${lineCount} lines, ${height}px tall`)
```

**Textarea-like text with preserved whitespace:**

```typescript
const prepared = prepare(textareaValue, '16px Courier New', { whiteSpace: 'pre-wrap' })
const { height } = layout(prepared, textareaWidth, 20)
```

**Rich layout with line access:**

```typescript
import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext'

const prepared = prepareWithSegments('Hello world', '18px "Helvetica Neue"')
const { lines } = layoutWithLines(prepared, 320, 26)

// Render each line to canvas
for (let i = 0; i < lines.length; i++) {
  ctx.fillText(lines[i].text, 0, i * 26)
}
```

**Dynamic width layout (text flowing around obstacles):**

```typescript
let cursor = { segmentIndex: 0, graphemeIndex: 0 }
let y = 0

while (true) {
  // Width changes as we flow down past a floated image
  const width = y < imageBottom ? columnWidth - imageWidth : columnWidth
  const line = layoutNextLine(prepared, cursor, width)
  if (line === null) break
  ctx.fillText(line.text, 0, y)
  cursor = line.end
  y += 26
}
```

**Find tightest container width (shrink-wrap layout):**

```typescript
const prepared = prepareWithSegments(text, '16px Inter')

// Test widths and find one that produces "nice" line count
let bestWidth = 0
let bestLineCount = Infinity

for (let testWidth = 100; testWidth <= 500; testWidth += 10) {
  let lineCount = 0
  walkLineRanges(prepared, testWidth, () => { lineCount++ })
  if (lineCount < bestLineCount) {
    bestLineCount = lineCount
    bestWidth = testWidth
  }
}

// Now get actual lines at best width
const { lines } = layoutWithLines(prepared, bestWidth, 26)
```

### Development & Demo Setup

Clone the repository and run:

```bash
bun install
bun start                    # http://localhost:3000 — stable demo pages
bun run start:watch          # with Bun file watch enabled
bun run check                # typecheck + lint (oxlint)
bun run build:package        # emit dist/ for npm package
bun run accuracy-check       # Chrome browser sweep
bun run benchmark-check      # Performance snapshot
```

Available demo pages at `/demos/`:
- `/demos/index` — Overview
- `/demos/accordion` — Collapsible sections with text measurement
- `/demos/bubbles` — Dynamic sizing
- `/demos/dynamic-layout` — Text flowing around obstacles
- `/accuracy` — Browser compatibility matrix
- `/benchmark` — Performance metrics

## Limitations and Caveats

### Browser Compatibility

- **`system-ui` font**: Not recommended on macOS. Canvas resolves to different optical font variants than DOM rendering. Use explicitly named fonts (Helvetica, Inter, etc.) for guaranteed accuracy.

### Text Layout Scope

Pretext targets the common CSS text setup:
- `white-space: normal` (default) or `white-space: pre-wrap`
- `word-break: normal` (cannot break CJK mid-word in normal mode)
- `overflow-wrap: break-word` (allowed, enables grapheme-level breaking in very narrow widths)
- `line-break: auto` (default browser behavior)
- Tab size: Fixed at `tab-size: 8` in pre-wrap mode (browser default)

Pretext does NOT attempt to be a full font rendering engine. It targets text measurement and line breaking only.

### Very Narrow Widths

At extremely narrow widths where word-break rules cannot fit a single word, Pretext falls back to grapheme-level (character-level) breaking, matching CSS `overflow-wrap: break-word` behavior.

## Relevance to Claude Code Development

This library is particularly relevant for AI-assisted development in several contexts:

1. **Layout Validation Without Browsers**: Enables _development-time_ verification (especially useful with AI agents) that UI labels, buttons, form fields, and other text-containing components don't overflow to unexpected lines. No browser required—pure JavaScript validation.

2. **Preventing Layout Shift**: Accurate text height prediction allows re-anchoring scroll position when new text loads dynamically, preventing jarring "layout shift" during content updates (common in AI-generated content).

3. **Custom Virtualization**: Enables proper virtualization and occlusion of long lists or documents without guesstimates or caching issues. Agents can reason about exact text dimensions for paging algorithms.

4. **Flexible Layout Patterns**: Supports JS-driven alternatives to CSS flexbox/grid for specialized layouts:
   - Masonry layouts that respect exact text heights
   - Text flowing around floated images or other obstacles
   - Shrink-wrap layouts for balanced text display (e.g., balanced headlines)
   - All without CSS hacks or manual measurements

5. **Server-Side Rendering**: Foundation for future server-side text layout (announced roadmap), enabling exact text dimensions during server-side rendering without headless browser overhead.

6. **Performance**: The separation of expensive one-time preparation (`prepare()`) from cheap repeated layout (`layout()`) makes it ideal for interactive AI assistants where text updates frequently but dimensions must remain accurate.

## References

- [Pretext GitHub Repository](https://github.com/chenglou/pretext) (accessed 2026-03-29)
- [npm Package: @chenglou/pretext](https://www.npmjs.com/package/@chenglou/pretext) (accessed 2026-03-29)
- [Pretext README](https://github.com/chenglou/pretext/blob/main/README.md) (accessed 2026-03-29)
- [STATUS.md — Browser accuracy & benchmark dashboard](https://github.com/chenglou/pretext/blob/main/STATUS.md) (accessed 2026-03-29, snapshots from 2026-03-27 and 2026-03-28)
- [DEVELOPMENT.md — Dev setup and testing](https://github.com/chenglou/pretext/blob/main/DEVELOPMENT.md) (accessed 2026-03-29)
- [CHANGELOG.md — Release notes](https://github.com/chenglou/pretext/blob/main/CHANGELOG.md) (accessed 2026-03-29)
- Sebastian Markbage's [text-layout](https://github.com/chenglou/text-layout) research (foundational work referenced in Pretext documentation)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Gridland](./gridland.md) | developer-tools | Shares React + Canvas rendering pattern for multi-environment output; Gridland's TextBuffer abstraction parallels Pretext's text measurement system for terminal/browser layout |
| [json-render](../agent-frameworks/json-render.md) | agent-frameworks | Overlapping use case: structured UI generation where accurate text layout prevents component overflow; json-render's streaming spec compilation and Pretext's text measurement enable accurate multi-platform rendering |
| [Pixel Agents](./pixel-agents.md) | developer-tools | Both use Canvas 2D API for measurement and rendering; shared performance optimization pattern of caching measurements to avoid repeated browser API calls |
| [Anime.js](./animejs.md) | developer-tools | Complementary library for animating text properties (color, opacity) calculated via Pretext's layout; both prioritize performance through cached state and minimal DOM access |
| [LVGL](../embedded-ui-libraries/lvgl.md) | embedded-ui-libraries | Text rendering and font metrics management for embedded displays; overlapping font measurement challenge (emoji width correction, multi-language support, layout performance) solved differently per platform |

## Freshness Tracking

**Last Reviewed**: 2026-03-29
**Next Review**: 2026-06-29 (3 months)

**Confidence by Section**:
- Identity/Metadata: **high** — npm package.json, GitHub API, CHANGELOG verified
- Key Statistics: **high** — GitHub metrics, benchmark snapshots from 2026-03-28, accuracy from 2026-03-27, version from official release
- Key Features: **high** — extracted directly from official README and source code comments
- Technical Architecture: **high** — extracted from annotated source files (`src/layout.ts`, `src/analysis.ts`, `src/measurement.ts`) with inline documentation; module structure confirmed via file inspection
- Installation & Usage: **high** — installation command and code examples from official README; confirmed against package.json exports
- Limitations and Caveats: **high** — extracted from README "Caveats" section and source code comments in layout.ts
- Relevance to Claude Code: **medium** — inferred from documented use cases (AI-friendly verification, no browser required); stated in README lines 49-50 but not explicitly detailed for AI development workflows
- Cross-References: **high** — verified via file inspection of related entries (gridland.md, json-render.md, pixel-agents.md, animejs.md, lvgl.md); scoring based on shared technologies (Canvas/React/text layout) and problem domains (performance, font metrics, measurement)

**Data Currency**:
- Browser accuracy snapshots: 2026-03-27 (2 days old, recent)
- Benchmark snapshots: 2026-03-28 (1 day old, recent)
- Package version: 0.0.3 published 2026-03-29 (today)
- Repository updated: 2026-03-29 15:32:00Z
