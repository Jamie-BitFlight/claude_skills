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
"""GitLab review-provider contract, normalization, and mutation tests."""

from __future__ import annotations

import json
import subprocess
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import pr_review_threads
from pr_review_cli_target import auto_target, remote_identity
from pr_review_contracts import ChangeRequestTarget, ReplyAction, RepositoryTarget, ResolveAction, TopLevelCommentAction
from pr_review_gitlab_normalize import normalize_state
from pr_review_gitlab_provider import GitLabProvider
from pr_review_gitlab_transport import collect_state, parse_ndjson
from pr_review_gitlab_wire import GitLabApprovals, GitLabDiscussion
from pr_review_output import summarize
from pr_review_provider import ProviderResponseError, ReviewProvider
from pr_review_state_models import AuthorizedReviewAction
from pr_review_threads import app
from review_test_gitlab_fixtures import NOW, note, state, target, user

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


RUNNER = CliRunner()


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        ("git@gitlab.example.test:group/subgroup/widgets.git", ("gitlab.example.test", "group/subgroup/widgets")),
        ("https://gitlab.example.test/group/subgroup/widgets.git", ("gitlab.example.test", "group/subgroup/widgets")),
    ],
)
def test_remote_identity_supports_ssh_https_and_nested_namespaces(remote: str, expected: tuple[str, str]) -> None:
    assert remote_identity(remote) == expected


def test_auto_target_verifies_custom_gitlab_remote_with_glab(mocker: MockerFixture) -> None:
    git_runner = mocker.Mock(return_value="git@gitlab.example.test:group/subgroup/widgets.git\n")
    glab_runner = mocker.Mock(
        return_value=json.dumps({
            "path_with_namespace": "group/subgroup/widgets",
            "web_url": "https://gitlab.example.test/group/subgroup/widgets",
        })
    )

    resolved = auto_target(
        3,
        timeout=5.0,
        github_resolver=lambda _repo, _number: pytest.fail("GitHub resolver must not run"),
        git_runner=git_runner,
        glab_runner=glab_runner,
    )

    assert resolved == target()
    git_runner.assert_called_once_with(["remote", "get-url", "origin"], timeout=5.0)
    glab_runner.assert_called_once_with(["repo", "view", "--output", "json"], timeout=5.0)


def test_auto_target_routes_github_without_calling_glab(mocker: MockerFixture) -> None:
    expected = ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name="acme/widgets"), number=17
    )
    github_resolver = mocker.Mock(return_value=expected)
    glab_runner = mocker.Mock()

    resolved = auto_target(
        17,
        timeout=5.0,
        github_resolver=github_resolver,
        git_runner=mocker.Mock(return_value="https://github.com/acme/widgets.git\n"),
        glab_runner=glab_runner,
    )

    assert resolved == expected
    github_resolver.assert_called_once_with("acme/widgets", 17)
    glab_runner.assert_not_called()


def test_gitlab_normalizes_complete_atomic_census_and_unavailable_codex_equivalence() -> None:
    snapshot = normalize_state(state(), target())

    assert snapshot.snapshot_complete is True
    assert snapshot.provider == "gitlab"
    assert snapshot.transport == "gitlab_cli"
    assert snapshot.codex_approved is None
    assert snapshot.codex_approval_equivalence == "unavailable"
    assert snapshot.revision_at == NOW + timedelta(minutes=1)
    assert {item.input_id for item in snapshot.review_inputs} == {
        "gitlab:note:10",
        "gitlab:note:11",
        "gitlab:note:12",
        "gitlab:note:14",
        "gitlab:approval:2",
        "gitlab:award:20",
        "gitlab:award:21",
    }
    assert "gitlab:note:13" not in {item.input_id for item in snapshot.review_inputs}
    kinds = {item.input_id: item.kinds for item in snapshot.review_inputs}
    assert kinds["gitlab:approval:2"] == {"approval"}
    assert kinds["gitlab:award:20"] == {"approval"}
    assert kinds["gitlab:award:21"] == {"rejection"}
    thread = next(item for item in snapshot.review_inputs if item.input_id == "gitlab:note:10")
    assert thread.provider_ids.reply_target_id == "discussion-1"
    assert thread.provider_ids.resolution_target_id == "discussion-1"
    assert thread.revision_relation == "current"
    assert snapshot.unresolved_count == 1


