# Interactivity: Events, Bindings, and Actions

## Key Bindings

Define keyboard shortcuts:

```python
from textual.app import App
from textual.binding import Binding


class MyApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),  # key, action, description
        ("s", "save", "Save"),
        ("ctrl+c", "copy", "Copy"),
        Binding("f1", "help", "Help", show=True, priority=True),
    ]

    def action_save(self) -> None:
        """Actions are methods prefixed with 'action_'."""
        self.notify("Saved!")

    def action_copy(self) -> None:
        self.notify("Copied!")

    def action_help(self) -> None:
        self.notify("Help content...")
```

### Binding Options

```python
Binding(
    key="f1",
    action="help",
    description="Help",
    show=True,  # Show in footer (default: True)
    priority=True,  # Prioritize over widget bindings
)
```

### Dynamic Bindings

Refresh bindings when state changes:

```python
class MyApp(App):
    page = reactive(0, bindings=True)  # Auto-refresh bindings

    def check_action(self, action: str, parameters) -> bool | None:
        """Control action availability."""
        if action == "next" and self.page >= MAX_PAGES:
            return None  # Disables and dims the key
        if action == "previous" and self.page == 0:
            return None
        return True  # Enabled
```

Or manually refresh:

```python
def update_state(self):
    self.state = "new_state"
    self.refresh_bindings()  # Update footer
```

## Mouse Events

Handle mouse interactions:

```python
from textual import events


class MyWidget(Widget):
    def on_click(self, event: events.Click) -> None:
        """Widget was clicked."""
        self.notify(f"Clicked at {event.x}, {event.y}")

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Mouse moved over widget."""
        pass

    def on_enter(self, event: events.Enter) -> None:
        """Mouse entered widget."""
        self.add_class("hover")

    def on_leave(self, event: events.Leave) -> None:
        """Mouse left widget."""
        self.remove_class("hover")
```

## Keyboard Events

Handle key presses:

```python
from textual import events


class MyApp(App):
    def on_key(self, event: events.Key) -> None:
        """Any key pressed."""
        if event.key == "escape":
            self.exit()
        elif event.key == "space":
            self.toggle_pause()

    def key_r(self, event: events.Key) -> None:
        """Specific key handler (press 'r')."""
        self.reset()
```

## Focus Events

Track focus changes:

```python
def on_focus(self, event: events.Focus) -> None:
    """Widget gained focus."""
    self.border_title = "Focused"


def on_blur(self, event: events.Blur) -> None:
    """Widget lost focus."""
    self.border_title = ""
```

Programmatic focus:

```python
widget.focus()  # Give focus to widget
widget.can_focus = True  # Enable focusing (default for inputs)
```

## Widget Messages

Handle messages from specific widgets:

```python
from textual.widgets import Button, Input, Switch


def on_button_pressed(self, event: Button.Pressed) -> None:
    """Any button pressed."""
    button_id = event.button.id
    self.notify(f"Button {button_id} pressed")


def on_input_changed(self, event: Input.Changed) -> None:
    """Input text changed."""
    self.update_preview(event.value)


def on_input_submitted(self, event: Input.Submitted) -> None:
    """User pressed Enter in input."""
    self.process(event.value)


def on_switch_changed(self, event: Switch.Changed) -> None:
    """Switch toggled."""
    self.feature_enabled = event.value


def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    """Row in table selected."""
    row_key = event.row_key
```

### Message Naming Convention

Handler method: `on_{widget_type}_{message_name}`
- Converts to snake_case
- Example: `Button.Pressed` → `on_button_pressed`
- Custom widget: `MyWidget.ValueChanged` → `on_my_widget_value_changed`

## Custom Messages

Define custom messages for your widgets:

```python
from textual.message import Message
from textual.widget import Widget


class Card(Widget):
    class Selected(Message):
        """Posted when card is selected."""

        def __init__(self, card_id: str, value: int) -> None:
            super().__init__()
            self.card_id = card_id
            self.value = value

    def on_click(self) -> None:
        self.post_message(self.Selected(self.id, self.value))


# Handle in parent
def on_card_selected(self, event: Card.Selected) -> None:
    self.notify(f"Card {event.card_id} (value: {event.value}) selected")
```

## Message Control

### Stop Propagation

Prevent message from bubbling to parent:

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    event.stop()  # Don't propagate to parent
    # Handle locally
```

### Prevent Messages

Temporarily suppress messages:

```python
with widget.prevent(Switch.Changed):
    widget.value = True  # Won't emit Changed message
```

Useful when programmatically updating to avoid infinite loops.

## Actions

Actions are methods that can be triggered by bindings or programmatically:

```python
class MyApp(App):
    BINDINGS = [("n", "next_page", "Next"), ("p", "prev_page", "Previous")]

    def action_next_page(self) -> None:
        self.page += 1
        self.refresh_view()

    def action_prev_page(self) -> None:
        self.page -= 1
        self.refresh_view()
```

### Parameterized Actions

Pass parameters to actions:

```python
BINDINGS = [("r", "add_color('red')", "Red"), ("g", "add_color('green')", "Green"), ("b", "add_color('blue')", "Blue")]


def action_add_color(self, color: str) -> None:
    self.add_widget(ColorBar(color))
```

### Programmatic Action Calls

```python
self.run_action("save")  # Trigger action by name
```

## Notifications

Show temporary messages to user:

```python
self.notify("File saved successfully!")
self.notify("Error occurred", severity="error")
self.notify("Warning!", severity="warning")
self.notify("Info message", severity="information", timeout=5)
```

## Timers

Schedule repeated actions:

```python
def on_mount(self) -> None:
    self.set_interval(1.0, self.update_timer)  # Every 1 second


def update_timer(self) -> None:
    self.elapsed += 1
    self.query_one("#timer").update(str(self.elapsed))
```

One-time delayed action:

```python
self.set_timer(2.0, self.delayed_action)  # After 2 seconds


def delayed_action(self) -> None:
    self.notify("Timer complete!")
```

## Example: Interactive Card Selection

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Label, Static
from textual.message import Message


class Card(Widget):
    DEFAULT_CSS = """
    Card {
        width: 12;
        height: 10;
        border: round white;
        background: $panel;
    }
    Card:hover {
        background: $boost;
    }
    Card.selected {
        border: double cyan;
        background: $accent;
    }
    """

    class Selected(Message):
        def __init__(self, card: "Card") -> None:
            super().__init__()
            self.card = card

    def __init__(self, suit: str, value: str) -> None:
        super().__init__()
        self.suit = suit
        self.value = value

    def compose(self) -> ComposeResult:
        yield Label(f"{self.value}\n{self.suit}")

    def on_click(self) -> None:
        self.post_message(self.Selected(self))


class CardGame(App):
    def compose(self) -> ComposeResult:
        with Horizontal(id="hand"):
            yield Card("♠", "A")
            yield Card("♥", "K")
            yield Card("♣", "Q")

    def on_card_selected(self, event: Card.Selected) -> None:
        # Deselect all
        for card in self.query(Card):
            card.remove_class("selected")
        # Select clicked
        event.card.add_class("selected")
        self.notify(f"Selected {event.card.value} of {event.card.suit}")
```
