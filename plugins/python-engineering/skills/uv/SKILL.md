---
name: uv
description: Use when working with uv. Covers this skill's uv policy and required overrides to Astral's official uv guidance — load alongside the `astral:uv` skill (which teaches uv itself); this skill covers only its own policy additions, not general uv usage.
allowed-tools: Read
---

# uv — Policy

Precedence: this skill's policy (below) > live `docs.astral.sh` / the `astral:uv` skill (tool facts) > the archived corpus linked below (may be stale).

The `astral:uv` skill covers command syntax, migration tables, and general usage — not duplicated here.

## Policy

- Follow the `python-engineering:standards-for-python-development` skill when applying shared architecture, typing, testing, or CLI rules.
- Use `uv add` / `uv sync` / `uv run` for all Python work — never `uv pip install`, `uv venv`, or `source .venv/bin/activate`. A `uv.lock`-managed project with PEP 723 scripts never needs the pip-compatible lane Astral documents.
- PEP 723 script shebang: `#!/usr/bin/env -S uv run --quiet --script`. Never add `--active` — it breaks PEP 723 isolation by resolving into an ambient `VIRTUAL_ENV` instead of an isolated ephemeral one.
- Use text mode (`'r'`/`'w'`) with `tomlkit`, never binary mode (`'rb'`/`'wb'`) — binary mode returns `bytes`, which `tomlkit` cannot parse or write.

## Archive

[`../python3-tools/references/uv/`](../python3-tools/references/uv/), part of the `python-engineering:python3-tools` skill, holds a generated, possibly-stale snapshot of `docs.astral.sh` — migration guide, CLI reference, troubleshooting. Check `docs.astral.sh` directly if anything there is disputed or looks out of date.

## External Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [uv Concepts](https://docs.astral.sh/uv/concepts/)
- [Migration Guides](https://docs.astral.sh/uv/guides/)
