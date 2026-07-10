"""Tests for the fragment-to-layer ETL in merge_layer.py.

Covers the documented public contract: node/edge removal-and-replacement by
``source_file``, bootstrap of a missing layer file, atomic write, and the
idempotency invariant (spec Section 4.2). See the merge_layer module
docstring for the full contract this module implements.
"""

from __future__ import annotations

import json
from pathlib import Path as _Path
from typing import TYPE_CHECKING

from merge_layer import (
    ExtractionFragment,
    MergeResult,
    merge_fragment,
    parse_extraction_fragment,
    parse_layer_json,
    read_layer,
    write_layer,
)

if TYPE_CHECKING:
    from pathlib import Path


def _fragment(
    source_file: str,
    items: list[dict[str, object]] | None = None,
    edges: list[dict[str, object]] | None = None,
    unverified_items: list[dict[str, object]] | None = None,
) -> ExtractionFragment:
    """Build a minimal, valid ExtractionFragment for tests."""
    return ExtractionFragment(
        source_file=_Path(source_file),
        layer_type="step",
        extracted_at="2026-07-10T00:00:00Z",
        items=tuple(items or []),
        unverified_items=tuple(unverified_items or []),
        edges=tuple(edges or []),
    )


class TestParseExtractionFragment:
    def test_edges_defaults_to_empty_when_key_absent(self) -> None:
        raw = {
            "meta": {
                "source_file": "a.py",
                "layer_type": "step",
                "extracted_at": "2026-07-10T00:00:00Z",
                "verified_count": 0,
                "unverified_count": 0,
            },
            "items": [],
            "unverified_items": [],
        }
        fragment = parse_extraction_fragment(raw)
        assert fragment.edges == ()

    def test_edges_parsed_when_present(self) -> None:
        raw = {
            "meta": {
                "source_file": "a.py",
                "layer_type": "step",
                "extracted_at": "2026-07-10T00:00:00Z",
                "verified_count": 0,
                "unverified_count": 0,
            },
            "items": [],
            "unverified_items": [],
            "edges": [{"from": "n1", "to": "n2"}],
        }
        fragment = parse_extraction_fragment(raw)
        assert fragment.edges == ({"from": "n1", "to": "n2"},)


class TestMergeFragmentNodes:
    def test_bootstrap_missing_layer_file(self, tmp_path: Path) -> None:
        layer_path = tmp_path / "step.json"
        fragment = _fragment("a.py", items=[{"id": "n1"}])

        result = merge_fragment(layer_path, fragment)

        assert layer_path.exists()
        assert result.removed_count == 0
        assert result.added_count == 1
        assert result.total_after == 1
        layer = read_layer(layer_path)
        assert layer.nodes == [{"id": "n1", "source_file": "a.py"}]

    def test_reextraction_replaces_only_that_files_nodes(self, tmp_path: Path) -> None:
        layer_path = tmp_path / "step.json"
        merge_fragment(layer_path, _fragment("a.py", items=[{"id": "n1"}]))
        merge_fragment(layer_path, _fragment("b.py", items=[{"id": "n2"}]))

        result = merge_fragment(layer_path, _fragment("a.py", items=[{"id": "n1-v2"}]))

        layer = read_layer(layer_path)
        node_ids = {node["id"] for node in layer.nodes}
        assert node_ids == {"n1-v2", "n2"}
        assert result.removed_count == 1
        assert result.added_count == 1


