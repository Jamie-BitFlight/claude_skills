# /// script
# requires-python = ">=3.11"
# ///
# ruff: file-ignore[complex-structure, too-many-branches, too-many-locals, too-many-return-statements, too-many-statements]
"""Replay and grade complete source-only workflow traces deterministically."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import runpy
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
canonical_ir = runpy.run_path(str(Path(__file__).with_name("canonical_ir.py")))
candidate_schema_failures = cast(
    "Callable[[dict[str, Any], dict[str, Any]], list[dict[str, str]]]",
    runpy.run_path(str(Path(__file__).with_name("candidate_schema.py")))["candidate_schema_failures"],
)
canonicalize_trace = cast(
    "Callable[..., tuple[dict[str, Any] | None, list[dict[str, str]]]]", canonical_ir["canonicalize_trace"]
)
source_unit_signature = cast("Callable[[str, str, dict[str, Any]], str]", canonical_ir["source_unit_signature"])
source_units_by_case = cast("Callable[[object], dict[tuple[str, str], set[str]]]", canonical_ir["source_units_by_case"])
DIMENSIONS = (
    "relations",
    "terminals",
    "actors",
    "artifacts_consumers",
    "uncertainty_contradictions",
    "consumer_change",
)
SOURCE_DERIVED_TABLE_ACTIONS = {"| J5 | `in-progress`, launch of this session still running | wait |": "wait"}


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
    cases = trace.get("cases")
    if not isinstance(cases, list):
        return {}
    return {case_id: case for case in cases if isinstance(case, dict) and isinstance(case_id := case.get("id"), str)}


def object_collection(case: dict[str, Any], field: str) -> list[dict[str, Any]]:
    """Return a candidate collection without trusting malformed input."""
    value = case.get(field)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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


def public_source_units(case_id: str, revision: str) -> set[str]:
    """Return exact public source-unit signatures for one case revision.

    Returns:
        Case-scoped quote interval signatures from the finite public manifest.
    """
    return source_units_by_case(load(ROOT / "source-unit-manifest.json")).get((case_id, revision), set())


def source_unit_is_declared(case_id: str, revision: str, span: dict[str, Any], allowed_units: set[str]) -> bool:
    """Return whether a structurally complete span is in the public finite vocabulary."""
    try:
        return source_unit_signature(case_id, revision, span) in allowed_units
    except KeyError:
        return False


def public_case_revisions() -> dict[str, set[str]]:
    """Return producer-visible revisions declared for each allowed case.

    Returns:
        Revisions keyed by case ID from the public source-unit manifest.
    """
    revisions: dict[str, set[str]] = {}
    for unit in load(ROOT / "source-unit-manifest.json").get("source_units", []):
        if not isinstance(unit, dict):
            continue
        case_id = unit.get("case_id")
        revision = unit.get("source_revision")
        if isinstance(case_id, str) and isinstance(revision, str):
            revisions.setdefault(case_id, set()).add(revision)
    return revisions


def structural_failures(candidate: dict[str, Any], candidate_contract: dict[str, Any]) -> dict[str, list[str]]:
    """Validate exact complete-trace coverage before dimension scoring.

    Returns:
        Failures keyed by declared case id, or `__corpus__` for global failures.
    """
    failures: dict[str, list[str]] = {}
    candidate_cases = candidate.get("cases")
    if not isinstance(candidate_cases, list) or not all(isinstance(case, dict) for case in candidate_cases):
        return {"__corpus__": ["candidate_cases_not_list"]}
    for schema_failure in candidate_schema_failures(candidate, candidate_contract):
        path = schema_failure["path"]
        case_id = "__corpus__"
        if path.startswith("cases["):
            index_text = path.split("]", 1)[0].removeprefix("cases[")
            if index_text.isdigit() and int(index_text) < len(candidate_cases):
                candidate_id = candidate_cases[int(index_text)].get("id")
                if isinstance(candidate_id, str):
                    case_id = candidate_id
        failures.setdefault(case_id, []).append(f"schema:{path}:{schema_failure['reason']}")
    revisions_by_case = public_case_revisions()
    allowed_case_ids = set(revisions_by_case)
    candidate_ids = [case.get("id") for case in candidate_cases]
    for case_id in duplicate_ids(candidate_cases):
        failures.setdefault(case_id, []).append("duplicate_case_id")
    candidate_id_set = {case_id for case_id in candidate_ids if isinstance(case_id, str)}
    for case_id in sorted(allowed_case_ids - candidate_id_set):
        failures.setdefault(case_id, []).append("missing_case")
    for case_id in sorted(candidate_id_set - allowed_case_ids):
        failures.setdefault("__corpus__", []).append(f"extra_case:{case_id}")
    for candidate_case in candidate_cases:
        case_id = candidate_case.get("id")
        if not isinstance(case_id, str) or case_id not in allowed_case_ids:
            continue
        case_failures = failures.setdefault(case_id, [])
        required = (
            "source_revision",
            "record_manifest",
            "relations",
            "rejected_relations",
            "rejected_annotations",
            "unknowns",
            "contradictions",
        )
        for field in required:
            if field not in candidate_case:
                case_failures.append(f"missing_field:{field}")
        expected_manifest = [
            entry for entry in load(ROOT / "record-manifest.json")["records"] if entry["case_id"] == case_id
        ]
        if sorted(candidate_case.get("record_manifest", []), key=canonical) != sorted(expected_manifest, key=canonical):
            case_failures.append("record_manifest_provenance_mismatch")
        for collection in ("relations", "rejected_relations", "rejected_annotations", "unknowns", "contradictions"):
            items = candidate_case.get(collection)
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                case_failures.append(f"invalid_collection:{collection}")
                continue
            for duplicate_id in duplicate_ids(items):
                case_failures.append(f"duplicate_{collection}_id:{duplicate_id}")
        unknown_ids = {
            item["id"] for item in object_collection(candidate_case, "unknowns") if isinstance(item.get("id"), str)
        }
        contradiction_ids = {
            item["id"]
            for item in object_collection(candidate_case, "contradictions")
            if isinstance(item.get("id"), str)
        }
        required_relation_fields = (
            "id",
            "actor",
            "condition",
            "action",
            "effect",
            "continuations",
            "terminal",
            "artifacts",
            "consumers",
            "source_spans",
        )
        revision = candidate_case.get("source_revision")
        if revision not in revisions_by_case.get(case_id, set()):
            case_failures.append("source_revision_not_in_public_source_unit_manifest")
        allowed_source_units = public_source_units(case_id, revision) if isinstance(revision, str) else set()
        for relation in object_collection(candidate_case, "relations"):
            for field in required_relation_fields:
                if field not in relation:
                    case_failures.append(f"relation_missing_field:{relation.get('id')}:{field}")
            if not relation.get("source_spans"):
                case_failures.append(f"relation_missing_replayable_source_span:{relation.get('id')}")
            for span in object_collection(relation, "source_spans"):
                if not isinstance(revision, str) or not source_unit_is_declared(
                    case_id, revision, span, allowed_source_units
                ):
                    case_failures.append(f"source_span_not_in_public_source_unit_manifest:{relation.get('id')}")
            for field, valid_ids in (("unknown_ids", unknown_ids), ("contradiction_ids", contradiction_ids)):
                links = relation.get(field)
                if not isinstance(links, list) or not all(isinstance(link, str) for link in links):
                    case_failures.append(f"invalid_{field}:{relation.get('id')}")
                    continue
                for link in links:
                    if link not in valid_ids:
                        case_failures.append(f"invalid_{field}_link:{relation.get('id')}:{link}")
        for collection in ("unknowns", "contradictions"):
            for item in object_collection(candidate_case, collection):
                if not item.get("source_spans"):
                    case_failures.append(f"{collection}_missing_replayable_source_span:{item.get('id')}")
                for span in object_collection(item, "source_spans"):
                    if not isinstance(revision, str) or not source_unit_is_declared(
                        case_id, revision, span, allowed_source_units
                    ):
                        case_failures.append(f"source_span_not_in_public_source_unit_manifest:{item.get('id')}")
        if not case_failures:
            failures.pop(case_id, None)
    return failures


def relation_index(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a case's relations by immutable relation identifier.

    Returns:
        Relations keyed by id.
    """
    return {
        relation_id: relation
        for relation in object_collection(case, "relations")
        if isinstance(relation_id := relation.get("id"), str)
    }


