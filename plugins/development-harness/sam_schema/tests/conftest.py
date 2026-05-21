"""Shared fixtures and test doubles for sam_schema beads backend tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.backends.bd_runner import BdInvocationError, BdNotInstalledError, BdRunner, JsonValue  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Sequence

# ---------------------------------------------------------------------------
# _FakeBdRunner — in-memory bd CLI simulator
# ---------------------------------------------------------------------------


class _FakeBdRunner(BdRunner):
    """In-memory test double for BdRunner.

    Simulates bd CLI operations used by BeadsTaskProvider and
    BeadsContextBackend without calling any subprocess.  State is kept in
    ``_memory`` (bd remember store) and ``_issues`` (created issues by ID).

    All call args are appended to ``json_calls`` and ``text_calls`` for
    assertion in tests.
    """

    def __init__(self) -> None:
        super().__init__()
        self._memory: dict[str, str] = {}
        self._issues: dict[str, dict[str, Any]] = {}
        self._id_counter: int = 1
        self.json_calls: list[list[str]] = []
        self.text_calls: list[list[str]] = []

    def _new_id(self) -> str:
        id_str = f"bd-t{self._id_counter:04d}"
        self._id_counter += 1
        return id_str

    def _make_issue(
        self,
        issue_id: str,
        title: str,
        issue_type: str = "task",
        status: str = "open",
        description: str | None = None,
        priority: int = 2,
        parent: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": issue_id,
            "title": title,
            "status": status,
            "type": issue_type,
            "priority": priority,
            "description": description,
            "notes": notes,
            "metadata": {"parent": parent} if parent else None,
            "labels": None,
            "assignee": None,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "closed_at": None,
        }

    def run_json(self, argv: Sequence[str]) -> JsonValue:
        """Simulate bd commands that produce JSON output."""
        args = list(argv)
        self.json_calls.append(args)

        if not args:
            raise BdInvocationError("No command", args, 1, "", "")

        cmd = args[0]

        if cmd == "create":
            return self._handle_create(args)

        if cmd == "show":
            if len(args) < 2:
                raise BdInvocationError("show requires an ID", args, 1, "", "")
            issue_id = args[1]
            if issue_id not in self._issues:
                raise BdInvocationError(f"Issue not found: {issue_id}", args, 1, "", "")
            return self._issues[issue_id]

        if cmd == "claim":
            if len(args) < 2:
                raise BdInvocationError("claim requires an ID", args, 1, "", "")
            issue_id = args[1]
            if issue_id not in self._issues:
                raise BdInvocationError(f"Issue not found: {issue_id}", args, 1, "", "")
            issue = self._issues[issue_id]
            if issue["status"] not in ("open", "not-started"):
                raise BdInvocationError(f"Cannot claim issue in status {issue['status']!r}", args, 2, "", "")
            issue["status"] = "hooked"
            return issue

        if cmd == "ready":
            # Always raise BdInvocationError: let BeadsTaskProvider fall back to
            # its local dependency-evaluation path, which correctly handles blocked tasks.
            raise BdInvocationError("ready --parent not implemented in test double", args, 1, "", "")

        if cmd == "memories":
            # bd memories --json returns flat dict {key: value, ..., schema_version: 1}
            result: dict[str, Any] = {"schema_version": 1}
            result.update(self._memory)
            return result

        raise BdInvocationError(f"Unhandled json command: {cmd!r}", args, 1, "", "")

    def run_text(self, argv: Sequence[str]) -> str:
        """Simulate bd commands that produce text output."""
        args = list(argv)
        self.text_calls.append(args)

        if not args:
            raise BdInvocationError("No command", args, 1, "", "")

        cmd = args[0]
        match cmd:
            case "remember":
                return self._handle_remember(args)
            case "recall":
                return self._handle_recall(args)
            case "forget":
                return self._handle_forget(args)
            case "update":
                return self._handle_update(args)
            case "dep":
                return ""  # bd dep add <issue> <depends-on> — silently succeed
            case _:
                raise BdInvocationError(f"Unhandled text command: {cmd!r}", args, 1, "", "")

    def _handle_remember(self, args: list[str]) -> str:
        """Handle bd remember <value> --key <key>."""
        key_idx = None
        for i, a in enumerate(args):
            if a == "--key" and i + 1 < len(args):
                key_idx = i
                break
        if key_idx is None:
            raise BdInvocationError("remember requires --key", args, 1, "", "")
        value = args[1]
        key = args[key_idx + 1]
        self._memory[key] = value
        return ""

    def _handle_recall(self, args: list[str]) -> str:
        """Handle bd recall <key>."""
        if len(args) < 2:
            raise BdInvocationError("recall requires a key", args, 1, "", "")
        key = args[1]
        if key not in self._memory:
            raise BdInvocationError(f"Key not found: {key!r}", args, 1, "", "")
        return self._memory[key]

    def _handle_forget(self, args: list[str]) -> str:
        """Handle bd forget <key>."""
        if len(args) < 2:
            raise BdInvocationError("forget requires a key", args, 1, "", "")
        key = args[1]
        if key in self._memory:
            del self._memory[key]
        return ""

    def _handle_update(self, args: list[str]) -> str:
        """Handle bd update <id> [--field value ...]."""
        if len(args) < 2:
            raise BdInvocationError("update requires an ID", args, 1, "", "")
        issue_id = args[1]
        if issue_id not in self._issues:
            raise BdInvocationError(f"Issue not found: {issue_id}", args, 1, "", "")
        issue = self._issues[issue_id]
        # Parse --flag value pairs from remaining args
        rest = args[2:]
        i = 0
        while i < len(rest) - 1:
            flag = rest[i]
            val = rest[i + 1]
            if flag == "--title":
                issue["title"] = val
            elif flag == "--description":
                issue["description"] = val
            elif flag == "--priority":
                issue["priority"] = int(val)
            elif flag == "--notes":
                issue["notes"] = val
            elif flag == "--status":
                issue["status"] = val
            i += 2
        return ""

    def _handle_create(self, args: list[str]) -> dict[str, Any]:
        """Parse bd create args and add to _issues store."""
        issue_type = "task"
        title = ""
        description = None
        priority = 2
        parent_id: str | None = None

        i = 1
        while i < len(args):
            a = args[i]
            if a == "--type" and i + 1 < len(args):
                issue_type = args[i + 1]
                i += 2
            elif a == "--title" and i + 1 < len(args):
                title = args[i + 1]
                i += 2
            elif a == "--description" and i + 1 < len(args):
                description = args[i + 1]
                i += 2
            elif a == "--priority" and i + 1 < len(args):
                priority = int(args[i + 1])
                i += 2
            elif a == "--parent" and i + 1 < len(args):
                parent_id = args[i + 1]
                i += 2
            else:
                i += 1

        new_id = self._new_id()
        issue = self._make_issue(
            new_id, title, issue_type=issue_type, description=description, priority=priority, parent=parent_id
        )
        self._issues[new_id] = issue
        return issue


class _ListParentBdRunner(_FakeBdRunner):
    """``_FakeBdRunner`` variant that also handles ``bd list --parent <id>``.

    The base ``_FakeBdRunner`` only simulates the ``bd`` commands the
    production code currently issues.  Efficiency regression tests for the
    batch-fetch optimisation expect ``read_plan`` to call ``bd list --parent``
    instead of N individual ``bd show`` calls.  This subclass overrides
    :meth:`run_json` to recognise that command, returning the child issues
    whose ``metadata.parent`` matches the requested parent ID.  Every other
    command is delegated to the base implementation.
    """

    def run_json(self, argv: Sequence[str]) -> JsonValue:
        """Handle ``list --parent`` locally; delegate all other commands."""
        args = list(argv)
        if args and args[0] == "list" and "--parent" in args:
            self.json_calls.append(args)
            parent_idx = args.index("--parent")
            parent_id = args[parent_idx + 1]
            return [
                issue
                for issue in self._issues.values()
                if isinstance(issue.get("metadata"), dict) and issue["metadata"].get("parent") == parent_id
            ]
        return super().run_json(argv)


# ---------------------------------------------------------------------------
# Shared pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_runner() -> _FakeBdRunner:
    """Return a fresh _FakeBdRunner instance per test."""
    return _FakeBdRunner()


def _seed_plan(runner: _FakeBdRunner, plan_id: str = "Ptest0001") -> str:
    """Insert an epic for *plan_id* into *runner* and return the epic ID."""
    epic_id = runner._new_id()
    runner._issues[epic_id] = runner._make_issue(epic_id, "my-plan", issue_type="epic")
    runner._memory[f"dh.plan-index.{plan_id}"] = epic_id
    return epic_id


@pytest.fixture
def plan_id_and_runner() -> tuple[str, _FakeBdRunner]:
    """Return a (plan_id, runner) pair where the plan already exists in the runner.

    Useful for tests that need a pre-existing plan without calling create_plan.
    The epic is inserted directly into the runner's issue store.
    """
    runner = _FakeBdRunner()
    plan_id = "Ptest0001"
    _seed_plan(runner, plan_id)
    return plan_id, runner


@pytest.fixture
def plan_id_and_list_runner() -> tuple[str, _ListParentBdRunner]:
    """Return a (plan_id, runner) pair using a runner that handles ``bd list --parent``.

    Identical setup to :func:`plan_id_and_runner` but the runner is a
    :class:`_ListParentBdRunner`, so efficiency tests that exercise the
    batch-fetch ``bd list --parent`` path do not need to monkey-patch
    ``run_json`` on a base ``_FakeBdRunner`` instance.
    """
    runner = _ListParentBdRunner()
    plan_id = "Ptest0001"
    _seed_plan(runner, plan_id)
    return plan_id, runner


def make_task_record(
    runner: _FakeBdRunner,
    plan_id: str,
    task_id: str,
    title: str = "A task",
    status: str = "open",
    parent_id: str | None = None,
) -> str:
    """Add a task issue to runner._issues and write it to the task index.

    Returns the generated bd_id for the task.
    """
    bd_id = runner._new_id()
    runner._issues[bd_id] = runner._make_issue(bd_id, title, status=status, parent=parent_id)
    payload = json.dumps({"bd_id": bd_id, "is_bookend": False, "bookend_type": None})
    runner._memory[f"dh.task-index.{plan_id}.{task_id}"] = payload
    return bd_id
