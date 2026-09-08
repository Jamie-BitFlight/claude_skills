"""Tests for beads task routing — T19.

Covers:
- fetch_tasks_from_backend: routes "bd-a3f8" → beads subprocess (mocked)
- fetch_tasks_from_backend: routes int → fetch_tasks_from_github (mocked)
- PEP 723 metadata validity for task_status_hook.py

No live ``bd`` binary is invoked — all subprocess interactions are mocked.

Divergence Note DN-1
--------------------
Task requirements referenced "mocked BdRunner".  The actual implementation
in ``fetch_tasks_from_beads`` uses ``subprocess.run`` directly — not the
``BdRunner`` class from ``backlog_core``.  Tests mock ``subprocess.run`` in
the ``implementation_manager`` namespace per the actual implementation.

Divergence Note DN-2
--------------------
Requirements implied ``handle_subagent_stop`` routes through
``fetch_tasks_from_backend`` at runtime.  It never did, and since the hook was
rewritten to settle the attempt named by the stopping sub-agent's own prompt it
reads no ``parent_issue_number`` at all — ``task_status_hook.read_task_context``
returns ``(plan, task_id)`` and nothing else.  The three tests that exercised the
hook's former ``_read_context_file`` reader for beads-nanoid, integer and absent
``parent_issue_number`` values were removed with it: the field is no longer read
by the hook, so the ``int()`` cast those tests guarded against cannot recur there.
The router's own type handling is still covered below, and
``tests/test_task_status_hook.py`` covers what survives of the context reader.
"""

from __future__ import annotations

import json
import math
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from implementation_manager import Task, TaskPriority, fetch_tasks_from_backend

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_BD = "/usr/local/bin/bd"
_HOOK_SCRIPT = (
    Path(__file__).resolve().parents[1] / "skills" / "implementation-manager" / "scripts" / "task_status_hook.py"
)


def _proc(returncode: int = 0, stdout: str = "[]", stderr: str = "") -> subprocess.CompletedProcess[str]:
    """Return a minimal subprocess.CompletedProcess stub."""
    return subprocess.CompletedProcess(args=[_FAKE_BD], returncode=returncode, stdout=stdout, stderr=stderr)


def _beads_issues_json(ids: list[str] | None = None) -> str:
    """Return a JSON list of minimal beads issue dicts."""
    issues = ids or ["bd-t001"]
    return json.dumps([
        {
            "id": issue_id,
            "title": f"Task {issue_id}",
            "status": "open",
            "priority": 2,
            "dependencies": [],
            "metadata": {},
        }
        for issue_id in issues
    ])


# ---------------------------------------------------------------------------
# fetch_tasks_from_backend — beads routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetch_tasks_from_backend_beads_id_routes_to_subprocess(mocker: MockerFixture) -> None:
    """fetch_tasks_from_backend("bd-a3f8", ...) invokes bd list --parent bd-a3f8 --json.

    Proves the beads routing branch in the match/case is reached for a valid
    beads nanoid.  No live bd binary is invoked.
    """
    mock_which = mocker.patch("implementation_manager.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch(
        "implementation_manager.subprocess.run", return_value=_proc(stdout=_beads_issues_json(["bd-t001", "bd-t002"]))
    )

    result = fetch_tasks_from_backend("bd-a3f8", "my-feature", Path("/tmp/cache.json"))

    # subprocess.run must have been called (proves live bd was not used)
    mock_which.assert_called_once_with("bd")
    mock_run.assert_called_once()

    argv = mock_run.call_args[0][0]
    assert argv == [_FAKE_BD, "list", "--parent", "bd-a3f8", "--json"], (
        "fetch_tasks_from_beads must pass the beads ID as the --parent argument"
    )

    # Two tasks should have been parsed and returned
    assert result is not None
    assert len(result) == 2
    assert all(isinstance(t, Task) for t in result)
    assert result[0].id == "bd-t001"
    assert result[1].id == "bd-t002"


@pytest.mark.unit
def test_fetch_tasks_from_backend_beads_id_returns_task_list(mocker: MockerFixture) -> None:
    """Tasks returned from beads have the expected field structure."""
    mocker.patch("implementation_manager.shutil.which", return_value=_FAKE_BD)
    mocker.patch(
        "implementation_manager.subprocess.run",
        return_value=_proc(
            stdout=json.dumps([
                {
                    "id": "bd-abc1",
                    "title": "Write integration tests",
                    "status": "open",
                    "priority": 1,
                    "dependencies": [],
                    "metadata": {"dh.agent": "python-pytest-architect"},
                }
            ])
        ),
    )

    result = fetch_tasks_from_backend("bd-a3f8", "feature-x", Path("/tmp/cache.json"))

    assert result is not None
    assert len(result) == 1
    task = result[0]
    assert task.id == "bd-abc1"
    assert task.name == "Write integration tests"
    assert task.agent == "python-pytest-architect"
    assert task.priority == TaskPriority.CRITICAL  # priority=1 → CRITICAL


