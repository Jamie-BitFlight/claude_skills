"""Unit tests for BeadsTaskProvider.

All tests mock the bd CLI via _FakeBdRunner — no live bd binary required.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from sam_schema.core.action_models import TaskDefinition
from sam_schema.core.backends.beads import BeadsTaskProvider
from sam_schema.core.exceptions import DocumentNotFoundError, PlanNotFoundError, TaskNotFoundError, TaskValidationError
from sam_schema.core.models import AcceptanceCriterion, PlanState

from .conftest import _FakeBdRunner, _ListParentBdRunner, _ListShowBdRunner, make_task_record

if TYPE_CHECKING:
    from sam_schema.core.task_backend_types import DocumentHandle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_def(
    task_id: str, title: str, deps: list[str] | None = None, priority: int = 2, description: str = ""
) -> TaskDefinition:
    return TaskDefinition.model_validate({
        "id": task_id,
        "title": title,
        "status": "not-started",
        "priority": priority,
        "complexity": "low",
        "body": "",
        "description": description,
        "dependencies": deps or [],
        "agent": None,
        "skills": [],
    })


# ---------------------------------------------------------------------------
# create_plan
# ---------------------------------------------------------------------------


class TestCreatePlan:
    def test_creates_epic_and_indexes_plan(self, fake_runner: _FakeBdRunner) -> None:
        """create_plan must create exactly one epic and register it in bd remember."""
        provider = BeadsTaskProvider(runner=fake_runner)
        tasks = [_task_def("T01", "Do something")]
        result = provider.create_plan("my-slug", "Goal text", tasks)

        plan_id = result["plan_id"]
        assert plan_id.startswith("P")

        # The epic was created
        epics = [i for i in fake_runner._issues.values() if i["type"] == "epic"]
        assert len(epics) == 1
        epic = epics[0]
        assert epic["title"] == "my-slug"
        assert epic["description"] == "Goal text"

        # Plan index written to bd remember
        idx_key = f"dh.plan-index.{plan_id}"
        assert idx_key in fake_runner._memory
        assert fake_runner._memory[idx_key] == epic["id"]

    def test_creates_child_task_issue(self, fake_runner: _FakeBdRunner) -> None:
        """Each task in the plan must become a child issue with --parent set."""
        provider = BeadsTaskProvider(runner=fake_runner)
        tasks = [_task_def("T01", "Write tests")]
        result = provider.create_plan("slug", "goal", tasks)

        # Exactly one child task issue
        task_issues = [i for i in fake_runner._issues.values() if i["type"] == "task"]
        assert len(task_issues) == 1

        # Task index entry was written
        plan_id = result["plan_id"]
        task_idx_key = f"dh.task-index.{plan_id}.T01"
        assert task_idx_key in fake_runner._memory
        payload = json.loads(fake_runner._memory[task_idx_key])
        assert payload["bd_id"] == task_issues[0]["id"]

    def test_returns_plan_data_with_tasks(self, fake_runner: _FakeBdRunner) -> None:
        """create_plan must return PlanData with tasks list."""
        provider = BeadsTaskProvider(runner=fake_runner)
        tasks = [_task_def("T01", "First"), _task_def("T02", "Second")]
        result = provider.create_plan("slug", "goal", tasks)

        assert result["feature"] == "slug"
        assert result["goal"] == "goal"
        assert len(result["tasks"]) == 2

    def test_raises_task_validation_error_on_duplicate_id(self, fake_runner: _FakeBdRunner) -> None:
        """create_plan must raise TaskValidationError when two tasks share the same ID."""
        provider = BeadsTaskProvider(runner=fake_runner)
        tasks = [_task_def("T01", "First"), _task_def("T01", "Duplicate")]
        with pytest.raises(TaskValidationError):
            provider.create_plan("slug", "goal", tasks)

    def test_context_appended_to_description(self, fake_runner: _FakeBdRunner) -> None:
        """Context string must appear in epic description when provided."""
        provider = BeadsTaskProvider(runner=fake_runner)
        provider.create_plan("slug", "goal", [], context="Extra context")

        epics = [i for i in fake_runner._issues.values() if i["type"] == "epic"]
        assert len(epics) == 1
        desc = epics[0]["description"] or ""
        assert "Extra context" in desc

    def test_create_plan_with_tasks_stores_ready_state(self, fake_runner: _FakeBdRunner) -> None:
        """When tasks are present at creation, the plan state is stored as ready."""
        provider = BeadsTaskProvider(runner=fake_runner)
        result = provider.create_plan("slug", "goal", [_task_def("T01", "Task")])

        plan_id = result["plan_id"]
        assert fake_runner._memory[f"dh.plan-state.{plan_id}"] == PlanState.READY.value

    def test_create_plan_without_tasks_stores_drafting_state(self, fake_runner: _FakeBdRunner) -> None:
        """An empty task list stores the plan as drafting for the incremental workflow."""
        provider = BeadsTaskProvider(runner=fake_runner)
        result = provider.create_plan("slug", "goal", [])

        plan_id = result["plan_id"]
        assert fake_runner._memory[f"dh.plan-state.{plan_id}"] == PlanState.DRAFTING.value

    def test_create_plan_stores_structured_criteria(self, fake_runner: _FakeBdRunner) -> None:
        """Structured acceptance criteria are persisted in bd remember."""
        provider = BeadsTaskProvider(runner=fake_runner)
        criterion = AcceptanceCriterion(criterion_id="AC-1", check_command="true")
        result = provider.create_plan("slug", "goal", [], acceptance_criteria_structured=[criterion])

        plan_id = result["plan_id"]
        stored = json.loads(fake_runner._memory[f"dh.plan-criteria.{plan_id}"])
        assert len(stored) == 1
        assert stored[0]["criterion_id"] == "AC-1"


# ---------------------------------------------------------------------------
# read_plan
# ---------------------------------------------------------------------------


class TestReadPlan:
    def test_raises_plan_not_found_for_unknown_plan(self, fake_runner: _FakeBdRunner) -> None:
        """read_plan must raise PlanNotFoundError for an unregistered plan."""
        provider = BeadsTaskProvider(runner=fake_runner)
        with pytest.raises(PlanNotFoundError):
            provider.read_plan("Punknown")

    def test_reads_plan_and_tasks(self, fake_runner: _FakeBdRunner) -> None:
        """read_plan must reconstruct PlanData from the epic and task issues."""
        runner = fake_runner
        provider = BeadsTaskProvider(runner=runner)
        tasks = [_task_def("T01", "Alpha"), _task_def("T02", "Beta")]
        created = provider.create_plan("test-plan", "Test goal", tasks)
        plan_id = created["plan_id"]

        plan = provider.read_plan(plan_id)
        assert plan["plan_id"] == plan_id
        assert plan["feature"] == "test-plan"
        assert len(plan["tasks"]) == 2

    def test_read_plan_passes_all_flag_to_list(self, plan_id_and_list_runner: tuple[str, _ListParentBdRunner]) -> None:
        """read_plan must pass ``--all`` to ``bd list --parent`` so closed tasks are included.

        Regression test for BUG-B: the original call omitted ``--all``, which
        caused ``bd list --parent`` to exclude closed/completed child issues.
        This meant ``sam_plan status`` reported incorrect completion percentages
        after tasks were closed.
        """
        plan_id, runner = plan_id_and_list_runner
        epic_id = runner._memory[f"dh.plan-index.{plan_id}"]
        make_task_record(runner, plan_id, "T01", status="closed", parent_id=epic_id)
        runner.json_calls.clear()

        provider = BeadsTaskProvider(runner=runner)
        provider.read_plan(plan_id)

        list_calls = [c for c in runner.json_calls if c[0] == "list"]
        assert len(list_calls) == 1
        assert "--all" in list_calls[0], (
            "read_plan must pass --all to bd list --parent so closed tasks are included; "
            "without --all, completed tasks are excluded and completion_pct is always 0%"
        )

    def test_read_plan_restores_drafting_state(self, fake_runner: _FakeBdRunner) -> None:
        """read_plan must return the persisted drafting state, not default to ready."""
        provider = BeadsTaskProvider(runner=fake_runner)
        created = provider.create_plan("slug", "goal", [])
        plan_id = created["plan_id"]

        plan = provider.read_plan(plan_id)
        assert plan["state"] == PlanState.DRAFTING

    def test_read_plan_restores_structured_criteria(self, fake_runner: _FakeBdRunner) -> None:
        """read_plan must include persisted structured acceptance criteria."""
        provider = BeadsTaskProvider(runner=fake_runner)
        criterion = AcceptanceCriterion(criterion_id="AC-1", check_command="true")
        created = provider.create_plan("slug", "goal", [], acceptance_criteria_structured=[criterion])
        plan_id = created["plan_id"]

        plan = provider.read_plan(plan_id)
        assert "acceptance_criteria_structured" in plan
        assert len(plan["acceptance_criteria_structured"]) == 1
        assert plan["acceptance_criteria_structured"][0]["criterion_id"] == "AC-1"

    def test_read_plan_restores_dependencies(self, fake_runner: _FakeBdRunner) -> None:
        """read_plan must reconstruct task dependencies from the task index.

        Regression test for the Codex review finding that read_plan rebuilt
        every child with dependencies=[], which made BookendValidator reject
        a valid T0 -> T1 -> TN plan at finalize time.
        """
        provider = BeadsTaskProvider(runner=fake_runner)
        tasks = [
            _task_def("T0", "Baseline"),
            _task_def("T1", "Impl", deps=["T0"]),
            _task_def("T2", "Verify", deps=["T1"]),
        ]
        created = provider.create_plan("slug", "goal", tasks)
        plan_id = created["plan_id"]

        plan = provider.read_plan(plan_id)
        deps_by_id = {t["id"]: t["dependencies"] for t in plan["tasks"]}
        assert deps_by_id["T0"] == []
        assert deps_by_id["T1"] == ["T0"]
        assert deps_by_id["T2"] == ["T1"]

    def test_append_task_persists_dependencies(self, fake_runner: _FakeBdRunner) -> None:
        """append_task must index and wire the new task's dependencies."""
        provider = BeadsTaskProvider(runner=fake_runner)
        created = provider.create_plan("slug", "goal", [_task_def("T0", "Baseline")])
        plan_id = created["plan_id"]

        provider.append_task(plan_id, _task_def("T1", "Impl", deps=["T0"]))

        plan = provider.read_plan(plan_id)
        deps_by_id = {t["id"]: t["dependencies"] for t in plan["tasks"]}
        assert deps_by_id["T1"] == ["T0"]
        assert any(c[:2] == ["dep", "add"] for c in fake_runner.text_calls)


