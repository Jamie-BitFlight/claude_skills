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
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LINE_RANGE_LENGTH = 2
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


def control_candidate_bytes(controls: dict[str, Any]) -> bytes:
    """Serialize deterministic control candidates in the repository format.

    Returns:
        UTF-8 JSON bytes for the tracked control-candidate artifact.
    """
    encoded = json.dumps(controls, indent=2, sort_keys=True)
    encoded = re.sub(r"\[\n(?P<indent>\s+)(?P<value>\"(?:[^\"\\\\]|\\\\.)*\")\n\s+\]", r"[\g<value>]", encoded)
    return (encoded + "\n").encode()


def write_control_candidates(path: Path, controls: dict[str, Any]) -> None:
    """Write control candidates in the repository's canonical JSON format.

    Args:
        path: Target control-candidate document.
        controls: Deterministic control payload to serialize.

    """
    path.write_bytes(control_candidate_bytes(controls))


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def source_bytes(revision: str, path: str) -> bytes:
    """Read one immutable source blob for source-span normalization.

    Returns:
        Source bytes at the requested revision and repository path.
    """
    git = shutil.which("git")
    if git is None:
        raise ValueError("git executable unavailable")
    result = subprocess.run([git, "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def byte_offset_for_line(content: bytes, line_number: int) -> int:
    """Return the UTF-8 byte offset where a one-based source line starts."""
    if line_number < 1:
        raise ValueError("line numbers are one-based")
    if line_number == 1:
        return 0
    offset = 0
    for _ in range(1, line_number):
        newline = content.find(b"\n", offset)
        if newline < 0:
            raise ValueError("line outside source")
        offset = newline + 1
    return offset


def catalog(source_packet_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load source metadata and compact evidence identifiers for one raw lane.

    Returns:
        Source metadata and evidence entries keyed by their raw identifiers.
    """
    packet = load(source_packet_path)
    sources = packet.get("sources", {})
    source_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(sources, dict):
        source_by_id = {key: value for key, value in sources.items() if isinstance(value, dict)}
    elif isinstance(sources, list):
        source_by_id = {
            str(item["id"]): item for item in sources if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
    evidence_by_id = {
        str(item["id"]): item
        for item in as_list(packet.get("evidence"))
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    return source_by_id, evidence_by_id


def source_span(
    evidence: dict[str, Any],
    record_id: str,
    relation_id: str,
    index: int,
    revision: str,
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve one raw evidence object to an exact revision-bound source span.

    Returns:
        A normalized span, or None when the raw evidence cannot be replayed exactly.
    """
    source = sources.get(str(evidence.get("source_id")), evidence)
    path = evidence.get("source_path", evidence.get("path", source.get("path")))
    quote = evidence.get("quote")
    lines = evidence.get("lines")
    line_start = evidence.get(
        "line_start",
        lines[0]
        if isinstance(lines, list) and len(lines) == LINE_RANGE_LENGTH
        else lines.get("start")
        if isinstance(lines, dict)
        else None,
    )
    line_end = evidence.get(
        "line_end",
        lines[1]
        if isinstance(lines, list) and len(lines) == LINE_RANGE_LENGTH
        else lines.get("end_inclusive")
        if isinstance(lines, dict)
        else None,
    )
    declared_sha256 = evidence.get(
        "source_sha256",
        evidence.get("raw_sha256", evidence.get("sha256", source.get("sha256", source.get("raw_sha256")))),
    )
    if (
        not isinstance(path, str)
        or not isinstance(quote, str)
        or not isinstance(line_start, int)
        or not isinstance(line_end, int)
    ):
        return None
    try:
        content = source_bytes(revision, path)
        if declared_sha256 and hashlib.sha256(content).hexdigest() != declared_sha256:
            return None
        bytes_range = evidence.get("utf8_bytes")
        byte_start = evidence.get(
            "utf8_byte_start", bytes_range.get("start_inclusive") if isinstance(bytes_range, dict) else None
        )
        byte_end = evidence.get(
            "utf8_byte_end_exclusive", bytes_range.get("end_exclusive") if isinstance(bytes_range, dict) else None
        )
        quote_bytes = quote.encode()
        if isinstance(byte_start, int) and isinstance(byte_end, int) and content[byte_start:byte_end] == quote_bytes:
            pass
        else:
            range_start = byte_offset_for_line(content, line_start)
            range_end = (
                byte_offset_for_line(content, line_end + 1) if line_end < content.count(b"\n") + 1 else len(content)
            )
            byte_start = content.find(quote_bytes, range_start, range_end)
            byte_end = byte_start + len(quote_bytes)
            if byte_start < 0:
                return None
    except ValueError:
        return None
    return {
        "id": f"{record_id}/{relation_id}/span-{index}",
        "repository_path": path,
        "git_blob_sha1": evidence.get("git_blob_sha1", source.get("git_blob_sha1")),
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "line_start": line_start,
        "line_end": line_end,
        "byte_start": byte_start,
        "byte_end_exclusive": byte_start + len(quote_bytes),
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote_bytes).hexdigest(),
    }


def evidence_spans(
    value: Any,
    record_id: str,
    relation_id: str,
    revision: str,
    sources: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for index, item in enumerate(as_list(value)):
        evidence = evidence_by_id.get(item) if isinstance(item, str) else item
        if not isinstance(evidence, dict):
            continue
        span = source_span(evidence, record_id, relation_id, index, revision, sources)
        if span is not None:
            spans.append(span)
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


def relation_from_raw(
    case_id: str,
    record_id: str,
    raw: dict[str, Any],
    index: int,
    revision: str,
    sources: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_id = str(raw.get("id", f"relation-{index}"))
    relation_id = f"{record_id}/{source_id}"
    raw_evidence = as_list(raw.get("evidence"))
    spans = evidence_spans(raw_evidence, record_id, source_id, revision, sources, evidence_by_id)
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
        "evidence_complete": bool(spans) and len(spans) == len(raw_evidence),
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


def collect_relations(
    case_id: str,
    record_id: str,
    trace: dict[str, Any],
    revision: str,
    sources: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_relations = trace.get("relationships", trace.get("steps", trace.get("records", [])))
    if not isinstance(raw_relations, list):
        return []
    return [
        relation_from_raw(case_id, record_id, relation, index, revision, sources, evidence_by_id)
        for index, relation in enumerate(raw_relations)
        if isinstance(relation, dict)
    ]


def collect_annotations(
    trace: dict[str, Any],
    record_id: str,
    key: str,
    revision: str,
    sources: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    annotations: list[dict[str, Any]] = []
    for index, annotation in enumerate(as_list(trace.get(key))):
        if not isinstance(annotation, dict):
            continue
        annotation_id = str(annotation.get("id", f"{key}-{index}"))
        annotations.append({
            "id": f"{record_id}/{annotation_id}",
            "source_records": [record_id],
            "statement": annotation.get("statement", annotation.get("condition", annotation)),
            "source_spans": evidence_spans(
                annotation.get("evidence"), record_id, annotation_id, revision, sources, evidence_by_id
            ),
            "source_annotation": annotation,
        })
    return annotations


def build_reference() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case_id, (revision, records) in CASE_RECORDS.items():
        inventory: list[dict[str, Any]] = []
        relations: list[dict[str, Any]] = []
        rejected_relations: list[dict[str, Any]] = []
        rejected_annotations: list[dict[str, Any]] = []
        unknowns: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        for label, trace_path in records:
            path = ROOT / trace_path
            trace = load(path)
            record_id = f"{case_id}/{label}"
            source_packet_path = path.with_name("source-packet.json")
            sources, evidence_by_id = catalog(source_packet_path)
            inventory.append({
                "record_id": record_id,
                "trace_path": trace_path,
                "raw_trace_sha256": sha256(path),
                "authority": "raw-source-only-lane; retained without relation-level lane selection",
            })
            for relation in collect_relations(case_id, record_id, trace, revision, sources, evidence_by_id):
                if relation["evidence_complete"]:
                    relations.append(relation)
                else:
                    rejected_relations.append({
                        "id": relation["id"],
                        "source_records": relation["source_records"],
                        "reason": "no_exact_replayable_source_span_in_retained_raw_evidence",
                        "raw_evidence": relation["source_relation"].get("evidence"),
                    })
            for annotation in collect_annotations(trace, record_id, "unknowns", revision, sources, evidence_by_id):
                if annotation["source_spans"]:
                    unknowns.append(annotation)
                else:
                    rejected_annotations.append({
                        "id": annotation["id"],
                        "collection": "unknowns",
                        "reason": "no_exact_replayable_source_span_in_retained_raw_evidence",
                        "raw_evidence": annotation["source_annotation"].get("evidence"),
                    })
            for annotation in collect_annotations(
                trace, record_id, "contradictions", revision, sources, evidence_by_id
            ):
                if annotation["source_spans"]:
                    contradictions.append(annotation)
                else:
                    rejected_annotations.append({
                        "id": annotation["id"],
                        "collection": "contradictions",
                        "reason": "no_exact_replayable_source_span_in_retained_raw_evidence",
                        "raw_evidence": annotation["source_annotation"].get("evidence"),
                    })
        case = {
            "id": case_id,
            "source_revision": revision,
            "raw_record_inventory": inventory,
            "relations": relations,
            "rejected_relations": rejected_relations,
            "rejected_annotations": rejected_annotations,
            "unknowns": unknowns,
            "contradictions": contradictions,
            "reference_status": "source-only-replayable-lane-normalization",
            "boundary": "Accepted relations have exact replayable source spans. Retained raw relations without exact source spans are explicitly rejected; neither category is an independent verification, runtime observation, or architecture selection.",
        }
        bind_relation_annotations(case)
        cases.append(case)
    return {
        "schema_version": 1,
        "reference_status": "replayable-source-only-awaiting-independent-complete-trace-receipts",
        "normalization": {
            "relation_identity": "record_id plus immutable raw relation id; identical spans never merge accepted relations",
            "rejection_rule": "A relation is accepted only with at least one exact revision-bound source span. Otherwise it remains in rejected_relations with its retained raw evidence identifiers.",
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
            "removed-source-span",
            [{"op": "remove_source_spans", "case_id": actor_case, "relation_id": actor_relation}],
            "fail",
        ),
        (
            "corrupted-source-quote",
            [
                {
                    "op": "corrupt_source_quote",
                    "case_id": actor_case,
                    "relation_id": actor_relation,
                    "value": "unsupported source quote",
                }
            ],
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
            "missing-required-case-field",
            [{"op": "remove_case_field", "case_id": "pinned-main-t5", "field": "unknowns"}],
            "fail",
        ),
        (
            "wrong-case-id",
            [{"op": "set_case_id", "case_id": "pinned-main-t5", "value": "not-a-declared-complete-trace-case"}],
            "fail",
        ),
        (
            "no-span-candidate-relation",
            [{"op": "remove_source_spans", "case_id": actor_case, "relation_id": actor_relation}],
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
        "schema_version": 3,
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    reference = build_reference()
    controls = build_controls(reference)
    trace_bytes = (json.dumps(reference, indent=2) + "\n").encode()
    controls_bytes = control_candidate_bytes(controls)
    if arguments.write:
        (ROOT / "trace-reference.json").write_bytes(trace_bytes)
        write_control_candidates(ROOT / "controls/control-candidates.json", controls)
    elif arguments.check:
        expected = {"trace-reference.json": trace_bytes, "controls/control-candidates.json": controls_bytes}
        mismatches = [path for path, contents in expected.items() if (ROOT / path).read_bytes() != contents]
        if mismatches:
            raise SystemExit(json.dumps({"status": "failed", "drift": mismatches}, indent=2))
        print(json.dumps({"status": "passed", "generated": sorted(expected)}))
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
