# Boneyard — Pixel-Perfect Skeleton Loading Screens

**Version**: 1.5.1
**Repository**: <https://github.com/0xGF/boneyard>
**NPM**: <https://www.npmjs.org/package/boneyard-js>
**License**: MIT
**Research Date**: 2026-04-03
**Last Updated**: 2026-04-03
**Next Review Recommended**: 2026-07-03

---

## Overview

Boneyard automates skeleton loading screen generation for React components by extracting pixel-exact bone positions directly from the rendered DOM. Instead of manually designing placeholder screens or hand-tuning layout measurements, developers wrap components with `<Skeleton>`, run `npx boneyard-js build` to snapshot the real layout, and every skeleton auto-resolves by name with zero configuration.

**Core value proposition**: Zero layout shift, no manual descriptors, pixel-perfect placeholders that match actual component layout exactly.

---

## Problem Addressed

Building loading placeholders for modern UIs requires capturing precise layout information — text dimensions, spacing, rounded corners, container backgrounds — at build time or runtime. Manual approaches (hand-measuring, CSS constants, mock content) are error-prone and don't adapt when layouts change. Skeleton screens must match the final content pixel-perfectly to avoid layout shift (CLS), but existing tools either require manual configuration or have high runtime overhead.

Boneyard solves this by:

1. Reading exact bounding rectangles from the rendered DOM using `getBoundingClientRect()`
2. Computing bone positions relative to the container (no simulation, just browser measurements)
3. Capturing at multiple breakpoints automatically
4. Storing bones as flat JSON arrays for zero-overhead runtime rendering
5. Providing a single registry lookup so every `<Skeleton name="...">` resolves automatically

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| Latest Version | 1.5.1 | npm registry (accessed 2026-04-03) |
| License | MIT | LICENSE file, npm registry |
| Repository Stars | Data unavailable at time of research | — |
| Package Type | ES modules + TypeScript | package.json `type: "module"` |
| Node Version Support | Inferred >=18 | devDependencies on @types/node ^22.19.15 |
| React Peer Dependency | >=18 (optional) | package.json peerDependencies |

---

## Key Features

### 1. DOM Snapshot Extraction

**Mechanism**: The `snapshotBones()` function walks the rendered DOM tree, reads `getBoundingClientRect()` on every visible leaf element and container, and stores positions as a flat array.

**Example usage**:
```typescript
import { snapshotBones } from 'boneyard-js'
const bones = snapshotBones(document.querySelector('.my-card'))
// Returns: { name: 'component', width: 320, height: 480, bones: [{x, y, w, h, r}, ...] }
```

**What it captures**:
- Text elements (paragraphs, headings, list items) as rectangular bones
- Media (images, videos, SVGs) with aspect ratio preservation
- Container backgrounds and borders (when visible)
- Form elements (buttons, inputs) as atomic bones
- Border radius per corner, detecting circles (50%) and pills automatically
- Exclusions for decorative elements (configurable via `snapshotConfig`)

**Source evidence**: `/packages/boneyard/src/extract.ts` lines 1–107 define `snapshotBones()`, which iterates `node.children` and calls `element.getBoundingClientRect()` for each visible element, storing positions as `{ x, y, w, h, r, c? }` objects. Lines 13–40 describe the snapshot algorithm. Default leaf tags (lines 3, 17–18) include `p, h1–h6, li, tr`. Lines 42–50 detect containers with visual surfaces (background, border-radius, background image).

### 2. React Component Wrapper

**Mechanism**: The `<Skeleton>` component conditionally renders either the skeleton (gray bone rectangles with pulse animation) or the real content based on the `loading` prop. It auto-detects dark mode, tracks container resize, and picks the correct breakpoint from pre-generated bones.

**Example usage**:
```tsx
import { Skeleton } from 'boneyard-js/react'

function BlogCard({ post, isLoading }) {
  return (
    <Skeleton name="blog-card" loading={isLoading}>
      <article>
        <img src={post.image} alt="" />
        <h2>{post.title}</h2>
        <p>{post.excerpt}</p>
      </article>
    </Skeleton>
  )
}
```

