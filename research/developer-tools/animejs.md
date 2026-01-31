# Anime.js - JavaScript Animation Engine

**Research Date**: January 31, 2026
**Source URL**: <https://animejs.com>
**GitHub Repository**: <https://github.com/juliangarnier/anime>
**Documentation**: <https://animejs.com/documentation>
**npm Package**: <https://www.npmjs.com/package/animejs>
**Version at Research**: v4.3.5
**License**: MIT

---

## Overview

Anime.js is a fast, multipurpose, and lightweight JavaScript animation library with a simple yet powerful API. It works with CSS properties, SVG, DOM attributes, and JavaScript Objects. Version 4 introduces a complete API redesign with ES module imports, improved timeline controls, and enhanced performance.

**Core Value Proposition**: Enable declarative, chainable animations with minimal code while supporting complex staggering, timelines, and easing functions across any animatable web property.

---

## Problem Addressed

| Problem                                                     | How Anime.js Solves It                                                        |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------- |
| CSS animations lack programmatic control                    | Full JavaScript API with play, pause, reverse, seek controls                  |
| Complex sequenced animations are hard to manage             | Timeline API with sequential and parallel composition                         |
| Staggered animations require manual delay calculations      | Built-in stagger utility with grid, from-center, and easing options           |
| SVG animations require specialized knowledge                | Native SVG property support including path morphing and motion paths          |
| Animation libraries are often heavyweight                   | ~17KB minified, zero dependencies, tree-shakeable ES modules                  |
| Coordinating animations across multiple elements is complex | Target-based approach with CSS selectors, NodeLists, or JavaScript objects    |
| Easing functions are limited in CSS                         | 30+ built-in easing functions plus custom cubic-bezier and spring physics     |

---

## Key Statistics (as of January 31, 2026)

| Metric              | Value                        |
| ------------------- | ---------------------------- |
| GitHub Stars        | 66,288                       |
| Forks               | 4,435                        |
| Open Issues         | 86                           |
| Primary Language    | JavaScript                   |
| Created             | March 2016                   |
| Latest Release      | v4.3.5 (January 25, 2026)    |
| npm Weekly Downloads| 487,588                      |
| npm Monthly Downloads| 1,477,792                   |
| License             | MIT                          |

---

## Key Features

### 1. ES Module Architecture (v4)

- **Tree-shakeable Imports**: Import only what you need (`animate`, `stagger`, `createTimeline`)
- **Named Exports**: Clean API surface with explicit function imports
- **TypeScript Support**: Full type declarations included

```javascript
import { animate, stagger, createTimeline } from 'animejs';
```

### 2. Target-Based Animation

- **CSS Selectors**: Animate elements matching any valid selector
- **DOM Elements**: Direct element or NodeList references
- **JavaScript Objects**: Animate any numeric object properties
- **Mixed Targets**: Combine different target types in single animation

### 3. Property Animation

- **CSS Properties**: All animatable CSS including transforms, colors, dimensions
- **SVG Attributes**: Native SVG property support (path d, stroke-dasharray, etc.)
- **DOM Attributes**: Any numeric DOM attribute
- **Object Properties**: Arbitrary JavaScript object values

### 4. Stagger System

- **Linear Stagger**: Incremental delays across targets
- **Grid Stagger**: 2D staggering for grid layouts
- **From Options**: Start from first, last, center, or specific index
- **Easing Integration**: Apply easing curves to stagger distribution

```javascript
animate('.item', {
  translateX: 250,
  delay: stagger(100, { from: 'center', ease: 'outQuad' })
});
```

### 5. Timeline API

- **Sequential Composition**: Chain animations with `add()`
- **Parallel Composition**: Overlap animations with offset parameters
- **Nested Timelines**: Compose complex sequences from simpler ones
- **Default Parameters**: Shared properties across all timeline children

