"""Pure-Python process models for Kaizen tool-call sequences."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict

Transition: TypeAlias = tuple[str, str]
ToolSequences: TypeAlias = Mapping[str, Sequence[str]]


class ConformanceDiagnostics(BaseModel):
    """Per-session conformance metrics for a target trace.

    ``uncovered_model_transitions`` is model-edge coverage, not token-replay
    residue: it counts every reference-model transition this trace didn't
    exercise, including transitions that belong to a different valid branch
    the trace was never expected to take. A fully conforming trace through
    one branch of a multi-path reference model can still have a nonzero
    count here.
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


def build_process_model(sequences: ToolSequences) -> ProcessModel:
    """Build a transition model from session tool-call sequences.

    Returns:
        Process model with activity, transition, start, and end counts.
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

    return ProcessModel(
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
    unexpected_transition_count = sum(
        1 for transition in observed_transitions if transition not in model.transition_set
    )
    start_mismatch = bool(tools) and tools[0] not in model.start_set
    end_mismatch = bool(tools) and tools[-1] not in model.end_set
    empty_trace_mismatch = not tools and model.event_count > 0

    missing_tokens = unexpected_transition_count + int(start_mismatch) + int(end_mismatch) + int(empty_trace_mismatch)
    produced_tokens = len(tools)
    consumed_tokens = max(0, produced_tokens - missing_tokens)
    uncovered_model_transitions = len(frozenset(model.transition_set) - frozenset(observed_transitions))

    return ConformanceDiagnostics(
        session_id=session_id,
        trace_is_fit=missing_tokens == 0,
        trace_fitness=_trace_fitness(missing_tokens, observed_transitions, tools),
        missing_tokens=missing_tokens,
        uncovered_model_transitions=uncovered_model_transitions,
        consumed_tokens=consumed_tokens,
        produced_tokens=produced_tokens,
    )


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