class TestUpdatePlanFields:
    def test_update_persists_structured_criteria(self, fake_runner: _FakeBdRunner) -> None:
        """update_plan_fields must persist acceptance-criteria-structured.

        Regression test for the Codex review finding that the update path
        ignored the criteria key, letting a plan add criteria post-create
        and finalize without T0/TN.
        """
        provider = BeadsTaskProvider(runner=fake_runner)
        created = provider.create_plan("slug", "goal", [])
        plan_id = created["plan_id"]

        criterion = AcceptanceCriterion(criterion_id="AC-2", check_command="true")
        provider.update_plan_fields(
            plan_id, set_fields={"acceptance-criteria-structured": [criterion.model_dump(mode="json", by_alias=False)]}
        )

        plan = provider.read_plan(plan_id)
        assert "acceptance_criteria_structured" in plan
        assert len(plan["acceptance_criteria_structured"]) == 1
        assert plan["acceptance_criteria_structured"][0]["criterion_id"] == "AC-2"

    def test_update_with_empty_criteria_clears_stored_criteria(self, fake_runner: _FakeBdRunner) -> None:
        """update_plan_fields with an empty criteria list clears the stored value."""
        provider = BeadsTaskProvider(runner=fake_runner)
        criterion = AcceptanceCriterion(criterion_id="AC-1", check_command="true")
        created = provider.create_plan("slug", "goal", [], acceptance_criteria_structured=[criterion])
        plan_id = created["plan_id"]

        provider.update_plan_fields(plan_id, set_fields={"acceptance-criteria-structured": []})

        plan = provider.read_plan(plan_id)
        assert not plan.get("acceptance_criteria_structured")


