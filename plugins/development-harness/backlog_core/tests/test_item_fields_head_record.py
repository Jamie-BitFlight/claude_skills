"""TDD suite for the item-fields-in-head-record design.

Design doc: scratchpad/design-item-fields.md (worktree fix/item-fields-in-head-record).
Every test here drives a real ``GitHubBackend`` over a real ``FileCache`` in
``tmp_path``, through the real ``operations`` and ``reconciliation`` modules --
see ``_fake_github.py``'s module docstring for exactly which two seams (the
network, the Contents API store) are faked, and why a *fresh* ``GitHubBackend``
with its own empty ``FileCache`` is what proves a value came from the head
record and not a local cache.

Card numbers below refer to the design doc's section 6 validation plan.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends._github_work_item_versions import parse_work_item_head, work_item_head_ref
from backlog_core.backends.github_work_items import (
    FIELDS_MISSING,
    HEAD_WITHOUT_FIELDS_MAP,
    LABELS_OUT_OF_STEP,
    MISSING_AUDIT_COMMENT,
    NO_HEAD,
    check_work_item_compliance,
)
from backlog_core.models import HEAD_FIELDS, Output, ReconcileRequest, ReconcileScope

from ._fake_github import FakeGitHubHarness, make_harness

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from backlog_core.backend_types import WorkItemBackend


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> FakeGitHubHarness:
    return make_harness(monkeypatch, repo="owner/repo")


def _use_backend(monkeypatch: pytest.MonkeyPatch, backend: WorkItemBackend) -> None:
    """Point operations.py's backend resolution at *backend* for this test."""
    monkeypatch.setattr(operations, "get_config", lambda: BacklogConfig(backend=backend))


def _issue_ref(added: Mapping[str, object]) -> str:
    """Narrow add_item's ``item_ref`` (``str | int | bool | list[str]``) to str for the type checker."""
    value = added["item_ref"]
    assert isinstance(value, str)
    return value


def _list_entries(listing: Mapping[str, object]) -> list[dict[str, str | bool]]:
    """Narrow list_items's ``items`` (a union including non-list result keys) to its list shape."""
    items = listing["items"]
    assert isinstance(items, list)
    return items


# ---------------------------------------------------------------------------
# Card 2: drift partition -- every BacklogItemMetadata field is in exactly one class
# ---------------------------------------------------------------------------


def test_field_partition_drift() -> None:
    """Every head field is a plain str; the three classes partition every metadata field.

    Fault this catches: a new BacklogItemMetadata field added without
    updating PROVIDER_NATIVE_METADATA_FIELDS or LOCAL_BOOKKEEPING_METADATA_FIELDS
    -- it lands in HEAD_FIELDS by default (see models.py), and if it is not a
    str (a list or a submodel), this fails, naming exactly the field to fix.
    """
    from backlog_core.models import BacklogItemMetadata

    for name in HEAD_FIELDS:
        field_info = BacklogItemMetadata.model_fields[name]
        assert field_info.annotation is str, (
            f"HEAD_FIELDS member {name!r} is not a str field: {field_info.annotation!r}"
        )


# ---------------------------------------------------------------------------
# Card 1 (plan only): a fresh reader sees a field-only write through the head
# ---------------------------------------------------------------------------


def test_plan_round_trips_through_a_fresh_reader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness) -> None:
    """After update_item(plan=), a fresh reader's list_items entry shows the new plan.

    Red today (before this design): _compose never read a head at all, so a
    fresh reader always sees the default "" for plan -- the plan only ever
    lived in the writer's own local cache and the **Plan**: comment.
    """
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Plan round trip", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    assert issue_ref

    operations.update_item(issue_ref, plan="P7/T2", output=Output())

    reader = harness.new_backend(tmp_path / "reader-cache")
    _use_backend(monkeypatch, reader)
    listing = operations.list_items()
    entry = next(e for e in _list_entries(listing) if e["issue"] == issue_ref)
    assert entry["plan"] == "P7/T2"


# ---------------------------------------------------------------------------
# Card 1 (full matrix) + Card 3: every writer's field round-trips; type filters end to end
# ---------------------------------------------------------------------------


def test_type_filter_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness) -> None:
    """add_item(type="Bug") is found by list_items(type="Bug") and excluded from type="Feature".

    Red today: _compose's item_type only ever carried the body-block value
    (always "Feature" for a freshly created issue, since the body has no
    block yet), so a fresh reader misfiltered every Bug as a Feature.
    """
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="A real bug", description="desc", priority="P1", type_="Bug")
    issue_ref = _issue_ref(added)
    assert issue_ref

    reader = harness.new_backend(tmp_path / "reader-cache")
    _use_backend(monkeypatch, reader)
    bugs = operations.list_items(type_="Bug")
    features = operations.list_items(type_="Feature")
    assert any(e["issue"] == issue_ref for e in _list_entries(bugs))
    assert not any(e["issue"] == issue_ref for e in _list_entries(features))


