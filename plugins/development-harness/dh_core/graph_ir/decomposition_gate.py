"""The decomposition-exit gate: checks a task's instructions against the referents they name.

``plugins/development-harness/ARCHITECTURE.md``, "The work graph" § "The decomposition-exit gate":
"Origin is not measurable from text -- a sentence invented from training reads exactly like one
recalled from a source. Absence of referent is measurable, and the two coincide." This module is
that measurement:
:class:`DecompositionGate` resolves every :class:`~dh_core.graph_ir.instructions.Referent` a
``DELEGATING`` instruction names (Tier 1) and verifies every quote an ``ASSERTING`` instruction
cites (Tier 2), and reports a :class:`~dh_core.graph_ir.findings.Finding` for each declared
predicate that does not hold.

Two protocols separate *what the gate checks* from *how referents and sources are read*:
:class:`ReferentResolver` answers "does this referent exist", :class:`SourceReader` answers "what
text is at this ref". :class:`RepoResolver` and :class:`RepoSourceReader` are the concrete
implementations over an actual repo checkout and a
:class:`~dh_core.graph_ir.work_layer.WorkGraph`, but the gate itself is written against the
protocols so a test can substitute a stub.

The severity mapping is the contract's own, and it is fixed here rather than derived: an
unresolved referent, an asserting instruction with no evidence at all, and one whose quote does not
verify are all reported ``DECLARED`` -> ``BROKEN`` -- "the instruction is the declaration". An
instruction that honestly records the gap (``ASSUMED``/``ABSENT`` with a non-empty
``absence_note``) is reported ``UNSPECIFIED`` -> ``CONTRACT_UNSPECIFIED`` and does not block: "does
not falsify the predicate ... It is reported at CONTRACT_UNSPECIFIED and does not block." Severity
itself is never assigned here -- as everywhere in this package, it comes from
:data:`~dh_core.graph_ir.findings.SEVERITY_BY_BASIS` alone, computed on the :class:`Finding` from
the ``basis`` this module chooses.

What this module does not decide: a quote that resolves and verifies but does not support the claim
it is cited for. Per ``plugins/development-harness/ARCHITECTURE.md``, "The work graph" §
"The judgement tier blocks, and demotion clears it", that support question is judgement, not a
referent or verbatim-quote check, and this module leaves it to the adversarial pass untouched.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from marko import Markdown
from marko.block import Heading
from marko.ext.gfm.elements import Table
from marko.inline import CodeSpan, RawText

from dh_core.graph_ir.descriptors import SourceSpan
from dh_core.graph_ir.findings import ContractBasis, Finding, Predicate, Severity
from dh_core.graph_ir.instructions import Instruction, InstructionKind, Referent, ReferentKind
from dh_core.graph_ir.model import Observation
from dh_core.graph_ir.work_layer import WorkGraph

CONTRACT_REF = "plugins/development-harness/ARCHITECTURE.md#the-decomposition-exit-gate"
"""Where the decomposition-exit gate itself is declared; cited as every finding's source span."""

CONTRACT_SPAN = SourceSpan(ref=CONTRACT_REF)
"""The one source span every gate finding cites: where the rule it falsifies is declared."""

ARTIFACT_SECTION_HEADING = "Artifact types and registering agents"
"""The AGENTS.md heading whose table :func:`artifact_types` reads."""


@runtime_checkable
class ReferentResolver(Protocol):
    """Resolves a Tier-1 :class:`Referent` to what it names, or ``None`` when it does not exist."""

    def resolve(self, referent: Referent) -> str | None:
        """Return what ``referent`` resolves to, or ``None`` when it does not resolve.

        Args:
            referent: The referent a ``DELEGATING`` instruction named.

        Returns:
            A string describing what was found (a path, a node id, ...), or ``None``.
        """
        ...


@runtime_checkable
class SourceReader(Protocol):
    """Reads the text a :class:`~dh_core.graph_ir.descriptors.SourceSpan` names, or ``None``."""

    def read(self, ref: str) -> str | None:
        """Return the text at ``ref``, or ``None`` when ``ref`` does not exist.

        Args:
            ref: A :attr:`~dh_core.graph_ir.descriptors.SourceSpan.ref`, e.g. ``'a.py#L10-L20'``.

        Returns:
            The text at that span, or the whole file for a bare path; ``None`` when the path itself
            does not exist.
        """
        ...


