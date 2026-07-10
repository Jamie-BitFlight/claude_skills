#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
r"""Assemble dh-workflow-graph.json from the 10 authoritative layer JSON files.

Usage:
    uv run plugins/development-harness/docs/assemble_graph.py
    uv run plugins/development-harness/docs/assemble_graph.py \\
        --layers plugins/development-harness/docs/workflow-layers/ \\
        --output plugins/development-harness/docs/dh-workflow-graph.json

Gap edges (docs/graph-schema.md "gap" edge type): the shipped L0/G1-G8/L1
layer files carry no per-transition ``verified``/``gap`` field of their own
-- verification status is derived here from what each L1 trace's
``terminal_type``/``terminal_target`` combination lets this assembler
confidently resolve. See :func:`_process_trace` for the exact rules that
produce a ``gap`` edge (``verified=False``, ``gap=True``). ``meta.gap_count``
in the assembled output (see :func:`_build_graph_dict`) is always computed
from the actual assembled edge set, never hardcoded, so it reflects
whatever the current layer files and extraction rules actually produce.

Orphan edges (docs/graph-schema.md "Orphan edges"): a node ID is a
deterministic slug of a layer-file key (see :func:`slugify`/:func:`_node_id`).
Renaming a key in any ``docs/workflow-layers/*.json`` layer file changes
that slug, which orphans every edge that referenced the old ID -- the
node it pointed to no longer exists in the current node set. See
:func:`self_check` for the annotation rule (``status="orphan"``,
``verified=False``; orphan edges are kept, never deleted). ``meta.orphan_count``
in the assembled output (see :func:`_build_graph_dict`) is always computed
from the actual assembled edge set, never hardcoded, for the same reason as
``meta.gap_count`` above.
"""

from __future__ import annotations

import argparse
import json
import operator
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------


def slugify(value: str) -> str:
    """Replace non-alphanumeric chars with _, lowercase, collapse repeated _.

    Returns:
        Slug string safe for use as an id component.
    """
    s = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return s.strip("_")


def _node_id(prefix: str, key: str) -> str:
    """Build a namespaced node id: '{prefix}.{slug(key)}'.

    Returns:
        Node id string.
    """
    return f"{prefix}.{slugify(key)}"


# ---------------------------------------------------------------------------
# Source-file / heading split
# ---------------------------------------------------------------------------


def split_source_file(raw: str | None) -> tuple[str | None, str | None]:
    r"""Split 'path/to/file.md:## Heading' into (file_path, heading).

    Splits on the FIRST ':'. In practice all source_file values use POSIX
    paths so there is no ambiguity with Windows drive letters.

    Returns:
        Two-tuple of (file_path, heading); either component may be None.
    """
    if not raw:
        return None, None
    idx = raw.find(":")
    if idx == -1:
        return raw, None
    file_part = raw[:idx].strip()
    heading_part = raw[idx + 1 :].strip() or None
    return file_part, heading_part


def prefix_source_file(path: str | None) -> str | None:
    """Ensure a path starts with 'plugins/development-harness/'.

    Relative workflow paths (e.g. 'skills/work-backlog-item/SKILL.md') are
    prefixed; already-prefixed and absolute paths are returned unchanged.

    Returns:
        Prefixed path, or None when the input is falsy.
    """
    if not path:
        return None
    if path.startswith(("plugins/", "/")):
        return path
    return f"plugins/development-harness/{path}"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILL_FILE_MAP: dict[str, str] = {
    "work-backlog-item": ("plugins/development-harness/skills/work-backlog-item/SKILL.md"),
    "add-new-feature": ("plugins/development-harness/skills/add-new-feature/SKILL.md"),
    "implement-feature": ("plugins/development-harness/skills/implement-feature/SKILL.md"),
    "complete-implementation": ("plugins/development-harness/skills/complete-implementation/SKILL.md"),
    "work-backlog-item/groom": (
        "plugins/development-harness/skills/work-backlog-item/references/workflows/groom/swarm.md"
    ),
    "work-milestone": ("plugins/development-harness/skills/work-milestone/SKILL.md"),
    "create": ("plugins/development-harness/skills/work-backlog-item/references/workflows/create/start.md"),
    "groom": ("plugins/development-harness/skills/work-backlog-item/references/workflows/groom/swarm.md"),
    "work": ("plugins/development-harness/skills/work-backlog-item/references/workflows/work/start.md"),
}

# Number of trailing path components to use as a reference_file label
_REF_LABEL_COMPONENTS: int = 2

_L1_FILENAMES: tuple[str, ...] = (
    "L1-trace-work-backlog-item.json",
    "L1-trace-complete-implementation.json",
    "L1-trace-feature-skills.json",
    "L1-trace-work-milestone.json",
)

# All terminal_type values this assembler has been taught to interpret into a
# normal (non-gap) edge, when the trace also carries the data that branch needs.
# A trace whose terminal_type falls outside this set, or whose terminal_type is
# in this set but is missing the terminal_target that branch requires, produces
# a `gap` edge instead of being silently dropped -- see _process_trace.
_KNOWN_TERMINAL_TYPES: frozenset[str] = frozenset({
    "loops_back",
    "hands_off_to_file",
    "STOP",
    "completes_workflow",
    "hands_off_to_skill",
})


# ---------------------------------------------------------------------------
# Layer data container
# ---------------------------------------------------------------------------