class TestMergeFragmentEdges:
    def test_reextraction_with_edges_replaces_that_files_edges_only(self, tmp_path: Path) -> None:
        """Re-extraction with edges in the fragment replaces that file's edges
        without touching other files' edges -- the fix for the edge-data-loss
        bug: fragments can now carry edges through re-extraction instead of
        having them permanently deleted."""
        layer_path = tmp_path / "step.json"
        merge_fragment(
            layer_path, _fragment("a.py", items=[{"id": "n1"}], edges=[{"from": "n1", "to": "n2", "kind": "calls"}])
        )
        merge_fragment(
            layer_path, _fragment("b.py", items=[{"id": "n2"}], edges=[{"from": "n2", "to": "n3", "kind": "calls"}])
        )

        # Re-extract a.py with a different edge set.
        result = merge_fragment(
            layer_path, _fragment("a.py", items=[{"id": "n1"}], edges=[{"from": "n1", "to": "n3", "kind": "invokes"}])
        )

        layer = read_layer(layer_path)
        edges_by_source = {(e["source_file"], e["from"], e["to"]) for e in layer.edges}
        assert edges_by_source == {
            ("a.py", "n1", "n3"),  # replaced a.py edge
            ("b.py", "n2", "n3"),  # untouched b.py edge
        }
        assert result.edges_removed_count == 1
        assert result.edges_added_count == 1
        assert result.edges_total_after == 2

    def test_fragment_without_edges_removes_stale_edges_for_that_file(self, tmp_path: Path) -> None:
        """A fragment that carries no edges for its source_file is documented,
        intentional behavior: it clears that file's prior edges from the layer,
        the same way an empty items list clears that file's prior nodes."""
        layer_path = tmp_path / "step.json"
        merge_fragment(
            layer_path, _fragment("a.py", items=[{"id": "n1"}], edges=[{"from": "n1", "to": "n2", "kind": "calls"}])
        )

        result = merge_fragment(layer_path, _fragment("a.py", items=[{"id": "n1"}], edges=[]))

        layer = read_layer(layer_path)
        assert layer.edges == []
        assert result.edges_removed_count == 1
        assert result.edges_added_count == 0
        assert result.edges_total_after == 0

    def test_idempotent_double_merge_byte_identical(self, tmp_path: Path) -> None:
        """Applying the same fragment to the same layer twice in a row produces
        byte-identical file content both times (spec Section 4.2 idempotency
        invariant), including when the fragment carries edges."""
        layer_path = tmp_path / "step.json"
        fragment = _fragment(
            "a.py", items=[{"id": "n1"}, {"id": "n2"}], edges=[{"from": "n1", "to": "n2", "kind": "calls"}]
        )

        merge_fragment(layer_path, fragment)
        first_bytes = layer_path.read_bytes()

        result = merge_fragment(layer_path, fragment)
        second_bytes = layer_path.read_bytes()

        assert first_bytes == second_bytes
        assert result.removed_count == 2
        assert result.added_count == 2
        assert result.edges_removed_count == 1
        assert result.edges_added_count == 1

    def test_edges_meta_total_edges_refreshed_when_present(self, tmp_path: Path) -> None:
        layer_path = tmp_path / "step.json"
        layer_path.write_text(
            json.dumps({"meta": {"total_nodes": 0, "total_edges": 0}, "nodes": [], "edges": []}), encoding="utf-8"
        )

        merge_fragment(
            layer_path, _fragment("a.py", items=[{"id": "n1"}], edges=[{"from": "n1", "to": "n1", "kind": "self"}])
        )

        raw = json.loads(layer_path.read_text(encoding="utf-8"))
        assert raw["meta"]["total_edges"] == 1


class TestReadWriteLayerRoundTrip:
    def test_round_trip_preserves_edges(self, tmp_path: Path) -> None:
        layer_path = tmp_path / "step.json"
        layer = parse_layer_json({
            "meta": {},
            "nodes": [],
            "edges": [{"from": "n1", "to": "n2", "source_file": "a.py"}],
        })
        write_layer(layer_path, layer)

        reread = read_layer(layer_path)
        assert reread.edges == [{"from": "n1", "to": "n2", "source_file": "a.py"}]


def test_merge_result_edge_fields_default_to_zero(tmp_path: Path) -> None:
    """MergeResult's new edge fields default to 0 so any code constructing it
    with only the pre-existing node-only fields still works."""
    result = MergeResult(removed_count=0, added_count=0, total_after=0, layer_path=tmp_path / "step.json")
    assert result.edges_removed_count == 0
    assert result.edges_added_count == 0
    assert result.edges_total_after == 0