```javascript
const tl = createTimeline({ defaults: { duration: 400, ease: 'outQuad' }});
tl.add('.el1', { translateX: 250 })
  .add('.el2', { translateY: 100 }, '-=200');
```

### 6. Playback Controls

- **play() / pause() / resume()**: Standard playback control
- **reverse()**: Play animation backwards
- **seek(time)**: Jump to specific time position
- **restart()**: Reset and play from beginning
- **Playback Rate**: Speed up or slow down animations

### 7. Easing Functions

- **Built-in Easings**: 30+ named easings (linear, quad, cubic, quart, quint, sine, expo, circ, back, elastic, bounce)
- **Directional Variants**: in, out, inOut for each easing type
- **Custom Bezier**: Define custom cubic-bezier curves
- **Spring Physics**: Physics-based spring animations
- **Stepped Easing**: Discrete step transitions

### 8. Callbacks and Promises

- **Event Callbacks**: onBegin, onUpdate, onLoop, onComplete
- **Promise-based**: Async/await support for animation completion
- **Progress Values**: Access current progress in callbacks

---

## Technical Architecture

```text
Application Code
      |
      v
+------------------------------------------+
|           Anime.js Engine                 |
|  +------------------------------------+  |
|  |         Target Resolution          |  |
|  |  - CSS selector parsing            |  |
|  |  - NodeList handling               |  |
|  |  - Object property mapping         |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |         Property Parser            |  |
|  |  - CSS value parsing               |  |
|  |  - Unit conversion                 |  |
|  |  - Color interpolation (RGB/HSL)   |  |
|  |  - Transform decomposition         |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |         Animation Scheduler        |  |
|  |  - requestAnimationFrame loop      |  |
|  |  - Easing calculation              |  |
|  |  - Progress interpolation          |  |
|  |  - Stagger delay management        |  |
|  +------------------------------------+  |
|                   |                       |
|                   v                       |
|  +------------------------------------+  |
|  |         Value Renderer             |  |
|  |  - Style application               |  |
|  |  - SVG attribute updates           |  |
|  |  - Object mutation                 |  |
|  |  - DOM batch updates               |  |
|  +------------------------------------+  |
+------------------------------------------+
      |
      v
Animated DOM / Objects
```

---

## Installation & Usage

### Installation Options

```bash
# npm
npm install animejs

# yarn
yarn add animejs

# pnpm
pnpm add animejs

# CDN (UMD)
<script src="https://cdn.jsdelivr.net/npm/animejs@4/lib/anime.umd.min.js"></script>
```

### Basic Usage (v4)

```javascript
import { animate } from 'animejs';

// Simple animation
animate('.box', {
  translateX: 250,
  rotate: '1turn',
  backgroundColor: '#FF0000',
  duration: 800,
  ease: 'outQuad'
});

// With keyframes
animate('.box', {
  translateX: [
    { to: 100, duration: 500 },
    { to: 250, duration: 500 }
  ],
  rotate: { from: -180, to: 180 },
  ease: 'inOutSine'
});
```

### Stagger Example

```javascript
import { animate, stagger } from 'animejs';

animate('.grid-item', {
  scale: [0, 1],
  opacity: [0, 1],
  delay: stagger(50, { grid: [10, 10], from: 'center' }),
  ease: 'outBack'
});
```

### Timeline Example

```javascript
import { createTimeline } from 'animejs';

const tl = createTimeline({
  defaults: { duration: 750, ease: 'outQuint' }
});

tl.add('.header', { translateY: [-50, 0], opacity: [0, 1] })
  .add('.content', { translateY: [30, 0], opacity: [0, 1] }, '-=500')
  .add('.footer', { translateY: [20, 0], opacity: [0, 1] }, '-=500');
```

### v3 to v4 Migration Key Changes

