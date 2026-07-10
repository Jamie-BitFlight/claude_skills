"""Tests for gap-edge wiring and gap_count computation in assemble_graph.py.

Covers the documented contract from the module and _process_trace docstrings:
which terminal_type/terminal_target combinations produce a `gap` edge
(verified=False, gap=True), and that meta.gap_count in the assembled output
is always derived from the actual edge set, never hardcoded. See
plugins/development-harness/docs/graph-schema.md ("gap" edge type) for the
schema this implements.
"""

from __future__ import annotations

from assemble_graph import _build_graph_dict, _process_trace, build_branch_edges_from_l1, self_check


def _trace(**overrides: object) -> dict[str, object]:
    """Build a minimal L1 trace dict, overridable per test."""
    base: dict[str, object] = {
        "from_fork": "work-backlog-item.q3-2",
        "branch_condition": "YES",
        "terminal_type": "hands_off_to_skill",
        "terminal_target": "find-cause",
        "source_file": "skills/work-backlog-item/references/workflows/work/prepare.md:## Step 3",
    }
    base.update(overrides)
    return base


class TestHandsOffToSkillGapEdges:
    def test_produces_gap_edge_and_stub_when_target_unknown(self) -> None:
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace()

        _process_trace(
            trace, known_fork_ids={"fork.work_backlog_item_q3_2"}, known_skill_ids=set(), edges=edges, extra_stubs=stubs
        )

        gap_edges = [e for e in edges.values() if e["type"] == "gap"]
        assert len(gap_edges) == 1
        edge = gap_edges[0]
        assert edge["verified"] is False
        assert edge["gap"] is True
        assert edge["source"] == "fork.work_backlog_item_q3_2"
        assert edge["target"] == "skill.find_cause"

        # A stub skill node was created since the target isn't independently known.
        assert "skill.find_cause" in stubs
        assert stubs["skill.find_cause"]["type"] == "skill"
        assert stubs["skill.find_cause"]["verified"] is False

    def test_no_stub_created_when_target_skill_already_known(self) -> None:
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace()

        _process_trace(
            trace,
            known_fork_ids={"fork.work_backlog_item_q3_2"},
            known_skill_ids={"skill.find_cause"},
            edges=edges,
            extra_stubs=stubs,
        )

        gap_edges = [e for e in edges.values() if e["type"] == "gap"]
        assert len(gap_edges) == 1
        assert gap_edges[0]["target"] == "skill.find_cause"
        # Already known -- no stub needed.
        assert "skill.find_cause" not in stubs


class TestCompletesWorkflowUnchangedBehavior:
    """Regression coverage: completes_workflow's existing deliberate design
    (routes_to only for a known skill target; heading-phrase targets are
    silently skipped, not treated as gaps) must be unaffected by the new
    gap-edge wiring."""

    def test_known_skill_target_produces_routes_to_not_gap(self) -> None:
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace(terminal_type="completes_workflow", terminal_target="work-backlog-item")

        _process_trace(
            trace, known_fork_ids=set(), known_skill_ids={"skill.work_backlog_item"}, edges=edges, extra_stubs=stubs
        )

        assert len(edges) == 1
        edge = next(iter(edges.values()))
        assert edge["type"] == "routes_to"
        assert edge["gap"] is False
        assert edge["verified"] is True

    def test_heading_phrase_target_still_silently_skipped(self) -> None:
        """A completes_workflow target that is a workflow-internal heading
        phrase (not a known skill name) produces NO edge -- this is the
        pre-existing, deliberate design (see collect_all_skill_names
        docstring), not a gap: it is not converted to a gap edge because the
        target-type ambiguity (heading vs skill) means there is no reliable
        signal to hang a gap edge on."""
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace(
            terminal_type="completes_workflow", terminal_target="Phase 3 architect delegation (no injection)"
        )

        _process_trace(
            trace, known_fork_ids={"fork.work_backlog_item_q3_2"}, known_skill_ids=set(), edges=edges, extra_stubs=stubs
        )

        # No edge and no target-related stub -- only the (already-known) source
        # fork stub logic runs unconditionally and adds nothing here.
        assert edges == {}
        assert stubs == {}


