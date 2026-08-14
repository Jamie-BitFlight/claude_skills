"""Shared test helper functions for development-harness test suites.

Centralises helpers used across multiple test files to eliminate copy-paste
duplication. Both ``tests/`` and ``tests_backlog/`` import from here via
``from tests.helpers import ...`` — enabled by the ``pythonpath = ["."]``
pytest configuration in pyproject.toml.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from pathlib import Path

    from fastmcp import FastMCP


async def call_mcp_tool(
    mcp: FastMCP, tool_name: str, params: dict | None = None, *, timeout_seconds: float = 30.0
) -> dict:
    """Call a tool through the in-memory FastMCP transport and parse the result.

    Args:
        mcp: The FastMCP server instance to connect to.
        tool_name: Registered MCP tool name (e.g. ``"backlog_list"``).
        params: Optional parameter dict to pass to the tool.
        timeout_seconds: Seconds to wait for the client handshake and tool call
            before raising ``McpError``. Defaults to 30s, matching
            ``run_cli_subprocess``'s default in this module. Passed as both
            ``timeout`` (per-request read timeout) and ``init_timeout`` --
            these are two separate FastMCP ``Client`` parameters, and
            ``init_timeout`` falls back to ``fastmcp.settings.client_init_timeout``
            (default ``None``, meaning disabled per that setting's own
            docstring) when not given explicitly. Passing ``timeout`` alone
            bounds tool calls but leaves the initialization handshake
            unbounded, so a stalled handshake would still hang this call (and
            the test using it) forever despite the documented bound. Named
            ``timeout_seconds`` rather than ``timeout`` to avoid ruff ASYNC109
            (async function with a bare ``timeout`` parameter) — see that
            rule's docs for the same rename guidance: this helper forwards to
            ``Client``'s own timeout mechanism rather than reimplementing
            timeout/cancellation logic itself, so ``asyncio.timeout()`` is not
            the right tool here.

    Returns:
        Parsed JSON response dict from the tool.

    Why: Ensures MCP tool wrappers behave correctly end-to-end without HTTP.
    Opens a Client connected to the mcp server, calls tool, parses JSON.
    """
    from fastmcp.client import Client

    async with Client(mcp, timeout=timeout_seconds, init_timeout=timeout_seconds) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


def run_cli_subprocess(
    args: list[str], *, timeout: int = 30, env: dict[str, str] | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a CLI subprocess (e.g. ``uv run <script>``) with whole-process-group timeout kill.

    Root cause this works around: ``subprocess.run(timeout=...)`` kills only the
    immediate child on timeout (``Popen.kill()`` signals ``self.pid`` alone — see the
    "Note" on ``Popen.kill()`` in the stdlib docs). When that immediate child is a
    launcher such as ``uv run`` that forks its own child process to actually execute
    the target script, SIGKILL to the launcher terminates it instantly (SIGKILL cannot
    be caught, so the launcher never gets a chance to forward the signal) while its
    grandchild is orphaned and keeps running. The orphan still holds the write end of
    the ``capture_output`` stdout/stderr pipes open, so ``Popen.communicate()``'s read
    loop blocks forever waiting for EOF that will never arrive until the orphan exits
    on its own — this is indistinguishable from a permanent hang under load (e.g. many
    concurrent ``uv run`` invocations under pytest-xdist competing for CPU/interpreter
    startup, which routinely pushes an individual invocation past a 30s timeout).

    Running the child in its own session (``start_new_session=True`` -> a new POSIX
    process group) and killing that whole group on timeout ensures the grandchild is
    also signalled, so the pipes actually close and ``communicate()`` can return.

    Args:
        args: Full argv, e.g. ``["uv", "run", str(cli_path), "plan", "list"]``.
        timeout: Seconds to wait before killing the process group.
        env: Environment for the subprocess; defaults to the current environment.
        cwd: Working directory for the subprocess.

    Returns:
        A ``CompletedProcess`` with captured text stdout/stderr.

    Raises:
        subprocess.TimeoutExpired: If the process group does not exit within timeout.
    """
    # POSIX only: os.killpg/os.getpgid have no Windows equivalent, and CI
    # (ubuntu-latest) is the only enforced target for this helper. On Windows
    # start_new_session is a no-op default (False) and the except branch below
    # falls back to a plain proc.kill().
    proc: subprocess.Popen[str] = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=cwd,
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            with contextlib.suppress(ProcessLookupError):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
        stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(args, timeout, output=stdout, stderr=stderr) from None
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def make_dh_paths_mock(project_root: Path, user_dh_root: Path | None = None) -> MagicMock:
    """Return a MagicMock that satisfies dh_paths usage in backend and config tests.

    Args:
        project_root: The fake project root path to return from git_project_root().
        user_dh_root: Optional fixed user DH root path. When omitted, _dh_user_root()
            uses a side_effect that resolves Path.home() at call time, so tests can
            monkeypatch HOME before calling the mock.

    Returns:
        A MagicMock with git_project_root, _dh_user_root, and project_dh_dir configured.

    Why: Isolates dh_paths filesystem lookups so tests don't depend on real
    project structure or home directory layout. The deferred Path.home() resolution
    (when user_dh_root is None) lets monkeypatching HOME take effect correctly.
    """
    from pathlib import Path as _Path

    mock = MagicMock()
    mock.git_project_root.return_value = project_root
    if user_dh_root is not None:
        mock._dh_user_root.return_value = user_dh_root
    else:
        mock._dh_user_root.side_effect = lambda: _Path.home() / ".dh"
    mock.project_dh_dir.return_value = project_root / ".dh"
    return mock
