"""Pure-Python process models for Kaizen tool-call sequences."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import NamedTuple, TypeAlias

from pydantic import BaseModel, ConfigDict, PrivateAttr

Transition: TypeAlias = tuple[str, str]
ToolSequences: TypeAlias = Mapping[str, Sequence[str]]


@dataclass
class _TrieNode:
    """Reference-path trie node -- internal only, never MCP output.

    Tracks connected reference paths (one root-to-leaf path per reference
    session) rather than independent per-transition/start/end sets, so
    conformance checking can't treat a "spliced" trace -- one that combines
    a valid transition from one reference branch with a valid endpoint from
    an unrelated branch -- as fully conforming just because each fragment
    is independently valid somewhere in the aggregate model.
    """

    children: dict[str, _TrieNode] = field(default_factory=dict)
    is_end: bool = False


def _build_reference_trie(sequences: ToolSequences) -> _TrieNode:
    root = _TrieNode()
    for tools in sequences.values():
        if not tools:
            continue
        node = root
        for tool in tools:
            node = node.children.setdefault(tool, _TrieNode())
        node.is_end = True
    return root


class ConformanceDiagnostics(BaseModel):
    """Per-session conformance metrics for a target trace.

    ``missing_tokens`` is path-aware: it walks the trace against the actual
    connected reference sessions (a trie), not independent transition/start/
    end sets, so a trace that combines a transition from one reference
    branch with an endpoint from an unrelated branch is correctly flagged
    -- it can't pass just because each fragment happens to be valid
    somewhere in the aggregate model.

    ``uncovered_model_transitions`` is a separate, looser metric -- model-
    edge coverage, not token-replay residue: it counts every reference-model
    transition this trace didn't exercise, including transitions that
    belong to a different valid branch the trace was never expected to
    take. A fully conforming trace through one branch of a multi-path
    reference model can still have a nonzero count here.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str
    trace_is_fit: bool
    trace_fitness: float
    missing_tokens: int
    uncovered_model_transitions: int
    consumed_tokens: int
    produced_tokens: int


class ActivityCount(BaseModel):
    """Observed count for one tool activity."""

    model_config = ConfigDict(frozen=True)

    name: str
    count: int