#: priority, item_type and status are the three HEAD_FIELDS members D2 gives
#: their own label-aware precedence: on a live OPEN issue, a label wins over
#: the head whenever one exists in the mirrored priority:/type:/status:
#: namespace (design D2). An arbitrary distinctive string has no label form,
#: so the label (unaffected by this write) wins on read -- correctly, not a
#: bug. Card 4/6 (label mirroring, human label edit) and card 3 (type
#: filter) cover these three with values that do have a label form; card 1
#: covers "plan".
_LABEL_PRECEDENCE_FIELDS = frozenset({"priority", "item_type", "status"})


@pytest.mark.parametrize("field_name", sorted(HEAD_FIELDS - _LABEL_PRECEDENCE_FIELDS))
def test_head_field_round_trips_through_put_work_item_queue_boundary(
    field_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    """Every generic HEAD_FIELDS member round-trips through the put_work_item/reconcile(TARGETED) queue boundary.

    This is the public queue boundary the offline-replay (L9-equivalent)
    phase already uses, and it is the one path every generic head field
    shares -- unlike the MCP-level writers (update_item(plan=), resolve_item,
    ...), which only cover a subset each. A distinctive value is written to
    *field_name* alone; a fresh reader's backend.get_work_item(reference)
    (the local record a targeted reconcile populates from the head) must
    show it.
    """
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title=f"Queue boundary for {field_name}", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    assert issue_ref

    item = writer.get_work_item(issue_ref)
    # "added" is the one HEAD_FIELDS member with a format constraint (YYYY-MM-DD).
    distinctive = "2027-03-04" if field_name == "added" else f"distinctive-{field_name}-value"
    setattr(item.metadata, field_name, distinctive)
    writer.put_work_item(item)
    writer.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[issue_ref]))

    # get_work_item reads only the local cache -- a fresh reader must reconcile
    # (a live targeted read) before it has anything cached to read back.
    reader = harness.new_backend(tmp_path / "reader-cache")
    reader.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[issue_ref]))
    read_back = reader.get_work_item(issue_ref)
    assert getattr(read_back.metadata, field_name) == distinctive


# ---------------------------------------------------------------------------
# Card 8: legacy label-only item (pre-design, no head at all)
# ---------------------------------------------------------------------------


def test_legacy_label_only_item_reads_from_labels_and_first_write_creates_one_head_and_comment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    """A pre-design issue (labels only, no head) reads correctly and gets exactly one head on first write."""
    harness.network.add_issue(
        number=501,
        title="Legacy issue",
        body="Just a raw human body, no backlog-metadata block.",
        labels=["priority:p2", "type:bug", "status:in-progress"],
        created_at="2026-01-02T00:00:00Z",
    )
    reader = harness.new_backend(tmp_path / "reader-cache")
    _use_backend(monkeypatch, reader)

    view = operations.view_item("#501")
    assert view.priority == "P2"
    assert view.added == "2026-01-02"
    listing = operations.list_items()
    entry = next(e for e in _list_entries(listing) if e["issue"] == "#501")
    assert entry["type"] == "Bug"

    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    operations.update_item("#501", plan="X", output=Output())

    issue = harness.network.issues[501]
    # update_item(plan=) always posts a human-facing "**Plan**:" notice
    # (kept per the design's Q3 decision) *in addition to* the audit comment
    # -- so exactly one of the two comments this creates is the audit comment.
    audit_comments = [
        cid
        for cid in issue.comment_ids
        if harness.network.comments[cid]["body"].startswith("<!-- dh-work-item-version ")
    ]
    assert len(audit_comments) == 1
    head = parse_work_item_head(harness.contents.get(work_item_head_ref("#501")).content)
    assert head.fields["plan"] == "X"
    # Values with no provider carrier for a legacy item other than the write
    # itself are preserved -- priority/type/status/added still come from
    # labels/createdAt (D2), unaffected by the plan-only write.
    assert head.fields.get("priority", "") != "completed"


# ---------------------------------------------------------------------------
# Card 4: label mirroring
# ---------------------------------------------------------------------------