**Key behaviors**:
- **Auto dark mode detection**: Watches `prefers-color-scheme` media query and `.dark` class on ancestor elements (lines 129–149 of react.tsx)
- **Responsive breakpoint selection**: Uses `resolveResponsive()` (lines 30–39) to pick the right bone set based on current viewport width
- **Color customization**: Light mode default `rgba(0,0,0,0.08)`, dark mode default `rgba(255,255,255,0.06)`, customizable via `color` and `darkColor` props
- **Pulse animation**: Keyframes fade bones from the base color to a lighter shade every 1.8 seconds (lines 227–229)
- **Build mode flag**: Detects `window.__BONEYARD_BUILD` to render fixtures instead of children during CLI capture (lines 127, 179–184)

**Source evidence**: `/packages/boneyard/src/react.tsx` lines 109–235 define the `Skeleton` component. The `SkeletonProps` interface (lines 63–100) documents all props. `resolveResponsive()` (lines 30–39) picks breakpoints by finding the largest min-width that doesn't exceed the current container width.

### 3. Build-Time Bone Generation (CLI)

**Mechanism**: The `npx boneyard-js build` command launches a dev server, uses Playwright to navigate to each component route, injects the snapshot function into the page, and writes bones to `./src/bones/registry.ts`.

**Usage**:
```bash
npx boneyard-js build                           # Auto-detect dev server
npx boneyard-js build http://localhost:3000    # Explicit URL
npx boneyard-js build --breakpoints 390,820,1440 --out ./public/bones
```

**Output**: For each named `<Skeleton name="blog-card">`, generates:
- `src/bones/blog-card.bones.json` — responsive bones at default breakpoints (375, 768, 1024 px)
- `src/bones/registry.ts` — auto-generated import of all bone files

**App setup** (one-time):
```tsx
// app/layout.tsx
import './bones/registry'  // Populates the bones registry
```

**Source evidence**: `/packages/boneyard/src/responsive.ts` lines 1–82 define `extractResponsive()`, which defaults to breakpoints `[0, 768, 1024]` (line 5). The function resizes the container to each breakpoint, forces layout recalc (line 66: `void container.offsetHeight`), extracts the descriptor, and restores original styles. The bin/cli.js file (referenced in package.json line 23 but not read) orchestrates browser navigation and bone capture.

### 4. Responsive Breakpoint Capture

**Mechanism**: The `extractResponsive()` function captures skeleton descriptors at multiple viewport widths, resizing the container and forcing a layout recalc between each capture.

**Default breakpoints**: 375px (mobile), 768px (tablet), 1024px (desktop)

**Example**:
```typescript
const descriptor = extractResponsive(element, [375, 768, 1280])
// Returns: { 375: SkeletonDescriptor, 768: SkeletonDescriptor, 1280: SkeletonDescriptor }
```

**At runtime**, `<Skeleton>` picks the best matching breakpoint:
- If container is 500px wide → uses 375px bones
- If container is 900px wide → uses 768px bones
- If container is 1400px wide → uses 1024px (or highest available)

**Source evidence**: `/packages/boneyard/src/responsive.ts` lines 39–82 define `extractResponsive()`. Default breakpoints are declared on line 5. Line 60 resizes container: `container.style.width = \`${targetWidth}px\``. Lines 62–72 extract and store results per breakpoint.

### 5. Layout Computation for SSR

**Mechanism**: The `computeLayout()` function takes a `SkeletonDescriptor` (structure, text, dimensions) and a container width, then computes pixel-perfect bone positions using the `@chenglou/pretext` library for text measurement.

**Use case**: Pre-compute bones at build time without a DOM or browser.

**Example**:
```typescript
import { computeLayout, renderBones } from 'boneyard-js'

const descriptor = {
  display: 'flex', flexDirection: 'column', padding: 16, gap: 12,
  children: [
    { aspectRatio: 16/9 },
    { text: 'Title', font: '700 18px Inter', lineHeight: 24 },
    { height: 44, borderRadius: 8 },
  ]
}

const bones = computeLayout(descriptor, 320)  // No DOM needed
const html = renderBones(bones)  // Render to HTML string
```

**Components**:
- `computeLayout()` — accepts SkeletonDescriptor, applies padding/margin/gap, measures text via pretext, returns SkeletonResult with bone positions
- `renderBones()` — converts SkeletonResult to HTML `<div>` elements with inline styles and optional CSS keyframes

