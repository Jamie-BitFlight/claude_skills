# Textual Basics

## App Structure

Every Textual app follows this pattern:

```python
from textual.app import App, ComposeResult
from textual.widgets import Widget


class MyApp(App):
    """Docstring describing the app."""

    # Optional: Link to external CSS file
    CSS_PATH = "app.tcss"

    # Optional: Inline CSS
    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Widget()

    def on_mount(self) -> None:
        """Called when app is mounted and ready."""
        pass


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

## Compose Method

The `compose()` method yields widgets to add to the app. It's called once during initialization:

```python
def compose(self) -> ComposeResult:
    yield Header()
    yield ContentWidget()
    yield Footer()
```

## Mounting

- `on_mount()`: Called when the app/widget is fully mounted and ready
- `mount()`: Dynamically add widgets after app starts (returns a coroutine)

```python
async def on_key(self) -> None:
    # Must await when modifying mounted widgets
    await self.mount(NewWidget())
    self.query_one(Button).label = "Modified!"
```

## Reactive Attributes

Reactive attributes automatically update the UI when changed:

```python
from textual.reactive import reactive


class Counter(Widget):
    count = reactive(0)  # Initial value

    def watch_count(self, new_value: int) -> None:
        """Called automatically when count changes."""
        self.query_one(Label).update(f"Count: {new_value}")

    def increment(self) -> None:
        self.count += 1  # Triggers watch_count
```

### Reactive with Bindings

Set `bindings=True` to auto-refresh footer bindings when reactive changes:

```python
class MyApp(App):
    page = reactive(0, bindings=True)

    def check_action(self, action: str, parameters) -> bool | None:
        """Return None to disable action."""
        if action == "next" and self.page == MAX_PAGES:
            return None  # Dims the key in footer
        return True
```

## Querying Widgets

Find widgets in the DOM:

```python
# Get one widget (raises if not found)
button = self.query_one(Button)
button = self.query_one("#my-id")

# Get multiple widgets
all_buttons = self.query(Button)
for button in all_buttons:
    pass

# Get with CSS selector
widget = self.query_one("#container .special-class")
```

## Messages and Events

### Built-in Events

Handle with `on_<event>` methods:

```python
def on_mount(self) -> None:
    """When mounted."""
    pass


def on_key(self, event: events.Key) -> None:
    """Key pressed."""
    if event.key == "escape":
        self.exit()
```

### Widget Messages

Handle messages from child widgets:

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    """Button was clicked."""
    self.notify(f"Button {event.button.id} clicked!")


def on_input_changed(self, event: Input.Changed) -> None:
    """Input text changed."""
    self.value = event.value
```

### Custom Messages

Define custom messages in your widgets:

```python
from textual.message import Message


class MyWidget(Widget):
    class ValueChanged(Message):
        """Posted when value changes."""

        def __init__(self, value: int) -> None:
            super().__init__()
            self.value = value

    def update_value(self, new_value: int) -> None:
        self.value = new_value
        self.post_message(self.ValueChanged(new_value))


# Handle in parent
def on_my_widget_value_changed(self, event: MyWidget.ValueChanged) -> None:
    self.notify(f"New value: {event.value}")
```

## Preventing Message Propagation

Stop messages from bubbling to parent:

```python
def on_switch_changed(self, event: Switch.Changed) -> None:
    event.stop()  # Don't propagate to parent
    # Handle here
```

## Preventing Reactive Watchers

Temporarily prevent reactive watchers from firing:

```python
with self.prevent(MyWidget.ValueChanged):
    self.value = new_value  # Won't trigger watch_value or post message
```
