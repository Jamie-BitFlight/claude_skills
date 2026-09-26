# Plugin project architecture

A plugin directory is a product boundary. Repository policy may be centralized; plugin functionality may not be.

## Isolation contract

A plugin SHOULD remain executable, testable, validateable, and understandable when its directory is copied into an otherwise empty repository.

A plugin MUST NOT require a plugin-local `pyproject.toml` or `uv.lock`. In this monorepo, lint, format, type-check, and shared development-tool policy stays at the repository root. A plugin-local Python project file is allowed only when the plugin intentionally becomes a separately packaged Python distribution.

A plugin owns everything specific to its behavior:

- host manifests and configuration;
- skills, agents, commands, hooks, and MCP entry points;
- implementation modules used by those entry points;
- tests and fixtures for plugin behavior;
- a PEP 723 `run_pytests.py` when it owns pytest tests;
- runtime and test dependencies declared at executable consumption boundaries;
- plugin-facing documentation.

The repository owns orchestration and policy:

- lint, format, type-check, and shared tool configuration;
- CI change-impact selection and aggregate quality gates;
- marketplace-wide consistency;
- repository-maintenance and cross-plugin tests.

## Dependency direction

Plugin runtime or test code MUST NOT depend implicitly on:

- the repository root being the current working directory;
- repository-root `PYTHONPATH` entries;
- root helper scripts that are not bundled with the plugin;
- implementation files in sibling plugins;
- source-tree-only aliases such as `.claude/skills`.

Use paths relative to the plugin entry point, bundle the required implementation, use an external declared dependency, or define an explicit plugin dependency when one genuinely exists.

Repository tooling MAY inspect a plugin through stable boundary artifacts such as its manifests and `run_pytests.py`; it SHOULD NOT encode the plugin's internal test directories or Python import roots.

## Recommended layout

```text
plugins/<name>/
├── .claude-plugin/
├── .codex-plugin/          # when supported
├── .cursor-plugin/         # when supported
├── README.md
├── AGENTS.md               # only when local development rules are needed
├── skills/
├── agents/
├── commands/
├── hooks/
├── scripts/                # plugin-owned executable/support code
├── tests/                  # plugin-owned tests/fixtures
└── run_pytests.py          # when the plugin owns pytest tests
```

Do not create empty directories to satisfy this example. Existing module-local or skill-local test directories may remain; `run_pytests.py` is their authority.

## Standalone extraction

Isolation and repository policy are deliberately separate. Copying a plugin proves the product boundary; it does not copy this monorepo's development policy.

When moving a plugin to its own repository:

1. Copy the plugin directory as the new repository root.
2. Replicate the canonical root development policy: Python/tool versions, lint/format/type-check configuration, shared markers, and CI quality gates that apply to the plugin.
3. Create the standalone repository lockfile and CI configuration there.
4. Keep PEP 723 executable dependency blocks authoritative; do not replace them with an accidental second runtime dependency source.
5. Run plugin validation, the plugin's `run_pytests.py`, and the replicated quality checks before removing the monorepo copy.

An extraction tool may automate step 2 later. The monorepo must not pre-emptively put standalone-repository scaffolding inside every plugin.
