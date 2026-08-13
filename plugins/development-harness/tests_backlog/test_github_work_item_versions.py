from __future__ import annotations

from _thread import LockType
from collections.abc import Sequence
from threading import Barrier, Lock, Thread
from unittest.mock import MagicMock

import pytest
from backlog_core.backend_types import IssueCommentNode
from backlog_core.backends._github_work_item_versions import (
    WorkItemHead,
    parse_work_item_comment,
    parse_work_item_head,
    render_work_item_comment,
    root_revision,
    work_item_head_ref,
)
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.models import (
    ContentConflictError,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    PatchResult,
    ProviderPatch,
    ReconcileRequest,
    ReconcileScope,
)


def _comment(comment_id: str, parent_revision: str, body: str) -> IssueCommentNode:
    return IssueCommentNode(
        id=comment_id,
        body=render_work_item_comment(parent_revision, body),
        url=f"https://example.test/comments/{comment_id}",
        author="agent",
        created_at="2026-08-12T00:00:00Z",
        updated_at="2026-08-12T00:00:00Z",
    )


def test_github_work_item_head_binds_initial_content_to_issue_identity_and_root() -> None:
    # Given: a human-owned Issue body with no prior agent head
    root = root_revision("#42", "issue-node", "Human-owned body")

    # When: an initial agent body is made into the authoritative head envelope
    head = WorkItemHead.create("#42", root, root, "rendered body", "comment-1")

    # Then: the head preserves the exact root and auditable projection identity
    assert (head.issue_reference, head.parent_revision, head.root_revision, head.body, head.comment_id) == (
        "#42",
        root,
        root,
        "rendered body",
        "comment-1",
    )


def test_github_work_item_head_subsequent_publish_chains_from_prior_head_sha() -> None:
    # Given: an existing authoritative head revision and validated first projection
    root = root_revision("#42", "issue-node", "Human-owned body")
    first = WorkItemHead.create("#42", root, root, "first rendered", "comment-1")

    # When: the next head uses the previous Contents SHA as its parent revision
    second = WorkItemHead.create("#42", "head-sha-1", first.root_revision, "second rendered", "comment-2")

    # Then: the new head preserves root provenance while chaining from the actual prior head
    assert (second.parent_revision, second.root_revision, second.body) == ("head-sha-1", root, "second rendered")


def test_github_work_item_root_revision_changes_when_human_body_changes() -> None:
    # Given: two human Issue bodies for the same Issue
    # When: their canonical root revisions are calculated
    # Then: identity-bound digests distinguish a human body edit and a different Issue
    assert root_revision("#42", "issue-node", "before") != root_revision("#42", "issue-node", "after")
    assert root_revision("#42", "issue-node", "before") != root_revision("#42", "other-node", "before")


def test_github_work_item_sibling_heads_preserve_common_parent_and_distinct_audits() -> None:
    # Given: two prospective heads based on the same observed root
    root = root_revision("#42", "issue-node", "Human-owned body")

    # When: each writer constructs its independent audit proposal
    siblings = [
        WorkItemHead.create("#42", root, root, "writer one", "comment-1"),
        WorkItemHead.create("#42", root, root, "writer two", "comment-2"),
    ]

    # Then: CAS receives the same parent while audit identity and content remain distinct
    assert {head.parent_revision for head in siblings} == {root}
    assert len({(head.digest, head.comment_id) for head in siblings}) == 2


@pytest.mark.parametrize(
    ("comment", "error"),
    [
        (None, "missing"),
        ({**_comment("comment-1", "root", "rendered"), "body": "forged"}, "invalid"),
        ({**_comment("comment-1", "root", "rendered"), "id": "other"}, "identity"),
    ],
)
def test_github_work_item_rejects_missing_forged_or_replaced_audit_comment(
    comment: IssueCommentNode | None, error: str
) -> None:
    # Given: an authoritative head requiring comment-1 with the rendered digest
    head = WorkItemHead.create("#42", "root", "root", "rendered", "comment-1")

    # When: audit projection validation receives an invalid remote comment state
    with pytest.raises(ContentUnavailableError, match=error):
        parse_work_item_comment(head, comment)

    # Then: malformed, edited, or deleted audit data cannot project as authoritative content


