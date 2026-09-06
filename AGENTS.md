# AGENTS.md — Agent Working Guide for claude_skills

## Evidence Proportionality

Before using tools, running tests, searching history, or gathering evidence, ask: Could the result
materially change the decision, recommendation, or action? If not, skip that work; if uncertain,
prefer the cheapest evidence that can resolve the uncertainty rather than maximizing information.

## Repository Overview

**Project**: Claude Code Marketplace Plugin Collection — marketplace name `jamie-bitflight-skills`,
defined in `.claude-plugin/marketplace.json`. Most entries are local directories under `plugins/`.
The rest are external: the upstream `astral` plugin pinned by git-subdir, and
`hallucination-detector` from a sibling GitHub repo. Read the manifest for the current roster.
**Purpose**: Extends Claude Code CLI (and secondarily Codex, OpenCode, and GitHub's coding agent)
with specialized skills, commands, and agents for Python development, code quality, Git/CI-CD,
AI/LLM tools, documentation, and agent orchestration.
**Languages**: Markdown (skills/commands/agents), Python 3.11+ (scripts; `.python-version` pins 3.13),
JavaScript/TypeScript (hooks, MCP scripts)
**Package Manager**: `uv` (Astral) — all Python commands use `uv run` prefix
**Python Version**: 3.11+ required

The largest plugin is `plugins/development-harness` (install name `dh`) — the SAM 7-stage pipeline
with its own MCP servers (`backlog_core/`, `sam_schema/`), agents, and skills. It has its own
`AGENTS.md`; read it before working inside that directory.

Backlog backend for this checkout: **GitHub Issues** (`.dh/config.yaml`'s `backend.name: github`).
This repo does not use Beads (`bd`) for task tracking. **Never run `bd init` or `bd setup` at the
repo root.** If a Beads integration block reappears in this file, delete it — it does not describe
this checkout. See `plugins/development-harness/AGENTS.md`'s "Backend Providers" section for the
backend abstraction's Protocol architecture when extending or modifying `dh`'s backend code.

## Environment Setup (Required First)

```bash
uv self update                             # Keep uv itself current (v0.10.0+ required)
uv sync                                    # Install all dependencies, create .venv/
uv run prek install -t pre-commit -t commit-msg -t pre-rebase -t post-merge  # Install git hooks
```

Before linting, formatting, or type-checking, read `docs/linting-and-type-checking.md`.
Before writing, running, or placing a test, read `docs/testing.md`.
Before validating an MCP server (protocol, Codex, or Claude plugin integration), read
`docs/mcp-server-validation.md`.

## Code Conventions

**Cross-platform native**: write scripts in Python, never POSIX shell or PowerShell. Bash is for
simple CI/CD wrappers only — see [rules/language-conventions.md](./rules/language-conventions.md).

**Cross-harness**: first-class support for Claude Code, Codex, Hermes, OpenCode and Cursor;
best-effort for pi, Kimi Code and Kilo Code. Before planning any change to an agent, skill, hook
or plugin system, dispatch subagents to read those harnesses' own documentation and this
repository's measurements of them, starting from
[plugins/development-harness/CLAIMS-REGISTER.md](./plugins/development-harness/CLAIMS-REGISTER.md);
add what you establish back to it.

### Python

- **Always** include `from __future__ import annotations` as first import
- **Docstrings**: Google convention (`Args:`, `Returns:`, `Raises:`)
- **Type hints**: Required for all public functions
- **Max line length**: 120 characters
- **Generics**: Use native forms (`list[str]`, `dict[str, Any]` not `List[str]`)
- **Imports**: isort with `combine-as-imports = true`, `force-single-line = false`
- **Banned**: `requests` library — use `httpx` instead (enforced by ruff `flake8-tidy-imports`).
  Narrow per-file exceptions exist in `[tool.ruff.lint.per-file-ignores]` (e.g.
  `backlog_core/sync_state.py`, which must match PyGithub's requests-based exception types).
- **Scripts**: PEP 723 inline metadata (`# /// script`) for standalone scripts run via `uv run --script`
- **Structured data → Pydantic, not dataclass/TypedDict**: this repo's ingestion and output objects
  are standardizing on Pydantic `BaseModel`, not `@dataclass` or `TypedDict`. The
  `python-engineering:python3-typing` skill's lane selection auto-detects from what a file already
  imports — that means an existing `@dataclass` never gets reconsidered on its own. When adding or
  touching a structured data shape (CLI output, MCP tool payloads, parsed file records), use
  Pydantic `BaseModel` by default. `TypedDict`/`dataclass` remain correct only for genuinely
  stdlib-only, dependency-constrained contexts (see `python-engineering:python3-stdlib-only`).
- **Default to already-declared dependencies**: before writing a new shared module, check the PEP
  723 dependency block of the scripts that will import it (`grep dependencies plugins/*/scripts/*.py`)
  and reuse what's already declared (e.g. `httpx`, `ruamel.yaml`) instead of assuming a stdlib-only
  design. Stdlib-only is a valid constraint only for a confirmed deployment restriction (airgapped,
  no pip access) — not a default posture.
- **Public by default**: name new functions and modules without a leading underscore. Early
  "private" naming gets cargo-culted onto things that aren't private, then breaks tests that
  legitimately need the name — add privacy once actually needed. Existing underscored code stays
  as-is.

Before writing a script or CLI meant to be consumed by an agent (which is every script/CLI/MCP
server in this repo), read `docs/cli-output-conventions.md`.

### Markdown (Skills/Commands/Agents)

Skill handoffs use plain prose (`plugin:skill-name`, `/plugin:skill-name`), not
`Skill(skill="...")` — that syntax is Claude-Code-only and this repo's plugin content also
targets Codex and OpenCode. Existing `Skill(...)` blocks are pre-convention, not bugs.

### JavaScript/TypeScript

- Formatted with Biome (`biome.json`)
- Pre-commit hooks use CJS format (`.cjs`)

## Commit Conventions

This repo enforces **Conventional Commits** with `--strict --force-scope` (scope is **required**) via
the `conventional-pre-commit` hook in `.pre-commit-config.yaml`.

**NEVER use `--no-verify` or flags that bypass git hooks.** If a hook fails, fix the underlying issue.

## Git Workflow: Commit, Push, and PR per Task

Repo owner instruction, standing: commit completed work as each discrete task finishes, push the
branch, and open a pull request for it. Do not wait for interactive approval before committing or
pushing in this repository — this overrides Claude Code's own default "ask before committing"
behavior here.

- Follow `rules/commit-cadence-and-worktrees.md` for commit hygiene: small, file-scoped commits
  via an explicit file list, never `git add -A`.
- One PR per discrete task or unit of work, not one PR per session. Push the branch and run
  `gh pr create` once a task's commit(s) land.
- This does not extend to force-pushing, pushing directly to `main`, merging PRs, or bypassing
  hooks (`--no-verify`) — those still need explicit approval every time.

## Working Tree Safety

The working tree may hold another contributor's uncommitted, legitimate work. Before reverting or
discarding an unexpected diff (`git checkout`, `git restore`, `git reset --hard`), read the diff
and confirm it is unintended rather than assuming it is an agent artifact — an unexplained change
is a reason to investigate and ask, not a reason to revert.

Before branch switching, selective checkout or cherry-pick, stash cleanup, or source-branch
deletion, read `docs/branch-transfer-preflight.md`.

## Security Considerations

- Never commit credentials. `.mcp.json` references API keys by environment indirection
  (`$REF_API_KEY`, `$CONTEXT7_API_KEY`), not literal values — follow that pattern.
- Live e2e tests create real GitHub issues in a sandbox repo and are gated to CI on `main` with
  `GITHUB_TOKEN`; do not run them locally against the production backlog.
- Git hooks are mandatory (see Commit Conventions); `conventional-pre-commit`, `skilllint`, and
  the manifest-sync hook all mutate or validate on commit — do not bypass them.

## Gotchas & Non-Obvious Patterns

1. **prek not pre-commit**: This repo uses `prek` (Rust-based), not `pre-commit`. Same config, different binary.
2. **Symlink issues on Windows**: Git symlinks (mode 120000) become plain files on Windows. The `repair-symlinks` pre-commit hook fixes this. Both `ruff` and `ty` have `extend-exclude` entries for symlinked directories.
3. **`.claude/` vs `docs/`**: `.claude/` is Claude Code configuration; `docs/` is project documentation. Check for an existing directory convention (`ls` the likely parent) before choosing where to create a new file.
4. **No `git stash` on the primary checkout**: compare against a clean baseline in an isolated worktree instead — other agents may be mid-write there.
5. **prek stash conflict**: prek stashes unstaged changes before running hooks. If a formatter hook (ruff-format, etc.) modifies staged files and the stash cannot restore cleanly, prek rolls back the hook's changes and the commit fails ("Stashed changes conflicted..."). Fix: `git add -u` to stage the hook's auto-fixes, then retry the commit — the second attempt has nothing left to stash.
6. **Dependency security upgrades**: use `uv add "pkg>=X.Y.Z"` (updates `pyproject.toml` and `uv.lock` atomically with explicit version output) rather than `uv lock --upgrade-package pkg` (silent) or manually verifying line numbers in `uv.lock` (4000+ lines — line numbers do not correspond reliably to package versions). Confirm with `uv tree | grep pkg`.
7. **PEP 723 scripts**: Standalone scripts use `#!/usr/bin/env -S uv run --quiet --script` with inline metadata blocks. This allows `uv run script.py` to auto-install dependencies. Never add `--active` — see `rules/script-invocation.md` for the isolation rationale.
8. **Bounded subprocess execution**: `scripts/run_bounded.py` runs a command with a timeout and terminates its full process group (POSIX process-group signals; `taskkill /T /F` on Windows) on expiry, including descendants a bare `subprocess.run(timeout=...)` would leave behind. Wrap any external command invocation that may hang or spawn children with `uv run --script scripts/run_bounded.py --timeout-seconds <n> -- <command>`.

## File Locations Quick Reference

| Purpose | Location |
|---------|----------|
| AI project instructions | `.claude/CLAUDE.md` (primary context file for Claude Code; imports this file) |
| Repo terminology (skill vs. plugin vs. agent vs. command vs. hook vs. MCP server) | `docs/terminology-glossary.md` |
| Linting config | `pyproject.toml [tool.ruff]` |
| Type checking config | `pyproject.toml [tool.ty]` |
| Test config | `pyproject.toml [tool.pytest.ini_options]` |
| Pre-commit hooks | `.pre-commit-config.yaml` |
| Markdown lint config | `.markdownlint-cli2.jsonc` |
| Plugin registry | `.claude-plugin/marketplace.json` |
| MCP servers | `.mcp.json` |
| Session hooks | `.claude/hooks/` |
| Backlog backend config | `.dh/config.yaml` |
| development-harness agent guide | `plugins/development-harness/AGENTS.md` |
| Harness capability matrix and its per-harness measurements | `plugins/development-harness/CLAIMS-REGISTER.md`, `plugins/development-harness/docs/work-ledger/measurements/` |
| Work-ledger state machine (commands, reason codes, transitions) | `plugins/development-harness/dh_core/ledger_spec.py` |
| Work-ledger orchestrator and runner contracts | `plugins/development-harness/docs/work-ledger/work-loop.md`, `runner-contract.md` |
| CI pipeline | `.github/workflows/code-quality.yml` (see `rules/ci-workflows.md`) |

GitHub's coding agent reads `AGENTS.md` directly; no separate `.github/copilot-instructions.md`
exists.

Rule files outside `rules/` that other harnesses read — not a full rule-file index:

| File | Purpose |
|------|---------|
| `.cursor/rules/backlog-before-work.mdc` | Always create backlog items for multi-step work |
| `.cursor/rules/json-no-pretty-print.mdc` | Compact-JSON rule for agent-facing CLI output |
| `.agent/rules/git-commits.md` | Commit message rules (conventional commits, no --no-verify) |

## PR Review Protocol

After pushing a commit to a PR, or when asked to check or address PR reviews, load the
`receiving-pr-reviews` skill.

## GitHub CLI Conventions

Before using the `gh` CLI, read `docs/github-cli-conventions.md`.
