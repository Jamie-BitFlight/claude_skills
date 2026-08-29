---
paths:
- hooks/**
- skills/implementation-manager/scripts/task_status_hook.py
---

# Hook Subprocess Invocation

When writing or editing a hook script (anything registered in `hooks/hooks.json`) or any other
high-frequency automated path that needs to call into the SAM/backlog backend:

## Never call `fastmcp call` from here

`fastmcp call` (documented in `AGENTS.md`'s FastMCP CLI section) is correct for manual
verification and CI — a human or a CI job running it once does not care about a stranded
process. It is **not** safe for a hook or any other path that runs frequently and
unattended.

Upstream `fastmcp`'s CLI `call` command builds its `StdioTransport` without
`keep_alive=False`, so it inherits the library default `keep_alive=True`. That causes
`connect_session()` to skip calling `disconnect()` when the call finishes — the only thing
that triggers the MCP SDK's shutdown sequence (close stdin → wait → SIGTERM → SIGKILL on the
process group). Cleanup is then left to asyncio's best-effort task-cancellation at
interpreter exit, which loses the race whenever the server's stdin-reading thread is already
blocked in an uninterruptible OS read — a non-daemon thread, so the process can never exit
once that happens.

This exact defect caused a real orphaned-process incident: `task_status_hook.py` used
`fastmcp call` for its SAM state writes; each PostToolUse invocation made two sequential
MCP round-trips measuring ~5.65s each (~11.3s total), exceeding Claude Code's own 10s
PostToolUse hook timeout — so Claude Code SIGKILLed the hook before its own internal
subprocess timeout could fire, and the hook's cleanup code never ran. Over time this
accumulated 160+ zombie processes.

## Use the plain CLI instead

Call `sam_schema/cli.py` directly (via its PEP 723 sibling `scripts/run_sam_cli.py`, which
resolves to the same cached uv environment as `run_sam_server.py`) instead of going through
the MCP protocol. Both front-ends resolve through the same `get_config().backend` and
delegate to the same `dh_core.operations` functions — the CLI is not a lesser-featured
shortcut, it is the same backend-agnostic write path with a plain-subprocess front end
instead of an MCP-over-stdio one. See `task_status_hook.py`'s `_call_sam_cli()` for the
current pattern (measured ~1.29s per call, comfortably inside any hook timeout budget).

Do not add a generic JSON-passthrough escape hatch to route around a missing CLI option —
if an operation the CLI doesn't support yet is needed, add a typed option to the relevant
`sam_schema/cli.py` subcommand instead.
