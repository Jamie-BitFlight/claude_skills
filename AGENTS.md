# AGENTS.md — Agent Working Guide for claude_skills

This document covers everything an AI agent needs to work effectively in this repository.

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

## Essential Commands

### Environment Setup (Required First)

```bash
uv self update                             # Keep uv itself current (v0.10.0+ required)
uv sync                                    # Install all dependencies, create .venv/
uv run prek install -t pre-commit -t commit-msg -t pre-rebase -t post-merge  # Install git hooks
```

### Linting & Formatting

For full uv/ty/ruff usage guidance beyond this repo's own overrides, load the `astral` plugin
skills (`/astral:uv`, `/astral:ty`, `/astral:ruff`) if installed, or see `docs.astral.sh` directly.

Run lint, format, and type checks through `prek` — it dispatches to ruff, ty, and every other
configured hook, and skips hooks that don't apply to the given files.

```bash
uv run prek run --files path/to/file.py    # Run ALL pre-commit hooks on specific files
uv run prek run --all-files                # Run ALL hooks on all files (slow)
uv run prek run ruff --files <file>        # Run one hook by id (e.g. ruff, ty) on specific files
uvx skilllint@latest check <path>          # Validate skill/agent/plugin frontmatter
```

### Testing

```bash
uv run pytest                              # Fast suite (parallel via xdist); e2e, cross_backend, and integration are deselected by addopts
uv run pytest -m "not slow"                # Additionally skip slow tests
uv run pytest -m integration plugins/development-harness/tests/   # Integration tests (deselected by default)
uv run pytest plugins/development-harness/tests/  # Specific test directory
uv run pytest plugins/development-harness/tests/test_migrate_tasks_to_github.py  # Specific test file
```

Coverage (`--cov=scripts --cov=plugins`) is always on via addopts — passing `--cov` again is redundant.

### Plugin Testing

```bash
claude --plugin-dir ./plugins/python3-development       # Load single plugin
claude --plugin-dir ./plugins/holistic-linting          # Load multiple plugins
/plugin marketplace add ./.claude-plugin/marketplace.json  # Add local marketplace
/plugin install python3-development@jamie-bitflight-skills --scope local
/plugin validate ./plugins/plugin-name                  # Validate plugin structure
```

### MCP Server Validation

Read [Codex MCP Runtime Guide](./docs/codex-mcp-runtime.md) before configuring
or validating a Codex marketplace MCP. It documents Codex's literal `env`
behavior, `env_vars` pass-through, the two-root `cwd` plus `PWD` pattern, and
host prerequisites for FastMCP and project hooks.

For a FastMCP server, use the active `fastmcp-creator:fastmcp-client-cli` skill for protocol
checks and `fastmcp-creator:fastmcp-python-tests` for Python tests when the harness exposes them.
If either is unavailable, read its corresponding `SKILL.md` under
`plugins/fastmcp-creator/skills/` before choosing test commands; do not invent an invocation or
test pattern from memory.

Validate separate concerns separately:

1. **Server protocol and tools**: from outside the plugin directory, use `fastmcp list` to
   discover tools and `fastmcp call` to invoke one against the configured stdio command. Use a
   non-sensitive temporary fixture and assert a successful, meaningful response.
2. **Codex plugin integration**: install the plugin from an isolated local marketplace and
   invoke a named MCP tool through Codex. Do not count manually opening `SKILL.md` or starting a
   server process as proof that Codex loaded the plugin.
3. **Claude plugin integration**: start Claude with the packaged plugin and invoke a named MCP
   tool. If Claude authentication is unavailable, record this as blocked rather than inferring
   runtime compatibility from static configuration.

FastMCP client syntax is versioned. Run `fastmcp call --help` before relying on an invocation
from documentation; for FastMCP 3.4.5, use explicit `--command` and `--target` options together.

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

Two further PEP 723 wrappers let the development-harness plugin run standalone, without the
per-plugin `pyproject.toml`/project env this repo intentionally removed:

```bash
uv run plugins/development-harness/scripts/run_sam_cli.py --help    # SAM CLI, self-resolving
uv run plugins/development-harness/tests/run_pytest.py              # Run plugin test suites
```

`run_sam_cli.py` is a thin wrapper around `sam_schema.cli:app`. `run_pytest.py` `os.chdir`s to the
plugin root and forwards to `pytest.main()`, defaulting to `["tests", "tests_sam",
"sam_schema/tests", "backlog_core/tests"]` when no paths are given, and always injecting
`--asyncio-mode=auto` and `--strict-config` — a standalone bundle has no parent `pyproject.toml` to
supply `asyncio_mode = "auto"`, so pytest's strict default would otherwise silently skip this
repo's intentionally-undecorated async tests, and `--strict-config` turns invalid or unavailable
pytest configuration into a hard failure instead of a silently degraded warning.

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

A plugin's directory name need not equal its install name: `plugins/development-harness` installs
as `dh`, `plugins/the-rewrite-room` as `rwr`, `plugins/clang-format` as `clang-format-configuration`.

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

Plugins commonly ship a `{plugin-name}-meta-docs` skill so other skills can reach the plugin's
`docs/` without hardcoding a cross-plugin relative path — those break on every directory
restructure. When a skill needs another plugin's documentation, load that plugin's meta-docs skill
instead.

A bare path listing has no value on its own — an agent can already enumerate `docs/` itself with
`Glob`/`find`. The value of a hand-maintained list is the annotation beside each path: a stated
reason to read that file, which is what lets the agent skip everything else in the list with
confidence. List only docs a real skill or agent hook actually depends on discovering through this
index. Add an entry only when some skill or agent file's hook text depends on this index resolving
it (e.g. "load `{plugin}-meta-docs` and read the X document it lists") — confirm that dependency
exists before adding, give the entry a specific reason to read it, and drop the entry once nothing
depends on it. Use `${CLAUDE_PLUGIN_ROOT}` for each listed path so the substitution still resolves
correctly regardless of installation location.

## Code Conventions

### Python

