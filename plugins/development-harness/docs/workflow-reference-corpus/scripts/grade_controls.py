"""Deterministically grade isolated #4102 control candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NoReturn

JsonObject = dict[str, object]


def fail(message: str) -> NoReturn:
    """Raise a contextual validation error."""
    raise ValueError(message)


def read_object(path: Path) -> JsonObject:
    """Read a JSON object from a UTF-8 file.

    Returns:
        Parsed JSON object.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def object_value(value: object, name: str) -> JsonObject:
    """Return a required JSON object value.

    Returns:
        Validated JSON object.
    """
    if not isinstance(value, dict):
        fail(f"{name} must be a JSON object")
    return value


def string_value(value: object, name: str) -> str:
    """Return a required non-empty string value.

    Returns:
        Validated string.
    """
    if not isinstance(value, str) or not value:
        fail(f"{name} must be a non-empty string")
    return value


def bool_value(value: object, name: str) -> bool:
    """Return a required boolean value.

    Returns:
        Validated boolean.
    """
    if not isinstance(value, bool):
        fail(f"{name} must be a boolean")
    return value


def integer_value(value: object, name: str) -> int:
    """Return a required integer value without accepting booleans.

    Returns:
        Validated integer.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        fail(f"{name} must be an integer")
    return value


def string_list_value(value: object, name: str) -> list[str]:
    """Return a required list of non-empty strings.

    Returns:
        Validated string values.
    """
    if not isinstance(value, list):
        fail(f"{name} must be a JSON array")
    return [string_value(item, f"{name} item") for item in value]


def case_revisions(manifest: JsonObject) -> dict[str, str]:
    """Map each declared case to its immutable source revision.

    Returns:
        Case ID to source revision mapping.
    """
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        fail("corpus manifest cases must be a JSON array")

    revisions: dict[str, str] = {}
    for case in cases:
        case_object = object_value(case, "corpus manifest case")
        case_id = string_value(case_object.get("id"), "corpus manifest case id")
        revisions[case_id] = string_value(case_object.get("source_revision"), f"source revision for {case_id}")
    return revisions


def evaluate_candidate(candidate: JsonObject, revisions: dict[str, str]) -> tuple[str, str]:
    """Classify a candidate using only its values and pinned case metadata.

    Returns:
        Verdict and reason tuple.
    """
    case_id = string_value(candidate.get("case_id"), "candidate case_id")
    expected_revision = revisions.get(case_id)
    source_revision = string_value(candidate.get("source_revision"), "candidate source_revision")
    profile_spawned_child = bool_value(candidate.get("profile_spawned_child"), "candidate profile_spawned_child")
    nested_return_count = integer_value(
        candidate.get("nested_reference_return_count"), "candidate nested_reference_return_count"
    )
    relation_ids = string_list_value(candidate.get("same_span_relation_ids"), "candidate same_span_relation_ids")
    expected_relation_count = integer_value(
        candidate.get("expected_distinct_same_span_relations"), "candidate expected_distinct_same_span_relations"
    )
    activity_stamping_consumer = string_value(
        candidate.get("activity_stamping_specific_consumer"), "candidate activity_stamping_specific_consumer"
    )
    failures = [
        (expected_revision is None, "unknown_case"),
        (source_revision != expected_revision, "source_revision_mismatch"),
        (profile_spawned_child, "loaded_profile_is_not_spawned_child"),
        (nested_return_count < 1, "nested_return_missing"),
        (len(set(relation_ids)) < expected_relation_count, "same_span_relations_collapsed"),
        (activity_stamping_consumer != "unobserved", "activity_stamping_consumer_overclaim"),
    ]
    for failed, reason in failures:
        if failed:
            return "fail", reason
    return "pass", "all_required_source_boundaries_hold"


def grade_controls(manifest: JsonObject, controls: JsonObject, candidates: JsonObject) -> list[JsonObject]:
    """Grade every candidate and compare it to the grader-only expectation.

    Returns:
        One result object per declared control.
    """
    revisions = case_revisions(manifest)
    control_specs = controls.get("controls")
    candidate_specs = candidates.get("controls")
    if not isinstance(control_specs, list) or not isinstance(candidate_specs, list):
        fail("control specifications and candidates must be JSON arrays")

    candidates_by_id: dict[str, JsonObject] = {}
    for candidate_spec in candidate_specs:
        candidate_object = object_value(candidate_spec, "control candidate")
        candidates_by_id[string_value(candidate_object.get("id"), "control candidate id")] = candidate_object

    results: list[JsonObject] = []
    for control_spec in control_specs:
        control_object = object_value(control_spec, "control specification")
        control_id = string_value(control_object.get("id"), "control id")
        candidate_spec = candidates_by_id.get(control_id)
        if candidate_spec is None:
            fail(f"missing candidate for control {control_id}")
        expected = object_value(candidate_spec.get("expected"), f"expected result for {control_id}")
        candidate = object_value(candidate_spec.get("candidate"), f"candidate for {control_id}")
        verdict, reason = evaluate_candidate(candidate, revisions)
        expected_verdict = string_value(expected.get("verdict"), f"expected verdict for {control_id}")
        expected_reason = string_value(expected.get("reason"), f"expected reason for {control_id}")
        results.append({
            "control_id": control_id,
            "verdict": verdict,
            "reason": reason,
            "expected_verdict": expected_verdict,
            "expected_reason": expected_reason,
            "matches_expected": verdict == expected_verdict and reason == expected_reason,
        })
    return results


def self_check() -> None:
    """Exercise the correct baseline and every rejection reason."""
    revisions = {"case": "revision"}
    baseline: JsonObject = {
        "case_id": "case",
        "source_revision": "revision",
        "profile_spawned_child": False,
        "nested_reference_return_count": 1,
        "same_span_relation_ids": ["first", "second"],
        "expected_distinct_same_span_relations": 2,
        "activity_stamping_specific_consumer": "unobserved",
    }
    if evaluate_candidate(baseline, revisions) != ("pass", "all_required_source_boundaries_hold"):
        fail("self-check baseline did not pass")
    checks = {
        "source_revision": ({**baseline, "source_revision": "wrong"}, "source_revision_mismatch"),
        "profile": ({**baseline, "profile_spawned_child": True}, "loaded_profile_is_not_spawned_child"),
        "nested": ({**baseline, "nested_reference_return_count": 0}, "nested_return_missing"),
        "same_span": ({**baseline, "same_span_relation_ids": ["first", "first"]}, "same_span_relations_collapsed"),
        "stamping": (
            {**baseline, "activity_stamping_specific_consumer": "absent"},
            "activity_stamping_consumer_overclaim",
        ),
    }
    for candidate, expected_reason in checks.values():
        if evaluate_candidate(candidate, revisions) != ("fail", expected_reason):
            fail(f"self-check did not reject {expected_reason}")


def parse_arguments() -> argparse.Namespace:
    """Parse the grader's JSON input and output locations.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-manifest", type=Path)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run a self-check or emit a deterministic control-grade record."""
    arguments = parse_arguments()
    if arguments.self_check:
        self_check()
        print(json.dumps({"status": "self-check-passed"}, separators=(",", ":")))
        return
    required_paths = [arguments.corpus_manifest, arguments.controls, arguments.candidates, arguments.output]
    if any(path is None for path in required_paths):
        fail("--corpus-manifest, --controls, --candidates, and --output are required")

    results = grade_controls(
        read_object(arguments.corpus_manifest), read_object(arguments.controls), read_object(arguments.candidates)
    )
    result: JsonObject = {
        "schema_version": 1,
        "status": "deterministic-control-grade",
        "grader": "workflow-reference-corpus/scripts/grade_controls.py",
        "control_results": results,
        "all_expected_results_match": all(
            bool_value(item["matches_expected"], "control matches_expected") for item in results
        ),
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
