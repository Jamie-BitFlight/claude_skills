# Codex MCP Runtime Guide

## Standard Marketplace MCP Configuration

Codex marketplace plugins load MCP definitions from the file referenced by
`.codex-plugin/plugin.json`. In the standard plugin format, Codex:

- resolves a relative `cwd` against the installed plugin bundle;
- passes `command`, `args`, and literal `env` values unchanged;
- does not expand `$VAR`, `${VAR}`, or plugin-root placeholders in `args` or `env`;
- clears the child environment, then passes a small OS allowlist plus names declared in `env_vars`.

Do not put shell interpolation in an MCP configuration. For example, this
passes the four literal characters `$PWD` to the server:

```json
"env": { "PWD": "$PWD" }
```

Use `env_vars` to forward a variable already present in Codex's environment.

## Plugin And Project Roots

A packaged MCP server can need two different roots:

- `Path.cwd()` for files bundled with the installed plugin;
- the agent project directory for Git-aware state and operations.

Codex does not inject a plugin-root or project-root variable. It does provide a
reliable two-root pattern for local marketplace plugins:

```json
{
  "command": "uv",
  "args": ["run", "--script", "scripts/run_server.py"],
  "cwd": ".",
  "env": { "DH_CODEX_MCP": "1" },
  "env_vars": ["PWD"]
}
```

`cwd: "."` starts the server in the installed plugin bundle. `PWD` is the
Codex agent project working directory when forwarded through `env_vars`.
`DH_CODEX_MCP: "1"` is a launch-mode hint supplied by the dedicated Codex
configuration, not provenance or authentication. Use it only to select the
Codex `PWD` fallback, then validate `PWD` with GitPython before using it; it
can name a directory that is not a Git repository.

Keep explicit project overrides and existing host-specific project hints ahead
of the Codex fallback. Development Harness uses this order: explicit override,
workspace/IDE hints, Codex `PWD`, then process-cwd discovery.

## Runtime Validation

Validate a Codex plugin through a fresh local marketplace and a real Codex MCP
call. Starting a script or reading a `SKILL.md` is not integration evidence.

```bash
CODEX_HOME=/tmp/codex-plugin-test codex plugin marketplace add /path/to/repository
CODEX_HOME=/tmp/codex-plugin-test codex plugin add plugin-name@marketplace-name
CODEX_HOME=/tmp/codex-plugin-test codex exec -C /path/to/project \
  "Use the installed plugin MCP tool named tool_name."
```

Use a fresh `CODEX_HOME` for each check. The positive control must invoke a
named read-only DH MCP tool from a Git project with `CODEX_THREAD_ID` absent;
the marker in the dedicated configuration and forwarded `PWD` must still let
the tool resolve the project. The negative control must use a separate,
disposable package copy whose `.mcp.codex.json` omits `DH_CODEX_MCP`, or launch
against an invalid `PWD`; the same project-dependent tool must fail to resolve
the project. Do not modify the source package for either control.

For direct protocol checks, load the `fastmcp-creator:fastmcp-client-cli` skill
first. On this macOS host the isolated CLI command is:

```bash
uvx --from 'fastmcp-slim[server]' fastmcp list --command 'uv run --script scripts/run_server.py'
```

FastMCP 3.4.5 supplies its CLI through the `server` extra. The unqualified
`fastmcp-slim` package lacks `cyclopts` and cannot run the CLI.

## Host Prerequisites

`uvx`-generated FastMCP launchers call `realpath`. On this macOS host, install
GNU Coreutils and add its normal-name directory to login-shell `PATH`:

```bash
brew install coreutils
export PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
```

The project-wide hook environment can build `cvxopt` through `pm4py`. If hooks
fail with `fatal error: 'umfpack.h' file not found`, install SuiteSparse:

```bash
brew install suite-sparse
```

Then rerun the failed `prek` hooks. Do not call an environment failure
expected: record the exact missing prerequisite and resolve it.
