"""Falsification of the decomposition-exit gate's honest-absence exit.

:class:`~dh_core.workflow_multigraph.decomposition_gate.DecompositionGate` checks a task's instructions
against the referents and quotes they cite. What this module falsifies is the one behaviour that
does not depend on any document's wording or a real referent existing in this checkout: an
``ASSERTING`` instruction that honestly records a gap (``ASSUMED``/``ABSENT`` plus a stated
``absence_note``) is reported ``CONTRACT_UNSPECIFIED`` and does not block, while the same status
with no stated gap still blocks. Tier-1 referent resolution (``FILE``, ``RULE``, ``TASK_OUTPUT``,
``ARTIFACT``, ``GRAPH_POSITION``) and Tier-2 quote verification against a real span are not covered
by any test as of this writing -- a gap, not a decision.

The gate is exercised against this actual repository checkout through
:class:`~dh_core.workflow_multigraph.decomposition_gate.RepoResolver` and
:class:`~dh_core.workflow_multigraph.decomposition_gate.RepoSourceReader` -- not stubs.
"""

from __future__ import annotations

from pathlib import Path

from dh_core.workflow_multigraph.decomposition_gate import DecompositionGate, RepoResolver, RepoSourceReader
from dh_core.workflow_multigraph.findings import Predicate, Severity
from dh_core.workflow_multigraph.instructions import Instruction, InstructionKind
from dh_core.workflow_multigraph.vocabulary import ExtractionStatus
from dh_core.workflow_multigraph.work_layer import WorkGraph

PLUGIN_ROOT: Path = Path(__file__).resolve().parents[1]
REPO_ROOT: Path = PLUGIN_ROOT.parents[1]


def build_gate() -> DecompositionGate:
    """Construct a gate wired to this actual repository checkout.

    Returns:
        A gate whose resolver and reader read this repository rather than a stub.
    """
    return DecompositionGate(RepoResolver(REPO_ROOT, WorkGraph()), RepoSourceReader(REPO_ROOT))


def test_assumed_with_absence_note_reports_contract_unspecified_and_does_not_block() -> None:
    """The honest Tier-2 exit: ASSUMED/ABSENT plus a stated gap -- CONTRACT_UNSPECIFIED, does not block."""
    gate = build_gate()
    instruction = Instruction(
        id="how-honest",
        kind=InstructionKind.ASSERTING,
        text="the retry queue backs off exponentially, doubling on every failure",
        extraction_status=ExtractionStatus.ASSUMED,
        absence_note="no source establishes this; falsify it before relying on it",
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].predicate is Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE
    assert findings[0].severity is Severity.CONTRACT_UNSPECIFIED
    assert gate.blocks((instruction,)) is False


def test_absent_status_with_absence_note_also_reports_contract_unspecified() -> None:
    """ABSENT is the other honest-gap status the gate treats the same as ASSUMED."""
    gate = build_gate()
    instruction = Instruction(
        id="how-honest-absent",
        kind=InstructionKind.ASSERTING,
        text="the ledger fold replays events in commit order",
        extraction_status=ExtractionStatus.ABSENT,
        absence_note="the sources are silent on ordering; falsify before relying on it",
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].severity is Severity.CONTRACT_UNSPECIFIED
    assert gate.blocks((instruction,)) is False


def test_assumed_status_with_no_absence_note_still_blocks() -> None:
    """ASSUMED alone, with no stated gap, is not the honest exit -- it still blocks.

    The gate requires the gap *stated*, not merely a status flag. An empty ``absence_note`` is not
    a stated gap.
    """
    gate = build_gate()
    instruction = Instruction(
        id="how-half-honest",
        kind=InstructionKind.ASSERTING,
        text="the ledger fold replays events in commit order",
        extraction_status=ExtractionStatus.ASSUMED,
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].severity is Severity.BROKEN
    assert gate.blocks((instruction,)) is True
