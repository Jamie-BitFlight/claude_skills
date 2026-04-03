---
category: project-metadata
topics: [entry-points, plugins, plugin-discovery, extensibility, plugin-namespaces]
related: [entry-points-cli, entry-points-gui]
---

# Plugin Entry Points

Plugin entry points provide a mechanism for packages to advertise components they provide for discovery and use by other code, enabling extensible applications through plugin systems.

When Claude helps users create plugin systems, explain that plugin entry points enable dynamic discovery of components at runtime. Each namespace under `[project.entry-points.<namespace>]` groups related plugins. Other packages can query these entry points using `importlib.metadata.entry_points()` to discover and load plugins dynamically. Show both the publisher (plugin implementation) and consumer (plugin discovery) perspectives.

## Configuration

Plugin entry points are defined under `[project.entry-points.<namespace>]`:

```toml

[project.entry-points.my-app-plugins]
plugin-name = "my_package.plugins:Plugin"
another = "my_package.plugins:AnotherPlugin"

```

## How Plugin Discovery Works

Other packages can discover plugins through entry points:

```python

from importlib.metadata import entry_points

# Get all plugins in a namespace
plugins = entry_points(group="my-app-plugins")

for plugin in plugins:
    plugin_class = plugin.load()
    print(f"{plugin.name}: {plugin_class}")

```

## Practical Examples

### Web Framework Middleware

```toml

[project.entry-points."my-framework.middleware"]
cors = "my_package.middleware:CORS"
auth = "my_package.middleware:Authentication"
logging = "my_package.middleware:RequestLogging"

```

### Testing Framework Plugins

```toml

[project.entry-points."pytest"]
my_plugin = "my_package.pytest_plugin"

```

### Documentation Generation

```toml

[project.entry-points."sphinx.html_themes"]
my_theme = "my_package.theme"

```

### CLI Plugin System

```toml

[project.entry-points."my-cli.commands"]
init = "my_package.commands:InitCommand"
deploy = "my_package.commands:DeployCommand"
backup = "my_package.commands:BackupCommand"

```

## Entry Point Format

Format: `name = "module.path:object"`

- `name`: Plugin identifier
- `module.path`: Module containing the plugin
- `object`: Class, function, or object name (optional if module itself is the plugin)

### Variations

```toml

# With class
plugin = "my_package.plugins:MyPlugin"

# With function
handler = "my_package.handlers:handle_request"

# Just module (module must be importable and usable directly)
theme = "my_package.themes.blue"

```

## Plugin Discovery Pattern

Typical plugin system implementation:

```python

from importlib.metadata import entry_points

def load_plugins(group_name):
    plugins = {}
    for entry_point in entry_points(group=group_name):
        try:
            plugin = entry_point.load()
            plugins[entry_point.name] = plugin
        except Exception as e:
            print(f"Failed to load {entry_point.name}: {e}")
    return plugins

# Usage
middleware = load_plugins("my-app.middleware")
for name, plugin in middleware.items():
    print(f"Loaded: {name}")

```

## Multiple Namespaces

A package can provide multiple plugin namespaces:

```toml

[project.entry-points."app.filters"]
uppercase = "my_package.filters:UppercaseFilter"
lowercase = "my_package.filters:LowercaseFilter"

[project.entry-points."app.exporters"]
json = "my_package.exporters:JsonExporter"
csv = "my_package.exporters:CsvExporter"

[project.entry-points."app.validators"]
email = "my_package.validators:EmailValidator"
url = "my_package.validators:UrlValidator"

```

## Best Practices

1. Use descriptive namespace names (e.g., `my-app.plugins` not just `plugins`)
2. Document expected plugin interface
3. Handle plugin loading failures gracefully
4. Provide plugin examples in documentation
5. Version your plugin API for backward compatibility
6. Use clear, consistent naming conventions

## Dynamic Entry Points

Entry points can be declared dynamic:

```toml

[project]
dynamic = ["entry-points"]

[tool.hatch.metadata.hooks.custom]

```

## Related Configuration

- `entry-points-cli.md`
- `entry-points-gui.md`
- `dynamic-metadata.md`
