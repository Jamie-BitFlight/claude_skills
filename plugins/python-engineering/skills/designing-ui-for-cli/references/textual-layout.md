# Layout and Positioning

## Layout Types

### Vertical (Default)

Stacks widgets vertically:

```css
Container {
    layout: vertical;
}
```

### Horizontal

Arranges widgets side-by-side:

```css
Container {
    layout: horizontal;
}
```

### Grid

Grid layout with rows and columns:

```css
Grid {
    layout: grid;
    grid-size: 3 2;  /* 3 columns, 2 rows */
    grid-gutter: 1 2;  /* vertical horizontal spacing */
}
```

#### Grid Cell Spanning

Make widgets span multiple cells:

```css
#header {
    column-span: 3;  /* Span 3 columns */
}

#sidebar {
    row-span: 2;     /* Span 2 rows */
}
```

#### Grid Rows and Columns

Define row heights and column widths:

```css
Grid {
    grid-size: 2 3;
    grid-rows: 1fr 6 25%;     /* Flexible, fixed 6, 25% */
    grid-columns: 1fr 2fr;    /* 1:2 ratio */
}
```

## Alignment

### Screen/Container Alignment

Center content within screen:

```css
Screen {
    align: center middle;  /* horizontal vertical */
}
```

Options: `left`, `center`, `right` × `top`, `middle`, `bottom`

### Content Alignment

Align content within a widget:

```css
MyWidget {
    content-align: center middle;
    text-align: center;
}
```

## Docking

Pin widgets to screen edges:

```css
#header {
    dock: top;
    height: 3;
}

#sidebar {
    dock: left;
    width: 20;
}

#footer {
    dock: bottom;
}
```

Docking order matters — widgets yielded later from `compose` appear on top when multiple
widgets are docked to the same edge. Earlier-yielded widgets render below later-yielded ones.
SOURCE: <https://textual.textualize.io/guide/layout/#docking> (accessed 2026-05-07)

## Sizing

### Fixed Sizes

```css
Widget {
    width: 50;      /* 50 cells */
    height: 10;     /* 10 rows */
}
```

### Relative Sizes

```css
Widget {
    width: 50%;     /* 50% of parent */
    height: 100%;
}
```

### Fractional Units

Share available space proportionally:

```css
#left {
    width: 1fr;     /* Gets 1 part */
}

#right {
    width: 2fr;     /* Gets 2 parts (twice as wide) */
}
```

### Auto Sizing

Fit content:

```css
Widget {
    width: auto;
    height: auto;
}
```

### Min/Max Constraints

```css
Widget {
    min-width: 20;
    max-width: 80;
    min-height: 5;
    max-height: 30;
}
```

## Spacing

### Margin

Space outside widget border:

```css
Widget {
    margin: 1;          /* All sides */
    margin: 1 2;        /* vertical horizontal */
    margin: 1 2 3 4;    /* top right bottom left */
}
```

### Padding

Space inside widget border:

```css
Widget {
    padding: 1;         /* All sides */
    padding: 1 2;       /* vertical horizontal */
}
```

## Visibility

### Display

Show or hide widgets:

```css
#hidden {
    display: none;
}

#visible {
    display: block;
}
```

Toggle in Python:

```python
widget.display = False  # Hide
widget.display = True  # Show
```

### Visibility

Similar to display but reserves space:

```css
Widget {
    visibility: hidden;  /* Hidden but takes space */
    visibility: visible;
}
```

## Layers

Control stacking order. The `layers:` declaration on the **parent container** is required —
without it, `layer:` on child widgets has no effect.
SOURCE: <https://textual.textualize.io/guide/layout/#layers> (accessed 2026-05-07)

```css
Screen {
    layers: below above;  /* defines two layers; 'below' is behind 'above' */
}

#background {
    layer: below;
}

#popup {
    layer: above;  /* renders on top of #background */
}
```

## Scrolling

### Enable Scrolling

```css
Container {
    overflow-x: auto;  /* Horizontal scrolling */
    overflow-y: auto;  /* Vertical scrolling */
    overflow: auto auto;  /* Both */
}
```

### Programmatic Scrolling

```python
# Scroll to specific position
container.scroll_to(x=0, y=100)

# Scroll widget into view
widget.scroll_visible()

# Scroll to end
self.screen.scroll_end(animate=True)
```

## Example: Card Game Layout

```css
Screen {
    layout: vertical;
}

#opponent-hand {
    dock: top;
    height: 12;
    layout: horizontal;
    align: center top;
}

#play-area {
    height: 1fr;
    layout: grid;
    grid-size: 5 3;
    align: center middle;
}

#player-hand {
    dock: bottom;
    height: 15;
    layout: horizontal;
    align: center bottom;
    padding: 1;
}

.card {
    width: 12;
    height: 10;
    margin: 0 1;
}
```
