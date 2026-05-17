"""Tests for task_status_hook.py beads integration — T19.

Covers:
- _read_context_file: beads nanoid parent_issue_number does NOT raise ValueError (T12 fix)
- _read_context_file: integer parent_issue_number regression
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
``fetch_tasks_from_backend`` at runtime.  The actual hook receives
``_parent_issue_number`` (underscore-prefixed: intentionally unused) with
an inline comment reserving the call for a future version.  End-to-end
routing through the hook is therefore not testable at present; tests cover
``_read_context_file`` and the ``fetch_tasks_from_backend`` router directly.
"""

from __future__ import annotations

import json
import math
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from implementation_manager import Task, TaskPriority, fetch_tasks_from_backend
from task_status_hook import _read_context_file

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_BD = "/usr/local/bin/bd"
_HOOK_SCRIPT = (
    Path(__file__).resolve().parents[1] / "skills" / "implementation-manager" / "scripts" / "task_status_hook.py"
)


def _context_json(task_file_path: str, task_id: str, parent_issue_number: int | str | None) -> str:
    """Serialise a minimal active-task context JSON payload."""
    payload: dict[str, object] = {
        "task_file_path": task_file_path,
        "task_id": task_id,
        "parent_issue_number": parent_issue_number,
    }
    return json.dumps(payload)


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
# _read_context_file — beads nanoid does NOT raise ValueError (T12 fix)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_read_context_file_beads_id_no_valueerror(tmp_path: Path) -> None:
    """T12 fix: _read_context_file returns beads nanoid str, never raises ValueError.

    Prior to T12 the function performed ``int(data.get("parent_issue_number"))``
    which raises ``ValueError`` for "bd-a3f8".  The fix widened the type to
    ``str | int | None`` and removed the cast.
    """
    ctx = tmp_path / "active-task-test.json"
    ctx.write_text(
        _context_json(task_file_path="/tmp/plan/P001-feature.yaml", task_id="T1", parent_issue_number="bd-a3f8"),
        encoding="utf-8",
    )

    task_path, task_id, parent = _read_context_file(ctx)

    assert parent == "bd-a3f8", "beads nanoid must be returned as-is (str), not int-cast"
    assert isinstance(parent, str), "type must be str, not int"
    assert task_id == "T1"
    assert task_path == "/tmp/plan/P001-feature.yaml"


@pytest.mark.unit
def test_read_context_file_beads_id_type_is_str(tmp_path: Path) -> None:
    """Explicit type check: parent_issue_number for beads ID is str, not None or int."""
    ctx = tmp_path / "active-task-test.json"
    ctx.write_text(_context_json("/tmp/plan/P001.yaml", "T2", "bd-a3f8"), encoding="utf-8")

    _, _, parent = _read_context_file(ctx)

    assert type(parent) is str


# ---------------------------------------------------------------------------
# _read_context_file — integer parent_issue_number regression (GitHub path)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_read_context_file_integer_parent_issue_number(tmp_path: Path) -> None:
    """Regression: integer parent_issue_number (GitHub) is returned unchanged as int."""
    ctx = tmp_path / "active-task-42.json"
    ctx.write_text(_context_json("/tmp/plan/P042.yaml", "T3", 42), encoding="utf-8")

    _task_path, task_id, parent = _read_context_file(ctx)

    assert parent == 42
    assert isinstance(parent, int)
    assert task_id == "T3"


@pytest.mark.unit
def test_read_context_file_none_parent_issue_number(tmp_path: Path) -> None:
    """parent_issue_number absent from context file is returned as None."""
    ctx = tmp_path / "active-task-none.json"
    ctx.write_text(_context_json("/tmp/plan/P001.yaml", "T4", None), encoding="utf-8")

    _, _, parent = _read_context_file(ctx)

    assert parent is None


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
        fetch_tasks_from_backend(math.pi, "feature-x", Path("/tmp/cache.json"))  # type: ignore[arg-type]


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
