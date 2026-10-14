# ruff: file-ignore[complex-structure, docstring-missing-returns, too-many-branches, too-many-locals, too-many-statements]
"""Canonical complete-trace representation shared by producer validation and grading."""

from __future__ import annotations

import hashlib
import json
import operator
import unicodedata
from pathlib import Path
from typing import Any

SPEC_VERSION = 1
REJECTION_REASON = "no_exact_replayable_source_span"
TEXT_FIELDS = ("actor", "condition", "action", "effect", "statement")
CONSUMER_STATUSES = frozenset({"changed", "unchanged", "unresolved"})
ROOT = Path(__file__).resolve().parents[1]
SOURCE_UNIT_MANIFEST = ROOT / "source-unit-manifest.json"
SOURCE_UNIT_FIELDS = (
    "case_id",
    "source_revision",
    "repository_path",
    "source_sha256",
    "line_start",
    "line_end",
    "byte_start",
    "byte_end_exclusive",
    "quote",
    "quote_sha256",
)


def canonical_json(value: object) -> str:
    """Encode a stable JSON value for hashing and comparison."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(domain: str, value: object) -> str:
    """Return the domain-separated identifier for canonical content."""
    preimage = f"workflow-reference-corpus/v{SPEC_VERSION}/{domain}\0{canonical_json(value)}".encode()
    return f"{domain}:{hashlib.sha256(preimage).hexdigest()}"


def normal_text(value: object) -> str | None:
    """Normalize textual IR values without substituting semantic vocabulary."""
    if value is None:
        return None
    if not isinstance(value, str):
        return canonical_json(value)
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def normal_value(value: object) -> object:
    """Normalize free-form JSON while preserving scalar and object semantics."""
    if isinstance(value, str):
        return normal_text(value)
    if isinstance(value, list):
        return sorted((normal_value(item) for item in value), key=canonical_json)
    if isinstance(value, dict):
        return {str(key): normal_value(item) for key, item in sorted(value.items())}
    return value


def source_unit_payload(case_id: str, revision: str, span: dict[str, Any]) -> dict[str, Any]:
    """Return the public source-unit fields that define a finite quote interval."""
    return {
        "case_id": case_id,
        "source_revision": revision,
        "repository_path": span["repository_path"],
        "source_sha256": span["source_sha256"],
        "line_start": span["line_start"],
        "line_end": span["line_end"],
        "byte_start": span["byte_start"],
        "byte_end_exclusive": span["byte_end_exclusive"],
        "quote": span["quote"],
        "quote_sha256": span["quote_sha256"],
    }


def source_unit_signature(case_id: str, revision: str, span: dict[str, Any]) -> str:
    """Return the canonical identity of one manifest-declared source unit."""
    return canonical_json(source_unit_payload(case_id, revision, span))


def source_units_by_case(manifest: object) -> dict[tuple[str, str], set[str]]:
    """Index valid declared source units by case and revision."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("source_units"), list):
        return {}
    output: dict[tuple[str, str], set[str]] = {}
    for unit in manifest["source_units"]:
        if not isinstance(unit, dict) or any(field not in unit for field in SOURCE_UNIT_FIELDS):
            continue
        case_id, revision = unit["case_id"], unit["source_revision"]
        if not isinstance(case_id, str) or not isinstance(revision, str):
            continue
        output.setdefault((case_id, revision), set()).add(
            canonical_json({field: unit[field] for field in SOURCE_UNIT_FIELDS})
        )
    return output


