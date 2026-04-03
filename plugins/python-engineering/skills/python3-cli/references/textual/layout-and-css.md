# Layout and CSS

Textual layout types, CSS selectors, specificity, variables, and styling patterns.

## Table of Contents

1. [Layout Types](#layout-types)
2. [Utility Containers](#utility-containers)
3. [Grid Layout](#grid-layout)
4. [Docking](#docking)
5. [Layers](#layers)
6. [Offsets](#offsets)
7. [CSS Selectors](#css-selectors)
8. [Pseudo Classes](#pseudo-classes)
9. [Combinators](#combinators)
10. [Specificity](#specificity)
11. [CSS Variables](#css-variables)
12. [Nesting CSS](#nesting-css)
13. [Style Properties Quick Reference](#style-properties-quick-reference)

---

## Layout Types

Set layout via CSS or the `styles` object at runtime.

```css
Screen {
    layout: vertical;  /* default for Screen */
}

.toolbar {
    layout: horizontal;
}
```

```python
widget.styles.layout = "vertical"
```

| Layout | Behavior |
|--------|----------|
| `vertical` | Children stacked top to bottom (Screen default) |
| `horizontal` | Children arranged left to right |
| `grid` | Children placed in grid cells |

### Vertical layout

- Widgets expand to the full width of the parent container by default.
- Set `height: 1fr` to distribute available height equally among children.
- Screen adds a vertical scrollbar automatically when children exceed its height (`overflow-y: auto`).

### Horizontal layout

- Widgets expand to the full width of the parent — set `width: 1fr` to share space.
- Set `height: 100%` explicitly; horizontal layout does not auto-expand height.
- Horizontal scrollbar is not added automatically; add `overflow-x: auto` to enable it.

### fr units

`fr` (fraction) units allocate remaining space proportionally:

```css
.left-panel { width: 1fr; }
.right-panel { width: 2fr; }  /* twice as wide as left */
```

---

## Utility Containers

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical


class MyApp(App):
    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Label("Top left")
                yield Label("Bottom left")
            with Vertical():
                yield Label("Top right")
                yield Label("Bottom right")
```

- `with Container()` syntax adds yielded widgets as children of the container.
- Equivalent to passing widgets as positional arguments to the container constructor.
- `Vertical`, `Horizontal`, `Grid` containers from `textual.containers` apply the corresponding layout.

---

## Grid Layout

```css
Screen {
    layout: grid;
    grid-size: 3 2;        /* 3 columns, 2 rows */
    grid-columns: 2fr 1fr 1fr;  /* column widths */
    grid-rows: 25% 75%;         /* row heights */
    grid-gutter: 1 2;           /* vertical horizontal gutter */
}
```

- `grid-size: <columns>` — omit rows for auto row creation on overflow.
- `grid-size: <columns> <rows>` — fixed grid; extra widgets beyond cell count are not visible.
- `grid-columns` and `grid-rows` accept space-separated values; short lists repeat (e.g. `2 4` for 4 columns → `2 4 2 4`).
- `auto` in `grid-columns`/`grid-rows` sizes the column/row to fit content.
- `grid-gutter` applies between cells only — not between cells and container edges.

### Cell spans

```css
#wide-cell {
    column-span: 2;
    row-span: 2;
}
```

- `column-span` makes a cell occupy multiple columns to the right.
- `row-span` makes a cell occupy multiple rows downward.
- Subsequent widgets shift to fill remaining cells.

---

## Docking

```css
.sidebar {
    dock: left;
    width: 20;
}

Header {
    dock: top;
    height: 3;
}
```

- `dock: top | right | bottom | left` removes the widget from layout flow and pins it to the edge.
- Docked widgets do not scroll out of view — ideal for headers, footers, sidebars.
- Multiple widgets docked to the same edge overlap; widgets yielded later in `compose` appear on top.

---

## Layers

```css
Screen {
    layers: below above;  /* left = lowest, right = highest */
}

#background-widget {
    layer: below;
}

#foreground-widget {
    layer: above;  /* drawn on top of below */
}
```

- `layers` on a parent defines named layer ordering (space-separated, left to lowest, right to highest).
- `layer` on a child assigns it to one of the parent's named layers.
- Layers override yield-order for z-ordering.

---

## Offsets

```css
.shifted {
    offset: 2 -1;  /* 2 right, 1 up */
}
```

- `offset: <x> <y>` shifts a widget relative to its layout-determined position.
- Positive x shifts right; negative x shifts left.
- Positive y shifts down; negative y shifts up.
- Useful for animation (animate from offset `(0 -5)` to `(0 0)` for slide-in).

---

## CSS Selectors

### Type selector — matches Python class name

```css
Button { background: blue; }
```

Also matches base classes: `Static` selector matches any widget extending `Static`.

### ID selector — matches `id` attribute

```css
#next { outline: red; }
```

ID cannot be changed after widget construction.

### Class selector — matches CSS classes

```css
.success { background: green; color: white; }
.error.disabled { background: darkred; }  /* both classes required */
```

```python
yield Button(classes="success")
yield Button(classes="error disabled")
```

CSS class management methods:

| Method | Effect |
|--------|--------|
| `add_class("name")` | Add class to widget |
| `remove_class("name")` | Remove class from widget |
| `toggle_class("name")` | Add if absent, remove if present |
| `has_class("name")` | Returns bool |
| `set_class(condition, "name")` | Add if True, remove if False |

### Universal selector

```css
* { outline: solid red; }       /* all widgets */
VerticalScroll * { background: red; }  /* all children of VerticalScroll */
```

---

## Pseudo Classes

Automatically set by Textual; no manual application needed.

| Pseudo class | Matches when |
|-------------|--------------|
| `:focus` | Widget has input focus |
| `:blur` | Widget does not have input focus |
| `:hover` | Mouse cursor is over the widget |
| `:disabled` | Widget is in disabled state |
| `:enabled` | Widget is in enabled state |
| `:dark` | App theme has `dark == True` |
| `:light` | App theme has `dark == False` |
| `:focus-within` | Widget has a focused descendant |
| `:inline` | App is running in inline mode |
| `:first-child` | First sibling |
| `:last-child` | Last sibling |
| `:first-of-type` | First of its type among siblings |
| `:last-of-type` | Last of its type among siblings |
| `:odd` | Odd-numbered sibling position |
| `:even` | Even-numbered sibling position |
| `:empty` | Has no displayed children |

---

## Combinators

### Descendant combinator (space)

```css
#dialog Button { text-style: bold; }
```

Matches `Button` anywhere inside `#dialog` at any depth.

### Child combinator (`>`)

```css
#sidebar > Button { text-style: underline; }
```

Matches `Button` that is a direct child of `#sidebar` only.

---

## Specificity

When multiple selectors match the same widget and set the same property, the winner is determined by:

1. Most IDs in selector (highest priority).
2. Most class names (pseudo-classes count as class names).
3. Most type names.

`!important` overrides all specificity:

```css
Button:hover { background: blue !important; }
```

Use `!important` sparingly — it makes future overrides difficult.

---

## CSS Variables

```css
$accent: lime;
$border: wide $accent;

#header {
    border: $border;
    color: $accent;
}
```

- Variables prefixed with `$`.
- Variables can reference other variables.
- Variables can only appear in rule values — not in selectors.

---

## Nesting CSS

```css
#dialog {
    background: darkblue;

    .button {
        width: 100%;

        &.affirmative { background: green; }
        &.destructive  { background: red; }
    }
}
```

- Nested rule sets inherit the enclosing selector as a prefix.
- `&` (nesting selector) combines with the parent selector without adding a space — equivalent to chained class selectors.
- Without `&`, the nested selector adds a descendant combinator (space).
- Equivalent non-nested form of `&.affirmative` inside `.button` inside `#dialog` is `#dialog .button.affirmative`.

---

## Style Properties Quick Reference

| Property | Values | Effect |
|----------|--------|--------|
| `layout` | `vertical`, `horizontal`, `grid` | Layout algorithm |
| `width` | `auto`, `N`, `N%`, `Nfr` | Widget width |
| `height` | `auto`, `N`, `N%`, `Nfr` | Widget height |
| `min-width` / `max-width` | `N`, `N%` | Width constraints |
| `min-height` / `max-height` | `N`, `N%` | Height constraints |
| `padding` | `N`, `N N`, `N N N N` | Inner spacing |
| `margin` | `N`, `N N`, `N N N N` | Outer spacing |
| `border` | `<style> <color>` | Border style |
| `outline` | `<style> <color>` | Outline (outside border) |
| `background` | color | Background color |
| `color` | color | Text color |
| `text-style` | `bold`, `italic`, `underline`, `strike`, etc. | Text decoration |
| `text-align` | `left`, `center`, `right` | Text alignment |
| `dock` | `top`, `right`, `bottom`, `left` | Pin to edge |
| `display` | `block`, `none` | Show/hide widget |
| `visibility` | `visible`, `hidden` | Visible/invisible (keeps space) |
| `overflow-x` | `auto`, `hidden`, `scroll` | Horizontal overflow |
| `overflow-y` | `auto`, `hidden`, `scroll` | Vertical overflow |
| `offset` | `<x> <y>` | Position offset |
| `opacity` | `0.0`–`1.0` | Widget transparency |
| `align` | `<horiz> <vert>` | Child alignment in container |
| `content-align` | `<horiz> <vert>` | Content alignment within widget |
| `grid-size` | `<cols>`, `<cols> <rows>` | Grid dimensions |
| `grid-columns` | space-separated sizes | Column widths |
| `grid-rows` | space-separated sizes | Row heights |
| `grid-gutter` | `N`, `N N` | Cell spacing |
| `column-span` | `N` | Columns to span |
| `row-span` | `N` | Rows to span |
| `layers` | space-separated names | Define layer order on parent |
| `layer` | name | Assign widget to layer |
| `tint` | `<color> <percentage>` | Color overlay |
| `keyline` | `<style> <color>` | Grid cell separator lines |
