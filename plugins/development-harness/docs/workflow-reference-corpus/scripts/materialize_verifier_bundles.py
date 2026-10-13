# /// script
# requires-python = ">=3.11"
# ///
# ruff: file-ignore[complex-structure, too-many-branches, too-many-locals, too-many-statements]
"""Materialize and validate isolated producer and adjudicator input bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path, PureWindowsPath
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_MANIFEST = ROOT / "verifier-input-manifest.json"
ADJUDICATOR_INPUT = ROOT / "complete-trace-verifier-input.json"
CANDIDATE_CONTRACT = ROOT / "blind-candidate-contract.json"
CANONICAL_IR = ROOT / "canonical-source-ir.json"
RECORD_MANIFEST = ROOT / "record-manifest.json"
SOURCE_UNIT_MANIFEST = ROOT / "source-unit-manifest.json"
ADJUDICATOR_PACKET_PROJECTION_MANIFEST = "adjudicator-packet-projection-manifest.json"
HOST_LOCAL_PROVENANCE_REDACTION = "<host-local-path-redacted>"
candidate_schema_failures = cast(
    "Callable[[dict[str, Any], dict[str, Any]], list[dict[str, str]]]",
    runpy.run_path(str(Path(__file__).with_name("candidate_schema.py")))["candidate_schema_failures"],
)


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


def copy_producer_public_files(manifest: dict[str, Any], output: Path, files: list[dict[str, str]]) -> None:
    """Copy every digest-bound non-gold producer contract artifact."""
    public_files = manifest.get("producer_public_files")
    if not isinstance(public_files, list):
        raise TypeError("producer_public_files must be a list")
    for entry in public_files:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            raise TypeError("producer public file entry is invalid")
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"producer public file escapes corpus: {entry['path']}")
        source = ROOT / relative
        if digest(source) != entry["sha256"]:
            raise ValueError(f"declared producer public file digest mismatch: {entry['path']}")
        copy_file(source, output, relative, files)


def copy_bytes(content: bytes, output: Path, relative_path: Path, files: list[dict[str, str]]) -> None:
    """Write immutable bytes into a bundle and record their digest."""
    target = output / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    files.append({"path": relative_path.as_posix(), "sha256": digest(target)})


def producer_destination(case_id: str, source_path: str) -> Path:
    """Map a declared verifier-input file to its producer-bundle destination.

    Returns:
        A case-scoped path preserving the file's location beneath verifier-input.
    """
    parts = Path(source_path).parts
    try:
        input_index = parts.index("verifier-input")
    except ValueError as error:
        raise ValueError(f"producer input is outside verifier-input: {source_path}") from error
    return Path("cases") / case_id / Path(*parts[input_index + 1 :])


def packet_source_entries(packet: dict[str, Any]) -> set[tuple[str, str]]:
    """Extract revision-pinned repository sources explicitly listed by one packet.

    Returns:
        Repository-relative paths and SHA-256 digests for public source inputs.
    """
    sources: set[tuple[str, str]] = set()
    for collection, digest_field in (
        (packet.get("cited_sources"), "sha256"),
        (packet.get("sources"), "raw_sha256"),
        (packet.get("quoted_source_files"), "sha256"),
        (packet.get("committed_sources"), "sha256"),
    ):
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            digest_value = entry.get(digest_field)
            relative = Path(path) if isinstance(path, str) else None
            if (
                relative is not None
                and not relative.is_absolute()
                and ".." not in relative.parts
                and isinstance(digest_value, str)
            ):
                sources.add((relative.as_posix(), digest_value))
    return sources


def copy_producer_sources(manifest: dict[str, Any], output: Path, files: list[dict[str, str]]) -> None:
    """Materialize every packet-declared source file with a digest-bound inventory."""
    entries: list[dict[str, str]] = []
    destinations: dict[Path, str] = {}
    for bundle in manifest["case_bundles"]:
        case_id = bundle["case_id"]
        revision = bundle["source_revision"]
        for file in bundle["files"]:
            if not file["path"].endswith("source-packet.json"):
                continue
            packet = load(ROOT / file["path"])
            for repository_path, expected_digest in sorted(packet_source_entries(packet)):
                content = git_source_bytes(revision, repository_path)
                actual_digest = hashlib.sha256(content).hexdigest()
                if actual_digest != expected_digest:
                    raise ValueError(f"packet source digest mismatch: {case_id}:{repository_path}")
                destination = Path("source-inputs") / case_id / revision / repository_path
                prior = destinations.get(destination)
                if prior is not None and prior != actual_digest:
                    raise ValueError(f"conflicting producer source digest: {destination}")
                if prior is None:
                    copy_bytes(content, output, destination, files)
                    destinations[destination] = actual_digest
                entries.append({
                    "case_id": case_id,
                    "source_revision": revision,
                    "repository_path": repository_path,
                    "sha256": actual_digest,
                    "bundle_path": destination.as_posix(),
                })
    write_json(output / "producer-source-manifest.json", {"schema_version": 1, "sources": entries})
    files.append({"path": "producer-source-manifest.json", "sha256": digest(output / "producer-source-manifest.json")})


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


def host_local_provenance(value: object) -> bool:
    """Return whether a provenance value is an absolute host-local path."""
    return isinstance(value, str) and (value.startswith("/") or PureWindowsPath(value).is_absolute())


def portable_packet_value(value: object) -> tuple[object, int]:
    """Recursively redact absolute host-local packet provenance values.

    Returns:
        The portable projection and its count of redacted values.
    """
    if host_local_provenance(value):
        return HOST_LOCAL_PROVENANCE_REDACTION, 1
    if isinstance(value, list):
        projected = [portable_packet_value(item) for item in value]
        return [item for item, _count in projected], sum(count for _item, count in projected)
    if not isinstance(value, dict):
        return value, 0
    output: dict[str, object] = {}
    redacted = 0
    for key, item in value.items():
        output[key], item_redacted = portable_packet_value(item)
        redacted += item_redacted
    return output, redacted


def packet_projection_failures(value: object) -> list[str]:
    """Return host-local provenance values that remain in a projected packet."""
    if host_local_provenance(value):
        return ["absolute_host_local_path"]
    if isinstance(value, list):
        return [failure for item in value for failure in packet_projection_failures(item)]
    if not isinstance(value, dict):
        return []
    return [failure for item in value.values() for failure in packet_projection_failures(item)]


def copy_adjudicator_source_packets(manifest: dict[str, Any], output: Path, files: list[dict[str, str]]) -> None:
    """Copy portable packet projections the bundle-local grader resolves through the producer manifest."""
    projections: list[dict[str, Any]] = []
    for bundle in manifest["case_bundles"]:
        for entry in bundle["files"]:
            source_path = entry["path"]
            if not source_path.endswith("source-packet.json"):
                continue
            source = ROOT / source_path
            if digest(source) != entry["sha256"]:
                raise ValueError(f"declared adjudicator packet digest mismatch: {source_path}")
            projection, redacted = portable_packet_value(load(source))
            if not isinstance(projection, dict):
                raise TypeError(f"adjudicator packet projection is not an object: {source_path}")
            content = (json.dumps(projection, indent=2, sort_keys=True) + "\n").encode()
            copy_bytes(content, output, Path(source_path), files)
            projections.append({
                "path": source_path,
                "source_sha256": entry["sha256"],
                "projection_sha256": hashlib.sha256(content).hexdigest(),
                "redacted_host_local_provenance_values": redacted,
            })
    write_json(
        output / ADJUDICATOR_PACKET_PROJECTION_MANIFEST,
        {
            "schema_version": 1,
            "purpose": "Bind portable adjudicator packet projections to their canonical corpus packet digests while removing host-local absolute provenance paths.",
            "redaction": {"all_absolute_host_local_path_strings": True, "replacement": HOST_LOCAL_PROVENANCE_REDACTION},
            "packets": projections,
        },
    )
    files.append({
        "path": ADJUDICATOR_PACKET_PROJECTION_MANIFEST,
        "sha256": digest(output / ADJUDICATOR_PACKET_PROJECTION_MANIFEST),
    })


def adjudicator_packet_projection_failures(root: Path) -> list[str]:
    """Validate canonical-digest bindings and redaction in portable packet projections.

    Returns:
        Projection-integrity and retained-host-path failures.
    """
    document = load(root / ADJUDICATOR_PACKET_PROJECTION_MANIFEST)
    packets = document.get("packets")
    if not isinstance(packets, list):
        return ["packet_projection_manifest_invalid"]
    source_digests = {
        entry["path"]: entry["sha256"]
        for bundle in load(root / "verifier-input-manifest.json")["case_bundles"]
        for entry in bundle["files"]
        if entry["path"].endswith("source-packet.json")
    }
    failures: list[str] = []
    for entry in packets:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            failures.append("packet_projection_entry_invalid")
            continue
        path = entry["path"]
        packet_path = root / path
        if entry.get("source_sha256") != source_digests.get(path):
            failures.append(f"packet_projection_source_digest:{path}")
        if not packet_path.is_file() or digest(packet_path) != entry.get("projection_sha256"):
            failures.append(f"packet_projection_digest:{path}")
            continue
        failures.extend(
            f"packet_projection_host_local_path:{path}:{field}"
            for field in packet_projection_failures(load(packet_path))
        )
    if set(source_digests) != {entry.get("path") for entry in packets if isinstance(entry, dict)}:
        failures.append("packet_projection_inventory")
    return failures


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
                    "verifier-input-manifest.json",
                    "source-unit-manifest.json",
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
                    "verifier-input-manifest.json",
                    "source-unit-manifest.json",
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
            copy_file(source, output, producer_destination(case_id, entry["path"]), files)
    contract_digest = manifest.get("candidate_contract", {}).get("sha256")
    if not isinstance(contract_digest, str) or digest(CANDIDATE_CONTRACT) != contract_digest:
        raise ValueError("declared blind candidate contract digest mismatch")
    copy_file(CANDIDATE_CONTRACT, output, Path("blind-candidate-contract.json"), files)
    copy_file(PRODUCER_MANIFEST, output, Path("verifier-input-manifest.json"), files)
    copy_producer_public_files(manifest, output, files)
    copy_file(ROOT / "scripts/candidate_schema.py", output, Path("scripts/candidate_schema.py"), files)
    copy_file(ROOT / "scripts/validate_candidate.py", output, Path("scripts/validate_candidate.py"), files)
    copy_producer_sources(manifest, output, files)
    write_commands(output, "blind-extractor", files)
    write_manifest(
        output,
        "blind-extractor",
        files,
        "Contains only source packets, source questions, the manifest declaring revision-pinned raw source blobs, public record provenance, and a non-gold canonicalization contract. It excludes complete references, candidate seeds, proposed claims, raw lane traces, controls, grading contracts, and receipts.",
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
        (PRODUCER_MANIFEST, Path("verifier-input-manifest.json")),
        (CANDIDATE_CONTRACT, Path("blind-candidate-contract.json")),
        (CANONICAL_IR, Path("canonical-source-ir.json")),
        (RECORD_MANIFEST, Path("record-manifest.json")),
        (SOURCE_UNIT_MANIFEST, Path("source-unit-manifest.json")),
        (ROOT / "scripts/canonical_ir.py", Path("scripts/canonical_ir.py")),
        (ROOT / "scripts/candidate_schema.py", Path("scripts/candidate_schema.py")),
        (ROOT / "scripts/grade_controls.py", Path("scripts/grade_controls.py")),
        (ROOT / "scripts/record_integrity.py", Path("scripts/record_integrity.py")),
        (ROOT / "record-integrity.json", Path("record-integrity.json")),
        (ADJUDICATOR_INPUT, Path("instructions/complete-trace-adjudicator-input.json")),
        (candidate, Path("candidate.json")),
    ):
        copy_file(source, output, destination, files)
    copy_adjudicator_source_packets(load(PRODUCER_MANIFEST), output, files)
    copy_source_replay(reference, output, files)
    write_commands(output, "complete-trace-adjudicator", files)
    write_manifest(
        output,
        "complete-trace-adjudicator",
        files,
        "Contains the frozen reference, supplied candidate, grading controls, integrity verifier, and every revision-bound source blob needed for offline replay. It excludes raw lanes, historical claim-projection receipts, and source-package paths.",
    )
    return output


def candidate_validation_result(root: Path, role: str, supplied_candidate: Path | None) -> dict[str, Any] | None:
    """Return a structured schema failure for a supplied or bundled candidate."""
    if role == "blind-extractor" and supplied_candidate is None:
        return None
    candidate_path = root / "candidate.json" if role == "complete-trace-adjudicator" else supplied_candidate
    if candidate_path is None or not candidate_path.is_file():
        return {"status": "failed", "candidate_schema_failures": [{"path": "candidate", "reason": "missing_file"}]}
    if role == "complete-trace-adjudicator" and supplied_candidate is not None:
        if not supplied_candidate.is_file():
            return {
                "status": "failed",
                "candidate_schema_failures": [{"path": "candidate", "reason": "missing_supplied_file"}],
            }
        if digest(candidate_path) != digest(supplied_candidate):
            return {
                "status": "failed",
                "candidate_schema_failures": [{"path": "candidate", "reason": "supplied_digest_mismatch"}],
            }
    contract = load(root / "blind-candidate-contract.json")
    failures = candidate_schema_failures(load(candidate_path), contract)
    if failures:
        return {"status": "failed", "candidate_schema_failures": failures}
    return None


def validate_bundle(path: Path, supplied_candidate: Path | None = None) -> dict[str, Any]:
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
    role = manifest.get("role")
    if not isinstance(role, str):
        raise TypeError("bundle manifest role must be a string")
    if role == "complete-trace-adjudicator" and (projection_failures := adjudicator_packet_projection_failures(root)):
        raise ValueError(json.dumps({"adjudicator_packet_projection_failures": projection_failures}))
    candidate_result = candidate_validation_result(root, role, supplied_candidate)
    if candidate_result is not None:
        return {"role": role, "files": len(files), **candidate_result}
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
    return {"status": "passed", "role": role, "files": len(files), "commands": results}


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
        result = validate_bundle(arguments.check, arguments.candidate)
    print(json.dumps(result, sort_keys=True))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
