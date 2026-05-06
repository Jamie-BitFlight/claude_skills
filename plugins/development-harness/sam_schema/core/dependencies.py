"""Dependency graph with cycle detection and task readiness queries.

Builds a directed acyclic graph (DAG) from task dependencies and provides
cycle detection, readiness checks, and blocked task reporting.
"""

from __future__ import annotations

import re

from sam_schema.core.models import BookendType, Plan, Task, TaskStatus

# Statuses that satisfy a dependency — a downstream task may proceed only when
# its dependency is in one of these statuses.  FAILED is intentionally excluded:
# a failed parent must NOT unblock its dependents (they should be auto-skipped).
SUCCESSFUL_STATUSES: frozenset[str] = frozenset({TaskStatus.COMPLETE, TaskStatus.DEFERRED})

# Statuses that represent the end of a task's lifecycle (no further transitions
# are expected).  Used for cycle detection and plan-completion checks.
TERMINAL_STATUSES: frozenset[str] = frozenset({
    TaskStatus.COMPLETE,
    TaskStatus.DEFERRED,
    TaskStatus.SKIPPED,
    TaskStatus.FAILED,
})

# Pattern used to extract the numeric portion of a task ID for ordering.
# Matches "T1", "1", "T2.3", "1.1" — captures the leading numeric part.
_ID_NUMERIC_RE: re.Pattern[str] = re.compile(r"[A-Za-z]*(\d+)(?:\.(\d+))?$")


def _task_id_sort_key(task_id: str) -> tuple[int, int]:
    """Return a (major, minor) integer tuple for stable task ID ordering.

    Args:
        task_id: A validated task ID string such as "T1", "2.3", or "T10".

    Returns:
        A tuple ``(major, minor)`` suitable for ascending numeric sort.
        IDs without a minor component use ``minor=0``.
    """
    m = _ID_NUMERIC_RE.match(task_id)
    if not m:
        return (0, 0)
    major = int(m.group(1))
    minor = int(m.group(2)) if m.group(2) else 0
    return (major, minor)


