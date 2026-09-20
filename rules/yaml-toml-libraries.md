# YAML and TOML Libraries

This repository uses `ruamel.yaml` for all YAML operations and `tomlkit` for TOML read-write operations.

- Use `ruamel.yaml` for YAML — never `pyyaml` (`import yaml`)
- Use `tomlkit` for TOML read-write operations
- Open files for `tomlkit` in text mode (`'r'`/`'w'`) — `tomlkit.dump` requires a text-mode stream
  (its signature is `fp: IO[str]`) and raises `TypeError: a bytes-like object is required, not 'str'`
  when given a `'wb'` file. `tomlkit.load` accepts binary mode too (`IO[str] | IO[bytes]`), but write
  in text mode for symmetry with `dump`, which cannot.
- `tomllib` (stdlib) is acceptable for read-only TOML in stdlib-only contexts
- For frontmatter parsing/writing, use the shared module: `from frontmatter_utils import load_frontmatter, dump_frontmatter`