class TestMissingTargetAndUnrecognizedTypeProduceGap:
    def test_completes_workflow_missing_target_produces_gap(self) -> None:
        """A completes_workflow trace with no terminal_target (observed in
        the shipped L1 layer files) must not be silently dropped."""
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace(terminal_type="completes_workflow", terminal_target=None)

        _process_trace(trace, known_fork_ids=set(), known_skill_ids=set(), edges=edges, extra_stubs=stubs)

        gap_edges = [e for e in edges.values() if e["type"] == "gap"]
        assert len(gap_edges) == 1
        assert gap_edges[0]["verified"] is False
        assert gap_edges[0]["gap"] is True
        label = gap_edges[0]["label"]
        assert isinstance(label, str)
        assert "missing" in label
        assert gap_edges[0]["target"] == "terminal.stop"

    def test_unrecognized_terminal_type_produces_gap_with_stub(self) -> None:
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace(terminal_type="some_future_type", terminal_target="some-target")

        _process_trace(trace, known_fork_ids=set(), known_skill_ids=set(), edges=edges, extra_stubs=stubs)

        gap_edges = [e for e in edges.values() if e["type"] == "gap"]
        assert len(gap_edges) == 1
        label = gap_edges[0]["label"]
        assert isinstance(label, str)
        assert "unrecognized" in label
        assert gap_edges[0]["target"] == "ref.some_target"
        assert "ref.some_target" in stubs
        assert stubs["ref.some_target"]["type"] == "reference_file"

    def test_empty_terminal_type_produces_no_edge(self) -> None:
        """A trace with no terminal_type at all is not a transition to
        represent -- must not fabricate a gap edge from nothing."""
        edges: dict[str, dict[str, object]] = {}
        stubs: dict[str, dict[str, object]] = {}
        trace = _trace(terminal_type="", terminal_target="")

        _process_trace(trace, known_fork_ids=set(), known_skill_ids=set(), edges=edges, extra_stubs=stubs)

        assert edges == {}


class TestGapCountComputedNotHardcoded:
    def test_zero_gap_edges_yields_zero_gap_count(self) -> None:
        nodes = [{"id": "a", "type": "decision"}, {"id": "b", "type": "skill"}]
        edges = [{"id": "e1", "type": "routes_to", "source": "a", "target": "b", "gap": False}]
        graph = _build_graph_dict(nodes, edges)
        assert graph["meta"]["gap_count"] == 0

    def test_gap_edges_counted_correctly(self) -> None:
        nodes = [{"id": "a", "type": "decision"}, {"id": "b", "type": "skill"}, {"id": "c", "type": "skill"}]
        edges = [
            {"id": "e1", "type": "routes_to", "source": "a", "target": "b", "gap": False},
            {"id": "e2", "type": "gap", "source": "a", "target": "c", "gap": True},
            {"id": "e3", "type": "gap", "source": "b", "target": "c", "gap": True},
        ]
        graph = _build_graph_dict(nodes, edges)
        assert graph["meta"]["gap_count"] == 2
        assert graph["meta"]["total_edges"] == 3


class TestGapEdgesSurviveSelfCheck:
    def test_gap_edge_with_valid_stub_target_is_not_orphaned(self) -> None:
        """The stub node _process_trace creates for an unresolved gap target
        must be sufficient for self_check to keep the gap edge -- otherwise
        the exact signal the gap edge exists to preserve would be silently
        stripped right back out."""
        traces = [_trace()]
        branch_edges, stubs = build_branch_edges_from_l1(traces, known_fork_ids=set(), known_skill_ids=set())

        all_nodes = [{"id": "fork.work_backlog_item_q3_2", "type": "decision"}, *stubs.values()]
        cleaned = self_check(all_nodes, branch_edges)

        gap_edges = [e for e in cleaned if e["type"] == "gap"]
        assert len(gap_edges) == 1
