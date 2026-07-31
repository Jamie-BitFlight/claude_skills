# Prompt Skill

## Purpose
Create beautiful, interactive terminal prompts using questionary.

## Instructions

### Custom Style
```python
import questionary
from questionary import Style

PROMPT_STYLE = Style([
    ("qmark", "bold cyan"),
    ("question", "bold"),
    ("answer", "cyan"),
    ("pointer", "cyan bold"),
    ("highlighted", "bold"),
    ("selected", ""),
    ("separator", "dim"),
    ("instruction", "dim"),
])
```

### Text Input
```python
def prompt_title() -> str:
    """Prompt for task title."""
    return questionary.text(
        "Task title:", validate=lambda t: len(t.strip()) > 0 or "Title cannot be empty", style=PROMPT_STYLE
    ).ask()


def prompt_description() -> str:
    """Prompt for optional description."""
    return questionary.text("Description (optional):", multiline=False, style=PROMPT_STYLE).ask() or ""
```

### Selection Menu
```python
def prompt_priority() -> str:
    """Prompt for priority selection."""
    choices = [
        questionary.Choice("Low", value="low"),
        questionary.Choice("Medium", value="medium"),
        questionary.Choice("High", value="high"),
        questionary.Choice("Urgent", value="urgent"),
    ]
    return questionary.select("Priority level:", choices=choices, default="medium", style=PROMPT_STYLE).ask()


def prompt_main_menu() -> str:
    """Main menu selection."""
    choices = [
        questionary.Choice("Add Task", value="add"),
        questionary.Choice("List Tasks", value="list"),
        questionary.Choice("Search", value="search"),
        questionary.Choice("Complete Task", value="complete"),
        questionary.Choice("Delete Task", value="delete"),
        questionary.Choice("Settings", value="settings"),
        questionary.Choice("Exit", value="exit"),
    ]
    return questionary.select("What would you like to do?", choices=choices, style=PROMPT_STYLE).ask()
```

### Checkbox (Multiple Selection)
```python
def prompt_tags(existing_tags: list = None) -> list:
    """Prompt for tag selection."""
    default_tags = ["work", "personal", "urgent", "shopping", "health"]
    all_tags = list(set(default_tags + (existing_tags or [])))

    choices = [questionary.Choice(tag, value=tag) for tag in sorted(all_tags)]

    return questionary.checkbox("Select tags:", choices=choices, style=PROMPT_STYLE).ask() or []
```

### Confirmation
```python
def confirm_action(message: str, default: bool = False) -> bool:
    """Confirm an action."""
    return questionary.confirm(message, default=default, style=PROMPT_STYLE).ask()


def confirm_delete(task_title: str) -> bool:
    """Confirm task deletion."""
    return confirm_action(f"Delete '{task_title}'? This cannot be undone.", default=False)
```

### Autocomplete
```python
def prompt_search(suggestions: list = None) -> str:
    """Search with autocomplete."""
    return questionary.autocomplete("Search tasks:", choices=suggestions or [], style=PROMPT_STYLE).ask()
```

### Complete Task Form
```python
def prompt_add_task(existing_tags: list = None) -> dict:
    """Complete form for adding a task."""

    # Get title
    title = questionary.text(
        "Task title:", validate=lambda t: len(t.strip()) > 0 or "Title is required", style=PROMPT_STYLE
    ).ask()

    if not title:  # User cancelled
        return None

    # Get description
    description = questionary.text("Description (optional):", style=PROMPT_STYLE).ask()

    # Get priority
    priority = questionary.select(
        "Priority:",
        choices=[
            questionary.Choice("Low", value="low"),
            questionary.Choice("Medium", value="medium"),
            questionary.Choice("High", value="high"),
            questionary.Choice("Urgent", value="urgent"),
        ],
        default="medium",
        style=PROMPT_STYLE,
    ).ask()

    # Get tags
    tags = (
        questionary.checkbox(
            "Tags:", choices=list(set(["work", "personal", "urgent"] + (existing_tags or []))), style=PROMPT_STYLE
        ).ask()
        or []
    )

    # Ask about due date
    has_due = questionary.confirm("Set a due date?", default=False, style=PROMPT_STYLE).ask()

    due_date = None
    if has_due:
        due_date = questionary.text(
            "Due date (YYYY-MM-DD):", validate=lambda d: _validate_date(d), style=PROMPT_STYLE
        ).ask()

    return {
        "title": title.strip(),
        "description": description.strip() if description else None,
        "priority": priority,
        "tags": tags,
        "due_date": due_date,
    }


def _validate_date(date_str: str) -> bool:
    """Validate date format."""
    if not date_str:
        return True
    try:
        from datetime import datetime

        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD"
```

### Task Selection
```python
def prompt_select_task(tasks: list) -> int:
    """Select a task from list."""
    if not tasks:
        return None

    choices = [questionary.Choice(f"[{t['id']}] {t['title']} ({t['priority']})", value=t["id"]) for t in tasks]

    return questionary.select("Select a task:", choices=choices, style=PROMPT_STYLE).ask()
```

## Best Practices

- Always provide a custom style for consistency
- Add validation to text inputs
- Use Choice objects for cleaner value mapping
- Handle None returns (user cancellation)
- Group related prompts into form functions
- Provide sensible defaults
- Add confirmation for destructive actions