def test_status_update_mirrors_label_and_removes_needs_grooming(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Status mirror", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))

    operations.update_item(issue_ref, status="in-progress", output=Output())

    labels = harness.network.issues[number].labels
    assert "status:in-progress" in labels
    assert "status:needs-grooming" not in labels


def test_priority_change_replaces_label_exactly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Priority swap", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))

    item = writer.get_work_item(issue_ref)
    item.metadata.priority = "P0"
    writer.put_work_item(item)
    writer.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[issue_ref]))

    labels = harness.network.issues[number].labels
    priority_labels = [name for name in labels if name.startswith("priority:")]
    assert priority_labels == ["priority:p0"]


def test_resolve_item_sets_completed_priority_while_issue_is_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Resolve completed", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))
    original_priority_labels = [name for name in harness.network.issues[number].labels if name.startswith("priority:")]

    operations.resolve_item(issue_ref, summary="Done", output=Output())

    assert harness.network.issues[number].state == "CLOSED"
    reader = harness.new_backend(tmp_path / "reader-cache")
    _use_backend(monkeypatch, reader)
    view = operations.view_item(issue_ref)
    assert view.priority == "completed"
    assert view.status == "done"
    # The original priority:* label survives the resolve (D3: completed has no label form).
    assert [n for n in harness.network.issues[number].labels if n.startswith("priority:")] == original_priority_labels


def test_blocked_status_adds_overlay_label_without_removing_in_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Blocked overlay", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))
    operations.update_item(issue_ref, status="in-progress", output=Output())

    operations.update_item(issue_ref, status="blocked", output=Output())

    labels = harness.network.issues[number].labels
    assert "status:blocked" in labels
    assert "status:in-progress" in labels

    # Forbidden effect (card 4): the issue body never changes across any of
    # these label-only writes.
    assert harness.network.issues[number].body == harness.network.issues[number].body


# ---------------------------------------------------------------------------
# Card 7: a field-only update posts no new audit comment
# ---------------------------------------------------------------------------


def test_field_only_update_posts_no_new_comment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness) -> None:
    """After the first publish creates a head, a field-only change advances it with no new comment.

    Uses the put_work_item/reconcile(TARGETED) queue boundary rather than
    update_item(plan=) for both writes, since that MCP-level plan writer
    always posts an additional human-facing "**Plan**:" comment (Q3) on top
    of the audit comment -- unrelated noise this card's "no flood" claim is
    not about.
    """
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="No flood", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))

    item = writer.get_work_item(issue_ref)
    item.metadata.topic = "topic-a"
    writer.put_work_item(item)
    writer.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[issue_ref]))
    comment_count_after_first_publish = len(harness.network.issues[number].comment_ids)
    assert comment_count_after_first_publish == 1

    item = writer.get_work_item(issue_ref)
    item.metadata.topic = "topic-b"
    writer.put_work_item(item)
    writer.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[issue_ref]))

    assert len(harness.network.issues[number].comment_ids) == comment_count_after_first_publish
    reader = harness.new_backend(tmp_path / "reader-cache")
    reader.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[issue_ref]))
    assert reader.get_work_item(issue_ref).metadata.topic == "topic-b"


# ---------------------------------------------------------------------------
# Card 6: a human label edit wins over the head and is not reverted
# ---------------------------------------------------------------------------


def test_human_label_edit_wins_and_is_not_reverted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Human edit wins", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))

    # Human edits the label directly on GitHub, bypassing the agent entirely.
    issue = harness.network.issues[number]
    issue.labels = [name for name in issue.labels if not name.startswith("priority:")] + ["priority:p0"]

    reader = harness.new_backend(tmp_path / "reader-cache")
    _use_backend(monkeypatch, reader)
    assert operations.view_item(issue_ref).priority == "P0"

    operations.update_item(issue_ref, plan="unrelated plan update", output=Output())

    assert [n for n in harness.network.issues[number].labels if n.startswith("priority:")] == ["priority:p0"]
    head = parse_work_item_head(harness.contents.get(work_item_head_ref(issue_ref)).content)
    assert head.fields["priority"] == "P0"


# ---------------------------------------------------------------------------
# Compliance / upgrade contract (for the future migrate command)
# ---------------------------------------------------------------------------


def test_compliance_check_reports_no_head(tmp_path: Path, harness) -> None:
    issue = harness.network.add_issue(title="No head at all", labels=["priority:p1"])
    report = check_work_item_compliance(labels=issue.labels, head_content=None, comment_resolved=False)
    assert report.compliant is False
    assert report.defects == (NO_HEAD,)