def test_github_work_item_rejects_digest_mismatch_in_authoritative_head() -> None:
    # Given: a serialized head envelope with content altered after its digest was computed
    valid = WorkItemHead.create("#42", "root", "root", "rendered", "comment-1").model_dump()
    valid["body"] = "tampered"

    # When: the head crosses the Contents envelope boundary
    with pytest.raises(ValueError, match="digest"):
        WorkItemHead.model_validate(valid)

    # Then: a Contents SHA alone cannot make tampered logical head content valid


class _ContentsFake:
    def __init__(self, barrier: Barrier | None = None) -> None:
        self._barrier = barrier
        self._records: dict[str, ContentRecord] = {}
        self._lock = Lock()
        self._revision = 0

    def get(self, reference: ContentRef) -> ContentRecord:
        try:
            return self._records[reference.model_dump_json()]
        except KeyError as exc:
            raise ContentNotFoundError("head missing") from exc

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        records = [
            record
            for record in self._records.values()
            if record.reference.kind == query.kind
            and query.search.casefold() in record.reference.name.casefold()
            and (query.owner_reference is None or record.owner_reference == query.owner_reference)
        ]
        records.sort(key=lambda record: record.reference.model_dump_json())
        return records[query.offset : query.offset + query.limit]

    def put(self, request: ContentWrite) -> ContentRecord:
        if request.create_only and self._barrier is not None:
            self._barrier.wait()
        key = request.reference.model_dump_json()
        with self._lock:
            current = self._records.get(key)
            if request.create_only and current is not None:
                raise ContentConflictError("head exists")
            if request.expected_revision and (current is None or current.revision != request.expected_revision):
                raise ContentConflictError("head changed")
            self._revision += 1
            record = ContentRecord(
                reference=request.reference, content=request.content, revision=f"head-{self._revision}"
            )
            self._records[key] = record
            return record


def _issue(body: str = "Human-owned body") -> dict[str, object]:
    return {
        "id": "issue-node",
        "number": 42,
        "title": "Human title",
        "body": body,
        "state": "OPEN",
        "labels": [{"id": "label-1", "name": "feature"}],
        "updatedAt": "changed-without-semantic-authority",
        "createdAt": "2026-08-12T00:00:00Z",
        "milestone": None,
        "assignees": [],
    }


def _backend(
    contents: _ContentsFake, comments: dict[str, IssueCommentNode], comment_lock: LockType | None = None
) -> GitHubBackend:
    backend = GitHubBackend(contents=contents)
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_targeted_issues = MagicMock(
        side_effect=lambda _repo, _owner, _name, references: {ref: _issue() for ref in references}
    )
    backend._fetch_issues_graphql = MagicMock(return_value=[_issue()])
    backend._fetch_comment_by_id_graphql = MagicMock(side_effect=lambda _repo, comment_id: comments[comment_id])

    lock = comment_lock or Lock()

    def add_comment(_repo: object, _issue_id: str, body: str) -> str:
        with lock:
            comment_id = f"comment-{len(comments) + 1}"
            comments[comment_id] = IssueCommentNode(
                id=comment_id,
                body=body,
                url=f"https://example.test/comments/{comment_id}",
                author="agent",
                created_at="2026-08-12T00:00:00Z",
                updated_at="2026-08-12T00:00:00Z",
            )
        return comment_id

    backend._add_comment_graphql = MagicMock(side_effect=add_comment)
    return backend


def test_github_work_item_backend_publishes_initial_then_subsequent_contents_heads() -> None:
    # Given: an Issue with no head and a deterministic Contents CAS fake
    comments: dict[str, IssueCommentNode] = {}
    contents = _ContentsFake()
    backend = _backend(contents, comments)
    root = root_revision("#42", "issue-node", "Human-owned body")

    # When: the first and second rendered bodies publish against their observed authoritative revisions
    [first] = backend._apply_patches([
        ProviderPatch(provider_id="issue-node", reference="#42", expected_revision=root, body="first")
    ])
    [second] = backend._apply_patches([
        ProviderPatch(provider_id="issue-node", reference="#42", expected_revision=first.revision, body="second")
    ])

    # Then: Contents SHAs become revisions and both append-only audit comments remain intact
    assert (first.status, second.status, second.revision) == ("applied", "applied", "head-2")
    assert [(comment_id, comment["body"].split("\n", 1)[1]) for comment_id, comment in comments.items()] == [
        ("comment-1", "first"),
        ("comment-2", "second"),
    ]


