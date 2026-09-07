"""Falsification of the decomposition-exit gate against ``ASSESSOR-CONTRACT.md``.

Two things are checked here. First, a closure test: the predicate enum must be a bijection with the
contract's "Falsified predicates to report" bullet list, statement for statement -- this is the test
that would have caught the drift the enum already had against that list before this module existed.
Second, five seeded falsification cases against
:class:`~dh_core.graph_ir.decomposition_gate.DecompositionGate`, each a task's instruction set, each
asserting the exact outcome ``ASSESSOR-CONTRACT.md``'s "The decomposition-exit gate" section fixes
for it.

The gate is exercised against this actual repository checkout through
:class:`~dh_core.graph_ir.decomposition_gate.RepoResolver` and
:class:`~dh_core.graph_ir.decomposition_gate.RepoSourceReader` -- not stubs -- so every "resolves"
or "verifies" claim below is a claim about this checkout, checked by running the resolver rather
than asserted from reading the file tree by eye.
"""

from __future__ import annotations

from pathlib import Path

from dh_core.graph_ir.decomposition_gate import DecompositionGate, RepoResolver, RepoSourceReader
from dh_core.graph_ir.descriptors import SourceSpan
from dh_core.graph_ir.findings import PREDICATES, Predicate, Severity
from dh_core.graph_ir.instructions import Instruction, InstructionKind, Referent, ReferentKind
from dh_core.graph_ir.vocabulary import ExtractionStatus
from dh_core.graph_ir.work_layer import WorkGraph
from marko import Markdown
from marko.block import Heading, List, ListItem, Paragraph
from marko.inline import CodeSpan, RawText

PLUGIN_ROOT: Path = Path(__file__).resolve().parents[1]
REPO_ROOT: Path = PLUGIN_ROOT.parents[1]
CONTRACT: Path = PLUGIN_ROOT / "docs" / "graph-ir" / "ASSESSOR-CONTRACT.md"

FALSIFIED_PREDICATES_HEADING = "Falsified predicates to report"


def spans(*refs: str, quote: str = "") -> list[SourceSpan]:
    return [SourceSpan(ref=r, quote=quote) for r in refs]


def contract_predicate_statements() -> list[str]:
    """Return the contract's own bullets under "Falsified predicates to report", via the marko AST.

    Mirrors the CONTRACT-path pattern in ``test_graph_ir_layers.py`` -- reading the governing
    document as data rather than trusting a hand-copied list -- and, per this repo's rule
    (``AGENTS.md``), parses markdown structure (headings, list items, inline code) with marko
    rather than a hand-rolled regex.

    Returns:
        One string per bullet, backtick code spans unwrapped to plain text.
    """
    doc = Markdown(extensions=["gfm"]).parse(CONTRACT.read_text(encoding="utf-8"))
    in_section = False
    for child in doc.children:
        if isinstance(child, Heading) and child.level == 2:
            if in_section:
                break
            in_section = "".join(c.children for c in child.children if isinstance(c, RawText)).strip() == (
                FALSIFIED_PREDICATES_HEADING
            )
            continue
        if in_section and isinstance(child, List):
            statements: list[str] = []
            for item in child.children:
                if not isinstance(item, ListItem):
                    continue
                parts: list[str] = []
                for block in item.children:
                    if not isinstance(block, Paragraph):
                        continue
                    parts.extend(
                        str(inline.children) for inline in block.children if isinstance(inline, (RawText, CodeSpan))
                    )
                statements.append("".join(parts))
            return statements
    return []


def test_predicate_enum_is_a_bijection_with_the_contracts_falsified_predicates_list():
    """Every bullet under "Falsified predicates to report" names exactly one Predicate, and vice versa.

    This is the test the drift needed: the contract's bullet list grew and the enum did not keep
    pace, and nothing compared the two. A set-equality check on the wording alone would still pass
    on a coincidental duplicate-and-drop pair, so this also checks the counts match 1:1.
    """
    contract_statements = contract_predicate_statements()
    assert contract_statements, "could not read the contract's bullet list at all -- fix the parser, not the test"

    enum_wording = {PREDICATES[p].statement for p in Predicate}
    contract_wording = set(contract_statements)

    assert enum_wording == contract_wording, (
        f"drift between Predicate and the contract's bullet list -- "
        f"in contract, not enum: {contract_wording - enum_wording}; "
        f"in enum, not contract: {enum_wording - contract_wording}"
    )
    assert len(contract_statements) == len(Predicate), "duplicate or missing bullet: counts must match 1:1"


