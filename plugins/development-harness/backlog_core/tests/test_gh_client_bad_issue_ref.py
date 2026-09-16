"""A non-numeric issue ref must not leave ``gh_client`` as a bare ``ValueError``.

Seven call sites in ``gh_client`` parse an issue ref into a GitHub issue number and
refuse a ref that is not one. Each raised a plain ``ValueError``, which nothing in
this project matches: the local handlers catch ``BacklogError``/``GithubException``,
and the MCP tools catch ``BacklogError``. The refusal therefore failed the tool call
with an unhandled exception. Same defect, same fix as 8bc308872 applied to
``operations``: raise ``ValidationError``, a ``BacklogError`` subclass.

The three sites covered here have three different caller-visible shapes, so each is
asserted on its own terms:

- ``close_github_issue`` and ``resolve_github_issue`` sit inside
  ``except BacklogError``, so the refusal becomes a warning and the call returns.
- ``apply_status_groomed`` sits in no ``try`` at all, and its caller ``groom_item``
  catches only ``GithubException``. The refusal still propagates -- but now as a
  ``BacklogError``, which ``backlog_groom`` reports as an ``error`` response
  instead of failing the tool call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from backlog_core import gh_client
from backlog_core.models import BacklogItem, Output, ValidationError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_BAD_REF = "gh-not-a-number"
_REFUSAL = "Invalid issue ref"


class _Repo:
    """Minimal stand-in for the PyGithub repository ``get_github`` returns."""

    full_name = "owner/repo"


@pytest.fixture(autouse=True)
def _github_reachable(mocker: MockerFixture) -> None:
    """Every site resolves a repository before it parses the ref."""
    mocker.patch.object(gh_client, "get_github", return_value=_Repo())


def test_close_reports_a_bad_issue_ref_as_a_warning() -> None:
    """``close_github_issue``'s own ``except BacklogError`` absorbs the refusal."""
    out = Output()

    gh_client.close_github_issue(_BAD_REF, "duplicate", output=out)

    assert any(_REFUSAL in w for w in out.warnings), out.warnings


def test_resolve_reports_a_bad_issue_ref_as_a_warning() -> None:
    """``resolve_github_issue``'s own ``except BacklogError`` absorbs the refusal."""
    out = Output()

    gh_client.resolve_github_issue(_BAD_REF, summary="Shipped", output=out)

    assert any(_REFUSAL in w for w in out.warnings), out.warnings


def test_apply_status_groomed_refuses_as_a_backlog_error() -> None:
    """``apply_status_groomed`` has no handler, so the refusal must at least be catchable.

    ``groom_item`` wraps this call in ``except GithubException``, which never matched
    the refusal and still does not. What changes is the type that escapes: a
    ``BacklogError`` subclass, which ``backlog_groom`` already handles.
    """
    item = BacklogItem(title="Bad Ref Item", issue=_BAD_REF, section="P1")

    with pytest.raises(ValidationError, match=_REFUSAL):
        gh_client.apply_status_groomed(item, output=Output())