class DependencyGraph:
    """Task dependency graph with cycle detection and readiness queries.

    Args:
        tasks: All tasks in a plan. Each task's ``dependencies`` list is
               used to build the directed graph edges.
    """

    def __init__(self, tasks: list[Task]) -> None:
        """Build the dependency graph from a list of tasks.

        Constructs an index of all tasks by ID and an adjacency mapping
        (``task_id -> list[dep_id]``) for O(1) lookups during graph queries.

        Args:
            tasks: All tasks in the plan.
        """
        self._tasks: list[Task] = tasks
        # Primary lookup: task ID -> Task
        self._by_id: dict[str, Task] = {t.id: t for t in tasks}
        # Adjacency list: task ID -> direct dependency IDs (raw from model)
        self._deps: dict[str, list[str]] = {t.id: list(t.dependencies) for t in tasks}

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_ready_tasks(self) -> list[Task]:
        """Return tasks that are ready for dispatch.

        A task is ready when:

        1. Its status is ``not-started``.
        2. All tasks listed in its ``dependencies`` are in a successful status
           (``complete`` or ``deferred``).

        Tasks referencing dependency IDs that do not exist in the task list
        are treated as having an unsatisfied dependency and are therefore
        **not** ready.

        Returns:
            Tasks ready for dispatch, sorted by priority (ascending integer
            value, lower = higher priority) then numeric task ID (ascending).
        """
        ready: list[Task] = []
        for task in self._tasks:
            if task.status != TaskStatus.NOT_STARTED:
                continue
            if self._all_deps_successful(task):
                ready.append(task)

        ready.sort(key=lambda t: (int(t.priority), _task_id_sort_key(t.id)))
        return ready

    def has_cycles(self) -> bool:
        """Check whether the dependency graph contains any cycles.

        Uses a DFS-based three-colour algorithm (white/grey/black) to detect
        back edges, which indicate cycles.

        Returns:
            ``True`` if at least one cycle exists, ``False`` otherwise.
        """
        return bool(self.get_cycles())

    def get_cycles(self) -> list[list[str]]:
        """Return all dependency cycles as lists of task IDs.

        Each cycle is represented as the minimal ordered sequence of task IDs
        that form the loop (e.g., ``["T1", "T2", "T3"]`` for T1→T2→T3→T1).
        The reported path starts and ends at the node that first closed the
        cycle during DFS traversal.

        Returns:
            List of cycles, where each cycle is a list of task ID strings.
            Empty list if no cycles exist.
        """
        # Three-colour DFS: 0=unvisited, 1=in-stack, 2=done
        colour: dict[str, int] = dict.fromkeys(self._by_id, 0)
        # Stack path for cycle reconstruction
        stack: list[str] = []
        cycles: list[list[str]] = []
        # Track cycles already found (by frozenset) to avoid duplicates
        seen_cycles: set[frozenset[str]] = set()

        def dfs(node: str) -> None:
            colour[node] = 1
            stack.append(node)
            for dep_id in self._deps.get(node, []):
                if dep_id not in colour:
                    # Dependency not in the task list — skip (not a cycle node)
                    continue
                if colour[dep_id] == 1:
                    # Back edge — cycle found. Extract cycle from stack.
                    cycle_start = stack.index(dep_id)
                    cycle = stack[cycle_start:]
                    key = frozenset(cycle)
                    if key not in seen_cycles:
                        seen_cycles.add(key)
                        cycles.append(list(cycle))
                elif colour[dep_id] == 0:
                    dfs(dep_id)
            _ = stack.pop()
            colour[node] = 2

        for task_id in list(self._by_id):
            if colour[task_id] == 0:
                dfs(task_id)

        return cycles

    def get_blocked_tasks(self) -> list[tuple[Task, list[str]]]:
        """Return tasks that are blocked by unsatisfied dependencies.

        A task is *blocked* when it is in ``not-started`` status and has at
        least one dependency that is not in a successful status.  Dependencies
        that reference task IDs absent from the plan are also treated as
        unsatisfied and reported.

        Note: tasks that are already in ``in-progress`` or ``blocked`` status
        are excluded — this method reports tasks that *cannot start* due to
        unmet prerequisites.

        Returns:
            List of ``(task, missing_dep_ids)`` tuples where ``missing_dep_ids``
             are the IDs of dependencies not yet in a successful status.
        """
        result: list[tuple[Task, list[str]]] = []
        for task in self._tasks:
            if task.status != TaskStatus.NOT_STARTED:
                continue
            unsatisfied = self._unsatisfied_deps(task)
            if unsatisfied:
                result.append((task, unsatisfied))
        return result

    def mark_downstream_skipped(self, failed_task_id: str) -> list[str]:
        """Mark transitive downstream tasks as skipped after an upstream failure.

        Performs a forward DFS from *failed_task_id* through the dependency graph
        (following edges in the direction "task → tasks that depend on it").
        Every reachable task still in ``not-started`` is transitioned in-memory to:

        - ``status = "skipped"``
        - ``reason = "skipped: upstream {failed_task_id} failed"``

        Args:
            failed_task_id: ID of the task that has just transitioned to FAILED.

        Returns:
            List of task IDs (in DFS discovery order) newly marked ``skipped``.
            Empty list when the failed task has no downstream dependents, or all
            downstream tasks were already non-actionable.
        """
        # Build reverse adjacency: task_id -> list of task_ids that depend on it.
        reverse: dict[str, list[str]] = {t.id: [] for t in self._tasks}
        for t in self._tasks:
            for dep_id in t.dependencies:
                if dep_id in reverse:
                    reverse[dep_id].append(t.id)

        skipped: list[str] = []
        visited: set[str] = set()

        def _dfs(node_id: str) -> None:
            for dependent_id in reverse.get(node_id, []):
                if dependent_id in visited:
                    continue
                visited.add(dependent_id)
                dep_task = self._by_id.get(dependent_id)
                if dep_task is not None:
                    if dep_task.status == TaskStatus.NOT_STARTED:
                        dep_task.status = TaskStatus.SKIPPED
                        dep_task.reason = f"skipped: upstream {failed_task_id} failed"
                        skipped.append(dependent_id)
                    _dfs(dependent_id)

        _dfs(failed_task_id)
        return skipped

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dep_is_successful(self, dep_id: str) -> bool:
        """Return True when *dep_id* exists and is in a successful status.

        Args:
            dep_id: Task ID of the dependency to check.

        Returns:
            ``True`` if the dependency exists and its status is in
            ``SUCCESSFUL_STATUSES``, ``False`` if the dependency is missing,
            not yet terminal, or in a FAILED status (which must not unblock
            downstream tasks — those should be auto-skipped instead).
        """
        dep_task = self._by_id.get(dep_id)
        if dep_task is None:
            return False
        return dep_task.status in SUCCESSFUL_STATUSES

    def _all_deps_successful(self, task: Task) -> bool:
        """Return True when all of *task*'s dependencies are in successful status.

        Args:
            task: The task whose dependencies are checked.

        Returns:
            ``True`` when every dependency ID resolves to a task in a successful
            status.  ``True`` for tasks with no dependencies.
        """
        return all(self._dep_is_successful(dep_id) for dep_id in task.dependencies)

    def _unsatisfied_deps(self, task: Task) -> list[str]:
        """Return dependency IDs that are not yet in a successful status.

        Args:
            task: The task whose dependencies are examined.

        Returns:
            List of dependency IDs (may include IDs absent from the plan)
             that are not in a successful status.
        """
        return [dep_id for dep_id in task.dependencies if not self._dep_is_successful(dep_id)]


