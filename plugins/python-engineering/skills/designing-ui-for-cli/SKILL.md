---
name: designing-ui-for-cli
description: "Use before any CLI/TUI display code is written, modified, or audited — runs the 7-stage discipline (Context, Register, Shape brief, Implement, Critique, Audit, Polish) for Typer, Rich, Textual, and Questionary work, grounded in per-project PRODUCT.md and DESIGN.TUI.md/DESIGN.md. Triggers on output formatting, display design, interactive prompts, visual consistency, TUI layout, progress display, dashboard design, design audit, design polish, design critique, shape brief, register decision (brand-cli vs product-cli), and AI-slop checks."
user-invocable: false
---
# CLI UI Design

Before any display or output code is written, the agent runs a 7-stage design discipline rooted in per-project PRODUCT.md, DESIGN.md (base design system — colours, tokens, typography, components), and DESIGN.TUI.md (TUI supplement — inherits from DESIGN.md, adds behavioural rules for output channels, symbols, and interaction). When both are present, load both: DESIGN.md provides the palette; DESIGN.TUI.md provides the terminal-specific contract. The skill governs registration, shape brief, implementation, critique, audit, and polish for any Typer, Rich, Textual, or Questionary surface.

## Setup Gates

The agent MUST satisfy each gate before progressing past it. Check order is top-down.

| Gate | Required check | If fail | Hard Rule |
|---|---|---|---|
| Context | First turn invokes `scripts/load-design-context.py` to load PRODUCT.md, DESIGN.TUI.md, DESIGN.md from project root, `.claude/context/`, or `docs/` | Skip only if context already in conversation history; otherwise run loader | Stage 0 actor |
| Product | PRODUCT.md present, non-empty, no `[TODO]` placeholders, ≥200 chars | Run inline interview using `./references/product-md-schema.md` template, write file with user confirmation, re-run loader, resume original task | PRODUCT.md absence re-entry |
| Shape | Shape brief produced and user-confirmed before any display code is written | Stop. Do not write display code until brief is signed off | Stage 2 sign-off gate |
| Mutation | Any code change to display logic must trace to a confirmed shape brief or recorded follow-up deferral | Reject change. Loop back to Shape | Stage 2 sign-off gate |

## Golden Path — 7 Stages

Stages run in order. Stages 4–6 also act as quality gates on existing UI code when invoked against a target.

| Stage | Trigger | Output | Reference file |
|---|---|---|---|
| 0 — Context | Skill invoked, no PRODUCT/DESIGN context in conversation | JSON from loader, or written PRODUCT.md after interview | `./references/product-md-schema.md`, `./references/design-md-schema.md` |
| 1 — Register | Stage 0 complete, target identified | Bare value `brand-cli` or `product-cli`, recorded against the target | `./references/register-decision.md` |
| 2 — Shape | Register set, Stage 3 not yet started | 10-section shape brief, user-confirmed | `./references/shape-brief-template.md` |
| 3 — Implement | Shape brief confirmed | Display code per the brief | Conditional by library in scope — see Reference Loading Guide §Stage 3 below |
| 4 — Critique | Invoked against any target (any stage) | Two-assessment report: Nielsen /40 score + AI-slop verdict + deterministic detector findings | `./references/critique-checklist.md`, `./references/ai-slop-test.md` |
| 5 — Audit | Invoked against any target | Per-issue P0–P3 severity tags + 5-dimension /20 advisory rating | `./references/audit-checklist.md` |
| 6 — Polish | Audit cleared (no P0); pre-ship check | 22-item checklist with each item checked or explicitly deferred with reason | `./references/polish-checklist.md` |

## Hard Rules

These rules govern stage transitions and gate behaviour. Violations require a recorded deferral.

- **Stage 0 actor** — agent invokes `scripts/load-design-context.py` on the first turn of any UI-touching task. Skip only when PRODUCT.md and DESIGN context are already in conversation history. Loader output JSON is read into context; no further file reads needed.
- **Stage 1 register tie-breaker** — apply the four-step first-match-wins decision rule in `./references/register-decision.md`. Default `product-cli` when nothing matches.
- **Stage 2 sign-off gate** — no display code is written until the shape brief is user-confirmed via AskUserQuestion. A shape run is incomplete until the brief is confirmed. If the user disagrees with any part, return to discovery questions for that part.
- **Stage 4 critique scope** — runs whenever invoked against a target. There is no skip condition for "trivial outputs". After findings, the agent runs AskUserQuestion offering `Top 3 only`, `All issues`, or `Critical only`; recommended actions are filtered by the user's chosen scope.
- **Stage 5 audit hard gate** — any P0 issue blocks ship. Zero P0 issues lets the work pass. Aggregate /20 score remains advisory only — Excellent / Good / Acceptable / Poor / Critical bands do not block. Severity tip: "Would a user contact support about this? If yes, it's at least P1."
- **Stage 6 polish hard gate** — every applicable checklist item must check, OR the unchecked item is explicitly marked "deferred to follow-up" with a recorded reason. No aggregate threshold. Triage rule when polish time is tight: functional issues ship first; cosmetic ones can land in a follow-up.
- **Recovery loop** — when Stage 4 or Stage 5 surfaces issues, the agent applies the per-issue Recommended Actions and re-runs the same gate. There is no "return to Implement" or "return to Shape" transition unless the user requests it.
- **PRODUCT.md absence re-entry** — when PRODUCT.md is missing, empty, or placeholder (`[TODO]` markers, <200 chars), the agent runs an inline interview using `./references/product-md-schema.md` as the question template, writes the file to project root with user confirmation, re-runs `scripts/load-design-context.py`, then resumes the original task. If the original task was Shape or beyond, agent resumes at Shape.
- **Target boundary** — skill activates against a user-supplied or task-named target (file, component, screen, surface). No auto-detection of "UI-touching tasks". The 7-stage workflow runs against the supplied target.