| v3 Syntax | v4 Syntax |
| --------- | --------- |
| `anime({ targets: 'div', ... })` | `animate('div', { ... })` |
| `easing: 'easeOutQuad'` | `ease: 'outQuad'` |
| `direction: 'alternate'` | `alternate: true` |
| `direction: 'reverse'` | `reversed: true` |
| `anime.timeline()` | `createTimeline()` |
| `endDelay: 1000` | `loopDelay: 1000` |
| `value: 100` | `to: 100` |

---

## Relevance to Claude Code Development

### Direct Applications

1. **AI-Generated Web Applications**: When Claude generates frontend code with animations, anime.js provides a well-documented, declarative API that produces reliable results
2. **Code Example Generation**: The consistent API patterns make it predictable for AI code generation with fewer hallucinations
3. **Documentation-to-Code Pattern**: Anime.js demonstrates excellent API documentation that translates cleanly to working code

### Patterns Worth Adopting

1. **Declarative Configuration**: The object-based parameter pattern (`{ duration: 800, ease: 'outQuad' }`) is highly readable and self-documenting
2. **Composable Building Blocks**: `animate()`, `stagger()`, `createTimeline()` compose naturally - similar to skill composition patterns
3. **Named Easing Functions**: Semantic names like 'outQuad' vs numeric cubic-bezier values improve code readability
4. **From/To Explicit Syntax**: `{ from: 0, to: 100 }` pattern eliminates ambiguity about animation direction
5. **Tree-Shakeable Exports**: ES module pattern that imports only needed functions reduces bundle size

### Integration Opportunities

1. **Frontend Skills**: Could inform a skill for generating animated web components
2. **Code Generation Patterns**: The declarative API style can inspire how Claude structures generated animation code
3. **Documentation Standards**: Anime.js documentation exemplifies API docs that work well for both human and AI consumption

### Key Insight

Anime.js demonstrates that declarative, composable APIs with semantic naming conventions are both human-readable and AI-friendly. The explicit `{ from, to }` pattern and named easings reduce ambiguity, making generated code more reliable. This principle applies to skill and agent API design: explicit, declarative configurations outperform imperative approaches for AI comprehension.

---

## References

1. **Official Website**: <https://animejs.com> (accessed 2026-01-31)
2. **GitHub Repository**: <https://github.com/juliangarnier/anime> (accessed 2026-01-31)
3. **Documentation**: <https://animejs.com/documentation> (accessed 2026-01-31)
4. **npm Package**: <https://www.npmjs.com/package/animejs> (accessed 2026-01-31)
5. **v3 to v4 Migration Guide**: <https://github.com/juliangarnier/anime/wiki/Migrating-from-v3-to-v4> (accessed 2026-01-31)
6. **CodePen Examples**: <https://codepen.io/collection/b392d3a52d6abf5b8d9fda4e4cab61ab/> (accessed 2026-01-31)

---

## Related Tools

| Tool                                                          | Relationship                                           |
| ------------------------------------------------------------- | ------------------------------------------------------ |
| [GSAP](https://greensock.com/gsap/)                           | More feature-rich animation platform (commercial)      |
| [Motion One](https://motion.dev/)                             | Modern alternative with Web Animations API             |
| [Framer Motion](https://www.framer.com/motion/)               | React-specific animation library                       |
| [Popmotion](https://popmotion.io/)                            | Functional animation library                           |
| [Lottie](https://airbnb.design/lottie/)                       | After Effects animation player for web                 |

---

## Freshness Tracking

| Field                        | Value                 |
| ---------------------------- | --------------------- |
| Last Verified                | 2026-01-31            |
| Version at Verification      | v4.3.5                |
| GitHub Stars at Verification | 66,288                |
| npm Weekly Downloads         | 487,588               |
| Next Review Recommended      | 2026-04-30 (3 months) |

**Change Detection Indicators**:

- Monitor npm for new version releases (v4.x active development)
- Check GitHub releases for changelog updates
- Watch for new easing functions or timeline features
- Track browser compatibility updates
- Review documentation for API additions
