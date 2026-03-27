---
category: project-metadata
topics: [dynamic-metadata, dynamic-fields, build-time-injection, version-from-code]
related: [metadata-hooks, custom-hooks, basic-metadata]
---

# Dynamic Metadata Fields

Dynamic metadata fields are declared in the `dynamic` list when values are determined at build time rather than statically in pyproject.toml. This enables reading versions from code, generating classifiers, or customizing metadata based on environment.

When Claude helps users implement dynamic metadata, explain that any field can be declared as dynamic by listing it in the `dynamic` array. Each dynamic field requires corresponding configuration in the `[tool.hatch.*]` section or a metadata hook. Common use cases include reading version from source code files (via `[tool.hatch.version]`) or generating metadata dynamically (via metadata hooks). See `metadata-hooks.md` for hook-based approaches.

## Declaring Dynamic Fields

Specify which metadata fields are dynamic:

```toml

[project]
name = "my-package"
dynamic = ["version", "description", "readme"]

[tool.hatch.version]
path = "src/my_package/__about__.py"

[tool.hatch.metadata.hooks.custom]

```

## Supported Dynamic Fields

Common fields that can be dynamic:

- `version` - Project version
- `description` - Short description
- `readme` - README file reference
- `requires-python` - Python version requirements
- `license` - License specification
- `authors` - Package authors
- `maintainers` - Package maintainers
- `keywords` - Search keywords
- `classifiers` - Trove classifiers
- `urls` - Project URLs
- `scripts` - CLI entry points
- `gui-scripts` - GUI entry points
- `entry-points` - Plugin entry points
- `dependencies` - Required dependencies
- `optional-dependencies` - Feature groups

## Version as Dynamic Field

Most commonly, version is declared dynamic:

```toml

[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
path = "src/my_package/__about__.py"

```

Then in `src/my_package/__about__.py`:

```python
__version__ = "0.1.0"
```

## Multiple Dynamic Fields

```toml

[project]
name = "my-package"
dynamic = ["version", "description", "readme"]

[tool.hatch.version]
path = "src/my_package/__version__.py"

```

## Dynamic Dependencies

```toml

[project]
name = "my-package"
dynamic = ["dependencies"]

[tool.hatch.metadata.hooks.unidep]

```

## Why Use Dynamic Metadata?

1. **Single Source of Truth**: Version defined in one place (code)
2. **Consistency**: Automatic version synchronization
3. **Build-Time Customization**: Adapt metadata based on build environment
4. **Complex Logic**: Computed metadata based on conditions
5. **Conditional Dependencies**: Include dependencies based on Python version

## Comparison: Static vs. Dynamic

**Static (Recommended for simple cases):**

```toml
[project]
version = "1.0.0"
description = "My package description"
```

**Dynamic (For derived or complex metadata):**

```toml
[project]
dynamic = ["version", "description"]
[tool.hatch.metadata.hooks.custom]
```

## Related Configuration

- `custom-hooks.md` - Implementing dynamic metadata
- `metadata-hooks.md` - Hook system overview
- `basic-metadata.md` - Static field definitions
