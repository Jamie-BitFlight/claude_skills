from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).parents[1] / ".claude" / "hooks" / "pytest-concurrency-gate.cjs"


def run_gate(command: str) -> subprocess.CompletedProcess[str]:
    event = {"tool_input": {"command": command}}
    return subprocess.run(["node", str(HOOK)], capture_output=True, check=False, input=json.dumps(event), text=True)


@pytest.mark.parametrize(
    "command",
    [
        "pytest tests/test_run_bounded.py",
        "uv run pytest tests/test_run_bounded.py",
        "python -m pytest tests/test_run_bounded.py",
    ],
)
def test_gate_rejects_raw_pytest_commands(command: str) -> None:
    result = run_gate(command)

    assert result.returncode == 2
    assert "scripts/run_bounded.py" in result.stderr


def test_gate_allows_the_canonical_bounded_pytest_wrapper() -> None:
    result = run_gate(
        "uv run --script scripts/run_bounded.py --timeout-seconds 300 -- uv run pytest tests/test_run_bounded.py"
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_gate_ignores_non_pytest_bash_commands() -> None:
    result = run_gate("uv run ruff check scripts/run_bounded.py")

    assert result.returncode == 0
    assert result.stderr == ""
