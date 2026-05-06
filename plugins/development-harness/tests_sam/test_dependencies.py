"""Tests for sam_schema.core.dependencies — dependency graph, cycle detection, and bookend validation."""

from __future__ import annotations

from sam_schema.core.dependencies import (
    SUCCESSFUL_STATUSES,
    TERMINAL_STATUSES,
    BookendValidator,
    DependencyGraph,
    _task_id_sort_key,
)
from sam_schema.core.models import AcceptanceCriterion, BookendType, Complexity, Plan, Priority, Task, TaskStatus

# ---------------------------------------------------------------------------
# Helpers (shared — see conftest.py)
# ---------------------------------------------------------------------------
from tests_sam.conftest import make_task

# ---------------------------------------------------------------------------
# _task_id_sort_key unit tests
# ---------------------------------------------------------------------------


def test_task_id_sort_key_numeric_only_returns_correct_tuple() -> None:
    # Arrange / Act / Assert
    assert _task_id_sort_key("1") == (1, 0)


def test_task_id_sort_key_t_prefix_returns_correct_tuple() -> None:
    assert _task_id_sort_key("T5") == (5, 0)


def test_task_id_sort_key_with_minor_component_returns_correct_tuple() -> None:
    assert _task_id_sort_key("T2.3") == (2, 3)


def test_task_id_sort_key_non_matching_returns_zero_tuple() -> None:
    assert _task_id_sort_key("unknown") == (0, 0)


def test_task_id_sort_key_orders_correctly_in_sort() -> None:
    # Arrange
    ids = ["T10", "T2", "T1", "T3"]
    # Act
    sorted_ids = sorted(ids, key=_task_id_sort_key)
    # Assert
    assert sorted_ids == ["T1", "T2", "T3", "T10"]


# ---------------------------------------------------------------------------
# DependencyGraph.get_ready_tasks
# ---------------------------------------------------------------------------


def test_get_ready_tasks_no_dependencies_returns_all_not_started() -> None:
    # Arrange
    tasks = [make_task("T1"), make_task("T2")]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert
    assert {t.id for t in ready} == {"T1", "T2"}


