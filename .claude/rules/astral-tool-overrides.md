---
paths:
- '**/*.py'
- '**/pyproject.toml'
- '**/uv.lock'
---

# Astral Tool Overrides

Precedence when this repo and Astral's `uv`/`ty`/`ruff` guidance disagree: repo policy on *how we
work here* wins first, live `docs.astral.sh` / the `astral:` plugin skills are authoritative on
*tool facts* second, and this repo's archived corpus
([`uv`](../../plugins/python-engineering/skills/python3-tools/references/uv/) /
[`ty`](../../plugins/python-engineering/skills/python3-tools/references/ty/)) is lowest priority —
re-check the live site when a claim is disputed, since the archive is refreshed only weekly.
SOURCE: Astral plugin adoption migration (PR #3019), "Precedence" decision (2026-08-19).

The rows below are every point where Astral's shipped skills (`astral/{uv,ty,ruff}/SKILL.md`,
fetched 2026-08-19) and this repo's own rules disagree, verified against those primary sources.
Load alongside `astral:uv`/`:ty`/`:ruff` — that skill covers tool mechanics, this file covers where
this repo overrides them.

## C1 — `ty: ignore` / `type: ignore` suppressions

Astral (`astral/ty:110–124`): "Only add ignore comments when explicitly requested by the user. Use
`ty: ignore`, not `type: ignore`, and prefer rule-specific ignores." This repo
(`.claude/rules/python-development.md:37`): inline suppressions are prohibited outright.

**Resolution**: Never add `# ty: ignore` or `# type: ignore`, including when a user asks for it —
fix the type error instead, or escalate with the specific blocker. Astral's `ty: ignore`-over-
`type: ignore` preference does not apply, since neither form is permitted.

## C2 — ruff suppression via `--ignore` / `# noqa`

Astral (`astral/ruff:32,58,131–147`): teaches `ruff check --ignore E501 .` and
`--fix --unsafe-fixes`, with no suppression policy beyond "always review changes before applying."
This repo (`.claude/rules/linting-exceptions.md:9,28,30–34`): "Resolve linting errors — do not
suppress them"; BLE001/D103/TRY300 are never suppressible; `# noqa` needs explicit user approval.

**Resolution**: Never pass `--ignore` to `ruff check` to make this repository's CI pass, and never
suppress BLE001, D103, or TRY300 by any mechanism. A `# noqa` requires explicit user approval
first. `--unsafe-fixes` is permitted only with the `--diff` preview reviewed before applying.
Config-level per-file exclusions in `pyproject.toml` remain the approved mechanism for the six
exception categories in `linting-exceptions.md`.

## C3 — formatting scope

Astral (`astral/ruff:22–30`): "Don't format unformatted code … skip formatting to avoid obscuring
actual changes"; "scope fixes to files you're editing." This repo
(`.pre-commit-config.yaml:89` `ruff-format` hook, `.github/workflows/code-quality.yml:37`
`--all-files` CI gate, `linting-exceptions.md:43` "Touched Files Must Be Clean"): `ruff-format`
runs repo-wide in CI, not scoped to the diff.

**Resolution**: Format every Python file you touch — `ruff-format` is both a prek hook and an
`--all-files` CI gate, so skipping it fails the build rather than keeping the diff clean. Astral's
"don't format unformatted code" and "scope fixes to files you're editing" advice applies to repos
that haven't adopted ruff formatting; this one has.

## C4 — pip-compatible interface / venv activation

Astral (`astral/uv:74–91`): documents the full pip-interface lane (`uv venv`,
`uv pip install -r`, `uv pip compile/sync`), gated only by "don't use the pip interface unless
clearly needed." This repo (`AGENTS.md`'s Package Manager line, global `CLAUDE.md`,
`.claude/rules/python-development.md:12`): always `uv run`, never a hardcoded interpreter, no uv
workspace — plugin MCP servers are PEP 723 self-resolving scripts.