def load_source_unit_manifest() -> dict[str, Any]:
    """Load the public source-unit manifest beside this canonicalizer."""
    value = json.loads(SOURCE_UNIT_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("source-unit-manifest.json must contain a JSON object")
    return value


def failures_for_span(span: object, path: str) -> list[dict[str, str]]:
    """Report canonical span precondition failures."""
    if not isinstance(span, dict):
        return [{"path": path, "reason": "expected_object"}]
    required_strings = ("repository_path", "source_sha256", "quote", "quote_sha256")
    required_ints = ("line_start", "line_end", "byte_start", "byte_end_exclusive")
    failures: list[dict[str, str]] = [
        {"path": f"{path}.{field}", "reason": "expected_string"}
        for field in required_strings
        if not isinstance(span.get(field), str)
    ]
    failures.extend(
        {"path": f"{path}.{field}", "reason": "expected_integer"}
        for field in required_ints
        if type(span.get(field)) is not int
    )
    if failures:
        return failures
    quote = span["quote"]
    if hashlib.sha256(quote.encode()).hexdigest() != span["quote_sha256"]:
        failures.append({"path": f"{path}.quote_sha256", "reason": "quote_digest_mismatch"})
    if span["line_start"] < 1 or span["line_end"] < span["line_start"]:
        failures.append({"path": path, "reason": "invalid_line_range"})
    if span["byte_start"] < 0 or span["byte_end_exclusive"] < span["byte_start"]:
        failures.append({"path": path, "reason": "invalid_byte_range"})
    return failures


def canonical_span(span: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize a revision-bound source span and derive its identifier."""
    normalized_quote = unicodedata.normalize("NFKC", span["quote"])
    payload = {
        "repository_path": span["repository_path"],
        "source_sha256": span["source_sha256"],
        "line_start": span["line_start"],
        "line_end": span["line_end"],
        "byte_start": span["byte_start"],
        "byte_end_exclusive": span["byte_end_exclusive"],
        "quote": normalized_quote,
        "quote_sha256": hashlib.sha256(normalized_quote.encode()).hexdigest(),
    }
    return {
        "id": stable_id("span", payload),
        **{key: value for key, value in payload.items() if key not in {"quote", "quote_sha256"}},
        "quote": span["quote"],
        "quote_sha256": span["quote_sha256"],
    }


def canonical_spans(
    spans: object,
    path: str,
    failures: list[dict[str, str]],
    case_id: str | None,
    revision: str | None,
    source_units: dict[tuple[str, str], set[str]],
) -> list[dict[str, Any]]:
    """Validate, deduplicate, and order a span collection."""
    if not isinstance(spans, list) or not spans:
        failures.append({"path": path, "reason": "must_not_be_empty"})
        return []
    output: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(spans):
        failures.extend(failures_for_span(value, f"{path}[{index}]"))
        if isinstance(value, dict) and not failures_for_span(value, f"{path}[{index}]"):
            if (
                case_id is None
                or revision is None
                or source_unit_signature(case_id, revision, value) not in source_units.get((case_id, revision), set())
            ):
                failures.append({"path": f"{path}[{index}]", "reason": "source_unit_not_declared"})
                continue
            normalized = canonical_span(value)
            output[normalized["id"]] = normalized
    return [output[span_id] for span_id in sorted(output)]


def canonical_consumer(consumer: object, failures: list[dict[str, str]], path: str) -> dict[str, Any] | None:
    """Normalize one consumer entity and derive its content identity."""
    if not isinstance(consumer, dict):
        failures.append({"path": path, "reason": "expected_object"})
        return None
    name = normal_text(consumer.get("name"))
    status = normal_text(consumer.get("comparison_status"))
    if name is None:
        failures.append({"path": f"{path}.name", "reason": "expected_string"})
        return None
    if status not in CONSUMER_STATUSES:
        failures.append({"path": f"{path}.comparison_status", "reason": "unsupported_status"})
        return None
    return {"name": name, "comparison_status": status}


def relation_payload(
    relation: dict[str, Any], spans: list[dict[str, Any]], annotations: dict[str, str]
) -> dict[str, Any]:
    """Project one relation onto its complete canonical semantic payload."""
    provisional: dict[str, object] = {
        field: normal_text(relation.get(field)) for field in TEXT_FIELDS if field != "statement"
    }
    provisional["continuations"] = normal_value(relation.get("continuations"))
    provisional["terminal"] = normal_value(relation.get("terminal"))
    provisional["artifacts"] = sorted(
        (normal_value(item) for item in relation.get("artifacts", [])), key=canonical_json
    )
    provisional["source_span_ids"] = [span["id"] for span in spans]
    provisional["unknown_ids"] = sorted(
        annotations[item] for item in relation.get("unknown_ids", []) if item in annotations
    )
    provisional["contradiction_ids"] = sorted(
        annotations[item] for item in relation.get("contradiction_ids", []) if item in annotations
    )
    return provisional


def canonical_annotation(
    annotation: object,
    kind: str,
    path: str,
    failures: list[dict[str, str]],
    case_id: str | None,
    revision: str | None,
    source_units: dict[tuple[str, str], set[str]],
) -> tuple[str, dict[str, Any]] | None:
    """Canonicalize an uncertainty or contradiction annotation."""
    if not isinstance(annotation, dict):
        failures.append({"path": path, "reason": "expected_object"})
        return None
    statement = normal_text(annotation.get("statement"))
    if statement is None:
        failures.append({"path": f"{path}.statement", "reason": "expected_string"})
        return None
    spans = canonical_spans(
        annotation.get("source_spans"), f"{path}.source_spans", failures, case_id, revision, source_units
    )
    if not spans:
        return None
    if len(spans) != 1:
        failures.append({"path": f"{path}.source_spans", "reason": "noncanonical_source_unit_boundary"})
        return None
    payload = {"class": kind, "statement": statement, "source_span_ids": [span["id"] for span in spans]}
    return str(annotation.get("id", "")), {"id": stable_id(kind, payload), **payload, "source_spans": spans}


def canonical_rejection(
    item: object, collection: str, path: str, failures: list[dict[str, str]]
) -> dict[str, Any] | None:
    """Classify unsupported source units without preserving raw producer identifiers."""
    if not isinstance(item, dict):
        failures.append({"path": path, "reason": "expected_object"})
        return None
    reason = item.get("reason_code", item.get("reason"))
    if reason != REJECTION_REASON:
        failures.append({"path": f"{path}.reason_code", "reason": "unsupported_rejection_reason"})
        return None
    source_unit = normal_value(item.get("source_unit", item.get("raw_evidence")))
    raw_source_records = item.get("source_records", [])
    source_record_ids = (
        [normal_text(record_id) for record_id in raw_source_records] if isinstance(raw_source_records, list) else []
    )
    source_record_ids = sorted(record_id for record_id in source_record_ids if record_id is not None)
    payload = {
        "collection": collection,
        "reason_code": reason,
        "source_record_ids": source_record_ids,
        "source_unit": source_unit,
    }
    return {"id": stable_id("rejection", payload), **payload}


def canonicalize_case(
    case: object, source_units: dict[tuple[str, str], set[str]], path: str = "case"
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Canonicalize one complete trace case while preserving all semantic dimensions."""
    failures: list[dict[str, str]] = []
    if not isinstance(case, dict):
        return None, [{"path": path, "reason": "expected_object"}]
    case_id = case.get("id")
    revision = case.get("source_revision")
    if not isinstance(case_id, str):
        failures.append({"path": f"{path}.id", "reason": "expected_string"})
    if not isinstance(revision, str):
        failures.append({"path": f"{path}.source_revision", "reason": "expected_string"})
    annotations: dict[str, str] = {}
    annotation_objects: dict[str, list[dict[str, Any]]] = {"unknowns": [], "contradictions": []}
    for collection, kind in (("unknowns", "unknown"), ("contradictions", "contradiction")):
        values = case.get(collection, [])
        if not isinstance(values, list):
            failures.append({"path": f"{path}.{collection}", "reason": "expected_array"})
            continue
        for index, item in enumerate(values):
            normalized = canonical_annotation(
                item, kind, f"{path}.{collection}[{index}]", failures, case_id, revision, source_units
            )
            if normalized is not None:
                supplied_id, canonical_annotation_item = normalized
                annotations[supplied_id] = canonical_annotation_item["id"]
                annotation_objects[collection].append(canonical_annotation_item)
    relations: list[dict[str, Any]] = []
    values = case.get("relations", [])
    if not isinstance(values, list):
        failures.append({"path": f"{path}.relations", "reason": "expected_array"})
        values = []
    for index, relation in enumerate(values):
        relation_path = f"{path}.relations[{index}]"
        if not isinstance(relation, dict):
            failures.append({"path": relation_path, "reason": "expected_object"})
            continue
        spans = canonical_spans(
            relation.get("source_spans"), f"{relation_path}.source_spans", failures, case_id, revision, source_units
        )
        if not spans:
            continue
        if len(spans) != 1:
            failures.append({"path": f"{relation_path}.source_spans", "reason": "noncanonical_source_unit_boundary"})
            continue
        for field in ("unknown_ids", "contradiction_ids"):
            links = relation.get(field, [])
            if not isinstance(links, list) or not all(isinstance(link, str) for link in links):
                failures.append({"path": f"{relation_path}.{field}", "reason": "expected_string_array"})
                continue
            failures.extend(
                {"path": f"{relation_path}.{field}", "reason": "unknown_annotation_link"}
                for link in links
                if link not in annotations
            )
        payload = relation_payload(relation, spans, annotations)
        consumers: list[dict[str, Any]] = []
        raw_consumers = relation.get("consumers", [])
        if not isinstance(raw_consumers, list):
            failures.append({"path": f"{relation_path}.consumers", "reason": "expected_array"})
        else:
            for consumer_index, consumer in enumerate(raw_consumers):
                normalized = canonical_consumer(consumer, failures, f"{relation_path}.consumers[{consumer_index}]")
                if normalized is not None:
                    consumers.append(normalized)
        payload["consumers"] = sorted(consumers, key=canonical_json)
        relation_id = stable_id("relation", {"case_id": case_id, **payload})
        for consumer in payload["consumers"]:
            consumer["id"] = stable_id(
                "consumer",
                {
                    "relation_id": relation_id,
                    "name": consumer["name"],
                    "comparison_status": consumer["comparison_status"],
                },
            )
            consumer["relation_id"] = relation_id
            consumer["comparison_evidence_span_ids"] = [span["id"] for span in spans]
        relations.append({"id": relation_id, **payload, "source_spans": spans})
    rejections: dict[str, list[dict[str, Any]]] = {}
    for collection in ("rejected_relations", "rejected_annotations"):
        values = case.get(collection, [])
        if not isinstance(values, list):
            failures.append({"path": f"{path}.{collection}", "reason": "expected_array"})
            values = []
        normalized = [
            item
            for index, value in enumerate(values)
            if (item := canonical_rejection(value, collection, f"{path}.{collection}[{index}]", failures)) is not None
        ]
        unique_rejections = {item["id"]: item for item in normalized}
        rejections[collection] = sorted(unique_rejections.values(), key=operator.itemgetter("id"))
    if failures:
        return None, failures
    duplicate_relation_ids = {
        relation["id"] for relation in relations if sum(other["id"] == relation["id"] for other in relations) > 1
    }
    failures.extend(
        {"path": path, "reason": f"noncanonical_relation_boundary:{relation_id}"}
        for relation_id in sorted(duplicate_relation_ids)
    )
    if failures:
        return None, failures
    relations.sort(key=operator.itemgetter("id"))
    for values in annotation_objects.values():
        values.sort(key=operator.itemgetter("id"))
    return {
        "id": case_id,
        "source_revision": revision,
        "record_manifest": case.get("record_manifest", []),
        "relations": relations,
        "unknowns": annotation_objects["unknowns"],
        "contradictions": annotation_objects["contradictions"],
        **rejections,
    }, failures


def canonicalize_trace(
    trace: object, source_unit_manifest: dict[str, Any] | None = None
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Canonicalize an entire trace into ID-independent semantic records."""
    if not isinstance(trace, dict) or not isinstance(trace.get("cases"), list):
        return None, [{"path": "cases", "reason": "expected_array"}]
    failures: list[dict[str, str]] = []
    cases: list[dict[str, Any]] = []
    source_units = source_units_by_case(
        load_source_unit_manifest() if source_unit_manifest is None else source_unit_manifest
    )
    for index, case in enumerate(trace["cases"]):
        normalized, case_failures = canonicalize_case(case, source_units, f"cases[{index}]")
        failures.extend(case_failures)
        if normalized is not None:
            cases.append(normalized)
    duplicate_case_ids = {case["id"] for case in cases if sum(other["id"] == case["id"] for other in cases) > 1}
    failures.extend(
        {"path": "cases", "reason": f"duplicate_case_id:{case_id}"} for case_id in sorted(duplicate_case_ids)
    )
    return {"schema_version": SPEC_VERSION, "cases": sorted(cases, key=operator.itemgetter("id"))}, failures
