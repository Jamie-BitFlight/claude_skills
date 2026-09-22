#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Provider-interface tests for GitHub review transport and mutation validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import pr_review_threads
from pr_review_gh import GitHubProvider
from pr_review_models import (
    ChangeRequestTarget,
    FetchResult,
    ReplyAction,
    RepositoryTarget,
    ResolveAction,
    Reviewability,
    ReviewAction,
    ReviewActionResult,
    ReviewSnapshot,
    ThreadRef,
    TopLevelCommentAction,
)
from pr_review_provider import ProviderResponseError, ReviewProvider
from pr_review_threads import app

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


runner = CliRunner()


def target() -> ChangeRequestTarget:
    """Return one explicit GitHub target for provider tests."""
    return ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name="acme/widgets"), number=17
    )


def legacy_snapshot() -> FetchResult:
    """Return the smallest legacy GitHub snapshot the adapter must preserve."""
    return FetchResult(
        reviews_count=0,
        reviews_with_body=[],
        unresponded_reviews=[],
        threads_count=0,
        unresolved=[],
        unresolved_count=0,
        codex_approved=False,
        reviewability=Reviewability(is_draft=False, mergeable="MERGEABLE", merge_state_status="CLEAN", blockers=[]),
    )


def test_github_provider_satisfies_review_provider_and_returns_complete_single_transport_snapshot(
    mocker: MockerFixture,
) -> None:
    loader = mocker.Mock(return_value=legacy_snapshot())
    provider = GitHubProvider(snapshot_loader=loader, command_runner=mocker.Mock())

    assert isinstance(provider, ReviewProvider)

    result = provider.snapshot(target(), deadline=123.0, command_timeout=9.0)

    assert isinstance(result, ReviewSnapshot)
    assert result.provider == "github"
    assert result.target == target()
    assert result.snapshot_complete is True
    assert result.transport == "github_cli"
    assert result.codex_approved is False
    loader.assert_called_once_with("acme", "widgets", 17, deadline=123.0, gh_timeout=9.0)


def test_github_provider_validates_reply_response(mocker: MockerFixture) -> None:
    command_runner = mocker.Mock(return_value=json.dumps({"id": 991, "html_url": "https://github.com/x"}))
    provider = GitHubProvider(snapshot_loader=mocker.Mock(), command_runner=command_runner)
    action = ReplyAction(thread=ThreadRef(thread_id="T1", opening_comment_id=42), body="Addressed in abc123.")

    result = provider.act(target(), action, command_timeout=8.0)

    assert result.success is True
    assert result.provider_object_id == "991"
    assert result.resolved is None
    command_runner.assert_called_once_with(
        ["api", "-X", "POST", "repos/acme/widgets/pulls/17/comments/42/replies", "-f", "body=Addressed in abc123."],
        timeout=8.0,
    )


@pytest.mark.parametrize("raw", ["{}", '{"id": null}', "[]", "not-json"])
def test_github_provider_rejects_invalid_reply_response(raw: str, mocker: MockerFixture) -> None:
    provider = GitHubProvider(snapshot_loader=mocker.Mock(), command_runner=mocker.Mock(return_value=raw))
    action = ReplyAction(thread=ThreadRef(thread_id="T1", opening_comment_id=42), body="Addressed.")

    with pytest.raises(ProviderResponseError):
        provider.act(target(), action, command_timeout=None)


