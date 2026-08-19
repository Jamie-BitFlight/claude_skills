# DESIGN.TUI.md / DESIGN.md schema for CLI work

A per-project design contract that captures the visual system in a parseable form. Tokens are normative; prose provides context for how to apply them. AI agents implementing CLI screens read this file to stay on-brand without re-deriving choices each session.

## Two file variants

Two files are recognised. Precedence is fixed.

`DESIGN.TUI.md` is the primary contract for terminal/CLI work. Its frontmatter and prose target TCSS theme variables, Rich named colours, hex inside TCSS, cell-grid spacing, and Unicode-glyph typography. When this file is present, agents working on CLI/TUI surfaces use it as the sole source of truth.

`DESIGN.md` is the general fallback. Projects with a web frontend keep web design here; projects with only a CLI may use this single file and add `runtime: tui` to its frontmatter for unambiguous parsing. When both files exist, `DESIGN.TUI.md` overrides `DESIGN.md` for CLI work and `DESIGN.md` remains the authority for non-TUI surfaces in the same repo.

The sidecar `.impeccable/design.json` from impeccable's web flow is NOT ported. It exists for browser shadow-DOM rendering of HTML/CSS component snippets. Terminals have no analogue, so no sidecar is generated for TUI projects.

## File structure

Both variants follow the same shape: YAML frontmatter on top, then a markdown body with sections in fixed order (listed below). Section headers must match character-for-character so DESIGN.md-aware tools (impeccable, awesome-design-md, skill-rest) can parse the file. Optional evocative subtitles are allowed in the form `## 2. Colors: The Terminal Palette` as long as the canonical word (`Overview`, `Colors`, `Typography`, `Elevation`, `Components`, `Do's and Don'ts`) is present.

The sections in order:

```text
## 1. Overview
## 2. Colors
## 3. Typography
## 4. Elevation
## 5. Components
## 6. Do's and Don'ts
```

Do not reorder, do not rename, do not insert new top-level sections (no `## Layout`, `## Motion`, `## Responsive Behavior`). Fold that content into the canonical sections above where it naturally belongs.

## Frontmatter schema (TUI-adapted)

The YAML frontmatter is the machine-readable layer. Keep entries tight; every entry should correspond to a token the project actually uses. For TUI work, value formats differ from web — see substitutions below.

```yaml
---
name: <project title>
description: <one-line tagline>
register: brand-cli  # or: product-cli
runtime: tui  # optional marker; required on DESIGN.md when used as TUI fallback
colors:
  primary: "$accent"        # TCSS theme variable
  surface: "$surface"
  splash-orange: "#f97316"  # hex inside TCSS
  status-ok: "green"        # Rich named colour
  status-warn: "yellow"
  status-err: "red"
typography:
  display:
    text-style: "bold"      # text-style strings only — no fontFamily, fontSize, lineHeight
    glyph: "pyfiglet-font"  # opt-in, splash surfaces only
  heading:
    text-style: "bold"
  body:
    text-style: "default"
  dim:
    text-style: "dim"
  emphasis:
    text-style: "italic"
spacing:
  tight: 1   # cell-grid integers, not px or rem
  normal: 2
  loose: 4
  panel: 8
rounded:
  none: "none"
  ascii: "ascii"
  soft: "round"
  firm: "thick"
  heavy: "heavy"
  formal: "double"
  hint: "dashed"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.heading}"
    rounded: "{rounded.firm}"
    padding: 2
  button-primary-hover:
    backgroundColor: "{colors.splash-orange}"
  panel-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.soft}"
    padding: "{spacing.panel}"
---
```

Rules that matter:

- Token refs use `{path.to.token}` (e.g. `{colors.primary}`, `{rounded.soft}`). Components may reference primitives; primitives may not reference each other.
- Component sub-tokens are limited to these props: `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width`. Anything outside this set (focus rings, transitions, custom border characters) belongs in prose, not frontmatter.
- Variants are naming convention, not schema. Use `button-primary`, `button-primary-hover`, `button-primary-active` as sibling keys. The same convention applies to panels, inputs, and any stateful component.
- Scale keys are open-ended. Use whatever names the project already uses (`splash-orange`, `surface-container-low`); do not rename to Material defaults.
- Do not duplicate token values between frontmatter and prose. The frontmatter is the canonical value; prose names the role and explains application.