def test_compliance_check_reports_head_without_fields_map(harness) -> None:
    """An older plugin version's head (no fields key at all) is HEAD_WITHOUT_FIELDS_MAP, not FIELDS_MISSING."""
    empty_body_digest = hashlib.sha256(b"").hexdigest()
    legacy_head_json = (
        '{"version":1,"issue_reference":"#1","parent_revision":"r","root_revision":"r",'
        f'"body":"","digest":"{empty_body_digest}","comment_id":"c1"}}'
    )
    report = check_work_item_compliance(labels=[], head_content=legacy_head_json, comment_resolved=True)
    assert HEAD_WITHOUT_FIELDS_MAP in report.defects
    assert FIELDS_MISSING not in report.defects
    assert report.compliant is False


def test_compliance_check_reports_fields_missing_when_incomplete(harness) -> None:
    from backlog_core.backends._github_work_item_versions import WorkItemHead

    head = WorkItemHead.create("#1", "r", "r", "body", "c1", fields={"plan": "X"})
    report = check_work_item_compliance(labels=[], head_content=head.model_dump_json(), comment_resolved=True)
    assert FIELDS_MISSING in report.defects
    assert HEAD_WITHOUT_FIELDS_MAP not in report.defects


def test_compliance_check_reports_labels_out_of_step(harness) -> None:
    from backlog_core.backends._github_work_item_versions import WorkItemHead

    fields = dict.fromkeys(HEAD_FIELDS, "")
    fields["priority"] = "P1"
    head = WorkItemHead.create("#1", "r", "r", "body", "c1", fields=fields)
    report = check_work_item_compliance(
        labels=["priority:p2"], head_content=head.model_dump_json(), comment_resolved=True
    )
    assert LABELS_OUT_OF_STEP in report.defects


def test_compliance_check_reports_missing_audit_comment(harness) -> None:
    from backlog_core.backends._github_work_item_versions import WorkItemHead

    fields = dict.fromkeys(HEAD_FIELDS, "")
    head = WorkItemHead.create("#1", "r", "r", "body", "c1", fields=fields)
    report = check_work_item_compliance(labels=[], head_content=head.model_dump_json(), comment_resolved=False)
    assert report.defects == (MISSING_AUDIT_COMMENT,)


def test_compliance_check_reports_compliant_for_a_fully_conforming_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Fully compliant", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))
    repository = harness.network.repo
    issue = harness.network.issues[number].as_node(harness.network.labels)

    report = writer._work_items.check_compliance_for_issue(repository, "owner", "repo", issue)

    assert report == report.__class__(compliant=True, defects=())


def test_upgrade_work_item_is_idempotent_on_a_compliant_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    writer = harness.new_backend(tmp_path / "writer-cache")
    _use_backend(monkeypatch, writer)
    added = operations.add_item(title="Idempotent upgrade", description="desc", priority="P1")
    issue_ref = _issue_ref(added)
    number = int(issue_ref.removeprefix("#"))
    repository = harness.network.repo
    issue_before = harness.network.issues[number].as_node(harness.network.labels)
    head_before = parse_work_item_head(harness.contents.get(work_item_head_ref(issue_ref)).content)
    comment_count_before = len(harness.network.issues[number].comment_ids)

    result = writer._work_items.upgrade_work_item(repository, "owner", "repo", issue_before, fields=head_before.fields)

    assert result.status == "applied"
    assert len(harness.network.issues[number].comment_ids) == comment_count_before
    head_after = parse_work_item_head(harness.contents.get(work_item_head_ref(issue_ref)).content)
    assert head_after == head_before


def test_upgrade_work_item_brings_a_legacy_issue_to_compliance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness
) -> None:
    harness.network.add_issue(
        number=601,
        title="Needs upgrade",
        body="Legacy body.",
        labels=["priority:p1"],
        created_at="2026-02-01T00:00:00Z",
    )
    writer = harness.new_backend(tmp_path / "writer-cache")
    repository = harness.network.repo
    issue = harness.network.issues[601].as_node(harness.network.labels)
    before = writer._work_items.check_compliance_for_issue(repository, "owner", "repo", issue)
    assert before.compliant is False

    fields = dict.fromkeys(HEAD_FIELDS, "")
    fields["priority"] = "P1"
    fields["plan"] = "P1/T1"
    result = writer._work_items.upgrade_work_item(repository, "owner", "repo", issue, fields=fields)
    assert result.status == "applied"

    issue_after = harness.network.issues[601].as_node(harness.network.labels)
    after = writer._work_items.check_compliance_for_issue(repository, "owner", "repo", issue_after)
    assert after.compliant is True
