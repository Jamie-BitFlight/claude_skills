"""Tests for ``output_json``'s handling of nested Pydantic models.

Tests: ``output_json`` serializes a Pydantic ``BaseModel`` nested anywhere
inside a plain ``dict``/list result — not just a bare top-level model or a
list whose every element is a model — as a real JSON object with its fields
individually addressable, never as a Python ``repr()`` string.

How: Call ``output_json`` directly with a locally defined ``BaseModel`` that
mirrors the shape reported in the PR #3564 Codex review finding
(``backlog_core.operations.CommentListEntry`` nested inside
``ListCommentsResult``'s mapping-valued ``comments`` list) and assert on the JSON parsed
back from stdout.

Why: ``output_json`` previously special-cased only two shapes — a bare
``BaseModel`` and a list where *every* element is a ``BaseModel`` — and fell
back to ``json.dumps(data, default=str)`` for anything else. A ``dict``
result (the shape every ``operations.py`` function returns) carrying a
``BaseModel`` inside a nested list took that fallback path, and ``str()`` on
an unhandled ``BaseModel`` produces its ``repr()`` (e.g. ``"id='IC_1'
database_id=123 ..."``), not a JSON object — breaking the CLI wire type and
making fields like ``database_id`` unreachable to a programmatic JSON
consumer. See PR #3564 review thread and
``backlog_core/operations.py::list_comments``/``ListCommentsResult`` for the
real-world case this regression-guards.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from backlog_core.operations import CommentListEntry, ListCommentsResult
from pydantic import BaseModel, ConfigDict

from sam_schema.cli_output import output_json


class _CommentEntryLike(BaseModel):
    """Mirrors ``backlog_core.operations.CommentListEntry``'s shape.

    Defined locally rather than imported so this regression test exercises
    ``output_json`` as a generic serialization boundary, independent of
    ``operations.py``'s internal model definition.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    id: str
    database_id: int | None
    author: str
    preview: str


class TestOutputJsonNestedModels:
    """A ``BaseModel`` nested inside a plain result serializes as an object."""

    def test_model_nested_in_dict_list_serializes_as_json_objects(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The PR #3564 regression shape: ``{"comments": [Model, Model]}``.

        Tests: A ``TypedDict``-shaped result (a plain ``dict`` at runtime)
        whose ``comments`` key holds a list of ``BaseModel`` instances
        serializes each entry as a JSON object, not a string.
        How: Build a result dict shaped exactly like
        ``ListCommentsResult`` and pass it to ``output_json``.
        Why: This is the literal shape ``sam backlog comments`` emits;
        before the fix, ``json.dumps(..., default=str)`` stringified each
        entry via ``repr()``.
        """
        result = {
            "comments": [
                _CommentEntryLike(id="IC_1", database_id=123, author="alice", preview="hello"),
                _CommentEntryLike(id="IC_2", database_id=456, author="bob", preview="world"),
            ],
            "count": 2,
            "has_more": False,
            "messages": [],
            "warnings": [],
            "errors": [],
        }

        output_json(result)

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["comments"][0] == {"id": "IC_1", "database_id": 123, "author": "alice", "preview": "hello"}
        assert parsed["comments"][1]["database_id"] == 456

    def test_comment_list_result_serializes_entries_as_objects(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The public comment-list result remains structured at the CLI boundary."""
        result = ListCommentsResult(
            comments=[
                CommentListEntry(
                    id="IC_1",
                    database_id=123,
                    author="alice",
                    created_at="2026-09-16T00:00:00Z",
                    updated_at="2026-09-16T00:00:00Z",
                    preview="hello",
                )
            ],
            count=1,
            has_more=False,
            messages=[],
            warnings=[],
            errors=[],
        )

        output_json(result)

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["comments"][0]["database_id"] == 123
        assert isinstance(parsed["comments"][0], dict)

    def test_database_id_is_an_int_not_embedded_in_a_repr_string(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``database_id`` is reachable as ``comments[0]["database_id"]``.

        Tests: The exact programmatic-consumer failure mode from the
        Codex finding — ``database_id`` must be a top-level JSON field on
        each comment object, not a substring of a stringified model.
        How: Parse the emitted JSON and access the field by key.
        Why: Feature #3546's goal (reachability of ``database_id`` through
        ``list_comments`` -> ``read_comment``) requires this field to
        survive the CLI JSON boundary intact.
        """
        result = {"comments": [_CommentEntryLike(id="IC_1", database_id=789, author="alice", preview="hi")]}

        output_json(result)

        parsed = json.loads(capsys.readouterr().out)
        assert isinstance(parsed["comments"][0]["database_id"], int)
        assert parsed["comments"][0]["database_id"] == 789

    def test_exclude_none_propagates_to_nested_models(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``exclude_none`` applies to nested models, not just the top level.

        Tests: A ``None`` field on a nested model is omitted by default,
        matching the top-level-model behavior already documented for
        ``output_json``.
        How: Nest a model with ``database_id=None`` and check the key is
        absent from the parsed JSON object.
        Why: Consistent ``exclude_none`` semantics between a bare model and
        a nested one avoids surprising callers who rely on the documented
        default.
        """
        result = {"comments": [_CommentEntryLike(id="IC_1", database_id=None, author="alice", preview="hi")]}

        output_json(result)

        parsed = json.loads(capsys.readouterr().out)
        assert "database_id" not in parsed["comments"][0]

    def test_exclude_none_false_keeps_nested_null_fields(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``exclude_none=False`` keeps an explicit ``null`` on a nested model.

        Tests: The opt-out path (used by ``cli_active_task.py`` for
        ``active_task: null``) also reaches nested models.
        How: Pass ``exclude_none=False`` with a nested ``None`` field.
        Why: A caller that explicitly asked for ``null`` visibility should
        get it consistently, not just at the top level.
        """
        result = {"comments": [_CommentEntryLike(id="IC_1", database_id=None, author="alice", preview="hi")]}

        output_json(result, exclude_none=False)

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["comments"][0]["database_id"] is None

    def test_bare_top_level_model_still_uses_fast_path(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A bare top-level ``BaseModel`` is unaffected by the fix.

        Tests: Regression guard — the pre-existing fast path
        (``model_dump_json``) for a single top-level model still produces
        the same JSON shape.
        How: Pass a bare model instance directly.
        Why: Every other ``sam`` command that returns a single Pydantic
        result model (e.g. ``sam_plan.py``) must keep working unchanged.
        """
        model = _CommentEntryLike(id="IC_1", database_id=1, author="alice", preview="hi")

        output_json(model)

        parsed = json.loads(capsys.readouterr().out)
        assert parsed == {"id": "IC_1", "database_id": 1, "author": "alice", "preview": "hi"}

    def test_non_model_non_serializable_value_still_falls_back_to_str(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A value that is neither JSON-native nor a ``BaseModel`` stringifies.

        Tests: The ``str()`` last-resort fallback (e.g. for ``Path``) is
        preserved alongside the new ``BaseModel`` handling.
        How: Nest a ``pathlib.Path`` inside the result dict.
        Why: Existing callers relying on ``default=str`` for non-Pydantic,
        non-JSON-native types must not regress.
        """
        result = {"path": Path("/tmp/example.txt")}

        output_json(result)

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["path"] == "/tmp/example.txt"
