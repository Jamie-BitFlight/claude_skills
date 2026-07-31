# Textual Advanced Patterns

This file covers Textual features absent from or underdocumented in the existing reference files.
All content is verified against the official Textual documentation.

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)
SOURCE: <https://textual.textualize.io/guide/events/> (accessed 2026-05-07)
SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)
SOURCE: <https://textual.textualize.io/guide/screens/> (accessed 2026-05-07)
SOURCE: <https://textual.textualize.io/guide/testing/> (accessed 2026-05-07)

---

## @on Decorator for Per-Widget Event Filtering

The `@on` decorator lets you bind an event handler to a specific widget identified by a CSS
selector. This eliminates `if event.button.id == "..."` chains in handlers.

```python
from textual import on
from textual.widgets import Button


class MyApp(App):
    def compose(self) -> ComposeResult:
        yield Button("Bell", id="bell")
        yield Button("Quit", id="quit")
        yield Button("Toggle dark", classes="toggle dark")

    @on(Button.Pressed, "#bell")
    def play_bell(self) -> None:
        self.bell()

    @on(Button.Pressed, "#quit")
    def quit_app(self) -> None:
        self.exit()

    @on(Button.Pressed, ".toggle.dark")
    def toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"
```

The selector is any CSS selector valid in Textual: `#id`, `.class`, `WidgetType`,
compound selectors. All `@on` handlers matching the message execute in definition order.
The `on_<name>` naming-convention handler runs last, after all decorated handlers.

Some messages expose additional attributes for matching beyond the sending widget. Access
these by passing a keyword argument matching the attribute name. For `TabbedContent.TabActivated`
the `pane` attribute is matchable:

```python
@on(TabbedContent.TabActivated, pane="#home")
def home_tab(self) -> None:
    self.log("Switched to home tab")
```

SOURCE: <https://textual.textualize.io/guide/events/> (accessed 2026-05-07)

---

## Reactive Advanced Parameters

### recompose=True

Setting `recompose=True` on a reactive causes Textual to remove all child widgets and call
`compose()` again whenever the reactive value changes. Use this for dynamically generated
child lists.

```python
class MultiGreet(Widget):
    names: reactive[list[str]] = reactive(list, recompose=True)

    def compose(self) -> ComposeResult:
        for name in self.names:
            yield Label(f"Hello, {name}!")

    def add_name(self, name: str) -> None:
        self.names.append(name)
        self.mutate_reactive(MultiGreet.names)
```

Caveat: recompose resets all child widget state. Do not use `recompose=True` with stateful
children such as `DataTable`, `Input`, or `TextArea` — their in-flight state is destroyed on
each recompose.

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

### layout=True

Setting `layout=True` triggers a CSS layout recalculation when the reactive value changes,
not just a content refresh. Required when a reactive change affects widget size — for
example, an auto-width widget whose displayed content changes length.

```python
class MyWidget(Widget):
    who = reactive("World", layout=True)
```

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

### var — Non-Refreshing Reactive

`var` creates a reactive-like attribute that does not trigger refresh or layout recalculation
on change. It still supports `watch_<name>` watchers. Use for internal state that has no
direct rendering effect.

```python
from textual.reactive import var


class MyWidget(Widget):
    internal_counter = var(0)  # watcher fires, but no refresh/layout
```

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

---

## Reactive Lifecycle Methods

### validate_<name> — Value Interception

Define `validate_<name>` to intercept and transform a value before it is set. The method
receives the incoming value and returns the value to actually store. Use to clamp ranges,
normalise strings, or reject invalid inputs.

```python
class Counter(Widget):
    count = reactive(0)

    def validate_count(self, value: int) -> int:
        return max(0, min(10, value))
```

Execution order for a reactive assignment: `compute_<name>` → `validate_<name>` → `watch_<name>`.

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

### compute_<name> — Derived Reactives

Define `compute_<name>` to derive a reactive value from other reactives. Textual caches the
result and recalculates whenever any reactive on the object changes. The computed reactive
cannot be assigned directly — it is always the result of the compute method.

