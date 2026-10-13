# /// script
# requires-python = ">=3.11"
# ///
# ruff: file-ignore[complex-structure, too-many-branches]
"""Materialize and validate isolated producer and adjudicator input bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_MANIFEST = ROOT / "verifier-input-manifest.json"
ADJUDICATOR_INPUT = ROOT / "complete-trace-verifier-input.json"
CANDIDATE_CONTRACT = ROOT / "blind-candidate-contract.json"


def digest(path: Path) -> str:
    """Return one file's SHA-256 digest."""
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


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one canonical JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_output(path: Path) -> Path:
    """Reject source-package and pre-existing output directories.

    Returns:
        Absolute output directory path that does not yet exist.
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
    write_json(
        output / "bundle-manifest.json", {"schema_version": 2, "role": role, "boundary": boundary, "files": files}
    )


def copy_file(source: Path, output: Path, relative_path: Path, files: list[dict[str, str]]) -> None:
    """Copy one declared bundle input and record its digest."""
    target = output / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    files.append({"path": relative_path.as_posix(), "sha256": digest(target)})


def copy_bytes(content: bytes, output: Path, relative_path: Path, files: list[dict[str, str]]) -> None:
    """Write immutable bytes into a bundle and record their digest."""
    target = output / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    files.append({"path": relative_path.as_posix(), "sha256": digest(target)})


def source_replay_entries(reference: dict[str, Any]) -> list[tuple[str, str, str]]:
    """List unique revision-bound files needed to replay all reference spans.

    Returns:
        Revision, repository path, and source digest tuples.
    """
    entries: dict[tuple[str, str], str] = {}
    for case in reference.get("cases", []):
        if not isinstance(case, dict) or not isinstance(case.get("source_revision"), str):
            raise TypeError("reference has a case without source_revision")
        for collection in ("relations", "unknowns", "contradictions"):
            for item in case.get(collection, []):
                if not isinstance(item, dict):
                    continue
                for span in item.get("source_spans", []):
                    if not isinstance(span, dict):
                        continue
                    path = span.get("repository_path")
                    source_sha256 = span.get("source_sha256")
                    if not isinstance(path, str) or not isinstance(source_sha256, str):
                        raise TypeError("reference has an incomplete replay source span")
                    key = (case["source_revision"], path)
                    prior = entries.get(key)
                    if prior is not None and prior != source_sha256:
                        raise ValueError(f"reference disagrees on replay source digest: {path}")
                    entries[key] = source_sha256
    return [(revision, path, entries[revision, path]) for revision, path in sorted(entries)]


def git_source_bytes(revision: str, path: str) -> bytes:
    """Read one source file at a declared immutable Git revision.

    Returns:
        Exact source bytes at the requested revision.
    """
    git = shutil.which("git")
    if git is None:
        raise ValueError("git executable unavailable")
    result = subprocess.run([git, "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def copy_source_replay(reference: dict[str, Any], output: Path, files: list[dict[str, str]]) -> None:
    """Materialize all source blobs necessary for offline byte-span replay."""
    for revision, repository_path, expected_digest in source_replay_entries(reference):
        content = git_source_bytes(revision, repository_path)
        if hashlib.sha256(content).hexdigest() != expected_digest:
            raise ValueError(f"reference replay source digest mismatch: {revision}:{repository_path}")
        copy_bytes(content, output, Path("source-replay") / revision / repository_path, files)


def write_commands(output: Path, role: str, files: list[dict[str, str]]) -> None:
    """Declare bundle-relative deterministic commands and their dependencies."""
    commands: list[dict[str, Any]] = []
    if role == "complete-trace-adjudicator":
        commands = [
            {
                "id": "bundle-integrity",
                "argv": [
                    "uv",
                    "run",
                    "--script",
                    "scripts/record_integrity.py",
                    "--bundle-root",
                    ".",
                    "--bundle-manifest",
                    "bundle-manifest.json",
                    "--validate-bundle",
                ],
                "dependencies": ["scripts/record_integrity.py", "bundle-manifest.json"],
            },
            {
                "id": "candidate-grade",
                "argv": [
                    "uv",
                    "run",
                    "--script",
                    "scripts/grade_controls.py",
                    "--reference",
                    "trace-reference.json",
                    "--candidate",
                    "candidate.json",
                    "--source-replay-root",
                    "source-replay",
                ],
                "dependencies": [
                    "scripts/grade_controls.py",
                    "trace-reference.json",
                    "candidate.json",
                    "source-replay",
                ],
            },
            {
                "id": "control-self-check",
                "argv": [
                    "uv",
                    "run",
                    "--script",
                    "scripts/grade_controls.py",
                    "--reference",
                    "trace-reference.json",
                    "--candidates",
                    "controls/control-candidates.json",
                    "--source-replay-root",
                    "source-replay",
                    "--self-check",
                ],
                "dependencies": [
                    "scripts/grade_controls.py",
                    "trace-reference.json",
                    "controls/control-candidates.json",
                    "source-replay",
                ],
            },
        ]
    write_json(output / "bundle-commands.json", {"schema_version": 1, "role": role, "commands": commands})
    files.append({"path": "bundle-commands.json", "sha256": digest(output / "bundle-commands.json")})


def materialize_producer(output_path: Path) -> Path:
    """Emit a fresh blind-extractor bundle containing only allowlisted inputs.

    Returns:
        Materialized producer-bundle directory.
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
    contract_digest = manifest.get("candidate_contract", {}).get("sha256")
    if not isinstance(contract_digest, str) or digest(CANDIDATE_CONTRACT) != contract_digest:
        raise ValueError("declared blind candidate contract digest mismatch")
    copy_file(CANDIDATE_CONTRACT, output, Path("blind-candidate-contract.json"), files)
    write_commands(output, "blind-extractor", files)
    write_manifest(
        output,
        "blind-extractor",
        files,
        "Contains only source packets, source questions, and a non-gold candidate schema. It excludes complete references, candidate seeds, proposed claims, raw lanes, controls, grading contracts, and receipts.",
    )
    return output