**Source evidence**: `/packages/boneyard/src/layout.ts` lines 1–100 define `computeLayout()`. Line 11 imports pretext: `import { prepare, layout as pretextLayout } from '@chenglou/pretext'`. The function recursively layouts nodes (lines 54–96), applying padding, margin, gap, and flex layout. Text measurement uses pretext (inferred from imports, not visible in excerpt).

---

## Technical Architecture

### Core Components

**Extraction & Snapshot** (`extract.ts`):
- `snapshotBones(element, name, config)` — walks DOM, reads bounding rects, emits bones
- `fromElement(element)` — extracts SkeletonDescriptor (structure, text, spacing) from rendered element
- `snapshotAsLeaf()` — fallback for unsupported layouts (grid, absolute positioning) — captures bounding box and tries to extract children

**React Integration** (`react.tsx`):
- `<Skeleton>` component — conditionally renders skeleton or content
- `registerBones(map)` — populates the in-memory bones registry
- `resolveResponsive(bones, width)` — picks the best breakpoint for current width
- `adjustColor()` — lightens the bone color for the pulse animation

**Layout Engine** (`layout.ts`):
- `computeLayout(descriptor, width)` — recursively applies flex layout, padding, margin, gap; measures text via pretext
- `layoutNode()` — lays out a single node and its children
- `resolveLeafHeight()` — computes height for text, images, form elements

**Types** (`types.ts`):
- `SkeletonDescriptor` — structure describing a component (flexbox layout, spacing, text, dimensions)
- `SkeletonResult` — computed bones for a specific width
- `ResponsiveBones` — map of breakpoints to SkeletonResults
- `Bone` — single rectangular placeholder with position (x, y), dimensions (w, h), border radius (r), and optional container flag (c)
- `SnapshotConfig` — customization for DOM extraction (which tags are leaves, which to exclude, etc.)

**Responsive Capture** (`responsive.ts`):
- `extractResponsive(element, breakpoints)` — captures descriptors at multiple widths by resizing container and calling `fromElement()` at each breakpoint

**HTML Rendering** (`runtime.ts`):
- `renderBones(result, color, animate)` — converts SkeletonResult to HTML string with inline styles and CSS keyframes

### Data Flow

1. **Development build time** (`npx boneyard-js build`):
   - CLI launches Playwright browser
   - Navigates to dev server (e.g., `http://localhost:3000`)
   - Injects `snapshotBones()` into page
   - For each `<Skeleton name="x">`, calls `snapshotBones(element)` at multiple breakpoints
   - Writes `src/bones/{name}.bones.json` per skeleton
   - Generates `src/bones/registry.ts` importing all bones

2. **App initialization** (once):
   - Import `import './bones/registry'` in app entry point
   - `registry.ts` calls `registerBones(bonesMap)`, populating the in-memory Map

3. **Runtime** (every render):
   - `<Skeleton name="blog-card" loading={isLoading}>` checks `bonesRegistry.get('blog-card')`
   - If bones exist and `loading=true`, renders gray rectangles with pulse animation
   - If `loading=false`, renders real children
   - `ResizeObserver` tracks container width; if bones are responsive, picks the matching breakpoint

### Extension Points

**Snapshot Configuration** via `SnapshotConfig`:
- `leafTags` — add custom tags to always be treated as atomic bones (default: `['p', 'h1'–'h6', 'li', 'tr']`)
- `excludeTags` — skip entire elements (e.g., `['nav', 'footer']`)
- `excludeSelectors` — skip elements matching CSS selectors (e.g., `['.icon', '[data-no-skeleton]']`)
- `captureRoundedBorders` — include containers with visible rounded borders even if background is white (default: true)

Pass via:
```tsx
<Skeleton snapshotConfig={{ excludeTags: ['nav'], excludeSelectors: ['.icon'] }}>
  <MyComponent />
</Skeleton>
```

**Color Customization**:
- `color` — bone color in light mode (default: `'rgba(0,0,0,0.08)'`)
- `darkColor` — bone color in dark mode (default: `'rgba(255,255,255,0.06)'`)
- `animate` — enable/disable pulse animation (default: true)

**Manual Bone Supply** via `initialBones` prop:
```tsx
import bones from './src/bones/blog-card.bones.json'
<Skeleton loading={isLoading} initialBones={bones}>
  <BlogCard />
</Skeleton>
```