def test_github_work_item_backend_human_body_change_invalidates_prior_head() -> None:
    # Given: a stored head rooted in the prior human Issue body
    comments: dict[str, IssueCommentNode] = {"comment-1": _comment("comment-1", "root", "rendered")}
    contents = _ContentsFake()
    old_root = root_revision("#42", "issue-node", "before")
    head = WorkItemHead.create("#42", old_root, old_root, "rendered", "comment-1")
    contents.put(ContentWrite(reference=work_item_head_ref("#42"), content=head.model_dump_json(), create_only=True))
    backend = _backend(contents, comments)
    backend._fetch_issues_graphql = MagicMock(return_value=[_issue("after")])
    backend._fetch_targeted_issues = MagicMock(return_value={"#42": _issue("after")})

    # When: snapshot sees a human body whose identity-bound root digest differs
    [item] = backend._fetch_snapshot(ReconcileRequest(scope=ReconcileScope.INITIAL)).items

    # Then: the obsolete head is ignored and the human Issue body/root become current
    assert (item.body, item.revision) == ("after", root_revision("#42", "issue-node", "after"))

    # When: an agent publishes from the new root revision
    [patched] = backend._apply_patches([
        ProviderPatch(provider_id="issue-node", reference="#42", expected_revision=item.revision, body="new rendered")
    ])

    # Then: the stale head is replaced through its old Contents SHA and binds the new root
    stored = parse_work_item_head(contents.get(work_item_head_ref("#42")).content)
    assert (patched.status, stored.root_revision, stored.body) == ("applied", item.revision, "new rendered")


def test_github_work_item_snapshot_batches_heads_and_audit_comments() -> None:
    contents = _ContentsFake()
    issues = [_issue(), {**_issue(), "id": "issue-node-43", "number": 43}]
    first_root = root_revision("#42", "issue-node", "Human-owned body")
    second_root = root_revision("#43", "issue-node-43", "Human-owned body")
    heads = [
        WorkItemHead.create("#42", first_root, first_root, "first", "comment-1"),
        WorkItemHead.create("#43", second_root, second_root, "second", "comment-2"),
    ]
    for reference, head in zip(("#42", "#43"), heads, strict=True):
        contents.put(
            ContentWrite(reference=work_item_head_ref(reference), content=head.model_dump_json(), create_only=True)
        )
    backend = _backend(contents, {})
    backend._contents = MagicMock(wraps=contents)
    backend._fetch_issues_graphql = MagicMock(return_value=issues)
    backend._graphql_request = MagicMock(
        return_value={
            "nodes": [
                {
                    "id": f"comment-{index}",
                    "body": render_work_item_comment(head.parent_revision, head.body),
                    "url": f"https://example.test/comments/{index}",
                    "author": {"login": "agent"},
                    "createdAt": "2026-08-12T00:00:00Z",
                    "updatedAt": "2026-08-12T00:00:00Z",
                }
                for index, head in enumerate(heads, 1)
            ]
        }
    )

    snapshot = backend._fetch_snapshot(ReconcileRequest(scope=ReconcileScope.INITIAL))

    assert [(item.reference, item.body) for item in snapshot.items] == [("#42", "first"), ("#43", "second")]
    backend._contents.get.assert_not_called()
    backend._contents.list.assert_called_once()
    backend._graphql_request.assert_called_once()


def test_github_work_item_backend_concurrent_initial_cas_has_one_winner_and_two_audit_comments() -> None:
    # Given: two writers racing through the same initial Contents create-only boundary
    comments: dict[str, IssueCommentNode] = {}
    contents = _ContentsFake(Barrier(2))
    comment_lock = Lock()
    root = root_revision("#42", "issue-node", "Human-owned body")
    results: list[PatchResult] = []

    def publish(body: str) -> None:
        backend = _backend(contents, comments, comment_lock)
        results.append(
            backend._apply_patches([
                ProviderPatch(provider_id="issue-node", reference="#42", expected_revision=root, body=body)
            ])[0]
        )

    # When: both writers append an audit comment and attempt the same head CAS
    writers = [Thread(target=publish, args=("one",)), Thread(target=publish, args=("two",))]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join()

    # Then: one Contents head wins, while both comments remain forensic evidence
    assert sorted(result.status for result in results) == ["applied", "conflict"]
    assert sorted(comment["body"].split("\n", 1)[1] for comment in comments.values()) == ["one", "two"]
