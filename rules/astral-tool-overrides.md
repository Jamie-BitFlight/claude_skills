# Astral Tool Overrides

Where this repo's policy and Astral's `uv`/`ty`/`ruff` guidance disagree, this repo wins. Live
`docs.astral.sh` / the `astral:` plugin skills are authoritative on tool facts. Load alongside
`astral:uv`/`:ty`/`:ruff` for tool mechanics; this file is only the overrides.

- **Suppressions**: never add `# ty: ignore`, `# type: ignore`, `# noqa`, `# ruff: ignore[<rule>]`, or
  `# ruff: file-ignore[<rules>]` — including when asked — fix the error or escalate. `# noqa` requires
  explicit user approval as the sole exception; none of the other forms is.
- **`ruff check --ignore`**: never, to make CI pass. **`--add-ignore`**: never — it auto-generates
  `# ruff: ignore[<rule>]` comments, which the Suppressions rule above already forbids. See
  `linting-exceptions.md` for codes that must always be fixed. `--unsafe-fixes` only with `--diff`
  reviewed first. Config-level per-file exclusions in `pyproject.toml` are the only approved
  exception mechanism — see the categories in `linting-exceptions.md`.
- **Formatting scope**: format every Python file you touch, in full — `ruff-format` is a prek hook
  and an `--all-files` CI gate here, so partial formatting fails the build. Astral's "scope fixes to
  files you're editing" advice is for repos that haven't adopted ruff formatting; this one has.
- **Package management**: `uv add`/`uv sync`/`uv run` only — never `uv pip install`, `uv venv`, or
  `source .venv/bin/activate`. A root `uv.lock` with PEP 723 scripts never needs the pip-compatible
  lane Astral documents. For an "externally managed environment" error, run under `uv run` — don't
  activate a venv to work around it.
- **Security upgrades**: raise a pinned floor with `uv add "pkg>=X.Y.Z"`, which updates
  `pyproject.toml` and `uv.lock` together and prints the resolved version. `uv lock
  --upgrade-package pkg` moves only the lockfile, within the constraint `pyproject.toml` already
  carries, so the vulnerable floor survives and a later resolution can return to it. Confirm the
  result with `uv tree | grep pkg`.
- **ty per-file relaxation**: see `python-development.md`'s "ty Type Checker Errors" section.
- **Tool invocation**: always `uv run <tool>` — never bare `ruff`/`ty`/`pytest`, never `uvx <tool>`
  for a tool already in the dev dependency group. Both resolve a different version than the one CI
  gates against. `uvx` is correct only for tools this repo doesn't depend on (e.g.
  `uvx skilllint@latest`).
- **Type checker**: `ty` only — never run `mypy`, `pyright`, or
  `basedpyright` for type checking. The
  only allowed config for either is an explicit all-off stanza (`[tool.mypy] exclude = [".*"]`,
  `[tool.basedpyright] typeCheckingMode = "off"`) that stops an IDE defaulting to it — see
  `pyproject.toml`. Never add config that *enables* checking with them. Astral's migration tables describe moving *to* ty from mypy/Pyright; this repo
  already made that move.
- **CI lockfile flags**: every `uv run`/`uv sync` invocation in `.github/workflows/*.yml` passes
  `--locked` (run) or `--frozen` (sync). Exempt: any `uv run` of a script carrying its own `# /// script` PEP 723 block (with or without an
  explicit `--script` flag — `uv` auto-detects the block either way; e.g.
  `.github/workflows/code-quality.yml`'s `uv run plugins/development-harness/scripts/close_test_issues.py`)
  — it resolves from that block, not the root lockfile. Also exempt: any call that already passes
  `--no-sync` (skips environment resolution entirely, so neither flag applies).