@pytest.mark.unit
def test_fetch_tasks_from_backend_bd_not_installed_returns_none(mocker: MockerFixture) -> None:
    """When bd is not on PATH, fetch_tasks_from_beads returns None (no crash)."""
    mocker.patch("implementation_manager.shutil.which", return_value=None)

    result = fetch_tasks_from_backend("bd-a3f8", "feature-x", Path("/tmp/cache.json"))

    assert result is None


@pytest.mark.unit
def test_fetch_tasks_from_backend_bd_nonzero_exit_returns_none(mocker: MockerFixture) -> None:
    """When bd list exits non-zero, fetch_tasks_from_beads returns None."""
    mocker.patch("implementation_manager.shutil.which", return_value=_FAKE_BD)
    mocker.patch("implementation_manager.subprocess.run", return_value=_proc(returncode=1, stderr="bd: unknown parent"))

    result = fetch_tasks_from_backend("bd-a3f8", "feature-x", Path("/tmp/cache.json"))

    assert result is None


# ---------------------------------------------------------------------------
# fetch_tasks_from_backend — integer (GitHub) routing regression
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetch_tasks_from_backend_integer_id_routes_to_github(mocker: MockerFixture) -> None:
    """fetch_tasks_from_backend(42, ...) must delegate to fetch_tasks_from_github.

    Regression guard: integer IDs must not be routed through the beads subprocess.
    """
    mock_github = mocker.patch("implementation_manager.fetch_tasks_from_github", return_value=[])

    result = fetch_tasks_from_backend(42, "my-feature", Path("/tmp/cache.json"))

    mock_github.assert_called_once_with(42, "my-feature", Path("/tmp/cache.json"))
    assert result == []


@pytest.mark.unit
def test_fetch_tasks_from_backend_invalid_string_raises_valueerror() -> None:
    """fetch_tasks_from_backend raises ValueError for a non-beads-nanoid string."""
    with pytest.raises(ValueError, match="Unrecognized parent_issue_number format"):
        fetch_tasks_from_backend("not-a-valid-id-123!", "feature-x", Path("/tmp/cache.json"))


@pytest.mark.unit
def test_fetch_tasks_from_backend_float_raises_typeerror() -> None:
    """fetch_tasks_from_backend raises TypeError for non-str/int input."""
    with pytest.raises(TypeError, match="parent_issue_number must be int"):
        fetch_tasks_from_backend(cast("str | int", math.pi), "feature-x", Path("/tmp/cache.json"))


# ---------------------------------------------------------------------------
# PEP 723 metadata validity for task_status_hook.py
# ---------------------------------------------------------------------------


def _extract_pep723_block(path: Path) -> str:
    """Extract the TOML content from a PEP 723 '# /// script' block.

    Args:
        path: Path to the script file containing the PEP 723 inline metadata block.

    Returns:
        The TOML source text inside the block, with leading '# ' prefixes stripped.
        Returns an empty string if no block is found.

    Why: Two PEP 723 metadata tests contain identical extraction loops — extracting
    this to a module-level helper eliminates the duplication and gives the logic
    a clear, named home.
    """
    in_block = False
    block_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.rstrip() == "# /// script":
            in_block = True
            continue
        if in_block:
            if line.rstrip() == "# ///":
                break
            if line.startswith("# "):
                block_lines.append(line[2:])
            else:
                block_lines.append(line)
    return "\n".join(block_lines)


@pytest.mark.unit
def test_task_status_hook_pep723_metadata_is_valid_toml() -> None:
    """task_status_hook.py PEP 723 inline metadata block is valid TOML."""
    assert _HOOK_SCRIPT.exists(), f"Expected hook script at {_HOOK_SCRIPT}"

    toml_src = _extract_pep723_block(_HOOK_SCRIPT)
    assert toml_src, "No PEP 723 script block found in task_status_hook.py"

    metadata = tomllib.loads(toml_src)

    assert "requires-python" in metadata, "PEP 723 block must declare requires-python"
    assert "dependencies" in metadata, "PEP 723 block must declare dependencies"
    assert isinstance(metadata["dependencies"], list), "dependencies must be a list"
    assert len(metadata["dependencies"]) > 0, "dependencies list must not be empty"


@pytest.mark.unit
def test_task_status_hook_pep723_requires_python_311_or_newer() -> None:
    """task_status_hook.py requires Python 3.11 or newer per PEP 723 metadata."""
    metadata = tomllib.loads(_extract_pep723_block(_HOOK_SCRIPT))
    requires = metadata.get("requires-python", "")

    # Must specify >=3.11 or stricter (>=3.12, ==3.11, etc.)
    assert "3.1" in requires or "3.2" in requires, f"requires-python must be >=3.11, got: {requires!r}"
