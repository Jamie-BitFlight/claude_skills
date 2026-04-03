# File Selection

How ty selects which files to check, include/exclude patterns, gitignore integration, and the default excluded directories. Load when the user asks about excluding files, changing which files ty checks, or why certain files are included or excluded.

## Table of Contents

1. [Default File Discovery](#default-file-discovery)
2. [Explicit Path Arguments](#explicit-path-arguments)
3. [Include and Exclude Configuration](#include-and-exclude-configuration)
4. [Default Excluded Directories](#default-excluded-directories)
5. [Glob Pattern Syntax](#glob-pattern-syntax)
6. [Gitignore Integration](#gitignore-integration)
7. [Virtual Environment Files](#virtual-environment-files)

---

## Default File Discovery

ty runs on all Python files in the working directory (including subdirectories, recursively).

When running from a project (directory containing `pyproject.toml`), ty runs on all Python files starting from the project root.

---

## Explicit Path Arguments

Provide specific paths as positional arguments to `ty check`:

```bash
ty check example.py
ty check src scripts/benchmark.py
```

Paths passed as positional arguments are included even if they would otherwise be excluded by `exclude` filters or ignore files.

`--force-exclude` enforces exclusions even for explicitly passed paths. Use `--no-force-exclude` to disable.

---

## Include and Exclude Configuration

```toml
# pyproject.toml — check src/ and tests/ but not src/generated/
[tool.ty.src]
include = ["src", "tests"]
exclude = ["src/generated"]

# ty.toml
[src]
include = ["src", "tests"]
exclude = ["src/generated"]
```

`exclude` takes precedence over `include`.

Override a default exclusion using a negated pattern:

```toml
[tool.ty.src]
exclude = ["!dist"]
```

---

## Default Excluded Directories

ty excludes these directories by default:

```text
**/.bzr/
**/.direnv/
**/.eggs/
**/.git/
**/.git-rewrite/
**/.hg/
**/.mypy_cache/
**/.nox/
**/.pants.d/
**/.pytype/
**/.ruff_cache/
**/.svn/
**/.tox/
**/.venv/
**/__pypackages__/
**/_build/
**/buck-out/
**/dist/
**/node_modules/
**/venv/
```

---

## Glob Pattern Syntax

ty uses reduced portable glob syntax from PEP 639:

| Pattern | Meaning |
|---------|---------|
| `./src/` | Matches only a directory named `src` |
| `./src` | Matches files and directories named `src` |
| `src` | Matches file or directory named `src` |
| `*` | Any sequence of characters except `/` |
| `**` | Zero or more path components (must be a single path component — `**a` and `b**` are invalid) |
| `?` | Any single character except `/` |
| `[abc]` | Any character inside brackets; supports ranges like `[0-9]` |
| `!pattern` | Negates a pattern (undoes exclusion) |

All patterns are anchored relative to the project root. `src` matches only `<project_root>/src`, not `<project_root>/test/src`. To match any directory named `src`, use `**/src`.

Prefix include patterns like `**/src` can slow down file discovery.

Escape characters with a backslash.

---

## Gitignore Integration

ty respects `.ignore`, `.gitignore`, `.git/info/exclude`, and global gitignore files by default.

Disable via configuration:

```toml
[tool.ty.src]
respect-ignore-files = false
```

Or via CLI flag:

```bash
ty check --no-respect-ignore-files
```

---

## Virtual Environment Files

In Python 3.13+, `venv` adds a `.gitignore` to the virtual environment root, preventing ty from checking venv files.

For older Python versions, exclude virtual environment files manually:

```bash
# Add gitignore to the .venv directory
echo "*" > .venv/.gitignore
```

Or add the virtual environment to your project's `.gitignore` or `.ignore` file.
