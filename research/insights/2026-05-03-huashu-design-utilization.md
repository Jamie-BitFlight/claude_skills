# Utilization Proposals: Huashu Design

**Research entry**: ./research/ai-design-tools/huashu-design.md
**Generated**: 2026-05-03
**Integration surfaces found**: 2 (NPM skill + CLI toolchain)
**Proposals written**: 2
**Skipped**: 1 — see below

---

## Utilization 1: /prepare-walkthrough-presentation → Huashu Design (Deck Export)

**Research entry**: ./research/ai-design-tools/huashu-design.md
**Caller**: ./.claude/skills/prepare-walkthrough-presentation/SKILL.md
**Integration mechanism**: Subprocess call to Huashu's export toolchain (`scripts/export_deck_pptx.mjs`)
**Replaces or adds**: Converts markdown deck outlines to native PPTX with editable text frames (currently missing — outlines stay as markdown)
**Setup cost**: Low (npm dependency, one export script call per deck)
**Integration surface**: `npx skills add alchaincyf/huashu-design` + `scripts/export_deck_pptx.mjs` for PPTX export

### Why this caller

The `/prepare-walkthrough-presentation` skill produces structured deck outlines as markdown files in `presentation/decks/` (Phase 4, deliverable in SKILL.md line 141). These outlines contain slide-by-slide narrative, speaker notes, and visual suggestions—the raw material for a presentation. Currently, these artifacts remain as markdown: the user must manually transcribe content into PowerPoint or Keynote to produce a deliverable deck.

Huashu Design's PPTX export mechanism (documented in research entry §Key Features §Slide Decks) reads DOM-computed styles and translates HTML elements into native PowerPoint objects with **editable text frames**—not rasterized images. The research entry explicitly states (line 52): "Output exports as **actual text frames**, not image-bed fakes. Enables downstream editing in PowerPoint without rasterization."

Integrating Huashu would close this gap: convert markdown deck outlines to styled HTML (Huashu can do this conversationally), then export to PPTX using `html2pptx.js`. Result: presentation-ready PPTX with real text frames, ready for speaker notes and client feedback, without manual transcription.

### Integration sketch

**Phase 4.5 (new): Deck Export** — added after Phase 4 Packaging completes.

```text
Orchestrator reads: presentation/decks/ (all finalized deck outlines from Phase 4)

For each deck outline:
  1. Call Huashu Design (as a subprocess or spawned agent task):
     Input: markdown deck outline from presentation/decks/component-deck-outline-{name}.md
     Task: "Convert this markdown deck outline to HTML using Huashu's slide deck engine, apply brand colors from brand-spec.md if available, export to PPTX"

  2. Huashu processes:
     - Reads markdown structure (headings, speaker notes, visual suggestions)
     - Generates HTML slide deck using deck_stage.js + slide structure
     - Applies brand colors via CSS variables (from brand-spec.md if present)
     - Calls html2pptx.js to export to native PPTX with editable text frames

  3. Output: presentation/decks/component-deck-{name}.pptx (native, text-frame editable)

Orchestrator verifies: .pptx files exist, one per markdown deck
```

**Prerequisite**: Huashu Design skill must be installed (`npx skills add alchaincyf/huashu-design`). Brand spec optional (SKILL.md can provide brand assets from walkthrough context if available).

---

## Utilization 2: /design-anti-patterns → Huashu Design (Brand-Enforced UI Generation)

**Research entry**: ./research/ai-design-tools/huashu-design.md
**Caller**: ./.claude/skills/design-anti-patterns/SKILL.md
**Integration mechanism**: Skill invocation (conversational prompt delegation + subprocess)
**Replaces or adds**: Adds ability to generate production-grade interactive prototypes from anti-pattern rules (currently missing — rules are enforcement only, no generation)
**Setup cost**: Low (skill installation, one prompt template in anti-patterns reference)
**Integration surface**: `npx skills add alchaincyf/huashu-design` + Huashu's Interactive App & Web Prototypes (research entry §Key Features)

### Why this caller

The `/design-anti-patterns` skill (SKILL.md lines 1–76) enforces the Uncodixfy UI design methodology: a metacognitive check that prevents "AI slop" patterns (glassmorphism, fake gradients, oversized rounded corners, decorative copy). The skill achieves this through a **pre-flight check** (lines 14–19) and a **banned patterns list** (lines 24–44), followed by **normal standards** for each component (lines 51–61).

What the skill does NOT do: generate UI code from scratch. It constrains existing generation, but leaves the generator to the agent. The research entry for design-anti-patterns does not mention (and would not include) generation capability—it is purely preventive.

Huashu Design's core strength is **conversational UI generation**. The research entry documents (line 15): "produces high-fidelity design deliverables from natural language prompts…in 3–30 minutes: interactive prototypes, slide decks, motion graphics, infographics, and design direction explorations." The Anti-AI-Slop Design Rules section (lines 69–74) explicitly lists the same principles Uncodixfy enforces: avoid purple gradients, emoji icons, rounded-corner accents, SVG humans, Inter-as-display, CSS silhouettes. Instead, use `text-wrap: pretty`, CSS Grid, carefully chosen serif display faces, oklch colors.

Integration would pair the constraint framework (anti-patterns) with the generation engine (Huashu): agents generating UI components for Claude Code-based tools could invoke Huashu with the anti-pattern rules embedded in the prompt, receive single-file HTML/React prototypes that are production-ready and rule-compliant, and iterate on brand fit using Huashu's Design Variation Parameterization (research entry line 179).

### Integration sketch

**New section in design-anti-patterns skill**: "Generation with Huashu Design"

```text
When generating a UI component from scratch (not reviewing existing code):

1. Invoke /huashu-design as a sub-skill
   Input prompt structure:
   - Component description (what should it do, what does it show)
   - Anti-pattern constraints (see /design-anti-patterns)
   - Brand context: colors, fonts, logo (from brand-spec.md if available)
   - Output format: "single-file HTML with real images (Unsplash/Wikimedia), state-driven navigation, Playwright-verified interactivity"

2. Huashu generates:
   - React component in single HTML file
   - Applies oklch colors (not gradients), CSS Grid layout, serif display faces
   - Embeds real images (not AI-generated)
   - State-driven navigation verified by Playwright

3. Output: {component-name}.html — ready for user testing, no design review loop needed

4. If iteration needed:
   - Use Huashu's Tweaks panel (design_canvas.jsx)
   - Toggle live parameters, user selects refined direction
   - Export final version
```

**Prerequisite**: Huashu Design skill installed. Brand spec recommended (speeds up color/font decisions). First invocation includes Core Asset Protocol steps (lines 86–95 of research entry).

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| /cove-prompt-design | Skill documents Chain of Verification for prompt design (factual accuracy, hallucination reduction). Huashu Design is a UI/design generation tool, not a prompt verification pattern. No integration surface — different problem domains. |

---

## Summary

Two integration opportunities identified where Huashu Design's documented surfaces (skill installation, deck export, UI prototyping, brand asset protocol) directly address gaps in existing local systems:

1. **prepare-walkthrough-presentation**: Huashu closes the gap between markdown deck outlines and deliverable PPTX with native text frames.
2. **design-anti-patterns**: Huashu pairs constraint rules with production-grade UI generation, enabling one-pass anti-pattern-compliant component design.

Both opportunities leverage Huashu's documented export toolchain and brand-aware generation, require minimal setup (npm install + one prompt template each), and would materially improve output quality without requiring changes to existing local system design.
