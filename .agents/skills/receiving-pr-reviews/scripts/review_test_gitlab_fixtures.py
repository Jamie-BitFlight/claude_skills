"""Shared strict GitLab provider fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pr_review_contracts import ChangeRequestTarget, RepositoryTarget
from pr_review_gitlab_wire import (
    GitLabApprovals,
    GitLabApprovedBy,
    GitLabAwardEmoji,
    GitLabDiffVersion,
    GitLabDiscussion,
    GitLabMergeRequest,
    GitLabNote,
    GitLabPosition,
    GitLabState,
    GitLabUser,
)

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def user(user_id: int, username: str, *, bot: bool = False) -> GitLabUser:
    """Build one strict GitLab actor.

    Args:
        user_id: Provider user identifier.
        username: Provider username.
        bot: Observed bot classification.

    Returns:
        Strict GitLab user fixture.
    """
    return GitLabUser(id=user_id, username=username, name=username.title(), bot=bot)


def note(
    note_id: int,
    author: GitLabUser,
    body: str,
    *,
    system: bool = False,
    resolvable: bool = False,
    resolved: bool | None = None,
    head_sha: str | None = None,
) -> GitLabNote:
    """Build one strict note fixture.

    Args:
        note_id: Provider note identifier and timestamp offset.
        author: Note author.
        body: Complete note body.
        system: Whether GitLab generated the note.
        resolvable: Whether the note's discussion can be resolved.
        resolved: Provider resolution state.
        head_sha: Optional diff position revision.

    Returns:
        Strict GitLab note fixture.
    """
    position = None
    if head_sha is not None:
        position = GitLabPosition(head_sha=head_sha, new_path="src/widget.py", new_line=9)
    return GitLabNote(
        id=note_id,
        body=body,
        author=author,
        created_at=NOW + timedelta(seconds=note_id),
        updated_at=NOW + timedelta(seconds=note_id),
        system=system,
        resolvable=resolvable,
        resolved=resolved,
        position=position,
    )


def target() -> ChangeRequestTarget:
    """Return one self-managed nested GitLab target."""
    return ChangeRequestTarget(
        repository=RepositoryTarget(
            provider="gitlab", hostname="gitlab.example.test", full_name="group/subgroup/widgets"
        ),
        number=3,
    )


def state() -> GitLabState:
    """Return a complete state covering every normalized input surface."""
    author = user(1, "author")
    reviewer = user(2, "reviewer")
    bot = user(3, "review-bot", bot=True)
    current = user(9, "agent")
    discussion = GitLabDiscussion(
        id="discussion-1",
        individual_note=False,
        notes=[
            note(10, reviewer, "This invariant is broken", resolvable=True, resolved=False, head_sha="head-1"),
            note(11, current, "Existing response", resolvable=True, resolved=False, head_sha="head-1"),
        ],
    )
    individual = GitLabDiscussion(
        id="individual-1", individual_note=True, notes=[note(12, reviewer, "Could this be shared?")]
    )
    system = GitLabDiscussion(
        id="system-1", individual_note=True, notes=[note(13, author, "pushed commits", system=True)]
    )
    merge_request = GitLabMergeRequest(
        iid=3,
        sha="head-1",
        web_url="https://gitlab.example.test/group/subgroup/widgets/-/merge_requests/3",
        state="opened",
        draft=False,
        work_in_progress=False,
        has_conflicts=False,
        merge_status="can_be_merged",
        detailed_merge_status="mergeable",
        blocking_discussions_resolved=False,
        author=author,
    )
    return GitLabState(
        merge_request=merge_request,
        discussions=[discussion, individual, system],
        notes=[*discussion.notes, *individual.notes, *system.notes, note(14, bot, "Top-level bot concern")],
        approvals=GitLabApprovals(
            approved=True, approvals_required=1, approvals_left=0, approved_by=[GitLabApprovedBy(user=reviewer)]
        ),
        awards=[
            GitLabAwardEmoji(id=20, name="thumbsup", user=reviewer, created_at=NOW, updated_at=NOW),
            GitLabAwardEmoji(id=21, name="thumbsdown", user=bot, created_at=NOW, updated_at=NOW),
        ],
        versions=[
            GitLabDiffVersion(
                id=1, head_commit_sha="head-1", base_commit_sha="base", start_commit_sha="start", created_at=NOW
            ),
            GitLabDiffVersion(
                id=2,
                head_commit_sha="head-1",
                base_commit_sha="base-2",
                start_commit_sha="start",
                created_at=NOW + timedelta(minutes=1),
            ),
        ],
        current_user=current,
    )
