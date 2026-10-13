# /// script
# requires-python = ">=3.11"
# ///
"""Validate the blind extractor allowlist and receipt-only claim partition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SUFFIXES = (
    "/verifier-input/source-packet.json",
    "/verifier-input/source-question.md",
    "/verifier-input/handoff-a-source-packet.json",
    "/verifier-input/handoff-a-source-question.md",
)


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


def main() -> None:
    """Check that blind and historical inputs are disjoint."""
    manifest: dict[str, Any] = json.loads((ROOT / "verifier-input-manifest.json").read_text())
    failures: list[str] = []
    failures.extend(candidate_contract_failures(manifest))
    blind_paths: set[str] = set()
    for bundle in manifest["case_bundles"]:
        for file in bundle["files"]:
            path = file["path"]
            if not path.endswith(ALLOWED_SUFFIXES):
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
