---
category: project-metadata
topics: [entry-points, GUI-scripts, graphical-interface, Windows-compatibility]
related: [entry-points-cli, entry-points-plugins]
---

# Entry Points: GUI Scripts

GUI (Graphical User Interface) scripts are similar to CLI scripts but receive special handling on Windows to launch without displaying a console window.

When Claude helps users configure GUI applications, explain that GUI scripts use identical configuration syntax to CLI scripts in the `[project.gui-scripts]` table, but receive special treatment on Windows to hide the console window. On Unix-like systems, GUI scripts behave identically to CLI scripts. Recommend GUI scripts for applications using Tkinter, PyQt, or other graphical frameworks.

## Configuration

Define GUI scripts in the `[project.gui-scripts]` table:

```toml

[project.gui-scripts]
my-app = "my_package.gui:main"

```

## Windows Behavior

On Windows, GUI scripts are executed without a console window, providing a native application experience. On Unix-like systems, GUI scripts behave identically to CLI scripts.

## Examples

### Tkinter Application

```toml

[project.gui-scripts]
myapp = "myapp.gui:main"

```

With implementation:

```python

import tkinter as tk

def main():
    root = tk.Tk()
    root.title("My App")
    root.mainloop()
    return 0

```

### PyQt Application

```toml

[project.gui-scripts]
editor = "myeditor.main:launch"

```

### Multiple GUI Applications

```toml

[project.gui-scripts]
app-ui = "myapp.ui:launch"
app-settings = "myapp.settings:launch"

```

## Function Requirements

Same as CLI scripts:

1. Accept no required arguments
2. Return exit code or None
3. Handle exceptions appropriately

## Platform-Specific Considerations

- **Windows**: No console window displayed
- **macOS**: Runs as normal executable
- **Linux**: Runs as normal executable

## Best Practices

1. Handle window closing events gracefully
2. Implement proper error dialogs for user feedback
3. Test on target platforms (especially Windows)
4. Use established GUI frameworks (Tkinter, PyQt, wxPython)
5. Provide meaningful error messages in dialogs

## CLI vs. GUI Scripts

| Aspect         | CLI Scripts       | GUI Scripts       |
| -------------- | ----------------- | ----------------- |
| Console Window | Always shown      | Hidden on Windows |
| Use Case       | Terminal commands | GUI applications  |
| Output         | stdout/stderr     | GUI dialogs       |
| Exit Codes     | Important         | Less critical     |

## Dynamic Entry Points

GUI entry points can be declared dynamic:

```toml

[project]
dynamic = ["gui-scripts"]

[tool.hatch.metadata.hooks.custom]

```

## Related Configuration

- `entry-points-cli.md`
- `entry-points-plugins.md`
- `dynamic-metadata.md`
