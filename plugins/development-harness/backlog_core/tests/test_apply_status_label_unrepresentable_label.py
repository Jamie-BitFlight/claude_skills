"""A repository label GitHub reports must not leave ``gh_client`` as a bare ``ValueError``.

``_resolve_label_ids_graphql`` and ``_resolve_labels_graphql`` embed each label name
directly in a GraphQL query string, so both refuse a name outside
``_LABEL_NAME_PATTERN``. The refusal was a plain ``ValueError``, which nothing on the
path matches: ``_apply_status_label`` wraps the resolve call in ``except BacklogError``,
and the MCP tools catch ``BacklogError``. The refusal therefore failed the tool call
with an unhandled exception.

The names are not caller-supplied. ``_apply_status_label`` reads them off the live
issue and sends the whole set back, so one repository label carrying an emoji -- or any
character outside ``^[a-zA-Z0-9:_\\-. ]+$``, all of which GitHub permits -- breaks every
``apply_status_*`` call against every issue wearing it.

Same defect, same fix as d0f7bee87 applied to the issue-ref refusals: raise
``ValidationError``, a ``BacklogError`` subclass. ``_apply_status_label``'s own
``except BacklogError`` then absorbs it, and the caller sees the warning its docstring
already promises for a failed label update instead of an unhandled exception.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from backlog_core import gh_client
from backlog_core.models import BacklogItem, Output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# A label GitHub accepts and this module's pattern does not.
_EMOJI_LABEL = "🔥 on-fire"
_REFUSAL = "disallowed characters"


class _Repo:
    """Minimal stand-in for the PyGithub repository ``get_github`` returns."""

    full_name = "owner/repo"

    def get_label(self, name: str) -> object:
        """Report the status label as already present, so no REST creation runs."""
        return object()


@pytest.fixture(autouse=True)
def _live_issue_wearing_an_emoji_label(mocker: MockerFixture) -> None:
    """The issue carries a label name that came from the repository, not from a caller."""
    mocker.patch.object(gh_client, "get_github", return_value=_Repo())
    mocker.patch.object(
        gh_client, "_fetch_issue_graphql", return_value={"id": "I_kwDOnode", "labels": [{"name": _EMOJI_LABEL}]}
    )


def test_apply_status_verified_reports_an_unrepresentable_repo_label_as_a_warning() -> None:
    """``_apply_status_label``'s ``except BacklogError`` absorbs the refusal.

    ``apply_status_verified`` itself has no handler, so before the fix the refusal ran
    all the way out to the MCP tool wrapper.
    """
    out = Output()
    item = BacklogItem(title="Emoji Labelled", issue="#7", section="P1")

    gh_client.apply_status_verified(item, output=out)

    assert any(_REFUSAL in w for w in out.warnings), out.warnings


def test_apply_status_in_progress_reports_an_unrepresentable_repo_label_as_a_warning() -> None:
    """The sibling with its own ``except BacklogError`` reports through the same surface."""
    out = Output()
    item = BacklogItem(title="Emoji Labelled", issue="#7", section="P1")

    gh_client.apply_status_in_progress(item, output=out)

    assert any(_REFUSAL in w for w in out.warnings), out.warnings