class TransitionCount(BaseModel):
    """Observed count for one source-to-target tool transition."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    count: int


class ProcessModel(BaseModel):
    """Activity, transition, start, and end sets mined from tool traces."""

    model_config = ConfigDict(frozen=True)

    session_count: int
    event_count: int
    activity_counts: tuple[ActivityCount, ...]
    transition_counts: tuple[TransitionCount, ...]
    start_counts: tuple[ActivityCount, ...]
    end_counts: tuple[ActivityCount, ...]
    activity_set: frozenset[str]
    # Ordered tuple, not frozenset[Transition]: a frozenset of 2-item tuples
    # round-trips through FastMCP's JSON structured-output validation as a
    # list of lists, and Pydantic's generic schema-derived reconstruction on
    # the client side fails with "Set items should be hashable" (lists are
    # not hashable) before any tuple coercion runs. Plain strings (str-only
    # frozensets below) don't have this problem -- only tuple-of-str does.
    transition_set: tuple[Transition, ...]
    start_set: frozenset[str]
    end_set: frozenset[str]

    # Internal only -- private attrs are never part of the public schema or
    # model_dump()/JSON output, so this never reaches MCP callers. Always
    # set by build_process_model(); walk_trace() raises if a
    # ProcessModel reaches it without one (e.g. constructed directly by a
    # caller that bypassed build_process_model()).
    _reference_trie: _TrieNode | None = PrivateAttr(default=None)

    def walk_trace(self, tools: Sequence[str]) -> _TrieWalkResult:
        """Walk tools against the reference path, path-aware.

        Walks tools against the connected reference sessions (a trie), not
        independent transition/start/end sets -- see _walk_reference_trie.

        Returns:
            missing_tokens (for fitness/is_fit) and unmatched_positions (for
            consumed_tokens -- see _walk_reference_trie for why these differ).

        Raises:
            ValueError: If this model wasn't built via build_process_model().
        """
        if self._reference_trie is None:
            msg = "ProcessModel.reference_trie is unset; build the model via build_process_model()"
            raise ValueError(msg)
        return _walk_reference_trie(self._reference_trie, tools)

    @classmethod
    def from_sequences(cls, sequences: ToolSequences) -> ProcessModel:
        """Build a ProcessModel, including its internal reference trie.

        Returns:
            Process model with activity, transition, start, end counts, and
            the reference trie walk_trace() needs.
        """
        activity_counter: Counter[str] = Counter()
        transition_counter: Counter[Transition] = Counter()
        start_counter: Counter[str] = Counter()
        end_counter: Counter[str] = Counter()

        for tools in sequences.values():
            if not tools:
                continue
            activity_counter.update(tools)
            transition_counter.update(_transitions(tools))
            start_counter[tools[0]] += 1
            end_counter[tools[-1]] += 1

        model = cls(
            session_count=len(sequences),
            event_count=sum(activity_counter.values()),
            activity_counts=_activity_counts(activity_counter),
            transition_counts=_transition_counts(transition_counter),
            start_counts=_activity_counts(start_counter),
            end_counts=_activity_counts(end_counter),
            activity_set=frozenset(activity_counter),
            transition_set=tuple(sorted(transition_counter)),
            start_set=frozenset(start_counter),
            end_set=frozenset(end_counter),
        )
        model._reference_trie = _build_reference_trie(sequences)
        return model


def build_process_model(sequences: ToolSequences) -> ProcessModel:
    """Build a transition model from session tool-call sequences.

    Returns:
        Process model with activity, transition, start, and end counts.
    """
    return ProcessModel.from_sequences(sequences)


def check_sequence_conformance(
    target_sequences: ToolSequences, reference_model: ProcessModel
) -> list[ConformanceDiagnostics]:
    """Compare target sequences against a reference process model.

    Returns:
        Per-session conformance diagnostics.
    """
    return [_diagnose_sequence(session_id, tools, reference_model) for session_id, tools in target_sequences.items()]


def _diagnose_sequence(session_id: str, tools: Sequence[str], model: ProcessModel) -> ConformanceDiagnostics:
    observed_transitions = _transitions(tools)
    uncovered_model_transitions = len(frozenset(model.transition_set) - frozenset(observed_transitions))

    if not tools:
        missing_tokens = 1 if model.event_count > 0 else 0
        return ConformanceDiagnostics(
            session_id=session_id,
            trace_is_fit=missing_tokens == 0,
            trace_fitness=_trace_fitness(missing_tokens, observed_transitions, tools),
            missing_tokens=missing_tokens,
            uncovered_model_transitions=uncovered_model_transitions,
            consumed_tokens=0,
            produced_tokens=0,
        )

    walk = model.walk_trace(tools)
    missing_tokens = walk.missing_tokens
    produced_tokens = len(tools)
    # Subtract only positions that actually broke the path, not the extra
    # endpoint-mismatch penalty folded into missing_tokens -- a trace that is
    # a valid prefix of a longer reference path (e.g. A->B against A->B->C)
    # matched every token it produced even though it never reached is_end.
    consumed_tokens = max(0, produced_tokens - walk.unmatched_positions)

    return ConformanceDiagnostics(
        session_id=session_id,
        trace_is_fit=missing_tokens == 0,
        trace_fitness=_trace_fitness(missing_tokens, observed_transitions, tools),
        missing_tokens=missing_tokens,
        uncovered_model_transitions=uncovered_model_transitions,
        consumed_tokens=consumed_tokens,
        produced_tokens=produced_tokens,
    )


class _TrieWalkResult(NamedTuple):
    """Result of walking a trace against the reference trie.

    ``missing_tokens`` and ``unmatched_positions`` differ by exactly the
    endpoint-mismatch penalty: a trace that is a valid *prefix* of a longer
    reference path (target A->B against reference A->B->C) never breaks the
    path, so unmatched_positions is 0, but it also never reaches a genuine
    reference-session ending, so missing_tokens is 1. Use missing_tokens for
    trace_is_fit/trace_fitness (an incomplete trace should score below a
    complete one); use unmatched_positions for consumed_tokens (every token
    the trace produced was still validly on-path, so none of them should be
    subtracted out just because the walk stopped short of an ending).
    """

    missing_tokens: int
    unmatched_positions: int


def _walk_reference_trie(root: _TrieNode, tools: Sequence[str]) -> _TrieWalkResult:
    """Walk tools against the reference trie, counting steps that break the path.

    Each position is only a match if the *entire path so far* also matched
    a reference session, not just the individual activity in isolation --
    this is what stops "A" (a valid start elsewhere) followed by "B" (a
    valid next-step elsewhere) from passing when no single reference
    session actually contains that A->B path. Once a step fails to match,
    every subsequent step also counts as missing: there is no principled
    way to guess which reference branch, if any, the trace meant to
    rejoin, so re-syncing would just be a different kind of guess.

    Returns:
        missing_tokens: unmatched_positions, plus one more if the walk
            stayed on-path throughout but ended at a position that isn't a
            genuine reference-session ending.
        unmatched_positions: count of positions that failed to match the
            reference trie (excludes the endpoint-mismatch penalty).
    """
    node = root
    on_path = True
    unmatched_positions = 0
    for tool in tools:
        if on_path and tool in node.children:
            node = node.children[tool]
        else:
            unmatched_positions += 1
            on_path = False
    missing_tokens = unmatched_positions
    if on_path and not node.is_end:
        missing_tokens += 1
    return _TrieWalkResult(missing_tokens=missing_tokens, unmatched_positions=unmatched_positions)


def _trace_fitness(missing_tokens: int, observed_transitions: Sequence[Transition], tools: Sequence[str]) -> float:
    """Fitness as a fraction of the checks missing_tokens actually draws from.

    A non-empty trace is scored on len(observed_transitions) transition
    checks plus one start check and one end check -- matching exactly what
    missing_tokens counts, so a trace that only fails a start/end check
    (with every transition correct) doesn't get an artificially low score
    from a denominator that counted transitions alone. An empty trace has
    exactly one check (empty_trace_mismatch).

    Returns:
        Fitness in [0.0, 1.0]: the fraction of checks that passed.
    """
    checks = len(observed_transitions) + 2 if tools else 1
    return round(max(0.0, 1.0 - (missing_tokens / checks)), 6)


def _transitions(tools: Sequence[str]) -> list[Transition]:
    return [(tools[index], tools[index + 1]) for index in range(len(tools) - 1)]


def _activity_counts(counter: Counter[str]) -> tuple[ActivityCount, ...]:
    return tuple(
        ActivityCount(name=name, count=count)
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    )


def _transition_counts(counter: Counter[Transition]) -> tuple[TransitionCount, ...]:
    return tuple(
        TransitionCount(source=source, target=target, count=count)
        for (source, target), count in sorted(counter.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    )


__all__ = [
    "ActivityCount",
    "ConformanceDiagnostics",
    "ProcessModel",
    "ToolSequences",
    "Transition",
    "TransitionCount",
    "build_process_model",
    "check_sequence_conformance",
]