```python
class ColorMixer(App):
    red = reactive(0)
    green = reactive(0)
    blue = reactive(0)
    color = reactive(Color.parse("transparent"))

    def compute_color(self) -> Color:
        return Color(self.red, self.green, self.blue).clamped

    def watch_color(self, color: Color) -> None:
        self.query_one("#swatch").styles.background = color
```

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

### watch_<name> Two-Argument Form

Watch methods accept either one argument (new value) or two arguments (old value, new value).
The two-argument form is useful for reverting or animating transitions.

```python
def watch_color(self, old_color: Color, new_color: Color) -> None:
    self.query_one("#old").styles.background = old_color
    self.query_one("#new").styles.background = new_color
```

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

---

## set_reactive() — Constructor-Safe Initialisation

Direct reactive assignment in `__init__` fires `watch_<name>` immediately. If the watcher
queries the DOM (e.g., `self.query_one(Label)`), it raises `NoMatches` because no widgets
have mounted yet. Use `set_reactive()` to set the initial value without invoking watchers.

```python
class Greeter(Widget):
    greeting: reactive[str] = reactive("Hello")
    who: reactive[str] = reactive("World")

    def __init__(self, greeting: str = "Hello", who: str = "World") -> None:
        super().__init__()
        self.set_reactive(Greeter.greeting, greeting)  # safe — no watcher fired
        self.set_reactive(Greeter.who, who)
```

`set_reactive` takes the class-level reactive descriptor (not a string) as first argument,
and the value as second argument.

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

---

## mutate_reactive() — Mutable Collections

Textual detects reactive changes by identity comparison. Mutating a list or dict in-place
(`.append()`, `[key] = value`, etc.) does not change the object's identity, so watchers and
recompose do not fire. Call `mutate_reactive()` after any in-place mutation.

```python
class NameList(Widget):
    names: reactive[list[str]] = reactive(list, recompose=True)

    def add_name(self, name: str) -> None:
        self.names.append(name)
        self.mutate_reactive(NameList.names)  # tells Textual the list changed
```

`mutate_reactive` takes the class-level descriptor, not a string.

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

---

## data_bind() — Parent-to-Child Reactive Binding

`data_bind()` connects a reactive on a parent app or widget to a reactive on a child widget.
When the parent reactive changes, the child reactive updates automatically. Binding is
unidirectional: parent changes flow to child, not the reverse.

```python
class WorldClock(Widget):
    clock_time: reactive[datetime] = reactive(datetime.now)


class WorldClockApp(App):
    time: reactive[datetime] = reactive(datetime.now)

    def compose(self) -> ComposeResult:
        # Bind WorldClock.clock_time to WorldClockApp.time (same name inferred)
        yield WorldClock("Europe/London").data_bind(WorldClockApp.time)
        yield WorldClock("Europe/Paris").data_bind(WorldClockApp.time)
```

When the child reactive name differs from the parent, use keyword arguments:

```python
yield WorldClock("UTC").data_bind(clock_time=WorldClockApp.time)
```

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

---

## Dynamic Watcher Registration

`self.watch()` registers a watcher callback on another widget's reactive at runtime, without
subclassing. Useful for reacting to reactives on third-party widgets.

```python
def on_mount(self) -> None:
    counter = self.query_one(Counter)
    progress = self.query_one(ProgressBar)

    def update_progress(value: int) -> None:
        progress.update(progress=value)

    self.watch(counter, "counter", update_progress)
```

SOURCE: <https://textual.textualize.io/guide/reactivity/> (accessed 2026-05-07)

---

## @work Decorator — Idiomatic Worker API

The `@work` decorator is the primary way to create workers in Textual. It wraps an async or
threaded function and automatically creates and starts a worker when the method is called —
no `await` is needed at the call site.

```python
from textual import work


class WeatherApp(App):
    # Async worker — for I/O-bound tasks using async libraries
    @work(exclusive=True)
    async def update_weather(self, city: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://wttr.in/{city}")
            self.query_one("#weather", Static).update(response.text)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.update_weather(event.value)  # no await — work handles it
```

`exclusive=True` cancels any prior workers in the same group before starting the new one.
This prevents stale results from earlier requests overwriting newer ones.

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)

### thread=True for Non-Async Functions