def test_zero_required_approved_state_is_preserved_as_provider_metadata() -> None:
    fetched = state().model_copy(
        update={
            "approvals": GitLabApprovals(
                approved=True, approvals_required=0, approvals_left=0, approved_by=[], approval_rules_left=[]
            ),
            "awards": [],
        }
    )

    snapshot = normalize_state(fetched, target())

    assert not any("approval" in item.kinds for item in snapshot.review_inputs)
    assert snapshot.codex_approved is None
    assert snapshot.provider_metadata.approval_state is not None
    assert snapshot.provider_metadata.approval_state.model_dump() == {
        "approved": True,
        "approvals_required": 0,
        "approvals_left": 0,
        "approval_rules_left": [],
    }
    assert [item.model_dump() for item in snapshot.provider_metadata.system_notes] == [
        {"id": "13", "body": "pushed commits", "created_at": NOW + timedelta(seconds=13)}
    ]
    assert summarize(snapshot, pr=3, max_body=None).provider_metadata == snapshot.provider_metadata


def test_note_actor_without_observed_role_remains_unknown() -> None:
    snapshot = normalize_state(state(), target())

    item = next(value for value in snapshot.review_inputs if value.input_id == "gitlab:note:10")

    assert item.actor.role == "unknown"


def test_outbound_exact_reference_reconciles_provider_communication() -> None:
    fetched = state()
    inbound = fetched.discussions[0].notes[0]
    reference = f"{fetched.merge_request.web_url}#note_{inbound.id}"
    response = note(99, fetched.current_user, f"Addressed.\n\n{reference}")
    fetched = fetched.model_copy(update={"notes": [*fetched.notes, response]})

    snapshot = normalize_state(fetched, target())

    assert snapshot.communicated_input_ids == {"gitlab:note:10"}


def test_input_edited_after_exact_reference_response_requires_new_communication() -> None:
    fetched = state()
    original = fetched.discussions[0].notes[0]
    reference = f"{fetched.merge_request.web_url}#note_{original.id}"
    response = note(99, fetched.current_user, f"Addressed.\n\n{reference}")
    edited = original.model_copy(
        update={
            "body": "This is a materially different concern.",
            "updated_at": response.created_at + timedelta(seconds=1),
        }
    )
    discussion = fetched.discussions[0].model_copy(update={"notes": [edited, *fetched.discussions[0].notes[1:]]})
    notes = [edited if item.id == edited.id else item for item in fetched.notes]
    fetched = fetched.model_copy(
        update={"discussions": [discussion, *fetched.discussions[1:]], "notes": [*notes, response]}
    )

    snapshot = normalize_state(fetched, target())

    assert "gitlab:note:10" not in snapshot.communicated_input_ids
    assert snapshot.outstanding_input_count > 0
    assert snapshot.has_outstanding_work() is True


def test_new_already_resolved_input_still_requires_assessment_and_communication() -> None:
    reviewer = user(8, "observer")
    resolved_note = note(80, reviewer, "Resolved before the review cycle observed it", resolvable=True, resolved=True)
    fetched = state().model_copy(
        update={
            "discussions": [GitLabDiscussion(id="resolved-1", individual_note=False, notes=[resolved_note])],
            "notes": [resolved_note],
            "approvals": GitLabApprovals(approved=False, approvals_required=0, approvals_left=0, approved_by=[]),
            "awards": [],
        }
    )

    snapshot = normalize_state(fetched, target())

    assert snapshot.unresolved_count == 0
    assert snapshot.outstanding_input_count == 1
    assert snapshot.has_outstanding_work() is True


def test_top_level_gitlab_inputs_stop_watch() -> None:
    fetched = state().model_copy(
        update={
            "discussions": [],
            "notes": [note(80, user(8, "observer"), "Please clarify")],
            "approvals": GitLabApprovals(approved=False, approvals_required=0, approvals_left=0, approved_by=[]),
            "awards": [],
        }
    )

    snapshot = normalize_state(fetched, target())

    assert snapshot.unresolved_count == 0
    assert snapshot.outstanding_input_count == 1
    assert snapshot.has_outstanding_work() is True


def test_snapshot_fingerprint_covers_reviewability_and_provider_metadata() -> None:
    original = normalize_state(state(), target())
    draft_state = state().model_copy(update={"merge_request": state().merge_request.model_copy(update={"draft": True})})
    metadata_state = state().model_copy(
        update={"approvals": state().approvals.model_copy(update={"approvals_left": 1})}
    )

    assert normalize_state(draft_state, target()).snapshot_fingerprint != original.snapshot_fingerprint
    assert normalize_state(metadata_state, target()).snapshot_fingerprint != original.snapshot_fingerprint