# ---------------------------------------------------------------------------
# finalize_plan
# ---------------------------------------------------------------------------


class TestFinalizePlan:
    def test_finalize_plan_transitions_state_to_ready(self, fake_runner: _FakeBdRunner) -> None:
        """finalize_plan must update the persisted plan state from drafting to ready."""
        provider = BeadsTaskProvider(runner=fake_runner)
        created = provider.create_plan("slug", "goal", [])
        plan_id = created["plan_id"]
        assert fake_runner._memory[f"dh.plan-state.{plan_id}"] == PlanState.DRAFTING.value

        result = provider.finalize_plan(plan_id)

        assert result["state"] == PlanState.READY
        assert fake_runner._memory[f"dh.plan-state.{plan_id}"] == PlanState.READY.value


# ---------------------------------------------------------------------------
# bd show list-wrapping — parse_show_issue call sites
# ---------------------------------------------------------------------------


class TestBdShowListWrapping:
    """Verify all bd show call sites handle the real ``[{...}]`` JSON shape.

    The real ``bd`` CLI wraps ``bd show <id> --json`` output in a single-element
    list ``[{...}]``.  :func:`~backlog_core.backends.beads_models.parse_show_issue`
    unwraps this transparently.  These tests use :class:`_ListShowBdRunner` to
    reproduce the actual CLI shape and assert that each provider method returns
    correct results rather than crashing with a ``ValidationError``.
    """

    def test_list_plans_handles_list_wrapped_show(self, list_show_runner: _ListShowBdRunner) -> None:
        """list_plans must succeed when bd show returns [{...}] for the epic."""
        runner = list_show_runner
        plan_id = "Plistshow01"
        epic_id = runner._new_id()
        runner._issues[epic_id] = runner._make_issue(epic_id, "my-feature", issue_type="epic", description="goal")
        runner._memory[f"dh.plan-index.{plan_id}"] = epic_id
        make_task_record(runner, plan_id, "T01", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        summaries = provider.list_plans()

        assert len(summaries) == 1
        assert summaries[0]["plan_id"] == plan_id
        assert summaries[0]["feature"] == "my-feature"

    def test_read_plan_handles_list_wrapped_show(self, list_show_runner: _ListShowBdRunner) -> None:
        """read_plan must succeed when bd show returns [{...}] for the epic."""
        runner = list_show_runner
        provider = BeadsTaskProvider(runner=runner)
        tasks = [_task_def("T01", "First task")]
        created = provider.create_plan("lw-plan", "goal", tasks)
        plan_id = created["plan_id"]

        plan = provider.read_plan(plan_id)

        assert plan["plan_id"] == plan_id
        assert plan["feature"] == "lw-plan"

    def test_read_task_handles_list_wrapped_show(self, list_show_runner: _ListShowBdRunner) -> None:
        """read_task must succeed when bd show returns [{...}]."""
        runner = list_show_runner
        provider = BeadsTaskProvider(runner=runner)
        created = provider.create_plan("lw-task-plan", "goal", [_task_def("T01", "Single task")])
        plan_id = created["plan_id"]

        task_data = provider.read_task(plan_id, "T01")

        assert task_data["id"] == "T01"
        assert task_data["title"] == "Single task"

    def test_issue_type_field_accepted_via_alias(self, list_show_runner: _ListShowBdRunner) -> None:
        """BeadsIssueRaw must accept 'issue_type' as an alias for 'type'.

        Reproduces the ValidationError reported when TASKBACKEND=beads:
        bd list --json returns dicts with 'issue_type' (not 'type') which
        previously caused a ValidationError before AliasChoices was added.
        """
        from backlog_core.backends.beads_models import parse_issue

        raw_with_issue_type = {"id": "bd-a1b2", "title": "Test", "status": "open", "issue_type": "task", "priority": 2}

        # Must not raise ValidationError
        issue = parse_issue(raw_with_issue_type)
        assert issue.type.value == "task"


# ---------------------------------------------------------------------------
# claim_task
# ---------------------------------------------------------------------------


class TestClaimTask:
    def test_claim_succeeds_on_open_task(self, fake_runner: _FakeBdRunner) -> None:
        """claim_task must return True and mark issue as hooked when task is open."""
        plan_id, runner = "Pclaim01", fake_runner
        runner._memory["dh.plan-index.Pclaim01"] = runner._new_id()
        epic_id = runner._memory["dh.plan-index.Pclaim01"]
        runner._issues[epic_id] = runner._make_issue(epic_id, "epic", issue_type="epic")
        bd_id = make_task_record(runner, plan_id, "T01", status="open", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        result = provider.claim_task(plan_id, "T01")

        assert result is True
        assert runner._issues[bd_id]["status"] == "hooked"

    def test_claim_returns_false_when_already_claimed(self, fake_runner: _FakeBdRunner) -> None:
        """claim_task must return False when the issue is already claimed (hooked)."""
        plan_id = "Pclaim02"
        runner = fake_runner
        epic_id = runner._new_id()
        runner._issues[epic_id] = runner._make_issue(epic_id, "epic", issue_type="epic")
        runner._memory[f"dh.plan-index.{plan_id}"] = epic_id
        make_task_record(runner, plan_id, "T01", status="hooked", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        result = provider.claim_task(plan_id, "T01")

        assert result is False

    def test_claim_raises_task_not_found(self, fake_runner: _FakeBdRunner) -> None:
        """claim_task must raise TaskNotFoundError for an unregistered task ID."""
        plan_id = "Pclaim03"
        runner = fake_runner
        epic_id = runner._new_id()
        runner._issues[epic_id] = runner._make_issue(epic_id, "epic", issue_type="epic")
        runner._memory[f"dh.plan-index.{plan_id}"] = epic_id

        provider = BeadsTaskProvider(runner=runner)
        with pytest.raises(TaskNotFoundError):
            provider.claim_task(plan_id, "T99")

    def test_claim_uses_update_not_claim_command(self, fake_runner: _FakeBdRunner) -> None:
        """claim_task must call ``bd update --claim`` — not the non-existent ``bd claim``.

        Regression test for BUG-A: the original code called run_json(["claim", id])
        which does not exist in bd 1.0.4.  The correct invocation routes through
        run_text(["update", id, "--claim"]).
        """
        plan_id = "Pclaim04"
        runner = fake_runner
        epic_id = runner._new_id()
        runner._issues[epic_id] = runner._make_issue(epic_id, "epic", issue_type="epic")
        runner._memory[f"dh.plan-index.{plan_id}"] = epic_id
        bd_id = make_task_record(runner, plan_id, "T01", status="open", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        provider.claim_task(plan_id, "T01")

        # Must NOT appear in json_calls (bd claim does not exist in bd 1.0.4)
        claim_json_calls = [c for c in runner.json_calls if c and c[0] == "claim"]
        assert claim_json_calls == [], (
            "claim_task must not call run_json(['claim', ...]) — bd claim does not exist in bd 1.0.4"
        )

        # Must appear in text_calls as bd update --claim
        update_claim_calls = [c for c in runner.text_calls if c[0] == "update" and "--claim" in c]
        assert len(update_claim_calls) == 1
        assert bd_id in update_claim_calls[0]


# ---------------------------------------------------------------------------
# update_task_status
# ---------------------------------------------------------------------------


class TestUpdateTaskStatus:
    def test_update_status_valid(self, fake_runner: _FakeBdRunner) -> None:
        """update_task_status must call bd update --status with mapped value."""
        plan_id = "Pstat01"
        runner = fake_runner
        epic_id = runner._new_id()
        runner._issues[epic_id] = runner._make_issue(epic_id, "epic", issue_type="epic")
        runner._memory[f"dh.plan-index.{plan_id}"] = epic_id
        bd_id = make_task_record(runner, plan_id, "T01", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        provider.update_task_status(plan_id, "T01", "complete")

        # Check that bd update --status closed was called
        update_calls = [c for c in runner.text_calls if c[0] == "update" and "--status" in c]
        assert any(bd_id in c and "closed" in c for c in update_calls)

    def test_update_status_invalid_raises(self, fake_runner: _FakeBdRunner) -> None:
        """update_task_status must raise TaskValidationError for unknown status."""
        plan_id = "Pstat02"
        runner = fake_runner
        epic_id = runner._new_id()
        runner._issues[epic_id] = runner._make_issue(epic_id, "epic", issue_type="epic")
        runner._memory[f"dh.plan-index.{plan_id}"] = epic_id
        make_task_record(runner, plan_id, "T01", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        with pytest.raises(TaskValidationError):
            provider.update_task_status(plan_id, "T01", "bogus-status")


# ---------------------------------------------------------------------------
# store_document / read_document
# ---------------------------------------------------------------------------


class TestDocumentRoundTrip:
    def test_store_and_read_plan_level_document(self, fake_runner: _FakeBdRunner) -> None:
        """store_document followed by read_document must return the same content."""
        runner = fake_runner
        provider = BeadsTaskProvider(runner=runner)
        tasks = [_task_def("T01", "task")]
        created = provider.create_plan("doc-plan", "goal", tasks)
        plan_id = created["plan_id"]

        handle = provider.store_document(plan_id, None, "architect", "spec", "My Doc", "# Content here")

        assert handle["content_ref"].startswith("bd://")
        doc_data = provider.read_document(handle)
        assert doc_data["content"] == "# Content here"
        assert doc_data["title"] == "My Doc"

    def test_store_task_level_document(self, fake_runner: _FakeBdRunner) -> None:
        """store_document at task level must embed content in task issue notes."""
        runner = fake_runner
        provider = BeadsTaskProvider(runner=runner)
        tasks = [_task_def("T01", "task")]
        created = provider.create_plan("tdoc-plan", "goal", tasks)
        plan_id = created["plan_id"]

        handle = provider.store_document(plan_id, "T01", "stage", "type", "T Title", "task content")
        doc = provider.read_document(handle)
        assert "task content" in doc["content"]

    def test_read_document_raises_for_missing_ref(self, fake_runner: _FakeBdRunner) -> None:
        """read_document must raise DocumentNotFoundError for a made-up content_ref."""
        runner = fake_runner
        provider = BeadsTaskProvider(runner=runner)
        tasks = [_task_def("T01", "task")]
        created = provider.create_plan("missing-plan", "goal", tasks)
        plan_id = created["plan_id"]
        # Register valid plan so epic lookup succeeds, but ref won't be in notes
        fake_handle: DocumentHandle = {
            "content_ref": f"bd://{plan_id}/{plan_id}/stage/type/deadbeef",
            "owner_type": "plan",
            "owner_id": plan_id,
            "stage": "stage",
            "doc_type": "type",
            "title": "Missing",
            "fmt": "md",
        }
        with pytest.raises(DocumentNotFoundError):
            provider.read_document(fake_handle)


# ---------------------------------------------------------------------------
# append_task
# ---------------------------------------------------------------------------


class TestGetPlanStatus:
    def test_completion_pct_includes_closed_tasks(
        self, plan_id_and_list_runner: tuple[str, _ListParentBdRunner]
    ) -> None:
        """get_plan_status must reflect closed tasks in completion_pct.

        Regression test for BUG-B: without ``--all`` on the ``bd list --parent``
        call, closed issues are excluded from the batch result.  The plan then
        shows 0 tasks and 0% completion even after all work is done.
        """
        plan_id, runner = plan_id_and_list_runner
        epic_id = runner._memory[f"dh.plan-index.{plan_id}"]
        make_task_record(runner, plan_id, "T01", status="closed", parent_id=epic_id)
        make_task_record(runner, plan_id, "T02", status="closed", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        status = provider.get_plan_status(plan_id)

        assert status["total_tasks"] == 2, (
            "Both closed tasks must be visible to get_plan_status; "
            "without --all on bd list --parent, closed tasks are excluded"
        )
        assert status["completion_pct"] == pytest.approx(100.0)

    def test_completion_pct_mixed_open_and_closed(
        self, plan_id_and_list_runner: tuple[str, _ListParentBdRunner]
    ) -> None:
        """get_plan_status must count only closed tasks toward completion_pct."""
        plan_id, runner = plan_id_and_list_runner
        epic_id = runner._memory[f"dh.plan-index.{plan_id}"]
        make_task_record(runner, plan_id, "T01", status="closed", parent_id=epic_id)
        make_task_record(runner, plan_id, "T02", status="open", parent_id=epic_id)

        provider = BeadsTaskProvider(runner=runner)
        status = provider.get_plan_status(plan_id)

        assert status["total_tasks"] == 2
        assert status["completion_pct"] == pytest.approx(50.0)


class TestAppendTask:
    def test_append_task_creates_issue_and_indexes(self, fake_runner: _FakeBdRunner) -> None:
        """append_task must create a new child issue and register it in bd remember."""
        runner = fake_runner
        provider = BeadsTaskProvider(runner=runner)
        created = provider.create_plan("ap-plan", "goal", [])
        plan_id = created["plan_id"]

        new_task = _task_def("T01", "Appended task")
        result = provider.append_task(plan_id, new_task)

        assert result["appended"] is True
        assert result["task_id"] == "T01"
        idx_key = f"dh.task-index.{plan_id}.T01"
        assert idx_key in runner._memory

    def test_append_task_raises_for_duplicate(self, fake_runner: _FakeBdRunner) -> None:
        """append_task must raise TaskValidationError when the task ID already exists."""
        runner = fake_runner
        provider = BeadsTaskProvider(runner=runner)
        created = provider.create_plan("ap-plan2", "goal", [_task_def("T01", "Existing")])
        plan_id = created["plan_id"]

        with pytest.raises(TaskValidationError):
            provider.append_task(plan_id, _task_def("T01", "Duplicate"))