### TUI value-format substitutions

These replace the web equivalents from impeccable's `document.md`:

- Colour values: TCSS theme variables (`$primary`, `$accent`, `$surface`, `$panel`, `$boost`), Rich named colours (`cyan`, `magenta`, `green`, `bright_blue`), and hex (TCSS supports it; Rich does not). Do NOT use `oklch()`, `hsl()`, or P3 — terminals do not render those colour spaces.
- Typography role values: text-style strings (`bold`, `italic`, `dim`, `strike`, `reverse`, `default`) plus optional Unicode-glyph guidance (`box-drawing`, `emoji-fallback`, `pyfiglet-font`). The web `fontFamily`, `fontSize`, `lineHeight`, and `letterSpacing` props do NOT apply — terminals do not have them.
- Spacing units: cell-grid integers (`1`, `2`, `4`, `8` cells). No `px`, `rem`, `em`.
- `rounded` values: TCSS border-style tokens — `none`, `ascii`, `round`, `thick`, `heavy`, `double`, `dashed`. These are TCSS keywords, not numeric corner radii.
- `## 4. Elevation` for TUI means z-layer order in TCSS (`layer:`), focus-ring border style on `:focus`, modal scrim character (e.g. `▓` overlay), and any lift achieved through `$boost`/`$panel`/`$surface` lightness. There is no `box-shadow` analogue.
- Component examples translate one-for-one: `button-primary` → Textual `Button` variant or Rich `Panel` border style; `card` → `Panel` styling.
- The `register` field is required and takes a bare value — `brand-cli` or `product-cli`. No prose, no commentary in the field. See `register-decision.md`.
- The optional `runtime: tui` marker disambiguates a single `DESIGN.md` used for CLI work. When `DESIGN.TUI.md` is present, this marker is unnecessary.

## Two modes

### Scan mode (default)

Used when the project has design tokens, components, or rendered output to extract from. Search the codebase in priority order:

- TCSS files: `*.tcss` declarations, `App.CSS`, `App.CSS_PATH` content; Textual theme variables via `App.theme` and `register_theme()`
- Rich console code: `Theme()` definitions, `Console(theme=...)`, named-style usage in `Panel(border_style=...)` and `Table(header_style=...)`
- Questionary `Style` objects: `prompt_toolkit` style dictionaries
- Typer console wiring: `rich_console`, `rich.print` calls
- Rendered output: capture via `pytest --capture=no`, `rich.console.Console.export_text`, or actual run with output captured

Auto-extract token primitives from those sources, then ask the user for the qualitative language that cannot be derived (Creative North Star, descriptive colour names, philosophy paragraphs, named rules). Stage the YAML frontmatter from extracted tokens before writing prose.

### Seed mode

Used for greenfield CLI projects with no implementation yet. The file leads with:

```markdown
<!-- SEED: re-run once there's code -->
```

Seed-mode frontmatter is minimal — `name` and `description` only. No `colors`, `typography`, `rounded`, `spacing`, or `components` blocks. The body sections carry strategic answers (colour strategy as a Named Rule, typography direction, motion energy, anti-references) without committing to specific values. Real tokens land on the next Scan-mode pass once code exists.

Decide between modes by scanning first. If the scan finds no tokens, no styled components, and no rendered output, offer seed mode rather than fabricating values.

## Token reference syntax

Components reference primitives via `{path.to.token}`:

```yaml
button-primary:
  backgroundColor: "{colors.primary}"
  rounded: "{rounded.firm}"
  padding: "{spacing.normal}"
```

Primitives may not reference each other. Components may reference primitives. This keeps the dependency graph one level deep and parseable.

## Variant naming convention

State variants are sibling keys with the variant name appended:

```yaml
button-primary:
  backgroundColor: "{colors.primary}"
button-primary-hover:
  backgroundColor: "{colors.splash-orange}"
button-primary-active:
  backgroundColor: "{colors.primary-deep}"
button-primary-disabled:
  textColor: "{colors.dim}"
```

