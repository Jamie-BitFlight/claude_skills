"""Lazy subprocess wrapper for the bd (beads) CLI.

All subprocess I/O is channelled through :class:`BdRunner`.  The class is
**lazily-validating**: the constructor does NOT touch the filesystem or spawn
any process.  The ``bd`` binary is resolved (via :func:`shutil.which`) on the
first call to :meth:`BdRunner.run_json` or :meth:`BdRunner.run_text`.

Exception hierarchy (all inherit from :exc:`~backlog_core.models.BackendUnavailableError`):

- :exc:`BdNotInstalledError` — ``bd`` not found on ``PATH``
- :exc:`BdInvocationError` — ``bd`` returned non-zero exit code, timed out,
  or failed to launch
- :exc:`BdJsonDecodeError` — ``bd`` stdout was not valid JSON

Each exception carries :pep:`678` notes with ``argv``, ``returncode``,
``stderr``, and ``elapsed_ms`` for diagnostics.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from typing import TYPE_CHECKING, Final, TypeAlias, Union

from backlog_core.models import BackendUnavailableError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

#: Recursive JSON value type — the full set of values ``json.loads`` can return.
JsonValue: TypeAlias = Union[str, int, float, bool, "list[JsonValue]", "dict[str, JsonValue]", None]

__all__ = [
    "_DEFAULT_BD_TIMEOUT_SECONDS",
    "BdInvocationError",
    "BdJsonDecodeError",
    "BdNotInstalledError",
    "BdRunner",
    "JsonValue",
]

_DEFAULT_BD_TIMEOUT_SECONDS: Final[int] = 30

_log = logging.getLogger(__name__)

#: Environment variable names that MUST NOT be forwarded to bd subprocesses.
#: ``GITHUB_TOKEN`` is excluded to prevent bd from accidentally using GitHub
#: credentials, which would bypass the explicit backend selection and produce
#: confusing cross-backend side effects.
_BLOCKED_ENV_VARS: frozenset[str] = frozenset({"GITHUB_TOKEN"})


def _bd_env() -> dict[str, str]:
    """Return a copy of the current environment with blocked variables removed.

    Returns:
    --------
    dict[str, str]
        Filtered environment safe to pass to ``bd`` subprocesses.
    """
    return {k: v for k, v in os.environ.items() if k not in _BLOCKED_ENV_VARS}


# ---------------------------------------------------------------------------
# Exception types
# ---------------------------------------------------------------------------


class BdNotInstalledError(BackendUnavailableError):
    """``bd`` binary is not on ``PATH``.

    Callers catching this exception should surface installation guidance
    (e.g. ``https://beads.sh/docs/install``) rather than a generic error.
    """


class BdInvocationError(BackendUnavailableError):
    """``bd`` returned a non-zero exit code, timed out, or failed to start.

    Attributes:
        argv: Full argv list passed to ``bd``, including the resolved binary
            path as the first element.
        returncode: Exit code from the process.  ``-1`` indicates a timeout.
        stdout: Captured standard output (may be empty).
        stderr: Captured standard error (may be empty).

    PEP 678 notes are also attached with the same fields for tool-chain
    compatibility.
    """

    def __init__(self, message: str, argv: list[str], returncode: int, stdout: str, stderr: str) -> None:
        """Initialise with structured invocation details.

        Args:
            message: Human-readable summary.
            argv: Full argv (binary + subcommands + flags).
            returncode: ``bd`` exit code (``-1`` for timeout).
            stdout: Captured stdout text.
            stderr: Captured stderr text.
        """
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message)


class BdJsonDecodeError(BackendUnavailableError):
    """``bd`` stdout could not be parsed as JSON.

    Attributes:
        raw_output: Raw stdout text that failed JSON parsing.  Useful for
            diagnosing spurious banner text prepended to JSON by some
            ``bd`` versions.

    PEP 678 notes are also attached for tool-chain compatibility.
    """

    def __init__(self, message: str, raw_output: str) -> None:
        """Initialise with the unparseable raw output.

        Args:
            message: Human-readable summary.
            raw_output: The stdout string that failed ``json.loads``.
        """
        self.raw_output = raw_output
        super().__init__(message)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class BdRunner:
    """Lazy subprocess wrapper for the ``bd`` CLI.

    Parameters
    ----------
    timeout_seconds:
        Maximum number of seconds to wait for any single ``bd`` invocation.
        Defaults to :data:`_DEFAULT_BD_TIMEOUT_SECONDS`.
    env_overrides:
        Optional mapping of environment variable names to values that are
        merged into every ``bd`` subprocess environment.  Keys in this
        mapping take precedence over the inherited process environment.
        Variables listed in :data:`_BLOCKED_ENV_VARS` are removed first,
        then overrides are applied.  Pass ``None`` (default) to use the
        inherited environment with blocked variables removed.
        Keyword-only parameter.

    Notes:
    -----
    The constructor is **filesystem-free**.  No :func:`shutil.which` call,
    no :func:`subprocess.run` call, no ``os`` call happens at construction
    time.  This ensures that importing and instantiating :class:`BdRunner`
    inside the MCP server does not add latency at startup.
    """

    def __init__(
        self, timeout_seconds: int = _DEFAULT_BD_TIMEOUT_SECONDS, *, env_overrides: Mapping[str, str] | None = None
    ) -> None:
        """Store configuration only.  Does not touch the filesystem."""
        self._timeout_seconds = timeout_seconds
        if env_overrides:
            blocked = [k for k in env_overrides if k in _BLOCKED_ENV_VARS]
            if blocked:
                for key in blocked:
                    _log.warning("env_overrides key %r is blocked and will be ignored", key)
            self._env_overrides: dict[str, str] = {k: v for k, v in env_overrides.items() if k not in _BLOCKED_ENV_VARS}
        else:
            self._env_overrides: dict[str, str] = {}
        self._bd_path: str | None = None
        self._available: bool | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_json(self, argv: Sequence[str]) -> JsonValue:
        """Run ``bd`` with *argv*, inject ``--json`` if absent, parse output.

        Parameters
        ----------
        argv:
            Arguments passed to ``bd``.  ``--json`` is appended
            idempotently (only if not already present).

        Returns:
        -------
        JsonValue
            Parsed JSON value from ``bd`` stdout.

        Raises:
        ------
        BdNotInstalledError
            When ``bd`` is not on ``PATH``.
        BdInvocationError
            When ``bd`` exits non-zero, times out, or fails to launch.
        BdJsonDecodeError
            When ``bd`` stdout is not valid JSON.
        """
        bd = self._resolve_bd_path()
        argv_list = list(argv)
        if "--json" not in argv_list:
            argv_list.append("--json")
        raw = self._run(bd, argv_list)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            err = BdJsonDecodeError(f"bd stdout was not valid JSON for argv {argv_list!r}", raw_output=raw)
            err.add_note(f"argv: {argv_list!r}")
            err.add_note(f"stdout_preview: {raw[:200]!r}")
            raise err from exc

    def run_text(self, argv: Sequence[str]) -> str:
        """Run ``bd`` with *argv* and return raw stdout.

        Parameters
        ----------
        argv:
            Arguments passed to ``bd``.  No ``--json`` is injected.

        Returns:
        -------
        str
            Raw stdout from ``bd``.

        Raises:
        ------
        BdNotInstalledError
            When ``bd`` is not on ``PATH``.
        BdInvocationError
            When ``bd`` exits non-zero, times out, or fails to launch.
        """
        bd = self._resolve_bd_path()
        return self._run(bd, list(argv))

    def is_available(self) -> bool:
        """Return ``True`` if ``bd`` is on ``PATH`` and responds to ``version``.

        The result is cached after the first call.  This method **never raises**
        regardless of subprocess state; failures are converted to ``False``.
        """
        if self._available is not None:
            return self._available
        if not (path := shutil.which("bd")):
            self._available = False
            return False
        try:
            subprocess.run(
                [path, "version", "--json"],
                shell=False,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=self._effective_env(),
            )
            self._available = True
        except (OSError, subprocess.SubprocessError):
            self._available = False
        return self._available

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _effective_env(self) -> dict[str, str]:
        """Return the filtered base environment merged with instance-level overrides.

        Returns:
        -------
        dict[str, str]
            Environment mapping safe to pass to ``bd`` subprocesses.
        """
        env = _bd_env()
        if self._env_overrides:
            env.update(self._env_overrides)
        return env

    def _resolve_bd_path(self) -> str:
        """Lazily locate ``bd`` on ``PATH`` and cache the result.

        Returns:
        --------
        str
            Absolute path to the ``bd`` binary.

        Raises:
        ------
        BdNotInstalledError
            When ``bd`` is not found via :func:`shutil.which`.
        """
        if self._bd_path is not None:
            return self._bd_path
        if not (path := shutil.which("bd")):
            msg = "bd is not installed or not on PATH. Install beads: https://beads.sh/docs/install"
            raise BdNotInstalledError(msg)
        self._bd_path = path
        return path

    def _run(self, bd: str, argv: list[str]) -> str:
        """Execute ``bd`` as a subprocess and return stdout.

        Parameters
        ----------
        bd:
            Absolute path to the ``bd`` binary (already resolved by
            :meth:`_resolve_bd_path`).
        argv:
            Arguments to pass after the binary path.

        Returns:
        -------
        str
            Raw stdout text from the completed process.

        Raises:
        ------
        BdInvocationError
            When ``bd`` exits non-zero, times out, or fails to start.
        """
        full_cmd = [bd, *argv]
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                full_cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=self._effective_env(),
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            # exc.stdout / exc.stderr may be bytes or None; coerce defensively.
            stdout_text: str = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr_text: str = exc.stderr if isinstance(exc.stderr, str) else ""
            err = BdInvocationError(
                f"bd timed out after {self._timeout_seconds}s: {argv!r}",
                argv=full_cmd,
                returncode=-1,
                stdout=stdout_text,
                stderr=stderr_text,
            )
            err.add_note(f"argv: {full_cmd!r}")
            err.add_note("timed out")
            err.add_note(f"elapsed_ms: {elapsed_ms}")
            raise err from exc
        except (OSError, subprocess.SubprocessError) as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            start_err = BdInvocationError(
                f"bd failed to start: {exc!r}", argv=full_cmd, returncode=-1, stdout="", stderr=""
            )
            start_err.add_note(f"argv: {full_cmd!r}")
            start_err.add_note(f"elapsed_ms: {elapsed_ms}")
            raise start_err from exc

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        stdout_bytes = len(proc.stdout.encode("utf-8", errors="replace"))
        stderr_bytes = len(proc.stderr.encode("utf-8", errors="replace"))
        _log.debug(
            "bd argv=%r rc=%d stdout_bytes=%d stderr_bytes=%d elapsed_ms=%d",
            full_cmd,
            proc.returncode,
            stdout_bytes,
            stderr_bytes,
            elapsed_ms,
        )

        if proc.returncode != 0:
            err = BdInvocationError(
                f"bd exited {proc.returncode} for argv {argv!r}",
                argv=full_cmd,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
            err.add_note(f"argv: {full_cmd!r}")
            err.add_note(f"returncode: {proc.returncode}")
            err.add_note(f"stderr_preview: {proc.stderr[:500]!r}")
            err.add_note(f"elapsed_ms: {elapsed_ms}")
            raise err

        return proc.stdout
