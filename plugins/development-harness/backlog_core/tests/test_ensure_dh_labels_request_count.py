"""Regression test for the REST request count `ensure_dh_labels` spends per call.

Counted offline 2026-09-27: every `backlog_add` call reaches `create_issue_for_item`, which
calls `ensure_dh_labels` unconditionally -- and that function called `repo.get_label(name)` once
per entry in `DH_LABELS` (12 REST requests), even when every label already existed. Under a
tightened secondary rate limit, that is 12 wasted requests on the common case.

The fix must cost at most one REST call (`repo.get_labels()`) when every label already exists,
`create_label()` only for names actually missing, and skip entirely on a repeat call for the same
repo within one process -- labels don't change mid-session. No network is touched; `repo` is a
plain Mock, and each test uses a distinct `full_name` so the module-level process cache in
`ensure_dh_labels` cannot leak between tests (they may run in any order, including in parallel
xdist workers).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backlog_core.gh_client import DH_LABELS, ensure_dh_labels


@dataclass
class _FakeLabel:
    """Stands in for a PyGithub `Label` -- `ensure_dh_labels` only reads `.name`."""

    name: str


def _make_repo(mocker: Any, full_name: str, existing_label_names: list[str]) -> Any:
    """Build a Mock repo whose `get_labels()` reports the given existing labels."""
    repo = mocker.Mock()
    repo.full_name = full_name
    repo.get_labels.return_value = [_FakeLabel(name) for name in existing_label_names]
    return repo


class TestEnsureDhLabelsRequestCount:
    """Costs one list call plus creates for genuinely-missing labels, never a per-label GET."""

    def test_all_labels_present_costs_exactly_one_rest_call(self, mocker: Any) -> None:
        repo = _make_repo(mocker, "o/r-all-present", list(DH_LABELS))

        ensure_dh_labels(repo)

        assert repo.get_labels.call_count == 1
        assert repo.get_label.call_count == 0
        assert repo.create_label.call_count == 0

    def test_one_missing_label_creates_only_that_one(self, mocker: Any) -> None:
        missing_name = next(iter(DH_LABELS))
        present = [name for name in DH_LABELS if name != missing_name]
        repo = _make_repo(mocker, "o/r-one-missing", present)

        ensure_dh_labels(repo)

        assert repo.get_labels.call_count == 1
        assert repo.get_label.call_count == 0
        assert repo.create_label.call_count == 1
        created_name = repo.create_label.call_args.kwargs.get("name") or repo.create_label.call_args.args[0]
        assert created_name == missing_name

    def test_every_label_missing_creates_every_label_exactly_once(self, mocker: Any) -> None:
        repo = _make_repo(mocker, "o/r-all-missing", [])

        ensure_dh_labels(repo)

        assert repo.get_labels.call_count == 1
        assert repo.create_label.call_count == len(DH_LABELS)

    def test_a_second_call_for_the_same_repo_this_process_makes_no_rest_call(self, mocker: Any) -> None:
        repo = _make_repo(mocker, "o/r-repeat-call", list(DH_LABELS))

        ensure_dh_labels(repo)
        ensure_dh_labels(repo)

        assert repo.get_labels.call_count == 1

    def test_a_different_repo_still_gets_its_own_check(self, mocker: Any) -> None:
        """The process-level skip is keyed per repo, not global."""
        repo_a = _make_repo(mocker, "o/r-distinct-a", list(DH_LABELS))
        repo_b = _make_repo(mocker, "o/r-distinct-b", list(DH_LABELS))

        ensure_dh_labels(repo_a)
        ensure_dh_labels(repo_b)

        assert repo_a.get_labels.call_count == 1
        assert repo_b.get_labels.call_count == 1
