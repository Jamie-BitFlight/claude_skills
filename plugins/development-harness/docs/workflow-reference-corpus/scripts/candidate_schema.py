"""Validate the non-gold complete-trace candidate shape without reference answers."""

from __future__ import annotations

import hashlib
import runpy
from pathlib import PurePosixPath
from typing import Any

SHA256_HEX_LENGTH = 64
canonicalize_trace = runpy.run_path(str(PurePosixPath(__file__).with_name("canonical_ir.py")))["canonicalize_trace"]


def failure(path: str, reason: str) -> dict[str, str]:
    """Build one machine-readable schema failure.

    Returns:
        Path-addressed failure object.
    """
    return {"path": path, "reason": reason}


def object_items(value: object, path: str, failures: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Return object-list items while recording malformed container members."""
    if not isinstance(value, list):
        failures.append(failure(path, "expected_array"))
        return []
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            failures.append(failure(f"{path}[{index}]", "expected_object"))
            continue
        objects.append(item)
    return objects


def required_string(item: dict[str, Any], field: str, path: str, failures: list[dict[str, str]]) -> None:
    """Require one string property without raising on malformed input."""
    if field not in item:
        failures.append(failure(path, f"missing_field:{field}"))
    elif not isinstance(item[field], str):
        failures.append(failure(f"{path}.{field}", "expected_string"))


def required_integer(item: dict[str, Any], field: str, path: str, failures: list[dict[str, str]]) -> None:
    """Require one integer property without accepting booleans."""
    if field not in item:
        failures.append(failure(path, f"missing_field:{field}"))
    elif type(item[field]) is not int:
        failures.append(failure(f"{path}.{field}", "expected_integer"))


def string_list(item: dict[str, Any], field: str, path: str, failures: list[dict[str, str]]) -> None:
    """Require one list whose members are strings."""
    value = item.get(field)
    if not isinstance(value, list):
        failures.append(failure(f"{path}.{field}", "expected_array"))
        return
    for index, member in enumerate(value):
        if not isinstance(member, str):
            failures.append(failure(f"{path}.{field}[{index}]", "expected_string"))


def validate_span(span: dict[str, Any], path: str, failures: list[dict[str, str]]) -> None:
    """Validate every source-span field dereferenced by the grader."""
    for field in ("id", "repository_path", "source_sha256", "quote", "quote_sha256"):
        required_string(span, field, path, failures)
    for field in ("line_start", "line_end", "byte_start", "byte_end_exclusive"):
        required_integer(span, field, path, failures)
    repository_path = span.get("repository_path")
    if isinstance(repository_path, str):
        normalized_path = PurePosixPath(repository_path)
        if normalized_path.is_absolute() or ".." in normalized_path.parts:
            failures.append(failure(f"{path}.repository_path", "must_be_relative"))
    for field in ("source_sha256", "quote_sha256"):
        value = span.get(field)
        if isinstance(value, str) and (
            len(value) != SHA256_HEX_LENGTH or any(char not in "0123456789abcdef" for char in value)
        ):
            failures.append(failure(f"{path}.{field}", "expected_lowercase_sha256"))
    quote = span.get("quote")
    quote_sha256 = span.get("quote_sha256")
    if (
        isinstance(quote, str)
        and isinstance(quote_sha256, str)
        and hashlib.sha256(quote.encode()).hexdigest() != quote_sha256
    ):
        failures.append(failure(f"{path}.quote_sha256", "quote_digest_mismatch"))
    line_start, line_end = span.get("line_start"), span.get("line_end")
    if type(line_start) is int and type(line_end) is int and (line_start < 1 or line_end < line_start):
        failures.append(failure(path, "invalid_line_range"))
    byte_start, byte_end = span.get("byte_start"), span.get("byte_end_exclusive")
    if type(byte_start) is int and type(byte_end) is int and (byte_start < 0 or byte_end < byte_start):
        failures.append(failure(path, "invalid_byte_range"))


def validate_spans(item: dict[str, Any], path: str, failures: list[dict[str, str]]) -> None:
    """Validate a non-empty source-span object list."""
    spans = object_items(item.get("source_spans"), f"{path}.source_spans", failures)
    if not spans:
        failures.append(failure(f"{path}.source_spans", "must_not_be_empty"))
    for index, span in enumerate(spans):
        validate_span(span, f"{path}.source_spans[{index}]", failures)


def validate_consumer(
    consumer: dict[str, Any], path: str, contract: dict[str, Any], failures: list[dict[str, str]]
) -> None:
    """Validate a consumer-change object used by the consumer_change dimension."""
    for field in contract["consumer_required_fields"]:
        required_string(consumer, field, path, failures)
    status = consumer.get("comparison_status")
    if isinstance(status, str) and status not in contract["consumer_comparison_statuses"]:
        failures.append(failure(f"{path}.comparison_status", "unsupported_status"))
    string_list(consumer, "comparison_evidence_span_ids", path, failures)


def validate_relation(
    relation: dict[str, Any], path: str, contract: dict[str, Any], failures: list[dict[str, str]]
) -> None:
    """Validate collection types and nested values consumed while grading relations."""
    failures.extend(
        failure(path, f"missing_field:{field}")
        for field in contract["relation_required_fields"]
        if field not in relation
    )
    required_string(relation, "id", path, failures)
    string_list(relation, "unknown_ids", path, failures)
    string_list(relation, "contradiction_ids", path, failures)
    if not isinstance(relation.get("artifacts"), list):
        failures.append(failure(f"{path}.artifacts", "expected_array"))
    consumers = object_items(relation.get("consumers"), f"{path}.consumers", failures)
    for index, consumer in enumerate(consumers):
        validate_consumer(consumer, f"{path}.consumers[{index}]", contract, failures)
    validate_spans(relation, path, failures)


def validate_annotation(annotation: dict[str, Any], path: str, failures: list[dict[str, str]]) -> None:
    """Validate an unknown or contradiction object consumed by replay/scoring."""
    required_string(annotation, "id", path, failures)
    required_string(annotation, "statement", path, failures)
    validate_spans(annotation, path, failures)


def candidate_schema_failures(candidate: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, str]]:
    """Return all recursive candidate-schema failures without comparing reference content.

    Returns:
        Machine-readable path/reason records for every invalid consumed field.
    """
    output = contract.get("output")
    if not isinstance(output, dict):
        return [failure("contract.output", "expected_object")]
    failures: list[dict[str, str]] = []
    cases = object_items(candidate.get("cases"), "cases", failures)
    allowed_case_ids = output.get("allowed_case_ids")
    if not isinstance(allowed_case_ids, list) or not all(isinstance(case_id, str) for case_id in allowed_case_ids):
        return [*failures, failure("contract.output.allowed_case_ids", "expected_string_array")]
    observed_ids: list[str] = []
    for index, case in enumerate(cases):
        path = f"cases[{index}]"
        failures.extend(
            failure(path, f"missing_field:{field}")
            for field in output.get("case_required_fields", [])
            if field not in case
        )
        required_string(case, "id", path, failures)
        case_id = case.get("id")
        if isinstance(case_id, str):
            observed_ids.append(case_id)
            if case_id not in allowed_case_ids:
                failures.append(failure(f"{path}.id", "unsupported_case_id"))
        required_string(case, "source_revision", path, failures)
        for collection in ("record_manifest", "rejected_relations", "rejected_annotations"):
            object_items(case.get(collection), f"{path}.{collection}", failures)
        relations = object_items(case.get("relations"), f"{path}.relations", failures)
        for relation_index, relation in enumerate(relations):
            validate_relation(relation, f"{path}.relations[{relation_index}]", output, failures)
        for collection in ("unknowns", "contradictions"):
            annotations = object_items(case.get(collection), f"{path}.{collection}", failures)
            for annotation_index, annotation in enumerate(annotations):
                validate_annotation(annotation, f"{path}.{collection}[{annotation_index}]", failures)
    failures.extend(
        failure("cases", f"expected_exactly_one_case:{case_id}")
        for case_id in allowed_case_ids
        if observed_ids.count(case_id) != 1
    )
    _canonical_trace, canonicalization_failures = canonicalize_trace(candidate)
    failures.extend(failure(item["path"], f"canonical:{item['reason']}") for item in canonicalization_failures)
    return failures
