---
name: uv
description: Use when working with uv — this skill's uv policy and required overrides to Astral's official guidance. Pair with `astral:uv` (if installed) for general usage.
allowed-tools: Read
---

# uv — Policy

Precedence: this policy (below) > `astral:uv` (if installed) / live `docs.astral.sh` for command
syntax, migration tables, and general usage (not duplicated here) > the archived corpus below (may
be stale).

## Policy

- Follow `python-engineering:standards-for-python-development` for shared architecture, typing, testing, and CLI rules.
- Use `uv add` / `uv sync` / `uv run` for all Python work — never `uv pip install`, `uv venv`, or `source .venv/bin/activate`. A `uv.lock`-managed project with PEP 723 scripts never needs the pip-compatible lane Astral documents.
- PEP 723 script shebang: `#!/usr/bin/env -S uv run --quiet --script`. Never add `--active` — it breaks PEP 723 isolation by resolving into an ambient `VIRTUAL_ENV` instead of an isolated ephemeral one.
- Use text mode (`'r'`/`'w'`) with `tomlkit`, never binary mode (`'rb'`/`'wb'`) — binary mode returns `bytes`, which `tomlkit` cannot parse or write.

## Archive

[`../python3-tools/references/uv/`](../python3-tools/references/uv/) (part of `python-engineering:python3-tools`): migration guide, CLI reference, troubleshooting.

## External Resources (if `astral:uv` isn't installed)

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [uv Concepts](https://docs.astral.sh/uv/concepts/)
- [Migration Guides](https://docs.astral.sh/uv/guides/)
