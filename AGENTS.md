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
uv self update                             # Keep uv itself current (v0.10.0+ required)
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
uvx skilllint@latest check <path>          # Validate skill/agent/plugin frontmatter
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

Both servers are built with FastMCP v3. To validate a change against the live source (not the
installed plugin cache):

```bash
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_backlog_server.py" \
  --target <tool_name> --input-json '{"...": "..."}'
```

Use `--command "uv run --script <path>"` — invoking `fastmcp list/call <path>` directly conflicts
with the caller's own asyncio event loop. Suppress banner/log noise with the `FASTMCP_*` env vars
above rather than redirecting stderr to `/dev/null`, which would also hide real errors. `--json`
output is wrapped: unwrap with `json.loads(json.loads(stdout)["content"][0]["text"])`.

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

### Agent Frontmatter (plugin-shipped agents)

- Plugin-shipped agents (files under a plugin's `agents/`) forbid `hooks`, `mcpServers`, and
  `permissionMode` frontmatter fields — Claude Code ignores them or refuses to start the agent. Do
  not list these as supported fields when authoring plugin agents.
- `SubagentStop` hooks use `type: "prompt"` for context-aware validation — no `matcher` needed.
- The plugin-validator hook may silently strip unexpected frontmatter fields (e.g. `name` from
  skill frontmatter) — a field disappearing after commit is validator auto-fix, not a manual edit.

### Documentation Convention

Plugins commonly ship a `{plugin-name}-meta-docs` skill that dynamically lists the plugin's
`docs/` directory at load time (e.g. `find ${CLAUDE_PLUGIN_ROOT}/docs -name '*.md' -type f | sort`)
instead of hardcoding relative paths to another plugin's docs. When a skill needs another plugin's
documentation, load that plugin's meta-docs skill rather than hardcoding a cross-plugin relative
path — those break on every directory restructure.

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

### CLI and script output — agent-only, never human-facing

Every plugin in this repo exists to be consumed by an AI agent harness (Claude Code, Codex,
OpenCode, GitHub's coding agent) — that is the whole purpose of a Claude Code plugin. No script,
CLI tool, or MCP server under `plugins/**/scripts/` or `plugins/**/skills/*/scripts/` has a human
running it interactively at a terminal, ever. Design output accordingly, not as a dual-audience
guess:

- **Structured/tabular output → JSON, not aligned plain-text tables.** A text table binds each
  value to its meaning via column *position* (nth value = nth header); JSON binds via an explicit
  *repeated key* at each value — a more direct, unambiguous token-level association for an LLM
  parsing the output, with no risk of misparsing when a cell value contains whitespace. Emit
  compact JSON (`json.dumps(data)` / `model_dump_json()`, no `indent=`) — see
  `.claude/CLAUDE.md` "Code Quality Standards" for the JSON-output rule.
- **`logging` is for debug/trace/forensic output only** — never for primary output a calling agent
  needs to read or parse. Status messages, results, and errors meant to be consumed by the caller
  go through direct stdout/stderr emission (`typer.echo()`, `print()`, structured JSON), not a
  logger.
- **Never add a `--json`/`--format text|json` dual-mode flag "just in case."** There is one
  consumer. Dual-mode output is the right pattern for genuinely mixed-audience tools (`kubectl`,
  `gh`, `docker`) — it is not the right pattern here. Before assuming a tool has a human reader,
  verify by checking actual callers (`grep` for the script name across `plugin.json`, `hooks.json`,
  `SKILL.md` workflow steps) rather than inferring "interactive use" from docstring language.
- **Rich (`rich.console.Console`, `Table`, `Panel`, `Progress`)** defaults to a hardcoded 80-column
  width with no TTY attached (`rich/console.py`: `width = width or 80`), wrapping or truncating
  output — a correctness bug for an agent-only consumer, not a cosmetic one. Prefer plain
  `typer.echo()`/JSON over Rich for agent-facing CLI output. If Rich is genuinely needed (e.g. a
  `--verbose` diagnostic stream), see `python-engineering:python3-cli`'s
  `references/typer-rich-non-tty-patterns.md` for the measure-and-render pattern that keeps it
  data-loss-safe; do not use Rich's TTY-oriented defaults unmodified.

### Markdown (Skills/Commands/Agents)

- Skills are **AI-facing documentation**, NOT user documentation
- Use imperative language ("The model MUST...")
- Include XML tags for structured sections
- Cite sources with URLs and access dates
- File references use `./` relative prefix

**SKILL.md string substitution** happens at load time, including inside fenced code blocks —
backslash-escaping (`\$1`) does not prevent it:

- `$ARGUMENTS`, `$ARGUMENTS[N]`, `$0`–`$9` — arguments passed at invocation
- `${CLAUDE_SESSION_ID}` — current session ID
- `${CLAUDE_SKILL_DIR}` — the skill's own directory (for plugin skills: the skill subdirectory,
  NOT the plugin root)
- `${CLAUDE_PLUGIN_ROOT}` — the plugin's root directory. Applies only when the loaded `SKILL.md`
  belongs to a plugin (not a project-level `.claude/skills/` skill). Substitutes throughout the
  entire rendered body — plain prose and markdown link targets, not only `` !`bash` `` injection
  lines — before the model sees the text. Absent from `code.claude.com/docs/en/skills.md`'s own
  substitution table (a documentation gap on Anthropic's side, not evidence against the behavior).
  Verified live via `dh-meta-docs` and `implementation-manager`, and canary-tested against a
  no-variable control line (2026-08-06) — see
  `.claude/agent-memory/python-engineering-python-cli-architect/project_claude_plugin_root_bang_exec_vs_later_bash.md`.
- Literal `$N` is only safe to document inside `references/*.md` files, which are not substituted —
  a SKILL.md itself cannot explain this syntax without being corrupted by it. `${CLAUDE_PLUGIN_ROOT}`
  and `${CLAUDE_SKILL_DIR}` are likewise NOT substituted inside `references/*.md` files — only the
  `SKILL.md` body itself. Canary-test any new substitution-adjacent pattern
  (`/example-argument-substitution`) before applying it across multiple files.

Hook/command scripts additionally receive these as real process env vars (a separate mechanism from
the load-time text substitution above): `CLAUDE_PROJECT_DIR` (project root, all hooks),
`CLAUDE_PLUGIN_ROOT` (plugin root, plugin hooks only — `CLAUDE_PLUGIN_DIR` does not exist),
`CLAUDE_ENV_FILE` (SessionStart hooks only), `CLAUDE_CODE_REMOTE`.

**Multi-mode workflow skills**: when a SKILL.md parses `$ARGUMENTS` into a structured `<input>`
JSON block, its `references/workflows/*.md` files use self-closing XML tags (e.g. `<item_ref/>`)
as **labels naming a key in that JSON** — not variables passed into the file. Reference them as
"the value from the `item_ref` key," never "the parser provides `item_ref`."

**Agent `tools:` frontmatter** requires exact, correctly-cased tool names
(`mcp__Ref__ref_search_documentation`, not `mcp__ref__...`) — wildcards (`*`) and short-form MCP
aliases (`mcp__context-mode__ctx_stats` instead of the full
`mcp__plugin_context-mode_context-mode__ctx_stats`) silently resolve to zero tools, with no error
raised.

After editing any SKILL.md, invoke the skill and confirm it still renders correctly with no
unexpected prompts or extra steps.

### JavaScript/TypeScript

- Formatted with Biome (`biome.json`)
- Pre-commit hooks use CJS format (`.cjs`)

## Commit Conventions

This repo enforces **Conventional Commits** with `--strict --force-scope` (scope is **required**) via
the `conventional-pre-commit` hook in `.pre-commit-config.yaml`.

**NEVER use `--no-verify` or flags that bypass git hooks.** If a hook fails, fix the underlying issue.

## Working Tree Safety

The working tree may hold another contributor's uncommitted, legitimate work. Before reverting or
discarding an unexpected diff (`git checkout`, `git restore`, `git reset --hard`), read the diff
and confirm it is unintended rather than assuming it is an agent artifact — an unexplained change
is a reason to investigate and ask, not a reason to revert.

### Branch-transfer preflight

1. Before branch switching, selective checkout or cherry-pick, stash cleanup, or source-branch deletion, run
   `uv run scripts/audit_branch_transfer.py --source <source-ref> --base <base-ref> --target <target-ref> --manifest <manifest.json>`.
2. Build the compact JSON manifest using the schema in `uv run scripts/audit_branch_transfer.py --help`; record
   each source-only commit and changed path as transferred, intentionally excluded with a non-empty reason, or
   preserved by a named recovery ref.

Complete the operation only when the guard emits `{"ok":true}`: the manifest accounts for every source-only
commit and changed path.

## Testing Patterns

- **Framework**: pytest with `pytest-xdist` (parallel), `pytest-asyncio` (async), `pytest-mock`
- **Markers**: `unit`, `integration`, `e2e`, `slow`, `demos`
- **Async mode**: `asyncio_mode = "auto"` — tests auto-detect async
- **Test discovery**: Multiple test directories configured in `pyproject.toml [tool.pytest.ini_options] testpaths`
- **Type checker exclusions**: Test files get relaxed rules in `pyproject.toml` per-file overrides
- **Test file placement**: Tests go in `plugins/{name}/tests/` or root `tests/`
- **Close criteria**: passing pre-existing tests proves no regression, not correctness — do not
  mark a fix or issue closed without a test that specifically demonstrates the new/fixed behavior
- **SAM/backlog MCP error contract**: `sam_schema/server.py` tool handlers let exceptions
  (`PlanNotFoundError`, `TaskNotFoundError`, etc.) propagate rather than returning
  `{"error": ...}` dicts — FastMCP converts them to `isError=true` responses. Tests for
  invalid-input paths must use `pytest.raises(ToolError)` (`fastmcp.exceptions.ToolError`), not
  `assert result["error"]`.

## Type Checking

This repository enforces **ty** (Astral) only: `uv run ty check .`. `mypy`,
`pyright`, and `basedpyright` are not repository quality gates; references to
them in plugin-facing documentation describe options for external plugin users.

### Known ty overrides (in `pyproject.toml [tool.ty]`)

- Test files get relaxed rules (`call-non-callable = "warn"`, etc.)
- `plugins/agentskill-kaizen/**` has `call-non-callable = "warn"` (prefixspan incomplete stubs)
- Symlinked directories excluded: `plugins/uv/skills/uv`, `plugins/development-harness/skills/implementation-manager`

### Common ty Failure Patterns

- **`unresolved-attribute` on a `ModuleType`**: almost always means the module's directory is
  missing from `[tool.ty.environment] extra-paths` in `pyproject.toml`. Add it there first —
  mirroring the matching entry already in `[tool.pytest.ini_options] pythonpath` — and re-run
  before investigating the importing code itself.
- **TypedDict nominal typing**: ty treats a `TypedDict` as scoped to its defining module — two
  structurally identical TypedDicts from different modules are incompatible types to ty. Avoid
  making an implementation explicitly inherit from a `@runtime_checkable` Protocol when the
  Protocol's signatures reference TypedDicts duplicated across modules (`isinstance()` checks
  still work without explicit inheritance); if inheritance is required, have all signatures import
  the TypedDicts from one canonical module.

## CI Pipeline (`.github/workflows/code-quality.yml`)

Quality Gate requires ALL of these to pass:

| Job | What it does |
|-----|-------------|
| `lint-python` | Ruff lint + format (via prek) |
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

Before creating or updating Beads, skills, or persistent agent memories, load `writing-for-agents`; write ordered
steps with checkable, exhaustive completion criteria and keep each shared reference in one source.

### Backlog (provider-native plus structured MCP operations)

The backlog system uses the configured provider's native interface and selected structured MCP tools (prefix: `mcp__plugin_dh_backlog__`) — **never edit `.claude/backlog/` files directly**. In a Beads workspace, use `bd` directly for Beads-native issue, status, dependency, readiness, notes, and metadata operations.

Key tools: `backlog_add`, `backlog_list`, `backlog_view`, `backlog_update`, `backlog_close`

- The selected backend is the source of truth; in the default deployment this is GitHub Issues, while `.claude/backlog/` is local cache
- Before starting multi-step work: create a backlog item through the selected backend or its structured `backlog_add` operation
- Use `backlog_groom` with `append=True` for incremental section writes

### Planning Artifacts

- `plan/architect-{name}.md` — Architecture decisions
- `plan/tasks-{id}-{name}.yaml` — Task decompositions
- `plan/feature-context-{name}.md` — Feature context documents
- `plan/P{NNN}-{name}.yaml` — Follow-up task files
- Task YAML `agent:` fields must use plugin-qualified names (e.g. `dh:service-docs-maintainer`) —
  a bare name (`service-docs-maintainer`) silently degrades to generalist behavior if no plugin
  matches, or is ambiguous if two plugins ship an agent with that name
- Invoke `complete-implementation` with the implementation plan path (e.g. `P964-....yaml`), never
  the QG plan it generates internally — passing the QG plan back in produces a spurious second
  `qg-qg-...` plan and re-runs quality gates on an already-complete pass

### Rule Files

| File | Purpose |
|------|---------|
| `.cursor/rules/backlog-before-work.mdc` | Always create backlog items for multi-step work |
| `.agent/rules/git-commits.md` | Commit message rules (conventional commits, no --no-verify) |

GitHub's coding agent reads `AGENTS.md` directly — `.github/copilot-instructions.md` (a subset of
this file) was removed to avoid two files drifting out of sync.

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
13. **prek stash conflict**: prek stashes unstaged changes before running hooks. If a formatter hook (ruff-format, etc.) modifies staged files and the stash cannot restore cleanly, prek rolls back the hook's changes and the commit fails ("Stashed changes conflicted..."). Fix: `git add -u` to stage the hook's auto-fixes, then retry the commit — the second attempt has nothing left to stash.
14. **Dependency security upgrades**: use `uv add "pkg>=X.Y.Z"` (updates `pyproject.toml` and `uv.lock` atomically with explicit version output) rather than `uv lock --upgrade-package pkg` (silent) or manually verifying line numbers in `uv.lock` (4000+ lines — line numbers do not correspond reliably to package versions). Confirm with `uv tree | grep pkg`.
15. **`.claude/` vs `docs/`**: `.claude/` is Claude Code configuration; `docs/` is project documentation. Check for an existing directory convention (`ls` the likely parent) before choosing where to create a new file.
16. **No `git stash` on the primary checkout**: compare against a clean baseline in an isolated worktree instead — other agents may be mid-write there.

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

