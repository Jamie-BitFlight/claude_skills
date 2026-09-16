"""A non-numeric ``issue`` ref must not escape ``backlog_update`` as an unhandled error.

``_rename_item_title`` and ``_apply_plan_to_item`` each parse ``item.issue`` into a
GitHub issue number and refuse a ref that is not one. Both refusals sit inside a
``try`` whose only handler is ``except (GithubException, BacklogError)``, and both
raised a plain ``ValueError`` -- which matches neither, so the refusal left the
operation. ``backlog_update`` catches only ``BacklogError``, so the tool call failed
with an unhandled exception instead of the documented ``error``/``warnings`` surface.

Same defect, same fix as 267cb9730 applied to ``_apply_groomed_entries``: raise
``ValidationError``, a ``BacklogError`` subclass, so the existing handler downgrades
it to a warning and the backend-owned write that already succeeded still reports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogItem, Output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_BAD_REF = "gh-not-a-number"
_REFUSAL = "Expected numeric GitHub issue ref"


class _Repo:
    """Minimal stand-in for the PyGithub repository ``try_get_github`` returns."""

    full_name = "owner/repo"


@pytest.fixture
def _github_backed_bad_ref(mocker: MockerFixture) -> None:
    """Wire an integer-ID backend holding one item whose issue ref is not a number.

    ``try_get_github`` must return a repository: the refusal only fires on the
    branch that has decided GitHub is reachable.
    """
    backend = InMemoryBackend()
    backend.put_work_item(BacklogItem(title="Bad Ref Item", issue=_BAD_REF, section="P1"))
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
    mocker.patch.object(operations, "try_get_github", return_value=_Repo())


def _warnings(result: object) -> list[str]:
    """Return the warnings an operation result carries.

    Returns:
        The ``warnings`` list, or an empty list when the result carries none.
    """
    assert isinstance(result, dict)
    warnings = result.get("warnings", [])
    assert isinstance(warnings, list)
    return warnings


@pytest.mark.usefixtures("_github_backed_bad_ref")
def test_a_title_update_reports_a_bad_issue_ref_instead_of_raising() -> None:
    """``_rename_item_title``'s refusal reaches the caller as the documented warning."""
    result = operations.update_item(selector="Bad Ref Item", title="Renamed", output=Output())

    assert result.get("renamed_to") == "Renamed"
    assert any(_REFUSAL in w for w in _warnings(result)), _warnings(result)


@pytest.mark.usefixtures("_github_backed_bad_ref")
def test_a_plan_update_reports_a_bad_issue_ref_instead_of_raising() -> None:
    """``_apply_plan_to_item``'s refusal reaches the caller as the documented warning."""
    result = operations.update_item(selector="Bad Ref Item", plan="plan/tasks.yaml", output=Output())

    assert result.get("plan") == "plan/tasks.yaml"
    assert any(_REFUSAL in w for w in _warnings(result)), _warnings(result)