---

## Installation & Usage

### Install

```bash
npm install boneyard-js
# or
pnpm add boneyard-js
# or
yarn add boneyard-js
```

**Peer dependency**: React >=18 (optional — boneyard works in non-React contexts too, but the `<Skeleton>` component requires React).

### Quick Start (React)

**1. Wrap your component**:

```tsx
import { Skeleton } from 'boneyard-js/react'

export function BlogPost({ slug, isLoading }) {
  const { data, isLoading } = useFetch(`/api/posts/${slug}`)

  return (
    <Skeleton name="blog-post" loading={isLoading}>
      <article>
        <h1>{data.title}</h1>
        <p>{data.content}</p>
      </article>
    </Skeleton>
  )
}
```

**2. Generate bones** (one-time dev command):

```bash
npx boneyard-js build
# or with explicit server:
npx boneyard-js build http://localhost:3000
# or with custom breakpoints:
npx boneyard-js build --breakpoints 390,820,1440
```

The CLI writes:
- `src/bones/blog-post.bones.json` — responsive bones at breakpoints
- `src/bones/registry.ts` — auto-generated registry

**3. Import registry once** in your app entry:

```tsx
// app/layout.tsx or _app.tsx
import './bones/registry'

export default function RootLayout({ children }) {
  return <html>{children}</html>
}
```

**4. Done** — every `<Skeleton name="...">` auto-resolves.

### Non-React Usage

**Snapshot bones in browser console**:

```typescript
import { snapshotBones } from 'boneyard-js'

const el = document.querySelector('.card')
const bones = snapshotBones(el, 'my-card')
console.log(JSON.stringify(bones, null, 2))
// Copy-paste into my-card.bones.json
```

**Render to HTML**:

```typescript
import { renderBones } from 'boneyard-js'

const html = renderBones(bones, '#e0e0e0', true)
document.getElementById('placeholder').innerHTML = html
```

**SSR / build-time** (no DOM):

```typescript
import { computeLayout, renderBones } from 'boneyard-js'

const descriptor = {
  display: 'flex', flexDirection: 'column', gap: 12,
  children: [
    { text: 'Title', font: '700 18px Inter', lineHeight: 24 },
    { height: 200, aspectRatio: 16/9 },
  ]
}

const bones = computeLayout(descriptor, 320)
const html = renderBones(bones)
```

---

## Limitations and Caveats

### Documented Limitations

None explicitly documented in repository README or inline source comments beyond normal assumptions.

### Inferred Limitations (Not Documented)

1. **Grid and absolute positioning**: Elements with `display: grid`, `display: inline-grid`, or `position: absolute/fixed` are captured as fixed-size "leaf" containers rather than having their layout recomputed. This means grid items are not individually represented — the entire grid is a single bone. (Source: `/packages/boneyard/src/extract.ts` lines 122–127 in `extractNode()`)

2. **Pretext dependency for text measurement**: The layout engine (`computeLayout()`) relies on the optional `@chenglou/pretext` library for measuring text. If pretext is not installed or the font is not available, text height computation may be inaccurate. (Source: `/packages/boneyard/src/layout.ts` line 11 imports pretext)

3. **Browser environment assumption**: `snapshotBones()` and `extractResponsive()` require a live DOM and `getBoundingClientRect()` — they cannot run in Node.js. The `computeLayout()` path is DOM-free but requires a hand-authored `SkeletonDescriptor`. (Source: `/packages/boneyard/src/extract.ts` lines 13–14 call `element.getBoundingClientRect()` directly)

4. **Responsive capture overhead**: Calling `extractResponsive()` resizes the container multiple times and forces layout recalcs — expensive in large documents. The default is 3 breakpoints; scaling to many breakpoints may be slow. (Source: `/packages/boneyard/src/responsive.ts` lines 54–73 resize and force recalc per breakpoint)

5. **No animation customization beyond pulse**: The animation is hardcoded to a 1.8-second ease-in-out pulse. Custom animation curves, duration, or easing cannot be configured. (Source: `/packages/boneyard/src/react.tsx` line 223: `animation: animate ? 'boneyard-pulse 1.8s ease-in-out infinite' : undefined`)

---

## Relevance to Claude Code Development