def test_get_ready_tasks_with_complete_dep_returns_dependent_task() -> None:
    # Arrange
    tasks = [make_task("T1", status=TaskStatus.COMPLETE), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert
    assert len(ready) == 1
    assert ready[0].id == "T2"


def test_get_ready_tasks_with_not_started_dep_excludes_blocked_task() -> None:
    # Arrange
    tasks = [make_task("T1"), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert — only T1 is ready; T2 depends on not-yet-complete T1
    assert [t.id for t in ready] == ["T1"]


def test_get_ready_tasks_deferred_dep_satisfies_dependency() -> None:
    # Arrange
    tasks = [make_task("T1", status=TaskStatus.DEFERRED), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert — deferred is terminal, so T2 is ready
    assert [t.id for t in ready] == ["T2"]


def test_get_ready_tasks_skipped_dep_does_not_satisfy_dependency() -> None:
    # Arrange
    tasks = [make_task("T1", status=TaskStatus.SKIPPED), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert — skipped is terminal but not successful for dependency dispatch
    assert ready == []


def test_get_ready_tasks_in_progress_dep_does_not_satisfy() -> None:
    # Arrange
    tasks = [make_task("T1", status=TaskStatus.IN_PROGRESS), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert — in-progress is not terminal
    assert ready == []


def test_get_ready_tasks_missing_dep_id_blocks_task() -> None:
    # Arrange — T2 depends on T99 which doesn't exist
    tasks = [make_task("T2", dependencies=["T99"])]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert
    assert ready == []


def test_get_ready_tasks_sorted_by_priority_then_id() -> None:
    # Arrange — T3 has higher priority (lower number) than T1
    tasks = [
        make_task("T1", priority=Priority.LOW),
        make_task("T3", priority=Priority.HIGH),
        make_task("T2", priority=Priority.LOW),
    ]
    graph = DependencyGraph(tasks)

    # Act
    ready = graph.get_ready_tasks()

    # Assert — T3 (priority=2) comes first, then T1/T2 by ID
    assert ready[0].id == "T3"
    assert ready[1].id == "T1"
    assert ready[2].id == "T2"


def test_get_ready_tasks_empty_task_list_returns_empty() -> None:
    # Arrange
    graph = DependencyGraph([])

    # Act / Assert
    assert graph.get_ready_tasks() == []


# ---------------------------------------------------------------------------
# DependencyGraph.has_cycles / get_cycles
# ---------------------------------------------------------------------------


def test_has_cycles_no_cycles_returns_false() -> None:
    # Arrange
    tasks = [make_task("T1"), make_task("T2", dependencies=["T1"]), make_task("T3", dependencies=["T2"])]
    graph = DependencyGraph(tasks)

    # Act / Assert
    assert graph.has_cycles() is False


def test_has_cycles_simple_two_node_cycle_returns_true() -> None:
    # Arrange: T1 -> T2 -> T1
    tasks = [make_task("T1", dependencies=["T2"]), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act / Assert
    assert graph.has_cycles() is True


def test_has_cycles_three_node_cycle_returns_true() -> None:
    # Arrange: T1 -> T2 -> T3 -> T1
    tasks = [
        make_task("T1", dependencies=["T3"]),
        make_task("T2", dependencies=["T1"]),
        make_task("T3", dependencies=["T2"]),
    ]
    graph = DependencyGraph(tasks)

    # Act / Assert
    assert graph.has_cycles() is True


def test_get_cycles_returns_cycle_members() -> None:
    # Arrange: T1 -> T2 -> T3 -> T1
    tasks = [
        make_task("T1", dependencies=["T3"]),
        make_task("T2", dependencies=["T1"]),
        make_task("T3", dependencies=["T2"]),
    ]
    graph = DependencyGraph(tasks)

    # Act
    cycles = graph.get_cycles()

    # Assert — at least one cycle reported, all members are from the cycle
    assert len(cycles) >= 1
    assert set(cycles[0]).issubset({"T1", "T2", "T3"})


def test_get_cycles_empty_task_list_returns_empty() -> None:
    # Arrange / Act / Assert
    assert DependencyGraph([]).get_cycles() == []


def test_get_cycles_acyclic_graph_returns_empty() -> None:
    # Arrange
    tasks = [make_task("T1"), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act / Assert
    assert graph.get_cycles() == []


# ---------------------------------------------------------------------------
# DependencyGraph.get_blocked_tasks
# ---------------------------------------------------------------------------


def test_get_blocked_tasks_with_not_started_dep_reports_task() -> None:
    # Arrange
    tasks = [make_task("T1"), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    blocked = graph.get_blocked_tasks()

    # Assert — T2 blocked by T1 (not-started)
    assert len(blocked) == 1
    task, missing = blocked[0]
    assert task.id == "T2"
    assert "T1" in missing


def test_get_blocked_tasks_complete_dep_does_not_block() -> None:
    # Arrange
    tasks = [make_task("T1", status=TaskStatus.COMPLETE), make_task("T2", dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    blocked = graph.get_blocked_tasks()

    # Assert — T2 is NOT blocked (T1 is complete)
    assert blocked == []


def test_get_blocked_tasks_nonexistent_dep_reports_as_unsatisfied() -> None:
    # Arrange — T1 depends on T99 which is absent from the plan
    tasks = [make_task("T1", dependencies=["T99"])]
    graph = DependencyGraph(tasks)

    # Act
    blocked = graph.get_blocked_tasks()

    # Assert
    assert len(blocked) == 1
    _, missing = blocked[0]
    assert "T99" in missing


def test_get_blocked_tasks_in_progress_task_excluded_from_blocked() -> None:
    # Arrange — T2 is in-progress, T1 is not terminal
    tasks = [make_task("T1"), make_task("T2", status=TaskStatus.IN_PROGRESS, dependencies=["T1"])]
    graph = DependencyGraph(tasks)

    # Act
    blocked = graph.get_blocked_tasks()

    # Assert — only not-started tasks are reported as blocked
    assert all(t.status == TaskStatus.NOT_STARTED for t, _ in blocked)


# ---------------------------------------------------------------------------
# Helpers for BookendValidator tests
# ---------------------------------------------------------------------------


def make_bookend_task(
    task_id: str,
    bookend_type: BookendType,
    status: TaskStatus = TaskStatus.NOT_STARTED,
    dependencies: list[str] | None = None,
    priority: Priority = Priority.MEDIUM,
) -> Task:
    """Return a Task with bookend fields set.

    Args:
        task_id: Task identifier.
        bookend_type: Either 't0-baseline' or 'tn-verification'.
        status: Task status.
        dependencies: List of dependency task IDs.
        priority: Task priority.

    Returns:
        A Task with is_bookend=True and the given bookend_type.
    """
    return Task(
        id=task_id,
        title=f"Bookend {task_id}",
        status=status,
        dependencies=dependencies or [],
        priority=priority,
        complexity=Complexity.LOW,
        is_bookend=True,
        bookend_type=bookend_type,
    )


def make_plan_with_bookends(
    impl_tasks: list[Task] | None = None,
    t0: Task | None = None,
    tn: Task | None = None,
    criteria: list[AcceptanceCriterion] | None = None,
) -> Plan:
    """Build a Plan with optional T0, TN, implementation tasks, and structured criteria.

    Args:
        impl_tasks: Non-bookend implementation tasks.
        t0: The T0 baseline bookend task, or None to omit.
        tn: The TN verification bookend task, or None to omit.
        criteria: Structured acceptance criteria, or None for empty list.

    Returns:
        A Plan containing the specified tasks and criteria.
    """
    tasks: list[Task] = []
    if t0 is not None:
        tasks.append(t0)
    if impl_tasks is not None:
        tasks.extend(impl_tasks)
    if tn is not None:
        tasks.append(tn)
    return Plan(feature="bookend-test", tasks=tasks, acceptance_criteria_structured=criteria or [])


# ---------------------------------------------------------------------------
# BookendValidator.validate — valid plans
# ---------------------------------------------------------------------------


class TestBookendValidatorValidPlans:
    """Verify BookendValidator.validate() passes on correctly structured plans.

    Tests: BookendValidator structural constraint validation.
    How: Construct plans with valid bookend configurations and verify no errors.
    Why: Valid plans must not produce false-positive validation errors.
    """

    def test_valid_plan_with_bookends_returns_no_errors(self) -> None:
        """Verify valid plan with T0 and TN produces empty error list.

        Tests: Happy path — correct T0/TN configuration.
        How: Build plan with T0 (no deps), TN (deps on all impl tasks), criteria.
        Why: The primary success case must pass cleanly.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE, priority=Priority.CRITICAL)
        impl1 = make_task("T1", dependencies=["T0"])
        impl2 = make_task("T2", dependencies=["T0"])
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1", "T2"], priority=Priority.LOWEST)
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = make_plan_with_bookends(impl_tasks=[impl1, impl2], t0=t0, tn=tn, criteria=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert errors == []

    def test_plan_without_criteria_or_bookends_returns_no_errors(self) -> None:
        """Verify plan without structured criteria and no bookends is valid.

        Tests: Backward compatibility — legacy plans pass validation.
        How: Build plan with only implementation tasks, no criteria, no bookends.
        Why: Existing plans without bookend support must not be rejected.
        """
        # Arrange
        impl1 = make_task("T1")
        impl2 = make_task("T2", dependencies=["T1"])
        plan = make_plan_with_bookends(impl_tasks=[impl1, impl2])

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert errors == []

    def test_empty_plan_returns_no_errors(self) -> None:
        """Verify empty plan with no tasks produces no errors.

        Tests: Edge case — empty plan.
        How: Build plan with no tasks.
        Why: Empty plans are valid (nothing to validate).
        """
        # Arrange
        plan = Plan(feature="empty")

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert errors == []


# ---------------------------------------------------------------------------
# BookendValidator.validate — invalid plans
# ---------------------------------------------------------------------------


class TestBookendValidatorInvalidPlans:
    """Verify BookendValidator.validate() detects structural violations.

    Tests: BookendValidator error detection for each constraint rule.
    How: Construct plans violating one rule each, verify error messages.
    Why: Each constraint must be enforced independently — a missed rule
    allows invalid plans to reach T0/TN execution.
    """

    def test_t0_only_without_tn_returns_error(self) -> None:
        """Verify plan with T0 but missing TN produces error.

        Tests: Rule 5 — structured criteria require both bookends.
        How: Build plan with T0 and criteria but no TN.
        Why: TN is required to verify post-implementation state.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        impl = make_task("T1")
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = make_plan_with_bookends(impl_tasks=[impl], t0=t0, criteria=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert len(errors) == 1
        assert "TN verification task" in errors[0]

    def test_tn_only_without_t0_returns_error(self) -> None:
        """Verify plan with TN but missing T0 produces error.

        Tests: Rule 5 — structured criteria require both bookends.
        How: Build plan with TN and criteria but no T0.
        Why: T0 is required to capture baseline state.
        """
        # Arrange
        impl = make_task("T1")
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1"])
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = make_plan_with_bookends(impl_tasks=[impl], tn=tn, criteria=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert len(errors) == 1
        assert "T0 baseline task" in errors[0]

    def test_t0_with_dependencies_returns_error(self) -> None:
        """Verify T0 with non-empty dependencies produces error.

        Tests: Rule 3 — T0 must have empty dependencies.
        How: Build T0 with a dependency on T1.
        Why: T0 must be the first task executed — dependencies delay it.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE, dependencies=["T1"])
        impl = make_task("T1")
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1"])
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = make_plan_with_bookends(impl_tasks=[impl], t0=t0, tn=tn, criteria=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert any("empty dependencies" in e for e in errors)

    def test_tn_missing_dependency_on_impl_task_returns_error(self) -> None:
        """Verify TN missing a dependency on an implementation task produces error.

        Tests: Rule 4 — TN must depend on all non-bookend tasks.
        How: Build TN that depends on T1 but not T2.
        Why: Missing dependency means TN may run before T2 completes.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        impl1 = make_task("T1")
        impl2 = make_task("T2")
        # TN depends only on T1, missing T2
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1"])
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = make_plan_with_bookends(impl_tasks=[impl1, impl2], t0=t0, tn=tn, criteria=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert any("missing" in e.lower() and "T2" in e for e in errors)

    def test_multiple_t0_tasks_returns_error(self) -> None:
        """Verify multiple T0 tasks produce error.

        Tests: Rule 1 — at most one T0 per plan.
        How: Build plan with two T0 bookend tasks.
        Why: Multiple T0s create ambiguous baseline capture.
        """
        # Arrange
        t0a = make_bookend_task("T0", BookendType.T0_BASELINE)
        # Second T0 — violates uniqueness
        t0b = Task(
            id="T5",
            title="Another baseline",
            status=TaskStatus.NOT_STARTED,
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.LOW,
            is_bookend=True,
            bookend_type=BookendType.T0_BASELINE,
        )
        impl = make_task("T1")
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1"])
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = Plan(feature="dup-t0", tasks=[t0a, t0b, impl, tn], acceptance_criteria_structured=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert any("Multiple T0" in e for e in errors)

    def test_multiple_tn_tasks_returns_error(self) -> None:
        """Verify multiple TN tasks produce error.

        Tests: Rule 2 — at most one TN per plan.
        How: Build plan with two TN bookend tasks.
        Why: Multiple TNs create ambiguous verification verdicts.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        impl = make_task("T1")
        tn_a = make_bookend_task("T98", BookendType.TN_VERIFICATION, dependencies=["T1"])
        tn_b = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1"])
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = Plan(feature="dup-tn", tasks=[t0, impl, tn_a, tn_b], acceptance_criteria_structured=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert
        assert any("Multiple TN" in e for e in errors)

    def test_criteria_without_any_bookends_returns_two_errors(self) -> None:
        """Verify plan with criteria but no bookends produces two errors.

        Tests: Rule 5 — both T0 and TN are required when criteria exist.
        How: Build plan with criteria but no T0 or TN tasks.
        Why: Criteria without bookends cannot be validated.
        """
        # Arrange
        impl = make_task("T1")
        criteria = [AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")]
        plan = make_plan_with_bookends(impl_tasks=[impl], criteria=criteria)

        # Act
        errors = BookendValidator(plan).validate()

        # Assert — should have errors about both missing T0 and missing TN
        assert len(errors) == 2
        assert any("T0" in e for e in errors)
        assert any("TN" in e for e in errors)


# ---------------------------------------------------------------------------
# BookendValidator accessor methods
# ---------------------------------------------------------------------------


class TestBookendValidatorAccessors:
    """Verify BookendValidator accessor methods return correct results.

    Tests: get_t0_task, get_tn_task, get_implementation_task_ids.
    How: Build plans with known structure, verify accessor outputs.
    Why: These methods are used by T0/TN agents and implementation_manager
    to identify bookend and implementation tasks.
    """

    def test_get_t0_task_returns_t0(self) -> None:
        """Verify get_t0_task returns the T0 task when present.

        Tests: T0 task lookup by bookend_type.
        How: Build plan with T0, query via accessor.
        Why: T0 agent uses this to identify its target task.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        plan = make_plan_with_bookends(t0=t0)
        validator = BookendValidator(plan)

        # Act
        result = validator.get_t0_task()

        # Assert
        assert result is not None
        assert result.id == "T0"
        assert result.bookend_type == "t0-baseline"

    def test_get_t0_task_returns_none_when_absent(self) -> None:
        """Verify get_t0_task returns None when no T0 exists.

        Tests: Absent T0 lookup.
        How: Build plan without T0, query via accessor.
        Why: Plans without bookends must return None, not raise.
        """
        # Arrange
        impl = make_task("T1")
        plan = make_plan_with_bookends(impl_tasks=[impl])
        validator = BookendValidator(plan)

        # Act
        result = validator.get_t0_task()

        # Assert
        assert result is None

    def test_get_tn_task_returns_tn(self) -> None:
        """Verify get_tn_task returns the TN task when present.

        Tests: TN task lookup by bookend_type.
        How: Build plan with TN, query via accessor.
        Why: TN agent uses this to identify its target task.
        """
        # Arrange
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1"])
        impl = make_task("T1")
        plan = make_plan_with_bookends(impl_tasks=[impl], tn=tn)
        validator = BookendValidator(plan)

        # Act
        result = validator.get_tn_task()

        # Assert
        assert result is not None
        assert result.id == "T99"
        assert result.bookend_type == "tn-verification"

    def test_get_tn_task_returns_none_when_absent(self) -> None:
        """Verify get_tn_task returns None when no TN exists.

        Tests: Absent TN lookup.
        How: Build plan without TN, query via accessor.
        Why: Plans without bookends must return None, not raise.
        """
        # Arrange
        impl = make_task("T1")
        plan = make_plan_with_bookends(impl_tasks=[impl])
        validator = BookendValidator(plan)

        # Act
        result = validator.get_tn_task()

        # Assert
        assert result is None

    def test_get_implementation_task_ids_excludes_bookends(self) -> None:
        """Verify get_implementation_task_ids excludes bookend tasks.

        Tests: Implementation task ID filtering.
        How: Build plan with T0, TN, and implementation tasks. Verify IDs.
        Why: TN uses this to validate its dependency list covers all impl tasks.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        impl1 = make_task("T1")
        impl2 = make_task("T2")
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION, dependencies=["T1", "T2"])
        plan = make_plan_with_bookends(impl_tasks=[impl1, impl2], t0=t0, tn=tn)
        validator = BookendValidator(plan)

        # Act
        impl_ids = validator.get_implementation_task_ids()

        # Assert
        assert impl_ids == ["T1", "T2"]
        assert "T0" not in impl_ids
        assert "T99" not in impl_ids

    def test_get_implementation_task_ids_empty_when_only_bookends(self) -> None:
        """Verify get_implementation_task_ids returns empty list when no impl tasks.

        Tests: Edge case — plan with only bookend tasks.
        How: Build plan with T0 and TN only.
        Why: Plans with zero implementation tasks are structurally valid.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        tn = make_bookend_task("T99", BookendType.TN_VERIFICATION)
        plan = make_plan_with_bookends(t0=t0, tn=tn)
        validator = BookendValidator(plan)

        # Act
        impl_ids = validator.get_implementation_task_ids()

        # Assert
        assert impl_ids == []

    def test_get_implementation_task_ids_sorted_by_id(self) -> None:
        """Verify get_implementation_task_ids returns IDs in numeric sort order.

        Tests: ID sorting via _task_id_sort_key.
        How: Build plan with unordered task IDs, verify sorted output.
        Why: Consistent ordering prevents flaky dependency comparisons.
        """
        # Arrange
        t0 = make_bookend_task("T0", BookendType.T0_BASELINE)
        impl3 = make_task("T3")
        impl1 = make_task("T1")
        impl10 = make_task("T10")
        plan = make_plan_with_bookends(impl_tasks=[impl3, impl1, impl10], t0=t0)
        validator = BookendValidator(plan)

        # Act
        impl_ids = validator.get_implementation_task_ids()

        # Assert
        assert impl_ids == ["T1", "T3", "T10"]


# ---------------------------------------------------------------------------
# FAILED status — dependency satisfaction and downstream skipping
# ---------------------------------------------------------------------------


def test_get_ready_tasks_failed_parent_does_not_unblock_downstream() -> None:
    """A FAILED parent must NOT satisfy downstream dependencies.

    Tests: FAILED is not in SUCCESSFUL_STATUSES.
    How: Parent in FAILED; child depends on parent; verify child is NOT ready.
    Why: Downstream tasks of a FAILED parent must be auto-skipped, not dispatched.
    """
    # Arrange
    parent = make_task("T1", status=TaskStatus.FAILED)
    child = make_task("T2", dependencies=["T1"])
    graph = DependencyGraph([parent, child])

    # Act
    ready = graph.get_ready_tasks()

    # Assert
    assert {t.id for t in ready} == set()


def test_mark_downstream_skipped_single_level() -> None:
    """mark_downstream_skipped returns direct dependents of the failed task.

    Tests: DependencyGraph.mark_downstream_skipped single-level propagation.
    How: T1 fails — T2 depends on T1; T3 does not depend on T1.
    Why: Only T2 should be in the returned list.
    """
    # Arrange
    parent = make_task("T1", status=TaskStatus.FAILED)
    child = make_task("T2", dependencies=["T1"])
    unrelated = make_task("T3")
    graph = DependencyGraph([parent, child, unrelated])

    # Act
    to_skip = graph.mark_downstream_skipped("T1")

    # Assert
    assert "T2" in to_skip
    assert "T3" not in to_skip


def test_mark_downstream_skipped_transitive_chain() -> None:
    """mark_downstream_skipped propagates through a 3-task chain.

    Tests: Transitive DFS walk in mark_downstream_skipped.
    How: T1 -> T2 -> T3 chain; T1 fails -> T2 and T3 should be skipped.
    Why: The measurable signal in the item spec requires this exact scenario.
    """
    # Arrange
    t1 = make_task("T1", status=TaskStatus.FAILED)
    t2 = make_task("T2", dependencies=["T1"])
    t3 = make_task("T3", dependencies=["T2"])
    graph = DependencyGraph([t1, t2, t3])

    # Act
    to_skip = graph.mark_downstream_skipped("T1")

    # Assert
    assert "T2" in to_skip
    assert "T3" in to_skip
    assert t2.status == TaskStatus.SKIPPED
    assert t3.status == TaskStatus.SKIPPED
    assert t2.reason is not None
    assert "skipped: upstream T1 failed" in t2.reason
    assert t3.reason is not None
    assert "skipped: upstream T1 failed" in t3.reason


def test_mark_downstream_skipped_already_terminal_excluded() -> None:
    """mark_downstream_skipped excludes tasks already in a terminal status.

    Tests: Only not-started tasks are returned by mark_downstream_skipped.
    How: T1 fails -> T2 depends on T1 but is already SKIPPED.
    Why: Re-marking an already-skipped task is a no-op; the list must be clean.
    """
    # Arrange
    t1 = make_task("T1", status=TaskStatus.FAILED)
    t2 = make_task("T2", status=TaskStatus.SKIPPED, dependencies=["T1"])
    graph = DependencyGraph([t1, t2])

    # Act
    to_skip = graph.mark_downstream_skipped("T1")

    # Assert
    assert "T2" not in to_skip


def test_failed_status_downstream_skip_chain_leaves_no_ready_tasks() -> None:
    """Failing T1 cascades skip state to T2/T3 and leaves no ready work."""
    # Arrange
    t1 = make_task("T1", status=TaskStatus.FAILED)
    t2 = make_task("T2", dependencies=["T1"])
    t3 = make_task("T3", dependencies=["T2"])
    graph = DependencyGraph([t1, t2, t3])

    # Act
    skipped = graph.mark_downstream_skipped("T1")
    ready = graph.get_ready_tasks()

    # Assert
    assert skipped == ["T2", "T3"]
    assert t2.status == TaskStatus.SKIPPED
    assert t3.status == TaskStatus.SKIPPED
    assert t2.reason is not None
    assert "skipped: upstream T1 failed" in t2.reason
    assert t3.reason is not None
    assert "skipped: upstream T1 failed" in t3.reason
    assert ready == []


def test_failed_is_terminal_status() -> None:
    """FAILED must be in TERMINAL_STATUSES for plan-completion checks.

    Tests: TERMINAL_STATUSES contains FAILED.
    How: Direct membership check.
    Why: Plan completion checks use TERMINAL_STATUSES; a FAILED plan must be
         recognised as completed (no more work possible).
    """
    assert TaskStatus.FAILED in TERMINAL_STATUSES


def test_failed_not_in_successful_statuses() -> None:
    """FAILED must NOT be in SUCCESSFUL_STATUSES.

    Tests: SUCCESSFUL_STATUSES excludes FAILED.
    How: Direct membership check.
    Why: SUCCESSFUL_STATUSES gates dependency satisfaction; FAILED parents must
         not unblock downstream tasks.
    """
    assert TaskStatus.FAILED not in SUCCESSFUL_STATUSES


def test_mark_downstream_skipped_empty_for_task_without_dependents() -> None:
    """mark_downstream_skipped returns empty list when failed task has no dependents.

    Tests: Base case — leaf node failure produces empty skip list.
    How: Single failed task with no downstream dependents.
    Why: Must not error or return spurious IDs.
    """
    # Arrange
    t1 = make_task("T1", status=TaskStatus.FAILED)
    graph = DependencyGraph([t1])

    # Act
    to_skip = graph.mark_downstream_skipped("T1")

    # Assert
    assert to_skip == []