- **Always** include `from __future__ import annotations` as first import
- **Docstrings**: Google convention (`Args:`, `Returns:`, `Raises:`)
- **Type hints**: Required for all public functions
- **Max line length**: 120 characters
- **Generics**: Use native forms (`list[str]`, `dict[str, Any]` not `List[str]`)
- **Imports**: isort with `combine-as-imports = true`, `force-single-line = false`
- **Banned**: `requests` library — use `httpx` instead (enforced by ruff `flake8-tidy-imports`)
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
  compact JSON (`json.dumps(data)` / `model_dump_json()`, no `indent=`) for this — output a script
  or CLI emits for an agent to parse. The rule governs JSON a program emits at runtime, nothing
  else. It does not apply to JSON files committed to the repo as configuration or data — every
  harness plugin manifest (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`),
  `package.json`, `marketplace.json`, tool configs, fixtures, snapshots. Humans read and edit
  those, git diffs them line by line, and non-AI tooling consumes them; they keep their existing
  pretty-printed formatting. Never reformat one as part of an unrelated change.
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

### Writing `./rules/*.md` Files

Rules are the current requirement only — never provenance, citations, or narrative. Put those in
the commit message or PR description; put a durable architecture decision in `docs/` instead.

Rules are read only when small. Tightening an existing rule means rewriting it from scratch as
flat directives, not `Edit`-trimming words from its existing structure.

### Markdown (Skills/Commands/Agents)

- Skills are AI-facing documentation, NOT user documentation
- Runtime skill/agent/reference content has exactly one reader: the agent executing it. Never write
  a maintenance aside ("don't restate this here", "keep this in sync with X", "note for future
  editors") into runtime content.
- Design-time artifacts such as `SKILL-GOALS.md`, `BENCHMARKS.md`, `MAINTENANCE.md`,
  `maintenance/*.md`, and `evals/**` travel inside the skill package but do not load with
  `SKILL.md`. Do not link to them from runtime skill content. Maintenance, review, and evaluation
  workflows may read them explicitly when making decisions about the skill. Put transient
  provenance in a commit or PR and durable architectural decisions in an ADR.
- Use imperative language ("The model MUST...")
- No decorative `**bold**` — a model reads it as no stronger a signal than plain text. Use
  imperative wording for emphasis, backtick code-spans for literal identifiers (tool names, config
  keys)
- Include XML tags for structured sections
- Cite sources with URLs and access dates (not `./rules/*.md` — see above)
- File references use `./` relative prefix
- Skill handoffs use plain prose (`plugin:skill-name`, `/plugin:skill-name`), not
  `Skill(skill="...")` — that syntax is Claude-Code-only and this repo's plugin content also
  targets Codex and OpenCode. Existing `Skill(...)` blocks are pre-convention, not bugs.

Before writing or editing any SKILL.md, load `./rules/skill-substitution.md` — load-time
substitution can silently corrupt the rendered skill if unaccounted for.

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
- **Markers**: `unit`, `integration`, `e2e`, `slow`, `demos`, `cross_backend`, `critical`,
  `allow_startup_sync`
- **Default deselection**: addopts include `-m "not e2e and not cross_backend and not integration"`,
  so a bare `uv run pytest` runs the fast in-process suite only. Integration tests (real-subprocess
  CLI/network-guard behavior, ~2-30s each) and cross-backend tests run as separate CI jobs; e2e
  tests need a live `GITHUB_TOKEN` and run only on main.
- **Async mode**: `asyncio_mode = "auto"` — tests auto-detect async
- **Test discovery**: Multiple test directories configured in `pyproject.toml [tool.pytest.ini_options] testpaths`
  (plugin `tests/` dirs, `development-harness`'s `tests_sam`/`sam_schema/tests`/`backlog_core/tests`,
  root `tests/`, `examples/solid-review-ab/tests`, and the scripts dirs that host colocated tests)
- **Type checker exclusions**: Test files get relaxed rules in `pyproject.toml` per-file overrides
- **Test file placement**: A test lives beside the code it exercises. Tests for code inside a
  plugin go in that plugin's own test directory (`plugins/{name}/tests/`, or the module-local
  directory a plugin already uses, e.g. `sam_schema/tests/`). Root `tests/` is only for code that
  serves repository maintenance and systems — `scripts/`, `.claude/` skill scripts, and CI
  tooling. Placement follows the import target, not convenience: a test that imports plugin code
  belongs in that plugin even when it also touches root tooling. A plugin test placed in root
  `tests/` runs in CI but is invisible to that plugin's standalone runner, so its coverage
  silently disappears for anyone who installs the plugin on its own. Move a misplaced test file
  to the correct location rather than leaving it and noting the exception.
- **Close criteria**: passing pre-existing tests proves no regression, not correctness — do not
  mark a fix or issue closed without a test that specifically demonstrates the new/fixed behavior
- **SAM/backlog MCP error contract**: `sam_schema/server.py` tool handlers let exceptions
  (`PlanNotFoundError`, `TaskNotFoundError`, etc.) propagate rather than returning
  `{"error": ...}` dicts — FastMCP converts them to `isError=true` responses. Tests for
  invalid-input paths must use `pytest.raises(ToolError)` (`fastmcp.exceptions.ToolError`), not
  `assert result["error"]`.

## Type Checking

For full ty usage guidance beyond this repo's own overrides, load the `astral` plugin skill
(`/astral:ty`) if installed, or see `docs.astral.sh` directly.

This repository enforces **ty** (Astral) only, run via `prek`. `[tool.basedpyright]` is set to
`typeCheckingMode = "off"` so IDEs do not apply a second checker's defaults.

### ty overrides and suppression policy

Suppression policy (inline `# ty: ignore` prohibited; config-level `[[tool.ty.overrides]]`
relaxation allowed only for the categories in `linting-exceptions.md`) and its rationale live in
`./rules/astral-tool-overrides.md` and `./rules/python-development.md` ("ty Type
Checker Errors") — both load on any `*.py`/`pyproject.toml`/`uv.lock` edit. The current override
list itself lives in `pyproject.toml [tool.ty]`, not restated here.

### Common ty Failure Patterns

- **`unresolved-attribute` on a `ModuleType`**: almost always means the module's directory is
  missing from `[tool.ty.environment] extra-paths` in `pyproject.toml`. Add it there first —
  mirroring the matching entry already in `[tool.pytest.ini_options] pythonpath` — and re-run
  before investigating the importing code itself. For the related `unresolved-import` failure
  (same `extra-paths` root cause, different symptom — the module isn't found at all rather than
  an attribute on it), see `./rules/python-development.md`'s "`unresolved-import` errors"
  section.
- **TypedDict nominal typing**: ty treats a `TypedDict` as scoped to its defining module — two
  structurally identical TypedDicts from different modules are incompatible types to ty. Avoid
  making an implementation explicitly inherit from a `@runtime_checkable` Protocol when the
  Protocol's signatures reference TypedDicts duplicated across modules (`isinstance()` checks
  still work without explicit inheritance); if inheritance is required, have all signatures import
  the TypedDicts from one canonical module.

## CI Pipeline (`.github/workflows/code-quality.yml`)

The `quality-gate` summary job requires ALL of these to pass:

| Job | What it does |
|-----|-------------|
| `lint-python` | Ruff lint + format (via prek) |
| `typecheck-ty` | ty (Astral) |
| `lint-js` | Biome (JS/TS/JSON) |
| `lint-markdown` | markdownlint-cli2 |
| `lint-shell` | shellcheck + shfmt |
| `validate-plugins` | skilllint (plugin/skill structure) |
| `manifest-sync` | Auto-sync plugin manifests; the per-PR plugin.json version-bump check is advisory (`continue-on-error`) — `bump-marketplace.yml` on main is the backstop |
| `file-hygiene` | trailing whitespace, line endings, large files, merge conflicts |
| `test-python` | pytest fast suite (default addopts filter) |
| `test-cross-backend` | pytest `-m cross_backend` on a memory/sqlite matrix (`BACKLOG_BACKEND` env) |
| `test-integration` | pytest `-m integration` on `plugins/development-harness/tests/` |

Advisory jobs outside the gate: `research-validation` (research-corpus template gaps) and
`test-e2e` (live GitHub sandbox issues; main push / manual dispatch only).

Other workflows in `.github/workflows/`: `backlog-sync.yml`, `bump-marketplace.yml`,
`auto-rebase.yml`, `claude.yml`, `claude-code-review.yml`, `copilot-setup-steps.yml`,
`main-ci-health-check.yml`, `quality-gate-audit.yml`.

## Backlog & Planning System

Before creating or updating Beads, skills, or persistent agent memories, load `writing-for-agents`; write ordered
steps with checkable, exhaustive completion criteria and keep each shared reference in one source.

### Backlog (provider-native plus structured MCP operations)

The backlog system uses the configured provider's native interface and selected structured MCP tools (prefix: `mcp__plugin_dh_backlog__`) — **never edit `.claude/backlog/` files directly**. In a Beads workspace, use `bd` directly for Beads-native issue, status, dependency, readiness, notes, and metadata operations.

Key tools: `backlog_add`, `backlog_list`, `backlog_view`, `backlog_update`, `backlog_close`

- The selected backend is the source of truth. **This checkout's backend is GitHub Issues**
  (`.dh/config.yaml`'s `backend.name: github`, repo `Jamie-BitFlight/claude_skills` under `gh.repo`).
  A `.beads/` directory exists here but holds only `bd`-installed git hook shims — no issue
  database, no `issues.jsonl`, no `.beads/dh-backend` opt-in marker — so the Beads blocks near the
  end of this file (`BEADS INTEGRATION` and `BEADS CODEX SETUP`, generic boilerplate the `bd` CLI
  injects and periodically regenerates) do not describe this checkout's backend. Follow this
  section, not those blocks, unless a real Beads database appears. `.claude/backlog/` is local
  cache either way.
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

`plan/` is ignored working context. Use it to design and coordinate in-progress work, but do not
force-add or commit its contents. Put durable user-facing documentation in `docs/` or `research/`
only when that is explicitly part of the requested deliverable.

### Other Tools' Rule Files

Rule files outside `./rules/` that other harnesses read — not a full rule-file index:

| File | Purpose |
|------|---------|
| `.cursor/rules/backlog-before-work.mdc` | Always create backlog items for multi-step work |
| `.cursor/rules/json-no-pretty-print.mdc` | Compact-JSON rule for agent-facing CLI output |
| `.agent/rules/git-commits.md` | Commit message rules (conventional commits, no --no-verify) |

GitHub's coding agent reads `AGENTS.md` directly — `.github/copilot-instructions.md` (a subset of
this file) was removed to avoid two files drifting out of sync.

## Gotchas & Non-Obvious Patterns

1. **prek not pre-commit**: This repo uses `prek` (Rust-based), not `pre-commit`. Same config, different binary.
2. **Symlink issues on Windows**: Git symlinks (mode 120000) become plain files on Windows. The `repair-symlinks` pre-commit hook fixes this. Both `ruff` and `ty` have `extend-exclude` entries for symlinked directories.
3. **Skip magic trailing comma**: Ruff config has `skip-magic-trailing-comma = true` — formatting differences around trailing commas are expected.
4. **EXE003 ignored**: Scripts with `uv run --script` shebang pattern trigger EXE003 (intentionally suppressed).
5. **pytest parallelism**: Tests run with `-n 2 --dist loadgroup` (xdist): one controller plus two workers. Tests marked with `@pytest.mark.xdist_group` run in same worker.
6. **No uv workspace**: plugin MCP servers are PEP 723 self-resolving scripts (inline `# /// script` deps are the runtime source of truth); root `pyproject.toml` dev-deps only mirror them for `ty`/`ruff`/IDE. No `[tool.uv.workspace]`, no per-plugin `uv.lock`.
7. **Ignored planning context**: `plan/` and `.claude/backlog/` are ignored working context and excluded from markdownlint. Do not force-add either directory.
8. **Skilllint hook**: The pre-commit hook runs `uvx skilllint@latest check --fix` on SKILL.md, plugin.json, agent, and command files.
9. **conftest name collision**: `plugins/scientific-method/mcp/experiment-registry/tests` is excluded from pytest testpaths because its conftest collides with development-harness's conftest (both resolve as "tests.conftest").
10. **Banned API**: `requests` is banned — see "Python Conventions" above for the canonical statement and enforcement mechanism. Narrow per-file exceptions exist in `[tool.ruff.lint.per-file-ignores]` (e.g. `backlog_core/sync_state.py`, which must match PyGithub's requests-based exception types).
11. **PEP 723 scripts**: Standalone scripts use `#!/usr/bin/env -S uv run --quiet --script` with inline metadata blocks. This allows `uv run script.py` to auto-install dependencies. Never add `--active` — see `./rules/script-invocation.md` for the isolation rationale.
12. **prek stash conflict**: prek stashes unstaged changes before running hooks. If a formatter hook (ruff-format, etc.) modifies staged files and the stash cannot restore cleanly, prek rolls back the hook's changes and the commit fails ("Stashed changes conflicted..."). Fix: `git add -u` to stage the hook's auto-fixes, then retry the commit — the second attempt has nothing left to stash.
13. **Dependency security upgrades**: use `uv add "pkg>=X.Y.Z"` (updates `pyproject.toml` and `uv.lock` atomically with explicit version output) rather than `uv lock --upgrade-package pkg` (silent) or manually verifying line numbers in `uv.lock` (4000+ lines — line numbers do not correspond reliably to package versions). Confirm with `uv tree | grep pkg`.
14. **`.claude/` vs `docs/`**: `.claude/` is Claude Code configuration; `docs/` is project documentation. Check for an existing directory convention (`ls` the likely parent) before choosing where to create a new file.
15. **No `git stash` on the primary checkout**: compare against a clean baseline in an isolated worktree instead — other agents may be mid-write there.
16. **Bounded subprocess execution**: `scripts/run_bounded.py` runs a command with a timeout and terminates its full process group (POSIX process-group signals; `taskkill /T /F` on Windows) on expiry, including descendants a bare `subprocess.run(timeout=...)` would leave behind. Wrap any external command invocation that may hang or spawn children with `uv run --script scripts/run_bounded.py --timeout-seconds <n> -- <command>`.
17. **MCP runtime tests**: Load the active FastMCP client skill first; if it is unavailable, read the bundled FastMCP client guidance. Invoke the client through a `uv`-managed environment rather than assuming a host-global `fastmcp` binary, and run it from outside the plugin directory. Never use a native agent MCP tool. Wrap each actual `list` or `call` with `uv run --script scripts/run_bounded.py --timeout-seconds 5 -- <command>`; it terminates the process tree on expiry. Retain a redacted result and mark timeouts or startup failures as failed/blocked.
18. **Validation warnings**: Warnings fail validation unless a versioned, scope-limited exception is recorded in the relevant plan with an expiry/review condition. Never disable pytest's strict configuration to make a warning non-fatal; a minimal runner must explicitly retain `--strict-config` and install each configured pytest plugin it needs.

## Security Considerations

- Never commit credentials. `.mcp.json` references API keys by environment indirection
  (`$REF_API_KEY`, `$CONTEXT7_API_KEY`), not literal values — follow that pattern.
- Live e2e tests create real GitHub issues in a sandbox repo and are gated to CI on `main` with
  `GITHUB_TOKEN`; do not run them locally against the production backlog.
- Git hooks are mandatory (see Commit Conventions); `conventional-pre-commit`, `skilllint`, and
  the manifest-sync hook all mutate or validate on commit — do not bypass them.

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
| CI pipeline | `.github/workflows/code-quality.yml` |

## PR Review Protocol

After pushing a commit to a PR, or when asked to check or address PR reviews, load the
`receiving-pr-reviews` skill.

## GitHub CLI Conventions

- The canonical `<owner/repo>` for this checkout is written to `.dh/config.yaml` under `gh.repo`
  (`Jamie-BitFlight/claude_skills`, set by `setup_gh.py`). Pass `-R <owner/repo>` on every `gh`
  command rather than relying on remote auto-detection — checkout remotes vary (this one currently
  points at `github.com` directly, but proxied setups break auto-detection). `GITHUB_TOKEN` set in
  environment handles authentication automatically.
- Prefer extending this repo's existing GitHub tooling — backlog MCP tools
  (`mcp__plugin_dh_backlog__*`) and PyGithub-based scripts — over adding new `gh` CLI usage; the
  project has invested in portable Python tooling that needs no separate `gh` auth/installation.
- When `gh` is the right tool, prefer `gh graphql` (single call) over `gh api` (slower, often
  multi-step) for new usage — the PR Review Protocol above is an existing exception that already
  depends on `gh api`.
- To read a GitHub-hosted file's contents, use
  `gh api repos/{owner}/{repo}/contents/{path}?ref={branch} --jq '.content' | base64 -d` rather
  than a URL-fetch tool — it authenticates automatically and returns exact file bytes.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
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

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
