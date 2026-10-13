# /// script
# requires-python = ">=3.11"
# ///
"""Materialize and validate isolated producer and adjudicator input bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_MANIFEST = ROOT / "verifier-input-manifest.json"
ADJUDICATOR_INPUT = ROOT / "complete-trace-verifier-input.json"


def digest(path: Path) -> str:
    """Return one file's SHA-256 digest.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    """Read a required JSON object.

    Returns:
        Parsed JSON object.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def safe_output(path: Path) -> Path:
    """Reject source-package and pre-existing output directories.

    Returns:
        Absolute safe output directory path.
    """
    output = path.resolve()
    try:
        output.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("bundle output must be outside the tracked corpus package")
    if output.exists():
        raise ValueError(f"bundle output already exists: {output}")
    return output


def write_manifest(output: Path, role: str, files: list[dict[str, str]], boundary: str) -> None:
    """Write the bundle's self-contained allowlist manifest."""
    manifest = {"schema_version": 1, "role": role, "boundary": boundary, "files": files}
    (output / "bundle-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def copy_file(source: Path, output: Path, relative_path: Path, files: list[dict[str, str]]) -> None:
    """Copy one declared bundle input and record its digest."""
    target = output / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    files.append({"path": relative_path.as_posix(), "sha256": digest(target)})


def materialize_producer(output_path: Path) -> Path:
    """Emit a fresh blind-extractor bundle containing only allowlisted inputs.

    Returns:
        Materialized bundle directory.
    """
    output = safe_output(output_path)
    manifest = load(PRODUCER_MANIFEST)
    files: list[dict[str, str]] = []
    for bundle in manifest["case_bundles"]:
        case_id = bundle["case_id"]
        for entry in bundle["files"]:
            source = ROOT / entry["path"]
            if digest(source) != entry["sha256"]:
                raise ValueError(f"declared producer input digest mismatch: {entry['path']}")
            copy_file(source, output, Path("cases") / case_id / source.name, files)
    write_manifest(
        output,
        "blind-extractor",
        files,
        "Contains only source packets and source questions. It excludes complete references, candidate seeds, proposed claims, raw lanes, controls, grading contracts, and receipts.",
    )
    return output


def materialize_adjudicator(output_path: Path, candidate_path: Path) -> Path:
    """Emit an adjudicator bundle after a blind producer supplies a candidate.

    Returns:
        Materialized bundle directory.
    """
    output = safe_output(output_path)
    candidate = candidate_path.resolve()
    if not candidate.is_file():
        raise ValueError(f"candidate does not exist: {candidate}")
    files: list[dict[str, str]] = []
    copy_file(ROOT / "trace-reference.json", output, Path("reference/trace-reference.json"), files)
    copy_file(ROOT / "grading-contract.json", output, Path("contract/grading-contract.json"), files)
    copy_file(ROOT / "scripts/grade_controls.py", output, Path("grader/grade_controls.py"), files)
    copy_file(ADJUDICATOR_INPUT, output, Path("instructions/complete-trace-adjudicator-input.json"), files)
    copy_file(candidate, output, Path("candidate/candidate.json"), files)
    write_manifest(
        output,
        "complete-trace-adjudicator",
        files,
        "Contains the frozen reference, the blind producer's supplied candidate, the grading contract and grader. Source replay is restricted to repository paths and revisions declared by the reference.",
    )
    return output


def validate_bundle(path: Path) -> dict[str, Any]:
    """Fail closed if a materialized bundle has undeclared or altered files.

    Returns:
        Validation summary for the declared bundle.
    """
    root = path.resolve()
    manifest_path = root / "bundle-manifest.json"
    manifest = load(manifest_path)
    files = manifest.get("files")
    if not isinstance(files, list):
        raise TypeError("bundle manifest files must be a list")
    expected = {"bundle-manifest.json"}
    for entry in files:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            raise TypeError("bundle manifest has an invalid file entry")
        relative_path = Path(entry["path"])
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"bundle manifest path escapes output: {entry['path']}")
        expected.add(relative_path.as_posix())
        if digest(root / relative_path) != entry["sha256"]:
            raise ValueError(f"bundle digest mismatch: {entry['path']}")
    actual = {file.relative_to(root).as_posix() for file in root.rglob("*") if file.is_file()}
    if actual != expected:
        raise ValueError(json.dumps({"unexpected": sorted(actual - expected), "missing": sorted(expected - actual)}))
    return {"status": "passed", "role": manifest.get("role"), "files": len(files)}


def main() -> None:
    """Materialize or validate one isolated verifier bundle."""
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--producer-output", type=Path)
    mode.add_argument("--adjudicator-output", type=Path)
    mode.add_argument("--check", type=Path)
    parser.add_argument("--candidate", type=Path)
    arguments = parser.parse_args()
    if arguments.producer_output:
        if arguments.candidate:
            raise SystemExit("--candidate is only valid with --adjudicator-output")
        result = {"status": "materialized", "path": str(materialize_producer(arguments.producer_output))}
    elif arguments.adjudicator_output:
        if arguments.candidate is None:
            raise SystemExit("--adjudicator-output requires --candidate")
        result = {
            "status": "materialized",
            "path": str(materialize_adjudicator(arguments.adjudicator_output, arguments.candidate)),
        }
    else:
        result = validate_bundle(arguments.check)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