def apply_mutation(trace: dict[str, Any], mutation: dict[str, Any]) -> None:
    """Apply one explicit grader-only complete-trace mutation."""
    operation = mutation["op"]
    if operation == "clear_cases":
        trace["cases"] = []
        return
    if operation == "remove_case":
        trace["cases"] = [case for case in trace["cases"] if case["id"] != mutation["case_id"]]
        return
    case = index_cases(trace)[mutation["case_id"]]
    if operation == "set_case_revision":
        case["source_revision"] = mutation["value"]
        return
    if operation == "set_case_field":
        case[mutation["field"]] = mutation["value"]
        return
    if operation == "remove_case_field":
        case.pop(mutation["field"], None)
        return
    if operation == "set_case_id":
        case["id"] = mutation["value"]
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
    if operation == "relabel_transport_ids":
        annotation_ids: dict[str, str] = {}
        for collection in ("unknowns", "contradictions"):
            for index, annotation in enumerate(case[collection]):
                original_id = annotation["id"]
                replacement = f"transport-{collection}-{index}"
                annotation_ids[original_id] = replacement
                annotation["id"] = replacement
                for span_index, span in enumerate(annotation["source_spans"]):
                    span["id"] = f"transport-{collection}-{index}-span-{span_index}"
        for index, relation in enumerate(case["relations"]):
            relation["id"] = f"transport-relation-{index}"
            relation["unknown_ids"] = [annotation_ids[item] for item in relation["unknown_ids"]]
            relation["contradiction_ids"] = [annotation_ids[item] for item in relation["contradiction_ids"]]
            for span_index, span in enumerate(relation["source_spans"]):
                span["id"] = f"transport-relation-{index}-span-{span_index}"
        return
    if operation == "equivalent_format":
        for relation in case["relations"]:
            for field in ("actor", "condition", "action", "effect"):
                if isinstance(relation.get(field), str):
                    relation[field] = f"  {relation[field].upper()}  "
            for consumer in relation["consumers"]:
                consumer["name"] = f"  {consumer['name'].upper()}  "
                consumer["comparison_status"] = consumer["comparison_status"].upper()
        return
    if operation == "reorder_collection":
        case[mutation["collection"]].reverse()
        return
    if operation == "move_relation_to_rejection":
        relation = relation_index(case)[mutation["relation_id"]]
        case["relations"] = [item for item in case["relations"] if item is not relation]
        case["rejected_relations"].append({
            "id": "transport-rejection",
            "source_records": relation.get("source_records", []),
            "reason_code": "no_exact_replayable_source_span",
            "source_unit": relation,
        })
        return
    if operation == "merge_source_units":
        primary = relation_index(case)[mutation["relation_id"]]
        secondary = relation_index(case)[mutation["merge_relation_id"]]
        primary["source_spans"].extend(copy.deepcopy(secondary["source_spans"]))
        case["relations"] = [item for item in case["relations"] if item is not secondary]
        return
    if operation == "set_rejection_reason":
        for item in case[mutation["collection"]]:
            if item["id"] == mutation["id"]:
                item["reason_code"] = mutation["value"]
                return
        raise ValueError("rejection mutation target missing")
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
    elif operation == "append_split_relation":
        split = copy.deepcopy(relation)
        split["id"] = f"transport-split-{relation['id']}"
        case["relations"].append(split)
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


