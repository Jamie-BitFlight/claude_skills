#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# ///
# ruff: file-ignore[undocumented-public-module, undocumented-public-class, undocumented-public-function]
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

Status: TypeAlias = Literal["excluded", "recovery", "transferred"]
JsonValue: TypeAlias = bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None


@dataclass(frozen=True, slots=True)
class Account:
    status: Status
    reason: str | None = None
    recovery_ref: str | None = None
    target_commit: str | None = None
    target_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Manifest:
    commits: dict[str, Account]
    paths: dict[str, Account]


class AuditError(Exception):
    pass


def git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise AuditError("git executable is unavailable")
    return executable


def patch_id(repository: Path, commit: str) -> str:
    patch = git(repository, "show", "--pretty=format:", commit)
    result = subprocess.run(
        [git_executable(), "patch-id", "--stable"],
        cwd=repository,
        capture_output=True,
        check=False,
        input=patch,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise AuditError(f"cannot calculate patch ID for {commit}: {message}")
    output = result.stdout.split(maxsplit=1)
    if not output:
        raise AuditError(f"cannot calculate patch ID for {commit}: empty patch")
    return output[0]


def parse_account(raw: JsonValue, key: str) -> Account:
    if not isinstance(raw, dict):
        raise AuditError(f"{key} must be an object")
    status = raw.get("status")
    if status not in {"excluded", "recovery", "transferred"}:
        raise AuditError(f"{key}.status must be excluded, recovery, or transferred")
    reason = raw.get("reason")
    recovery_ref = raw.get("recovery_ref")
    target_commit = raw.get("target_commit")
    target_paths = raw.get("target_paths", [])
    if reason is not None and not isinstance(reason, str):
        raise AuditError(f"{key}.reason must be a string")
    if recovery_ref is not None and not isinstance(recovery_ref, str):
        raise AuditError(f"{key}.recovery_ref must be a string")
    if target_commit is not None and not isinstance(target_commit, str):
        raise AuditError(f"{key}.target_commit must be a string")
    if not isinstance(target_paths, list) or not all(isinstance(path, str) for path in target_paths):
        raise AuditError(f"{key}.target_paths must be an array of strings")
    match status:
        case "excluded" if not reason or not reason.strip():
            raise AuditError(f"{key}.reason must be non-empty for excluded work")
        case "recovery" if not recovery_ref or not recovery_ref.strip():
            raise AuditError(f"{key}.recovery_ref must name a ref for recovered work")
        case "transferred" if target_commit is None and not target_paths:
            raise AuditError(f"{key} must name target_commit or target_paths for transferred work")
        case _:
            pass
    return Account(
        status=status,
        reason=reason,
        recovery_ref=recovery_ref,
        target_commit=target_commit,
        target_paths=tuple(target_paths),
    )


def parse_accounts(raw: JsonValue, category: str) -> dict[str, Account]:
    if not isinstance(raw, dict):
        raise AuditError(f"{category} must be an object")
    accounts: dict[str, Account] = {}
    for key, value in raw.items():
        accounts[key] = parse_account(value, f"{category}.{key}")
    return accounts


def parse_manifest(path: Path) -> Manifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise AuditError(f"cannot read manifest: {error}") from error
    except json.JSONDecodeError as error:
        raise AuditError(f"invalid manifest JSON: {error.msg}") from error
    if not isinstance(raw, dict):
        raise AuditError("manifest must be an object")
    return Manifest(
        commits=parse_accounts(raw.get("commits", {}), "commits"), paths=parse_accounts(raw.get("paths", {}), "paths")
    )


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run([git_executable(), *arguments], cwd=repository, capture_output=True, check=False, text=True)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise AuditError(f"git {' '.join(arguments)} failed: {message}")
    return result.stdout.strip()


def ref_contains(repository: Path, ancestor: str, ref: str) -> bool:
    result = subprocess.run(
        [git_executable(), "merge-base", "--is-ancestor", ancestor, ref],
        cwd=repository,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode in {0, 1}:
        return result.returncode == 0
    message = result.stderr.strip() or result.stdout.strip()
    raise AuditError(f"cannot inspect recovery ref {ref}: {message}")


def blob_at_ref(repository: Path, ref: str, path: str) -> str | None:
    result = subprocess.run(
        [git_executable(), "rev-parse", "--verify", f"{ref}:{path}"],
        cwd=repository,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode in {0, 128}:
        return result.stdout.strip() or None
    message = result.stderr.strip() or result.stdout.strip()
    raise AuditError(f"cannot inspect {path} at {ref}: {message}")


def matching_target_blob(repository: Path, source: str, path: str, target: str, target_paths: tuple[str, ...]) -> bool:
    source_blob = blob_at_ref(repository, source, path)
    return source_blob is not None and any(
        source_blob == blob_at_ref(repository, target, target_path) for target_path in target_paths
    )


def require_clean_worktree(repository: Path) -> None:
    if git(repository, "status", "--porcelain", "--untracked-files=all"):
        raise AuditError("worktree is dirty; commit or preserve it before transfer")


def is_accounted(
    account: Account | None, unit: str, source: str, target: str, repository: Path, *, is_commit: bool
) -> bool:
    if account is None:
        return False
    match account.status:
        case "excluded":
            return True
        case "recovery":
            ancestor = unit if is_commit else source
            return ref_contains(repository, ancestor, account.recovery_ref or "")
        case "transferred" if is_commit:
            return (
                account.target_commit is not None
                and ref_contains(repository, account.target_commit, target)
                and patch_id(repository, unit) == patch_id(repository, account.target_commit)
            )
        case "transferred":
            return matching_target_blob(repository, source, unit, target, account.target_paths)


def audit(repository: Path, source: str, base: str, target: str, manifest: Manifest) -> dict[str, list[str]]:
    require_clean_worktree(repository)
    source_commits = set(git(repository, "rev-list", f"{base}..{source}").splitlines())
    source_paths = set(git(repository, "diff", "--name-only", f"{base}...{source}").splitlines())
    missing_commits = sorted(
        commit
        for commit in source_commits
        if not is_accounted(manifest.commits.get(commit), commit, source, target, repository, is_commit=True)
    )
    missing_paths = sorted(
        path
        for path in source_paths
        if not is_accounted(manifest.paths.get(path), path, source, target, repository, is_commit=False)
    )
    return {"commits": missing_commits, "paths": missing_paths}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit source-only Git work before destructive branch operations.",
        epilog=(
            'Manifest: {"commits":{"<source-commit>":{"status":"transferred","target_commit":"<target-commit>"}},'
            '"paths":{"<source-path>":{"status":"transferred","target_paths":["<target-path>"]}}}. '
            'Use {"status":"excluded","reason":"..."} or {"status":"recovery","recovery_ref":"<ref>"}.'
        ),
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        missing = audit(
            Path.cwd(), arguments.source, arguments.base, arguments.target, parse_manifest(arguments.manifest)
        )
    except AuditError as error:
        print(json.dumps({"ok": False, "error": str(error)}, separators=(",", ":")))
        return 2
    if missing["commits"] or missing["paths"]:
        print(json.dumps({"ok": False, "missing": missing}, separators=(",", ":")))
        return 1
    print(json.dumps({"ok": True}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