Boneyard is relevant to Claude Code in the following scenarios:

1. **Building AI-powered UI automation tools**: Claude Code agents that interact with web UIs can use Boneyard to extract layout structure from components, enabling precise element positioning and interaction prediction.

2. **Generating test fixtures and mocks**: Agents generating test code or component stubs can use `snapshotBones()` to capture real layout data, then generate mock implementations that preserve the layout exactly.

3. **AI-assisted UI refactoring**: When Claude Code agents refactor React components, they can compare `SkeletonDescriptor` outputs before and after to verify layout changes preserve structure and spacing.

4. **Skeleton screen generation in agent-generated apps**: If Claude Code generates a new React app, agents could run `npx boneyard-js build` as part of the build pipeline to automatically generate loading screens without manual placeholders.

5. **Zero-CLS monitoring in performance-critical agents**: For agents building performance-optimized applications, Boneyard ensures layout shift is eliminated, which is measurable and verifiable in e2e tests.

---

## References

- **GitHub Repository**: <https://github.com/0xGF/boneyard> (accessed 2026-04-03)
  - `/packages/boneyard/src/extract.ts` — DOM snapshot extraction, leaf detection
  - `/packages/boneyard/src/react.tsx` — React component, responsive selection, dark mode
  - `/packages/boneyard/src/layout.ts` — layout computation, text measurement integration
  - `/packages/boneyard/src/types.ts` — type definitions (Bone, SkeletonDescriptor, ResponsiveBones)
  - `/packages/boneyard/src/responsive.ts` — multi-breakpoint extraction
  - `/packages/boneyard/src/runtime.ts` — HTML rendering
  - `package.json` — metadata, version 1.5.0 (local clone), dependencies
  - `LICENSE` — MIT license
  - `README.md` — feature overview, installation, props table, CLI reference
- **NPM Registry**: <https://registry.npmjs.org/boneyard-js> (accessed 2026-04-03)
  - Package name: `boneyard-js`
  - Latest version: 1.5.1
  - License: MIT
  - Description: "Pixel-perfect skeleton loading screens. Wrap your component in <Skeleton> and boneyard snapshots the real DOM layout — no manual descriptors, no configuration."

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Pretext](./pretext.md) | developer-tools | Provides the text measurement library (`@chenglou/pretext`) that Boneyard uses for computing layout dimensions without DOM reflow |
| [Anime.js](./animejs.md) | developer-tools | Complements skeleton screen rendering with chainable animation API; Boneyard's pulse animation uses keyframes, Anime.js provides programmatic control alternative |
| [Gridland](./gridland.md) | developer-tools | Shares multi-environment rendering challenge: responsive layout snapshot extraction at multiple breakpoints mirrors Gridland's write-once-deploy-anywhere rendering strategy |
| [UI UX Pro Max Skill](../ai-design-tools/ui-ux-pro-max-skill.md) | ai-design-tools | Provides design system and color palette guidance for skeleton screen customization and dark mode theme selection |
| [CopilotKit](../agent-frameworks/copilotkit.md) | agent-frameworks | React-first framework with bi-directional state sync; skeleton screens complement Copilot UI for loading state visualization during agent operations |

---

## Freshness Tracking

**Last researched**: 2026-04-03
**Next review**: 2026-07-03

### Confidence Summary

| Section | Confidence | Notes |
|---------|------------|-------|
| Identity/Metadata | high | npm registry and local package.json read in full; version, license, description confirmed |
| Key Features | high | All features extracted from source code with exact line references; algorithms traced through implementation |
| Technical Architecture | high | Core components and data flow reverse-engineered from source; types and function signatures exact |
| Installation & Usage | high | Examples extracted from README and official source code; commands and patterns verified |
| Limitations | medium | Documented limitations are minimal; inferred limitations based on code inspection (not explicitly stated in docs) |
| Relevance to Claude Code | medium | Use cases are plausible but not validated against actual Claude Code workflows; relevance is inferred from feature set |

### Data Changes Since Last Research

N/A — first research entry.

---

**Research completed by Research Curator Agent**
**Methodology**: Shallow repository clone, Phase 1 extractive read (README, package.json, core source files), no Phase 1b code analysis required (doc sufficiency check passed: features and architecture named with specific components and data flow).
