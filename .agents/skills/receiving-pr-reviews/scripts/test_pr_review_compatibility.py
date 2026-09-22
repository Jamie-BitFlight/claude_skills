#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
#   "pytest-asyncio",
#   "pytest-cov",
#   "pytest-mock",
#   "pytest-xdist",
#   "typer",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Compatibility tests for the review CLI and strict GitHub ingress models."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel, ValidationError

import pr_review_gh
import pr_review_models
import pr_review_threads
from pr_review_models import FetchResult, Reviewability
from pr_review_threads import app
from review_test_gh_fixtures import (
    _default_github_detection as _default_github_detection,
    _head_state,
    _review,
    _state,
    runner,
)

SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_EVAL_TAGS = {
    "github-activation",
    "gitlab-activation",
    "negative-activation",
    "mixed-census",
    "question",
    "approval-only",
    "rejection",
    "bot-summary",
    "shared-cause",
    "stale-input",
    "incomplete-pagination",
    "mutation-authorization",
    "unavailable-capability",
    "new-input",
    "quiet-watch",
}

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# --- instruction package ------------------------------------------------------------------------


def test_model_invoked_description_covers_both_providers_and_trigger_branches() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    description = next(
        line.removeprefix("description: ") for line in skill.splitlines() if line.startswith("description:")
    )

    assert len(description.split()) <= 35
    assert "GitHub PR" in description
    assert "GitLab MR" in description
    assert "after pushing" in description
    assert "asked to check or address review feedback" in description
    assert "disable-model-invocation" not in skill


def test_instruction_links_are_one_hop_and_resolve_through_both_skill_paths() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+\.md)\)", skill)

    assert links == [
        "./references/gitlab-review-operations.md",
        "./references/github-mcp-fallback.md",
        "./references/review-cycle-contract.md",
    ]
    for link in links:
        relative = link.removeprefix("./")
        assert (SKILL_ROOT / relative).is_file()
        assert (SKILL_ROOT.parents[2] / ".claude/skills/receiving-pr-reviews" / relative).is_file()
    for reference in (SKILL_ROOT / "references").glob("*.md"):
        assert "references/" not in reference.read_text(encoding="utf-8")


def test_instructions_have_no_volatile_source_citations_or_cli_option_cache() -> None:
    instruction_files = [SKILL_ROOT / "SKILL.md", *(SKILL_ROOT / "references").glob("*.md")]
    volatile_citation = re.compile(r"(?:According to )?lines? \d+|\.py:\d+|\.py#L\d+")

    for path in instruction_files:
        text = path.read_text(encoding="utf-8")
        assert volatile_citation.search(text) is None, path
        assert "--provider-timeout-seconds" not in text, path


def test_review_contract_names_every_terminal_gate_and_input_class() -> None:
    contract = (SKILL_ROOT / "references/review-cycle-contract.md").read_text(encoding="utf-8")

    for term in (
        "comment",
        "question",
        "approval",
        "rejection/change request",
        "bot summary",
        "stakeholder input",
        "Clusters",
        "systemic",
        "no_change",
        "Verification",
        "Communication",
        "resolution",
        "Recheck",
        "REVIEW_COMPLETE",
    ):
        assert term in contract


def test_instruction_evals_have_unique_ids_and_required_scenarios() -> None:
    payload = json.loads((SKILL_ROOT / "evals/evals.json").read_text(encoding="utf-8"))
    evals = payload["evals"]
    ids = [case["id"] for case in evals]
    tags = {tag for case in evals for tag in case["tags"]}

    assert payload["skill_name"] == "receiving-pr-reviews"
    assert len(ids) == len(set(ids))
    assert tags >= REQUIRED_EVAL_TAGS
    assert all(case["expectations"] for case in evals)