Applying `@work` to a regular `def` function requires `thread=True`. Textual raises an
exception if `@work` is applied to a non-async function without `thread=True`.

```python
from textual.worker import get_current_worker


class FileApp(App):
    @work(exclusive=True, thread=True)
    def process_file(self, path: str) -> None:
        worker = get_current_worker()
        result = expensive_computation(path)
        if not worker.is_cancelled:
            self.call_from_thread(self.display_result, result)
```

In a thread worker, direct widget method calls and reactive assignments are unsafe.
Use `call_from_thread()` for single calls, or `post_message()` for multiple updates.

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)

---

## get_current_worker() — Cancellation Checks in Thread Workers

Within a thread worker body, call `get_current_worker()` to obtain the `Worker` instance.
Check `worker.is_cancelled` before performing UI updates to avoid touching the DOM after
the worker has been cancelled.

```python
from textual.worker import get_current_worker


@work(thread=True)
def stream_results(self) -> None:
    worker = get_current_worker()
    for chunk in generate_results():
        if worker.is_cancelled:
            return
        self.post_message(ResultChunk(chunk))
```

For async workers, cancellation arrives as `asyncio.CancelledError` raised inside the
coroutine — check `is_cancelled` is only the idiomatic pattern for thread workers.

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)

---

## post_message() is Thread-Safe

Direct widget method calls from thread workers are not safe, but `post_message()` is
explicitly documented as thread-safe. For thread workers that need to send multiple updates
to the UI, posting custom messages is preferred over multiple `call_from_thread()` calls.

```python
from textual.message import Message


class ResultChunk(Message):
    def __init__(self, data: str) -> None:
        self.data = data
        super().__init__()


class ProcessorApp(App):
    @work(thread=True)
    def background_processor(self) -> None:
        worker = get_current_worker()
        for item in expensive_generator():
            if worker.is_cancelled:
                return
            self.post_message(ResultChunk(item))  # thread-safe

    def on_result_chunk(self, message: ResultChunk) -> None:
        # runs on main thread — safe to update widgets directly
        self.query_one(Log).write_line(message.data)
```

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)

---

## Worker Error Handling — exit_on_error=False

By default, an unhandled exception in a worker exits the app immediately and displays a
traceback. Set `exit_on_error=False` (either via `@work` or `run_worker()`) to keep the app
alive and handle the failure via `on_worker_state_changed`.

```python
@work(exit_on_error=False)
async def risky_fetch(self) -> None:
    result = await unreliable_api()
    self.display(result)


def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
    if event.state == WorkerState.ERROR:
        self.notify(f"Failed: {event.worker.error}", severity="error")
    elif event.state == WorkerState.SUCCESS:
        self.log("Worker completed successfully")
```

`event.worker.error` contains the original exception object.

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)

---

## Worker Lifetime and Scoping

Workers are tied to the DOM node (widget, screen, or app) where they were created. When a
widget is removed or a screen is popped, all workers created on that node are cancelled
automatically. `Worker.StateChanged` events are sent to the creating node, so if a screen
is popped before its worker finishes, the event handler on the screen will not fire on the
app level.

Create workers on the app when you need them to outlive screens.

SOURCE: <https://textual.textualize.io/guide/workers/> (accessed 2026-05-07)

---

## Screen MODES — Multi-Stack Navigation

`MODES` enables an app with multiple independent screen stacks. Each mode maintains its own
push/pop history. Switching modes makes the top screen of the destination stack visible
without disturbing the other stacks.

```python
class MyApp(App):
    MODES = {
        "dashboard": DashboardScreen,  # pass the class, not an instance
        "settings": SettingsScreen,
        "help": HelpScreen,
    }
    DEFAULT_MODE = "dashboard"

    BINDINGS = [
        ("d", "switch_mode('dashboard')", "Dashboard"),
        ("s", "switch_mode('settings')", "Settings"),
        ("h", "switch_mode('help')", "Help"),
    ]
```

The `SCREENS` dict also takes classes (callables), not instances:

```python
class BSODApp(App):
    SCREENS = {"bsod": BSOD}  # correct — class reference
    # SCREENS = {"bsod": BSOD()}  # wrong — instance is not documented API
```