def source_bytes(
    revision: str, path: str, cache: dict[tuple[str, str], bytes], source_replay_root: Path | None
) -> bytes:
    """Load and cache one revision-bound Git source blob.

    Returns:
        Source bytes at the declared revision.
    """
    key = (revision, path)
    if key not in cache:
        if source_replay_root is not None:
            source = source_replay_root / revision / path
            if not source.is_file():
                raise ValueError(f"bundle source unavailable: {source}")
            cache[key] = source.read_bytes()
            return cache[key]
        git = shutil.which("git")
        if git is None:
            raise ValueError("git executable unavailable")
        result = subprocess.run([git, "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True, check=False)
        if result.returncode:
            raise ValueError(result.stderr.decode(errors="replace").strip())
        cache[key] = result.stdout
    return cache[key]


def source_derived_semantic_control() -> dict[str, str]:
    """Prove canonical equivalence from one producer-visible pinned source interval.

    Returns:
        A passing control record when independent source-derived decompositions
        canonicalize together. Blind source-action enforcement is exercised by
        the corpus-level J5 control through ``grade``.
    """
    revision = "e66b55e05e130ea905afaf8d650ec0f5980d08d0"
    repository_path = "plugins/development-harness/agents/review-synthesizer.md"
    source_input = ROOT / "source-replay" / revision / repository_path
    if not source_input.is_file():
        source_input = (
            ROOT
            / "cases/pinned-main-t5/verifier-input/raw"
            / revision
            / "plugins/development-harness/agents/review-synthesizer.blob"
        )
    quote = "Before following any other instruction, first load `dh:synthesize-review-findings` and follow its process step by step."
    content = source_input.read_bytes()
    quote_bytes = quote.encode()
    byte_start = content.index(quote_bytes)
    byte_end = byte_start + len(quote_bytes)
    line_start = content[:byte_start].count(b"\n") + 1
    span = {
        "id": "producer-local-span",
        "repository_path": repository_path,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "line_start": line_start,
        "line_end": line_start,
        "byte_start": byte_start,
        "byte_end_exclusive": byte_end,
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote_bytes).hexdigest(),
    }
    relation = {
        "id": "producer-local-relation",
        "actor": None,
        "condition": "before following any other instruction",
        "action": "load dh:synthesize-review-findings",
        "effect": None,
        "continuations": None,
        "terminal": None,
        "artifacts": [],
        "consumers": [],
        "unknown_ids": [],
        "contradiction_ids": [],
        "source_spans": [span],
    }
    trace: dict[str, Any] = {
        "cases": [
            {
                "id": "source-derived-control",
                "source_revision": revision,
                "record_manifest": [],
                "relations": [relation],
                "rejected_relations": [],
                "rejected_annotations": [],
                "unknowns": [],
                "contradictions": [],
            }
        ]
    }
    equivalent = copy.deepcopy(trace)
    equivalent_case = cast("dict[str, Any]", equivalent["cases"][0])
    equivalent_relation = cast("dict[str, Any]", equivalent_case["relations"][0])
    equivalent_relation["id"] = "independent-local-relation"
    equivalent_span = cast("dict[str, Any]", equivalent_relation["source_spans"][0])
    equivalent_span["id"] = "independent-local-span"
    equivalent_relation["condition"] = " Before   Following Any Other Instruction "
    equivalent_relation["action"] = " LOAD dh:synthesize-review-findings "
    source_unit_manifest = {
        "schema_version": 1,
        "source_units": [
            {
                "case_id": "source-derived-control",
                "source_revision": revision,
                **{key: span[key] for key in span if key != "id"},
            }
        ],
    }
    canonical_trace, trace_failures = canonicalize_trace(trace, source_unit_manifest)
    canonical_equivalent, equivalent_failures = canonicalize_trace(equivalent, source_unit_manifest)
    if trace_failures or equivalent_failures or canonical_trace is None or canonical_equivalent is None:
        raise ValueError("source-derived control failed canonicalization")
    if canonical_trace != canonical_equivalent:
        raise ValueError("source-derived equivalent record did not canonicalize identically")
    return {
        "id": "source-derived-semantic-equivalence",
        "verdict": "pass",
        "independent_source_derived_decompositions": "converged",
        "unsupported_actor_and_boundary": "reference-semantic-only",
        "source_supported_action_control": "grade:source-supported-wrong-action",
    }


def replay_case(case: dict[str, Any], source_replay_root: Path | None) -> list[dict[str, str]]:
    """Validate every required source span in a candidate case.

    Returns:
        Source replay failures.
    """
    failures: list[dict[str, str]] = []
    cache: dict[tuple[str, str], bytes] = {}
    trace_items = [
        *object_collection(case, "relations"),
        *object_collection(case, "unknowns"),
        *object_collection(case, "contradictions"),
    ]
    for item in trace_items:
        spans = item.get("source_spans")
        if not isinstance(spans, list) or not spans:
            failures.append({"id": str(item.get("id")), "reason": "missing_replayable_source_span"})
            continue
        for span in spans:
            if not isinstance(span, dict):
                failures.append({"id": str(item.get("id")), "reason": "invalid_source_span"})
                continue
            span_id = str(span.get("id", item.get("id")))
            path = span.get("repository_path")
            if not isinstance(path, str) or not isinstance(span.get("quote"), str):
                failures.append({"id": span_id, "reason": "incomplete_source_span"})
                continue
            revision = case.get("source_revision")
            if not isinstance(revision, str):
                failures.append({"id": span_id, "reason": "invalid_source_revision"})
                continue
            try:
                content = source_bytes(revision, path, cache, source_replay_root)
            except ValueError as error:
                failures.append({"id": span_id, "reason": f"source_unavailable:{error}"})
                continue
            if span.get("source_sha256") and hashlib.sha256(content).hexdigest() != span["source_sha256"]:
                failures.append({"id": span_id, "reason": "source_sha256_mismatch"})
                continue
            start, end = span.get("byte_start"), span.get("byte_end_exclusive")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or content[start:end].decode(errors="replace") != span["quote"]
            ):
                failures.append({"id": span_id, "reason": "quoted_byte_span_mismatch"})
    return failures


