---
name: uv
description: Use when working with uv in this repository. Covers this repository's uv conventions and required overrides to Astral's official uv guidance — load alongside `/astral:uv` (which teaches uv itself); this skill covers only what is specific to this codebase.
allowed-tools: Read
---

# uv — This Repo's Conventions

Precedence: this repo's policy (below) > live `docs.astral.sh` / the `astral:uv` skill (tool facts) > the archived corpus linked below (may be stale).

Load `/astral:uv` next for command syntax, migration tables, and general usage — it is not duplicated here.

## Repo-specific policy

- Load and follow `/python-engineering:standards-for-python-development` when applying shared architecture, typing, testing, or CLI rules.
- Use `uv add` / `uv sync` / `uv run` for all Python work here — never `uv pip install`, `uv venv`, or `source .venv/bin/activate`. This repo has a root `uv.lock` and PEP 723 scripts; the pip-compatible lane Astral documents is never the right lane here.
- PEP 723 script shebang: `#!/usr/bin/env -S uv run --quiet --script`. Never add `--active` — it breaks PEP 723 isolation by resolving into an ambient `VIRTUAL_ENV` instead of an isolated ephemeral one. See `.claude/rules/script-invocation.md`.
- Use text mode (`'r'`/`'w'`) with `tomlkit`, never binary mode (`'rb'`/`'wb'`) — see `.claude/rules/yaml-toml-libraries.md`.

Full conflict table (uv rows C4, C6, C8): `.claude/rules/astral-tool-overrides.md`.

## Archive

`python3-tools/references/uv/` (load via `Skill(skill="python-engineering:python3-tools")`) holds a generated, possibly-stale snapshot of `docs.astral.sh` — migration guide, CLI reference, troubleshooting. Check `docs.astral.sh` directly if anything there is disputed or looks out of date.

## External Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [uv Concepts](https://docs.astral.sh/uv/concepts/)
- [Migration Guides](https://docs.astral.sh/uv/guides/)
