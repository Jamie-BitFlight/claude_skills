"""Idempotent fragment-to-layer ETL for the DH workflow extractor system.

Merges one :class:`ExtractionFragment` into a layer JSON file (e.g.
``docs/workflow-layers/step.json``), atomically and idempotently. This module
owns exactly three responsibilities, per the architect spec's module boundary
(``plan/architect-dh-workflow-extractor-system.md`` Section 4.2):

- Removing prior nodes/edges that belong to the fragment's ``source_file``.
- Appending the fragment's new nodes.
- Writing the result back to disk without ever leaving a partial file.

It does NOT generate fragments (owned by ``dh-extract-file.js``), does NOT
write ``docs/workflow-layers/meta.json`` (owned by the SessionStart hook),
and does NOT perform cross-layer graph assembly (owned by
``docs/assemble_graph.py``). See architect spec Sections 1.1, 2.4, 2.5, 2.10,
3.1, 3.4, and 4.2 for the full contract this module implements.

This module is imported by callers (and by tests), not executed as a
standalone script -- it declares no PEP 723 dependency block and has no
``__main__`` entry point, matching the convention used by other pure-logic
helper modules in this directory (e.g. ``manifest_merge.py``). It requires no
third-party dependencies.

Design notes (decisions not fully spelled out by the architect spec):

- **Meta-shape tolerance**: ``LayerJSON.meta`` is validated only as a JSON
  object (``dict[str, object]``) -- individual keys documented in spec
  Section 2.5 (``generated``, ``source``, ``total_nodes``) are neither
  required nor stripped. This matches the spec's own Section 9.2 test
  fixtures, which construct layer files with ``"meta": {}``. Extra keys
  real layer files carry (``layer_type``, ``total_edges``, ``scope_version``,
  ``last_analyzed_commit``) are preserved verbatim across a read/write
  round-trip; ``total_nodes``/``total_edges`` are refreshed by
  :func:`merge_fragment` when present so the file never advertises a stale
  count of its own contents.
- **Edge cleanup scope**: :func:`merge_fragment` drops edges whose own
  ``source_file`` field matches the fragment's ``source_file`` (mirroring
  node removal), because those edges were extracted from the same file
  revision that is being wholly superseded and the fragment carries no
  replacement edges for them. It deliberately does NOT prune edges based on
  whether their endpoints still exist elsewhere in the layer -- this module
  only has visibility into a single layer file, and a target node id may
  legitimately live in a different layer file (L0, G1-G8) that this module
  never reads. Cross-layer edge-endpoint validation belongs to
  ``docs/assemble_graph.py``, which has full-graph visibility (spec Section
  4.2, "Does NOT own: ... graph assembly").
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

__all__ = [
    "ExtractionFragment",
    "LayerJSON",
    "MergeResult",
    "merge_fragment",
    "parse_extraction_fragment",
    "parse_layer_json",
    "read_layer",
    "write_layer",
]


class _RawFragmentMeta(TypedDict):
    """Documented shape of ``ExtractionFragment.meta`` on disk (spec Section 2.4)."""

    source_file: str
    layer_type: str
    extracted_at: str
    verified_count: int
    unverified_count: int


@dataclass(frozen=True, slots=True)
class ExtractionFragment:
    """A validated, typed per-file extraction result (spec Section 2.4).

    Attributes:
        source_file: Plugin-relative path to the source file this fragment
            was extracted from. Used by :func:`merge_fragment` to isolate
            which prior layer nodes/edges get replaced.
        layer_type: The layer this fragment targets (e.g. ``"step"``).
        extracted_at: ISO 8601 timestamp of extraction completion.
        items: Verified (or plausible) node dicts to merge into the layer.
            Typed generically as ``dict[str, object]`` rather than a single
            node TypedDict because the architect spec notes items may be
            "other node types per layer_type" -- the shape varies by layer.
        unverified_items: Node dicts the verifier could not confirm
            (REFUTED findings). Carried through for caller-side logging;
            :func:`merge_fragment` does not write these into the layer.
    """

    source_file: Path
    layer_type: str
    extracted_at: str
    items: tuple[dict[str, object], ...]
    unverified_items: tuple[dict[str, object], ...]


@dataclass
class LayerJSON:
    """Mutable, typed representation of a layer JSON file (spec Section 2.5).

    Mutable (unlike :class:`ExtractionFragment` and :class:`MergeResult`)
    because :func:`merge_fragment` merges in place before handing the result
    to :func:`write_layer`.

    Attributes:
        meta: The layer's metadata block, preserved verbatim except for
            ``total_nodes``/``total_edges`` refreshed by
            :func:`merge_fragment` when those keys are already present.
        nodes: All graph nodes currently in the layer.
        edges: All graph edges currently in the layer.
    """

    meta: dict[str, object]
    nodes: list[dict[str, object]]
    edges: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class MergeResult:
    """Outcome of a single :func:`merge_fragment` call (spec Section 2.10).

    Attributes:
        removed_count: Number of prior nodes removed because their
            ``source_file`` matched the fragment's ``source_file``.
        added_count: Number of nodes appended from the fragment's ``items``.
        total_after: Total node count in the layer after the merge.
        layer_path: The layer file that was written.
    """

    removed_count: int
    added_count: int
    total_after: int
    layer_path: Path


def parse_extraction_fragment(raw: object) -> ExtractionFragment:
    """Validate raw JSON data and construct a typed :class:`ExtractionFragment`.

    This is the untyped-JSON-in / typed-object-out boundary for fragment
    files (spec Section 2.4). Pass the result of ``json.loads()`` on a
    fragment file (or an equivalent freshly-decoded JSON value).

    Args:
        raw: JSON-decoded fragment content of unknown shape.

    Returns:
        A validated, immutable :class:`ExtractionFragment`.

    Raises:
        TypeError: If a required key is missing or has the wrong type.
    """
    fragment_dict = _require_dict(raw, field_name="fragment")
    meta_dict = _require_dict(fragment_dict.get("meta"), field_name="fragment.meta")
    meta = _validate_fragment_meta(meta_dict)
    items = _require_list_of_dicts(fragment_dict.get("items"), field_name="fragment.items")
    unverified_items = _require_list_of_dicts(
        fragment_dict.get("unverified_items"), field_name="fragment.unverified_items"
    )
    return ExtractionFragment(
        source_file=Path(meta["source_file"]),
        layer_type=meta["layer_type"],
        extracted_at=meta["extracted_at"],
        items=tuple(items),
        unverified_items=tuple(unverified_items),
    )


def parse_layer_json(raw: object) -> LayerJSON:
    """Validate raw JSON data and construct a typed :class:`LayerJSON`.

    This is the untyped-JSON-in / typed-object-out boundary for layer files
    (spec Section 2.5). Pass the result of ``json.loads()`` on a layer file
    (or an equivalent freshly-decoded JSON value).

    Only the outer shape is validated: ``meta`` must be a JSON object,
    ``nodes``/``edges`` must be JSON arrays of JSON objects. The meta
    block's inner keys are intentionally NOT validated -- see the "Meta
    shape tolerance" module note for why.

    Args:
        raw: JSON-decoded layer content of unknown shape.

    Returns:
        A validated :class:`LayerJSON`.

    Raises:
        TypeError: If the top-level shape does not match (not an object,
            or ``meta``/``nodes``/``edges`` missing or wrongly typed).
    """
    layer_dict = _require_dict(raw, field_name="layer")
    meta = _require_dict(layer_dict.get("meta"), field_name="layer.meta")
    nodes = _require_list_of_dicts(layer_dict.get("nodes"), field_name="layer.nodes")
    edges = _require_list_of_dicts(layer_dict.get("edges"), field_name="layer.edges")
    return LayerJSON(meta=meta, nodes=nodes, edges=edges)


def read_layer(layer_path: Path) -> LayerJSON:
    """Read and validate a layer JSON file from disk.

    If ``layer_path`` does not exist, returns a fresh, empty
    :class:`LayerJSON` held only in memory -- this function never creates
    the file itself. Callers that need the file to exist on disk (e.g.
    :func:`merge_fragment`'s missing-file bootstrap, spec Section 4.2 /
    Section 3 requirement 5) must call :func:`write_layer`.

    Args:
        layer_path: Path to the layer JSON file.

    Returns:
        The parsed layer content, or a fresh empty layer if the file is
        missing.

    Raises:
        TypeError: If the file exists but its content is not a valid
            layer JSON object (see :func:`parse_layer_json`).
        json.JSONDecodeError: If the file exists but is not valid JSON.
    """
    if not layer_path.exists():
        return LayerJSON(meta=_bootstrap_layer_meta(), nodes=[], edges=[])
    raw_text = layer_path.read_text(encoding="utf-8")
    raw_data: object = json.loads(raw_text)
    return parse_layer_json(raw_data)


def write_layer(layer_path: Path, layer: LayerJSON) -> None:
    """Atomically write a :class:`LayerJSON` to disk.

    Writes to a uniquely named temporary file in the same directory as
    ``layer_path`` (guaranteeing the final rename is on the same
    filesystem), flushes and fsyncs it to guarantee durability, then
    replaces ``layer_path`` with it in a single atomic filesystem
    operation. If any step fails, the temporary file is removed and the
    original ``layer_path`` (if any) is left completely untouched -- no
    partial or corrupted layer file is ever observable.

    JSON is written without indentation (repository convention: this file
    is machine-read by other tooling in the extraction pipeline, not
    intended for human review).

    Args:
        layer_path: Destination path for the layer JSON file.
        layer: The layer content to serialize.

    Raises:
        OSError: If the temporary file cannot be written, or the atomic
            replace fails. ``layer_path`` is guaranteed unmodified in this
            case.
    """
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {"meta": layer.meta, "nodes": layer.nodes, "edges": layer.edges}
    serialized = json.dumps(payload)

    fd, tmp_name = tempfile.mkstemp(suffix=".tmp", prefix=f"{layer_path.name}.", dir=layer_path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(serialized)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        tmp_path.replace(layer_path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def merge_fragment(layer_path: Path, fragment: ExtractionFragment) -> MergeResult:
    """Merge one extraction fragment into a layer JSON file.

    Removes every existing node (and every existing edge tagged with the
    same ``source_file`` -- see the module docstring's "Edge cleanup
    scope" note) whose ``source_file`` matches ``fragment.source_file``,
    then appends ``fragment.items`` as new nodes, and writes the result
    atomically via :func:`write_layer`. Each appended node is a shallow
    copy of the corresponding ``fragment.items`` entry with its
    ``source_file`` field set (or overwritten) to
    ``str(fragment.source_file)`` -- the fragment's own dict objects are
    never mutated. This guarantees every node this call appends agrees
    with the removal filter on the next merge, regardless of what
    ``source_file`` value (missing, mismatched, or absent) the fragment
    producer put on the item.

    If ``layer_path`` does not exist, it is bootstrapped as an empty layer
    (``{"meta": {...}, "nodes": [], "edges": []}``) before the merge is
    applied, per spec Section 3 requirement 5 -- this always yields
    ``removed_count=0`` for a first run.

    Idempotency invariant (spec Section 4.2): applying the same fragment
    to the same layer twice in a row produces byte-identical file content
    both times. This holds because node/edge removal and re-addition are
    both pure functions of ``layer_path``'s current content and
    ``fragment`` -- the second call removes exactly what the first call
    added (its ``source_file`` field having been forced to
    ``str(fragment.source_file)`` on append, as above) and re-adds the
    identical items, and no wall-clock-dependent field (e.g. a "last
    modified" timestamp) is touched on every merge -- only the
    bootstrap's one-time ``generated`` timestamp is time-based, and it is
    written once, before the idempotent portion of the contract applies.

    Path-matching contract (spec Section 4.2): ``fragment.source_file`` is
    compared against each node's/edge's ``source_file`` field as a plain
    string (``str(fragment.source_file)``). The caller is responsible for
    path normalisation before calling this function -- a mismatched path
    (e.g. absolute vs. plugin-relative) silently produces a no-op removal
    (nothing removed, fragment items still appended). This is intentional
    per spec Section 4.2, not a bug to fix here.

    Args:
        layer_path: Path to the layer JSON file to merge into.
        fragment: The extraction fragment to merge.

    Returns:
        A :class:`MergeResult` describing what changed.

    Raises:
        TypeError: If ``layer_path`` exists but does not contain valid
            layer JSON (propagated from :func:`read_layer`).
        json.JSONDecodeError: If ``layer_path`` exists but is not valid
            JSON (propagated from :func:`read_layer`).
        OSError: If the atomic write fails (propagated from
            :func:`write_layer`). ``layer_path`` is left unmodified.
    """
    layer = read_layer(layer_path)
    source_file_str = str(fragment.source_file)

    surviving_nodes = [node for node in layer.nodes if node.get("source_file") != source_file_str]
    removed_count = len(layer.nodes) - len(surviving_nodes)

    new_nodes = [{**item, "source_file": source_file_str} for item in fragment.items]
    merged_nodes = [*surviving_nodes, *new_nodes]

    surviving_edges = [edge for edge in layer.edges if edge.get("source_file") != source_file_str]

    layer.nodes = merged_nodes
    layer.edges = surviving_edges
    layer.meta["total_nodes"] = len(merged_nodes)
    if "total_edges" in layer.meta:
        layer.meta["total_edges"] = len(surviving_edges)

    write_layer(layer_path, layer)

    return MergeResult(
        removed_count=removed_count, added_count=len(new_nodes), total_after=len(merged_nodes), layer_path=layer_path
    )


def _bootstrap_layer_meta() -> dict[str, object]:
    """Build the default meta block for a newly bootstrapped layer file.

    Returns:
        A meta dict following the minimal documented shape from spec
        Section 2.5 (``generated``, ``source``, ``total_nodes``).
    """
    return {"generated": datetime.now(UTC).isoformat(), "source": "merge_layer.py bootstrap", "total_nodes": 0}


def _validate_fragment_meta(meta: dict[str, object]) -> _RawFragmentMeta:
    """Validate and narrow a fragment's meta block to the documented shape.

    Args:
        meta: The raw ``fragment["meta"]`` dict, already confirmed to be a
            JSON object with string keys.

    Returns:
        The validated, strongly typed fragment meta.

    Raises:
        TypeError: If a required key is missing or has the wrong type.
    """
    return {
        "source_file": _require_str(meta.get("source_file"), field_name="fragment.meta.source_file"),
        "layer_type": _require_str(meta.get("layer_type"), field_name="fragment.meta.layer_type"),
        "extracted_at": _require_str(meta.get("extracted_at"), field_name="fragment.meta.extracted_at"),
        "verified_count": _require_int(meta.get("verified_count"), field_name="fragment.meta.verified_count"),
        "unverified_count": _require_int(meta.get("unverified_count"), field_name="fragment.meta.unverified_count"),
    }


def _require_dict(value: object, *, field_name: str) -> dict[str, object]:
    """Validate that ``value`` is a JSON object and copy it to ``dict[str, object]``.

    Args:
        value: The raw value to validate.
        field_name: Dotted path used in the error message for diagnostics.

    Returns:
        A fresh dict containing the same entries as ``value``.

    Raises:
        TypeError: If ``value`` is not a dict, or contains a non-string key.
    """
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a JSON object, got {type(value).__name__}")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{field_name} must have string keys, got key of type {type(key).__name__}")
        result[key] = item
    return result


def _require_list_of_dicts(value: object, *, field_name: str) -> list[dict[str, object]]:
    """Validate that ``value`` is a JSON array of JSON objects.

    Args:
        value: The raw value to validate.
        field_name: Dotted path used in the error message for diagnostics.

    Returns:
        A list of freshly copied ``dict[str, object]`` entries.

    Raises:
        TypeError: If ``value`` is not a list, or any element is not a
            JSON object.
    """
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a JSON array, got {type(value).__name__}")
    return [_require_dict(item, field_name=f"{field_name}[{index}]") for index, item in enumerate(value)]


def _require_str(value: object, *, field_name: str) -> str:
    """Validate that ``value`` is a string.

    Args:
        value: The raw value to validate.
        field_name: Dotted path used in the error message for diagnostics.

    Returns:
        ``value``, narrowed to ``str``.

    Raises:
        TypeError: If ``value`` is not a string.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string, got {type(value).__name__}")
    return value


def _require_int(value: object, *, field_name: str) -> int:
    """Validate that ``value`` is an int (excluding ``bool``).

    ``bool`` is a subclass of ``int`` in Python; a JSON boolean silently
    passing an int check would be a real correctness gap for count fields,
    so it is explicitly rejected here.

    Args:
        value: The raw value to validate.
        field_name: Dotted path used in the error message for diagnostics.

    Returns:
        ``value``, narrowed to ``int``.

    Raises:
        TypeError: If ``value`` is not an int, or is a bool.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an int, got {type(value).__name__}")
    return value
