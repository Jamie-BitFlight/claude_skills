"""Stable model contracts that are not exercised by persisted backlog YAML."""

from __future__ import annotations

import hashlib

import backlog_core.models as bc_models
import pytest
from backlog_core.models import (
    COMMIT_PREFIX_RE,
    TYPE_TO_LABEL,
    BacklogConfig,
    BacklogError,
    BacklogItem,
    DuplicateItemError,
    GitHubUnavailableError,
    IssueLocalFields,
    IssueStatus,
    ItemNotFoundError,
    Output,
    PullRequestRef,
    ValidationError,
    ViewItemResult,
    resolve_repo,
)
from backlog_core.search import ContentDuplicateMatch
from pydantic import ValidationError as PydanticValidationError


class TestBacklogItemReferenceHealing:
    """Every backend stores work items using the derived reference."""

    def test_reference_derivation_and_explicit_override_are_stable(self) -> None:
        assert BacklogItem(title="Tracked", issue="#42").reference == "#42"
        assert BacklogItem(title="Untracked").reference == hashlib.sha256(b"Untracked").hexdigest()
        assert BacklogItem(title="Tracked", reference="explicit-ref").reference == "explicit-ref"

    def test_reference_fallback_is_deterministic_and_survives_reload_projection(self) -> None:
        first = BacklogItem(title="Same title")
        reloaded = BacklogItem.model_validate(first.model_dump())

        assert first.reference == BacklogItem(title="Same title").reference == reloaded.reference


def test_output_keeps_diagnostic_channels_ordered_and_explicit_on_the_wire() -> None:
    output = Output()
    output.info("first")
    output.info("second")
    output.warn("warning")
    output.record_error("error")

    assert output.to_dict() == {"messages": ["first", "second"], "warnings": ["warning"], "errors": ["error"]}


def test_output_instances_do_not_share_diagnostics() -> None:
    first = Output()
    first.info("only first")

    assert Output().to_dict() == {"messages": [], "warnings": [], "errors": []}


def test_public_response_models_carry_complete_provider_values() -> None:
    assert IssueStatus(status="open", milestone="v1").model_dump()["milestone"] == "v1"
    assert ViewItemResult(title="Item", number=7, labels=["type:feature"], groomed="2026-03-01").model_dump()[
        "labels"
    ] == ["type:feature"]
    assert (
        IssueLocalFields(title="Imported", priority="P0", item_type="Bug", status="open", milestone="v2").model_dump()[
            "milestone"
        ]
        == "v2"
    )
    assert PullRequestRef(number=42, title="Fix", url="https://example.test/pull/42").model_dump()["number"] == 42


def test_pull_request_reference_requires_a_number() -> None:
    with pytest.raises(PydanticValidationError, match="number"):
        PullRequestRef.model_validate({"title": "Missing", "url": "https://example.test"})


def test_supported_backlog_exceptions_are_catchable_at_the_tool_boundary() -> None:
    duplicate = ContentDuplicateMatch(title="One", item_ref="#1", matched_field="title", snippet="one", match_count=1)
    for error in (
        ItemNotFoundError("missing"),
        DuplicateItemError([duplicate]),
        GitHubUnavailableError("offline"),
        ValidationError("bad input"),
    ):
        with pytest.raises(BacklogError):
            raise error


def test_item_not_found_and_duplicate_errors_keep_actionable_identifiers() -> None:
    assert str(ItemNotFoundError("wanted")) == "No item found for: wanted"
    single = DuplicateItemError([
        ContentDuplicateMatch(title="Alpha", item_ref="#1", matched_field="title", snippet="one", match_count=1)
    ])
    multiple = DuplicateItemError([
        ContentDuplicateMatch(title="Alpha", item_ref="#1", matched_field="title", snippet="one", match_count=1),
        ContentDuplicateMatch(title="Beta", item_ref="p1-beta", matched_field="body", snippet="two", match_count=2),
    ])

    assert str(single) == 'Similar backlog items found: "Alpha" (#1)'
    assert "#1" in str(multiple)
    assert "p1-beta" in str(multiple)


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        ("feature", "type:feature"),
        ("bug", "type:bug"),
        ("refactor", "type:refactor"),
        ("docs", "type:docs"),
        ("chore", "type:chore"),
    ],
)
def test_type_labels_match_provider_contract(kind: str, label: str) -> None:
    assert TYPE_TO_LABEL[kind] == label


@pytest.mark.parametrize("prefix", ["feat", "fix", "refactor", "docs", "chore", "perf", "test", "ci", "FEAT", "Fix"])
def test_conventional_commit_prefixes_are_removed_from_imported_titles(prefix: str) -> None:
    assert COMMIT_PREFIX_RE.sub("", f"{prefix}: A title") == "A title"


@pytest.mark.parametrize("title", ["A plain title", "wip: A title"])
def test_non_conventional_titles_are_not_rewritten(title: str) -> None:
    assert COMMIT_PREFIX_RE.sub("", title) == title


def test_resolve_repo_uses_the_explicit_slug_or_configured_default(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = bc_models._config
    root = existing.repo_root if existing is not None else bc_models._resolve_repo_root()
    backlog_dir = existing.backlog_dir if existing is not None else bc_models.dh_paths.backlog_dir(root)
    monkeypatch.setattr(
        bc_models, "_config", BacklogConfig(repo_root=root, backlog_dir=backlog_dir, default_repo="owner/default")
    )

    assert resolve_repo("") == "owner/default"
    assert resolve_repo("owner/custom") == "owner/custom"