def heading_text(heading: Heading) -> str:
    """Reconstruct a marko ``Heading``'s plain text from its inline children.

    Args:
        heading: A parsed marko ``Heading`` node.

    Returns:
        The heading's text, inline formatting stripped.
    """
    return "".join(child.children for child in heading.children if isinstance(child, RawText))


def cell_text(cell: object) -> str:
    """Reconstruct a marko GFM table cell's plain text, unwrapping a code span.

    Args:
        cell: A parsed marko ``TableCell`` node.

    Returns:
        The cell's text, with any backtick code-span markers removed.
    """
    parts = [str(child.children) for child in getattr(cell, "children", []) if isinstance(child, (RawText, CodeSpan))]
    return "".join(parts)


def artifact_types(agents_md: Path) -> frozenset[str]:
    """Return the artifact types the plugin's own registry table names.

    Parses the "Artifact types and registering agents" table in ``plugins/development-harness/
    AGENTS.md`` via the marko GFM AST, per this repo's rule to parse markdown structure with marko
    rather than regex. Returns an empty set, rather than raising, when the file or table is absent
    -- an ARTIFACT referent then simply fails to resolve, which is the gate's own reporting job.

    Args:
        agents_md: Path to the plugin's ``AGENTS.md``.

    Returns:
        Every value in the table's ``Type`` column, backtick markers stripped.
    """
    if not agents_md.is_file():
        return frozenset()
    doc = Markdown(extensions=["gfm"]).parse(agents_md.read_text(encoding="utf-8"))
    in_section = False
    for child in doc.children:
        if isinstance(child, Heading):
            if in_section:
                break
            in_section = heading_text(child).strip() == ARTIFACT_SECTION_HEADING
            continue
        if in_section and isinstance(child, Table):
            body_rows = child.children[1:]  # first row is the header
            types: set[str] = set()
            for row in body_rows:
                cells = getattr(row, "children", None)
                if cells:
                    types.add(cell_text(cells[0]).strip())
            return frozenset(types)
    return frozenset()


def normalize(text: str) -> str:
    """Collapse ``text`` to single-spaced words, for containment comparison only.

    Args:
        text: The text to collapse.

    Returns:
        ``text`` with every run of whitespace reduced to a single space, leading and trailing
        whitespace stripped.
    """
    return " ".join(text.split())


class RepoResolver:
    """Resolves Tier-1 referents against a repo checkout and a decomposed :class:`WorkGraph`.

    Skill existence is deliberately not one of these referents. A skill name is verified by the
    acting agent in its own harness at runtime, not by this gate at decomposition time: skill
    availability is a property of the agent harness the work eventually runs in (Claude Code,
    Codex, Hermes, OpenCode, Cursor, pi, Kimi Code, Kilo Code each resolve skills their own way),
    not of this repository's filesystem layout, and a built-in skill (Claude Code's ``/code-review``,
    say) lives in no plugin directory here at all.
    """

    def __init__(self, repo_root: Path, work: WorkGraph) -> None:
        """Initialize the resolver.

        Args:
            repo_root: The repository checkout root that ``FILE`` and ``RULE`` referents are
                resolved relative to.
            work: The decomposed layer-2 graph that ``TASK_OUTPUT`` and ``GRAPH_POSITION`` referents
                are resolved against.
        """
        self._repo_root = repo_root
        self._work = work

    def resolve(self, referent: Referent) -> str | None:
        """Resolve ``referent`` per the decomposition-exit gate's tier-1 table.

        Args:
            referent: The referent to resolve.

        Returns:
            What was found, or ``None`` when the referent does not resolve.
        """
        resolvers = {
            ReferentKind.FILE: self.resolve_file,
            ReferentKind.RULE: self.resolve_rule,
            ReferentKind.TASK_OUTPUT: self.resolve_work_node,
            ReferentKind.GRAPH_POSITION: self.resolve_work_node,
            ReferentKind.ARTIFACT: self.resolve_artifact,
        }
        return resolvers[referent.kind](referent.target)

    def resolve_file(self, target: str) -> str | None:
        """Resolve a ``FILE`` referent: a repo-relative path that must exist.

        Args:
            target: The repo-relative path to resolve.

        Returns:
            The resolved path, or ``None`` when it does not exist.
        """
        candidate = self._repo_root / target
        return str(candidate) if candidate.exists() else None

    def resolve_rule(self, target: str) -> str | None:
        """Resolve a ``RULE`` referent: a rules file, optionally with a ``#section`` anchor.

        Args:
            target: A ``rules/``-relative or bare filename, optionally suffixed ``#Section Name``.

        Returns:
            The resolved path, or ``None`` when the file (or its named section) does not exist.
        """
        path_part, _, section = target.partition("#")
        candidates = [self._repo_root / path_part]
        if not path_part.startswith("rules/"):
            candidates.append(self._repo_root / "rules" / path_part)
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if section:
                text = candidate.read_text(encoding="utf-8")
                if not re.search(rf"^#+\s+{re.escape(section)}\s*$", text, re.MULTILINE | re.IGNORECASE):
                    continue
            return str(candidate)
        return None

    def resolve_work_node(self, target: str) -> str | None:
        """Resolve a ``TASK_OUTPUT`` or ``GRAPH_POSITION`` referent against the work graph.

        Args:
            target: The work-graph node id the referent names.

        Returns:
            The node's id, or ``None`` when no node in the graph carries it.
        """
        try:
            return self._work.node(target).id
        except KeyError:
            return None

    def resolve_artifact(self, target: str) -> str | None:
        """Resolve an ``ARTIFACT`` referent: a ``type#id`` pair against the artifact registry.

        Args:
            target: A ``'<type>#<id>'`` string.

        Returns:
            ``target`` unchanged when its type is in the registry and it carries an id; ``None``
            otherwise.
        """
        artifact_type, sep, artifact_id = target.partition("#")
        if not sep or not artifact_id:
            return None
        agents_md = self._repo_root / "plugins" / "development-harness" / "AGENTS.md"
        if artifact_type in artifact_types(agents_md):
            return target
        return None


