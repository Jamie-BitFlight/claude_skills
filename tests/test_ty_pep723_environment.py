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
with no ambient `uv run` and no project `.venv/bin` on `PATH`. This repo's mitigation is
`.claude/settings.json`'s `env.VIRTUAL_ENV = ".venv"`. See
`rules/python-development.md#unresolved-import-on-a-pep-723-script-specifically-in-the-language-server`
for the full narrative.

These tests invoke the project's own pinned `.venv/bin/ty` directly (never via `uv run`, which
would set `VIRTUAL_ENV` and prepend `.venv/bin` to `PATH` itself, masking exactly the condition
under test) so they are portable across machines and CI without depending on a global
`uv tool install`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TY_BINARY = REPO_ROOT / ".venv" / "bin" / "ty"
PEP723_FIXTURE = Path(__file__).parent / "fixtures" / "pep723_ty_environment_fixture.py"

pytestmark = pytest.mark.skipif(
    not TY_BINARY.exists(), reason="requires `uv sync` to have installed the pinned ty binary into .venv/bin/ty"
)


def _bare_environment() -> dict[str, str]:
    """Build a subprocess environment with no ambient venv signal at all.

    Strips `VIRTUAL_ENV`, `UV_PROJECT_ENVIRONMENT`, and any `.venv/bin`-style `PATH` entry that
    the *test runner's own* `uv run pytest` invocation prepended. Without this, `subprocess.run`
    would silently inherit the test runner's `PATH` (which already has the project's `.venv/bin`
    first) and every case would resolve correctly regardless of what this function's caller sets
    afterward -- exactly the false-negative this helper exists to prevent. This reproduces what
    the language server's `uvx ty@latest server` actually experiences: `uvx` never adds a project
    `.venv/bin` to `PATH`.

    Returns:
        A fresh copy of the current process environment with every ambient venv signal removed.
    """
    env = dict(os.environ)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    env.pop("VIRTUAL_ENV", None)
    path_entries = env.get("PATH", "").split(os.pathsep)
    env["PATH"] = os.pathsep.join(p for p in path_entries if "/.venv/" not in p and not p.endswith("/.venv"))
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
    """The `.claude/settings.json` `VIRTUAL_ENV=.venv` mitigation must keep the LSP green.

    This is the actual regression gate: it reproduces exactly what the language server does
    (bare `ty check`, no `uv run`, no project `.venv/bin` on `PATH`) with the one mitigation this
    repo applies (`VIRTUAL_ENV` set, relative so it resolves from whatever directory -- primary
    checkout or a `.claude/worktrees/*` worktree -- the server is launched from). If this starts
    failing, the mitigation has stopped working; do not respond by suppressing the diagnostic,
    re-verify against `rules/python-development.md` first.
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
    """
    result = _run_ty_check(virtual_env=None)

    assert result.returncode == 0, result.stdout
