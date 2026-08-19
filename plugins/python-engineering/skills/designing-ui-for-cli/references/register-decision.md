# Register Decision: brand-cli vs product-cli

The register names the stance the CLI takes toward its user. It is chosen before colour, before typography, before layout. Adapted from impeccable's `reference/brand.md`, `reference/product.md`, and the Register section of impeccable's `SKILL.md`.

## Core distinction

- **brand-cli** — design IS the product. The CLI surface is the moment: an installer banner, a demo recording, a marketing CLI (`bun create`, `gh demo`), a one-shot welcome flow. The visitor's impression is the deliverable.
- **product-cli** — design SERVES the product. The CLI surface is a tool the user operates: subcommand trees, dashboards, settings panels, data tables, authenticated/configured flows. The tool disappears into the task.

A CLI rarely sits in both registers at once. A product-cli MAY contain one brand-cli surface (a first-run welcome, a milestone celebration), but the product register is the floor.

## First-match-wins decision rule

Apply the checks below in order. The first one that yields a register name is the answer. Stop there.

1. **Task cue.** Words in the task itself. "splash", "demo", "marketing", "installer", "welcome", "onboarding-art" → brand-cli. "dashboard", "monitor", "manage", "audit", "migrate", "inspect" → product-cli.
2. **Surface in focus.** What is the CLI surface being designed? An interactive welcome screen or one-shot art moment → brand-cli. A subcommand that processes data, a panel a user returns to, a flag-driven utility → product-cli.
3. **PRODUCT.md `register` field.** A bare value: `brand-cli` or `product-cli`. No prose, no commentary.
4. **Default.** Nothing matched. Default to **product-cli**. Most CLIs are tools.

No further tie-breaker is required. First match wins.

## Examples

| Surface | Task cue | Surface check | PRODUCT.md | Register |
|---|---|---|---|---|
| `bun create` install banner | "installer", "marketing" | one-shot welcome | (any) | brand-cli |
| `kubectl get pods` table output | "manage" | data subcommand | product-cli | product-cli |
| `gh demo` recording surface | "demo" | one-shot art | (any) | brand-cli |
| `terraform apply` plan view | "audit", "manage" | dashboard-style | product-cli | product-cli |
| `uv init` first-run welcome (one-time) | none in task | one-shot welcome | product-cli | brand-cli |
| Database migration tool TUI | "migrate", "manage" | dashboard-style | (absent) | product-cli |

The fifth row shows the surface check overriding PRODUCT.md when the task itself produces a brand-cli surface inside an otherwise product-cli tool. First match wins.

## brand-cli register summary

**Permissions** (from `brand.md` lines 107-114, adapted for terminal):

- Ambitious first-load motion: animated splash, staggered reveal, typographic choreography
- Drenched colour strategies: the surface IS the colour for one screen
- Typographic risk via PyFiglet, `rich.text` styling, oversize glyphs as hero
- Art direction per command surface: different command moments may have different visual worlds when the narrative demands it

**Bans** (from `brand.md` lines 96-104, adapted for terminal):

- Timid palettes that ignore the brief
- Splash on every command (a brand moment is one moment, not a recurring overlay)
- Monospace as default-for-technical-feel when the brand isn't technical
- All-caps body output (caps reserved for short labels and headings)
- Zero personality on a brief that calls for personality

## product-cli register summary

**Permissions** (from `product.md` lines 56-62, adapted for terminal):

- Terminal-default fonts; system stacks for any embedded text-mode UI
- Familiar subcommand patterns: standard verbs, breadcrumb-style help, GNU-style flags
- Density: data tables with many rows, dense status output, panels with many labels
- Consistency over surprise: same status symbols, same flag vocabulary, same layout shape across subcommands

**Bans** (from `product.md` lines 47-53, adapted for terminal):

- Decorative motion that doesn't convey state
- Inconsistent status vocabulary across subcommands (one subcommand prints `OK`, another prints `[+]`, a third prints a green check — pick one)
- Display-style output where labels suffice (PyFiglet titles on a `--list` subcommand)
- Reinventing standard subcommand affordances for flavour (custom `--help` shapes, non-GNU flag conventions)

