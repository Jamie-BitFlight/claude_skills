---
name: python3-tools
description: Use when working with Python tooling — uv package management, Hatchling build backend, ty or mypy type checker configuration, ruff linting, pre-commit hook setup, TOML read-write with tomlkit or tomllib, or PyPI packaging and release workflows. Routes to standalone specialist skills for deep dives on any single tool.
user-invocable: false
---

# Python Tooling

Consult `python3-core` for standing defaults.

Command defaults and quick reference for uv, the type checker, ruff, the build backend,
pre-commit, TOML, and PyPI packaging: `references/tooling-defaults.md`.

This plugin's policy and conflict resolution against Astral's official guidance for a specific
tool: load the matching wrapper skill below.

## Standalone Tool Skills

Load when the task is focused entirely on one tool:

| Skill | Load when the task involves |
|---|---|
| `python-engineering:uv` | uv commands, lockfiles, PEP 723 scripts, workspace config, Python version management, CI/CD integration, Docker setup, or pip/poetry/pyenv migration |
| `python-engineering:ty` | ty type checks, `ty.toml`/`[tool.ty]` config, diagnostic suppression, ty error codes, editor integration, or mypy/pyright migration |
| `python-engineering:ruff` | ruff linting/formatting, rule selection, suppression policy, or `--unsafe-fixes` review |
| `python-engineering:hatchling` | build hooks, custom builders, wheel/sdist config, editable installs, VCS version sources, PEP 517/518/621/660 compliance, or setuptools migration |
| `python-engineering:toml-python` | comment-preserving read-modify-write, atomic config updates, tomlkit API patterns, or XDG config management |
| `python-engineering:pre-commit` | hook stage config, `.pre-commit-hooks.yaml`, `prepare-commit-msg` hooks, or distributing a tool as a pre-commit hook |
| `python-engineering:pypi-readme-creator` | PyPI README validation, Markdown vs RST choice, `readme` config, or `twine check` |

## References

- `references/tooling-defaults.md` — command defaults and quick reference
- `references/compatibility-lanes.md` — version compatibility
- `references/pre-commit/pre-commit-official-docs.md` — cached snapshot of pre-commit's official docs
