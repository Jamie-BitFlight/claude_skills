# AGENTS.md — Agent Working Guide for claude_skills

This document covers everything an AI agent needs to work effectively in this repository.

## Repository Overview

**Project**: Claude Code Marketplace Plugin Collection (22+ plugins)
**Purpose**: Extends Claude Code CLI with specialized skills, commands, and agents for Python development, code quality, Git/CI-CD, AI/LLM tools, documentation, and agent orchestration.
**Languages**: Markdown (skills/commands/agents), Python 3.11+ (scripts), JavaScript/TypeScript (hooks, MCP scripts)
**Package Manager**: `uv` (Astral) — all Python commands use `uv run` prefix
**Python Version**: 3.11+ required

## Essential Commands

### Environment Setup (Required First)

```bash
uv sync                                    # Install all dependencies, create .venv/
uv run prek install -t pre-commit -t commit-msg -t pre-rebase -t post-merge  # Install git hooks
```

### Linting & Formatting

```bash
uv run ruff check --fix path/to/file.py    # Lint with auto-fix
uv run ruff format path/to/file.py         # Format Python
uv run ty check path/to/file.py            # Type check (Astral's ty)
uv run prek run --files path/to/file.py    # Run ALL pre-commit hooks on specific files
uv run prek run --all-files                # Run ALL hooks on all files (slow)
uv run prek run ruff --files <file>        # Run single hook on specific files
```

### Testing

```bash
uv run pytest                              # Run full test suite (parallel via xdist)
uv run pytest -m "not slow"                # Skip slow tests
uv run pytest --cov=scripts                # With coverage
uv run pytest plugins/development-harness/tests/  # Specific test directory
uv run pytest plugins/development-harness/tests/test_migrate_tasks_to_github.py  # Specific test file
```

### Plugin Testing

```bash
claude --plugin-dir ./plugins/python3-development       # Load single plugin
claude --plugin-dir ./plugins/holistic-linting          # Load multiple plugins
/plugin marketplace add ./.claude-plugin/marketplace.json  # Add local marketplace
/plugin install python3-development@jamie-bitflight-skills --scope local
/plugin validate ./plugins/plugin-name                  # Validate plugin structure
```

### MCP Server Scripts

```bash
uv run plugins/development-harness/scripts/run_backlog_server.py  # Backlog MCP server
uv run plugins/development-harness/scripts/run_sam_server.py      # SAM MCP server
```

## Directory Structure

```
claude_skills/
├── .claude/                    # Claude Code local config
│   ├── skills/                 # Symlinked skill directories
│   ├── commands/               # Command markdown files
│   ├── agents/                 # Agent markdown files
│   ├── hooks/                  # Session hooks (JS/CJS)
│   ├── backlog/                # Local backlog cache
│   ├── plan/                   # Plan artifacts (architect/, tasks-*, feature-context-*)
│   └── settings.json           # Permissions and hook config
├── .claude-plugin/
│   └── marketplace.json        # Plugin registry manifest
├── plugins/                    # All 22+ plugins
│   └── {plugin-name}/
│       ├── .claude-plugin/
│       │   └── plugin.json     # Required: plugin manifest
│       ├── skills/             # Skill directories (SKILL.md + references/)
│       ├── commands/           # Optional: slash command definitions
│       ├── agents/             # Optional: agent definitions
│       ├── scripts/            # Python scripts (PEP 723 or modules)
│       └── README.md
├── scripts/                    # Root-level utility scripts
├── tests/                      # Root-level tests
├── plan/                       # Task/plan artifacts (YAML, markdown)
├── research/                   # Research artifacts
├── sessions/                   # cc-sessions framework
├── docs/                       # Documentation (MCP docs, etc.)
├── pyproject.toml              # Python config (linting, type checking, test config)
├── .pre-commit-config.yaml     # prek hook configuration
├── .mcp.json                   # MCP server definitions
├── package.json                # Node.js config (biome, hooks)
└── biome.json                  # JS/TS formatter config
```

## Plugin Structure

Every plugin follows this pattern:

```
plugins/{name}/
├── .claude-plugin/
│   └── plugin.json             # REQUIRED: name, description, version, skills[], commands[], agents[]
├── skills/
│   └── {skill-name}/
│       ├── SKILL.md            # REQUIRED: YAML frontmatter (name, description) + markdown body
│       └── references/         # Optional: reference docs
├── commands/                   # Optional: .md command definitions
├── agents/                     # Optional: .md agent definitions
├── scripts/                    # Optional: Python scripts
└── README.md                   # Optional
```

### SKILL.md Frontmatter

```yaml
---
name: skill-name
description: Description with trigger conditions
---
```

### plugin.json Schema

```json
{
  "name": "plugin-name",
  "description": "ACTION->TRIGGER->OUTCOME format",
  "version": "1.0.0",
  "skills": ["./skills/skill-name"],
  "commands": ["./commands"],
  "agents": ["./agents"]
}
```

## Code Conventions

### Python

- **Always** include `from __future__ import annotations` as first import
- **Docstrings**: Google convention (`Args:`, `Returns:`, `Raises:`)
- **Type hints**: Required for all public functions
- **Max line length**: 120 characters
- **Generics**: Use native forms (`list[str]`, `dict[str, Any]` not `List[str]`)
- **Imports**: isort with `combine-as-imports = true`, `force-single-line = false`
- **Banned**: `requests` library — use `httpx` instead
- **Scripts**: PEP 723 inline metadata (`# /// script`) for standalone scripts run via `uv run --script`

### Markdown (Skills/Commands/Agents)

- Skills are **AI-facing documentation**, NOT user documentation
- Use imperative language ("The model MUST...")
- Include XML tags for structured sections
- Cite sources with URLs and access dates
- File references use `./` relative prefix

### JavaScript/TypeScript

- Formatted with Biome (`biome.json`)
- Pre-commit hooks use CJS format (`.cjs`)

## Commit Conventions

This repo enforces **Conventional Commits** with `--strict --force-scope` (scope is **required**):

```
type(scope): description

feat(auth): add user authentication
fix(parser): handle null pointer exception
docs(claude): update skills documentation
refactor(api): extract validation logic
```

Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**NEVER use `--no-verify` or flags that bypass git hooks.** If a hook fails, fix the underlying issue.

## Testing Patterns

- **Framework**: pytest with `pytest-xdist` (parallel), `pytest-asyncio` (async), `pytest-mock`
- **Markers**: `unit`, `integration`, `e2e`, `slow`, `demos`
- **Async mode**: `asyncio_mode = "auto"` — tests auto-detect async
- **Test discovery**: Multiple test directories configured in `pyproject.toml [tool.pytest.ini_options] testpaths`
- **Type checker exclusions**: Test files get relaxed rules in `pyproject.toml` per-file overrides
- **Test file placement**: Tests go in `plugins/{name}/tests/` or root `tests/`

## Type Checking

Two type checkers run in CI:

1. **ty** (Astral, primary) — `uv run ty check .`
2. **basedpyright** (secondary) — run via `pep723-loader`

### Known ty overrides (in `pyproject.toml [tool.ty]`)

- Test files get relaxed rules (`call-non-callable = "warn"`, etc.)
- `plugins/agentskill-kaizen/**` has `call-non-callable = "warn"` (prefixspan incomplete stubs)
- Symlinked directories excluded: `plugins/uv/skills/uv`, `plugins/development-harness/skills/implementation-manager`

## CI Pipeline (`.github/workflows/code-quality.yml`)

Quality Gate requires ALL of these to pass:

| Job | What it does |
|-----|-------------|
| `lint-python` | Ruff lint + format (via prek) |
| `typecheck-python` | basedpyright |
| `typecheck-ty` | ty (Astral) |
| `lint-js` | Biome (JS/TS/JSON) |
| `lint-markdown` | markdownlint-cli2 |
| `lint-shell` | shellcheck + shfmt |
| `validate-plugins` | skilllint (plugin/skill structure) |
| `manifest-sync` | Auto-sync plugin manifests |
| `file-hygiene` | trailing whitespace, line endings, large files, merge conflicts |
| `test-python` | pytest |
| `test-node` | npm test (if defined) |

## Backlog & Planning System

### Backlog (MCP-driven)

The backlog system uses MCP tools (prefix: `mcp__plugin_dh_backlog__`) — **never edit `.claude/backlog/` files directly**.

Key tools: `backlog_add`, `backlog_list`, `backlog_view`, `backlog_update`, `backlog_close`