## Register splits across dimensions

The register modulates each design dimension. When a task asks for "bolder", "quieter", "more delight", or similar adjustment, look up which register is in play and apply the matching column.

### Bolder vs quieter

Source: `bolder.md` lines 5-11 and `quieter.md` lines 5-11.

| Dimension | brand-cli | product-cli |
|---|---|---|
| Bolder | Distinctive: extreme scale, unexpected colour, typographic risk via PyFiglet, committed POV | Stronger hierarchy, clearer weight contrast, one sharper accent, more committed density (clarity, not drama) |
| Quieter | Restrained palette, more whitespace, more typographic air; drama reduced, POV intact | Fewer accents, less colour, less motion; the tool disappears more completely into the task |

### Delight

Source: `delight.md` lines 7-13.

| brand-cli | product-cli |
|---|---|
| Distributed across copy voice, splash transitions, discovery rewards, seasonal touches, personality across the whole surface | At specific moments only: completion, first-time actions, error recovery, milestone crossings. Reliability and consistency carry the rest. Delight everywhere reads as noise. |

### Animate

Source: `animate.md` lines 7-13, terminal-adapted.

| brand-cli | product-cli |
|---|---|
| Orchestrated splash sequences, staggered reveal, scroll-driven motion where applicable. Motion is part of the voice. | 150-250ms on most transitions. Motion conveys state: feedback, reveal, loading, transitions between views. No startup choreography; users are in a task. |

### Typeset

Source: `typeset.md` lines 5-11, terminal-adapted.

| brand-cli | product-cli |
|---|---|
| Run a font selection procedure for any embedded display moment. PyFiglet for hero text. ≥1.25 ratio between text-style steps; fluid scale where the surface allows. | Terminal-default fonts. Single hierarchy. 1.125-1.2 ratio between text-style steps (regular → dim → bold). One well-tuned set carries headings, labels, body, data. |

### Layout

Source: `layout.md` lines 5-11, terminal-adapted.

| brand-cli | product-cli |
|---|---|
| Asymmetric compositions, intentional grid-breaking for emphasis, rhythm through contrast: tight groupings paired with generous separations | Predictable grids, consistent densities, structural responsive behaviour (collapse columns at narrow widths, not fluid sizing). Consistency IS an affordance. |

## Reflex-reject for TUI category aesthetic lanes

A second-altitude AI slop trap, analogous to `brand.md` lines 32-38. The first-order trap is the obvious category reflex (DevOps → green-on-black; AI CLI → purple-and-emoji). The second-order trap is what the model reaches for when the first reflex has been banned: the next training-data default one tier deeper.

Examples:

- "DevOps tool that's not green-on-black" → next reflex is desaturated-blue + Nerd-Font icons
- "AI CLI that's not purple-emoji" → next reflex is editorial-monospaced minimalism
- "Package manager that's not cyan-and-checkmarks" → next reflex is mono + brackets (`[ok]` / `[fail]`)

The full second-altitude category list lives in [./ai-slop-test.md](./ai-slop-test.md). When choosing a brand-cli aesthetic lane, run both the first-order and second-order checks against that file before committing to colours, glyphs, or banner treatment.

## Source

- `brand.md` lines 3, 96-104, 107-114 (brand register definition, bans, permissions)
- `product.md` lines 3, 47-53, 56-62 (product register definition, bans, permissions)
- impeccable's `SKILL.md` lines 60-66 (Register section: identify before designing, first-match-wins priority)
- `bolder.md` lines 5-11, `quieter.md` lines 5-11, `delight.md` lines 7-13, `animate.md` lines 7-13, `typeset.md` lines 5-11, `layout.md` lines 5-11 (six register splits)
- `brand.md` lines 32-38 (reflex-reject aesthetic lanes pattern)

Cache path verified 2026-05-07: `~/.claude/plugins/cache/impeccable/impeccable/3.0.7/skills/impeccable/`.