# -- the gate, exercised against this actual repo checkout --------------------------------------------------------


def build_gate() -> DecompositionGate:
    return DecompositionGate(RepoResolver(REPO_ROOT, WorkGraph()), RepoSourceReader(REPO_ROOT))


def test_case_1_unwarranted_how_asserting_instruction_with_no_span_blocks():
    """An asserting instruction prescribing a method with no span at all -- BROKEN, blocks.

    This is Tier 2's plainest failure: "a prescribed method carries no evidence, and none is
    recorded as absent." No ``source_refs``, no ``extraction_status``, no ``absence_note``.
    """
    gate = build_gate()
    instruction = Instruction(
        id="how-1",
        kind=InstructionKind.ASSERTING,
        text="the retry queue backs off exponentially, doubling on every failure",
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].predicate is Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE
    assert findings[0].severity is Severity.BROKEN
    assert gate.blocks((instruction,)) is True


def test_case_2_warranted_how_asserting_instruction_quoting_a_verified_real_span_does_not_block():
    """An asserting instruction quoting a real, verbatim span in this repo -- passes, does not block."""
    gate = build_gate()
    instruction = Instruction(
        id="how-2",
        kind=InstructionKind.ASSERTING,
        text="a delegating instruction must resolve because it sends the agent somewhere",
        source_refs=spans(
            f"{CONTRACT.relative_to(REPO_ROOT)}#L173", quote="An instruction that sends the agent somewhere"
        ),
    )
    findings = gate.check((instruction,))
    assert findings == ()
    assert gate.blocks((instruction,)) is False


def test_case_3a_how_citing_a_span_that_does_not_exist_blocks():
    """An asserting instruction citing a ref whose path does not exist -- BROKEN, blocks.

    Worse than none, per the contract: "A citation that does not resolve is worse than none, because
    it buys the authority of a source without one."
    """
    gate = build_gate()
    instruction = Instruction(
        id="how-3a",
        kind=InstructionKind.ASSERTING,
        text="tasks retry up to five times before escalating",
        source_refs=spans(
            "plugins/development-harness/docs/graph-ir/DOES-NOT-EXIST.md#L1", quote="tasks retry up to five times"
        ),
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].predicate is Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE
    assert findings[0].severity is Severity.BROKEN
    assert gate.blocks((instruction,)) is True


def test_case_3b_how_citing_a_real_ref_whose_quote_is_not_in_it_blocks():
    """An asserting instruction citing a real ref, but a quote that is not there verbatim -- BROKEN, blocks."""
    gate = build_gate()
    instruction = Instruction(
        id="how-3b",
        kind=InstructionKind.ASSERTING,
        text="the retry queue backs off exponentially",
        source_refs=spans(
            f"{CONTRACT.relative_to(REPO_ROOT)}#L173",
            quote="the retry queue backs off exponentially, doubling on every failure",
        ),
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].predicate is Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE
    assert findings[0].severity is Severity.BROKEN
    assert gate.blocks((instruction,)) is True


def test_case_4_how_citing_a_real_verified_span_that_does_not_support_the_claim_does_not_block():
    """A real span, verified verbatim, that does not support the claim it is cited for -- PASSES.

    This is the documented residue the gate hands to the adversarial pass, per the contract's "What
    the gate does not decide": "A quote that resolves and verifies but does not support the claim
    passes. ... Both are judgement, and both go to the adversarial pass. The gate's contribution is
    making them the *only* remaining failure mode rather than two among many." The instruction below
    claims something about retry backoff; the quote it cites is real and verbatim, but is a sentence
    about design-principle preservation that has nothing to do with retries. The gate does not, and
    per the contract must not, catch this -- it is exactly the case that must survive to the
    adversarial pass rather than being caught (and so silently "handled") here.
    """
    gate = build_gate()
    instruction = Instruction(
        id="how-4",
        kind=InstructionKind.ASSERTING,
        text="the retry queue backs off exponentially, doubling on every failure",
        source_refs=spans(
            f"{CONTRACT.relative_to(REPO_ROOT)}#L66",
            quote="Nothing here is preserved because the incumbent implementation has it.",
        ),
    )
    findings = gate.check((instruction,))
    assert findings == (), "citation padding: a real, verified quote beside an unrelated claim must pass the gate"
    assert gate.blocks((instruction,)) is False


