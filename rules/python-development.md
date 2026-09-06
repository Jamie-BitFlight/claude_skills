## Plugin Python — PEP 723 Scripts, No uv Workspace

**This repo has NO uv workspace.** Do not add `[tool.uv.workspace]` entries; plugin sub-projects are not workspace members. Plugin MCP servers are PEP 723 self-resolving scripts, not installed projects.

- **Runtime source of truth** is the script's inline `# /// script … dependencies = [...] # ///` block — `uv` resolves it at launch, with no `pyproject.toml`, `uv.lock`, or workspace lookup. See the PEP 723 shebang and block in [`run_backlog_server.py`](plugins/development-harness/scripts/run_backlog_server.py), launched via the `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/…` command in [`plugin.json`](plugins/development-harness/.claude-plugin/plugin.json). `${CLAUDE_PLUGIN_ROOT}` resolves in the installed plugin cache, not the source tree.
- **Plugins ship zipped, outside this repo** — no source-tree `uv.lock` is consulted at runtime.
- **Root dev-dependencies mirror the script blocks**, solely so `ty`, `ruff`, and the IDE/LSP (which don't read PEP 723) can resolve imports while editing here — tooling convenience, not the runtime or distribution path. See `[dependency-groups] dev` in [`pyproject.toml`](pyproject.toml).

### Adding a new plugin MCP server

1. Declare dependencies in the script's PEP 723 frontmatter (runtime source of truth).
2. Mirror them into the root `[dependency-groups] dev` so `ty`, `ruff`, and the IDE resolve them.

Do not create a per-plugin `pyproject.toml` sub-project or a per-plugin `uv.lock`.

This extends to every directory a script imports (`backlog_core/`, `dh_core/`, `sam_schema/`,
etc.): they have `__init__.py` and dotted imports for internal organization, but are not
distributable packages — never build, bundle, publish, or add a `pyproject.toml` beside them.
Doing so creates two dependency sources of truth (the script's own inline deps vs. a new
package's) that silently diverge — a split-brain, not a cleanup.

### Splitting a PEP 723 script

A PEP 723 script may import its own modules; the inline block governs its PyPI dependencies, not
its file count. Split a script that passes ~500 lines, per the File Size Policy in
[`python-cli-architect.md`](plugins/python-engineering/agents/python-cli-architect.md). Verified
2026-09-06 by running a two-file PEP 723 script from an unrelated working directory, and by
`sam_schema/cli.py`, which has shipped this way.

Imports resolve two ways:

- **A sibling module in the script's own directory** imports by name with no setup. `uv run` puts
  the script's directory first on `sys.path` whatever the working directory.
- **A script inside a package, importing that package by name**, needs the package's parent on the
  path first:

  ```python
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
  ```

  `sam_schema/cli.py` does exactly this before `from sam_schema import artifacts, backlog, …`.

Only the entry script carries the shebang and the `# /// script` block; the modules it imports are
plain `.py` files.

`ty` will not resolve those imports yet: it treats a file with inline metadata as a standalone
script, so `pyproject.toml` does not apply to it. Set `root` inside the script's own block, not
`extra-paths` — `root` replaces ty's root detection rather than adding to it, so include `"."` or
the script's declared dependencies stop resolving too. `tests_sam/scripted_runner.py` carries
`root = [".", ".."]`. Load `python-engineering:ty` before changing this; it holds the full rule.

### Invariant

```bash
git ls-files | grep uv.lock
```

Must return only the root `uv.lock`. A per-plugin `uv.lock` is never read — the runtime self-resolves via PEP 723 and the linters use the root dev group — so it would only drift from the real dependency set.

---

## ty Type Checker Errors

Fix the code to satisfy the type checker — inline `# ty: ignore` suppressions are prohibited.
Config-level relaxation via `[[tool.ty.overrides]]` in `pyproject.toml` is allowed, but only for a
case matching one of the acceptable-exception categories in
[`linting-exceptions.md`](rules/linting-exceptions.md) — cite the matching category by name in a
comment beside the override (the SOLID-corpus override in `pyproject.toml` shows the pattern).
Load `python-engineering:ty` for suppression syntax, diagnostics, and unresolved-import/environment
resolution. Load `python-engineering:python3-typing` for the boundary-validation pattern
(`model_validate()` on raw input) instead of passing untyped values to typed constructors.

### `unresolved-import` errors

A PEP 723 script importing its own modules is the exception, and is fixed by `root` inside the
script's block — see "Splitting a PEP 723 script" above, and `python-engineering:ty`. Everywhere
else: when `ty` reports `unresolved-import` for a module that genuinely exists on disk, the
module's directory is almost always missing from `[tool.ty.environment] extra-paths` in
`pyproject.toml`.
Add the directory there, then re-verify with `uv run ty check <path>` before investigating the
importing code itself. A root-level `ty.toml`, if one exists, takes precedence over
`pyproject.toml`'s `[tool.ty]` table — check for one first if an `extra-paths` addition doesn't
resolve the error. For the related `unresolved-attribute` failure on a `ModuleType` (a different
symptom, same environment-resolution root cause), see [AGENTS.md's "Common ty Failure
Patterns"](AGENTS.md#common-ty-failure-patterns).

### `unresolved-import` on a PEP 723 script, specifically in the language server

If the file is a PEP 723 script (has a `# /// script … # ///` block, per the pattern above) and
the false `unresolved-import` shows up in **live editor/LSP diagnostics** but `uv run ty check
<path>` passes clean on the same file, this is **not** an `extra-paths` problem — do not add
entries for it. Confirmed root cause (evidence trail and minimal 7-line reproduction in the PR that
added this note): ty (through at least 0.0.80) type-checks a `# /// script` file as an isolated
single-file project and, by default, never consults `[tool.ty.environment]` (from either
`pyproject.toml` or `ty.toml`) for it — `extra-paths`, `root`, and every other environment key are
silently ignored for that file, regardless of where they're declared. Tracked upstream, open as of
this writing: <https://github.com/astral-sh/ty/issues/691>.

**The fix is Astral's own experimental PEP 723/uv integration, not an environment-variable
workaround.** Announced by MichaReiser against #691 on 2026-08-28 (requires uv ≥0.12.3): ty can
shell out to `uv` to synchronise a script's own inline `dependencies = [...]` list, in both the CLI
and the language server. It is opt-in on both sides, and both sides are driven by the same knob —
directly confirmed here by a minimal LSP JSON-RPC probe (`initialize` → `textDocument/didOpen` →
`textDocument/publishDiagnostics`) against `uvx ty@latest server` (this repo's Astral plugin's exact
launch command): setting the plain `TY_UV` **environment variable** on that server process clears
the diagnostic, with no `initializationOptions` message required at all.

- **CLI**: set `TY_UV=scripts` in the environment `ty check` runs in.
- **Language server, generic protocol form**: set the experimental `useUv` initialization option to
  `"scripts"` — `initialization_options.experimental.useUv` in the `initialize` request. This is
  what Astral's announcement documents and what an editor extension typically exposes as a setting.
- **`"scripts"` is the only value verified to work.** ty ignores an unrecognised value silently —
  no warning, no non-zero exit — so a wrong value looks configured while the fix is off. Measured
  on both ty 0.0.75 (pinned) and 0.0.80 (`uvx ty@latest`) against
  `tests/fixtures/pep723_ty_environment_fixture.py`: `TY_UV=scripts` → `All checks passed!`;
  `TY_UV=on` and any other value → `error[unresolved-import]: Cannot resolve imported module
  typer`, stderr empty. Re-verify behaviourally before documenting any other value.
- **Language server, environment-variable form**: since `ty server` reads `TY_UV` the same way
  `ty check` does (verified above), any client that can set the server process's environment can
  use the exact same env var as the CLI, with no protocol-level configuration at all.

This repo has **two distinct language-server consumers**, with different coverage:

1. **VS Code's `astral-sh.ty` extension** (already recommended in
   [`.vscode/extensions.json`](.vscode/extensions.json)): covered by
   `"ty.experimental.useUv": "scripts"` checked into
   [`.vscode/settings.json`](.vscode/settings.json) — no further setup needed for VS Code
   contributors. Any other editor's LSP client without a repo-committed config file (Zed, Neovim,
   Emacs, etc.) configures the same `initialization_options.experimental.useUv` knob directly in
   its own editor config.
2. **Claude Code's own bundled Astral-plugin language server** — the process that actually produces
   the live `unresolved-import` diagnostics inside a Claude Code session, launched as
   `command: uvx, args: ["ty@latest", "server"]` by that plugin's own `plugin.json`. This repo does
   not vendor that file: the `astral` plugin is pulled live from `astral-sh/claude-code-plugins` at
   a pinned SHA (`git-subdir` source in `.claude-plugin/marketplace.json`), so there is nothing in
   this repo to edit to add `env`/`initializationOptions` to its `lspServers.ty` entry directly.
   **This is a still-open gap, not fixed by this repo's `.vscode/settings.json` change.** The
   reachable lever is `.claude/settings.json`'s top-level `env` block: confirmed by inspecting the
   live `ty server` process's own environment (`ps -E <pid>`), which already carries that file's two
   existing `env` entries (`CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`,
   `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) — proving that file's `env` values do reach this exact
   spawned process. Adding `"TY_UV": "scripts"` there would close this gap, but no agent may write
   it: that file is denied to agents as security-sensitive (this is the same permission wall that
   caused PR #3533's `VIRTUAL_ENV` attempt to land undocumented-as-unapplied). A human with write
   access to `.claude/settings.json` needs to add that one key.

This repo's own `uv run ty check` (prek, CI, and any contributor running it from the CLI) already
resolves PEP 723 scripts correctly **without** `TY_UV`, because `uv run` sets `VIRTUAL_ENV` to the
project's own `.venv`, and every PEP 723 script's dependencies are mirrored into the root
`[dependency-groups] dev` group (see above) — so the project venv already satisfies the import.
`TY_UV=scripts` is not wired into prek or CI here because that path isn't broken; it remains
available as a CLI escape hatch for a script whose dependency was never mirrored.

**Why this is still better than the rejected `VIRTUAL_ENV` mitigation, even where it also needs
`.claude/settings.json`**: `TY_UV=scripts` needs only `uv`/`uvx` reachable on `PATH` — true by
construction for a process `uvx` itself just launched — with no dependency on a relative `.venv`
existing at the process's working directory, and it does not take ty down entirely when that
condition isn't met (`VIRTUAL_ENV` did, with `Failed to discover local Python environment`). It is
also the exact env var ty's own CLI and LSP already read, not a Claude-Code-specific `env` hack
being repurposed for an unrelated variable.

**Do not use `[tool.ty.environment]` inside a PEP 723 script's own inline metadata block either.**
It appears to resolve the same symptom, but it is accidental, not supported: uv's PR
[#26671](https://github.com/astral-sh/uv/pull/26671) (merged 2026-07-21) added `[tool.ty.rules]`
and `[tool.ty.analysis]` to the set of `[tool.ty]` keys read from PEP 723 metadata, and its author
stated `environment` settings were deliberately excluded because different environments require
different databases. Relying on it ships an unsupported configuration surface that could be
removed without notice.

See [`docs/linting-and-type-checking.md`](docs/linting-and-type-checking.md) for the
trustworthy-channel guidance and
[`tests/test_ty_pep723_environment.py`](tests/test_ty_pep723_environment.py) for the CLI-level
regression coverage (the LSP-protocol-level verification above was done manually, not encoded as an
automated test — it exercises the same underlying ty resolution engine as `ty check`, only over a
different transport, and encoding it would add a network dependency on `uvx ty@latest` and JSON-RPC
framing for no additional engine coverage) — including a canary for #691 fully closing.

#691 remains **open**, and the shipped support is explicitly labeled experimental/preview by its
author ("Expect rough edges, missing documentation, and breaking changes") — treat `TY_UV`/`useUv`
as the current best mitigation, not a closed issue. Two related upstream rough edges, not yet fixed
as of this writing, are why the environment-pointing approaches (this one included) remain a
mitigation rather than a full fix:

- [astral-sh/ty#4083](https://github.com/astral-sh/ty/issues/4083) — project `[tool.ty]` settings
  are ignored in PEP 723 scripts.
- [astral-sh/ty#4324](https://github.com/astral-sh/ty/issues/4324) — `[environment] root` from an
  auto-discovered `ty.toml` is ignored for scripts; an explicit `--config-file` is required.