class RepoSourceReader:
    """Reads source text at a :class:`~dh_core.graph_ir.descriptors.SourceSpan` ref, for Tier 2."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the reader.

        Args:
            repo_root: The repository checkout root every ``ref`` is resolved relative to.
        """
        self._repo_root = repo_root

    def read(self, ref: str) -> str | None:
        """Return the text at ``ref``, or ``None`` when the path it names does not exist.

        Args:
            ref: A ``path``, ``path#L10`` or ``path#L10-L20`` reference.

        Returns:
            The line range for a ``path#L10-L20`` (or single ``path#L10``) ref; the whole file for a
            bare path, and for any other anchor form this does not parse as a line range.
        """
        path_part, _, anchor = ref.partition("#")
        path = self._repo_root / path_part
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", anchor) if anchor else None
        if not match:
            return text
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        lines = text.splitlines()
        return "\n".join(lines[max(start - 1, 0) : end])


class DecompositionGate:
    """The decomposition-exit gate over a task's instructions.

    Constructed against a :class:`ReferentResolver` and a :class:`SourceReader` rather than a repo
    path directly, so a test can substitute stubs without touching the filesystem.
    """

    def __init__(self, resolver: ReferentResolver, reader: SourceReader) -> None:
        """Initialize the gate.

        Args:
            resolver: Resolves Tier-1 referents.
            reader: Reads Tier-2 source text for quote verification.
        """
        self._resolver = resolver
        self._reader = reader

    def check(self, instructions: Sequence[Instruction]) -> tuple[Finding, ...]:
        """Check every instruction against the tier it declares.

        Args:
            instructions: The instructions a task carries out of decomposition.

        Returns:
            One finding per falsified predicate; empty when every instruction resolves or quotes.
        """
        findings: list[Finding] = []
        for instruction in instructions:
            if instruction.kind is InstructionKind.DELEGATING:
                findings.extend(self.check_delegating(instruction))
            else:
                findings.extend(self.check_asserting(instruction))
        return tuple(findings)

    def blocks(self, instructions: Sequence[Instruction]) -> bool:
        """Return whether any finding over ``instructions`` is severity ``BROKEN``.

        Args:
            instructions: The instructions a task carries out of decomposition.

        Returns:
            True iff :meth:`check` returns at least one ``BROKEN`` finding.
        """
        return any(finding.severity is Severity.BROKEN for finding in self.check(instructions))

    def check_delegating(self, instruction: Instruction) -> tuple[Finding, ...]:
        """Check one ``DELEGATING`` instruction's referents against Tier 1.

        Args:
            instruction: The instruction to check.

        Returns:
            One finding per referent that does not resolve; empty when every referent resolves.
        """
        findings: list[Finding] = []
        for referent in instruction.referents:
            resolved = self._resolver.resolve(referent)
            if resolved is not None:
                continue
            observation = Observation(
                subject=f"{instruction.id}:{referent.kind.value}:{referent.target}",
                expected=f"referent {referent.target!r} ({referent.kind.value}) resolves at decomposition time",
                observed="does not resolve; the repository demonstrably lacks it",
            )
            findings.append(
                Finding.from_observation(
                    Predicate.REFERENT_DOES_NOT_RESOLVE,
                    ContractBasis.DECLARED,
                    (
                        "ARCHITECTURE.md, 'The decomposition-exit gate' Tier 1: 'An instruction that sends the agent somewhere names "
                        "a referent, and the referent must exist at decomposition time. ... The instruction "
                        f"is the declaration.' Instruction {instruction.text!r} declares {referent.target!r} "
                        "exists; it does not."
                    ),
                    observation,
                    (*referent.source_refs,),
                    (instruction.id,),
                )
            )
        return tuple(findings)

    def check_asserting(self, instruction: Instruction) -> tuple[Finding, ...]:
        """Check one ``ASSERTING`` instruction's spans against Tier 2.

        Args:
            instruction: The instruction to check.

        Returns:
            Empty when a span verifies; one ``CONTRACT_UNSPECIFIED`` finding for an honestly
            recorded absence; otherwise one ``BROKEN`` finding.
        """
        if any(span.quote.strip() and self.quote_verifies(span.ref, span.quote) for span in instruction.source_refs):
            return ()
        if instruction.is_recorded_absent():
            # is_recorded_absent() already establishes extraction_status is ASSUMED or ABSENT, but
            # that guarantee lives behind a method call ty cannot see through -- narrow it locally.
            status = instruction.extraction_status
            status_repr = status.value if status is not None else "None"
            observation = Observation(
                subject=instruction.id,
                expected="a SourceSpan whose quote verifies, or a recorded absence",
                observed=f"extraction_status={status_repr!r}, absence_note={instruction.absence_note!r}",
            )
            return (
                Finding.from_observation(
                    Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE,
                    ContractBasis.UNSPECIFIED,
                    (
                        "ARCHITECTURE.md, 'The decomposition-exit gate' Tier 2: an assertion marked ASSUMED or ABSENT with the gap "
                        "stated 'does not falsify the predicate ... reported at CONTRACT_UNSPECIFIED and "
                        f"does not block'. Instruction {instruction.text!r} records exactly this."
                    ),
                    observation,
                    (CONTRACT_SPAN,),
                    (instruction.id,),
                ),
            )
        observation = Observation(
            subject=instruction.id,
            expected="a SourceSpan whose quote is found verbatim in the text at its ref",
            observed=self.no_evidence_observed(instruction),
        )
        return (
            Finding.from_observation(
                Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE,
                ContractBasis.DECLARED,
                (
                    "ARCHITECTURE.md, 'The decomposition-exit gate' Tier 2: 'An instruction stating how a system behaves carries a "
                    "SourceSpan whose quote is found verbatim in the text at its ref. Citing is not enough; "
                    f"the quote must be there.' Instruction {instruction.text!r} carries neither."
                ),
                observation,
                (CONTRACT_SPAN,),
                (instruction.id,),
            ),
        )

    def quote_verifies(self, ref: str, quote: str) -> bool:
        """Return whether ``quote`` appears verbatim (whitespace-normalized) in the text at ``ref``.

        Args:
            ref: The source span's ref.
            quote: The quote to look for.

        Returns:
            True when the ref resolves and the normalized quote is contained in the normalized text.
        """
        text = self._reader.read(ref)
        return text is not None and normalize(quote) in normalize(text)

    def no_evidence_observed(self, instruction: Instruction) -> str:
        """Describe, for reporting, why an ``ASSERTING`` instruction carries no evidence.

        Args:
            instruction: The instruction that failed Tier 2 with no recorded absence.

        Returns:
            A human-readable description of which of the three no-evidence shapes applies.
        """
        if not instruction.source_refs:
            return "no SourceSpan at all, and no recorded absence"
        unresolved = [span.ref for span in instruction.source_refs if self._reader.read(span.ref) is None]
        if unresolved:
            return f"ref(s) {unresolved!r} do not exist"
        return "the quoted span(s) do not appear verbatim in the text at their ref"