class LayerData:
    """Holds extracted lists from all loaded layer files."""

    def __init__(self) -> None:
        """Initialise with empty collections."""
        self.forks: list[dict[str, Any]] = []
        self.artifacts: list[dict[str, Any]] = []
        self.concurrency_map: list[dict[str, Any]] = []
        self.backend_routing: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Layer loaders
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load a JSON file whose top-level value is an object.

    Returns:
        Parsed dict, or None when the file is missing (with a warning to
        stderr).

    Raises:
        TypeError: If the file exists but its top-level JSON value is not
            an object (e.g. a JSON array). Missing files are an
            anticipated, recoverable condition (see :func:`load_layers`);
            a malformed existing file is not, and returning the wrong
            shape here would only surface later as a confusing
            ``AttributeError`` deep inside a caller instead of a clear
            error at this boundary.
    """
    if not path.exists():
        print(f"WARNING: Layer file not found: {path}", file=sys.stderr)
        return None
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: expected a JSON object at the top level, got {type(data).__name__}")
    return data


def load_layers(layers_dir: Path) -> LayerData:
    """Load all 10 authoritative layer JSON files into a LayerData container.

    Missing files produce a warning but do not abort; the corresponding
    collection remains empty.

    Returns:
        Populated LayerData instance.
    """
    ld = LayerData()

    l0 = _load_json(layers_dir / "L0-forks.json")
    g2 = _load_json(layers_dir / "G2-artifacts.json")
    g4 = _load_json(layers_dir / "G4-concurrency.json")
    g8 = _load_json(layers_dir / "G8-backend-routing.json")

    if l0:
        ld.forks = l0.get("forks", [])
    if g2:
        ld.artifacts = g2.get("artifacts", [])
    if g4:
        ld.concurrency_map = g4.get("concurrency_map", [])
    if g8:
        ld.backend_routing = g8.get("backend_routing", [])

    for fname in _L1_FILENAMES:
        data = _load_json(layers_dir / fname)
        if data:
            ld.traces.extend(data.get("traces", []))

    return ld


# ---------------------------------------------------------------------------
# Node builders
# ---------------------------------------------------------------------------


def build_decision_nodes(forks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build 'decision' nodes from L0 forks.

    Returns:
        Dict mapping node id → node dict.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for fork in forks:
        raw_id = fork["fork_id"]
        node_id = f"fork.{slugify(raw_id)}"
        raw_sf, heading = split_source_file(fork.get("source_file"))
        source_file = prefix_source_file(raw_sf)
        label = (fork.get("decision_question") or raw_id).strip().strip('"')
        nodes[node_id] = {
            "id": node_id,
            "type": "decision",
            "label": label,
            "route": fork.get("skill"),
            "source_file": source_file,
            "source_heading": fork.get("source_block") or heading,
            "verified": True,
            "metadata": {"evaluated_by": fork.get("evaluated_by"), "skill": fork.get("skill")},
        }
    return nodes


def build_skill_nodes(skill_names: set[str]) -> dict[str, dict[str, Any]]:
    """Build 'skill' nodes from the union of all referenced skill names.

    Returns:
        Dict mapping node id → node dict.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for skill in sorted(skill_names):
        node_id = _node_id("skill", skill)
        source_file = SKILL_FILE_MAP.get(skill)
        nodes[node_id] = {
            "id": node_id,
            "type": "skill",
            "label": skill,
            "route": skill,
            "source_file": source_file,
            "source_heading": None,
            "verified": source_file is not None,
            "metadata": {},
        }
    return nodes