@pytest.mark.parametrize("command", ["fetch", "watch"])
def test_instruction_facing_help_uses_pr_and_mr_terminology(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0, result.output
    assert "PR or MR number" in result.output


# --- strict ingress ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (pr_review_models.CommentNode, {"databaseId": "12", "body": "b", "line": 1, "originalLine": 1, "author": None}),
        (pr_review_models.PageInfo, {"hasNextPage": "false"}),
        (pr_review_models.ReviewThreadsConnection, {"totalCount": "3", "nodes": []}),
        (
            pr_review_models.PullRequestHeadState,
            {"isDraft": "false", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", "commits": {"nodes": []}},
        ),
        (
            pr_review_models.PullRequestHeadState,
            {"isDraft": False, "mergeable": 1, "mergeStateStatus": "CLEAN", "commits": {"nodes": []}},
        ),
    ],
    ids=["int-as-string", "bool-as-string", "count-as-string", "is-draft-as-string", "mergeable-as-number"],
)
def test_ingress_models_reject_a_coerced_producer_shape(model: type[BaseModel], payload: dict[str, object]) -> None:
    """A `gh` response whose scalar types do not match the schema fails at the boundary.

    In lax mode `"3"` silently becomes `3` and `"false"` becomes `True` — a producer-shape change
    would then reach review state looking valid. `GitHubResponseModel` sets `strict=True` so it
    raises here instead.
    """
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_ingress_models_still_parse_github_iso_timestamps() -> None:
    """Strict mode does not break timestamps: GitHub sends ISO-8601 strings and that is correct.

    These models are validated from `json.loads` output (Pydantic's Python mode), where a strict
    `datetime` field would reject the string GitHub actually sends. `GitHubTimestamp` relaxes
    strictness on exactly those fields and nothing else — so an unparseable value is still
    rejected, while the other forms a lax `datetime` accepts (a Unix epoch number) remain accepted.
    """
    assert pr_review_models.GitHubCommitDate.model_validate({"committedDate": "2026-01-06T00:00:00Z"}) == (
        pr_review_models.GitHubCommitDate(committedDate=datetime(2026, 1, 6, tzinfo=UTC))
    )
    with pytest.raises(ValidationError):
        pr_review_models.GitHubCommitDate.model_validate({"committedDate": "not-a-timestamp"})


def test_internal_result_models_are_not_strict() -> None:
    """`FetchResult`/`WatchResult`/`UnresolvedThread` are output shapes, not ingress.

    They are assembled from already-validated values, so they deliberately do not inherit
    `GitHubResponseModel` — see its docstring.
    """
    for model in (pr_review_models.FetchResult, pr_review_models.WatchResult, pr_review_models.UnresolvedThread):
        assert model.model_config.get("strict") is not True


# --- every command can bound its own gh calls -----------------------------------------------------


def test_fetch_accepts_a_timeout_bound(mocker: MockerFixture) -> None:
    """`--gh-timeout-seconds` reaches the fetch provider."""
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--github", "o/r", "--gh-timeout-seconds", "7"])

    assert result.exit_code == 0, result.output


# --- --github: autodetect vs explicit override ---------------------------------------------------


def test_fetch_uses_detected_github_when_not_overridden(mocker: MockerFixture) -> None:
    """Without `--github`, `fetch` autodetects this checkout's own `owner/repo` and uses it."""
    detect_mock = mocker.patch.object(
        pr_review_threads, "detect_repo_identity", return_value=("detected-owner", "detected-repo")
    )
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())

    result = runner.invoke(app, ["fetch", "--pr", "3208"])

    assert result.exit_code == 0, result.output
    detect_mock.assert_called_once()
    assert fetch_mock.call_args.args[:2] == ("detected-owner", "detected-repo")


@pytest.mark.parametrize(
    "detection_error",
    [subprocess.CalledProcessError(1, ["gh"]), subprocess.TimeoutExpired(cmd=["gh"], timeout=30)],
    ids=["called-process-error", "timeout-expired"],
)
def test_fetch_exits_nonzero_and_names_github_flag_when_detection_fails(
    detection_error: Exception, mocker: MockerFixture
) -> None:
    """When autodetection fails, `fetch` exits non-zero and names `--github` as the way out.

    A wrong owner/repo would send a reply to the wrong repository, so a failed detection must stop
    the command rather than fall back to a guess. Regression coverage for `TimeoutExpired`: a
    `--gh-timeout-seconds`-bounded `gh repo view` call that exceeds it must produce this same clean
    exit rather than an unhandled exception.
    """
    mocker.patch.object(pr_review_threads, "detect_repo_identity", side_effect=detection_error)
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result")

    result = runner.invoke(app, ["fetch", "--pr", "3208"])

    assert result.exit_code != 0
    assert "--github" in result.output
    fetch_mock.assert_not_called()


def test_fetch_uses_explicit_github_override_and_skips_detection(mocker: MockerFixture) -> None:
    """`--github owner/repo` is used as-is, and autodetection is never attempted."""
    detect_mock = mocker.patch.object(pr_review_threads, "detect_repo_identity")
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--github", "acme/widgets"])

    assert result.exit_code == 0, result.output
    detect_mock.assert_not_called()
    assert fetch_mock.call_args.args[:2] == ("acme", "widgets")


