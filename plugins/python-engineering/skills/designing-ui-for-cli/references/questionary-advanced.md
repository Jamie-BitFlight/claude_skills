# questionary Advanced Patterns

Advanced questionary features not covered in questionary-patterns.md. All content verified against
official docs (accessed 2026-05-07).

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html>
SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html>
SOURCE: <https://questionary.readthedocs.io/en/stable/pages/api_reference.html>

---

## questionary.form() — idiomatic multi-question API

`questionary.form()` accepts keyword arguments where each key becomes the answer dict key and each
value is a `Question` returned by any prompt function. It returns a `Form` object. Calling
`.ask()` on the form presents questions sequentially and returns a dict mapping each key to its
answer. If the user cancels (Ctrl+C), `.ask()` returns `None`.

```python
import questionary

answers = questionary.form(
    title=questionary.text("Task title:", validate=lambda t: len(t.strip()) > 0 or "Title is required"),
    priority=questionary.select(
        "Priority:",
        choices=[
            questionary.Choice("Low", value="low"),
            questionary.Choice("Medium", value="medium"),
            questionary.Choice("High", value="high"),
        ],
    ),
    confirmed=questionary.confirm("Create task?", default=True),
).ask()

# answers is None if user cancelled, otherwise:
# {"title": "...", "priority": "low"|"medium"|"high", "confirmed": True|False}
if answers is None:
    return  # user pressed Ctrl+C
```

`Form.unsafe_ask()` is also available and does not catch `KeyboardInterrupt`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/api_reference.html> — Form class

---

## ask() vs unsafe_ask() — keyboard interrupt handling

Every `Question` and `Form` has two synchronous invocation methods and two async variants.

`ask()` catches `KeyboardInterrupt` (Ctrl+C), prints "Cancelled by user" (or a custom `kbi_msg`),
and returns `None`. Callers must check every `.ask()` return for `None`.

`unsafe_ask()` does not catch `KeyboardInterrupt`. The exception propagates to the caller, which
must handle it explicitly.

```python
# Safe — returns None on Ctrl+C
title = questionary.text("Title:").ask()
if title is None:
    return  # user cancelled

# Unsafe — caller handles KeyboardInterrupt
try:
    title = questionary.text("Title:").unsafe_ask()
except KeyboardInterrupt:
    return
```

The same distinction applies at the form and prompt level:

- `questionary.prompt()` — safe (catches Ctrl+C)
- `questionary.unsafe_prompt()` — unsafe (raises KeyboardInterrupt)
- `Form.ask()` — safe
- `Form.unsafe_ask()` — unsafe
- `Question.ask()` — safe
- `Question.unsafe_ask()` — unsafe

Async variants: `ask_async()` and `unsafe_ask_async()` follow the same safe/unsafe contract.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html#keyboard-interrupts>

---

## Additional prompt types

### password

`questionary.password()` prompts for text input where typed characters are replaced with `*`.
Supports the same `validate` parameter as `text()`.

```python
import re
import questionary


def validate_password(pw: str) -> bool | str:
    if len(pw) < 10:
        return "Password must be at least 10 characters"
    if re.search("[0-9]", pw) is None:
        return "Password must contain a number"
    if re.search("[A-Z]", pw) is None:
        return "Password must contain an upper-case letter"
    return True


secret = questionary.password("Enter password:", validate=validate_password).ask()
```

Parameters: `message`, `default`, `validate`, `qmark`, `style`.
Returns `str` or `None` on cancellation.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html#password>

### path

`questionary.path()` presents a text input with filesystem autocomplete. The `only_directories`
flag restricts suggestions to directories. The `file_filter` callable filters suggested completions
but does not validate the final typed path — combine it with `validate` to enforce constraints.

```python
from pathlib import Path
import questionary

config_path = questionary.path(
    "Config file path:", validate=lambda p: Path(p).exists() or "File not found", only_directories=False
).ask()
```

Parameters: `message`, `default`, `qmark`, `validate`, `completer`, `only_directories`,
`get_paths`, `file_filter`, `complete_style`, `style`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html#file-path>