- GitHub Issues are the source of truth; `.claude/backlog/` is local cache
- Before starting multi-step work: create a backlog item via `backlog_add`
- Use `backlog_groom` with `append=True` for incremental section writes

### Planning Artifacts

- `plan/architect-{name}.md` — Architecture decisions
- `plan/tasks-{id}-{name}.yaml` — Task decompositions
- `plan/feature-context-{name}.md` — Feature context documents
- `plan/P{NNN}-{name}.yaml` — Follow-up task files

### Rule Files

| File | Purpose |
|------|---------|
| `.cursor/rules/backlog-before-work.mdc` | Always create backlog items for multi-step work |
| `.agent/rules/git-commits.md` | Commit message rules (conventional commits, no --no-verify) |
| `.github/copilot-instructions.md` | Copilot agent instructions (also serves as repo overview) |

## MCP Configuration

`.mcp.json` defines MCP servers. The project uses:

- **Ref-local**: Documentation reference tools
- **context7-local**: Context7 MCP
- **octocode**: Code search

## Gotchas & Non-Obvious Patterns

1. **Always `uv run`**: Never run Python commands directly — always prefix with `uv run`
2. **prek not pre-commit**: This repo uses `prek` (Rust-based), not `pre-commit`. Same config, different binary.
3. **Symlink issues on Windows**: Git symlinks (mode 120000) become plain files on Windows. The `repair-symlinks` pre-commit hook fixes this. Both `ruff` and `ty` have `extend-exclude` entries for symlinked directories.
4. **Skip magic trailing comma**: Ruff config has `skip-magic-trailing-comma = true` — formatting differences around trailing commas are expected.
5. **EXE003 ignored**: Scripts with `uv run --script` shebang pattern trigger EXE003 (intentionally suppressed).
6. **pytest parallelism**: Tests run with `-n auto --dist loadgroup` (xdist). Tests marked with `@pytest.mark.xdist_group` run in same worker.
7. **No uv workspace**: plugin MCP servers are PEP 723 self-resolving scripts (inline `# /// script` deps are the runtime source of truth); root `pyproject.toml` dev-deps only mirror them for `ty`/`ruff`/IDE. No `[tool.uv.workspace]`, no per-plugin `uv.lock`.
8. **Markdown lint exclusions**: `plan/` and `.claude/backlog/` are excluded from markdownlint (they may have intentionally relaxed formatting).
9. **Skilllint hook**: The pre-commit hook runs `uvx skilllint@latest check --fix` on SKILL.md, plugin.json, agent, and command files.
10. **conftest name collision**: `plugins/scientific-method/mcp/experiment-registry/tests` is excluded from pytest testpaths because its conftest collides with development-harness's conftest (both resolve as "tests.conftest").
11. **Banned API**: `requests` is banned — use `httpx` (enforced by ruff `flake8-tidy-imports`).
12. **PEP 723 scripts**: Standalone scripts use `#!/usr/bin/env -S uv run --quiet --script` with inline metadata blocks. This allows `uv run script.py` to auto-install dependencies.

## File Locations Quick Reference

| Purpose | Location |
|---------|----------|
| AI project instructions | `.claude/CLAUDE.md` (primary context file for Claude Code) |
| Linting config | `pyproject.toml [tool.ruff]` |
| Type checking config | `pyproject.toml [tool.ty]` |
| Test config | `pyproject.toml [tool.pytest.ini_options]` |
| Pre-commit hooks | `.pre-commit-config.yaml` |
| Markdown lint config | `.markdownlint-cli2.jsonc` |
| Plugin registry | `.claude-plugin/marketplace.json` |
| MCP servers | `.mcp.json` |
| Session hooks | `.claude/hooks/` |
| CI pipeline | `.github/workflows/code-quality.yml` |

## Development Workflow

1. **Start work**: Create a backlog item via MCP `backlog_add` (for multi-step tasks)
2. **Plan**: Write architect/feature-context docs in `plan/`
3. **Implement**: Write code following conventions above
4. **Validate**: Run `uv run ruff check --fix && uv run ruff format && uv run ty check`
5. **Test**: Run `uv run pytest` on affected areas
6. **Pre-commit**: Run `uv run prek run --files <changed-files>` to verify hooks pass
7. **Commit**: Use conventional commit format with required scope
