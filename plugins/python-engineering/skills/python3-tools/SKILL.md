---
name: python3-tools
description: Use when working with Python tooling — uv package management, Hatchling build backend, ty or mypy type checker configuration, ruff linting, pre-commit hook setup, TOML read-write with tomlkit or tomllib, or PyPI packaging and release workflows. Routes to standalone specialist skills for deep dives on any single tool.
user-invocable: false
---

# Python Tooling

Consult `python3-core` for standing defaults.

Command defaults and quick reference for uv, the type checker, ruff, the build backend,
pre-commit, TOML, and PyPI packaging: `references/tooling-defaults.md`.

Repo policy, conflict resolution against Astral's official guidance, and archive links for a
specific tool: load the matching wrapper skill below.

## Standalone Tool Skills

Load these skills when the task is focused entirely on one tool:

- Load `python-engineering:uv` when the task involves uv commands, lockfiles, PEP 723 scripts, workspace configuration, Python version management, CI/CD integration, Docker setup with uv, or migration from pip/poetry/pyenv.
- Load `python-engineering:ty` when the task involves running ty type checks, configuring `ty.toml` or `[tool.ty]`, suppressing diagnostics, interpreting ty error codes, ty editor integration, or migrating from mypy/pyright to ty.
- Load `python-engineering:ruff` when the task involves ruff linting or formatting, rule selection, suppression policy, or reviewing `--unsafe-fixes`.
- Load `python-engineering:hatchling` when the task involves Hatchling build hooks, custom builders, wheel/sdist configuration, editable installs, VCS version sources, PEP 517/518/621/660 compliance, or setuptools migration.
- Load `python-engineering:toml-python` when the task requires advanced TOML manipulation: comment-preserving read-modify-write, atomic config updates, tomlkit API patterns, or XDG config file management.
- Load `python-engineering:pre-commit` when the task requires configuring hook stages, writing `.pre-commit-hooks.yaml` definitions, implementing `prepare-commit-msg` hooks, or distributing a tool as a pre-commit hook.
- Load `python-engineering:pypi-readme-creator` when the task involves creating or validating a PyPI README, choosing between Markdown and RST formats, configuring `readme` in `pyproject.toml`, or running `twine check`.

## References

- `references/tooling-defaults.md` — command defaults and quick reference
- `references/compatibility-lanes.md` — version compatibility
- `references/uv/README.md` — cached snapshot of `docs.astral.sh/uv` (generated, not authored); read its precedence chain before trusting a stale-looking claim
- `references/ty/README.md` — cached snapshot of `docs.astral.sh/ty` (generated, not authored); read its precedence chain before trusting a stale-looking claim
