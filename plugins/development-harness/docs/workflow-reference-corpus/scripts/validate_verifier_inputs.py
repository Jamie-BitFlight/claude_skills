# /// script
# requires-python = ">=3.11"
# ///
"""Validate the blind extractor allowlist and receipt-only claim partition."""

from __future__ import annotations

import hashlib
import json
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
candidate_schema_failures = cast(
    "Callable[[dict[str, Any], dict[str, Any]], list[dict[str, str]]]",
    runpy.run_path(str(Path(__file__).with_name("candidate_schema.py")))["candidate_schema_failures"],
)
ALLOWED_SUFFIXES = (
    "/verifier-input/source-packet.json",
    "/verifier-input/source-question.md",
    "/verifier-input/handoff-a-source-packet.json",
    "/verifier-input/handoff-a-source-question.md",
)
RAW_SOURCE_MARKER = "/verifier-input/raw/"


def digest(path: Path) -> str:
    """Return the SHA-256 digest of one bundle file.

    Returns:
        Lowercase hexadecimal digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_contract_failures(manifest: dict[str, Any]) -> list[str]:
    """Return failures for the non-gold producer candidate contract.

    Returns:
        Zero or more contract-validation failure identifiers.
    """
    candidate_contract = manifest.get("candidate_contract")
    if not isinstance(candidate_contract, dict):
        return ["candidate_contract_missing"]
    path = candidate_contract.get("path")
    expected_digest = candidate_contract.get("sha256")
    if not isinstance(path, str) or not isinstance(expected_digest, str):
        return ["candidate_contract_invalid"]
    return [] if digest(ROOT / path) == expected_digest else ["candidate_contract_digest"]


def producer_public_file_failures(manifest: dict[str, Any]) -> list[str]:
    """Validate every producer-visible canonicalization input by digest.

    Returns:
        Digest or shape failures for the public producer contract files.
    """
    files = manifest.get("producer_public_files")
    if not isinstance(files, list):
        return ["producer_public_files_missing"]
    failures: list[str] = []
    for entry in files:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            failures.append("producer_public_file_invalid")
            continue
        path = ROOT / entry["path"]
        if not path.is_file() or digest(path) != entry["sha256"]:
            failures.append(f"producer_public_file_digest:{entry['path']}")
    return failures


def regression_fixture_failures() -> list[str]:
    """Verify the retained malformed independent candidate stays byte-exact and invalid.

    Returns:
        Fixture-integrity or expected-schema-failure identifiers.
    """
    controls: dict[str, Any] = json.loads((ROOT / "controls/negative-controls.json").read_text())
    fixtures = controls.get("independent_regression_fixtures")
    if not isinstance(fixtures, list) or len(fixtures) != 1 or not isinstance(fixtures[0], dict):
        return ["independent_fixture_metadata"]
    fixture = fixtures[0]
    path = fixture.get("path")
    expected_digest = fixture.get("sha256")
    expected_paths = fixture.get("expected_schema_failure_paths")
    if not isinstance(path, str) or not isinstance(expected_digest, str) or not isinstance(expected_paths, list):
        return ["independent_fixture_fields"]
    fixture_path = ROOT / "controls" / path.removeprefix("./")
    if not fixture_path.is_file() or digest(fixture_path) != expected_digest:
        return ["independent_fixture_digest"]
    contract: dict[str, Any] = json.loads((ROOT / "blind-candidate-contract.json").read_text())
    candidate: dict[str, Any] = json.loads(fixture_path.read_text())
    actual_paths = {failure["path"] for failure in candidate_schema_failures(candidate, contract)}
    return [f"independent_fixture_missing_failure:{path}" for path in expected_paths if path not in actual_paths]


def main() -> None:
    """Check that blind and historical inputs are disjoint."""
    manifest: dict[str, Any] = json.loads((ROOT / "verifier-input-manifest.json").read_text())
    failures: list[str] = []
    failures.extend(candidate_contract_failures(manifest))
    failures.extend(producer_public_file_failures(manifest))
    failures.extend(regression_fixture_failures())
    blind_paths: set[str] = set()
    for bundle in manifest["case_bundles"]:
        for file in bundle["files"]:
            path = file["path"]
            if not path.endswith(ALLOWED_SUFFIXES) and RAW_SOURCE_MARKER not in path:
                failures.append(f"blind_allowlist:{path}")
            if "proposed-claims.json" in path:
                failures.append(f"historical_claim_in_blind_bundle:{path}")
            if digest(ROOT / path) != file["sha256"]:
                failures.append(f"blind_digest:{path}")
            blind_paths.add(path)
    for file in manifest["historical_claims_receipt_only"]:
        path = file["path"]
        if path in blind_paths:
            failures.append(f"historical_claim_not_partitioned:{path}")
        if not path.endswith("/proposed-claims.json"):
            failures.append(f"unexpected_receipt_only_path:{path}")
        if digest(ROOT / path) != file["sha256"]:
            failures.append(f"historical_digest:{path}")
    if failures:
        raise SystemExit(json.dumps({"status": "failed", "failures": failures}, indent=2))
    print(
        json.dumps({
            "status": "passed",
            "blind_bundle_files": len(blind_paths),
            "receipt_only_claim_files": len(manifest["historical_claims_receipt_only"]),
        })
    )


if __name__ == "__main__":
    main()
