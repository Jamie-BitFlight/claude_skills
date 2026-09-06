# Mermaid Flowchart Node Shapes Reference

> Parent: [Mermaid Flowchart Syntax](../SKILL.md)

All Mermaid flowchart node shapes: basic syntax, direction codes, classic bracket shapes, and the expanded `@{ shape: }` syntax (v11.3.0+). Every syntax example is verbatim from the source documentation.

## Table of Contents

- [Basic Syntax](#basic-syntax)
- [Direction](#direction)
- [Classic Node Shapes (Bracket Syntax)](#classic-node-shapes-bracket-syntax)
- [Unicode and Markdown Text](#unicode-and-markdown-text)
- [Expanded Node Shapes v11.3.0+ Syntax](#expanded-node-shapes-v1130-syntax)
- [Expanded Shape Name Table](#expanded-shape-name-table)
- [Special Shapes: Icon](#special-shapes-icon)
- [Special Shapes: Image](#special-shapes-image)
- [Warnings and Constraints](#warnings-and-constraints)

## Basic Syntax

A flowchart is declared with the keyword `flowchart` (or `graph`) followed by a direction code. `flowchart` and `graph` are interchangeable.

A bare node ID with no brackets renders as a rectangle displaying the ID as its text: `id`

A node with text different from its ID uses square brackets: `id1[This is the text in the box]`

If text is set multiple times for the same node ID, the last definition wins. If edges are defined after a node's text was set, the text can be omitted on subsequent references — the previously defined text is reused.

## Direction

The five valid direction codes:

| Code | Meaning |
|------|---------|
| `TB` | Top to bottom |
| `TD` | Top down (identical to TB) |
| `BT` | Bottom to top |
| `RL` | Right to left |
| `LR` | Left to right |

Example: `flowchart LR` declares left-to-right orientation.

## Classic Node Shapes (Bracket Syntax)

### Round Edges

Round-edged rectangle uses parentheses: `id1(This is the text in the box)`

```mermaid
flowchart LR
    id1(This is the text in the box)
```

### Stadium

Stadium-shaped node (pill shape) uses parentheses wrapping brackets: `id1([This is the text in the box])`

```mermaid
flowchart LR
    id1([This is the text in the box])
```

### Subroutine

Subroutine-shaped node uses double square brackets: `id1[[This is the text in the box]]`

```mermaid
flowchart LR
    id1[[This is the text in the box]]
```

### Cylinder

Cylindrical node uses bracket-parenthesis: `id1[(Database)]`

```mermaid
flowchart LR
    id1[(Database)]
```

### Circle

Circle node uses double parentheses: `id1((This is the text in the circle))`

```mermaid
flowchart LR
    id1((This is the text in the circle))
```

### Asymmetric (Flag/Ribbon)

Asymmetric shape (flag/ribbon pointing right) uses `>` and `]`: `id1>This is the text in the box]`

The asymmetric shape currently only exists as a right-pointing flag; no mirror variant is available.

```mermaid
flowchart LR
    id1>This is the text in the box]
```

### Rhombus (Diamond)

Rhombus (diamond) node uses curly braces: `id1{This is the text in the box}`

```mermaid
flowchart LR
    id1{This is the text in the box}
```

### Hexagon

Hexagon node uses double curly braces: `id1{{This is the text in the box}}`

```mermaid
flowchart LR
    id1{{This is the text in the box}}
```

### Parallelogram

Parallelogram (lean right) uses `[/ /]`: `id1[/This is the text in the box/]`

```mermaid
flowchart TD
    id1[/This is the text in the box/]
```

### Parallelogram Alt

Parallelogram alt (lean left) uses `[\ \]`: `id1[\This is the text in the box\]`

```mermaid
flowchart TD
    id1[\This is the text in the box\]
```

### Trapezoid

Trapezoid (base at bottom) uses `[/ \]`: `A[/Christmas\]`

```mermaid
flowchart TD
    A[/Christmas\]
```

### Trapezoid Alt

Trapezoid alt (base at top) uses `[\ /]`: `B[\Go shopping/]`

```mermaid
flowchart TD
    B[\Go shopping/]
```

### Double Circle

Double circle node uses triple parentheses: `id1(((This is the text in the circle)))`

```mermaid
flowchart TD
    id1(((This is the text in the circle)))
```

## Unicode and Markdown Text

To use Unicode characters in node text, enclose the text in double quotes: `id["This ❤ Unicode"]`

```mermaid
flowchart LR
    id["This ❤ Unicode"]
```

To use Markdown formatting in node text, enclose text in double quotes and backticks: `` markdown["`This **is** _Markdown_`"] ``

Markdown text in nodes supports multi-line content by inserting literal newlines inside the backtick-quoted string. Markdown formatting requires `htmlLabels: false` in the config block when used with certain renderers.

```mermaid
%%{init: {"flowchart": {"htmlLabels": false}} }%%
flowchart LR
    markdown["`This **is** _Markdown_`"]
    newLines["`Line1
    Line 2
    Line 3`"]
    markdown --> newLines
```

## Expanded Node Shapes v11.3.0+ Syntax

Starting in Mermaid v11.3.0, nodes can be defined with `A@{ shape: shapeName }` to assign any of 30+ shape types. The `@{ shape: ... }` syntax creates a node identical to bracket syntax — `A@{ shape: rect }` renders the same as `A["A"]` or bare `A`. The `label` property sets the display text.

```mermaid
flowchart TD
    A@{ shape: rect, label: "This is a process" }
```

Any shape from the table below works with the same pattern: `A@{ shape: NAME, label: "text" }`

Example using multiple shapes with edges:

```mermaid
flowchart RL
    A@{ shape: manual-file, label: "File Handling"}
    B@{ shape: manual-input, label: "User Input"}
    C@{ shape: docs, label: "Multiple Documents"}
    D@{ shape: procs, label: "Process Automation"}
    E@{ shape: paper-tape, label: "Paper Records"}
```

Representative shapes across categories:

```mermaid
flowchart TD
    A@{ shape: rect, label: "Process" }
    B@{ shape: diam, label: "Decision" }
    C@{ shape: cyl, label: "Database" }
    D@{ shape: circle, label: "Start" }
    E@{ shape: dbl-circ, label: "Stop" }
    F@{ shape: hex, label: "Prepare" }
```

## Expanded Shape Name Table

The complete list of shapes available with `@{ shape: NAME }` syntax (v11.3.0+). The **Short Name** is the canonical value for the `shape:` property. **Aliases** are alternative values that resolve to the same shape.

| Semantic Name | Shape Name | Short Name | Aliases |
|---|---|---|---|
| Process | Rectangle | `rect` | `proc`, `process`, `rectangle` |
| Event | Rounded Rectangle | `rounded` | `event` |
| Terminal Point | Stadium | `stadium` | `pill`, `terminal` |
| Subprocess | Framed Rectangle | `subproc` | `fr-rect`, `framed-rectangle`, `subprocess`, `subroutine` |
| Database | Cylinder | `cyl` | `cylinder`, `database`, `db` |
| Start (Circle) | Circle | `circle` | `circ` |
| Odd | Odd | `odd` | `odd` |
| Decision | Diamond | `diam` | `decision`, `diamond`, `question` |
| Prepare Conditional | Hexagon | `hex` | `hexagon`, `prepare` |
| Data Input/Output (Lean Right) | Lean Right | `lean-r` | `in-out`, `lean-right` |
| Data Input/Output (Lean Left) | Lean Left | `lean-l` | `lean-left`, `out-in` |
| Priority Action | Trapezoid Base Bottom | `trap-b` | `priority`, `trapezoid`, `trapezoid-bottom` |
| Manual Operation | Trapezoid Base Top | `trap-t` | `inv-trapezoid`, `manual`, `trapezoid-top` |
| Stop (Double Circle) | Double Circle | `dbl-circ` | `double-circle` |
| Text Block | Text Block | `text` | |
| Card | Notched Rectangle | `notch-rect` | `card`, `notched-rectangle` |
| Lined/Shaded Process | Lined Rectangle | `lin-rect` | `lin-proc`, `lined-process`, `lined-rectangle`, `shaded-process` |
| Start (Small Circle) | Small Circle | `sm-circ` | `small-circle`, `start` |
| Stop (Framed Circle) | Framed Circle | `framed-circle` | `fr-circ`, `stop` |
| Fork/Join | Filled Rectangle | `fork` | `join` |
| Collate | Hourglass | `hourglass` | `collate` |
| Comment (Left Brace) | Curly Brace | `brace` | `brace-l`, `comment` |
| Comment (Right Brace) | Curly Brace Right | `brace-r` | |
| Comment (Both Braces) | Curly Braces | `braces` | |
| Com Link | Lightning Bolt | `bolt` | `com-link`, `lightning-bolt` |
| Document | Document | `doc` | `document` |
| Delay | Half-Rounded Rectangle | `delay` | `half-rounded-rectangle` |
| Direct Access Storage | Horizontal Cylinder | `h-cyl` | `das`, `horizontal-cylinder` |
| Disk Storage | Lined Cylinder | `lin-cyl` | `disk`, `lined-cylinder` |
| Display | Curved Trapezoid | `curv-trap` | `curved-trapezoid`, `display` |
| Divided Process | Divided Rectangle | `div-rect` | `div-proc`, `divided-process`, `divided-rectangle` |
| Extract | Triangle | `tri` | `extract`, `triangle` |
| Internal Storage | Window Pane | `win-pane` | `internal-storage`, `window-pane` |
| Junction | Filled Circle | `f-circ` | `filled-circle`, `junction` |
| Lined Document | Lined Document | `lin-doc` | `lined-document` |
| Loop Limit | Trapezoidal Pentagon | `notch-pent` | `loop-limit`, `notched-pentagon` |
| Manual File | Flipped Triangle | `flip-tri` | `flipped-triangle`, `manual-file` |
| Manual Input | Sloped Rectangle | `sl-rect` | `manual-input`, `sloped-rectangle` |
| Multi-Document | Stacked Document | `docs` | `documents`, `st-doc`, `stacked-document` |
| Multi-Process | Stacked Rectangle | `st-rect` | `processes`, `procs`, `stacked-rectangle` |
| Paper Tape | Flag | `flag` | `paper-tape` |
| Stored Data | Bow Tie Rectangle | `bow-rect` | `bow-tie-rectangle`, `stored-data` |
| Summary | Crossed Circle | `cross-circ` | `crossed-circle`, `summary` |
| Tagged Document | Tagged Document | `tag-doc` | `tagged-document` |
| Tagged Process | Tagged Rectangle | `tag-rect` | `tag-proc`, `tagged-process`, `tagged-rectangle` |
| Bang | Bang | `bang` | |
| Cloud | Cloud | `cloud` | |

## Special Shapes: Icon

The `icon` shape includes an icon from a registered icon pack in the flowchart node. Icon packs must be registered before use; see Mermaid icon configuration docs.

```mermaid
flowchart TD
    A@{ icon: "fa:user", form: "square", label: "User Icon", pos: "t", h: 60 }
```

### Icon Parameters

| Parameter | Required | Description | Values |
|---|---|---|---|
| `icon` | Yes | Icon name from registered icon pack | e.g., `"fa:user"` |
| `form` | No | Background shape behind the icon; if omitted, no background is rendered | `square`, `circle`, `rounded` |
| `label` | No | Text label for the icon; if omitted, no label is displayed | any string |
| `pos` | No | Position of the label relative to the icon; defaults to bottom | `t` (top), `b` (bottom) |
| `h` | No | Height of the icon in pixels; defaults to 48 (minimum) | integer |

## Special Shapes: Image

The `image` shape embeds an image in a flowchart node.

```text
flowchart TD
    A@{ img: "https://example.com/image.png", label: "Image Label", pos: "t", w: 60, h: 60, constraint: "off" }
```

To resize an image while preserving aspect ratio, set `h` and `constraint: "on"`; the width adjusts automatically.

```mermaid
flowchart TD
    A@{ img: "https://mermaid.js.org/favicon.svg", label: "My example image label", pos: "t", h: 60, constraint: "on" }
```

### Image Parameters

| Parameter | Required | Description | Values |
|---|---|---|---|
| `img` | Yes | URL of the image to display | any valid URL string |
| `label` | No | Text label for the image; if omitted, no label is displayed | any string |
| `pos` | No | Position of the label relative to the image; defaults to bottom | `t` (top), `b` (bottom) |
| `w` | No | Width of the image in pixels; defaults to the natural width | integer |
| `h` | No | Height of the image in pixels; defaults to the natural height | integer |
| `constraint` | No | Whether the image constrains the node size and maintains aspect ratio; defaults to `"off"` | `"on"`, `"off"` |

## Warnings and Constraints

- Using the word `end` in all lowercase as a node name will break the flowchart. Capitalize at least one letter (e.g., `End`, `END`) or use the workaround from GitHub issue #1444.
- Using `o` or `x` as the first letter of a connecting node (e.g., `A---oB`) will create a circle edge or cross edge respectively. Add a space before the letter or capitalize it (e.g., `dev--- ops`, `dev---Ops`).
- `\n` does not render as a line break inside a node label — Mermaid treats it as literal text. Use `<br>` instead: `id["Line one<br>Line two"]`.
- A bare colon inside a quoted node label string can break rendering (Mermaid's parser can misread it as label/attribute syntax). Use `=` for assignments inside labels instead: `id["subagent_type='plugin:agent-name'"]` rather than `id["subagent_type: plugin:agent-name"]`.

## See Also

- [Edge Syntax](./edge-syntax.md) — link types, arrows, chaining, edge IDs, animations
- [Subgraphs and Layout](./subgraphs-and-layout.md) — grouping, direction, special characters
- [Styling and Configuration](./styling-and-config.md) — classDef, CSS classes, interactivity

## References

[Mermaid Flowchart Docs](https://github.com/mermaid-js/mermaid/blob/develop/packages/mermaid/src/docs/syntax/flowchart.md) (accessed 2026-03-07)
