# /// script
# requires-python = ">=3.11"
# ///
"""Regenerate and validate package-byte integrity without rewriting freeze receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_RECORDS = {
    "pinned-main-t5/review-a": "cases/pinned-main-t5/records/review-a",
    "pinned-main-t5/review-b": "cases/pinned-main-t5/records/review-b",
    "pinned-4095-source-check/review-a": "cases/pinned-4095-source-check/records/review-a",
    "pinned-4095-source-check/review-b": "cases/pinned-4095-source-check/records/review-b",
    "grooming-nested-references/actor-a-final": "cases/grooming-main/records/actor-a/final",
    "grooming-nested-references/actor-b-initial": "cases/grooming-main/records/actor-b/initial",
    "grooming-nested-references/actor-b-attempt-2": "cases/grooming-main/records/actor-b/attempt-2",
    "grooming-nested-references/actor-b-attempt-3": "cases/grooming-main/records/actor-b/attempt-3",
    "prose-task-profile-start-task/handoff-a": "cases/prose-task-profile-start-task/records/handoff-a",
    "prose-task-profile-start-task/handoff-b": "cases/prose-task-profile-start-task/records/handoff-b",
}
INTEGRITY_DOCUMENT = "record-integrity.json"


def digest(path: Path) -> str:
    """Return the SHA-256 digest of one tracked package file.

    Returns:
        Lowercase hexadecimal digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_digests() -> dict[str, str]:
    """Hash every package artifact except the self-describing integrity document.

    Returns:
        Package-relative artifact digests.
    """
    return {
        str(path.relative_to(ROOT)): digest(path)
        for path in sorted(ROOT.rglob("*"))
        if path.is_file()
        and path.relative_to(ROOT).as_posix() != INTEGRITY_DOCUMENT
        and "__pycache__" not in path.parts
    }


def package_root(artifacts: dict[str, str]) -> str:
    """Hash a canonical non-self-referential package artifact map.

    Returns:
        Package-root digest.
    """
    return hashlib.sha256(json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def inventory() -> dict[str, object]:
    """Build the final-byte inventory without mutating freeze receipts.

    Returns:
        Package integrity document.
    """
    records: dict[str, object] = {}
    for record_id, relative_directory in PRIMARY_RECORDS.items():
        directory = ROOT / relative_directory
        package_files = {
            str(path.relative_to(directory)): digest(path) for path in sorted(directory.iterdir()) if path.is_file()
        }
        freeze_receipts = {name: value for name, value in package_files.items() if name.startswith("freeze")}
        records[record_id] = {
            "path": relative_directory,
            "package_byte_digests": package_files,
            "immutable_freeze_receipt_provenance": {
                "receipt_package_byte_digests": freeze_receipts,
                "note": "These receipt-file digests identify immutable historical provenance. They are not assertions that current package payload bytes equal freeze-time payload digests.",
            },
        }
    return {
        "schema_version": 3,
        "status": "final-package-artifact-root-and-primary-record-digests",
        "algorithm": "sha256",
        "scope": "Every package artifact consumed or declared by the corpus after final writes and formatting. Immutable freeze receipts remain separate historical provenance.",
        "non_self_referential_root_strategy": "record-integrity.json is intentionally excluded from artifact_digests. package_root_sha256 hashes the complete sorted digest map of every other package artifact, including manifests, receipts, blind/adjudicator inputs, controls, scripts, references, and records.",
        "artifact_digests": artifact_digests(),
        "package_root_sha256": package_root(artifact_digests()),
        "primary_record_count": len(records),
        "records": records,
    }


def validate(document: dict[str, object]) -> list[str]:
    """Return every mismatched package-byte digest.

    Returns:
        Validation failure identifiers.
    """
    failures: list[str] = []
    if document.get("primary_record_count") != len(PRIMARY_RECORDS):
        failures.append("primary_record_count")
    records = document.get("records", {})
    if not isinstance(records, dict):
        return ["records_not_object"]
    for record_id in PRIMARY_RECORDS:
        entry = records.get(record_id)
        if not isinstance(entry, dict):
            failures.append(f"missing_record:{record_id}")
            continue
        directory = ROOT / str(entry["path"])
        for relative_path, expected in entry["package_byte_digests"].items():
            if digest(directory / relative_path) != expected:
                failures.append(f"record_digest:{record_id}/{relative_path}")
    artifacts = document.get("artifact_digests")
    if not isinstance(artifacts, dict):
        return [*failures, "artifact_digests_not_object"]
    current = artifact_digests()
    if artifacts != current:
        failures.append("artifact_graph_mismatch")
    if document.get("package_root_sha256") != package_root(current):
        failures.append("package_root_sha256")
    return failures


def validate_bundle(root: Path, manifest_path: Path) -> list[str]:
    """Validate a materialized bundle's closed file and digest inventory.

    Returns:
        All detected integrity failures.
    """
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = document.get("files")
    if not isinstance(entries, list):
        return ["bundle_files_not_list"]
    expected = {manifest_path.name}
    failures: list[str] = []
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            failures.append("bundle_invalid_entry")
            continue
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            failures.append(f"bundle_path_escape:{entry['path']}")
            continue
        expected.add(relative.as_posix())
        source = root / relative
        if not source.is_file():
            failures.append(f"bundle_missing:{entry['path']}")
        elif digest(source) != entry["sha256"]:
            failures.append(f"bundle_digest:{entry['path']}")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    failures.extend(f"bundle_unexpected:{path}" for path in sorted(actual - expected))
    failures.extend(f"bundle_missing:{path}" for path in sorted(expected - actual))
    return failures


def main() -> None:
    """Write and/or validate the tracked-byte integrity inventory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--bundle-root", type=Path)
    parser.add_argument("--bundle-manifest", type=Path)
    parser.add_argument("--validate-bundle", action="store_true")
    arguments = parser.parse_args()
    if arguments.validate_bundle:
        if arguments.write or arguments.validate or arguments.bundle_root is None or arguments.bundle_manifest is None:
            raise SystemExit("--validate-bundle requires --bundle-root and --bundle-manifest only")
        root = arguments.bundle_root.resolve()
        manifest = (root / arguments.bundle_manifest).resolve()
        try:
            manifest.relative_to(root)
        except ValueError as error:
            raise SystemExit("bundle manifest must be inside bundle root") from error
        failures = validate_bundle(root, manifest)
        if failures:
            raise SystemExit(json.dumps({"status": "failed", "failures": failures}, indent=2))
        print(json.dumps({"status": "passed", "files": len(list(root.rglob("*")))}))
        return
    target = ROOT / "record-integrity.json"
    if arguments.write:
        target.write_text(json.dumps(inventory(), indent=2) + "\n")
    if arguments.validate:
        failures = validate(json.loads(target.read_text()))
        if failures:
            raise SystemExit(json.dumps({"status": "failed", "failures": failures}, indent=2))
        print(json.dumps({"status": "passed", "records": len(PRIMARY_RECORDS), "artifacts": len(artifact_digests())}))


if __name__ == "__main__":
    main()
