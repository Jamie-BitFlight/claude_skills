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

Validate through a fresh local marketplace and an interactive Codex MCP call.
Starting a script, reading a `SKILL.md`, or a passing `codex exec` command is
not integration evidence. Do not report an interactive call as passed until
its rendered tool result and the server artifact below are both retained.

Use one disposable directory for `CODEX_HOME`, the local marketplace copy,
fixture artifacts, and a fresh tmux server. Start that server under `env -i`
so it cannot inherit the orchestrating session. Give it an explicit complete
`PATH`: include the directories containing `codex`, `uv`, `npx`, and every
other command the selected MCP entries launch, plus the required system paths.
For example:

```bash
TEST_ROOT=$(mktemp -d)
TEST_PATH="$(dirname "$(command -v codex)"):$(dirname "$(command -v uv)"):$(dirname "$(command -v npx)"):/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
TMUX_SOCKET="codex-mcp-$RANDOM"

env -i HOME="$TEST_ROOT/home" PATH="$TEST_PATH" TERM=xterm-256color TMPDIR="$TEST_ROOT/tmp" \
  tmux -L "$TMUX_SOCKET" -f /dev/null start-server
tmux -L "$TMUX_SOCKET" set-option -g default-shell /bin/sh
tmux -L "$TMUX_SOCKET" set-option -g update-environment ''
tmux -L "$TMUX_SOCKET" new-session -d -s codex-mcp /bin/sh
```

Copy the marketplace and plugin under test into `TEST_ROOT`, set
`CODEX_HOME="$TEST_ROOT/home"`, and add/install that marketplace from the
interactive shell. Do not reuse an installed plugin or an existing
`CODEX_HOME`.

Before testing DH, install a disposable fixture plugin whose named MCP tool
writes its child `cwd` and forwarded `PWD` to `TEST_ROOT/fixture-mcp.json`,
then returns the same values. Invoke that named tool in the interactive Codex
session and capture the rendered result. The rendered result must match
`fixture-mcp.json`; this is the canary that proves plugin-cache `cwd` and
agent-project `PWD` reached the MCP process before DH results are interpreted.

Run the DH controls as separate fresh interactive sessions, each forwarding a
repository `PWD` and with `CODEX_THREAD_ID` absent:

1. Positive: install the unmodified disposable package, whose dedicated MCP
   configuration contains `DH_CODEX_MCP: "1"`. Invoke a named read-only tool
   such as `backlog_list`; retain its rendered result and server logs.
2. Negative: install a second disposable package copy after removing only
   `DH_CODEX_MCP` from its dedicated MCP entries. The same project-dependent
   tool must fail project-root resolution; retain the rendered error and logs.

These controls exercise the marker contract. They do not prove that an
arbitrary resumed Codex thread has the same launch state. Treat a new
interactive session as the controlled integration check. If a resumed session
has a handshake error, preserve its stderr/log evidence and compare it with a
new session launched from the same repository before changing DH source.

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