### rawselect

`questionary.rawselect()` presents a numbered list where selection requires typing the item's
shortcut key and pressing Enter — no arrow keys. Useful in restricted terminal environments.

```python
action = questionary.rawselect(
    "What do you want to do?", choices=["Order a pizza", "Make a reservation", "Ask for opening hours"]
).ask()
```

Parameters: `message`, `choices`, `default`, `qmark`, `pointer`, `style`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html#raw-select>

### press_any_key_to_continue

`questionary.press_any_key_to_continue()` blocks until the user presses any key. Returns an empty
string. Useful as a pause before clearing the screen or before a destructive operation.

```python
questionary.press_any_key_to_continue("Press any key to continue...").ask()
```

Parameters: `message` (defaults to `"Press any key to continue..."`), `style`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html#press-any-key-to-continue>

### print

`questionary.print()` renders styled inline text without asking a question. The `style` parameter
is a plain style string (e.g. `"bold italic fg:darkred"`), not a `Style` object.

```python
questionary.print("Warning: this action is irreversible", style="bold fg:red")
```

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html#printing-formatted-text>

---

## skip_if() for conditional prompts

`Question.skip_if(condition, default)` returns `self`, enabling method chaining. When `condition`
is `True`, the question is skipped and `default` is returned without prompting the user. When
`condition` is `False`, the question is asked normally and `default` is ignored.

This replaces `if`/`else` guards around `.ask()` calls.

```python
# Instead of:
if show_deadline:
    deadline = questionary.text("Deadline (YYYY-MM-DD):").ask()
else:
    deadline = None

# Use:
deadline = questionary.text("Deadline (YYYY-MM-DD):").skip_if(not show_deadline, default=None).ask()
```

`condition` must be a `bool`, not a callable.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html#conditionally-skip-questions>

---

## Validator class pattern

The `Validator` subclass pattern provides cursor-positioned error messages. The `document`
argument is a prompt_toolkit `Document` object. Access typed text via `document.text`.

```python
from questionary import Validator, ValidationError


class NonEmptyValidator(Validator):
    def validate(self, document):
        if len(document.text.strip()) == 0:
            raise ValidationError(message="Value cannot be empty", cursor_position=len(document.text))


title = questionary.text("Task title:", validate=NonEmptyValidator).ask()
```

The lambda form (`validate=lambda text: True if len(text) > 0 else "Error"`) is simpler and
sufficient when cursor positioning is not needed. `checkbox()` does not support `Validator`
subclasses — only callables returning `bool` or `str`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html#validation>

---

## Choice(checked=True) — pre-selected checkbox items

`questionary.Choice(title, checked=True)` pre-selects a choice in a `checkbox()` prompt. The
`checked` attribute controls the initial selection state.

```python
choices = [
    questionary.Choice("work", checked=True),  # pre-selected
    questionary.Choice("personal", checked=False),
    questionary.Choice("urgent"),  # not pre-selected by default
]
tags = questionary.checkbox("Select tags:", choices=choices).ask() or []
```

`checked` is only meaningful in `checkbox()` — it has no effect in `select()` or `rawselect()`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/api_reference.html#questionary.Choice>

---

## Choice(disabled="reason") — non-selectable items

When `disabled` is set to a non-empty string, the choice is displayed but cannot be selected. The
string is shown as a reason.

```python
choices = [
    questionary.Choice("Standard plan"),
    questionary.Choice("Enterprise plan", disabled="Contact sales"),
    questionary.Choice("Trial (expired)", disabled="Upgrade required"),
]
plan = questionary.select("Choose a plan:", choices=choices).ask()
```

Style the disabled appearance with the `'disabled'` token in `PROMPT_STYLE`:

```python
from questionary import Style

PROMPT_STYLE = Style([
    ("qmark", "fg:#FF00FF bold"),
    ("question", "fg:#00FFFF bold"),
    ("answer", "fg:#00FF00 bold"),
    ("pointer", "fg:#FF00FF bold"),
    ("highlighted", "fg:#00FFFF bold"),
    ("selected", "fg:#00FF00"),
    ("separator", "fg:#888888"),
    ("instruction", "fg:#888888"),
    ("text", "fg:#FFFFFF"),
    ("disabled", "fg:#555555 italic"),  # required for disabled choices to render correctly
])
```

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/api_reference.html#questionary.Choice>
SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html#themes-styling>

---

## Separator in choice lists

`questionary.Separator()` places a visual divider in `select()`, `rawselect()`, or `checkbox()`
choice lists. The default text is `"---------------"`. Pass a string to customize it.

```python
choices = [
    questionary.Choice("Low priority"),
    questionary.Choice("Medium priority"),
    questionary.Separator(),  # default separator line
    questionary.Separator("--- Urgent ---"),  # custom separator text
    questionary.Choice("Critical"),
    questionary.Choice("Blocker (premium)", disabled="Upgrade required"),
]
priority = questionary.select("Priority:", choices=choices).ask()
```

Separators are not selectable and do not appear in the return value.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/api_reference.html#questionary.Separator>

---

## questionary.prompt() — dict-style form with when and filter

`questionary.prompt()` accepts a list of question config dicts. Each dict requires `type`, `name`,
and `message`. Optional keys include `when` (conditional display) and `filter` (answer
transformation).

`when` receives the current answers dict and must return a bool. If `False`, the question is
skipped and no key is added to answers.

`filter` receives the raw user input string and returns the value stored in answers.

```python
from questionary import prompt, Separator

questions = [
    {"type": "confirm", "name": "advanced", "message": "Enable advanced options?", "default": False},
    {
        "type": "text",
        "name": "timeout",
        "message": "Connection timeout (seconds):",
        "when": lambda answers: answers["advanced"],
        "filter": lambda val: int(val),
        "validate": lambda val: val.isdigit() or "Enter a number",
    },
    {"type": "select", "name": "format", "message": "Output format:", "choices": ["json", Separator(), "csv", "plain"]},
]

answers = prompt(questions)
# answers["timeout"] is an int if advanced=True, else the key is absent
```

`questionary.prompt()` is safe (catches Ctrl+C). `questionary.unsafe_prompt()` raises
`KeyboardInterrupt`.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html#create-questions-from-dictionaries>

---

## 'disabled' Style token

The `'disabled'` token styles choices created with `Choice(disabled="reason")`. Without it,
disabled choices render with the default terminal color, making them visually indistinguishable
from enabled choices.

The official example from the docs uses `('disabled', 'fg:#858585 italic')`.

```python
from questionary import Style

custom_style = Style([
    ("qmark", "fg:#673ab7 bold"),
    ("question", "bold"),
    ("answer", "fg:#f44336 bold"),
    ("pointer", "fg:#673ab7 bold"),
    ("highlighted", "fg:#673ab7 bold"),
    ("selected", "fg:#cc5454"),
    ("separator", "fg:#cc5454"),
    ("instruction", ""),
    ("text", ""),
    ("disabled", "fg:#858585 italic"),  # for disabled choices
])
```

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/advanced.html#themes-styling>

---

## autocomplete choices accepts only List[str]

`questionary.autocomplete()` `choices` parameter type is `List[str]`. It does not accept
`Choice` objects or `Separator` objects, unlike `select()` and `checkbox()`.

```python
# Correct
suggestions = ["apple", "banana", "cherry"]
result = questionary.autocomplete("Pick a fruit:", choices=suggestions).ask()

# Wrong — Choice objects are not accepted
result = questionary.autocomplete(
    "Pick a fruit:",
    choices=[questionary.Choice("apple", value="apple")],  # raises TypeError
).ask()
```

Use `select()` instead of `autocomplete()` when `Choice` objects or `Separator` objects are needed.

The `meta_information` parameter accepts `Dict[str, Any]` to annotate choices in the completion
menu. The `ignore_case` (default `True`) and `match_middle` (default `True`) parameters control
matching behavior.

SOURCE: <https://questionary.readthedocs.io/en/stable/pages/types.html#autocomplete>
