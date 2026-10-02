---
name: jakubkrehel-skills
title: Jakub Krehel Interface Skills Collection
subtitle: Agent skills for interface design, typography, colors, accessibility, and UI polish
research_date: 2026-10-02
source_url: https://github.com/jakubkrehel/skills
github_repository: https://github.com/jakubkrehel/skills
version_at_research: 1.6.3
license: MIT
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 1.6.3
  next_review: 2027-01-02
  confidence_map: "Overview: high | Features: high | Architecture: high | Usage: high | Limitations: medium"
---

# Jakub Krehel Interface Skills Collection

## Overview

A distributed collection of specialized agent skills for building product interfaces, covering typography, colors, layout, accessibility, UI polish, and product writing. Published as both an npm package (`npx skills add jakubkrehel/skills`) and a Claude Code plugin (`interfaces`). All content is documentation-only with no build, lint, or test tooling. The collection provides multi-domain review orchestration, design exploration via variant testing, component stress testing, and evidence-first review criteria that rank findings by user impact rather than taste.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Interface reviews lack systematic, domain-specific criteria | Multi-skill orchestration (`better-interface`) routes review across accessibility, layout, writing, typography, color, and UI polish, consolidates findings, and ranks by user impact |
| Design explorers need structured comparison of alternatives across design axes | `variant` skill builds multiple design solutions on a single axis (structure, density, emphasis, type, voice) and presents tradeoffs without claiming a winner |
| Components fail under realistic stress testing | `break` skill renders a component in every scenario it accepts, observes what visibly broke, and routes fixes to the owning domain skill |
| Interface code lacks inspection tools for understanding how UI was built | `explain-interface` analyzes existing interfaces to extract the mechanism and measured behavior underlying them |
| Reviewers apply taste instead of evidence | All skills emphasize evidence-backed findings with specific citations; escalation triggers (e.g., "interactive control with no accessible name") override stylistic preferences |

---

## Key Features

### Multi-Domain Review Orchestration

- `better-interface` combines all domain skills in order: accessibility → layout → writing → typography → colors → UI polish
- Consolidates evidence across domains, ranks findings by user impact, caps report at 15 findings
- Escalation triggers (accessibility failures, keyboard reachability, contrast, reduced-motion, content clipping, destructive actions without confirmation) rank HIGH severity immediately
- Shared severity scale: HIGH (blocks task, misleads user, hides content, causes data loss, repeated systemic failure), MEDIUM (harms comprehension/efficiency/adaptability/consistency), LOW (isolated polish)

### Domain Skills Covering Product Interface

- `better-accessibility`: semantic HTML, keyboard/focus behavior, accessible names, assistive technology, accessibility requirements
- `better-layout`: spatial grouping, alignment, spacing, responsive structure, logical CSS, RTL behavior
- `better-writing`: copy wording, terminology, voice, tone, labels, errors, empty states
- `better-typography`: text rendering, type systems, font behavior, wrapping, punctuation, text-level bidi
- `better-colors`: palette structure, color token naming, gamut, contrast measurement, remediation
- `better-ui`: concentric border radius, optical alignment, surfaces, icons, motion (enter/exit animations, icon animations, scale on press)

### Design Variant Exploration

- `variant` builds 3-5 design candidates that differ on a single primary axis (structure, density, emphasis, type, or voice)
- Renders variants behind a URL-based picker (`?variant=quiet`) on the real page with real content and tokens
- Each variant must clear `better-interface`'s escalation triggers before promotion
- Presents measured tradeoffs, hands decision to the user, then promotes one variant into production

### Component Stress Testing

- `break` renders a component in every scenario it accepts (content length, states, container widths)
- Runs one load, one look in a browser; observes and reports what visibly broke
- Finds owner domain skill for each break, routed to the right fix workflow
- Destroys throwaway test harness after findings are reported

### Specialized Review Entry Points

- `interface-review`: change-scoped review (branches, PRs, uncommitted work) that classifies findings as Introduced/Regression/Pre-existing
- `explain-interface`: reads an interface from URL or screenshot, traces mechanism and measured behavior, names the design pattern and technique
- `better-interface`: full-interface review across all domains

### Practical Design Guidance

Each domain skill carries exact values, not ranges: "scale 0.96 on press" (not below 0.95), "cubic-bezier(0.2, 0, 0, 1)" for icon animations, "outer radius = inner radius + padding" for concentric borders, "1.5px stroke beside regular text weight, 2px beside semibold"