The hyphenated suffix is the convention: `-hover`, `-focus`, `-active`, `-pressed`, `-disabled`. Apply the same pattern to panels (`panel-card`, `panel-card-selected`), inputs (`input-text`, `input-text-focus`, `input-text-error`), and any stateful component.

## Named Rules pattern

Rules are short forceful doctrines that AI consumers can cite. Format ported verbatim from impeccable:

```text
**The [Name] Rule.** [short doctrine]
```

Rules can appear in any of the sections (Colors, Typography, Elevation, Components, Do's and Don'ts) where they apply. Aim for 1-3 per section. Rules beat bullet lists for stickiness because they have a quotable name.

TUI examples to seed projects:

```text
**The Status Column Rule.** Status symbols always occupy column 0 of a row. Position is the affordance.

**The 80-Cell Floor Rule.** Primary commands MUST render readably at 80 cells. Wider tiers (100, 120, ≥160) are progressive enhancement.

**The NO_COLOR Rule.** When NO_COLOR is set, every colour decision falls back to monochrome plus shape. Test path runs with NO_COLOR=1.

**The Pipe Test Rule.** When stdout is not a TTY, ANSI is stripped, progress bars are suppressed, and output is line-oriented.
```

These rules apply to most CLI projects and can be carried into a project's DESIGN.TUI.md verbatim. Add project-specific rules alongside them.

## When to run

- The user just established a CLI project's product brief and needs the visual side documented.
- The skill noticed no DESIGN.TUI.md or DESIGN.md exists and needs one before implementation begins.
- An existing DESIGN file is stale and the design has drifted.
- Before a large redesign, to capture the current state as a reference point.

If a DESIGN.TUI.md or DESIGN.md already exists, do not silently overwrite. Show the user the existing file and ask whether to refresh, overwrite, or merge.

## Style guidelines

- Frontmatter first, prose second. Tokens go in YAML; prose contextualises them. Do not redefine a token value in two places.
- Cite PRODUCT.md anti-references by name in section 6 Do's and Don'ts. If PRODUCT.md says "not lolcat-coloured", the Don'ts should repeat that phrase verbatim.
- Match the spec, do not invent new sections. The section names above are fixed. Layout, motion, responsive behaviour, agent prompt guidance — fold each into the section where it naturally belongs (Overview for philosophy-level rules, Components for per-component behaviour).
- Descriptive over technical: "Soft round border (TCSS `round`)" beats "rounded: round". Include the technical token in parens, lead with the description.
- Functional over decorative: for each token, explain WHERE and WHY it is used, not just WHAT it is.
- Exact values in parens: TCSS keywords, Rich style strings, cell counts, named colours; always the technical value alongside the description.
- Be forceful. The voice of a design director: "always", "never", "prohibited", "forbidden", not "consider" or "prefer".
- Group colours by role, not by hue or hex order. Primary / Accent / Status / Neutral is the conventional ordering for CLI palettes.

## Pitfalls

- Don't paste raw TCSS class names. Translate to descriptive language.
- Don't extract every observed style. Stop at what is actually reused; one-offs pollute the system.
- Don't invent components that don't exist. If the project only has Buttons and Panels, document only those.
- Don't overwrite an existing DESIGN file without asking.
- Don't duplicate content from PRODUCT.md. DESIGN files are strictly visual.
- Don't rename sections even slightly. "Colors" not "Color Palette". "Typography" not "Type Rules". Tooling parsing depends on exact headers.
- Don't duplicate token values between frontmatter and prose. The frontmatter is normative.
- Don't invent frontmatter token groups outside the supported set. The accepted top-level keys are `name`, `description`, `register`, `runtime`, `colors`, `typography`, `rounded`, `spacing`, `components`. Anything else (motion, breakpoints, shadows) does not belong here — TUI surfaces have no equivalent and inventing keys breaks parser interop with DESIGN.md-aware tooling.
- Don't include `oklch()`, P3 colours, `clamp()`, `box-shadow`, `fontFamily`, `fontSize`, `lineHeight`, or `letterSpacing` in TUI frontmatter. Terminals do not render these.
- Don't generate a `.impeccable/design.json` sidecar. There is no terminal equivalent of the browser shadow-DOM panel that consumes it.