## Reference Loading Guide

Load only the files relevant to libraries in scope and the active stage. Do not pre-load every reference.

### Stage 0 — Context

- `./references/product-md-schema.md` — PRODUCT.md structure (Register, Users, Product Purpose, Brand Personality, Anti-references, Design Principles, Accessibility & Inclusion); interview cadence; visual styling exclusion rule
- `./references/design-md-schema.md` — DESIGN.TUI.md / DESIGN.md structure (Overview, Colors, Typography, Elevation, Components, Do's and Don'ts); token reference syntax; Scan vs Seed mode; Named Rules pattern

### Stage 1 — Register

- `./references/register-decision.md` — brand-cli vs product-cli; first-match-wins priority; permissions and bans per register

### Stage 2 — Shape

- `./references/shape-brief-template.md` — 10-section brief structure; confirmation gate
- `./references/colour-strategy.md` — Restrained / Committed / Full / Drenched levels with TUI mapping
- `./references/theme-decision.md` — scene-sentence method for dark / light / auto / high-contrast
- `./references/ai-slop-test.md` — two-altitude category-reflex check, used during Design Direction selection
- `./references/design-principles.md` — progressive disclosure, density progression, status column rule, scene-sentence rule
- `./references/anti-references.md` — twelve-row match-and-refuse table; check before finalising any colour or visual choice in the brief

### Stage 3 — Implement

Load by library in scope. Detect via pyproject.toml dependencies and imports.

#### When Rich is in scope

- `./references/render-patterns.md` — tables, panels, progress, status, themes, dashboard layout
- `./references/rich-extras.md` — multi-task progress, syntax highlighting, tree displays
- `./references/rich-gaps.md` — pager, console.rule, console.screen, escape(), Table.grid, MofNCompleteColumn

#### When Questionary is in scope

- `./references/questionary-patterns.md` — prompt types, Style, Choice, validation
- `./references/questionary-advanced.md` — form(), unsafe_ask, conditional prompts, password / path / rawselect

#### When Textual is in scope (load all — Textual requires the full picture)

- `./references/textual-basics.md` — App structure, reactive, querying, events
- `./references/textual-interactivity.md` — key bindings, mouse, focus, custom messages, actions
- `./references/textual-layout.md` — layout types, sizing, docking, scrolling
- `./references/textual-styling.md` — CSS selectors, colours, borders, pseudo-classes
- `./references/textual-widgets.md` — all widget types, custom widgets
- `./references/textual-advanced.md` — `@on` decorator, reactive advanced, `@work`, screen modes, testing
- `./references/textual-builder-skill.md` — textual-builder workflow guide
- `./references/textual-tui-skill.md` — TUI skill with workers, modals, screens, testing
- `./references/tui-layouts.md`, `./references/tui-styling.md`, `./references/tui-widgets.md`, `./references/tui-official-guides-index.md` — aperepel/textual-tui-skill reference set

#### When Typer output or help text is in scope

- `./references/typer-ui-patterns.md` — output hierarchy, `rich_markup_mode`, help panels, `pretty_exceptions`

#### When animated or branded splash screens are needed

- `./references/animation-patterns.md` — PyFiglet splash screens, ASCII art, animated loading

#### When Pydantic models carry CLI data

- `./references/model-patterns.md` — Pydantic v2 models for CLI data
- `./references/pydantic-cli-patterns.md` — pydantic-settings, ValidationError formatting, FilePath

### Stage 4 — Critique

- `./references/critique-checklist.md` — Assessment A (LLM design review with Nielsen 0-4 per heuristic, total /40) and Assessment B (deterministic detector: TCSS lint, Rich markup escape audit, terminal-width tests, NO_COLOR check, non-TTY fallback test); user-driven scope selection
- `./references/ai-slop-test.md` — first-order and second-order category-reflex examples

### Stage 5 — Audit

- `./references/audit-checklist.md` — dimensions covering Inclusion & Accessibility, Performance & Responsiveness, Theming & Portability, Width & Adaptive Layout, and Anti-Patterns & Slop; per-dimension 0–4 rubric; per-issue P0–P3 severity tagging; re-run loop

### Stage 6 — Polish

- `./references/polish-checklist.md` — binary items adapted for TUI (column alignment at 80/100/120/≥160 cells, NO_COLOR honoured, terminal-emulator portability, Tab-order keyboard targets); pre-polish assessment; triage rule

### Always loadable when implementing display logic

- `./references/code-quality-patterns.md` — naming, function design, error handling conventions


## Status Indicator Reference

Status indicators must be scannable in under one second using shape, colour, and position — no reading required. This table is the canonical CLI status vocabulary; every implementation aligns with it unless DESIGN.TUI.md overrides explicitly.

| State | Symbol | Rich colour | Rule |
|---|---|---|---|
| Running | `⠸` (spinner) | `cyan` | Animated while active |
| Success | `✓` | `green` | Always leftmost in row |
| Warning | `!` | `yellow` | Same position as success |
| Error | `✗` | `red` | Same position as success |
| Skipped | `–` | `dim` | Visually quieter than success |

- Shape alone (not just colour) must distinguish states — colour-blind safe
- Position consistent: status symbol always in column 0 of a row (the Status Column Rule)
- No reading required: the pattern is scannable before comprehension kicks in

## Dependencies

```bash
uv add typer textual pydantic tinydb questionary pyfiglet python-dateutil
```