class BookendValidator:
    """Validator for T0/TN bookend task structural constraints within a plan.

    Validates that bookend tasks are configured correctly relative to each
    other and the plan's structured acceptance criteria.  Plans without
    bookend tasks and without structured criteria always pass validation.

    Args:
        plan: The plan to validate.
    """

    def __init__(self, plan: Plan) -> None:
        """Initialise the validator with a plan.

        Args:
            plan: The plan whose bookend tasks are to be validated.
        """
        self._plan: Plan = plan

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_t0_task(self) -> Task | None:
        """Return the T0 baseline bookend task, or None if absent.

        Returns:
            The task whose ``bookend_type`` is ``BookendType.T0_BASELINE``, or ``None``.
        """
        for task in self._plan.tasks:
            if task.bookend_type == BookendType.T0_BASELINE:
                return task
        return None

    def get_tn_task(self) -> Task | None:
        """Return the TN verification bookend task, or None if absent.

        Returns:
            The task whose ``bookend_type`` is ``BookendType.TN_VERIFICATION``, or ``None``.
        """
        for task in self._plan.tasks:
            if task.bookend_type == BookendType.TN_VERIFICATION:
                return task
        return None

    def get_implementation_task_ids(self) -> list[str]:
        """Return task IDs of all non-bookend tasks in the plan.

        Returns:
            Sorted list of task IDs whose ``is_bookend`` field is ``False``.
        """
        return sorted([t.id for t in self._plan.tasks if not t.is_bookend], key=_task_id_sort_key)

    def validate(self) -> list[str]:
        """Validate bookend structural constraints and return error strings.

        Checks:

        1. At most one T0 per plan (``bookend_type == "t0-baseline"``).
        2. At most one TN per plan (``bookend_type == "tn-verification"``).
        3. T0 must have an empty ``dependencies`` list.
        4. TN must depend on every non-bookend task ID.
        5. If ``acceptance_criteria_structured`` is non-empty, both T0 and TN
           must exist.

        Plans without bookend tasks and without structured criteria produce
        no errors.

        Returns:
            List of human-readable error strings.  An empty list means the
            plan is valid with respect to bookend constraints.
        """
        errors: list[str] = []

        t0_tasks = [t for t in self._plan.tasks if t.bookend_type == BookendType.T0_BASELINE]
        tn_tasks = [t for t in self._plan.tasks if t.bookend_type == BookendType.TN_VERIFICATION]

        # Rule 1: at most one T0
        if len(t0_tasks) > 1:
            ids = ", ".join(t.id for t in t0_tasks)
            errors.append(f"Multiple T0 baseline tasks found ({ids}); only one is allowed per plan.")

        # Rule 2: at most one TN
        if len(tn_tasks) > 1:
            ids = ", ".join(t.id for t in tn_tasks)
            errors.append(f"Multiple TN verification tasks found ({ids}); only one is allowed per plan.")

        t0 = t0_tasks[0] if t0_tasks else None
        tn = tn_tasks[0] if tn_tasks else None

        # Rule 3: T0 must have no dependencies
        if t0 is not None and t0.dependencies:
            dep_list = ", ".join(t0.dependencies)
            errors.append(f"T0 task '{t0.id}' must have an empty dependencies list, but depends on: {dep_list}.")

        # Rule 4: TN must depend on all non-bookend tasks
        if tn is not None:
            impl_ids = set(self.get_implementation_task_ids())
            tn_deps = set(tn.dependencies)
            missing = impl_ids - tn_deps
            if missing:
                missing_list = ", ".join(sorted(missing, key=_task_id_sort_key))
                errors.append(
                    f"TN task '{tn.id}' must depend on all non-bookend tasks, but is missing: {missing_list}."
                )

        # Rule 5: structured criteria require both bookend tasks
        if self._plan.acceptance_criteria_structured:
            if t0 is None:
                errors.append(
                    "Plan has acceptance-criteria-structured but no T0 baseline task (bookend_type='t0-baseline'). Add a T0 task or remove structured criteria."
                )
            if tn is None:
                errors.append(
                    "Plan has acceptance-criteria-structured but no TN verification task (bookend_type='tn-verification'). Add a TN task or remove structured criteria."
                )

        return errors