SOURCE: <https://textual.textualize.io/guide/screens/> (accessed 2026-05-07)
SOURCE: <https://textual.textualize.io/api/app/> (accessed 2026-05-07)

---

## push_screen_wait() — Worker Requirement

`push_screen_wait()` pushes a screen and suspends execution until `screen.dismiss()` is
called, returning the dismissed value. It must be called from inside a `@work` worker.
Calling it from a plain `async def` event handler is incorrect — the waiting would block app
updates.

```python
from textual import work
from textual.screen import ModalScreen


class ConfirmDialog(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Button("Yes", id="yes")
        yield Button("No", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class MyApp(App):
    @work
    async def confirm_action(self) -> None:
        confirmed = await self.push_screen_wait(ConfirmDialog())
        if confirmed:
            self.perform_action()
```

SOURCE: <https://textual.textualize.io/guide/screens/> (accessed 2026-05-07)

---

## Testing — asyncio_mode Configuration

The official Textual testing guide uses bare `async def` test functions without
`@pytest.mark.asyncio`. This requires `asyncio_mode = "auto"` in pytest configuration.

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

With this configuration all async test functions run automatically without decoration.

```python
from my_app import MyApp


async def test_app_starts():
    app = MyApp()
    async with app.run_test() as pilot:
        assert app.screen is not None


async def test_button_click():
    app = MyApp()
    async with app.run_test() as pilot:
        await pilot.click("#submit")
        await pilot.pause()  # wait for all pending messages to process
        assert app.query_one("#result").renderable == "done"


async def test_custom_size():
    app = MyApp()
    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.press("ctrl+q")
```

SOURCE: <https://textual.textualize.io/guide/testing/> (accessed 2026-05-07)

---

## Pilot API — pause(), hover(), and Click Modifiers

`pilot.pause()` waits until all pending messages in the message queue are processed. Call it
after any action that posts messages before asserting state.

```python
await pilot.pause()  # flush all pending messages
await pilot.pause(delay=0.5)  # sleep 0.5 s, then flush messages
```

`pilot.hover()` simulates a mouse hover, useful for triggering `:hover` pseudo-class
styles or `on_mouse_enter` / `on_mouse_leave` handlers.

```python
await pilot.hover("#number-5")
```

`pilot.click()` supports offset positioning and keyboard modifiers:

```python
await pilot.click("#slider", offset=(10, 0))  # click 10 cells right of widget origin
await pilot.click(Button, times=2)  # double-click
await pilot.click(Button, control=True)  # Ctrl+click
```

SOURCE: <https://textual.textualize.io/guide/testing/> (accessed 2026-05-07)

---

## Snapshot Testing with pytest-textual-snapshot

Snapshot tests compare the rendered terminal output of an app against a saved baseline image.
Install the plugin:

```bash
pip install pytest-textual-snapshot
```

Basic snapshot test — pass the path to the app file:

```python
def test_my_app_renders(snap_compare):
    assert snap_compare("src/my_app.py")
```

Snapshot with key presses applied before capture:

```python
def test_my_app_after_keys(snap_compare):
    assert snap_compare("src/my_app.py", press=["ctrl+d", "tab"])
```

Snapshot with a custom terminal size:

```python
def test_my_app_narrow(snap_compare):
    assert snap_compare("src/my_app.py", terminal_size=(40, 24))
```

Snapshot with async setup code run via pilot before capture:

```python
def test_my_app_hover(snap_compare):
    async def run_before(pilot) -> None:
        await pilot.hover("#number-5")

    assert snap_compare("src/my_app.py", run_before=run_before)
```

On first run, `snap_compare` creates the baseline snapshot and the test fails (no baseline to
compare against). Review the generated HTML report to verify the rendering is correct, then
accept the baseline:

```bash
pytest --snapshot-update
```

Subsequent runs fail if any pixel of the rendered output changes, providing visual regression
protection.

SOURCE: <https://textual.textualize.io/guide/testing/> (accessed 2026-05-07)
SOURCE: <https://github.com/Textualize/pytest-textual-snapshot> (accessed 2026-05-07)