---

## Technical Architecture

### Skill Structure and Ownership Model

Each skill owns specific rules. Rule ownership prevents duplication:

- `better-interface` owns review orchestration, shared severity, escalation triggers, finding cap, verdict
- `interface-review` owns change scope resolution, blast radius, finding classification (Introduced/Regression/Pre-existing)
- Each domain skill (`better-accessibility`, `better-layout`, `better-writing`, `better-typography`, `better-colors`, `better-ui`) owns its domain's principles, severity definitions (for standalone review), and verification checks
- `variant` owns design exploration: axis selection, tradeoff presentation, promotion
- `break` owns component stress testing: scenario selection, visual observation, breakage reporting
- `explain-interface` owns interface reading: mechanism extraction, measured behavior analysis

### Invocation Model

- **User-invoked skills** (cannot reach other user-invoked skills): `interface-review`, `variant`, `break`, `explain-interface`
- **Model-invoked skills** (reached by other skills): `better-interface`, all `better-*` domain skills
- `better-interface` routes to every available domain skill in order; if a domain skill is unavailable, marks that domain "Not reviewed" and continues

### Supporting References

Each skill links to supporting `.md` files for depth beyond principles:

- `better-ui/surfaces.md`: radius, shadow, outline recipes
- `better-ui/enter-exit.md`: entrance animation stagger guidance
- `better-ui/animations.md`: keyframe vs transition use; icon animation techniques; theme-switch suppression
- `better-ui/icons.md`: icon sizing, stroke weights, RTL behavior
- `better-ui/performance.md`: will-change usage
- `better-colors/palette-construction.md`: palette building recipes
- `better-typography/type-scale.md`: type system design
- `variant/picker.md`: URL picker implementation
- `break/scenarios.md`: scenario axes and applicability cues
- `interface-review/scope-resolution.md`: scope detection for branches, PRs, uncommitted changes
- `interface-review/removed-signals.md`: interface reading signals no longer present in removed code

### Distribution and Plugin Manifest

Published via two channels:

1. **npm `skills` CLI**: `npx skills add jakubkrehel/skills`
2. **Claude Code plugin marketplace**: `.claude-plugin/plugin.json` (name: "interfaces", version: 1.6.3) published to marketplace via `.claude-plugin/marketplace.json`

Both entry points discover skills from `skills/` directory automatically; no manifest declaration needed per skill. Skill availability resolves at install time; unavailable skills do not block the review.

---

## Installation & Usage

### NPM Skills CLI

```bash
npx skills add jakubkrehel/skills
```

Skill invocation: `/better-interface`, `/variant`, `/break` (each user-invoked skill on its own)

### Claude Code Plugin

```text
/plugin marketplace add jakubkrehel/skills
/plugin install interfaces@interfaces
```

Skill invocation: `/interfaces:better-interface`, `/interfaces:variant`, `/interfaces:break` (plugin-namespaced)

### Standalone Usage Example

Request an interface review across a screenshot or live page:

```text
/better-interface
[Provide scope: screenshot, page URL, or "the dashboard on [branch]"]
```

The skill resolves scope, reads the project's conventions from contributing/design docs, identifies framework and tokens, then routes to each domain skill in order and consolidates the verdict.

---

## Relevance to Claude Code Development

### Applications

- **Skill dispatch and orchestration** → `plugins/agent-orchestration/skills/delegate/SKILL.md`
  - Term: `orchestrat`
  - Today: "The orchestrator's context is the one window that lasts the whole session. Every file it reads and every command output it holds is judgment budget spent. Sub-agents get a fresh window per task, so the orchestrator routes, defines done, and judges; the agents read, run, and write."
  - Change: none — the delegate skill implements orchestration patterns (phase decomposition, dispatch, adjudication) that mirror `better-interface`'s multi-domain skill routing and consolidation

- **Plugin distribution and marketplace registration** → `.claude-plugin/marketplace.json`
  - Term: `marketplace`
  - Today: The marketplace.json file at the repository root registers plugins and their sources, allowing installation via `/plugin marketplace add` or `npx skills add` — a mechanism the jakubkrehel/skills repository itself uses
  - Change: none — marketplace distribution and dual-channel publishing (npm + Claude Code) are already patterns in this repository

### Patterns Worth Adopting