def materialize_adjudicator(output_path: Path, candidate_path: Path) -> Path:
    """Emit a self-contained adjudicator bundle after blind extraction.

    Returns:
        Materialized adjudicator-bundle directory.
    """
    output = safe_output(output_path)
    candidate = candidate_path.resolve()
    if not candidate.is_file():
        raise ValueError(f"candidate does not exist: {candidate}")
    files: list[dict[str, str]] = []
    reference = load(ROOT / "trace-reference.json")
    for source, destination in (
        (ROOT / "trace-reference.json", Path("trace-reference.json")),
        (ROOT / "grading-contract.json", Path("grading-contract.json")),
        (ROOT / "controls/control-candidates.json", Path("controls/control-candidates.json")),
        (ROOT / "controls/negative-controls.json", Path("controls/negative-controls.json")),
        (ROOT / "scripts/grade_controls.py", Path("scripts/grade_controls.py")),
        (ROOT / "scripts/record_integrity.py", Path("scripts/record_integrity.py")),
        (ROOT / "record-integrity.json", Path("record-integrity.json")),
        (ADJUDICATOR_INPUT, Path("instructions/complete-trace-adjudicator-input.json")),
        (candidate, Path("candidate.json")),
    ):
        copy_file(source, output, destination, files)
    copy_source_replay(reference, output, files)
    write_commands(output, "complete-trace-adjudicator", files)
    write_manifest(
        output,
        "complete-trace-adjudicator",
        files,
        "Contains the frozen reference, supplied candidate, grading controls, integrity verifier, and every revision-bound source blob needed for offline replay. It excludes raw lanes, historical claim-projection receipts, and source-package paths.",
    )
    return output


def validate_bundle(path: Path) -> dict[str, Any]:
    """Fail closed if a materialized bundle has altered files or failed checks.

    Returns:
        Closed-inventory and declared-command validation summary.
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
    commands_document = load(root / "bundle-commands.json")
    commands = commands_document.get("commands")
    if not isinstance(commands, list):
        raise TypeError("bundle commands must be a list")
    results: list[dict[str, Any]] = []
    for command in commands:
        if not isinstance(command, dict) or not isinstance(command.get("id"), str):
            raise TypeError("bundle command is invalid")
        argv = command.get("argv")
        dependencies = command.get("dependencies")
        if not isinstance(argv, list) or not all(isinstance(value, str) for value in argv):
            raise TypeError(f"bundle command argv is invalid: {command['id']}")
        if not isinstance(dependencies, list) or not all(isinstance(value, str) for value in dependencies):
            raise TypeError(f"bundle command dependencies are invalid: {command['id']}")
        for dependency in dependencies:
            if not (root / dependency).exists():
                raise ValueError(f"bundle command dependency missing: {command['id']}:{dependency}")
        completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise ValueError(
                json.dumps({
                    "bundle_command_failed": command["id"],
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                })
            )
        result: dict[str, Any] = {"id": command["id"], "exit_code": completed.returncode}
        try:
            payload = json.loads(completed.stdout)
            if isinstance(payload, dict) and isinstance(payload.get("verdict"), str):
                result["verdict"] = payload["verdict"]
        except json.JSONDecodeError:
            pass
        results.append(result)
    return {"status": "passed", "role": manifest.get("role"), "files": len(files), "commands": results}


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
