# MCP Server Validation

Read [Codex MCP Runtime Guide](./codex-mcp-runtime.md) before configuring or validating a Codex
marketplace MCP. It documents Codex's literal `env` behavior, `env_vars` pass-through, the
two-root `cwd` plus `PWD` pattern, and host prerequisites for FastMCP and project hooks.

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

Use `--command "uv run --script <path>"` — invoking `fastmcp list/call <path>` directly conflicts
with the caller's own asyncio event loop. Suppress banner/log noise with the `FASTMCP_*` env vars
(`FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false`) rather than redirecting stderr to
`/dev/null`, which would also hide real errors. `--json` output is wrapped: unwrap with
`json.loads(json.loads(stdout)["content"][0]["text"])`.

## Bounded execution

`scripts/run_bounded.py` runs a command with a timeout and terminates its full process group
(POSIX process-group signals; `taskkill /T /F` on Windows) on expiry, including descendants a bare
`subprocess.run(timeout=...)` would leave behind. Wrap any external command invocation that may
hang or spawn children with
`uv run --script scripts/run_bounded.py --timeout-seconds <n> -- <command>`.

For MCP runtime tests specifically: load the active FastMCP client skill first; if it is
unavailable, read the bundled FastMCP client guidance. Invoke the client through a `uv`-managed
environment rather than assuming a host-global `fastmcp` binary, and run it from outside the
plugin directory. Never use a native agent MCP tool. Wrap each actual `list` or `call` with
`uv run --script scripts/run_bounded.py --timeout-seconds 5 -- <command>`; it terminates the
process tree on expiry. Retain a redacted result and mark timeouts or startup failures as
failed/blocked.

`development-harness`'s own backlog/SAM MCP servers have their own dedicated run/validation
commands — see `plugins/development-harness/AGENTS.md`, not this file.
