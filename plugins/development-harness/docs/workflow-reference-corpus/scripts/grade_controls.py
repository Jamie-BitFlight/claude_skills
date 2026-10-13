# /// script
# requires-python = ">=3.11"
# ///
# ruff: file-ignore[complex-structure, too-many-branches]
"""Replay and grade complete source-only workflow traces deterministically."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = (
    "relations",
    "terminals",
    "actors",
    "artifacts_consumers",
    "uncertainty_contradictions",
    "consumer_change",
)


def load(path: Path) -> dict[str, Any]:
    """Read one required JSON object.

    Returns:
        Parsed JSON object.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def canonical(value: object) -> str:
    """Encode a stable JSON comparison signature.

    Returns:
        Canonical JSON text.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def index_cases(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a trace's cases by immutable case identifier.

    Returns:
        Cases keyed by id.
    """
    return {case["id"]: case for case in trace["cases"]}


def duplicate_ids(items: list[dict[str, Any]]) -> list[str]:
    """Return repeated identifiers without silently overwriting an entry.

    Returns:
        Duplicate identifiers in encounter order.
    """
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if item_id in seen:
            duplicates.append(item_id)
        seen.add(item_id)
    return duplicates


def structural_failures(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, list[str]]:
    """Validate exact complete-trace coverage before dimension scoring.

    Returns:
        Failures keyed by declared case id, or `__corpus__` for global failures.
    """
    failures: dict[str, list[str]] = {}
    candidate_cases = candidate.get("cases")
    if not isinstance(candidate_cases, list) or not all(isinstance(case, dict) for case in candidate_cases):
        return {"__corpus__": ["candidate_cases_not_list"]}
    reference_cases = reference["cases"]
    reference_ids = {case["id"] for case in reference_cases}
    candidate_ids = [case.get("id") for case in candidate_cases]
    for case_id in duplicate_ids(candidate_cases):
        failures.setdefault(case_id, []).append("duplicate_case_id")
    candidate_id_set = {case_id for case_id in candidate_ids if isinstance(case_id, str)}
    for case_id in sorted(reference_ids - candidate_id_set):
        failures.setdefault(case_id, []).append("missing_case")
    for case_id in sorted(candidate_id_set - reference_ids):
        failures.setdefault("__corpus__", []).append(f"extra_case:{case_id}")
    reference_by_id = index_cases(reference)
    for candidate_case in candidate_cases:
        case_id = candidate_case.get("id")
        if not isinstance(case_id, str) or case_id not in reference_by_id:
            continue
        reference_case = reference_by_id[case_id]
        case_failures = failures.setdefault(case_id, [])
        required = (
            "source_revision",
            "raw_record_inventory",
            "relations",
            "rejected_relations",
            "rejected_annotations",
            "unknowns",
            "contradictions",
        )
        for field in required:
            if field not in candidate_case:
                case_failures.append(f"missing_field:{field}")
        if candidate_case.get("raw_record_inventory") != reference_case["raw_record_inventory"]:
            case_failures.append("raw_record_inventory_mismatch")
        for collection in ("relations", "rejected_relations", "rejected_annotations", "unknowns", "contradictions"):
            items = candidate_case.get(collection)
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                case_failures.append(f"invalid_collection:{collection}")
                continue
            for duplicate_id in duplicate_ids(items):
                case_failures.append(f"duplicate_{collection}_id:{duplicate_id}")
        if candidate_case.get("rejected_relations") != reference_case.get("rejected_relations"):
            case_failures.append("rejected_relations_mismatch")
        if candidate_case.get("rejected_annotations") != reference_case.get("rejected_annotations"):
            case_failures.append("rejected_annotations_mismatch")
        unknown_ids = {
            item["id"]
            for item in candidate_case.get("unknowns", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        contradiction_ids = {
            item["id"]
            for item in candidate_case.get("contradictions", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for relation in candidate_case.get("relations", []):
            if not isinstance(relation, dict):
                continue
            if not relation.get("source_spans"):
                case_failures.append(f"relation_missing_replayable_source_span:{relation.get('id')}")
            for field, valid_ids in (("unknown_ids", unknown_ids), ("contradiction_ids", contradiction_ids)):
                links = relation.get(field)
                if not isinstance(links, list) or not all(isinstance(link, str) for link in links):
                    case_failures.append(f"invalid_{field}:{relation.get('id')}")
                    continue
                for link in links:
                    if link not in valid_ids:
                        case_failures.append(f"invalid_{field}_link:{relation.get('id')}:{link}")
        for collection in ("unknowns", "contradictions"):
            for item in candidate_case.get(collection, []):
                if isinstance(item, dict) and not item.get("source_spans"):
                    case_failures.append(f"{collection}_missing_replayable_source_span:{item.get('id')}")
        if not case_failures:
            failures.pop(case_id, None)
    return failures


def relation_index(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a case's relations by immutable relation identifier.

    Returns:
        Relations keyed by id.
    """
    return {relation["id"]: relation for relation in case["relations"]}


def apply_mutation(trace: dict[str, Any], mutation: dict[str, Any]) -> None:
    """Apply one explicit grader-only complete-trace mutation."""
    case = index_cases(trace)[mutation["case_id"]]
    operation = mutation["op"]
    if operation == "set_case_revision":
        case["source_revision"] = mutation["value"]
        return
    if operation == "set_case_field":
        case[mutation["field"]] = mutation["value"]
        return
    if operation == "append_duplicate_case":
        trace["cases"].append(copy.deepcopy(case))
        return
    if operation == "append_false_relation":
        relation = {key: value for key, value in mutation.items() if key not in {"op", "case_id"}}
        relation.setdefault("source_records", [])
        relation.setdefault("continuations", None)
        relation.setdefault("adjudication", "refuted")
        relation.setdefault("source_relation", {})
        case["relations"].append(relation)
        return
    if operation == "remove_annotation":
        case[mutation["collection"]] = [item for item in case[mutation["collection"]] if item["id"] != mutation["id"]]
        return
    if operation == "append_annotation":
        case[mutation["collection"]].append({
            key: value for key, value in mutation.items() if key not in {"op", "case_id", "collection"}
        })
        return
    relation = relation_index(case)[mutation["relation_id"]]
    if operation == "remove_relation":
        case["relations"] = [item for item in case["relations"] if item["id"] != relation["id"]]
    elif operation == "set_relation_field":
        relation[mutation["field"]] = mutation["value"]
    elif operation == "set_consumer_status":
        if not relation["consumers"]:
            raise ValueError("consumer mutation target has no consumer")
        relation["consumers"][0]["comparison_status"] = mutation["value"]
    elif operation == "remove_source_spans":
        relation["source_spans"] = []
        relation["evidence_span_ids"] = []
    elif operation == "corrupt_source_quote":
        relation["source_spans"][0]["quote"] = mutation["value"]
    elif operation == "append_duplicate_relation":
        case["relations"].append(copy.deepcopy(relation))
    else:
        raise ValueError(f"unknown mutation operation: {operation}")


def hydrate(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Produce a complete candidate trace from reference and mutations.

    Returns:
        Hydrated complete candidate trace.
    """
    if candidate.get("base_reference") != "../trace-reference.json":
        raise ValueError("complete-trace control candidates must declare the frozen reference base")
    trace = copy.deepcopy(reference)
    for mutation in candidate.get("mutations", []):
        apply_mutation(trace, mutation)
    return trace


def source_bytes(revision: str, path: str, cache: dict[tuple[str, str], bytes]) -> bytes:
    """Load and cache one revision-bound Git source blob.

    Returns:
        Source bytes at the declared revision.
    """
    key = (revision, path)
    if key not in cache:
        git = shutil.which("git")
        if git is None:
            raise ValueError("git executable unavailable")
        result = subprocess.run([git, "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True, check=False)
        if result.returncode:
            raise ValueError(result.stderr.decode(errors="replace").strip())
        cache[key] = result.stdout
    return cache[key]


def replay_case(case: dict[str, Any]) -> list[dict[str, str]]:
    """Validate every required source span in a candidate case.

    Returns:
        Source replay failures.
    """
    failures: list[dict[str, str]] = []
    cache: dict[tuple[str, str], bytes] = {}
    trace_items = [*case["relations"], *case.get("unknowns", []), *case.get("contradictions", [])]
    for item in trace_items:
        spans = item.get("source_spans")
        if not isinstance(spans, list) or not spans:
            failures.append({"id": str(item.get("id")), "reason": "missing_replayable_source_span"})
            continue
        for span in spans:
            if not isinstance(span, dict):
                failures.append({"id": str(item.get("id")), "reason": "invalid_source_span"})
                continue
            path = span.get("repository_path")
            if not isinstance(path, str) or not isinstance(span.get("quote"), str):
                failures.append({"id": str(span.get("id", item.get("id"))), "reason": "incomplete_source_span"})
                continue
            try:
                content = source_bytes(case["source_revision"], path, cache)
            except ValueError as error:
                failures.append({"id": span["id"], "reason": f"source_unavailable:{error}"})
                continue
            if span.get("source_sha256") and hashlib.sha256(content).hexdigest() != span["source_sha256"]:
                failures.append({"id": span["id"], "reason": "source_sha256_mismatch"})
                continue
            start, end = span.get("byte_start"), span.get("byte_end_exclusive")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or content[start:end].decode(errors="replace") != span["quote"]
            ):
                failures.append({"id": span["id"], "reason": "quoted_byte_span_mismatch"})
    return failures


def dimension_items(case: dict[str, Any], dimension: str) -> dict[str, str]:
    """Return stable identifiers and signatures for one dimension.

    Returns:
        Item signatures keyed by stable identifier.
    """
    values: dict[str, str] = {}
    for relation in case["relations"]:
        relation_id = relation["id"]
        if dimension == "relations":
            values[relation_id] = canonical({
                "id": relation_id,
                "actor": relation.get("actor"),
                "condition": relation.get("condition"),
                "action": relation.get("action"),
                "effect": relation.get("effect"),
                "continuations": relation.get("continuations"),
                "terminal": relation.get("terminal"),
                "unknown_ids": relation.get("unknown_ids", []),
                "contradiction_ids": relation.get("contradiction_ids", []),
                "source_spans": relation.get("source_spans", []),
            })
        elif dimension == "terminals" and relation.get("terminal") is not None:
            values[relation_id] = canonical(relation["terminal"])
        elif dimension == "actors" and relation.get("actor") is not None:
            values[relation_id] = canonical(relation["actor"])
        elif dimension == "artifacts_consumers" and (relation.get("artifacts") or relation.get("consumers")):
            values[relation_id] = canonical({
                "artifacts": relation.get("artifacts", []),
                "consumers": relation.get("consumers", []),
            })
        elif dimension == "consumer_change":
            for index, consumer in enumerate(relation.get("consumers", [])):
                values[f"{relation_id}/consumer-{index}"] = canonical({
                    "name": consumer.get("name"),
                    "comparison_status": consumer.get("comparison_status"),
                })
    if dimension == "uncertainty_contradictions":
        for collection in ("unknowns", "contradictions"):
            for item in case.get(collection, []):
                values[item["id"]] = canonical(item)
        for relation in case["relations"]:
            if relation.get("unknown_ids") or relation.get("contradiction_ids"):
                values[f"{relation['id']}/annotation-links"] = canonical({
                    "unknown_ids": relation.get("unknown_ids", []),
                    "contradiction_ids": relation.get("contradiction_ids", []),
                })
    return values


def score(reference_case: dict[str, Any], candidate_case: dict[str, Any], dimension: str) -> dict[str, Any]:
    """Compare one candidate case against one frozen case dimension.

    Returns:
        Correct, missed, and false identifiers.
    """
    reference = dimension_items(reference_case, dimension)
    candidate = dimension_items(candidate_case, dimension)
    correct = sorted(key for key in reference if key in candidate and reference[key] == candidate[key])
    missed = sorted(key for key in reference if key not in candidate or reference[key] != candidate[key])
    false = [key for key in candidate if key not in reference or reference.get(key) != candidate[key]]
    if dimension == "relations":
        false.extend(
            f"{relation_id}#duplicate-{index}"
            for index, relation_id in enumerate(duplicate_ids(candidate_case["relations"]), start=1)
        )
    false.sort()
    return {"dimension": dimension, "correct": correct, "missed": missed, "false": false}


def grade(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Grade all complete-trace dimensions and source replays.

    Returns:
        Per-case grading outcome.
    """
    failures = structural_failures(reference, candidate)
    candidates = index_cases(candidate) if isinstance(candidate.get("cases"), list) else {}
    results: list[dict[str, Any]] = []
    for reference_case in reference["cases"]:
        candidate_case = candidates.get(reference_case["id"])
        if candidate_case is None:
            results.extend(
                {
                    "case_id": reference_case["id"],
                    "dimension": dimension,
                    "correct": [],
                    "missed": sorted(dimension_items(reference_case, dimension)),
                    "false": [],
                    "source_replay_failures": [{"id": reference_case["id"], "reason": "candidate_case_missing"}],
                    "verdict": "fail",
                }
                for dimension in DIMENSIONS
            )
            continue
        replay_failures = replay_case(candidate_case)
        structural = [*failures.get("__corpus__", []), *failures.get(reference_case["id"], [])]
        replay_failures.extend({"id": reference_case["id"], "reason": failure} for failure in structural)
        if candidate_case["source_revision"] != reference_case["source_revision"]:
            replay_failures.append({"id": reference_case["id"], "reason": "source_revision_mismatch"})
        for dimension in DIMENSIONS:
            row = {"case_id": reference_case["id"], **score(reference_case, candidate_case, dimension)}
            row["source_replay_failures"] = replay_failures
            row["verdict"] = "pass" if not row["missed"] and not row["false"] and not replay_failures else "fail"
            results.append(row)
    return {
        "schema_version": 1,
        "acceptance_threshold": "every case and every dimension has zero missed, zero false, and zero source replay failures",
        "results": results,
        "verdict": "pass" if all(row["verdict"] == "pass" for row in results) else "fail",
    }


def parse_args() -> argparse.Namespace:
    """Parse standalone grader arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=ROOT / "trace-reference.json")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--candidates", type=Path, default=ROOT / "controls/control-candidates.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run a complete candidate grade or the control self-check."""
    arguments = parse_args()
    reference = load(arguments.reference)
    if arguments.candidate:
        output = grade(reference, load(arguments.candidate))
        encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
        if arguments.output:
            arguments.output.write_text(encoded)
        print(encoded, end="")
        return
    controls = load(arguments.candidates)
    control_results: list[dict[str, Any]] = []
    for control in controls["controls"]:
        result = grade(reference, hydrate(reference, control["candidate"]))
        if result["verdict"] != control["expected"]["verdict"]:
            raise SystemExit(f"{control['id']}: expected {control['expected']['verdict']}, got {result['verdict']}")
        control_results.append({"id": control["id"], "verdict": result["verdict"], "grade": result})
    output = {"status": "self-check-passed", "control_results": control_results}
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