def normalized_source_text(value: str) -> str:
    """Normalize a source-derived semantic token for deterministic comparison.

    Returns:
        Lower-cased, whitespace-normalized source text.
    """
    return " ".join(value.split()).casefold()


def source_supported_table_action(span: dict[str, Any]) -> str | None:
    """Project an action from one complete producer-visible Markdown-table row.

    Returns:
        The action from a complete public table-row rule, otherwise ``None``
        when no public action projection applies.
    """
    quote = span.get("quote")
    if not isinstance(quote, str):
        return None
    quote = quote.strip()
    return SOURCE_DERIVED_TABLE_ACTIONS.get(quote)


def source_derived_semantic_failures(case: dict[str, Any]) -> list[dict[str, str]]:
    """Reject semantic values deterministically projected by public source bytes.

    Returns:
        Producer-visible action projection mismatches. Other semantic payloads
        remain outside blind acceptance unless another public rule projects them.
    """
    failures: list[dict[str, str]] = []
    for relation in object_collection(case, "relations"):
        action = relation.get("action")
        if not isinstance(action, str):
            continue
        expected_actions = {
            expected
            for span in object_collection(relation, "source_spans")
            if (expected := source_supported_table_action(span)) is not None
        }
        if expected_actions and normalized_source_text(action) not in expected_actions:
            failures.append({"id": str(relation.get("id")), "reason": "source_derived_action_mismatch"})
    return failures


