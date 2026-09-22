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
"""Provider-interface tests for GitHub review transport and mutation validation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

import pytest
from typer.testing import CliRunner

import pr_review_threads
from pr_review_gh import RESOLVE_THREAD_MUTATION
from pr_review_github_provider import GitHubProvider, upgrade_legacy_snapshot
from pr_review_models import (
    ChangeRequestTarget,
    FetchResult,
    ReplyAction,
    RepositoryTarget,
    ResolveAction,
    Reviewability,
    ReviewActionResult,
    ReviewSnapshot,
    TopLevelCommentAction,
)
from pr_review_provider import ProviderResponseError, ReviewProvider
from pr_review_state_models import (
    AuthorizedReviewAction,
    ProviderInputIdentity,
    ReviewActor,
    ReviewCapabilities,
    ReviewInput,
)
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


def provider(mocker: MockerFixture, *, command_result: str = "{}") -> GitHubProvider:
    """Return a GitHub provider with injected test transports."""
    return GitHubProvider(
        snapshot_loader=mocker.Mock(return_value=legacy_snapshot()),
        command_runner=mocker.Mock(return_value=command_result),
        resolve_query=RESOLVE_THREAD_MUTATION,
    )


def authorized(action: ReplyAction | ResolveAction | TopLevelCommentAction) -> AuthorizedReviewAction:
    """Bind one action to a valid inline GitHub input fixture."""
    item = ReviewInput(
        input_id="github:review-comment:42",
        provider="github",
        provider_ids=ProviderInputIdentity(object_id="42", reply_target_id="42", resolution_target_id="T1"),
        source_kind="review_comment",
        kinds={"comment"},
        location="inline",
        direction="inbound",
        actor=ReviewActor(actor_id="reviewer", login="reviewer", classification="human", role="reviewer"),
        body="finding",
        stable_reference="https://github.com/acme/widgets/pull/17#discussion_r42",
        created_at=None,
        updated_at=None,
        revision_relation="current",
        path="x.py",
        line=1,
        provider_state="open",
        capabilities=ReviewCapabilities(can_reply=True, can_resolve=True, can_comment=True, unavailable=[]),
        thread_id="T1",
        parent_id=None,
    )
    return AuthorizedReviewAction(
        target=target(),
        snapshot_fingerprint="fingerprint",
        revision="abc123",
        review_input=item,
        cluster_id="cluster-1",
        disposition="accepted_change",
        communication_plan="reply",
        inspectable_revision="abc123",
        implementation_evidence=["Commit abc123 contains the correction."],
        verification_evidence=["pytest passed at abc123."],
        action=action,
    )


def test_github_provider_satisfies_review_provider_and_returns_complete_single_transport_snapshot(
    mocker: MockerFixture,
) -> None:
    loader = mocker.Mock(return_value=legacy_snapshot())
    provider_value = GitHubProvider(
        snapshot_loader=loader, command_runner=mocker.Mock(), resolve_query=RESOLVE_THREAD_MUTATION
    )

    assert isinstance(provider_value, ReviewProvider)

    result = provider_value.snapshot(target(), deadline=123.0, command_timeout=9.0)

    assert isinstance(result, ReviewSnapshot)
    assert result.provider == "github"
    assert result.target == target()
    assert result.snapshot_complete is True
    assert result.transport == "github_cli"
    assert result.codex_approved is False
    loader.assert_called_once_with("acme", "widgets", 17, deadline=123.0, gh_timeout=9.0, target=target())


def test_github_provider_validates_reply_response(mocker: MockerFixture) -> None:
    command_runner = mocker.Mock(return_value=json.dumps({"id": 991, "html_url": "https://github.com/x"}))
    provider_value = GitHubProvider(
        snapshot_loader=mocker.Mock(), command_runner=command_runner, resolve_query=RESOLVE_THREAD_MUTATION
    )
    action = authorized(ReplyAction(body="Addressed in abc123."))

    result = provider_value.act(target(), action, command_timeout=8.0)

    assert result.success is True
    assert result.provider_object_id == "991"
    assert result.resolved is None
    command_runner.assert_called_once_with(
        ["api", "-X", "POST", "repos/acme/widgets/pulls/17/comments/42/replies", "-f", "body=Addressed in abc123."],
        timeout=8.0,
    )


@pytest.mark.parametrize("raw", ["{}", '{"id": null}', "[]", "not-json"])
def test_github_provider_rejects_invalid_reply_response(raw: str, mocker: MockerFixture) -> None:
    provider_value = provider(mocker, command_result=raw)
    action = authorized(ReplyAction(body="Addressed."))

    with pytest.raises(ProviderResponseError):
        provider_value.act(target(), action, command_timeout=None)


def test_github_provider_requires_resolved_thread_confirmation(mocker: MockerFixture) -> None:
    command_runner = mocker.Mock(
        return_value=json.dumps({"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}})
    )
    provider_value = GitHubProvider(
        snapshot_loader=mocker.Mock(), command_runner=command_runner, resolve_query=RESOLVE_THREAD_MUTATION
    )

    result = provider_value.act(target(), authorized(ResolveAction()), command_timeout=5.0)

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
    provider_value = provider(mocker, command_result=json.dumps(payload))

    with pytest.raises(ProviderResponseError):
        provider_value.act(target(), authorized(ResolveAction()), command_timeout=None)


def test_github_provider_posts_top_level_comment_with_exact_references(mocker: MockerFixture) -> None:
    command_runner = mocker.Mock(return_value=json.dumps({"id": 77, "html_url": "https://github.com/comment"}))
    provider_value = GitHubProvider(
        snapshot_loader=mocker.Mock(), command_runner=command_runner, resolve_query=RESOLVE_THREAD_MUTATION
    )
    review_url = "https://github.com/acme/widgets/pull/17#pullrequestreview-5"

    result = provider_value.act(
        target(),
        authorized(TopLevelCommentAction(body="Addressed together in abc123.", references=[review_url])),
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
        self.actions: list[AuthorizedReviewAction] = []

    def snapshot(
        self, change_request: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Record and return one complete quiet snapshot.

        Returns:
            A complete in-memory snapshot.
        """
        self.snapshot_targets.append(change_request)
        return upgrade_legacy_snapshot(legacy_snapshot(), change_request)

    def act(
        self, change_request: ChangeRequestTarget, action: AuthorizedReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Record and confirm one in-memory action.

        Returns:
            A successful normalized action result.
        """
        self.actions.append(action)
        if isinstance(action.action, ResolveAction):
            return ReviewActionResult(
                provider="github",
                action_kind="resolve",
                success=True,
                resolved=True,
                raw={"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}},
            )
        kind = "reply" if isinstance(action.action, ReplyAction) else "comment"
        return ReviewActionResult(
            provider="github", action_kind=kind, success=True, provider_object_id="1", raw={"id": 1}
        )


def test_cli_fetch_and_watch_cross_only_provider_interface(mocker: MockerFixture) -> None:
    fake = FakeProvider()
    mocker.patch.object(pr_review_threads, "review_provider", return_value=fake)
    legacy_fetch = mocker.patch.object(pr_review_threads, "build_fetch_result")
    legacy_runner = mocker.patch.object(pr_review_threads, "run_gh")
    common_target = ["--github", "acme/widgets"]

    commands = [
        ["fetch", "--pr", "17", *common_target],
        ["watch", "--pr", "17", "--timeout-seconds", "0", *common_target],
    ]

    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output

    assert len(fake.snapshot_targets) == 2
    assert fake.actions == []
    legacy_fetch.assert_not_called()
    legacy_runner.assert_not_called()


def test_github_provider_rejects_raw_action(mocker: MockerFixture) -> None:
    provider_value = provider(mocker, command_result=json.dumps({"id": 1}))

    with pytest.raises(TypeError, match="AuthorizedReviewAction"):
        provider_value.act(target(), cast("Any", ReplyAction(body="raw")), command_timeout=None)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