**Resolution**: Use `uv add`/`uv sync`/`uv run` for all Python work, never `source
.venv/bin/activate` or `uv pip install` — a root `uv.lock` and PEP 723 scripts mean the
pip-compatible lane Astral documents is never the right lane here.

## C5 — ty per-file relaxation via `[[tool.ty.overrides]]`

Astral (`astral/ty:66–80`): "Use overrides to apply different rules to specific files, such as
relaxing rules for tests." This repo previously had an internal contradiction:
`python-development.md:37` called *all* per-file-ignores relaxation prohibited, while
`pyproject.toml:169–216` already ships four `[[tool.ty.overrides]]` blocks, and
`linting-exceptions.md:36–41` already blesses config-level per-file exceptions.

**Resolution**: Relax ty rules only through `[[tool.ty.overrides]]` in `pyproject.toml`, never
through inline comments, and only for a case matching one of the six exception categories in
`linting-exceptions.md`, named in a comment beside the override. `python-development.md` has been
amended accordingly — see its "ty Type Checker Errors" section.

## C6 — bare tool invocation vs `uv run`

Astral (`astral/ruff:38–44`, `astral/ty:22–27`, `astral/uv:66`): "Use `ruff …` if ruff is installed
globally"; promotes `uvx ty …` and `uvx <tool>` generally. This repo (`AGENTS.md`'s Package Manager line,
Essential Commands, `.github/workflows/code-quality.yml`): every gate runs `uv run <tool>` against
the pinned dev-group version.

**Resolution**: Invoke every Python tool as `uv run <tool>` — never bare `ruff`/`ty`/`pytest`, and
never `uvx <tool>` for a tool already in the dev dependency group, because both resolve a different
version than the one CI gates against. `uvx` remains correct only for tools this repo does not
depend on (e.g. `uvx skilllint@latest`).

## C7 — mypy / pyright / basedpyright

Astral (`astral/ty:5–7,10–11,97–107`): describes ty as replacing mypy and Pyright, and teaches
migration *from* either as if one might still be present. This repo (`AGENTS.md` "Type Checking"):
"This repository enforces **ty** (Astral) only … `mypy`, `pyright`, and `basedpyright` are not
repository quality gates."

**Resolution**: Do not add, install, configure, or run `mypy`, `pyright`, or `basedpyright` — `ty`
is the only type checker that gates CI. Astral's migration tables describe moving *to* ty from a
repo that used those tools; this repo already completed that move.

## C8 — venv-activation workaround for "externally managed environment" (internal contradiction)

Not an Astral conflict — an internal one, found while auditing the now-deleted
`uv/SKILL.md:849–855` against its own `:994` ("Don't activate venv manually"). Line 849–855
prescribed `uv venv` → `source .venv/bin/activate` → `uv pip install` as the fix for an externally
managed environment error, directly contradicting the rule six lines away in the same file.

**Resolution**: For an "externally managed environment" error, run the command under `uv run` — do
not create and activate a virtualenv to work around it.

## Aspirational vs current: `--frozen` / `--locked` in CI

Astral's `astral/uv` do/don't guidance (mirrored in the old `uv/SKILL.md:987,998`) says to use
`--locked`/`--frozen` on every `uv run`/`uv sync` in CI. This is enforced: every project-mode
`uv run`/`uv sync` invocation in `.github/workflows/*.yml` passes
`--frozen` (sync) or `--locked` (run) — see `.claude/rules/ci-workflows.md` for the CI modification
protocol this was applied under. PEP 723 `--script` invocations are exempt: they resolve from their
own inline metadata block, not the root `uv.lock`, so neither flag applies to them.

SOURCE: verified against `astral-sh/claude-code-plugins`
`plugins/astral/skills/{uv,ty,ruff}/SKILL.md` fetched 2026-08-19, and this repo's `.claude/rules/`,
`AGENTS.md`, `pyproject.toml` as of commit `343e4757` (PR #3019).