def test_github_provider_requires_resolved_thread_confirmation(mocker: MockerFixture) -> None:
    command_runner = mocker.Mock(
        return_value=json.dumps({"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}})
    )
    provider = GitHubProvider(snapshot_loader=mocker.Mock(), command_runner=command_runner)

    result = provider.act(
        target(), ResolveAction(thread=ThreadRef(thread_id="T1", opening_comment_id=42)), command_timeout=5.0
    )

    assert result.success is True
    assert result.resolved is True


@pytest.mark.parametrize(
    "payload",
    [
        {"errors": [{"message": "denied"}]},
        {"data": {"resolveReviewThread": None}},
        {"data": {"resolveReviewThread": {"thread": None}}},
        {"data": {"resolveReviewThread": {"thread": {"isResolved": False}}}},
    ],
)
def test_github_provider_rejects_unconfirmed_resolution(payload: dict[str, object], mocker: MockerFixture) -> None:
    provider = GitHubProvider(
        snapshot_loader=mocker.Mock(), command_runner=mocker.Mock(return_value=json.dumps(payload))
    )

    with pytest.raises(ProviderResponseError):
        provider.act(
            target(), ResolveAction(thread=ThreadRef(thread_id="T1", opening_comment_id=42)), command_timeout=None
        )


def test_github_provider_posts_top_level_comment_with_exact_references(mocker: MockerFixture) -> None:
    command_runner = mocker.Mock(return_value=json.dumps({"id": 77, "html_url": "https://github.com/comment"}))
    provider = GitHubProvider(snapshot_loader=mocker.Mock(), command_runner=command_runner)
    review_url = "https://github.com/acme/widgets/pull/17#pullrequestreview-5"

    result = provider.act(
        target(),
        TopLevelCommentAction(body="Addressed together in abc123.", references=[review_url]),
        command_timeout=None,
    )

    assert result.success is True
    posted_body = command_runner.call_args.args[0][-1]
    assert posted_body == f"body=Addressed together in abc123.\n\n{review_url}"


class FakeProvider:
    """In-memory adapter proving orchestration depends only on the provider interface."""

    def __init__(self) -> None:
        """Initialize recorded snapshot targets and actions."""
        self.snapshot_targets: list[ChangeRequestTarget] = []
        self.actions: list[ReviewAction] = []

    def snapshot(
        self, change_request: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Record and return one complete quiet snapshot.

        Returns:
            A complete in-memory snapshot.
        """
        self.snapshot_targets.append(change_request)
        return ReviewSnapshot.model_validate({
            **legacy_snapshot().model_dump(),
            "provider": "github",
            "target": change_request,
            "transport": "github_cli",
            "snapshot_complete": True,
        })

    def act(
        self, change_request: ChangeRequestTarget, action: ReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Record and confirm one in-memory action.

        Returns:
            A successful normalized action result.
        """
        self.actions.append(action)
        if isinstance(action, ResolveAction):
            return ReviewActionResult(
                provider="github",
                action_kind="resolve",
                success=True,
                resolved=True,
                raw={"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}},
            )
        kind = "reply" if isinstance(action, ReplyAction) else "comment"
        return ReviewActionResult(
            provider="github", action_kind=kind, success=True, provider_object_id="1", raw={"id": 1}
        )


def test_cli_fetch_watch_and_mutations_cross_only_provider_interface(tmp_path: Path, mocker: MockerFixture) -> None:
    fake = FakeProvider()
    mocker.patch.object(pr_review_threads, "_provider", return_value=fake)
    legacy_fetch = mocker.patch.object(pr_review_threads, "build_fetch_result")
    legacy_runner = mocker.patch.object(pr_review_threads, "run_gh")
    common_target = ["--github", "acme/widgets"]

    commands = [
        ["fetch", "--pr", "17", *common_target],
        ["watch", "--pr", "17", "--timeout-seconds", "0", *common_target],
        ["reply", "--pr", "17", "--comment-id", "42", "--body", "done", *common_target],
        ["resolve", "--thread-id", "T1"],
        ["comment", "--pr", "17", "--body", "done", "--reference", "https://example/review/1", *common_target],
        [
            "reply-and-resolve",
            "--pr",
            "17",
            "--thread-id",
            "T2",
            "--comment-id",
            "43",
            "--body",
            "done",
            *common_target,
        ],
    ]
    batch_file = tmp_path / "batch.json"
    batch_file.write_text(json.dumps([{"thread_id": "T3", "comment_id": 44, "body": "done"}]))
    commands.append(["reply-and-resolve-batch", "--pr", "17", "--input-file", str(batch_file), *common_target])

    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output

    assert len(fake.snapshot_targets) == 2
    assert [action.kind for action in fake.actions] == [
        "reply",
        "resolve",
        "comment",
        "reply",
        "resolve",
        "reply",
        "resolve",
    ]
    legacy_fetch.assert_not_called()
    legacy_runner.assert_not_called()
