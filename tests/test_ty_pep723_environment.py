"""Regression coverage for ty's PEP 723 script-scoped environment resolution.

ty (0.0.75 through at least 0.0.80) type-checks a `.py` file carrying a PEP 723
`# /// script ... # ///` block as an isolated single-file project and never consults
`[tool.ty.environment]` (from `pyproject.toml` or `ty.toml`) for it, regardless of
`extra-paths`/`root`/`python` settings declared there. This is upstream, tracked, and open:
https://github.com/astral-sh/ty/issues/691.

`uv run ty check` is unaffected because `uv run` sets `VIRTUAL_ENV` (and prepends the project's
`.venv/bin` to `PATH`), and ty's PEP-723-scoped resolution does fall back to `VIRTUAL_ENV` -- or,
failing that, a `python`/`python3` found on `PATH` -- before giving up. The Astral plugin's bundled
language server (`uvx ty@latest server`) has neither: `uvx` runs in its own ephemeral environment
with no ambient `uv run` and no project `.venv/bin` on `PATH`. This repo's prescribed mitigation is
`.claude/settings.json`'s `env.VIRTUAL_ENV = ".venv"` -- prescribed, not asserted here: these tests
gate ty's behaviour under that value, not the presence of the `env` entry itself. See
`rules/python-development.md#unresolved-import-on-a-pep-723-script-specifically-in-the-language-server`
for the full narrative.

These tests invoke the pinned `ty` sitting beside the interpreter running the suite, directly
(never via `uv run`, which would set `VIRTUAL_ENV` and prepend the project environment to `PATH`
itself, masking exactly the condition under test) so they are portable across machines and CI
without depending on a global `uv tool install`.
"""

from __future__ import annotations

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
    helper exists to prevent. This reproduces what the language server's `uvx ty@latest server`
    actually experiences: `uvx` never adds a project environment to `PATH`.

    Returns:
        A fresh copy of the current process environment with every ambient venv signal removed.
    """
    env = dict(os.environ)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    env.pop("VIRTUAL_ENV", None)
    path_entries = env.get("PATH", "").split(os.pathsep)
    env["PATH"] = os.pathsep.join(p for p in path_entries if p and os.path.normpath(p) != str(VENV_BIN))
    return env


def _run_ty_check(*, virtual_env: str | None) -> subprocess.CompletedProcess[str]:
    """Run `ty check` on the PEP 723 fixture under a controlled, otherwise-bare environment.

    Args:
        virtual_env: Value to set for `VIRTUAL_ENV`, or `None` to leave the environment fully bare
            (reproducing the exact conditions the Astral `ty` language server launches under).

    Returns:
        The completed subprocess. `ty check`'s diagnostics are written to stdout.
    """
    env = _bare_environment()
    if virtual_env is not None:
        env["VIRTUAL_ENV"] = virtual_env
    return subprocess.run(
        [str(TY_BINARY), "check", str(PEP723_FIXTURE)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )


def test_ty_resolves_pep723_script_imports_when_virtual_env_is_set() -> None:
    """`VIRTUAL_ENV=.venv` must be enough to make ty resolve a PEP 723 script's imports.

    This gates *ty's behaviour under the prescribed mitigation*, not the presence of the
    mitigation itself: it reproduces what the language server does (bare `ty check`, no
    `uv run`, no project environment on `PATH`) with `VIRTUAL_ENV` set the way
    `rules/python-development.md` prescribes for `.claude/settings.json` (relative, so it
    resolves from whatever directory -- primary checkout or a `.claude/worktrees/*` worktree --
    the server is launched from). It cannot detect someone deleting that `env` entry from
    `.claude/settings.json`; only that the value stops working. If this starts failing, do not
    respond by suppressing the diagnostic -- re-verify against `rules/python-development.md`
    first.
    """
    result = _run_ty_check(virtual_env=".venv")

    assert result.returncode == 0, result.stdout
    assert "unresolved-import" not in result.stdout


@pytest.mark.xfail(
    reason=(
        "upstream astral-sh/ty#691: PEP 723 scripts ignore [tool.ty.environment] entirely. "
        "An unexpected pass means ty shipped a fix -- remove this test and the VIRTUAL_ENV "
        "workaround (both here and in .claude/settings.json) together, and rely on "
        "pyproject.toml's [tool.ty.environment] directly."
    ),
    strict=True,
)
def test_ty_pep723_scripts_ignore_project_environment_without_virtual_env() -> None:
    """Canary for astral-sh/ty#691 -- XPASSes (failing the suite) once ty ships a fix.

    With no ambient venv signal at all, ty falls back to system/default Python discovery for any
    PEP 723 file, regardless of `[tool.ty.environment]` in `pyproject.toml`/`ty.toml`. This is the
    exact condition the language server runs under before the `.claude/settings.json` mitigation
    is applied.

    The symptom only materialises when that fallback discovery actually lands on an interpreter
    whose site-packages lack `typer`. On a machine where the stripped `PATH` exposes no usable
    interpreter at all, ty reports `All checks passed!` for reasons unrelated to #691 -- which
    under `strict=True` would XPASS and fail the suite with a bogus "upstream shipped a fix,
    delete the workaround" instruction. Detect that case and skip instead.
    """
    result = _run_ty_check(virtual_env=None)

    if result.returncode == 0 and "unresolved-import" not in result.stdout:
        pytest.skip(
            "stripped PATH exposed no interpreter that reproduces astral-sh/ty#691 on this machine, "
            "so a pass here says nothing about whether ty still has the bug"
        )

    assert result.returncode == 0, result.stdout