def test_case_5_delegating_to_a_skill_that_does_not_exist_blocks():
    """The contract's own illustrative example: 'Load `restructuring-to-solid`' -- BROKEN, blocks.

    ``ASSESSOR-CONTRACT.md``, Tier 1: "'Load `restructuring-to-solid`' declares that skill exists;
    the repository demonstrably lacks it; a declared predicate is demonstrably false, so the basis
    is DECLARED and the severity BROKEN."
    """
    gate = build_gate()
    instruction = Instruction(
        id="delegate-bad",
        kind=InstructionKind.DELEGATING,
        text="load the `restructuring-to-solid` skill",
        referents=(
            Referent(
                kind=ReferentKind.SKILL,
                target="restructuring-to-solid",
                source_refs=spans(str(CONTRACT.relative_to(REPO_ROOT))),
            ),
        ),
    )
    findings = gate.check((instruction,))
    assert len(findings) == 1
    assert findings[0].predicate is Predicate.REFERENT_DOES_NOT_RESOLVE
    assert findings[0].severity is Severity.BROKEN
    assert gate.blocks((instruction,)) is True


def test_case_5_real_skills_and_a_real_rules_file_resolve_and_do_not_block():
    """The contrast the owner's example draws: real referents in this repo resolve and do not block.

    Verified directly (not assumed) before writing this assertion:

    * ``python-engineering:python3-typing`` resolves --
      ``plugins/python-engineering/skills/python3-typing/SKILL.md`` exists. A *bare* plugin name
      ("python-engineering") does not resolve as SKILL under the contract's own tier-1 definition
      ("a directory containing SKILL.md") -- ``plugins/python-engineering/`` itself contains no
      ``SKILL.md``, only its ``skills/*/`` subdirectories do -- so the qualified ``plugin:skill``
      form is used here instead, matching this repo's own skill-addressing convention
      (``AGENTS.md``: ``python-engineering:python3-typing``).
    * ``modernpython`` resolves bare -- ``plugins/python-engineering/skills/modernpython/SKILL.md``
      exists (also under ``plugins/python3-development/skills/modernpython/``; the resolver only
      needs one match).
    * ``rules/commit-cadence-and-worktrees.md`` resolves as a RULE -- the file exists at the repo
      root's ``rules/`` directory.
    """
    resolver = RepoResolver(REPO_ROOT, WorkGraph())
    good_referents = (
        Referent(kind=ReferentKind.SKILL, target="python-engineering:python3-typing", source_refs=spans("x.md")),
        Referent(kind=ReferentKind.SKILL, target="modernpython", source_refs=spans("x.md")),
        Referent(kind=ReferentKind.RULE, target="rules/commit-cadence-and-worktrees.md", source_refs=spans("x.md")),
    )
    for referent in good_referents:
        assert resolver.resolve(referent) is not None, f"expected {referent.target!r} to resolve, and it did not"

    gate = build_gate()
    instruction = Instruction(
        id="delegate-good",
        kind=InstructionKind.DELEGATING,
        text="see python-engineering:python3-typing, modernpython, and rules/commit-cadence-and-worktrees.md",
        referents=good_referents,
    )
    assert gate.check((instruction,)) == ()
    assert gate.blocks((instruction,)) is False


# -- the honest exit: recorded absence --------------------------------------------------------


def test_assumed_with_absence_note_reports_contract_unspecified_and_does_not_block():
    """The honest Tier-2 exit: ASSUMED/ABSENT plus a stated gap -- CONTRACT_UNSPECIFIED, does not block.

    ``ASSESSOR-CONTRACT.md``: "An assertion marked ASSUMED or ABSENT with the gap stated ... does
    not falsify the predicate ... It is reported at CONTRACT_UNSPECIFIED and does not block."
    """
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


def test_absent_status_with_absence_note_also_reports_contract_unspecified():
    """ABSENT is the other honest-gap status the contract names, alongside ASSUMED."""
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


def test_assumed_status_with_no_absence_note_still_blocks():
    """ASSUMED alone, with no stated gap, is not the honest exit -- it still blocks.

    The contract requires the gap *stated*, not merely a status flag: "ASSUMED or ABSENT with the
    gap stated". An empty ``absence_note`` is not a stated gap.
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
