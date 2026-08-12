from __future__ import annotations

import pytest
from process_model import build_process_model, check_sequence_conformance, render_process_model


def test_build_process_model_counts_events_and_transitions(sample_sequences: dict[str, list[str]]) -> None:
    model = build_process_model(sample_sequences)

    assert model.session_count == 3
    assert model.event_count == 9
    assert ("Read", "Grep") in model.transition_set
    assert "Read" in model.activity_set


def test_render_process_model_includes_transition_counts(sample_sequences: dict[str, list[str]]) -> None:
    rendered = render_process_model(build_process_model(sample_sequences))

    assert "Process model" in rendered
    assert "Read -> Grep: 2" in rendered


def test_check_sequence_conformance_flags_unseen_transition() -> None:
    reference_model = build_process_model({"reference": ["Read", "Grep", "Write"]})

    result = check_sequence_conformance(
        {"matching": ["Read", "Grep", "Write"], "drifted": ["Read", "Bash", "Write"]}, reference_model
    )

    diagnostics = {entry["session_id"]: entry for entry in result}
    assert diagnostics["matching"]["trace_is_fit"] is True
    assert diagnostics["matching"]["trace_fitness"] == pytest.approx(1.0)
    assert diagnostics["drifted"]["trace_is_fit"] is False
    assert diagnostics["drifted"]["missing_tokens"] == 2
    assert diagnostics["drifted"]["trace_fitness"] == pytest.approx(0.0)