def test_ndjson_validates_every_paginated_item_and_rejects_a_bad_later_page() -> None:
    valid = json.dumps(state().discussions[0].model_dump(mode="json"))
    invalid = json.dumps({"id": "late-page", "individual_note": False, "notes": []})

    with pytest.raises(ProviderResponseError, match="item 2"):
        parse_ndjson(f"{valid}\n{invalid}\n", GitLabDiscussion, "discussions")


def test_transport_requests_every_list_with_complete_pagination(mocker: MockerFixture) -> None:
    fetched = state()
    responses = {
        "/discussions?": "\n".join(item.model_dump_json() for item in fetched.discussions),
        "/notes?": "\n".join(item.model_dump_json() for item in fetched.notes),
        "/approvals": fetched.approvals.model_dump_json(),
        "/award_emoji?": "\n".join(item.model_dump_json() for item in fetched.awards),
        "/versions?": "\n".join(item.model_dump_json() for item in fetched.versions),
        "user": fetched.current_user.model_dump_json(),
        "merge_requests/3": fetched.merge_request.model_dump_json(),
    }

    def run(arguments: list[str], *, timeout: float | None) -> str:
        endpoint = arguments[-1]
        return next(value for marker, value in responses.items() if marker in endpoint)

    runner = mocker.Mock(side_effect=run)
    result = collect_state(
        "gitlab.example.test", "group/subgroup/widgets", 3, deadline=None, command_timeout=4.0, runner=runner
    )

    assert result == fetched
    assert runner.call_count == 14
    list_calls = [call.args[0] for call in runner.call_args_list if "?per_page=100" in call.args[0][-1]]
    assert len(list_calls) == 8
    assert all("--paginate" in arguments and "ndjson" in arguments for arguments in list_calls)
    assert all(call.kwargs == {"timeout": 4.0} for call in runner.call_args_list)


def test_transport_recomputes_remaining_deadline_before_every_command(mocker: MockerFixture) -> None:
    fetched = state()
    responses = {
        "/discussions?": "\n".join(item.model_dump_json() for item in fetched.discussions),
        "/notes?": "\n".join(item.model_dump_json() for item in fetched.notes),
        "/approvals": fetched.approvals.model_dump_json(),
        "/award_emoji?": "\n".join(item.model_dump_json() for item in fetched.awards),
        "/versions?": "\n".join(item.model_dump_json() for item in fetched.versions),
        "user": fetched.current_user.model_dump_json(),
        "merge_requests/3": fetched.merge_request.model_dump_json(),
    }

    def run(arguments: list[str], *, timeout: float | None) -> str:
        endpoint = arguments[-1]
        return next(value for marker, value in responses.items() if marker in endpoint)

    runner = mocker.Mock(side_effect=run)
    mocker.patch("pr_review_gitlab_transport.time.monotonic", side_effect=range(14))

    with pytest.raises(subprocess.TimeoutExpired):
        collect_state(
            "gitlab.example.test", "group/subgroup/widgets", 3, deadline=5.0, command_timeout=20.0, runner=runner
        )

    assert [call.kwargs["timeout"] for call in runner.call_args_list] == [5.0, 4.0, 3.0, 2.0, 1.0]


def test_transport_rejects_mixed_time_collections(mocker: MockerFixture) -> None:
    fetched = state()
    changed_notes = [*fetched.notes, note(77, user(8, "observer"), "Late note")]
    calls = 0

    def run(arguments: list[str], *, timeout: float | None) -> str:
        nonlocal calls
        pass_number = calls // 7
        calls += 1
        endpoint = arguments[-1]
        if "/discussions?" in endpoint:
            return "\n".join(item.model_dump_json() for item in fetched.discussions)
        if "/notes?" in endpoint:
            values = fetched.notes if pass_number == 0 else changed_notes
            return "\n".join(item.model_dump_json() for item in values)
        if "/approvals" in endpoint:
            return fetched.approvals.model_dump_json()
        if "/award_emoji?" in endpoint:
            return "\n".join(item.model_dump_json() for item in fetched.awards)
        if "/versions?" in endpoint:
            return "\n".join(item.model_dump_json() for item in fetched.versions)
        if endpoint == "user":
            return fetched.current_user.model_dump_json()
        return fetched.merge_request.model_dump_json()

    with pytest.raises(ProviderResponseError, match="changed during collection"):
        collect_state(
            "gitlab.example.test", "group/subgroup/widgets", 3, deadline=None, command_timeout=4.0, runner=run
        )


