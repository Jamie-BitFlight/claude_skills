---
paths:
- '**/*.py'
---

# YAML and TOML Libraries

This repository uses `ruamel.yaml` for all YAML operations and `tomlkit` for TOML read-write operations.

- Use `ruamel.yaml` for YAML — never `pyyaml` (`import yaml`)
- Use `tomlkit` for TOML read-write operations
- Open files for `tomlkit` in text mode (`'r'`/`'w'`), never binary mode (`'rb'`/`'wb'`) — binary
  mode returns `bytes`, which `tomlkit.load`/`tomlkit.dump` cannot parse or write
- `tomllib` (stdlib) is acceptable for read-only TOML in stdlib-only contexts
- For frontmatter parsing/writing, use the shared module: `from frontmatter_utils import load_frontmatter, dump_frontmatter`
