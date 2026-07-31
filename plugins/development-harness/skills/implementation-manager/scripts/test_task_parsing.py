"""Tests for bare YAML frontmatter parsing and DEFERRED/SKIPPED task status handling.

Test suite covers:
- Bare YAML frontmatter parsing via parse_task_content (no fenced YAML recovery paths)
- DEFERRED and SKIPPED statuses: YAML parsing, title-override, get_ready_tasks, status output
- parse_status() text mapping for deferred/skipped indicators

All dead code paths (detect_fenced_yaml, fenced YAML recovery, legacy markdown parser)
are deliberately absent — those paths are deleted in T2/T3.

Mandatory standards:
- All tests follow AAA (Arrange-Act-Assert) pattern
- All fixtures and test functions are fully type-annotated
- Uses monkeypatch for stderr capture (sys.stderr.write is used by the module)
- No unittest.mock — pytest-mock / monkeypatch only
- Tests are fully isolated (no shared mutable state)
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Make the scripts directory importable for direct uv run pytest invocation.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import TYPE_CHECKING

import implementation_manager as im

if TYPE_CHECKING:
    import pytest


# =============================================================================
# Helpers
# =============================================================================

_MINIMAL_TASK_YAML = (
    "---\n"
    "task: T1\n"
    "title: Minimal Task\n"
    "status: not-started\n"
    "agent: python3-development:python-cli-architect\n"
    "dependencies: []\n"
    "priority: 1\n"
    "complexity: low\n"
    "---\n"
)

_DEFERRED_TASK_YAML = (
    "---\n"
    "task: T3\n"
    "title: Deferred Task\n"
    "status: deferred\n"
    "agent: python3-development:python-cli-architect\n"
    "dependencies: []\n"
    "priority: 3\n"
    "complexity: low\n"
    "---\n"
)

_SKIPPED_TASK_YAML = (
    "---\n"
    "task: T4\n"
    "title: Skipped Task\n"
    "status: skipped\n"
    "agent: python3-development:python-cli-architect\n"
    "dependencies: []\n"
    "priority: 4\n"
    "complexity: low\n"
    "---\n"
)

_DEFERRED_TITLE_YAML = (
    "---\n"
    "task: T5\n"
    "title: '[DEFERRED] Intentionally deferred task'\n"
    "status: not-started\n"
    "agent: python3-development:python-cli-architect\n"
    "dependencies: []\n"
    "priority: 5\n"
    "complexity: low\n"
    "---\n"
)


# =============================================================================
# Bare YAML frontmatter parsing
# =============================================================================


class TestParseTaskContentRawYaml:
    """Tests for parse_task_content with bare YAML frontmatter (the live code path).

    Scope: Verifies that correctly formatted raw ``---`` frontmatter is parsed
    into Task objects without emitting any WARNING to stderr.

    Strategy: Arrange raw YAML strings, capture stderr via monkeypatch, call
    parse_task_content, assert correct Task fields and silent stderr.

    Why: Bare YAML frontmatter is the only supported format after dead code
    removal. Regressions here break all orchestration, status tracking, and hooks.
    """

    def test_parse_task_content_raw_yaml_no_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Parses raw YAML frontmatter without emitting any WARNING.

        Tests: parse_task_content with correctly formatted raw frontmatter.
        How: Arrange raw '---\\n...\\n---\\n' content, capture stderr, assert
             1 Task returned and stderr is empty.
        Why: Correctly formatted files must not trigger warnings — warning presence
             would pollute orchestrator logs for well-formed task files.
        """
        # Arrange
        content = _MINIMAL_TASK_YAML
        stderr_buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", stderr_buf)

        # Act
        result = im.parse_task_content(content)

        # Assert
        monkeypatch.undo()
        stderr_output = stderr_buf.getvalue()
        assert len(result) == 1
        assert result[0].id == "T1"
        assert stderr_output == ""


# =============================================================================
# Tests for DEFERRED and SKIPPED status support (issue #408)
# =============================================================================