- **Design decisions and pattern documentation** → `.claude/agents/code-review.md`
  - Term: `design.*pattern\|design.*decision`
  - Today: "Your job is to catch bugs and security issues, not to redesign the architecture. Respect the project's existing patterns and decisions."
  - Change: none — the code-review agent's principle (respect existing patterns, focus on correctness within context) mirrors jakubkrehel/skills' separation of concerns: `better-interface` routes to domain experts, each domain enforces its own rules, neither overrides deliberate project choices

- **Evidence-first review criteria** → `rules/fact-verification-first.md`
  - Term: `evidence`
  - Today: Rule requires verification against primary sources rather than inference, matching the jakubkrehel design reviews' escalation-trigger approach
  - Change: none — the fact-verification-first rule carries the same principle; the design review's escalation triggers are a realization of it in a different domain

### Integration Opportunities

- **Component quality gates and stress testing** → `plugins/development-harness/skills/review-verdict-contract/SKILL.md`
  - Term: `component.*gate`
  - Today: "Load the shared verdict, punch-list, SKIP, and gate schema used by the dh multi-perspective review orchestrator, reviewers, and synthesizer."
  - Change: the dh review verdict schema gates component quality across reviewers; extending this with component stress-test routing (similar to `break`'s scenario exploration) would catch visual and behavioral breaks before code review

- **Robustness validation through stress testing** → `plugins/agentskill-kaizen/references/arl-ARL-agent-instructions.md`
  - Term: `stress.*test`
  - Today: "After synthesis is written, this phase stress-tests the work for scientific rigor."
  - Change: integrate component stress-test results (from a `break`-like skill) into the ARL's synthesis validation phase, where robustness can be verified as part of work output quality gates

---

## References

- [Repository README](https://github.com/jakubkrehel/skills/blob/main/README.md) (accessed 2026-10-02)
- [AGENTS.md — Repository working guide](https://github.com/jakubkrehel/skills/blob/main/AGENTS.md) (accessed 2026-10-02)
- [Plugin Manifest (.claude-plugin/plugin.json)](https://github.com/jakubkrehel/skills/blob/main/.claude-plugin/plugin.json) (accessed 2026-10-02)
- [Marketplace Registration (.claude-plugin/marketplace.json)](https://github.com/jakubkrehel/skills/blob/main/.claude-plugin/marketplace.json) (accessed 2026-10-02)
- [better-interface SKILL.md](https://github.com/jakubkrehel/skills/blob/main/skills/better-interface/SKILL.md) (accessed 2026-10-02)
- [better-ui SKILL.md](https://github.com/jakubkrehel/skills/blob/main/skills/better-ui/SKILL.md) (accessed 2026-10-02)
- [variant SKILL.md](https://github.com/jakubkrehel/skills/blob/main/skills/variant/SKILL.md) (accessed 2026-10-02)
- [break SKILL.md](https://github.com/jakubkrehel/skills/blob/main/skills/break/SKILL.md) (accessed 2026-10-02)
- [interfaces.dev — Jakub Krehel's design magazine](https://interfaces.dev/) (accessed 2026-10-02)
- [jakub.kr/ — Personal website](https://jakub.kr/) (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Pilot](./claude-pilot.md) | developer-tools | Quality-enforcement layer with systematic testing and code review; shares TDD enforcement and multi-phase verification approach with jakubkrehel's evidence-first review methodology |
| [Everything Claude Code](./everything-claude-code.md) | developer-tools | Comprehensive agent harness with 65+ specialized skills and quality gates; parallels jakubkrehel's multi-domain orchestration and agent skill ecosystem |
| [Claude Conductor](./claude-conductor.md) | developer-tools | Context-driven development plugin for Claude Code; shares design-context awareness with jakubkrehel's context-sensitive interface review |
| [mattpocock/skills](../skill-generation-tools/mattpocock-skills.md) | skill-generation-tools | Interface design and TDD skills with deep module patterns; shares systematic approach to design decisions and evidence-based quality criteria |
| [Compound Engineering Plugin](../skill-generation-tools/compound-engineering-plugin.md) | skill-generation-tools | Planning-first workflow plugin with multi-skill orchestration (plan/work/review/compound); parallels jakubkrehel's domain-specific skill routing architecture |
| [Claude Code Skills Library](../skill-generation-tools/claude-code-skills-alirezarezvani.md) | skill-generation-tools | 362 modular skill packages across 18 domains; shares distributed skill ecosystem architecture and domain-specific review pattern |
