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


def test_check_sequence_conformance_partial_credit_for_a_late_deviation() -> None:
    """A trace that diverges only at its last step shouldn't score 0.0 just
    because the fitness denominator undercounted the total checks.

    Regression test: reference model X->A->B, target X->A->C matches the
    start and first transition exactly, failing only the final step.
    """
    reference_model = build_process_model({"reference": ["X", "A", "B"]})

    result = check_sequence_conformance({"target": ["X", "A", "C"]}, reference_model)

    diagnostics = result[0]
    assert diagnostics.trace_is_fit is False
    assert diagnostics.missing_tokens == 1
    # 1 of 4 checks fails (2 transition positions + start + end) -- not 1 of 1.
    assert diagnostics.trace_fitness == pytest.approx(0.75)


def test_check_sequence_conformance_bad_start_diverges_the_whole_trace() -> None:
    """A trace that never lands on a valid reference start can't be "mostly
    right" -- it was never on any reference path, so every position after
    it is unaccounted for too.

    This is intentionally stricter than a naive "count the failed checks
    independently" model: reference X->A->B, target A->B has a transition
    (A->B) and an end activity (B) that both occur *somewhere* in the
    reference, but starting from A means the trace was never following the
    X->A->B path in the first place.
    """
    reference_model = build_process_model({"reference": ["X", "A", "B"]})

    result = check_sequence_conformance({"target": ["A", "B"]}, reference_model)

    diagnostics = result[0]
    assert diagnostics.trace_is_fit is False
    assert diagnostics.missing_tokens == 2
    assert diagnostics.trace_fitness == pytest.approx(1 / 3)


def test_check_sequence_conformance_rejects_a_spliced_path_across_branches() -> None:
    """A trace that combines a transition from one reference branch with an
    endpoint from a different, unrelated branch must not be marked as fully
    conforming just because each fragment is independently valid somewhere
    in the aggregate reference model.

    Regression test for the path-splicing bug: reference sessions A->B->D
    and C->B->E share activity B but are otherwise disjoint branches.
    Target A->B->E combines A->B (from the first branch) with B->E (from
    the second) into a path neither reference session actually contains.
    Independent transition/start/end checks would all pass (A is a valid
    start, A->B and B->E both occur somewhere, E is a valid end) -- the
    reference trie catches it because A->B only ever leads to D, never E.
    """
    reference_model = build_process_model({"ref-1": ["A", "B", "D"], "ref-2": ["C", "B", "E"]})

    result = check_sequence_conformance({"spliced": ["A", "B", "E"]}, reference_model)

    diagnostics = result[0]
    assert diagnostics.trace_is_fit is False
    assert diagnostics.missing_tokens == 1
    assert diagnostics.trace_fitness == pytest.approx(0.75)


def test_check_sequence_conformance_prefix_trace_consumes_every_matched_token() -> None:
    """A trace that is a valid prefix of a longer reference path matched
    every token it produced -- it should not lose a consumed_tokens credit
    just because it stopped short of a genuine reference-session ending.

    Regression test: reference A->B->C, target A->B follows the reference
    path exactly for both tokens, failing only the endpoint check. Before
    the fix, consumed_tokens subtracted missing_tokens (which folds in that
    endpoint penalty) from produced_tokens, undercounting to 1 even though
    both A and B were validly on-path.
    """
    reference_model = build_process_model({"reference": ["A", "B", "C"]})

    result = check_sequence_conformance({"target": ["A", "B"]}, reference_model)

    diagnostics = result[0]
    assert diagnostics.trace_is_fit is False
    assert diagnostics.missing_tokens == 1
    assert diagnostics.produced_tokens == 2
    assert diagnostics.consumed_tokens == 2


def test_check_sequence_conformance_empty_trace_against_nonempty_reference() -> None:
    reference_model = build_process_model({"reference": ["Read", "Write"]})

    result = check_sequence_conformance({"empty": []}, reference_model)

    diagnostics = result[0]
    assert diagnostics.trace_is_fit is False
    assert diagnostics.missing_tokens == 1
    assert diagnostics.produced_tokens == 0
