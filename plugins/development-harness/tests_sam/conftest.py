"""Shared pytest fixtures for sam_schema test suite.

Provides reusable Plan, Task, and temporary directory fixtures used across
all test modules (models, readers, writers, query, CLI, dependencies).

Fixture design follows AAA pattern with full type annotations and pytest-mock
(no unittest.mock).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sam_schema.core.action_models import TaskDefinition
from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config

if TYPE_CHECKING:
    from collections.abc import Generator

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Reusable test helpers (not fixtures — called directly with arguments)
# ---------------------------------------------------------------------------


def make_task(
    task_id: str,
    status: TaskStatus = TaskStatus.NOT_STARTED,
    dependencies: list[str] | None = None,
    priority: Priority = Priority.MEDIUM,
) -> Task:
    """Return a minimal Task for test use.

    This is the shared helper used across test_server, test_server_mcp,
    test_dependencies, and test_query.  Centralised here to eliminate
    duplication.
    """
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        status=status,
        dependencies=dependencies or [],
        priority=priority,
        complexity=Complexity.MEDIUM,
    )


def make_task_def(
    task_id: str = "T01",
    title: str = "Test task",
    status: str = "not-started",
    deps: list[str] | None = None,
    agent: str = "test-agent",
) -> TaskDefinition:
    """Return a minimal TaskDefinition suitable for TaskBackend.create_plan and append_task.

    Uses model_validate to accept raw test values (int priority, str complexity)
    without triggering ty type errors on enum fields.

    Used by test_consolidated_tools.  Centralised here to eliminate duplication.
    """
    return TaskDefinition.model_validate({
        "id": task_id,
        "title": title,
        "status": status,
        "agent": agent,
        "dependencies": deps if deps is not None else [],
        "priority": 1,
        "complexity": "low",
    })


# ---------------------------------------------------------------------------
# Backend fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_backend() -> Generator[InMemoryTaskProvider, None, None]:
    """Inject a fresh InMemoryTaskProvider via set_task_config.

    Calls reset_task_config() in teardown to prevent cross-test contamination.

    Yields:
        Configured InMemoryTaskProvider instance.
    """
    backend = InMemoryTaskProvider()
    set_task_config(TaskConfig(backend=backend))
    yield backend
    reset_task_config()


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
    r"""Return a Plan with 3 tasks forming a dependency chain.

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