## PR Review Protocol

When asked to check or address PR reviews, always fetch BOTH levels of feedback:

```bash
# 1. Top-level review state (APPROVED / CHANGES_REQUESTED / COMMENTED)
gh pr view <N> -R Jamie-BitFlight/claude_skills --json reviews,reviewDecision

# 2. Inline comments on specific lines — this is where substantive findings live
gh api repos/Jamie-BitFlight/claude_skills/pulls/<N>/comments --jq '[.[] | {path, line, body}]'
```

`reviewDecision` being empty and `state: COMMENTED` does NOT mean no findings. Codex and other bots post substantive per-line feedback as inline comments, not as blocking review verdicts. Checking only the top-level state misses these entirely.

Address all inline comments before declaring the PR review complete.

## GitHub CLI Conventions

- This checkout's git remote points to a local proxy (`127.0.0.1`), not `github.com` — `gh` cannot
  auto-detect the repository. Pass `-R <owner/repo>` on every `gh` command. `GITHUB_TOKEN` set in
  environment handles authentication automatically. The correct `<owner/repo>` for this checkout is
  written to `.dh/config.yaml` under `gh.repo` by `setup_gh.py`.
- Prefer extending this repo's existing GitHub tooling — backlog MCP tools
  (`mcp__plugin_dh_backlog__*`) and PyGithub-based scripts — over adding new `gh` CLI usage; the
  project has invested in portable Python tooling that needs no separate `gh` auth/installation.
- When `gh` is the right tool, prefer `gh graphql` (single call) over `gh api` (slower, often
  multi-step) for new usage — the PR Review Protocol above is an existing exception that already
  depends on `gh api`.
- To read a GitHub-hosted file's contents, use
  `gh api repos/{owner}/{repo}/contents/{path}?ref={branch} --jq '.content' | base64 -d` rather
  than a URL-fetch tool — it authenticates automatically and returns exact file bytes.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
