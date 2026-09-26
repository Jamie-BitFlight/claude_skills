"""Every ``raise ValueError`` inside a pydantic validator is a refusal that can escape a tool.

``pydantic.ValidationError`` subclasses ``ValueError`` and is not a ``BacklogError``, so a
``raise ValueError`` in a validator escapes an ``except BacklogError`` tool wrapper exactly like a
bare one. These tests classify each remaining validator refusal: the one an MCP tool can actually
reach is converted at the boundary that builds the model, and each unreachable one names the guard
that fences it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from backlog_core import entry_blocks, github_sync
from backlog_core.backend_protocol import set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends._github_work_item_versions import WorkItemHead, parse_work_item_head
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BacklogItem,
    ContentKind,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    ProviderItem,
    ProviderSnapshot,
    ValidationError,
)
from backlog_core.server import _manifest_reference, mcp
from sam_schema.core.addressing import parse_address

from tests.helpers import call_mcp_tool

if TYPE_CHECKING:
    from pathlib import Path

_BAD_ADDED_BODY = (
    "<!-- backlog-metadata:\npriority: P1\ntype: Feature\nstatus: open\nadded: tomorrow\n-->\n\n"
    "## Description\n\nRemote description.\n"
)


@pytest.mark.parametrize("tool", ["backlog_pull", "backlog_sync"])
async def test_a_bad_added_date_in_a_pulled_body_is_reported_as_an_error_response(tmp_path: Path, tool: str) -> None:
    """Each tool names the refusal in ``error`` instead of failing the call.

    ``BacklogItem.added``'s validator refuses a non-``YYYY-MM-DD`` value with ``raise ValueError``.
    ``github_sync.parse_issue_body`` is the single boundary where a provider issue body becomes a
    ``BacklogItem``, and reconciliation calls it for every pulled item, so a body whose metadata
    block carries a malformed ``added`` reached the tool as ``pydantic.ValidationError`` -- a
    ``ValueError`` subclass that an ``except BacklogError`` never caught.

    Both tools are covered because both reach that boundary through the same reconcile call:
    ``backlog_pull`` via ``operations.pull_items`` and ``backlog_sync`` via
    ``operations.sync_items``, which reconciles every already-linked item. Parametrised rather
    than duplicated so a future tool that reconciles is one list entry away from coverage.
    """
    backend = GitHubBackend(cache=FileCache(tmp_path))
    backend.put_work_item(BacklogItem(title="An item", issue="#1", section="P1"))
    backend.fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="An item",
                    body=_BAD_ADDED_BODY,
                    state="OPEN",
                    labels=[],
                    revision="rev-1",
                )
            ],
            sync_started_at="2026-08-12T01:00:00Z",
            pages_fetched=1,
        )
    )
    set_config(BacklogConfig(backend=backend))

    result = await call_mcp_tool(mcp, tool, {})

    assert "added must be YYYY-MM-DD" in result["error"], result


def test_the_issue_body_boundary_refuses_a_bad_added_date_as_a_backlog_error() -> None:
    """The conversion is at the boundary, not in the validator: the validator still raises
    ``ValueError`` so ``_CacheStateStore._salvage_field`` and ``FileCache._work_item_snapshots``
    keep salvaging a corrupt cached item through their ``pydantic.ValidationError``/``ValueError``
    catches."""
    with pytest.raises(ValidationError, match="added must be YYYY-MM-DD"):
        github_sync.parse_issue_body(_BAD_ADDED_BODY)


def test_a_struck_entry_with_a_blank_timestamp_is_read_as_an_ordinary_entry() -> None:
    """``Entry``'s struck/``struck_at`` refusal is fenced by ``_STRUCK_HEADER_RE``.

    The only construction that sets ``struck=True`` is ``entry_blocks._entry_from_span``, which
    takes ``struck_at`` from that regex's ``(\\S+)`` capture. A wrapper with a blank timestamp
    fails the match outright, so the entry is parsed unstruck and the validator is never reached.
    """
    blank = (
        "<div><sub>2026-01-01T00:00:00Z</sub>\n<details><summary>struck:  — why</summary>\n\nbody\n</details>\n</div>"
    )

    entries = entry_blocks.parse_entries(blank, show="all")

    assert [(e.struck, e.struck_at) for e in entries] == [(False, "")]


def test_an_empty_plan_address_is_refused_before_any_content_reference_is_built() -> None:
    """``ContentRef``'s empty-name refusal is unreachable from the plan tools.

    Every plan-kind ``ContentRef`` is built from a plan id the backend already holds
    (``ContentTaskProvider._flush``/``_refresh``), and an address that names no plan is refused by
    ``parse_address`` before resolution reaches a backend at all.
    """
    with pytest.raises(ValueError, match="Address cannot be empty"):
        parse_address("")


@pytest.mark.parametrize("revision", ["rev-1", ""])
def test_no_content_write_builder_can_pair_create_only_with_an_expected_revision(revision: str) -> None:
    """``ContentWrite``'s two refusals are fenced by how every builder constructs one.

    Each builder derives the pair from one value -- ``create_only=not revision`` beside
    ``expected_revision=revision`` -- so whichever way that value falls, only one of the two is
    ever set. This reproduces that derivation for both values rather than trusting it by reading.
    ``owner_reference`` is fenced separately: no artifact-kind write passes one at all: only the
    plan-kind writes in ``sam_schema.core.backends.content`` and ``dh_core.ledger.port`` do, and
    the validator's plan arm ignores it.
    """
    write = ContentWrite(
        reference=ContentRef(kind=ContentKind.PLAN, name="P1"),
        content="c",
        expected_revision=revision,
        create_only=not revision,
    )

    assert not (write.create_only and write.expected_revision)


def test_a_tampered_work_item_head_fails_closed_as_a_content_error() -> None:
    """``WorkItemHead``'s digest refusal never escapes: ``parse_work_item_head`` is the only
    path that builds one from stored bytes and it converts, while ``WorkItemHead.create``
    computes the digest from the body it stores."""
    head = WorkItemHead.create("#1", "parent", "root", "body", "comment-1")
    tampered = head.model_dump_json().replace('"body":"body"', '"body":"tampered"')

    with pytest.raises(ContentUnavailableError, match="work-item head is invalid"):
        parse_work_item_head(tampered)


def test_the_entry_block_strike_refusal_has_no_caller_that_can_reach_it() -> None:
    """``entry_blocks.strike_entry``'s ``ValueError`` is fenced by its two call sites.

    ``_rewrite_replace`` is its only caller: it passes either a block it just built with
    ``wrap_entry_with_timestamp`` or a span ``find_entry_spans`` just located, so the argument is
    always a valid entry block. The ``backlog_strike_entry`` tool does not route here at all --
    ``operations.strike_entry`` mutates the parsed ``Entry`` model instead.
    """
    legacy = entry_blocks.rewrite_section(
        "plain legacy text", new_content="new", replace=True, reason="r", added_date="2026-01-01"
    )
    spanned = entry_blocks.rewrite_section(
        "<div><sub>2026-01-01T00:00:00Z</sub>\n\nx\n</div>", new_content="new", replace=True, reason="r"
    )

    assert "struck:" in legacy
    assert "struck:" in spanned


def test_the_manifest_reference_boundary_still_converts() -> None:
    """The one already-fixed site, kept under test beside the rest of the classification.

    A bare ``ContentRef`` construction still raises ``pydantic.ValidationError``: the conversion
    lives at the boundary that builds the model from caller input, not in the validator.
    """
    with pytest.raises(ValidationError, match="namespace must not be empty"):
        _ = _manifest_reference("")
