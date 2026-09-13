"""Regression coverage for ty's PEP 723 script-scoped environment resolution.

ty (through at least 0.0.80) type-checks a `.py` file carrying a PEP 723
`# /// script ... # ///` block as an isolated single-file project and, by default, never
consults `[tool.ty.environment]` (from `pyproject.toml` or `ty.toml`) for it, regardless of
`extra-paths`/`root`/`python` settings declared there. This is upstream, tracked, and open:
https://github.com/astral-sh/ty/issues/691.

Astral shipped an experimental, opt-in fix against that issue on 2026-08-28 (requires
uv >= 0.12.3): ty can shell out to `uv` to synchronise a PEP 723 script's own inline
dependencies, in both the CLI (`TY_UV=scripts`) and the language server (the `useUv`
initialization option). This repo's checked-in configuration for the language-server side is
`.vscode/settings.json`'s `"ty.experimental.useUv"` key -- see
`rules/python-development.md#unresolved-import-on-a-pep-723-script-specifically-in-the-language-server`
for the full narrative and why `.claude/settings.json` needs no edit under this approach.

This suite reads that repo configuration file rather than restating its value, so deleting the
config entry it guards fails `test_repo_configures_ty_experimental_use_uv`, and drifting its value
changes what `test_ty_resolves_pep723_script_imports_under_repo_configured_use_uv` exercises too --
both gates track the one source of truth instead of a second hardcoded copy.

These tests invoke the pinned `ty` sitting beside the interpreter running the suite, directly
(never via `uv run`, which would set `VIRTUAL_ENV` and prepend the project environment to `PATH`
itself, masking exactly the condition under test) so they are portable across machines and CI
without depending on a global `uv tool install`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# Derived from the interpreter actually running the suite, not a hardcoded `.venv`: `uv sync`
# honours `UV_PROJECT_ENVIRONMENT`, so a hardcoded path would silently skip both gates (and leave
# the real environment on `PATH` in `_bare_environment`) whenever the env lives anywhere else.
# Deliberately not `.resolve()`d: a uv-created venv's `bin/python` is a symlink *out of* the venv
# to the managed interpreter, so resolving would point at the toolchain, not at `ty`.
VENV_BIN = Path(sys.executable).parent
TY_BINARY = VENV_BIN / "ty"
PEP723_FIXTURE = Path(__file__).parent / "fixtures" / "pep723_ty_environment_fixture.py"
VSCODE_SETTINGS = REPO_ROOT / ".vscode" / "settings.json"
USE_UV_SETTING_KEY = "ty.experimental.useUv"

pytestmark = pytest.mark.skipif(
    not TY_BINARY.exists(), reason=f"requires `uv sync` to have installed the pinned ty binary next to {sys.executable}"
)


def _bare_environment() -> dict[str, str]:
    """Build a subprocess environment with no ambient venv signal at all.

    Strips `VIRTUAL_ENV`, `UV_PROJECT_ENVIRONMENT`, and the running interpreter's own `bin`
    directory from `PATH` -- the entry the *test runner's own* `uv run pytest` invocation
    prepended. Without this, `subprocess.run` would silently inherit the test runner's `PATH`
    (which already has the project environment first) and every case would resolve correctly
    regardless of what this function's caller sets afterward -- exactly the false-negative this
    helper exists to prevent. This reproduces what a bare language server launch (e.g.
    `uvx ty@latest server`) actually experiences: no project environment on `PATH`. `uv`/`uvx`
    themselves are deliberately left reachable on `PATH`, matching reality -- `TY_UV=scripts`
    needs `uv` on `PATH` to shell out to, and a real editor launch inherits the same shell `PATH`
    that has `uv` on it even when it strips the project venv.

    Returns:
        A fresh copy of the current process environment with every ambient venv signal removed.
    """
    env = dict(os.environ)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    env.pop("VIRTUAL_ENV", None)
    path_entries = env.get("PATH", "").split(os.pathsep)
    env["PATH"] = os.pathsep.join(p for p in path_entries if p and os.path.normpath(p) != str(VENV_BIN))
    return env


def _run_ty_check(*, ty_uv: str | None) -> subprocess.CompletedProcess[str]:
    """Run `ty check` on the PEP 723 fixture under a controlled, otherwise-bare environment.

    Args:
        ty_uv: Value to set for `TY_UV`, or `None` to leave it unset (reproducing the exact
            conditions ty runs under before the experimental PEP 723/uv integration is enabled).

    Returns:
        The completed subprocess. `ty check`'s diagnostics are written to stdout.
    """
    env = _bare_environment()
    if ty_uv is not None:
        env["TY_UV"] = ty_uv
    return subprocess.run(
        [str(TY_BINARY), "check", str(PEP723_FIXTURE)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )


def _read_configured_use_uv() -> str:
    """Read this repo's checked-in `ty.experimental.useUv` value.

    Returns:
        The configured value (e.g. `"scripts"`).

    Raises:
        KeyError: `.vscode/settings.json` no longer sets `ty.experimental.useUv` -- the
            configuration this suite guards has been removed.
        FileNotFoundError: `.vscode/settings.json` itself is gone.
    """
    settings = json.loads(VSCODE_SETTINGS.read_text())
    return settings[USE_UV_SETTING_KEY]


def test_repo_configures_ty_experimental_use_uv() -> None:
    """`.vscode/settings.json` must still opt every VS Code contributor into ty's uv integration.

    This is the actual regression gate for the repo's configuration, independent of ty's runtime
    behaviour below: deleting or renaming the `ty.experimental.useUv` key fails this test even if
    ty itself still behaves correctly, because the config that reaches contributors is what
    disappeared.
    """
    assert _read_configured_use_uv() in {"scripts", "on"}


def test_ty_resolves_pep723_script_imports_under_repo_configured_use_uv() -> None:
    """The repo's configured `useUv` value must be enough for ty to resolve a script's imports.

    Uses `TY_UV` (the CLI form of the same opt-in ty feature `useUv` configures for the language
    server -- per the upstream announcement, both share one implementation) set to the value read
    from `.vscode/settings.json`, under otherwise-bare conditions (no `uv run`, no project
    environment on `PATH`) matching what a language server launch experiences. Coupling the value
    to the config file means a future change to that value (e.g. `"scripts"` -> `"on"`) is
    exercised here too, instead of drifting against a second hardcoded copy.
    """
    result = _run_ty_check(ty_uv=_read_configured_use_uv())

    assert result.returncode == 0, result.stdout
    assert "unresolved-import" not in result.stdout


@pytest.mark.xfail(
    reason=(
        "upstream astral-sh/ty#691: PEP 723 scripts ignore [tool.ty.environment] entirely by "
        "default, and the fix (TY_UV/useUv) is opt-in only. An unexpected pass means ty resolves "
        "PEP 723 script environments without opting in -- i.e. #691 is now closed or the fix is "
        "no longer opt-in. Remove this test and re-evaluate whether TY_UV/useUv (here and in "
        ".vscode/settings.json) are still needed, or can be simplified now that "
        "[tool.ty.environment] is consulted directly."
    ),
    strict=True,
)
def test_ty_pep723_scripts_ignore_project_environment_without_opt_in() -> None:
    """Canary for astral-sh/ty#691 -- XPASSes (failing the suite) once ty ships a non-opt-in fix.

    With no `TY_UV` set and no ambient venv signal, ty falls back to system/default Python
    discovery for any PEP 723 file, regardless of `[tool.ty.environment]` in
    `pyproject.toml`/`ty.toml`. This is the exact condition a language server runs under before
    `useUv` is configured.

    The symptom only materialises when that fallback discovery actually lands on an interpreter
    whose site-packages lack `typer`. On a machine where the stripped `PATH` exposes no usable
    interpreter at all, ty reports `All checks passed!` for reasons unrelated to #691 -- which
    under `strict=True` would XPASS and fail the suite with a bogus "upstream shipped a fix,
    delete the workaround" instruction. Detect that case and skip instead.
    """
    result = _run_ty_check(ty_uv=None)

    if result.returncode == 0 and "unresolved-import" not in result.stdout:
        pytest.skip(
            "stripped PATH exposed no interpreter that reproduces astral-sh/ty#691 on this machine, "
            "so a pass here says nothing about whether ty still has the bug"
        )

    assert result.returncode == 0, result.stdout