def build_artifact_nodes(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build 'artifact' nodes from G2 artifacts.

    Returns:
        Dict mapping node id → node dict.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for art in artifacts:
        raw_id = art["id"]
        art_key = raw_id.removeprefix("G2.")
        node_id = f"artifact.{slugify(art_key)}"
        pb = art.get("produced_by", {})
        raw_sf, heading = split_source_file(pb.get("source_file"))
        source_file = prefix_source_file(raw_sf)
        nodes[node_id] = {
            "id": node_id,
            "type": "artifact",
            "label": art.get("name", art_key),
            "source_file": source_file,
            "source_heading": heading,
            "verified": True,
            "metadata": {
                "artifact_type_key": art.get("artifact_type_key"),
                "storage": art.get("storage"),
                "persistent": art.get("persistent"),
                "producer_skill": pb.get("skill"),
            },
        }
    return nodes


def build_mcp_tool_nodes(backend_routing: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build 'mcp_tool' nodes — one per unique mcp_tool name from G8.

    Returns:
        Dict mapping node id → node dict.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for item in backend_routing:
        tool = item.get("mcp_tool")
        if not tool:
            continue
        node_id = _node_id("mcp_tool", tool)
        if node_id in nodes:
            continue
        # SAM tools live in run_sam_server.py; all others in run_backlog_server.py
        if tool.startswith("mcp__plugin_dh_sam__"):
            server_script = "plugins/development-harness/scripts/run_sam_server.py"
        else:
            server_script = "plugins/development-harness/scripts/run_backlog_server.py"
        nodes[node_id] = {
            "id": node_id,
            "type": "mcp_tool",
            "label": tool,
            "source_file": server_script,
            "source_heading": None,
            "verified": True,
            "metadata": {
                "routes_to_protocol_method": item.get("routes_to_protocol_method"),
                "backend_agnostic": item.get("backend_agnostic", False),
            },
        }
    return nodes


def build_backend_nodes(backend_routing: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build 'backend' nodes — one per unique backend from G8 per_backend keys.

    Returns:
        Dict mapping node id → node dict.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for item in backend_routing:
        for backend_name in item.get("per_backend", {}):
            node_id = _node_id("backend", backend_name)
            if node_id in nodes:
                continue
            nodes[node_id] = {
                "id": node_id,
                "type": "backend",
                "label": backend_name.capitalize(),
                "source_file": None,
                "source_heading": None,
                "verified": True,
                "metadata": {},
            }
    return nodes


def build_agent_nodes(concurrency_map: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build 'agent' nodes — one per unique agent name from G4, deduped.

    Returns:
        Dict mapping node id → node dict.
    """
    nodes: dict[str, dict[str, Any]] = {}
    for item in concurrency_map:
        for agent_name in item.get("agents_dispatched") or []:
            if not agent_name:
                continue
            node_id = _node_id("agent", agent_name)
            if node_id in nodes:
                continue
            nodes[node_id] = {
                "id": node_id,
                "type": "agent",
                "label": agent_name,
                "source_file": None,
                "source_heading": None,
                "verified": False,
                "metadata": {
                    "dispatch_mechanism": item.get("mechanism"),
                    "wave": item.get("wave"),
                    "skill": item.get("skill"),
                },
            }
    return nodes


def build_reference_file_nodes(forks: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build 'reference_file' nodes from L0 file-ref branches and L1 HOF traces.

    Both sources can reference target files — L1 may include files not listed
    in L0.

    Returns:
        Dict mapping node id → node dict.
    """
    file_to_forks: dict[str, list[str]] = {}

    for fork in forks:
        for branch in fork.get("branches", []):
            if branch.get("target_is_file_ref") and branch.get("target_file"):
                tf: str = branch["target_file"]
                file_to_forks.setdefault(tf, []).append(fork["fork_id"])

    for trace in traces:
        if trace.get("terminal_type") == "hands_off_to_file":
            tf = trace.get("terminal_target", "")
            if tf:
                from_fork = trace.get("from_fork", "")
                file_to_forks.setdefault(tf, [])
                if from_fork and from_fork not in file_to_forks[tf]:
                    file_to_forks[tf].append(from_fork)

    nodes: dict[str, dict[str, Any]] = {}
    for target_file, fork_ids in file_to_forks.items():
        node_id = _node_id("ref", target_file)
        parts = Path(target_file).parts
        label = "/".join(parts[-_REF_LABEL_COMPONENTS:]) if len(parts) >= _REF_LABEL_COMPONENTS else target_file
        nodes[node_id] = {
            "id": node_id,
            "type": "reference_file",
            "label": label,
            "source_file": prefix_source_file(target_file),
            "source_heading": None,
            "verified": False,
            "metadata": {"referenced_from": sorted(set(fork_ids))},
        }
    return nodes


def build_terminal_stub_node() -> dict[str, dict[str, Any]]:
    """Create the single shared STOP terminal stub node.

    Returns:
        Dict containing the one terminal stub node keyed by its id.
    """
    return {
        "terminal.stop": {
            "id": "terminal.stop",
            "type": "decision",
            "label": "STOP",
            "route": None,
            "source_file": None,
            "source_heading": None,
            "verified": True,
            "metadata": {"terminal": True},
        }
    }


# ---------------------------------------------------------------------------
# Edge builders
# ---------------------------------------------------------------------------


def _edge(
    edge_id: str,
    edge_type: str,
    source: str,
    target: str,
    label: str | None = None,
    source_file: str | None = None,
    source_heading: str | None = None,
    verified: bool = True,
    gap: bool = False,
) -> dict[str, Any]:
    """Construct a graph edge dict.

    Returns:
        Edge dict with all required fields.
    """
    return {
        "id": edge_id,
        "type": edge_type,
        "source": source,
        "target": target,
        "label": label,
        "source_file": source_file,
        "source_heading": source_heading,
        "verified": verified,
        "gap": gap,
    }


def _ensure_fork_stub(
    fork_id: str, label: str, source_file: str | None, reason: str, known: set[str], stubs: dict[str, dict[str, Any]]
) -> None:
    """Add a stub decision node to *stubs* when *fork_id* is absent from *known*.

    Does nothing if the id is already present in either set.
    """
    if fork_id not in known and fork_id not in stubs:
        stubs[fork_id] = {
            "id": fork_id,
            "type": "decision",
            "label": label,
            "route": None,
            "source_file": source_file,
            "source_heading": None,
            "verified": False,
            "metadata": {"stub": True, "reason": reason},
        }


def _ensure_skill_stub(
    skill_id: str, label: str, source_file: str | None, reason: str, known: set[str], stubs: dict[str, dict[str, Any]]
) -> None:
    """Add a stub skill node to *stubs* when *skill_id* is absent from *known*.

    Mirrors :func:`_ensure_fork_stub` for skill-typed targets. Used so a
    ``gap`` edge's target always resolves to a real node -- otherwise
    :func:`self_check` would remove the gap edge as an orphan, silently
    re-losing the exact signal this stub exists to preserve. Does nothing if
    the id is already present in either set.
    """
    if skill_id not in known and skill_id not in stubs:
        stubs[skill_id] = {
            "id": skill_id,
            "type": "skill",
            "label": label,
            "route": label,
            "source_file": source_file,
            "source_heading": None,
            "verified": False,
            "metadata": {"stub": True, "reason": reason},
        }


def _normalize_skill_target(target: str) -> str:
    """Strip a leading 'plugin:' qualifier from an L1 hands_off_to_skill target.

    L1 traces record ``hands_off_to_skill`` targets exactly as written in
    workflow prose (e.g. ``Skill(skill='dh:add-new-feature')``), which is
    often plugin-qualified. ``collect_all_skill_names()`` collects skill
    names from L0/G2/G4/G8 -- none of those layers record a plugin
    namespace, so known skill ids are always built from the unprefixed form
    (e.g. ``skill.add_new_feature``). Without stripping the qualifier here,
    a plugin-qualified hand-off to an already-known skill would slugify to
    a different, unmatched node id (``skill.dh_add_new_feature``), causing
    :func:`_process_trace` to spawn a redundant unverified stub for a skill
    that is already a real, sourced node -- fragmenting the graph instead
    of resolving the hand-off.

    Only the first ``:`` is treated as a qualifier separator, and only when
    both sides are non-empty -- this only ever fires for the simple
    ``plugin:skill-name`` shape; multi-segment or malformed targets (e.g.
    ``'dh:implement-feature -> dh:complete-implementation'``) are returned
    with just the leading qualifier stripped, which still won't match any
    known skill id and correctly falls through to the stub+gap path.

    Returns:
        target with a leading '<qualifier>:' prefix removed; target
        unchanged if it has no such prefix.
    """
    prefix, sep, rest = target.partition(":")
    return rest if sep and prefix and rest else target


def _process_trace(
    trace: dict[str, Any],
    known_fork_ids: set[str],
    known_skill_ids: set[str],
    edges: dict[str, dict[str, Any]],
    extra_stubs: dict[str, dict[str, Any]],
) -> None:
    """Emit edges and stub nodes for a single L1 trace into mutable dicts.

    Routes_to edges are only emitted when terminal_target maps to a known
    skill node — phrases that are workflow headings are silently skipped
    (deliberate: ``completes_workflow.terminal_target`` values are often
    workflow-internal headings, not skill names -- see
    :func:`collect_all_skill_names`'s docstring; converting all of them to
    ``gap`` edges would misrepresent internal step labels as cross-skill
    transitions).

    ``gap`` edges (``verified=False``, ``gap=True``) are emitted for three
    cases where source data marks a real transition that this assembler
    cannot independently attest:

    1. ``terminal_type == "hands_off_to_skill"`` whose target, after
       stripping any plugin qualifier (see :func:`_normalize_skill_target`,
       e.g. ``'dh:find-cause'`` -> ``'find-cause'``), is still not in
       ``known_skill_ids``: the L1 extractor recorded an explicit hand-off
       to another skill (e.g. ``Skill(skill='find-cause')`` in workflow
       prose), but that target skill is not independently confirmed by
       L0/G2/G4/G8 (it has no ``SKILL_FILE_MAP`` entry or explicit
       ``skill`` field anywhere in the authoritative layers). The
       transition is real and attested by the L1 trace itself; only the
       target's own identity/location is unverified. When the normalized
       target DOES match a known skill node, a ``routes_to`` edge is
       emitted instead (see the ``hands_off_to_skill`` branch below) -- the
       hand-off is both real and independently confirmed, so it is not a
       gap.
    2. A recognized ``terminal_type`` (``loops_back``, ``hands_off_to_file``,
       ``completes_workflow``) whose branch requires ``terminal_target`` but
       the trace has none (observed in the shipped L1 traces: 10
       ``completes_workflow`` traces record the workflow proceeding to a
       local next step with no extractable cross-file/cross-skill target).
    3. Any ``terminal_type`` outside ``_KNOWN_TERMINAL_TYPES`` (currently
       none occur in the shipped layer files — the five known values cover
       100% of observed traces).

    Cases 2 and 3 both fall through to an explicit final ``else`` that emits
    a ``gap`` edge rather than silently dropping the trace, per this repo's
    silent-failure-prevention policy: an incomplete or unrecognized trace is
    data this assembler cannot fully interpret, not a reason to lose the
    transition. The two cases are labeled distinctly so the gap edge's
    ``label`` field states which condition applies.
    """
    from_fork_raw = trace.get("from_fork") or ""
    source_id = f"fork.{slugify(from_fork_raw)}"
    condition = trace.get("branch_condition") or ""
    terminal_type = trace.get("terminal_type", "")
    terminal_target = trace.get("terminal_target") or ""
    raw_sf, heading = split_source_file(trace.get("source_file"))
    source_file = prefix_source_file(raw_sf)

    _ensure_fork_stub(source_id, from_fork_raw, source_file, "source fork not in L0", known_fork_ids, extra_stubs)

    cond_key = slugify(condition)
    edge_id_base = f"e.{slugify(from_fork_raw)}.{cond_key}"

    if terminal_type == "loops_back" and terminal_target:
        target_fork_id = f"fork.{slugify(terminal_target)}"
        _ensure_fork_stub(
            target_fork_id, terminal_target, source_file, "loops_back target not in L0", known_fork_ids, extra_stubs
        )
        eid = f"{edge_id_base}.branch"
        edges[eid] = _edge(
            eid,
            "branch",
            source_id,
            target_fork_id,
            label=condition[:80],
            source_file=source_file,
            source_heading=heading,
        )

    elif terminal_type == "hands_off_to_file" and terminal_target:
        eid = f"{edge_id_base}.branch"
        edges[eid] = _edge(
            eid,
            "branch",
            source_id,
            _node_id("ref", terminal_target),
            label=condition[:80],
            source_file=source_file,
            source_heading=heading,
        )

    elif terminal_type == "STOP":
        eid = f"{edge_id_base}.branch"
        edges[eid] = _edge(
            eid,
            "branch",
            source_id,
            "terminal.stop",
            label=condition[:80],
            source_file=source_file,
            source_heading=heading,
        )

    elif terminal_type == "completes_workflow" and terminal_target:
        skill_id = _node_id("skill", terminal_target)
        if skill_id in known_skill_ids:
            eid = f"e.routes_to.{slugify(from_fork_raw)}.{cond_key}"
            edges[eid] = _edge(
                eid,
                "routes_to",
                source_id,
                skill_id,
                label=condition[:80],
                source_file=source_file,
                source_heading=heading,
            )

    elif terminal_type == "hands_off_to_skill" and terminal_target:
        _emit_skill_handoff(
            trace_ctx={
                "source_id": source_id,
                "from_fork_raw": from_fork_raw,
                "cond_key": cond_key,
                "condition": condition,
                "terminal_target": terminal_target,
                "source_file": source_file,
                "heading": heading,
            },
            known_skill_ids=known_skill_ids,
            edges=edges,
            extra_stubs=extra_stubs,
        )

    elif terminal_type:
        _emit_unroutable_trace(
            trace_ctx={
                "source_id": source_id,
                "from_fork_raw": from_fork_raw,
                "cond_key": cond_key,
                "terminal_type": terminal_type,
                "terminal_target": terminal_target,
                "source_file": source_file,
                "heading": heading,
            },
            edges=edges,
            extra_stubs=extra_stubs,
        )


def _emit_skill_handoff(
    trace_ctx: dict[str, Any],
    known_skill_ids: set[str],
    edges: dict[str, dict[str, Any]],
    extra_stubs: dict[str, dict[str, Any]],
) -> None:
    """Emit the edge for a ``hands_off_to_skill`` trace.

    Plugin-qualifier-normalized target matching an independently confirmed
    skill node means the hand-off is both real (attested by the L1 trace)
    and independently confirmed -- a ``routes_to`` edge, not a gap (see
    :func:`_normalize_skill_target`). An unmatched target keeps the prior
    behavior: an unverified stub skill node plus a ``gap`` edge.
    """
    source_id = trace_ctx["source_id"]
    from_fork_raw = trace_ctx["from_fork_raw"]
    cond_key = trace_ctx["cond_key"]
    terminal_target = trace_ctx["terminal_target"]
    source_file = trace_ctx["source_file"]
    heading = trace_ctx["heading"]

    skill_id = _node_id("skill", _normalize_skill_target(terminal_target))
    if skill_id in known_skill_ids:
        eid = f"e.routes_to.{slugify(from_fork_raw)}.{cond_key}"
        edges[eid] = _edge(
            eid,
            "routes_to",
            source_id,
            skill_id,
            label=trace_ctx["condition"][:80],
            source_file=source_file,
            source_heading=heading,
        )
        return
    _ensure_skill_stub(
        skill_id,
        terminal_target,
        source_file,
        "hands_off_to_skill target not independently confirmed",
        known_skill_ids,
        extra_stubs,
    )
    eid = f"e.gap.{slugify(from_fork_raw)}.{cond_key}"
    edges[eid] = _edge(
        eid,
        "gap",
        source_id,
        skill_id,
        label=f"hands off to skill '{terminal_target}' — target not independently confirmed",
        source_file=source_file,
        source_heading=heading,
        verified=False,
        gap=True,
    )


def _emit_unroutable_trace(
    trace_ctx: dict[str, Any], edges: dict[str, dict[str, Any]], extra_stubs: dict[str, dict[str, Any]]
) -> None:
    """Emit a ``gap`` edge for a trace that cannot be routed to a normal edge.

    Explicit fallback (silent-failure-prevention.md): a trace
    :func:`_process_trace` cannot fully route must still surface as a
    transition, not silently vanish. Reached for (a) a known terminal_type
    missing the terminal_target its branch requires, or (b) a terminal_type
    outside ``_KNOWN_TERMINAL_TYPES``.
    """
    source_id = trace_ctx["source_id"]
    from_fork_raw = trace_ctx["from_fork_raw"]
    cond_key = trace_ctx["cond_key"]
    terminal_type = trace_ctx["terminal_type"]
    terminal_target = trace_ctx["terminal_target"]
    source_file = trace_ctx["source_file"]
    heading = trace_ctx["heading"]

    if terminal_type in _KNOWN_TERMINAL_TYPES:
        reason = f"terminal_type {terminal_type!r} recognized but terminal_target is missing"
    else:
        reason = f"unrecognized terminal_type {terminal_type!r}"

    if terminal_target:
        target_id = _node_id("ref", terminal_target)
        if target_id not in extra_stubs:
            extra_stubs[target_id] = {
                "id": target_id,
                "type": "reference_file",
                "label": terminal_target,
                "source_file": source_file,
                "source_heading": None,
                "verified": False,
                "metadata": {"stub": True, "reason": reason},
            }
    else:
        target_id = "terminal.stop"

    eid = f"e.gap.{slugify(from_fork_raw)}.{cond_key}.unrecognized"
    edges[eid] = _edge(
        eid,
        "gap",
        source_id,
        target_id,
        label=f"{reason} — transition unattested",
        source_file=source_file,
        source_heading=heading,
        verified=False,
        gap=True,
    )


def build_branch_edges_from_l1(
    traces: list[dict[str, Any]], known_fork_ids: set[str], known_skill_ids: set[str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build branch and routes_to edges from L1 traces.

    Uses L1 directly rather than the fragile L0 label→id join. Delegates
    per-trace processing to :func:`_process_trace`.

    Args:
        traces: All L1 trace records.
        known_fork_ids: Set of fork node ids built from L0.
        known_skill_ids: Set of skill node ids built from L0/G2/G4/G8.
            Routes_to edges are emitted only when terminal_target maps to
            a member of this set.

    Returns:
        Tuple of (edge list, extra stub decision nodes dict).
    """
    edges: dict[str, dict[str, Any]] = {}
    extra_stubs: dict[str, dict[str, Any]] = {}
    for trace in traces:
        _process_trace(trace, known_fork_ids, known_skill_ids, edges, extra_stubs)
    return list(edges.values()), extra_stubs


def build_writes_edges(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 'writes' edges from G2 produced_by.

    Returns:
        List of edge dicts.
    """
    edges: dict[str, dict[str, Any]] = {}
    for art in artifacts:
        pb = art.get("produced_by", {})
        producer_skill = pb.get("skill")
        if not producer_skill:
            continue
        art_id_raw = art["id"].removeprefix("G2.")
        source_id = _node_id("skill", producer_skill)
        target_id = f"artifact.{slugify(art_id_raw)}"
        action = (pb.get("action") or "")[:60]
        raw_sf, heading = split_source_file(pb.get("source_file"))
        source_file = prefix_source_file(raw_sf)
        eid = f"e.writes.{slugify(producer_skill)}.{slugify(art_id_raw)}"
        edges[eid] = _edge(
            eid, "writes", source_id, target_id, label=action or None, source_file=source_file, source_heading=heading
        )
    return list(edges.values())


def build_reads_edges(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 'reads' edges from G2 consumed_by, deduped per consumer+artifact.

    Returns:
        List of edge dicts.
    """
    edges: dict[str, dict[str, Any]] = {}
    for art in artifacts:
        art_id_raw = art["id"].removeprefix("G2.")
        target_id = f"artifact.{slugify(art_id_raw)}"
        for consumer in art.get("consumed_by", []):
            consumer_skill = consumer.get("skill")
            if not consumer_skill:
                continue
            source_id = _node_id("skill", consumer_skill)
            action = (consumer.get("action") or "")[:60]
            dedup_key = f"e.reads.{slugify(consumer_skill)}.{slugify(art_id_raw)}"
            if dedup_key not in edges:
                raw_sf, heading = split_source_file(consumer.get("source_file"))
                source_file = prefix_source_file(raw_sf)
                edges[dedup_key] = _edge(
                    dedup_key,
                    "reads",
                    source_id,
                    target_id,
                    label=action or None,
                    source_file=source_file,
                    source_heading=heading,
                )
    return list(edges.values())


def build_dispatches_edges(concurrency_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 'dispatches' edges from G4.

    Returns:
        List of edge dicts.
    """
    edges: dict[str, dict[str, Any]] = {}
    for item in concurrency_map:
        skill = item.get("skill")
        if not skill:
            continue
        source_id = _node_id("skill", skill)
        raw_sf, heading = split_source_file(item.get("source_file"))
        source_file = prefix_source_file(raw_sf)
        dispatch_label = (item.get("dispatch_label") or "")[:60]
        for agent_name in item.get("agents_dispatched") or []:
            if not agent_name:
                continue
            target_id = _node_id("agent", agent_name)
            eid = f"e.dispatches.{slugify(item.get('id') or '')}.{slugify(agent_name)}"
            if eid not in edges:
                edges[eid] = _edge(
                    eid,
                    "dispatches",
                    source_id,
                    target_id,
                    label=dispatch_label or None,
                    source_file=source_file,
                    source_heading=heading,
                )
    return list(edges.values())


def build_calls_edges(backend_routing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 'calls' edges from G8: skill → mcp_tool, deduped per skill+tool.

    Returns:
        List of edge dicts.
    """
    edges: dict[str, dict[str, Any]] = {}
    for item in backend_routing:
        skill = item.get("skill")
        tool = item.get("mcp_tool")
        if not skill or not tool:
            continue
        source_id = _node_id("skill", skill)
        target_id = _node_id("mcp_tool", tool)
        dedup_key = f"e.calls.{slugify(skill)}.{slugify(tool)}"
        if dedup_key not in edges:
            raw_sf, heading = split_source_file(item.get("source_file"))
            source_file = prefix_source_file(raw_sf)
            label = (item.get("step_label") or "")[:60]
            edges[dedup_key] = _edge(
                dedup_key,
                "calls",
                source_id,
                target_id,
                label=label or None,
                source_file=source_file,
                source_heading=heading,
            )
    return list(edges.values())


def build_stores_in_edges(backend_routing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 'stores_in' edges from G8: mcp_tool → backend, deduped.

    Returns:
        List of edge dicts.
    """
    edges: dict[str, dict[str, Any]] = {}
    for item in backend_routing:
        tool = item.get("mcp_tool")
        if not tool:
            continue
        source_id = _node_id("mcp_tool", tool)
        for backend_name in item.get("per_backend", {}):
            target_id = _node_id("backend", backend_name)
            dedup_key = f"e.stores_in.{slugify(tool)}.{slugify(backend_name)}"
            if dedup_key not in edges:
                edges[dedup_key] = _edge(dedup_key, "stores_in", source_id, target_id)
    return list(edges.values())


# ---------------------------------------------------------------------------
# Skill name collector
# ---------------------------------------------------------------------------


def _skills_from_artifacts(artifacts: list[dict[str, Any]]) -> set[str]:
    """Extract skill names referenced in G2 produced_by and consumed_by.

    Returns:
        Set of skill name strings.
    """
    skills: set[str] = set()
    for art in artifacts:
        pb = art.get("produced_by", {})
        if pb.get("skill"):
            skills.add(pb["skill"])
        for cb in art.get("consumed_by", []):
            if cb.get("skill"):
                skills.add(cb["skill"])
    return skills


def collect_all_skill_names(ld: LayerData) -> set[str]:
    """Return all skill names referenced as edge endpoints in L0/G2/G4/G8.

    Deliberately excludes L1 traces — L1 completes_workflow targets are often
    workflow headings, not skill names.  Skills are only added from authoritative
    sources with an explicit ``skill`` field.

    Returns:
        Set of skill name strings.
    """
    skills: set[str] = set()

    for fork in ld.forks:
        if fork.get("skill"):
            skills.add(fork["skill"])

    skills |= _skills_from_artifacts(ld.artifacts)

    for item in ld.concurrency_map:
        if item.get("skill"):
            skills.add(item["skill"])

    for item in ld.backend_routing:
        if item.get("skill"):
            skills.add(item["skill"])

    return skills


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

OVERLAYS: dict[str, dict[str, Any]] = {
    "workflow": {
        "label": "Workflow",
        "description": "Decision forks and routing",
        "node_types": ["decision", "skill"],
        "edge_types": ["branch", "routes_to", "gap"],
    },
    "agents": {
        "label": "Agents",
        "description": "Agent dispatch and execution",
        "node_types": ["decision", "skill", "agent"],
        "edge_types": ["branch", "dispatches"],
    },
    "instructions": {
        "label": "Instructions",
        "description": "Reference files loaded per agent",
        "node_types": ["decision", "skill", "agent", "reference_file"],
        "edge_types": ["branch"],
    },
    "tools": {
        "label": "MCP Tools",
        "description": "MCP tool calls and backend routing",
        "node_types": ["decision", "skill", "mcp_tool", "backend"],
        "edge_types": ["calls", "stores_in"],
    },
    "artifacts": {
        "label": "Artifact Flow",
        "description": "Artifact production and consumption",
        "node_types": ["skill", "artifact"],
        "edge_types": ["reads", "writes"],
    },
    "concurrency": {
        "label": "Concurrency",
        "description": "Parallel dispatch and waves",
        "node_types": ["decision", "skill", "agent"],
        "edge_types": ["branch", "dispatches"],
    },
}


def _count_types(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    """Count occurrences of each value of ``key`` across a list of dicts.

    Returns:
        Dict of value → count.
    """
    counts: dict[str, int] = {}
    for item in items:
        v = item.get(key, "")
        counts[v] = counts.get(v, 0) + 1
    return counts


def self_check(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate orphan edges; warn about overlay types with zero instances.

    An orphan edge is one whose source or target node id is absent from the
    node set -- typically because a key in a ``docs/workflow-layers/*.json``
    layer file was renamed, changing the deterministic ``_node_id`` slug an
    older edge still references (see module docstring "Orphan edges").

    Orphan edges are PRESERVED, not deleted: each is returned with
    ``status: "orphan"`` and ``verified: False`` added/overwritten so the
    condition is visible in ``meta.orphan_count`` (see
    :func:`_build_graph_dict`) rather than only as a stderr line. This is
    deliberately a different signal from a ``gap`` edge (``gap`` marks an
    unattested-but-real transition from source data; ``status: "orphan"``
    marks a transition whose recorded endpoint no longer exists) -- orphan
    edges never set ``gap: True``. Non-orphan edges are returned unchanged
    (no ``status`` key added), keeping the common-case payload minimal.
    Idempotent: re-running on already-annotated edges re-derives the same
    ``status``/``verified`` values from the same node/edge endpoints.

    Every overlay-referenced node type and edge type must have at least one
    instance.

    Returns:
        Edge list, same length as the input ``edges`` -- orphan edges
        annotated in place, non-orphan edges unchanged.
    """
    node_ids = {n["id"] for n in nodes}
    node_type_counts = _count_types(nodes, "type")
    edge_type_counts = _count_types(edges, "type")

    annotated_edges = []
    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src not in node_ids or tgt not in node_ids:
            src_status = "ok" if src in node_ids else "MISSING"
            tgt_status = "ok" if tgt in node_ids else "MISSING"
            print(
                f"ORPHAN PRESERVED: edge {edge['id']} src={src}({src_status}) tgt={tgt}({tgt_status})", file=sys.stderr
            )
            orphan_edge = dict(edge)
            orphan_edge["status"] = "orphan"
            orphan_edge["verified"] = False
            annotated_edges.append(orphan_edge)
        else:
            annotated_edges.append(edge)

    all_overlay_node_types: set[str] = set()
    all_overlay_edge_types: set[str] = set()
    for overlay in OVERLAYS.values():
        all_overlay_node_types.update(overlay["node_types"])
        all_overlay_edge_types.update(overlay["edge_types"])

    for nt in sorted(all_overlay_node_types):
        if node_type_counts.get(nt, 0) == 0:
            print(f"WARNING: overlay references node type '{nt}' but graph has 0 instances", file=sys.stderr)
    for et in sorted(all_overlay_edge_types):
        if edge_type_counts.get(et, 0) == 0:
            print(f"WARNING: overlay references edge type '{et}' but graph has 0 instances", file=sys.stderr)

    for overlay_key, overlay in OVERLAYS.items():
        node_count = sum(node_type_counts.get(nt, 0) for nt in overlay["node_types"])
        edge_count = sum(edge_type_counts.get(et, 0) for et in overlay["edge_types"])
        print(
            f"  overlay '{overlay_key}': "
            f"{node_count} nodes ({', '.join(overlay['node_types'])}), "
            f"{edge_count} edges ({', '.join(overlay['edge_types'])})"
        )

    return annotated_edges


# ---------------------------------------------------------------------------
# Main assembler
# ---------------------------------------------------------------------------


def _build_all_nodes(ld: LayerData) -> dict[str, dict[str, Any]]:
    """Construct the full node set from all layer data.

    Returns:
        Dict mapping node id → node dict.
    """
    all_skill_names = collect_all_skill_names(ld)
    return {
        **build_decision_nodes(ld.forks),
        **build_skill_nodes(all_skill_names),
        **build_artifact_nodes(ld.artifacts),
        **build_mcp_tool_nodes(ld.backend_routing),
        **build_backend_nodes(ld.backend_routing),
        **build_agent_nodes(ld.concurrency_map),
        **build_reference_file_nodes(ld.forks, ld.traces),
    }


def _build_all_edges(
    ld: LayerData, all_nodes: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build and deduplicate all edges; collect loop stub nodes.

    Returns:
        Two-tuple of (deduped_edges, loop_stubs).
    """
    known_fork_ids = {nid for nid in all_nodes if nid.startswith("fork.")}
    known_skill_ids = {nid for nid in all_nodes if nid.startswith("skill.")}
    branch_edges, loop_stubs = build_branch_edges_from_l1(ld.traces, known_fork_ids, known_skill_ids)
    raw: list[dict[str, Any]] = (
        branch_edges
        + build_writes_edges(ld.artifacts)
        + build_reads_edges(ld.artifacts)
        + build_dispatches_edges(ld.concurrency_map)
        + build_calls_edges(ld.backend_routing)
        + build_stores_in_edges(ld.backend_routing)
    )
    return list({e["id"]: e for e in raw}.values()), loop_stubs


def _build_graph_dict(sorted_nodes: list[dict[str, Any]], sorted_edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct the top-level graph output dict from sorted nodes and edges.

    ``meta.gap_count`` is computed as the count of assembled edges with
    ``gap: True`` -- see :func:`_process_trace` for exactly what produces a
    gap edge (hands_off_to_skill traces whose target skill isn't
    independently confirmed, and traces whose terminal_type is recognized
    but missing its required terminal_target, or is not recognized at all).
    It is never hardcoded: a hand-authored constant would silently drift
    from the actual edge set the moment either input data or the extraction
    rules above change, defeating the whole purpose of a gap-count signal
    for impact-radius analysis.

    ``meta.orphan_count`` is computed the same way, from edges with
    ``status == "orphan"`` -- see :func:`self_check` for exactly what makes
    an edge an orphan (a source or target node id absent from the assembled
    node set, typically from node-id drift on re-extraction). Also never
    hardcoded, for the same drift-avoidance reason as ``gap_count``.

    Returns:
        Graph dict ready for JSON serialisation.
    """
    gap_count = sum(1 for e in sorted_edges if e.get("gap") is True)
    orphan_count = sum(1 for e in sorted_edges if e.get("status") == "orphan")
    return {
        "meta": {
            "generated": datetime.now(tz=UTC).date().isoformat(),
            "source": "L0+L1+G1-G8 layers from docs/workflow-layers/",
            "total_nodes": len(sorted_nodes),
            "total_edges": len(sorted_edges),
            "node_type_counts": _count_types(sorted_nodes, "type"),
            "edge_type_counts": _count_types(sorted_edges, "type"),
            "routes": sorted({n["route"] for n in sorted_nodes if n.get("route")}),
            "gap_count": gap_count,
            "orphan_count": orphan_count,
        },
        "nodes": sorted_nodes,
        "edges": sorted_edges,
        "overlays": OVERLAYS,
    }


def _write_json_atomic(output_path: Path, payload: dict[str, Any]) -> None:
    """Atomically write a JSON payload to output_path.

    Writes to a uniquely named temporary file in the same directory as
    ``output_path`` (guaranteeing the final rename is on the same
    filesystem), flushes and fsyncs it to guarantee durability, then
    replaces ``output_path`` with it in a single atomic filesystem
    operation. If any step fails, the temporary file is removed and the
    original ``output_path`` (if any) is left completely untouched -- no
    partial or corrupted output file is ever observable. Mirrors the
    atomic-write pattern used by ``write_layer()`` in
    ``plugins/development-harness/scripts/merge_layer.py``.

    Raises:
        OSError: If the temporary file cannot be written, or the atomic
            replace fails. ``output_path`` is guaranteed unmodified in
            this case.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload)

    fd, tmp_name = tempfile.mkstemp(suffix=".tmp", prefix=f"{output_path.name}.", dir=output_path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(serialized)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        tmp_path.replace(output_path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def assemble(layers_dir: Path, output_path: Path) -> None:
    """Load all layer files and write the assembled graph to output_path.

    Idempotent: running twice with the same inputs produces identical output.
    """
    ld = load_layers(layers_dir)

    all_nodes = _build_all_nodes(ld)
    deduped_edges, loop_stubs = _build_all_edges(ld, all_nodes)
    all_nodes.update(loop_stubs)
    all_nodes.update(build_terminal_stub_node())

    sorted_nodes = sorted(all_nodes.values(), key=operator.itemgetter("id"))

    print("Overlay coverage:")
    sorted_edges = self_check(sorted_nodes, sorted(deduped_edges, key=operator.itemgetter("id")))
    sorted_edges = sorted(sorted_edges, key=operator.itemgetter("id"))

    # self_check() preserves every edge (never deletes) -- orphans are
    # annotated with status="orphan" in place. See docs/graph-schema.md
    # "Orphan edges" and self_check()'s docstring.
    orphan_count = sum(1 for e in sorted_edges if e.get("status") == "orphan")

    graph_dict = _build_graph_dict(sorted_nodes, sorted_edges)
    _write_json_atomic(output_path, graph_dict)

    print(
        f"Built: {len(sorted_nodes)} nodes, {len(sorted_edges)} edges, "
        f"{graph_dict['meta']['gap_count']} gaps, {orphan_count} orphans preserved"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(description="Assemble dh-workflow-graph.json from layer JSON files.")
    parser.add_argument(
        "--layers",
        type=Path,
        default=Path("plugins/development-harness/docs/workflow-layers/"),
        help="Directory containing the layer JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plugins/development-harness/docs/dh-workflow-graph.json"),
        help="Output path for the assembled graph (default: %(default)s)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    assemble(args.layers, args.output)
