"""The trigger that fires when the graph IR has earned the scenario-A migration.

ADR-3460-1 decided scenario C first and scenario A "when C is functional", and listed the
criteria. Criteria written only in an ADR are enforced at no layer: nobody re-reads an accepted
decision to notice that its conditions came true. This module evaluates them instead.

Each criterion answers from an evidence artifact rather than from a code API, so the trigger stays
stable while ``dh_core.graph_ir`` is still moving. While any criterion is unmet,
:func:`test_scenario_a_is_still_locked` passes and names what is missing. When every criterion is
met it FAILS, and the failure is the trigger: read ADR-3460-1, start the migration, or amend the
decision.

The criterion that matters is the last. The others are satisfiable by a representation that merely
fits the four defects it was built against, and those four were chosen by the author of the
design. Only a defect the IR found first shows it generalises.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

PLUGIN_ROOT: Path = Path(__file__).resolve().parents[1]
CONTRACT: Path = PLUGIN_ROOT / "docs" / "graph-ir" / "ASSESSOR-CONTRACT.md"
ADR: Path = PLUGIN_ROOT / "docs" / "adrs" / "ADR-3460-1-graph-ir-owns-the-unowned-edges-first.md"
FINDINGS: Path = PLUGIN_ROOT / "docs" / "graph-ir" / "findings"
DEFECT_TESTS: Path = PLUGIN_ROOT / "tests_sam" / "test_graph_ir_defects.py"
IR_PACKAGE: Path = PLUGIN_ROOT / "dh_core" / "graph_ir"

KNOWN_DEFECTS: tuple[str, ...] = ("D1", "D2", "D3", "D4")
"""The defects already found by hand, which the IR must refuse or detect. ADR-3460-1, Context."""


class Criterion(BaseModel):
    """One condition ADR-3460-1 requires before the scenario-A migration may start."""

    key: str
    question: str
    met: bool = False
    evidence: str = Field(default="", description="What was read, and what it said.")


def contract_predicates() -> list[str]:
    """Return the falsified predicates the assessor contract lists.

    Returns:
        One entry per bullet under the contract's "Falsified predicates to report" heading.
    """
    if not CONTRACT.is_file():
        return []
    body = CONTRACT.read_text(encoding="utf-8")
    section = re.split(r"^## ", body, flags=re.MULTILINE)
    for part in section:
        if part.startswith("Falsified predicates to report"):
            return [line[2:].strip() for line in part.splitlines() if line.startswith("- ")]
    return []


def defects_covered() -> set[str]:
    """Return the known-defect identifiers the falsification test names."""
    if not DEFECT_TESTS.is_file():
        return set()
    body = DEFECT_TESTS.read_text(encoding="utf-8")
    return {defect for defect in KNOWN_DEFECTS if re.search(rf"\b{defect}\b", body)}


def fidelity_verdict() -> str:
    """Return the model-fidelity verdict, or an empty string when none has been recorded.

    The file existing is not the verdict: a fidelity pass may conclude that the extractor did
    repair an ambiguity. Only an explicit ``Verdict: faithful`` line satisfies the criterion.

    Returns:
        The verdict word recorded in the fidelity findings, lowercased, or "".
    """
    path = FINDINGS / "fidelity.md"
    if not path.is_file():
        return ""
    found = re.search(r"^verdict:\s*(\w+)", path.read_text(encoding="utf-8"), flags=re.MULTILINE | re.IGNORECASE)
    return found.group(1).lower() if found else ""


def marker(body: str, name: str) -> str:
    """Return a marker's value, read from the first line that declares it.

    Anchored to the start of a line and to the document's first declaration, so prose *about* a
    marker cannot satisfy it — a findings file explaining that "Found-by: IR" is required must not
    thereby claim it.

    Args:
        body: The findings file's text.
        name: The marker name, without punctuation.

    Returns:
        The declared value lowercased, or "" when the marker is never declared.
    """
    found = re.search(rf"^\**{name}:\**\s*(\S+)", body, flags=re.MULTILINE | re.IGNORECASE)
    return found.group(1).strip("*` ").lower() if found else ""


def ir_found_defects() -> list[str]:
    """Return defects the IR found first, read from the findings directory.

    A finding qualifies only when its file records both that the IR surfaced it and that it was
    not already known. Prose alone does not qualify it; the two markers must be present.

    Returns:
        The file stems of qualifying findings.
    """
    if not FINDINGS.is_dir():
        return []
    qualifying: list[str] = []
    for path in sorted(FINDINGS.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        if marker(body, "found-by") == "ir" and marker(body, "previously-known") == "no":
            qualifying.append(path.stem)
    return qualifying


def evaluate() -> list[Criterion]:
    """Evaluate every ADR-3460-1 exit criterion against the evidence on disk.

    Returns:
        One :class:`Criterion` per condition, in the ADR's order.
    """
    covered = defects_covered()
    missing_defects = sorted(set(KNOWN_DEFECTS) - covered)
    predicates = contract_predicates()
    expressible = IR_PACKAGE / "predicates.py"
    verdict = fidelity_verdict()
    projection = IR_PACKAGE / "control_flow.py"
    found = ir_found_defects()

    return [
        Criterion(
            key="defects-refused-or-detected",
            question="Is each known defect unrepresentable in the IR, or caught by a named predicate?",
            met=not missing_defects,
            evidence=(
                f"{DEFECT_TESTS.name} names {sorted(covered)}"
                if covered
                else f"{DEFECT_TESTS.name} is absent or names no known defect"
            )
            + (f"; missing {missing_defects}" if missing_defects else ""),
        ),
        Criterion(
            key="contract-predicates-expressible",
            question="Is every falsified predicate in the contract expressible against the IR, or recorded out of scope?",
            met=bool(predicates) and expressible.is_file(),
            evidence=(
                f"contract lists {len(predicates)} predicates; "
                f"{'found' if expressible.is_file() else 'no'} {expressible.name} to answer them"
            ),
        ),
        Criterion(
            key="projection-replaces-transitions",
            question="Does the control-flow projection reproduce ledger_spec.TRANSITIONS exactly?",
            met=projection.is_file(),
            evidence=f"{'found' if projection.is_file() else 'no'} {projection.name}",
        ),
        Criterion(
            key="model-fidelity-verified",
            question="Has a fidelity pass confirmed the extractor repaired no ambiguity and dropped no branch?",
            met=verdict == "faithful",
            evidence=(
                f"fidelity.md records Verdict: {verdict}"
                if verdict
                else f"no 'Verdict: faithful' line in {FINDINGS.name}/fidelity.md"
            ),
        ),
        Criterion(
            key="ir-found-something-new",
            question="Has the IR caught a defect nobody had already found?",
            met=bool(found),
            evidence=(
                f"qualifying findings: {found}"
                if found
                else f"no file under {FINDINGS.name}/ carries both 'Found-by: IR' and 'Previously-known: no'"
            ),
        ),
    ]


def unmet() -> list[Criterion]:
    """Return the criteria that are not yet satisfied."""
    return [criterion for criterion in evaluate() if not criterion.met]


def test_the_adr_and_its_contract_are_both_present() -> None:
    """The trigger is meaningless if the decision it enforces has been deleted or renamed."""
    assert ADR.is_file(), f"{ADR} is missing: ADR-3460-1 is what this trigger enforces"
    assert CONTRACT.is_file(), f"{CONTRACT} is missing: it defines the predicates criterion 2 counts"


def test_every_criterion_is_evaluable() -> None:
    """Each criterion must answer from evidence, so none can sit permanently undecidable."""
    for criterion in evaluate():
        assert criterion.evidence, f"criterion {criterion.key} produced no evidence either way"


def test_scenario_a_is_still_locked() -> None:
    """Fail when every ADR-3460-1 criterion is met — that failure is the trigger to start A.

    While criteria remain unmet this passes and the assertion message lists them, so the state of
    the decision is visible in a normal test run rather than only to whoever re-reads the ADR.
    """
    outstanding = unmet()
    assert outstanding, (
        "Every exit criterion in ADR-3460-1 is now met. The graph IR has earned the scenario-A "
        "migration: the IR becomes the domain model and Task/Plan become a serialization view. "
        "Read the ADR, start the migration, and delete this test — or amend the ADR if the "
        "evidence is not what it appears. Blast radius recorded in the ADR: 71 importing files, "
        "7 TaskBackend implementations, 3 MCP tools, 44 skill and agent files."
    )


def test_prose_about_a_marker_does_not_claim_it(tmp_path: Path) -> None:
    """A findings file explaining the markers must not thereby satisfy them.

    The first version of :func:`ir_found_defects` matched the marker as a substring, so this
    module's own documentation of the convention satisfied it and the trigger read as unlocked.
    """
    explaining = tmp_path / "explains.md"
    explaining.write_text(
        "# Findings\n\n"
        "**Found-by:** hand\n"
        "**Previously-known:** no\n\n"
        "A finding qualifies only with `Found-by: IR` and `Previously-known: no`.\n",
        encoding="utf-8",
    )
    body = explaining.read_text(encoding="utf-8")
    assert marker(body, "found-by") == "hand", "the declaration wins, not the prose that mentions it"
    assert marker(body, "previously-known") == "no"


def test_a_declared_ir_finding_is_recognised(tmp_path: Path) -> None:
    """The marker check must still accept a genuine claim, or criterion 5 is unreachable."""
    genuine = tmp_path / "genuine.md"
    genuine.write_text("**Found-by:** IR\n**Previously-known:** no\n", encoding="utf-8")
    body = genuine.read_text(encoding="utf-8")
    assert marker(body, "found-by") == "ir"
    assert marker(body, "previously-known") == "no"
