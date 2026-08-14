from __future__ import annotations

import pytest
from process_model import build_process_model, check_sequence_conformance


def test_build_process_model_counts_events_and_transitions(sample_sequences: dict[str, list[str]]) -> None:
    model = build_process_model(sample_sequences)

    assert model.session_count == 3
    assert model.event_count == 9
    assert ("Read", "Grep") in model.transition_set
    assert "Read" in model.activity_set


def test_build_process_model_transition_counts_are_structured(sample_sequences: dict[str, list[str]]) -> None:
    model = build_process_model(sample_sequences)

    read_grep = next(entry for entry in model.transition_counts if entry.source == "Read" and entry.target == "Grep")
    assert read_grep.count == 2


def test_check_sequence_conformance_flags_unseen_transition() -> None:
    reference_model = build_process_model({"reference": ["Read", "Grep", "Write"]})

    result = check_sequence_conformance(
        {"matching": ["Read", "Grep", "Write"], "drifted": ["Read", "Bash", "Write"]}, reference_model
    )

    diagnostics = {entry.session_id: entry for entry in result}
    assert diagnostics["matching"].trace_is_fit is True
    assert diagnostics["matching"].trace_fitness == pytest.approx(1.0)
    assert diagnostics["drifted"].trace_is_fit is False
    assert diagnostics["drifted"].missing_tokens == 2
    # 2 of 4 checks (2 transitions + start + end) fail: both transitions are
    # wrong, but start/end still match -- see the denominator fix below.
    assert diagnostics["drifted"].trace_fitness == pytest.approx(0.5)


def test_check_sequence_conformance_fitness_counts_start_and_end_checks() -> None:
    """A trace with every transition correct but a start mismatch shouldn't
    score 0.0 just because the fitness denominator only counted transitions.

    Regression test: reference model X->A->B, target A->B has a perfectly
    conforming transition and end activity, failing only the start check.
    """
    reference_model = build_process_model({"reference": ["X", "A", "B"]})

    result = check_sequence_conformance({"target": ["A", "B"]}, reference_model)

    diagnostics = result[0]
    assert diagnostics.missing_tokens == 1
    # 1 of 3 checks (1 transition + start + end) fails -- not 1 of 1.
    assert diagnostics.trace_fitness == pytest.approx(2 / 3)