def dimension_items(case: dict[str, Any], dimension: str) -> dict[str, str]:
    """Return stable identifiers and signatures for one dimension.

    Returns:
        Item signatures keyed by stable identifier.
    """
    values: dict[str, str] = {}
    for relation in object_collection(case, "relations"):
        relation_id = relation.get("id")
        if not isinstance(relation_id, str):
            continue
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
            for index, consumer in enumerate(object_collection(relation, "consumers")):
                values[f"{relation_id}/consumer-{index}"] = canonical({
                    "name": consumer.get("name"),
                    "comparison_status": consumer.get("comparison_status"),
                })
    if dimension == "uncertainty_contradictions":
        for collection in ("unknowns", "contradictions"):
            for item in object_collection(case, collection):
                item_id = item.get("id")
                if isinstance(item_id, str):
                    values[item_id] = canonical(item)
        for relation in object_collection(case, "relations"):
            relation_id = relation.get("id")
            if not isinstance(relation_id, str):
                continue
            if relation.get("unknown_ids") or relation.get("contradiction_ids"):
                values[f"{relation_id}/annotation-links"] = canonical({
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
            for index, relation_id in enumerate(duplicate_ids(object_collection(candidate_case, "relations")), start=1)
        )
    false.sort()
    return {"dimension": dimension, "correct": correct, "missed": missed, "false": false}


def rejection_failures(reference_case: dict[str, Any], candidate_case: dict[str, Any]) -> list[dict[str, str]]:
    """Report semantic rejection-classification differences independent of order.

    Returns:
        Named differences between canonical rejected-source classifications.
    """
    failures: list[dict[str, str]] = []
    for collection in ("rejected_relations", "rejected_annotations"):
        reference_ids = {item["id"] for item in object_collection(reference_case, collection)}
        candidate_ids = {item["id"] for item in object_collection(candidate_case, collection)}
        if reference_ids != candidate_ids:
            failures.append({"id": reference_case["id"], "reason": f"{collection}_classification_mismatch"})
    return failures


def grade(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    candidate_contract: dict[str, Any],
    source_replay_root: Path | None = None,
) -> dict[str, Any]:
    """Grade all complete-trace dimensions and source replays.

    Returns:
        Per-case grading outcome.
    """
    failures = structural_failures(candidate, candidate_contract)
    canonical_reference, reference_failures = canonicalize_trace(reference)
    canonical_candidate, candidate_failures = canonicalize_trace(candidate)
    canonicalization_failures = [{"source": "reference", **failure} for failure in reference_failures] + [
        {"source": "candidate", **failure} for failure in candidate_failures
    ]
    public_cases = public_case_revisions()
    public_case_ids = sorted(public_cases)
    reference_cases = index_cases(canonical_reference) if canonical_reference is not None else {}
    candidates = index_cases(canonical_candidate) if canonical_candidate is not None else {}
    results: list[dict[str, Any]] = []
    for case_id in public_case_ids:
        reference_case = reference_cases.get(case_id)
        candidate_case = candidates.get(case_id)
        if candidate_case is None:
            results.extend(
                {
                    "case_id": case_id,
                    "dimension": dimension,
                    "correct": [],
                    "missed": sorted(dimension_items(reference_case, dimension)) if reference_case is not None else [],
                    "false": [],
                    "source_replay_failures": [{"id": case_id, "reason": "candidate_case_missing"}],
                    "reference_rejection_failures": [],
                    "blind_acceptance": "fail",
                    "reference_semantic": "fail",
                    "verdict": "fail",
                }
                for dimension in DIMENSIONS
            )
            continue
        blind_failures = replay_case(candidate_case, source_replay_root)
        source_derived_failures = source_derived_semantic_failures(candidate_case)
        blind_failures.extend(source_derived_failures)
        structural = [*failures.get("__corpus__", []), *failures.get(case_id, [])]
        blind_failures.extend({"id": case_id, "reason": failure} for failure in structural)
        blind_failures.extend(
            {"id": case_id, "reason": f"canonicalization:{failure['reason']}"} for failure in candidate_failures
        )
        reference_rejection_failures = (
            rejection_failures(reference_case, candidate_case)
            if reference_case is not None
            else [{"id": case_id, "reason": "reference_case_missing"}]
        )
        for dimension in DIMENSIONS:
            score_row = (
                score(reference_case, candidate_case, dimension)
                if reference_case is not None
                else {"dimension": dimension, "correct": [], "missed": [], "false": []}
            )
            row = {"case_id": case_id, **score_row}
            row["source_replay_failures"] = blind_failures
            row["source_derived_semantic_failures"] = source_derived_failures
            row["reference_rejection_failures"] = reference_rejection_failures
            row["blind_acceptance"] = "pass" if not blind_failures else "fail"
            row["reference_semantic"] = (
                "pass"
                if not row["missed"] and not row["false"] and not reference_rejection_failures and not blind_failures
                else "fail"
            )
            row["verdict"] = row["blind_acceptance"]
            results.append(row)
    return {
        "schema_version": 4,
        "acceptance_threshold": "every case and every dimension has zero producer-visible structural, canonicalization, and source replay failures",
        "reference_semantic_threshold": "every case and every dimension has zero missed, false, reference-rejection, structural, canonicalization, and source replay failures",
        "canonicalization_failures": canonicalization_failures,
        "results": results,
        "blind_acceptance_verdict": (
            "pass"
            if public_case_ids and results and all(row["blind_acceptance"] == "pass" for row in results)
            else "fail"
        ),
        "reference_semantic_verdict": (
            "pass"
            if public_case_ids and results and all(row["reference_semantic"] == "pass" for row in results)
            else "fail"
        ),
        "verdict": "pass"
        if public_case_ids and results and all(row["blind_acceptance"] == "pass" for row in results)
        else "fail",
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
    parser.add_argument("--source-replay-root", type=Path)
    parser.add_argument("--candidate-contract", type=Path, default=ROOT / "blind-candidate-contract.json")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run a complete candidate grade or the control self-check."""
    arguments = parse_args()
    reference = load(arguments.reference)
    candidate_contract = load(arguments.candidate_contract)
    if arguments.candidate:
        output = grade(reference, load(arguments.candidate), candidate_contract, arguments.source_replay_root)
        encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
        if arguments.output:
            arguments.output.write_text(encoded)
        print(encoded, end="")
        return
    controls = load(arguments.candidates)
    control_results: list[dict[str, Any]] = []
    for control in controls["controls"]:
        result = grade(
            reference, hydrate(reference, control["candidate"]), candidate_contract, arguments.source_replay_root
        )
        expected = control["expected"]
        actual = {
            "blind_acceptance": result["blind_acceptance_verdict"],
            "reference_semantic": result["reference_semantic_verdict"],
        }
        if actual != expected:
            raise SystemExit(f"{control['id']}: expected {expected}, got {actual}")
        control_results.append({"id": control["id"], **actual, "grade": result})
    control_results.append(source_derived_semantic_control())
    output = {"status": "self-check-passed", "control_results": control_results}
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
