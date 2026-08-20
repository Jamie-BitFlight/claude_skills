# clang-format Configuration Skill

A comprehensive skill for configuring clang-format to format C/C++/Java/JavaScript/JSON/Objective-C/Protobuf/C# code.

## Navigation

### Quick Access

- [CLI Usage](cli-usage.md) - Command-line tools, flags, and integrations
- [Quick Reference](quick-reference.md) - Common patterns and complete examples

### Style Options by Category

1. [Alignment Options](01-alignment.md) - Align code elements consistently
2. [Breaking & Line Wrapping](02-breaking.md) - Control line breaks and wrapping
3. [Brace Styles](03-braces.md) - Configure brace placement and wrapping
4. [Indentation](04-indentation.md) - Control indentation behavior
5. [Spacing](05-spacing.md) - Fine-tune whitespace placement
6. [Include Organization](06-includes.md) - Sort and organize include directives
7. [Language-Specific](07-languages.md) - Options for specific languages
8. [Comments & Misc](08-comments.md) - Comment formatting and other options
9. [Advanced Options](09-advanced.md) - Experimental and advanced features

### Complete Reference Documentation

- [Full CLI Reference](complete/clang-format-cli.md) - Complete command-line documentation
- [Full Style Options](complete/clang-format-style-options.md) - Complete style configuration reference

## What is clang-format?

clang-format is a tool that automatically formats source code according to configurable style rules. It ensures consistent code formatting across your project and team.

**Supported Languages:**

- C/C++
- Java
- JavaScript/TypeScript
- JSON
- Objective-C
- Protocol Buffers
- C#
- Verilog
- TableGen

## Quick Start

### 1. Create a Configuration File

Generate a `.clang-format` file based on a predefined style:

```bash
clang-format -style=llvm -dump-config > .clang-format
```

**Available Base Styles:**

- `LLVM` - LLVM coding conventions
- `Google` - Google C++ Style Guide
- `GNU` - GNU coding style
- `Chromium` - Chromium project style
- `Microsoft` - Microsoft coding style
- `Mozilla` - Mozilla coding style
- `WebKit` - WebKit coding style

### 2. Customize Your Configuration

Edit `.clang-format` to customize specific options:

```yaml
# Start with a base style
BasedOnStyle: Google

# Customize specific options
IndentWidth: 4
ColumnLimit: 120
PointerAlignment: Left
```

### 3. Format Your Code

```bash
# Format a single file in-place
clang-format -i src/main.cpp

# Format multiple files
clang-format -i src/*.cpp include/*.h

# Check without modifying (dry run)
clang-format --dry-run src/main.cpp

# Format only changed lines in git
git clang-format
```

## Configuration File Structure

A `.clang-format` file uses YAML format with key-value pairs:

```yaml
---
# Language-specific settings
Language: Cpp

# Base style to inherit from
BasedOnStyle: LLVM

# Indentation
IndentWidth: 4
UseTab: Never
TabWidth: 4

# Line length
ColumnLimit: 100

# Braces
BreakBeforeBraces: Allman

# Spacing
SpaceBeforeParens: ControlStatements

# Pointer alignment
PointerAlignment: Left

# Include sorting
SortIncludes: true
```

## Common Workflows

### Format on Commit

Format only staged changes before committing:

```bash
git clang-format
```

### Format Entire Project

```bash
find src include -name '*.cpp' -o -name '*.h' | xargs clang-format -i
```

### Check Formatting in CI

```bash
clang-format --dry-run --Werror src/*.cpp include/*.h
```

### Ignore Specific Files

Create `.clang-format-ignore`:

<eg>
# Ignore third-party code
third_party/**
external/**

# Ignore generated files
*.pb.cc
*.pb.h
</eg>

## Editor Integration

clang-format integrates with popular editors:

- **VS Code**: Install "Clang-Format" extension
- **CLion**: Built-in support (detects `.clang-format`)
- **Vim**: Use `assets/integrations/vimrc-clang-format.vim`
- **Emacs**: Use `assets/integrations/emacs-clang-format.el`

These integrations call the external `clang-format` binary, so make sure it is installed and discoverable before wiring them up:

```bash
clang-format --version
command -v clang-format
```

See [CLI Usage](cli-usage.md) for detailed integration instructions.

## Finding Style Options

Options are organized by category:

- **Need to align assignments?** → [Alignment Options](01-alignment.md)
- **Control where lines break?** → [Breaking & Line Wrapping](02-breaking.md)
- **Configure brace placement?** → [Brace Styles](03-braces.md)
- **Adjust indentation?** → [Indentation](04-indentation.md)
- **Fine-tune spacing?** → [Spacing](05-spacing.md)
- **Organize includes?** → [Include Organization](06-includes.md)
- **Language-specific needs?** → [Language-Specific](07-languages.md)

## Example Configurations

See [Quick Reference](quick-reference.md) for complete configuration examples:

- Google C++ style customized
- Linux kernel style
- Corporate/Microsoft style
- Modern C++ style

## Documentation Structure

This skill is organized into:

1. **Navigable sections** - Categorized options for easy browsing
2. **Complete reference** - Full documentation for deep dives
3. **Quick reference** - Ready-to-use configuration examples

## Best Practices

1. **Version control** your `.clang-format` file in the repository root
2. **Start with a base style** that matches your existing conventions
3. **Make minimal changes** to the base style to reduce maintenance
4. **Document deviations** from standard styles in comments
5. **Test on representative code** before applying project-wide
6. **Use git integration** to format only changed lines
7. **Set up editor integration** for automatic formatting
8. **Create `.clang-format-ignore`** for files that shouldn't be formatted

## Troubleshooting

**Configuration not found?**

- clang-format searches for `.clang-format` or `_clang-format` from the source file's directory upward
- Use `-style=file:/path/to/.clang-format` to specify explicitly

**Unknown options warning?**

- Use `--Wno-error=unknown` to allow formatting with unknown (newer) options
- This happens when your config has options not supported by your clang-format version

**Want to check effective config?**

```bash
clang-format -dump-config file.cpp
```

## Next Steps

- Browse [Style Options by Category](#style-options-by-category) to customize formatting
- Check [Quick Reference](quick-reference.md) for complete working examples
- Review [CLI Usage](cli-usage.md) for advanced command-line usage
- Consult full reference documentation for comprehensive details
