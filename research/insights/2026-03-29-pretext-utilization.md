# Utilization Proposals: Pretext

**Research entry**: ./research/developer-tools/pretext.md
**Generated**: 2026-03-29
**Integration surfaces found**: 1 (npm package + TypeScript API)
**Proposals written**: 0
**Skipped**: 1 — no current layout constraints requiring text measurement optimization

---

## Surface Analysis

Pretext documents a callable integration surface:

- **npm package**: `@chenglou/pretext` (v0.0.3)
- **Installation**: `npm install @chenglou/pretext` or `bun add @chenglou/pretext`
- **API**: TypeScript functions — `prepare(text, font, options)`, `layout(prepared, maxWidth, lineHeight)`, `layoutWithLines()`, `layoutNextLine()`, `walkLineRanges()`
- **Use case**: Text measurement and layout without DOM reflows; supports dynamic sizing, virtualization, and custom rendering

---

## Candidate Local Systems Assessed

### 1. dot-dash/frontend (plugins/dot-dash/frontend/)

**System type**: React + TypeScript frontend application

**Current text rendering pattern**:
- Transcript component (Transcript.tsx) renders dynamic chat messages with standard CSS layout
- Uses `scrollIntoView({ behavior: 'smooth' })` for scroll anchoring on new events (line 26)
- DOM rendering is simple: `message-text` divs with user/assistant messages wrapped in flexbox
- No custom canvas or SVG rendering
- No virtualization of transcript (all messages in DOM)

**Read assessment**:
- Text layout concerns: NOT present
- Layout reflow risk: NOT present (simple CSS, no repeated measurements during render)
- Scroll precision requirement: NOT present (uses browser's `scrollIntoView`, not sub-pixel scroll restoration)
- Virtualization opportunity: NOT pressing (typical session transcripts are 50-200 messages, not 1000+)

**Why this caller was skipped**:
Pretext solves three problems:
1. **Elimination of layout reflow** — when measuring text height repeatedly via DOM (`getBoundingClientRect`, `offsetHeight`)
2. **Virtualization support** — when rendering long lists where per-item height prediction is expensive
3. **Custom rendering** — when flowing text to canvas, SVG, or server-side targets

The dot-dash frontend exhibits none of these constraints:
- Text measurement is not a performance bottleneck (no per-message measurements during render)
- Transcript size is manageable without virtualization (typical 50-200 messages)
- Rendering target is DOM only (CSS flexbox, no canvas or SVG)

Integration would optimize a non-bottleneck. The cost (dependency addition, API surface complexity, testing) exceeds the current benefit.

**Future integration trigger**: If the app scales to support 10,000+ event transcripts OR implements canvas-based rendering for performance, revisit this analysis. At that point, Pretext would enable:
- Precise scroll position restoration without reflows
- Fast virtualization via cached segment widths
- Custom rendering to canvas for high-performance dense transcripts

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/agents/*.md` | Agents are Python documentation files; Pretext is a JavaScript library for browsers. No call surface. |
| `.claude/skills/*.md` | Skills are workflow documentation; Pretext is a browser text layout library. No call surface. |
| `plugins/*/hooks/hooks.json` | Hooks are CLI/lifecycle automation; Pretext is a browser text measurement library. Different runtimes (Node.js/CLI vs browser). |
| `package.json` (root) | Root project is Python-based tooling (uv, pre-commit, linting). Pretext is a browser library. No integration path. |

---

## Recommendation

**Status**: No utilization opportunity at this time.

Pretext is high-quality software with excellent browser compatibility and performance characteristics. However, the Claude Code repository's current architecture does not have a layout measurement problem that Pretext solves.

**Conditions for future re-assessment**:
- Transcript component scaled to 10,000+ events (virtualization becomes necessary)
- dot-dash frontend implements canvas-based rendering
- New frontend component introduced requiring precise multiline text layout (labels, tooltips, data visualization)

**How to proceed**: Bookmark this research entry for future reference. When a new frontend feature requires text layout optimization, reference the Pretext surface documented here.
