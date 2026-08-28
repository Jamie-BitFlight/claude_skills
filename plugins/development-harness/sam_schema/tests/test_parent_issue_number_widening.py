"""Tests for ActiveTaskContext.parent_issue_number type widening.

Verifies the ``str | int | None`` validator:
- None is accepted
- Non-negative integers are accepted
- Valid beads string IDs are accepted (^[a-z][a-z0-9_-]*-[A-Za-z0-9.]+$)
- Booleans are rejected
- Negative integers are rejected
- Strings that do not match the beads ID pattern are rejected

Also validates round-trip preservation through BeadsContextBackend storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from sam_schema.core.backends.beads import BeadsContextBackend
from sam_schema.core.models import ActiveTaskContext

if TYPE_CHECKING:
    from .conftest import _FakeBdRunner

# ---------------------------------------------------------------------------
# ActiveTaskContext validator tests
# ---------------------------------------------------------------------------


class TestParentIssueNumberValidator:
    def test_none_accepted(self) -> None:
        """parent_issue_number=None must be accepted."""
        ctx = ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": None})
        assert ctx.parent_issue_number is None

    def test_positive_int_accepted(self) -> None:
        """A positive integer issue number must be accepted."""
        ctx = ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": 42})
        assert ctx.parent_issue_number == 42

    def test_zero_int_accepted(self) -> None:
        """Zero is a non-negative integer and must be accepted."""
        ctx = ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": 0})
        assert ctx.parent_issue_number == 0

    def test_beads_id_accepted(self) -> None:
        """A valid beads ID string (bd-xxxx pattern) must be accepted."""
        ctx = ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": "bd-a1b2"})
        assert ctx.parent_issue_number == "bd-a1b2"

    def test_boolean_rejected(self) -> None:
        """True/False must be rejected as parent_issue_number.

        The validator raises TypeError (not ValueError) for booleans.
        Pydantic v2 does not wrap TypeError in ValidationError — it propagates directly.
        """
        with pytest.raises(TypeError):
            ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": True})

    def test_negative_int_rejected(self) -> None:
        """Negative integers must be rejected."""
        with pytest.raises(ValidationError):
            ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": -1})

    def test_arbitrary_string_rejected(self) -> None:
        """Strings that are not valid beads IDs must be rejected.

        The pattern ``^[a-z][a-z0-9_-]*-[A-Za-z0-9.]+$`` requires a lowercase
        first character.  "CAPS-id" starts with an uppercase letter and must fail.
        The validator raises ValueError which Pydantic wraps in ValidationError.
        """
        with pytest.raises(ValidationError):
            ActiveTaskContext.model_validate({"task_id": "T01", "parent_issue_number": "CAPS-id"})


# ---------------------------------------------------------------------------
# Round-trip preservation through BeadsContextBackend
# ---------------------------------------------------------------------------


class TestParentIssueNumberRoundTrip:
    def test_int_round_trips(self, fake_runner: _FakeBdRunner) -> None:
        """Integer parent_issue_number must survive JSON serialisation round-trip."""
        backend = BeadsContextBackend(runner=fake_runner)
        backend.set_active_task("sess-int", "Pplan", "T01", "/tmp", parent_issue_number=99)

        result = backend.get_active_task("sess-int")
        assert result is not None
        assert result.parent_issue_number == 99

    def test_beads_str_round_trips(self, fake_runner: _FakeBdRunner) -> None:
        """Beads string parent_issue_number must survive JSON serialisation round-trip."""
        backend = BeadsContextBackend(runner=fake_runner)
        backend.set_active_task("sess-bd", "Pplan", "T01", "/tmp", parent_issue_number="bd-x9y8")

        result = backend.get_active_task("sess-bd")
        assert result is not None
        assert result.parent_issue_number == "bd-x9y8"

    def test_none_round_trips(self, fake_runner: _FakeBdRunner) -> None:
        """None parent_issue_number must survive JSON serialisation round-trip."""
        backend = BeadsContextBackend(runner=fake_runner)
        backend.set_active_task("sess-none", "Pplan", "T01", "/tmp", parent_issue_number=None)

        result = backend.get_active_task("sess-none")
        assert result is not None
        assert result.parent_issue_number is None
