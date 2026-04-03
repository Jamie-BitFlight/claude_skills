# Reactivity

Reactive attributes, smart refresh, validation, watch methods, compute methods, data binding, and mutable reactives.

## Table of Contents

1. [Reactive Attributes](#reactive-attributes)
2. [Smart Refresh](#smart-refresh)
3. [var — Reactive Without Refresh](#var--reactive-without-refresh)
4. [Validation](#validation)
5. [Watch Methods](#watch-methods)
6. [Recompose](#recompose)
7. [Compute Methods](#compute-methods)
8. [Setting Reactives Without Superpowers](#setting-reactives-without-superpowers)
9. [Mutable Reactives](#mutable-reactives)
10. [Data Binding](#data-binding)

---

## Reactive Attributes

```python
from textual.reactive import reactive
from textual.widget import Widget


class MyWidget(Widget):
    name: reactive[str | None] = reactive("Paul")
    count = reactive(0)
    is_cool = reactive(True)
    start_time = reactive(time)  # callable — called to get default
```

- Import `reactive` from `textual.reactive`.
- Assign in class scope — no `__init__` modification required.
- First argument is the default value, or a callable that returns the default.
- Get/set like normal attributes: `self.count += 1`, `self.name = "Jessica"`.
- Type hints use `reactive[T]` form; optional when the default value makes the type unambiguous.

---

## Smart Refresh

When a reactive attribute is set to a new value, Textual automatically calls `render()` on the widget.

```python
class Greeting(Widget):
    who = reactive("World")

    def render(self) -> str:
        return f"Hello, {self.who}!"


class MyApp(App):
    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one(Greeting).who = event.value  # triggers automatic refresh
```

- Multiple reactive assignments in one handler produce a single refresh.
- Assigning the same value that is already set does not trigger a refresh.
- To trigger a layout update (not just a content update), set `layout=True`:

```python
class MyWidget(Widget):
    who = reactive("World", layout=True)  # refresh + layout recalculation
```

---

## var — Reactive Without Refresh

```python
from textual.reactive import var


class MyWidget(Widget):
    cursor_position = var((0, 0))  # changes don't auto-refresh
```

- `var` gives watch method and validation superpowers without triggering automatic refresh or layout.
- Use when you want to control refreshing manually (e.g. only refresh specific regions via Line API).

---

## Validation

Add a `validate_<name>` method to check or modify a value before it is set:

```python
class Counter(Widget):
    count = reactive(0)

    def validate_count(self, new_value: int) -> int:
        return max(0, min(10, new_value))  # clamp to 0–10
```

- Method receives the incoming value and must return the value to actually set (which may differ).
- Called every time the reactive is assigned.
- Executed before the watch method.

---

## Watch Methods

Add a `watch_<name>` method to react when a reactive value changes:

```python
from textual.color import Color


class ColorPicker(Widget):
    color = reactive(Color.parse("white"))

    def watch_color(self, old_color: Color, new_color: Color) -> None:
        self.styles.background = new_color
```

- One-argument signature receives the new value only.
- Two-argument signature receives old value and new value.
- Called only when the value actually changes (not when the same value is re-assigned).
- To call on every assignment including unchanged values: `reactive(default, always_update=True)`.

### Dynamic watchers

Add a watcher to a reactive you don't own (e.g. a third-party widget):

```python
class MyApp(App):
    def on_mount(self) -> None:
        counter = self.query_one(Counter)
        self.watch(counter, "count", self.on_count_change)

    def on_count_change(self, count: int) -> None:
        self.query_one(ProgressBar).advance(count)
```

- `DOMNode.watch(target_widget, attribute_name, callback)` registers an external watcher.

---

## Recompose

Setting `recompose=True` on a reactive causes Textual to call `compose()` again when the value changes, replacing all child widgets:

```python
from textual.widgets import Digits


class Clock(Widget):
    time: reactive[str] = reactive("", recompose=True)

    def compose(self) -> ComposeResult:
        yield Digits(self.time)
```

- Recompose replaces all children — avoid storing references to child widgets when using `recompose=True`; use `query()` instead.
- Widgets with internal state (`DataTable`, `Input`, `TextArea`) lose their state on recompose.
- Recompose is slightly less efficient than a targeted refresh; avoid for high-frequency or many-child updates.
- When to use recompose vs refresh: use recompose when the structure of child widgets changes; use refresh when only content changes.

---

## Compute Methods

Add a `compute_<name>` method to derive a reactive value from other reactives:

```python
from textual.color import Color


class ColorMixer(Widget):
    red = reactive(0)
    green = reactive(0)
    blue = reactive(0)
    color = reactive(Color(0, 0, 0))

    def compute_color(self) -> Color:
        return Color(self.red, self.green, self.blue)

    def watch_color(self, color: Color) -> None:
        self.styles.background = color
```

- `compute_<name>` is recalculated whenever any other reactive on the object changes.
- The result is cached; `watch_<name>` fires when the computed result changes.
- Execution order: compute → validate → watch.
- Avoid slow or CPU-intensive compute methods — they run on every reactive change on the object.

---

## Setting Reactives Without Superpowers

Use `set_reactive` to set a reactive value in `__init__` without triggering watchers:

```python
from textual.dom import DOMNode


class Greeter(Widget):
    greeting = reactive("Hello")

    def __init__(self, initial_greeting: str) -> None:
        super().__init__()
        self.set_reactive(Greeter.greeting, initial_greeting)
        # Avoids NoMatches error — watch_greeting runs before widget is mounted

    def watch_greeting(self, greeting: str) -> None:
        self.query_one(Label).update(greeting)
```

- `set_reactive(ClassName.attribute, value)` sets the value without calling validate or watch methods.
- Use in constructors when the watch method queries the DOM — the widget isn't mounted yet at that point.

---

## Mutable Reactives

Textual detects changes to basic types (int, float, str, bool) but not mutations to collections:

```python
class MyWidget(Widget):
    names: reactive[list[str]] = reactive(list)  # callable default avoids shared mutable

    def add_name(self, name: str) -> None:
        self.names.append(name)
        self.mutate_reactive(MyWidget.names)  # notify Textual of the mutation
```

- Assigning a new list triggers reactivity normally.
- Mutating an existing list/dict/set requires calling `mutate_reactive(ClassName.attribute)` after the mutation.
- Use a callable default (e.g. `reactive(list)`) so each instance gets its own list.

---

## Data Binding

Bind a child widget's reactive to a parent's reactive so changes propagate automatically:

```python
from textual.reactive import reactive
from textual.widget import Widget


class WorldClock(Widget):
    clock_time: reactive[str] = reactive("")

    def render(self) -> str:
        return self.clock_time


class WorldClockApp(App):
    time: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield WorldClock().data_bind(clock_time=WorldClockApp.time)
        yield WorldClock().data_bind(clock_time=WorldClockApp.time)
```

- `widget.data_bind(child_attr=ParentClass.parent_attr)` connects the attributes.
- When attributes share the same name: `widget.data_bind(WorldClockApp.time)`.
- Data binding is one-directional: parent changes propagate to child; child changes do not propagate to parent.
- `data_bind` returns the widget, so it can be chained with `yield`.
