# Copilot Coding Agent Instructions

This file contains only project decisions that differ from defaults and routing pointers to authoritative sources. Read the source files for discoverable details — do not rely on summaries here.

## Project Decisions (Differ from Defaults)

**Package manager**: All Python commands use `uv run` — never invoke `python` or `pytest` directly.

**Hook runner**: This repo uses `prek` (Rust-based), not `pre-commit`. Same `.pre-commit-config.yaml` config, different binary. Install hooks with `uv run prek install -t pre-commit -t commit-msg -t pre-rebase -t post-merge`.

**Commit scope is required**: Conventional Commits are enforced with `--force-scope`. Every commit needs a scope — `feat(scope): msg`. Never use `--no-verify`; fix hook failures instead. See `.agent/rules/git-commits.md`.

**Python-specific decisions** (see `pyproject.toml [tool.ruff]` for all settings):
- Always add `from __future__ import annotations` as the first import in every Python file
- `requests` is banned — use `httpx` instead
- Standalone scripts use PEP 723 shebang: `#!/usr/bin/env -S uv run --quiet --script`

**Backlog is MCP-driven**: Never edit `.claude/backlog/` files directly — use `mcp__plugin_dh_backlog__*` tools. GitHub Issues are the source of truth; `.claude/backlog/` is local cache only.

**No uv workspace**: plugin MCP servers are PEP 723 self-resolving scripts (inline `# /// script` deps are the runtime source of truth); root `pyproject.toml` dev-deps only mirror them for `ty`/`ruff`/IDE. No `[tool.uv.workspace]`, no per-plugin `uv.lock`.

**conftest isolation**: `plugins/scientific-method/mcp/experiment-registry/tests` is excluded from the root pytest run (conftest name collision). Test it independently: `cd` into the directory and run `uv run pytest`.

**Symlinks on Windows**: Git symlinks (mode 120000) become plain text files on Windows. The `repair-symlinks` pre-commit hook fixes this. Symlinked Python directories are excluded from `ruff` and `ty` to avoid parse errors.

**Two type checkers run in CI**: `uv run ty check .` (primary) and basedpyright (secondary). Both must pass. See `pyproject.toml [tool.ty]` for override rules.

## Where to Find Things

| What you need                          | Where to look                                    |
| -------------------------------------- | ------------------------------------------------ |
| AI project instructions (Claude Code)  | `.claude/CLAUDE.md`                              |
| Linting / formatting config            | `pyproject.toml` → `[tool.ruff]`                 |
| Type checking config & overrides       | `pyproject.toml` → `[tool.ty]`                   |
| Test paths & pytest config             | `pyproject.toml` → `[tool.pytest.ini_options]`   |
| Pre-commit hook definitions            | `.pre-commit-config.yaml`                        |
| CI jobs and quality gate               | `.github/workflows/code-quality.yml`             |
| MCP server definitions                 | `.mcp.json`                                      |
| Plugin structure reference             | `plugins/plugin-creator/skills/claude-plugins-reference-2026/SKILL.md` |
| Writing lean AI-facing instructions    | `plugins/plugin-creator/skills/optimize/SKILL.md` |
| Commit message rules                   | `.agent/rules/git-commits.md`                    |
