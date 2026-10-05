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

## Nested Codex CLI Runtime

Use this setup when a Codex session must run another Codex CLI session and
retain execution evidence. It prepares an isolated runtime; it does not
establish an actual endpoint or a gold result.

1. Freeze the source before setup. Record the source Git hash, archive or copy
   that exact source, and use it for every later check. Keep the disposable
   project, state, private Codex home, and artifacts beneath one runtime root.
2. Create a private `CODEX_HOME`. Copy only the existing selected provider
   configuration and its existing model catalog into it. Retain only the
   provider authentication mechanism and environment variable names required
   by that configuration. Never copy global plugins, global MCP entries,
   credentials, or provider URLs into logs or documentation.
3. For a DH backlog execution experiment, use a genuine disposable SQLite
   backend. For another target, use that target's real isolated backend. Set
   the project and state roots explicitly, then retain the backend identity and
   state snapshot. Launch Codex through a filtered environment containing only
   the provider variables and runtime variables the run requires.
4. Set `UV_CACHE_DIR` to a writable, disposable directory under the project.
   Warm harness prerequisites through the same isolated runtime before
   recording a baseline. If the evaluated target installs a dependency, retain
   that installation in the actor trace; it is part of the evaluated process.

### Marketplace And Native MCP

Give `codex plugin marketplace add` a marketplace **directory**, not a
manifest file. After installing the plugin, derive the installed plugin root
from retained private-cache evidence.

Plugin delivery alone does not establish that Codex registered its MCP tools.
When the package does not expose the needed native server, register the frozen
source-backed entry explicitly in the private `CODEX_HOME`. Substitute the
installed plugin directory into `cwd`; do not leave a shell variable literal
in the configuration. Register only the server needed for the run and forward
only its required environment variables, including the disposable project and
SQLite state roots.

When a registered native MCP server runs `uv`, forward the project-local
`UV_CACHE_DIR` through its `env_vars` as well as the shell actor subprocess
environment. Verify that both processes receive a writable disposable cache;
record the variable name in the environment-name manifest, not its contents.
Preserve the frozen source command and arguments, and do not forward
credentials to the MCP server.

Before proceeding, retain JSONL evidence of a native MCP call and its rendered
result, and confirm that result agrees with the isolated SQLite state. This is
an MCP availability check, not a complete packaging-validation claim.

Use the callable native MCP surface verified by the preflight, and record the
tool-to-server mapping. A successful preflight can call
`tools.mcp__backlog__backlog_list(...)` inside `functions.exec`; do not infer an
absent binding from final prose or a single `TypeError`. This proves the
preflight call only. It does not validate an actual endpoint.

### Launch, Resume, And Evidence

Run each Codex invocation through `scripts/run_bounded.py`. Retain its JSONL,
stderr, final message, resolved command, environment-name manifest, and a hash
of the complete private rollout. Public JSONL can omit wrapped `functions.exec`
events, so preserve the complete rollout separately and treat it as the source
for execution evidence.

When restoring workspace configuration for a cloned baseline, relocate MCP
`cwd` values and the private model-catalog path to that clone before launch.

For a resumed turn, use `codex exec resume --json` with the recorded thread in
the same private `CODEX_HOME`, project working directory, filtered environment,
and bounded launcher. Do not add initial-launch-only `--sandbox` or `--cd`
options to the resume command. Append its JSONL, stderr, prompt-input hash, and
state snapshot to the retained ordered rollout timeline.

Bind a native skill to its exact installed path and record its hash. A skill
name or an unpinned cache location is insufficient for source conformance.

### Baseline And Conformance

Create the baseline only after the preflight has produced the required native
MCP result and isolated-state evidence. Clone that baseline before an actual
run, and use the clone's project path in the actual command as well as its
environment. Retain the baseline manifest and hashes with the launch record.

After the actor stops, check the captured endpoint against the frozen source
and record the result separately. Only then may a marking sheet be frozen.
Do not start a blind hypothetical run from an unfrozen or unreviewed baseline.
An actual run remains unadjudicated until this source-conformance check is
captured; it is not a completed or gold result.

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