class TestDeferredSkippedStatus:
    """Tests for DEFERRED and SKIPPED task statuses (issue #408).

    Scope: Verifies that DEFERRED and SKIPPED statuses are:
    - Parsed correctly from YAML frontmatter
    - Inferred from [DEFERRED]/[SKIPPED] markers in task titles
    - Treated as terminal (not appearing in ready-tasks list)
    - Counted separately in status output
    - Treated as satisfying dependencies for dependent tasks

    Why: Without DEFERRED/SKIPPED as terminal statuses, intentionally deferred
    tasks prevent /complete-implementation from triggering even when all
    actionable tasks are COMPLETE.
    """

    def test_parse_deferred_status_from_yaml(self) -> None:
        """Parses 'deferred' YAML status into TaskStatus.DEFERRED.

        Tests: _parse_yaml_status and parse_task_from_frontmatter with deferred status.
        How: Arrange YAML with status: deferred, parse, assert TaskStatus.DEFERRED.
        Why: The fundamental fix — YAML files must be able to express deferred status.
        """
        # Arrange / Act
        result = im.parse_task_content(_DEFERRED_TASK_YAML)

        # Assert
        assert len(result) == 1
        assert result[0].status == im.TaskStatus.DEFERRED
        assert result[0].id == "T3"

    def test_parse_skipped_status_from_yaml(self) -> None:
        """Parses 'skipped' YAML status into TaskStatus.SKIPPED.

        Tests: _parse_yaml_status with skipped status.
        How: Arrange YAML with status: skipped, parse, assert TaskStatus.SKIPPED.
        Why: SKIPPED is a valid terminal status equivalent to DEFERRED for completion gating.
        """
        # Arrange / Act
        result = im.parse_task_content(_SKIPPED_TASK_YAML)

        # Assert
        assert len(result) == 1
        assert result[0].status == im.TaskStatus.SKIPPED
        assert result[0].id == "T4"

    def test_parse_wont_fix_status_maps_to_skipped(self) -> None:
        """Parses 'wont-fix' YAML status into TaskStatus.SKIPPED.

        Tests: _YAML_STATUS_TO_ENUM mapping for wont-fix.
        How: Arrange YAML with status: wont-fix, parse, assert TaskStatus.SKIPPED.
        Why: wont-fix is semantically equivalent to skipped for completion purposes.
        """
        # Arrange
        content = (
            "---\n"
            "task: T6\n"
            "title: Wont Fix Task\n"
            "status: wont-fix\n"
            "agent: python3-development:python-cli-architect\n"
            "dependencies: []\n"
            "priority: 3\n"
            "complexity: low\n"
            "---\n"
        )

        # Act
        result = im.parse_task_content(content)

        # Assert
        assert len(result) == 1
        assert result[0].status == im.TaskStatus.SKIPPED

    def test_deferred_title_marker_overrides_not_started_status(self) -> None:
        """[DEFERRED] in task title overrides not-started YAML status to DEFERRED.

        Tests: parse_task_from_frontmatter title-based status override.
        How: Arrange YAML with status: not-started and [DEFERRED] in title,
             parse, assert TaskStatus.DEFERRED.
        Why: Existing tasks often have [DEFERRED] in the title but status was not
             updated — the override prevents them from blocking completion.
        """
        # Arrange / Act
        result = im.parse_task_content(_DEFERRED_TITLE_YAML)

        # Assert
        assert len(result) == 1
        assert result[0].status == im.TaskStatus.DEFERRED

    def test_skipped_title_marker_overrides_not_started_status(self) -> None:
        """[SKIPPED] in task title overrides not-started YAML status to SKIPPED.

        Tests: parse_task_from_frontmatter title-based status override for SKIPPED.
        How: Arrange YAML with status: not-started and [SKIPPED] in title,
             parse, assert TaskStatus.SKIPPED.
        Why: Consistent with DEFERRED override — title markers must work for SKIPPED too.
        """
        # Arrange
        content = (
            "---\n"
            "task: T7\n"
            "title: '[SKIPPED] Optional enhancement'\n"
            "status: not-started\n"
            "agent: python3-development:python-cli-architect\n"
            "dependencies: []\n"
            "priority: 5\n"
            "complexity: low\n"
            "---\n"
        )

        # Act
        result = im.parse_task_content(content)

        # Assert
        assert len(result) == 1
        assert result[0].status == im.TaskStatus.SKIPPED

    def test_deferred_task_not_in_ready_tasks(self) -> None:
        """DEFERRED task does not appear in get_ready_tasks output.

        Tests: get_ready_tasks excludes DEFERRED tasks.
        How: Create task list with one NOT_STARTED and one DEFERRED task (no deps),
             call get_ready_tasks, assert only NOT_STARTED task is returned.
        Why: Deferred tasks must not be scheduled for execution by the orchestrator.
        """
        # Arrange
        from implementation_manager import Task, TaskPriority, TaskStatus, get_ready_tasks

        tasks = [
            Task(
                id="T1",
                name="Active",
                status=TaskStatus.NOT_STARTED,
                dependencies=[],
                agent="agent-a",
                priority=TaskPriority.HIGH,
                complexity="Low",
                started=None,
                completed=None,
                skills=[],
            ),
            Task(
                id="T2",
                name="Deferred",
                status=TaskStatus.DEFERRED,
                dependencies=[],
                agent="agent-b",
                priority=TaskPriority.LOW,
                complexity="Low",
                started=None,
                completed=None,
                skills=[],
            ),
        ]

        # Act
        ready = get_ready_tasks(tasks)

        # Assert
        assert len(ready) == 1
        assert ready[0].id == "T1"

    def test_deferred_dependency_does_not_block_dependent_task(self) -> None:
        """A task whose only dependency is DEFERRED is included in ready tasks.

        Tests: get_ready_tasks treats DEFERRED as satisfying dependencies.
        How: Create T2 NOT_STARTED depending on T1 DEFERRED, call get_ready_tasks,
             assert T2 is in ready list.
        Why: If a prerequisite is intentionally deferred, dependent work that can
             proceed independently should not be blocked.
        """
        from implementation_manager import Task, TaskPriority, TaskStatus, get_ready_tasks

        # Arrange
        tasks = [
            Task(
                id="T1",
                name="Deferred Prereq",
                status=TaskStatus.DEFERRED,
                dependencies=[],
                agent=None,
                priority=TaskPriority.HIGH,
                complexity="Low",
                started=None,
                completed=None,
                skills=[],
            ),
            Task(
                id="T2",
                name="Dependent",
                status=TaskStatus.NOT_STARTED,
                dependencies=["T1"],
                agent="agent-a",
                priority=TaskPriority.HIGH,
                complexity="Low",
                started=None,
                completed=None,
                skills=[],
            ),
        ]

        # Act
        ready = get_ready_tasks(tasks)

        # Assert
        assert len(ready) == 1
        assert ready[0].id == "T2"

    def test_parse_status_deferred_text(self) -> None:
        """parse_status() maps 'deferred' text to TaskStatus.DEFERRED.

        Tests: parse_status with raw 'deferred' text (legacy markdown scenario).
        How: Call parse_status with 'deferred', assert TaskStatus.DEFERRED returned.
        Why: Legacy markdown task files may set **Status**: DEFERRED.
        """
        # Arrange / Act / Assert
        assert im.parse_status("deferred") == im.TaskStatus.DEFERRED
        assert im.parse_status("DEFERRED") == im.TaskStatus.DEFERRED
        assert im.parse_status("[DEFERRED]") == im.TaskStatus.DEFERRED

    def test_parse_status_skipped_text(self) -> None:
        """parse_status() maps 'skipped' text to TaskStatus.SKIPPED.

        Tests: parse_status with raw 'skipped' / 'wont fix' text.
        How: Call parse_status with various skipped indicators, assert TaskStatus.SKIPPED.
        Why: Multiple synonyms exist for intentionally skipped tasks.
        """
        # Arrange / Act / Assert
        assert im.parse_status("skipped") == im.TaskStatus.SKIPPED
        assert im.parse_status("SKIPPED") == im.TaskStatus.SKIPPED
        assert im.parse_status("wont-fix") == im.TaskStatus.SKIPPED
        assert im.parse_status("wont fix") == im.TaskStatus.SKIPPED
