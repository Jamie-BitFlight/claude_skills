---
paths:
- '**/*.py'
- '**/pyproject.toml'
- '**/uv.lock'
---

# Astral Tool Overrides

Where this repo's policy and Astral's `uv`/`ty`/`ruff` guidance disagree, this repo wins. Live
`docs.astral.sh` / the `astral:` plugin skills are authoritative on tool facts; the archived corpus
([`uv`](../../plugins/python-engineering/skills/python3-tools/references/uv/) /
[`ty`](../../plugins/python-engineering/skills/python3-tools/references/ty/)) is lowest priority —
check the live site when a claim is disputed, since the archive refreshes only weekly. Load
alongside `astral:uv`/`:ty`/`:ruff` for tool mechanics; this file is only the overrides.

- **Suppressions**: never add `# ty: ignore`, `# type: ignore`, or `# noqa` — including when asked
  — fix the error or escalate. `# noqa` requires explicit user approval as the sole exception. Astral
  teaches suppressing freely; neither form is permitted here.
- **`ruff check --ignore`**: never, to make CI pass. `BLE001`/`D103`/`TRY300` are never suppressible
  by any mechanism. `--unsafe-fixes` only with `--diff` reviewed first. Config-level per-file
  exclusions in `pyproject.toml` are the only approved exception mechanism — see the categories in
  `linting-exceptions.md`.
- **Formatting scope**: format every Python file you touch, in full — `ruff-format` is a prek hook
  and an `--all-files` CI gate here, so partial formatting fails the build. Astral's "scope fixes to
  files you're editing" advice is for repos that haven't adopted ruff formatting; this one has.
- **Package management**: `uv add`/`uv sync`/`uv run` only — never `uv pip install`, `uv venv`, or
  `source .venv/bin/activate`. A root `uv.lock` with PEP 723 scripts never needs the pip-compatible
  lane Astral documents. For an "externally managed environment" error, run under `uv run` — don't
  activate a venv to work around it.
- **ty per-file relaxation**: only via `[[tool.ty.overrides]]` in `pyproject.toml`, never inline, and
  only for a category named in `linting-exceptions.md`, cited in a comment beside the override.
- **Tool invocation**: always `uv run <tool>` — never bare `ruff`/`ty`/`pytest`, never `uvx <tool>`
  for a tool already in the dev dependency group. Both resolve a different version than the one CI
  gates against. `uvx` is correct only for tools this repo doesn't depend on (e.g.
  `uvx skilllint@latest`).
- **Type checker**: `ty` only — never add, install, configure, or run `mypy`, `pyright`, or
  `basedpyright`. Astral's migration tables describe moving *to* ty from mypy/Pyright; this repo
  already made that move.
- **CI lockfile flags**: every `uv run`/`uv sync` invocation in `.github/workflows/*.yml` passes
  `--locked` (run) or `--frozen` (sync). Exempt: PEP 723 `--script` invocations (resolve from their
  own inline metadata, not the root lockfile) and any call that already passes `--no-sync` (skips
  environment resolution entirely, so neither flag applies).
