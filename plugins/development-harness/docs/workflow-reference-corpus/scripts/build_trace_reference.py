#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
# ruff: file-ignore[any-type, undocumented-public-function, too-many-locals]
"""Build the tracked, source-only complete-trace reference from frozen lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import operator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_RECORDS = {
    "pinned-main-t5": (
        "e66b55e05e130ea905afaf8d650ec0f5980d08d0",
        [
            ("review-a", "cases/pinned-main-t5/records/review-a/trace-output.json"),
            ("review-b", "cases/pinned-main-t5/records/review-b/trace-output.json"),
        ],
    ),
    "pinned-4095-source-check": (
        "e0b62965e13bcbdfd0648ae810d7dbb7ed3f1947",
        [
            ("review-a", "cases/pinned-4095-source-check/records/review-a/trace-output.json"),
            ("review-b", "cases/pinned-4095-source-check/records/review-b/trace-output.json"),
        ],
    ),
    "grooming-nested-references": (
        "e66b55e05e130ea905afaf8d650ec0f5980d08d0",
        [
            ("actor-a-final", "cases/grooming-main/records/actor-a/final/trace-output.json"),
            ("actor-b-initial", "cases/grooming-main/records/actor-b/initial/trace-output.json"),
            ("actor-b-attempt-2", "cases/grooming-main/records/actor-b/attempt-2/trace-output.json"),
            ("actor-b-attempt-3", "cases/grooming-main/records/actor-b/attempt-3/trace-output.json"),
        ],
    ),
    "prose-task-profile-start-task": (
        "e66b55e05e130ea905afaf8d650ec0f5980d08d0",
        [
            ("handoff-a", "cases/prose-task-profile-start-task/records/handoff-a/trace-output.json"),
            ("handoff-b", "cases/prose-task-profile-start-task/records/handoff-b/trace-output.json"),
        ],
    ),
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def evidence_spans(value: Any, record_id: str, relation_id: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for index, evidence in enumerate(as_list(value)):
        if not isinstance(evidence, dict):
            continue
        path = evidence.get("source_path", evidence.get("path"))
        quote = evidence.get("quote")
        lines = evidence.get("lines")
        line_start = evidence.get("line_start", lines.get("start") if isinstance(lines, dict) else None)
        line_end = evidence.get("line_end", lines.get("end_inclusive") if isinstance(lines, dict) else None)
        byte_start = evidence.get("utf8_byte_start")
        byte_end = evidence.get("utf8_byte_end_exclusive")
        if byte_start is None and isinstance(evidence.get("utf8_bytes"), dict):
            byte_start = evidence["utf8_bytes"].get("start_inclusive")
            byte_end = evidence["utf8_bytes"].get("end_exclusive")
        spans.append({
            "id": f"{record_id}/{relation_id}/span-{index}",
            "repository_path": path,
            "git_blob_sha1": evidence.get("git_blob_sha1"),
            "source_sha256": evidence.get("source_sha256", evidence.get("raw_sha256")),
            "line_start": line_start,
            "line_end": line_end,
            "byte_start": byte_start,
            "byte_end_exclusive": byte_end,
            "quote": quote,
            "quote_sha256": hashlib.sha256(quote.encode()).hexdigest() if isinstance(quote, str) else None,
        })
    return spans


def normalized_consumers(raw: dict[str, Any], span_ids: list[str]) -> list[dict[str, Any]]:
    consumers = as_list(raw.get("consumer", raw.get("consumers")))
    normalized: list[dict[str, Any]] = []
    for consumer in consumers:
        if consumer is None:
            continue
        if isinstance(consumer, dict):
            normalized.append({
                "name": consumer.get("name", consumer.get("consumer", json.dumps(consumer, sort_keys=True))),
                "comparison_status": consumer.get("comparison_status", "unresolved"),
                "comparison_evidence_span_ids": span_ids,
                "source_consumer": consumer,
            })
        else:
            normalized.append({
                "name": str(consumer),
                "comparison_status": "unresolved",
                "comparison_evidence_span_ids": span_ids,
                "source_consumer": consumer,
            })
    return normalized


def relation_from_raw(case_id: str, record_id: str, raw: dict[str, Any], index: int) -> dict[str, Any]:
    source_id = str(raw.get("id", f"relation-{index}"))
    relation_id = f"{record_id}/{source_id}"
    spans = evidence_spans(raw.get("evidence"), record_id, source_id)
    span_ids = [span["id"] for span in spans]
    artifact = raw.get("artifacts", raw.get("artifact"))
    artifacts = as_list(artifact)
    return {
        "id": relation_id,
        "source_records": [record_id],
        "actor": raw.get("actor"),
        "condition": raw.get("condition"),
        "action": raw.get("action", raw.get("operation", raw.get("kind"))),
        "effect": raw.get("effect", raw.get("to")),
        "continuations": raw.get("continuations", raw.get("continuation")),
        "terminal": raw.get("terminal"),
        "artifacts": artifacts,
        "consumers": normalized_consumers(raw, span_ids),
        "unknown_ids": [],
        "contradiction_ids": [],
        "evidence_span_ids": span_ids,
        "source_spans": spans,
        "adjudication": "unresolved",
        "source_relation": raw,
    }


def bind_relation_annotations(case: dict[str, Any]) -> None:
    """Normalize relation annotation values into case-local annotation identifiers."""
    for collection, raw_key in (("unknowns", "unknown"), ("contradictions", "contradiction")):
        known = {item["id"] for item in case[collection]}
        for relation in case["relations"]:
            record_id = relation["source_records"][0]
            links: list[str] = []
            for index, value in enumerate(as_list(relation["source_relation"].get(raw_key))):
                if value is None:
                    continue
                candidate_id = f"{record_id}/{value}" if isinstance(value, str) else ""
                if candidate_id in known:
                    links.append(candidate_id)
                    continue
                annotation_id = f"{relation['id']}/{raw_key}-{index}"
                case[collection].append({
                    "id": annotation_id,
                    "source_records": [record_id],
                    "statement": value,
                    "source_spans": relation["source_spans"],
                    "source_annotation": {"kind": raw_key, "value": value},
                })
                known.add(annotation_id)
                links.append(annotation_id)
            relation[f"{raw_key}_ids"] = links


def collect_relations(case_id: str, record_id: str, trace: dict[str, Any]) -> list[dict[str, Any]]:
    raw_relations = trace.get("relationships", trace.get("steps", trace.get("records", [])))
    if not isinstance(raw_relations, list):
        return []
    return [
        relation_from_raw(case_id, record_id, relation, index)
        for index, relation in enumerate(raw_relations)
        if isinstance(relation, dict)
    ]


def collect_annotations(trace: dict[str, Any], record_id: str, key: str) -> list[dict[str, Any]]:
    annotations: list[dict[str, Any]] = []
    for index, annotation in enumerate(as_list(trace.get(key))):
        if not isinstance(annotation, dict):
            continue
        annotation_id = str(annotation.get("id", f"{key}-{index}"))
        annotations.append({
            "id": f"{record_id}/{annotation_id}",
            "source_records": [record_id],
            "statement": annotation.get("statement", annotation.get("condition", annotation)),
            "source_spans": evidence_spans(annotation.get("evidence"), record_id, annotation_id),
            "source_annotation": annotation,
        })
    return annotations


def build_reference() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case_id, (revision, records) in CASE_RECORDS.items():
        inventory: list[dict[str, Any]] = []
        relations: list[dict[str, Any]] = []
        unknowns: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        for label, trace_path in records:
            path = ROOT / trace_path
            trace = load(path)
            record_id = f"{case_id}/{label}"
            inventory.append({
                "record_id": record_id,
                "trace_path": trace_path,
                "raw_trace_sha256": sha256(path),
                "authority": "raw-source-only-lane; retained without relation-level lane selection",
            })
            relations.extend(collect_relations(case_id, record_id, trace))
            unknowns.extend(collect_annotations(trace, record_id, "unknowns"))
            contradictions.extend(collect_annotations(trace, record_id, "contradictions"))
        case = {
            "id": case_id,
            "source_revision": revision,
            "raw_record_inventory": inventory,
            "relations": relations,
            "unknowns": unknowns,
            "contradictions": contradictions,
            "reference_status": "source-only-unresolved-lane-normalization",
            "boundary": "Relations are canonical references to every retained raw lane record, not an independent verification, runtime observation, or architecture selection.",
        }
        bind_relation_annotations(case)
        cases.append(case)
    return {
        "schema_version": 1,
        "reference_status": "adjudicated-source-only-awaiting-independent-complete-trace-receipts",
        "normalization": {
            "relation_identity": "record_id plus immutable raw relation id; identical spans never merge relations",
            "consumer_status": "unresolved unless the raw lane supplies a source-supported comparison status",
            "terminal_rule": "null terminals retain the raw lane boundary and are not inferred as success or failure",
            "authority": "This file normalizes frozen source-only records for grading; it does not upgrade raw observations or claim-projection receipts to complete-trace verification.",
        },
        "cases": cases,
    }


def first_matching(reference: dict[str, Any], predicate: Any) -> tuple[str, str] | None:
    for case in reference["cases"]:
        for relation in case["relations"]:
            if predicate(relation):
                return case["id"], relation["id"]
    return None


def required_target(value: tuple[str, str] | None, name: str) -> tuple[str, str]:
    if value is None:
        raise ValueError(f"frozen records do not expose {name} for a required negative control")
    return value


def build_controls(reference: dict[str, Any]) -> dict[str, Any]:
    terminal = first_matching(reference, lambda relation: relation["terminal"] is not None)
    actor = first_matching(reference, lambda relation: relation["actor"] is not None)
    continuation = first_matching(reference, lambda relation: relation["continuations"] not in (None, [], {}))
    artifacts = first_matching(reference, lambda relation: relation["artifacts"] or relation["consumers"])
    consumer = first_matching(reference, operator.itemgetter("consumers"))
    unknown_link = first_matching(reference, operator.itemgetter("unknown_ids"))
    contradiction_link = first_matching(reference, operator.itemgetter("contradiction_ids"))
    unknown = next(((case["id"], item["id"]) for case in reference["cases"] for item in case["unknowns"]), None)
    contradiction = next(
        ((case["id"], item["id"]) for case in reference["cases"] for item in case["contradictions"]), None
    )
    case_id, relation_id = required_target(terminal, "a terminal")
    actor_case, actor_relation = required_target(actor, "an actor")
    continuation_case, continuation_relation = required_target(continuation, "a continuation")
    artifact_case, artifact_relation = required_target(artifacts, "an artifact or consumer")
    consumer_case, consumer_relation = required_target(consumer, "a consumer")
    unknown_case, unknown_id = required_target(unknown, "an unknown")
    contradiction_case, _contradiction_id = required_target(contradiction, "a contradiction")
    unknown_link_case, unknown_link_relation = required_target(unknown_link, "an unknown link")
    contradiction_link_case, contradiction_link_relation = required_target(contradiction_link, "a contradiction link")
    controls = [
        ("correct-source-replay", [], "pass"),
        (
            "mixed-revision-sourcecheck",
            [
                {
                    "op": "set_case_revision",
                    "case_id": "pinned-4095-source-check",
                    "value": "e66b55e05e130ea905afaf8d650ec0f5980d08d0",
                }
            ],
            "fail",
        ),
        (
            "profile-is-child",
            [
                {
                    "op": "set_relation_field",
                    "case_id": actor_case,
                    "relation_id": actor_relation,
                    "field": "actor",
                    "value": "loaded profile as spawned child",
                }
            ],
            "fail",
        ),
        (
            "nested-return-loss",
            [
                {
                    "op": "set_relation_field",
                    "case_id": continuation_case,
                    "relation_id": continuation_relation,
                    "field": "continuations",
                    "value": [],
                }
            ],
            "fail",
        ),
        (
            "same-span-collapse",
            [{"op": "remove_relation", "case_id": continuation_case, "relation_id": continuation_relation}],
            "fail",
        ),
        (
            "activity-stamping-overclaim",
            [
                {
                    "op": "append_false_relation",
                    "case_id": "prose-task-profile-start-task",
                    "id": "unsupported-activity-stamping",
                    "actor": "configuration",
                    "condition": "registry entry",
                    "action": "claim runtime activation",
                    "effect": "specific consumer exists",
                    "terminal": None,
                    "artifacts": [],
                    "consumers": [
                        {
                            "name": "activity-stamping",
                            "comparison_status": "unchanged",
                            "comparison_evidence_span_ids": [],
                        }
                    ],
                    "unknown_ids": [],
                    "contradiction_ids": [],
                    "evidence_span_ids": [],
                    "source_spans": [],
                }
            ],
            "fail",
        ),
        (
            "missed-terminal",
            [
                {
                    "op": "set_relation_field",
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "field": "terminal",
                    "value": None,
                }
            ],
            "fail",
        ),
        (
            "false-terminal",
            [
                {
                    "op": "set_relation_field",
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "field": "terminal",
                    "value": {"kind": "invented", "outcome": "unsupported"},
                }
            ],
            "fail",
        ),
        (
            "missed-artifact-consumer",
            [
                {
                    "op": "set_relation_field",
                    "case_id": artifact_case,
                    "relation_id": artifact_relation,
                    "field": "artifacts",
                    "value": [],
                },
                {
                    "op": "set_relation_field",
                    "case_id": artifact_case,
                    "relation_id": artifact_relation,
                    "field": "consumers",
                    "value": [],
                },
            ],
            "fail",
        ),
        (
            "consumer-change-misclassification",
            [
                {
                    "op": "set_consumer_status",
                    "case_id": consumer_case,
                    "relation_id": consumer_relation,
                    "value": "changed",
                }
            ],
            "fail",
        ),
        (
            "dropped-unknown",
            [{"op": "remove_annotation", "case_id": unknown_case, "collection": "unknowns", "id": unknown_id}],
            "fail",
        ),
        (
            "invented-contradiction",
            [
                {
                    "op": "append_annotation",
                    "case_id": contradiction_case,
                    "collection": "contradictions",
                    "id": "invented-contradiction",
                    "statement": "unsupported",
                    "source_spans": [],
                }
            ],
            "fail",
        ),
        (
            "dropped-unknown-link",
            [
                {
                    "op": "set_relation_field",
                    "case_id": unknown_link_case,
                    "relation_id": unknown_link_relation,
                    "field": "unknown_ids",
                    "value": [],
                }
            ],
            "fail",
        ),
        (
            "invented-contradiction-link",
            [
                {
                    "op": "set_relation_field",
                    "case_id": contradiction_link_case,
                    "relation_id": contradiction_link_relation,
                    "field": "contradiction_ids",
                    "value": ["invented-contradiction-link"],
                }
            ],
            "fail",
        ),
        (
            "incomplete-raw-record-inventory",
            [{"op": "set_case_field", "case_id": "pinned-main-t5", "field": "raw_record_inventory", "value": []}],
            "fail",
        ),
        (
            "duplicate-relation-id",
            [{"op": "append_duplicate_relation", "case_id": continuation_case, "relation_id": continuation_relation}],
            "fail",
        ),
        ("duplicate-case-id", [{"op": "append_duplicate_case", "case_id": "pinned-main-t5"}], "fail"),
    ]
    return {
        "schema_version": 2,
        "status": "grader-only-complete-trace-control-candidates",
        "candidate_shape": "Each fixture hydrates the frozen complete trace reference, then applies transparent trace mutations. The grader receives the resulting full trace, not scalar assertions.",
        "controls": [
            {
                "id": control_id,
                "candidate": {"base_reference": "../trace-reference.json", "mutations": mutations},
                "expected": {"verdict": verdict},
            }
            for control_id, mutations, verdict in controls
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    reference = build_reference()
    controls = build_controls(reference)
    if arguments.write:
        (ROOT / "trace-reference.json").write_text(json.dumps(reference, indent=2) + "\n")
        (ROOT / "controls/control-candidates.json").write_text(json.dumps(controls, indent=2) + "\n")
    else:
        print(
            json.dumps(
                {
                    "cases": len(reference["cases"]),
                    "relations": sum(len(case["relations"]) for case in reference["cases"]),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