@pytest.mark.parametrize(
    "value",
    ["no-slash-here", "/repo", "owner/", "owner/repo/extra"],
    ids=["no-slash", "empty-owner", "empty-repo", "too-many-slashes"],
)
def test_fetch_rejects_a_malformed_github_override(value: str, mocker: MockerFixture) -> None:
    """A `--github` value must be exactly one `owner/repo` pair with both halves non-empty."""
    detect_mock = mocker.patch.object(pr_review_threads, "detect_repo_identity")
    build_mock = mocker.patch.object(pr_review_threads, "build_fetch_result")

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--github", value])

    assert result.exit_code != 0
    detect_mock.assert_not_called()
    build_mock.assert_not_called()


# --- reviewability -------------------------------------------------------------------------------


def test_reviewability_reports_no_blockers_for_a_ready_conflict_free_pr() -> None:
    """A non-draft, mergeable PR can be reviewed, so `blockers` is empty."""
    result = pr_review_gh._reviewability(_head_state())

    assert result.blockers == []
    assert result.is_draft is False
    assert result.mergeable == "MERGEABLE"
    assert result.merge_state_status == "CLEAN"


def test_reviewability_reports_a_draft_pr() -> None:
    """A draft PR gets no reviewers requested, so an empty review queue is expected, not clean."""
    result = pr_review_gh._reviewability(_head_state(is_draft=True, merge_state_status="DRAFT"))

    assert result.is_draft is True
    assert result.blockers == ["draft: reviewers are not requested until the PR is marked ready for review"]


def test_reviewability_reports_a_conflicting_pr() -> None:
    """A conflicting PR gets no review runs, so an empty review queue is expected, not clean."""
    result = pr_review_gh._reviewability(_head_state(mergeable="CONFLICTING", merge_state_status="DIRTY"))

    assert result.mergeable == "CONFLICTING"
    assert result.merge_state_status == "DIRTY"
    assert result.blockers == ["conflicting: reviews will not run until the merge conflicts are resolved"]


def test_reviewability_reports_both_blockers_when_both_apply() -> None:
    """A draft PR that also conflicts names both consequences, not just the first one found."""
    result = pr_review_gh._reviewability(
        _head_state(is_draft=True, mergeable="CONFLICTING", merge_state_status="DIRTY")
    )

    assert len(result.blockers) == 2


def test_reviewability_does_not_treat_unknown_mergeable_as_a_conflict() -> None:
    """`UNKNOWN` is GitHub still computing mergeability, not a conflict — reporting one is a lie.

    GitHub computes mergeability in a background job and returns `UNKNOWN` while it runs, which is
    exactly the moment just after a push — precisely when this script is most likely to be called.
    The value is surfaced as data and left for the next check to resolve; `watch` re-reads it every
    poll.
    """
    result = pr_review_gh._reviewability(_head_state(mergeable="UNKNOWN", merge_state_status="UNKNOWN"))

    assert result.mergeable == "UNKNOWN"
    assert result.blockers == []


def test_reviewability_survives_a_merge_state_status_this_script_has_never_seen() -> None:
    """An unrecognized GitHub state reaches the caller as data instead of failing validation."""
    result = pr_review_gh._reviewability(_head_state(merge_state_status="SOME_FUTURE_STATE"))

    assert result.merge_state_status == "SOME_FUTURE_STATE"
    assert result.blockers == []


def test_watch_reports_reviewability_on_a_timed_out_result(mocker: MockerFixture) -> None:
    """`watch` carries the blockers too: blocking 270s for reviews on a draft PR is pure waste."""
    blocked = _state()
    blocked.reviewability = Reviewability(
        is_draft=True, mergeable="CONFLICTING", merge_state_status="DIRTY", blockers=["draft: x", "conflicting: y"]
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=blocked)

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    assert data["state"]["reviewability"]["blockers"] == ["draft: x", "conflicting: y"]


def test_blockers_do_not_change_has_outstanding_work() -> None:
    """Reviewability explains an empty result set; it never creates or suppresses work."""
    blocked = _state()
    blocked.reviewability = Reviewability(
        is_draft=True, mergeable="CONFLICTING", merge_state_status="DIRTY", blockers=["draft: x"]
    )
    assert blocked.has_outstanding_work() is False

    blocked_with_work = _state(unresolved_count=1)
    blocked_with_work.reviewability = blocked.reviewability
    assert blocked_with_work.has_outstanding_work() is True


# --- FetchResult.has_outstanding_work -----------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        _state(unresolved_count=1),
        _state(unresponded_reviews=[_review("R1", body="x", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))]),
        _state(codex_approved=True),
    ],
    ids=["unresolved-thread", "unresponded-review", "codex-approved"],
)
def test_has_outstanding_work_true_when_any_signal_present(state: FetchResult) -> None:
    assert state.has_outstanding_work() is True


def test_has_outstanding_work_false_when_all_clear() -> None:
    assert _state().has_outstanding_work() is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
