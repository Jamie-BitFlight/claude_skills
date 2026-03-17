---
name: design-anti-patterns
description: 'Enforce anti-AI UI design rules based on the Uncodixfy methodology. Use when generating HTML, CSS, React, Vue, Svelte, or any frontend UI code. Prevents "Codex UI" — the generic AI aesthetic of soft gradients, floating panels, oversized rounded corners, glassmorphism, hero sections in dashboards, and decorative copy. Applies constraints from Linear/Raycast/Stripe/GitHub design philosophy: functional, honest, human-designed interfaces. Triggers on: UI generation, dashboard building, frontend component creation, CSS styling, landing page design, or any task producing visual interface code.'
---

# Design Anti-Patterns (Uncodixfy)

SOURCE: [Uncodixfy](https://github.com/cyxzdev/Uncodixfy/blob/main/Uncodixfy.md) (accessed 2026-03-17)

Before writing any UI code, apply the Uncodixfy metacognitive check: list the UI decisions you would make by default, then do NOT make them if they match any banned pattern below. Build interfaces that feel like Linear, Raycast, Stripe, or GitHub — functional, honest, no visual theatrics.

## Pre-Flight Check

Before generating any UI component, run this internal check:

1. List all styling decisions you would make by default for this component
2. Cross-reference each against the banned patterns in this skill and [the full rules reference](./references/uncodixfy-rules.md)
3. Replace every match with the "normal" standard from the reference
4. Verify the result contains zero banned patterns

## Absolute Prohibitions

These patterns are never acceptable unless the user explicitly overrides:

- Border radius > 12px on any element
- Pill-shaped buttons or badges
- Glassmorphism, frosted panels, blur haze
- Soft corporate gradients (backgrounds, buttons, text)
- Hero sections inside dashboards or internal tools
- Decorative copy ("Operational clarity without the clutter")
- Eyebrow labels (uppercase `<small>` with letter-spacing)
- KPI card grids as default dashboard layouts
- Fake charts that exist only to fill space
- Transform animations on hover (translateX, scale, bounce)
- Dramatic box shadows (> 8px blur, colored shadows)
- Floating detached sidebars with rounded outer shells
- `<small>` subheaders above `<h2>` headline blocks
- Decorative note cards with `<small>` + `<strong>` pattern
- Generic startup copy in any UI element
- Donut charts with hand-wavy percentages
- Multiple nested panel types (panel, panel-2, rail-panel)
- Status indicators using `::before` pseudo-element colored dots
- Nav badges showing "Live" or count indicators without functional purpose
- Footer meta lines ("Dashboard v2.1 - dark mode - single-file HTML")

## Normal Standards

Apply these defaults to every component:

| Component | Standard |
|-----------|----------|
| Sidebar | 240-260px fixed, solid background, simple border-right |
| Buttons | Solid fill or simple border, 8-10px radius max |
| Cards | 8-12px radius, subtle border, shadow max 0 2px 8px rgba(0,0,0,0.1) |
| Typography | System fonts or simple sans-serif, 14-16px body, clear hierarchy |
| Spacing | 4/8/12/16/24/32px scale only |
| Transitions | 100-200ms ease, opacity/color changes only |
| Containers | max-width 1200-1400px, centered, standard padding |
| Toolbars | Standard height 48-56px, simple horizontal layout |
| Inputs | Solid borders, simple focus ring, labels above fields |
| Modals | Centered overlay, simple backdrop, no slide-in animations |

## Color Selection

Follow this priority order:

1. **Use the project's existing colors** — search project files for existing palette definitions
2. **Pick from a predefined palette** — see [color palettes in the rules reference](./references/uncodixfy-rules.md#dark-color-schemes)
3. **Never invent random color combinations** unless the user explicitly requests it

When selecting from predefined palettes, pick randomly — do not default to the first one.

## Quick Reference

For the complete set of 30+ specifically banned implementation patterns, per-component "normal" standards, and 19 predefined color palettes (10 dark, 9 light), read [the full Uncodixfy rules](./references/uncodixfy-rules.md).
