"""Falsification of the decomposition-exit gate's honest-absence exit.

:class:`~dh_core.workflow_multigraph.decomposition_gate.DecompositionGate` checks a task's instructions
against the referents and quotes they cite. What this module falsifies is the one behaviour that
does not depend on any document's wording or a real referent existing in this checkout: an
``ASSERTING`` instruction that honestly records a gap (``ASSUMED``/``ABSENT`` plus a stated
``absence_note``) is reported ``CONTRACT_UNSPECIFIED`` and does not block, while the same status
with no stated gap still blocks.

Tier-1 ``ARTIFACT`` resolution is falsified here too, against this checkout's own artifact
registry: that referent kind shipped with no test over the gate's own path, and the gate rejected
every valid ``ARTIFACT`` referent because it looked for the registry under a heading AGENTS.md did
not carry. A test over the registry table's contents sat green throughout -- it read the same table
by its header row -- so the test that closes this reads nothing directly and asks the gate.
Tier-1 ``FILE``, ``RULE``, ``TASK_OUTPUT`` and ``GRAPH_POSITION`` resolution, and Tier-2 quote
verification against a real span, remain uncovered as of this writing -- a gap, not a decision.

The gate is exercised against this actual repository checkout through
:class:`~dh_core.workflow_multigraph.decomposition_gate.RepoResolver` and
:class:`~dh_core.workflow_multigraph.decomposition_gate.RepoSourceReader` -- not stubs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dh_core.artifact_registry import AGENTS_MD, registry_rows
from dh_core.workflow_multigraph.decomposition_gate import DecompositionGate, RepoResolver, RepoSourceReader
from dh_core.workflow_multigraph.descriptors import SourceSpan
from dh_core.workflow_multigraph.findings import Predicate, Severity
from dh_core.workflow_multigraph.instructions import Instruction, InstructionKind, Referent, ReferentKind
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


def artifact_instruction(target: str) -> Instruction:
    """Build a DELEGATING instruction naming one ARTIFACT referent.

    Args:
        target: The referent's ``'<type>#<id>'`` target.

    Returns:
        An instruction whose single referent is that artifact.
    """
    return Instruction(
        id=f"read-{target}",
        kind=InstructionKind.DELEGATING,
        text=f"read the {target} artifact before starting",
        referents=(
            Referent(
                kind=ReferentKind.ARTIFACT,
                target=target,
                source_refs=[SourceSpan(ref="plugins/development-harness/AGENTS.md")],
            ),
        ),
    )


@pytest.mark.parametrize("artifact_type", sorted(row.artifact_type for row in registry_rows(AGENTS_MD)))
def test_every_registered_artifact_type_resolves_through_the_gate(artifact_type: str) -> None:
    """A referent naming a registered type and an id resolves, so the gate does not block it.

    Tests: RepoResolver.resolve_artifact over this checkout, through DecompositionGate.blocks
    How: For each type the shared locator reads out of AGENTS.md, ask the gate to check a
         DELEGATING instruction naming that type with an id.
    Why: The gate located the registry by a heading AGENTS.md did not carry, so it read no types at
         all and rejected every valid ARTIFACT referent as BROKEN. The parametrisation takes the
         types from the locator rather than restating them, so this asserts what the pair of
         readers must agree on -- the gate resolves exactly what the registry declares -- rather
         than re-encoding the table's contents a third time. Reading the table and checking its
         contents cannot catch this: a test of that shape was green while the gate was broken.
    """
    gate = build_gate()
    instruction = artifact_instruction(f"{artifact_type}#some-artifact-id")

    assert gate.check((instruction,)) == ()
    assert gate.blocks((instruction,)) is False


@pytest.mark.parametrize(
    "target",
    ["not-a-registered-artifact-type#some-id", "code-review", "code-review#"],
    ids=["unregistered-type", "no-id", "empty-id"],
)
def test_artifact_referent_without_a_registered_type_and_an_id_blocks(target: str) -> None:
    """A referent naming an unregistered type, or carrying no id, does not resolve.

    Tests: RepoResolver.resolve_artifact's two rejection paths
    How: Check instructions whose ARTIFACT target names a type outside the registry, or names a
         registered type with no id at all.
    Why: Without this the test above is satisfied by a resolver that accepts everything, which is
         the opposite defect and equally silent. ARCHITECTURE.md's Tier-1 table requires "a type in
         the artifact registry, with its id" -- both halves.
    """
    gate = build_gate()
    findings = gate.check((artifact_instruction(target),))

    assert len(findings) == 1
    assert findings[0].predicate is Predicate.REFERENT_DOES_NOT_RESOLVE
    assert findings[0].severity is Severity.BROKEN