def test_cli_routes_explicit_gitlab_target_and_exposes_provider_help(mocker: MockerFixture) -> None:
    provider = mocker.Mock()
    provider.snapshot.return_value = normalize_state(state(), target())
    mocker.patch.object(pr_review_threads, "review_provider_for_target", return_value=provider)

    result = RUNNER.invoke(
        app,
        [
            "fetch",
            "--pr",
            "3",
            "--provider",
            "gitlab",
            "--host",
            "gitlab.example.test",
            "--repo",
            "group/subgroup/widgets",
            "--glab-timeout-seconds",
            "6",
        ],
    )
    help_result = RUNNER.invoke(app, ["fetch", "--help"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["provider"] == "gitlab"
    provider.snapshot.assert_called_once_with(target(), deadline=None, command_timeout=6.0)
    assert "--provider" in help_result.output
    assert "--provider-timeout" in help_result.output


def test_cli_rejects_mixed_github_and_gitlab_options_before_provider_call(mocker: MockerFixture) -> None:
    selected = mocker.patch.object(pr_review_threads, "review_provider_for_target")

    result = RUNNER.invoke(
        app,
        [
            "fetch",
            "--pr",
            "3",
            "--github",
            "acme/widgets",
            "--provider",
            "gitlab",
            "--host",
            "gitlab.example.test",
            "--repo",
            "group/subgroup/widgets",
        ],
    )

    assert result.exit_code != 0
    assert "cannot be combined" in result.output
    selected.assert_not_called()


def authorized(action: ReplyAction | ResolveAction | TopLevelCommentAction) -> AuthorizedReviewAction:
    """Bind one GitLab action to a normalized input."""
    item = next(item for item in normalize_state(state(), target()).review_inputs if item.input_id == "gitlab:note:10")
    return AuthorizedReviewAction(
        target=target(),
        snapshot_fingerprint="fingerprint",
        revision="head-1",
        review_input=item,
        cluster_id="cluster-1",
        disposition="accepted_change",
        communication_plan="reply",
        inspectable_revision="head-1",
        implementation_evidence=["commit"],
        verification_evidence=["tests"],
        action=action,
    )


def test_cli_does_not_expose_unrequested_approval_mutation() -> None:
    result = RUNNER.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "approval-state" not in result.output


def test_gitlab_provider_satisfies_seam_and_validates_all_mutations(mocker: MockerFixture) -> None:
    fetched = state()
    command = mocker.Mock()
    provider = GitLabProvider(state_loader=mocker.Mock(return_value=fetched), command_runner=command)
    assert isinstance(provider, ReviewProvider)
    assert provider.snapshot(target(), deadline=None, command_timeout=7.0).provider == "gitlab"

    command.return_value = json.dumps({"id": 91, "body": "done"})
    reply = provider.act(target(), authorized(ReplyAction(body="done")), command_timeout=7.0)
    assert reply.provider_object_id == "91"
    assert any("/discussions/discussion-1/notes" in argument for argument in command.call_args.args[0])
    assert authorized(ReplyAction(body="done")).review_input.stable_reference in command.call_args.args[0][-1]

    command.return_value = (
        state()
        .discussions[0]
        .model_copy(update={"notes": [state().discussions[0].notes[0].model_copy(update={"resolved": True})]})
        .model_dump_json()
    )
    resolved = provider.act(target(), authorized(ResolveAction()), command_timeout=7.0)
    assert resolved.resolved is True
    assert "resolved=true" in command.call_args.args[0]

    command.return_value = json.dumps({"id": 92, "body": "done"})
    reference = authorized(ReplyAction(body="unused")).review_input.stable_reference
    comment = provider.act(
        target(), authorized(TopLevelCommentAction(body="done", references=[reference])), command_timeout=7.0
    )
    assert comment.action_kind == "comment"
    assert reference in command.call_args.args[0][-1]


@pytest.mark.parametrize("raw", ["{}", "[]", "not-json"])
def test_gitlab_provider_rejects_unconfirmed_mutations(raw: str, mocker: MockerFixture) -> None:
    provider = GitLabProvider(state_loader=mocker.Mock(), command_runner=mocker.Mock(return_value=raw))
    with pytest.raises(ProviderResponseError):
        provider.act(target(), authorized(ReplyAction(body="done")), command_timeout=2.0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
