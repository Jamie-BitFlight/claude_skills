"""Shared pytest fixtures for sam_schema test suite.

Provides reusable Plan, Task, and temporary directory fixtures used across
all test modules (models, readers, writers, query, CLI, dependencies).

Fixture design follows AAA pattern with full type annotations and pytest-mock
(no unittest.mock).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Temporary plan directory
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_plan_dir(tmp_path: Path) -> Path:
    """Create a temporary plan directory for reader/writer tests.

    Returns:
        Path to a ``plan/`` directory inside ``tmp_path``.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    return plan_dir


# ---------------------------------------------------------------------------
# Model object fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_task() -> Task:
    """Return a minimal valid Task object.

    Returns:
        A ``Task`` with only required fields populated.
    """
    return Task(id="T1", title="Sample task", status=TaskStatus.NOT_STARTED)


@pytest.fixture
def sample_plan() -> Plan:
    """Return a Plan with 3 tasks forming a dependency chain.

    Dependency graph::

        T1 (no deps) --> T2 (depends T1) --> T3 (depends T1, T2)
                     \\--> T4 (depends T1)

    Returns:
        A ``Plan`` with four tasks and realistic metadata.
    """
    tasks = [
        Task(
            id="T1",
            title="Package scaffold and models",
            status=TaskStatus.COMPLETE,
            agent="python3-development:python-cli-architect",
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.MEDIUM,
        ),
        Task(
            id="T2",
            title="YAML reader implementation",
            status=TaskStatus.NOT_STARTED,
            agent="python3-development:python-cli-architect",
            dependencies=["T1"],
            priority=Priority.HIGH,
            complexity=Complexity.HIGH,
        ),
        Task(
            id="T3",
            title="Test infrastructure",
            status=TaskStatus.NOT_STARTED,
            agent="python3-development:python-pytest-architect",
            dependencies=["T1", "T2"],
            priority=Priority.MEDIUM,
            complexity=Complexity.MEDIUM,
        ),
        Task.model_validate({
            "id": "T4",
            "title": "CLI integration",
            "status": "blocked",
            "agent": "python3-development:python-cli-architect",
            "dependencies": ["T1"],
            "priority": Priority.LOW,
            "complexity": Complexity.LOW,
            "blocked_by": ["T2"],
        }),
    ]
    return Plan(feature="test-feature", version="1.0", description="A sample plan for testing purposes.", tasks=tasks)


@pytest.fixture
def plan_with_cycles() -> Plan:
    """Return a Plan containing circular dependencies.

    Cycle: T1 -> T2 -> T3 -> T1.

    Returns:
        A ``Plan`` whose dependency graph is cyclic.
    """
    tasks = [
        Task(
            id="T1",
            title="First task",
            status=TaskStatus.NOT_STARTED,
            dependencies=["T3"],
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
        ),
        Task(
            id="T2",
            title="Second task",
            status=TaskStatus.NOT_STARTED,
            dependencies=["T1"],
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
        ),
        Task(
            id="T3",
            title="Third task",
            status=TaskStatus.NOT_STARTED,
            dependencies=["T2"],
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
        ),
    ]
    return Plan(
        feature="cyclic-feature",
        version="1.0",
        description="Plan with circular dependencies for cycle detection testing.",
        tasks=tasks,
    )


# ---------------------------------------------------------------------------
# Fixture file path helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory.

    Returns:
        Absolute path to ``tests/fixtures/``.
    """
    return FIXTURES_DIR
