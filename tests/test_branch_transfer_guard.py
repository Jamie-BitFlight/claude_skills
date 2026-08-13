from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts" / "audit_branch_transfer.py"


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-C", str(repository), *arguments], capture_output=True, check=True, text=True)
    return result.stdout.strip()


def commit(repository: Path, path: str, contents: str, message: str) -> str:
    (repository / path).write_text(contents, encoding="utf-8")
    git(repository, "add", path)
    git(repository, "commit", "-m", message)
    return git(repository, "rev-parse", "HEAD")


def create_repository(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "--initial-branch=base")
    git(repository, "config", "user.email", "test@example.com")
    git(repository, "config", "user.name", "Test User")
    base = commit(repository, "base.txt", "base\n", "base")

    git(repository, "switch", "-c", "source")
    transferred = commit(repository, "transferred.txt", "transfer\n", "transfer")
    excluded = commit(repository, "excluded.txt", "exclude\n", "exclude")
    recovered = commit(repository, "recovered.txt", "recover\n", "recover")
    git(repository, "branch", "recovery/source", recovered)

    git(repository, "switch", "-c", "target", "base")
    git(repository, "cherry-pick", transferred)
    target_commit = git(repository, "rev-parse", "HEAD")
    return repository, {
        "base": base,
        "transferred": transferred,
        "excluded": excluded,
        "recovered": recovered,
        "target_commit": target_commit,
    }


def create_deletion_repository(tmp_path: Path, *, target_deletes: bool) -> tuple[Path, str, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "--initial-branch=base")
    git(repository, "config", "user.email", "test@example.com")
    git(repository, "config", "user.name", "Test User")
    commit(repository, "deleted.txt", "delete me\n", "base")

    git(repository, "switch", "-c", "source")
    git(repository, "rm", "deleted.txt")
    git(repository, "commit", "-m", "delete from source")
    source_commit = git(repository, "rev-parse", "HEAD")

    git(repository, "switch", "-c", "target", "base")
    if target_deletes:
        git(repository, "rm", "deleted.txt")
        git(repository, "commit", "-m", "delete from target")
    return repository, source_commit, git(repository, "rev-parse", "HEAD")


def run_guard(repository: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            "source",
            "--base",
            "base",
            "--target",
            "target",
            "--manifest",
            str(manifest),
        ],
        cwd=repository,
        capture_output=True,
        check=False,
        text=True,
    )


def test_audit_fails_when_source_only_commit_and_path_are_unaccounted(tmp_path: Path) -> None:
    # Given
    repository, identifiers = create_repository(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"commits": {}, "paths": {}}), encoding="utf-8")

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert identifiers["transferred"] in report["missing"]["commits"]
    assert "transferred.txt" in report["missing"]["paths"]


def test_audit_passes_when_every_source_only_unit_is_accounted(tmp_path: Path) -> None:
    # Given
    repository, identifiers = create_repository(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "commits": {
                identifiers["transferred"]: {"status": "transferred", "target_commit": identifiers["target_commit"]},
                identifiers["excluded"]: {"status": "excluded", "reason": "Deferred deliberately."},
                identifiers["recovered"]: {"status": "recovery", "recovery_ref": "recovery/source"},
            },
            "paths": {
                "transferred.txt": {"status": "transferred", "target_paths": ["transferred.txt"]},
                "excluded.txt": {"status": "excluded", "reason": "Deferred deliberately."},
                "recovered.txt": {"status": "recovery", "recovery_ref": "recovery/source"},
            },
        }),
        encoding="utf-8",
    )

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"ok": True}


def test_audit_rejects_a_transferred_commit_matched_to_an_unrelated_target_commit(tmp_path: Path) -> None:
    # Given
    repository, identifiers = create_repository(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "commits": {
                identifiers["transferred"]: {"status": "transferred", "target_commit": identifiers["base"]},
                identifiers["excluded"]: {"status": "excluded", "reason": "Deferred deliberately."},
                identifiers["recovered"]: {"status": "recovery", "recovery_ref": "recovery/source"},
            },
            "paths": {
                "transferred.txt": {"status": "transferred", "target_paths": ["transferred.txt"]},
                "excluded.txt": {"status": "excluded", "reason": "Deferred deliberately."},
                "recovered.txt": {"status": "recovery", "recovery_ref": "recovery/source"},
            },
        }),
        encoding="utf-8",
    )

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 1
    assert identifiers["transferred"] in json.loads(result.stdout)["missing"]["commits"]


def test_audit_rejects_dirty_and_untracked_worktree(tmp_path: Path) -> None:
    # Given
    repository, _ = create_repository(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"commits": {}, "paths": {}}), encoding="utf-8")
    (repository / "untracked.txt").write_text("preserve me\n", encoding="utf-8")

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 2
    assert json.loads(result.stdout) == {
        "ok": False,
        "error": "worktree is dirty; commit or preserve it before transfer",
    }


def test_audit_rejects_a_source_path_mapped_to_an_unrelated_target_path(tmp_path: Path) -> None:
    # Given
    repository, identifiers = create_repository(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "commits": {
                identifiers["transferred"]: {"status": "transferred", "target_commit": identifiers["target_commit"]},
                identifiers["excluded"]: {"status": "excluded", "reason": "Deferred deliberately."},
                identifiers["recovered"]: {"status": "recovery", "recovery_ref": "recovery/source"},
            },
            "paths": {
                "transferred.txt": {"status": "transferred", "target_paths": ["transferred.txt"]},
                "excluded.txt": {"status": "transferred", "target_paths": ["transferred.txt"]},
                "recovered.txt": {"status": "recovery", "recovery_ref": "recovery/source"},
            },
        }),
        encoding="utf-8",
    )

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 1
    assert "excluded.txt" in json.loads(result.stdout)["missing"]["paths"]


def test_audit_accepts_a_transferred_deletion_absent_from_source_and_target(tmp_path: Path) -> None:
    # Given
    repository, source_commit, target_commit = create_deletion_repository(tmp_path, target_deletes=True)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "commits": {source_commit: {"status": "transferred", "target_commit": target_commit}},
            "paths": {"deleted.txt": {"status": "transferred", "target_paths": ["deleted.txt"]}},
        }),
        encoding="utf-8",
    )

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"ok": True}


def test_audit_rejects_a_transferred_deletion_that_remains_at_target(tmp_path: Path) -> None:
    # Given
    repository, source_commit, _ = create_deletion_repository(tmp_path, target_deletes=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "commits": {source_commit: {"status": "excluded", "reason": "Testing path accounting only."}},
            "paths": {"deleted.txt": {"status": "transferred", "target_paths": ["deleted.txt"]}},
        }),
        encoding="utf-8",
    )

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 1
    assert json.loads(result.stdout)["missing"]["paths"] == ["deleted.txt"]


def test_audit_rejects_a_transferred_deletion_mapped_to_an_unrelated_absent_path(tmp_path: Path) -> None:
    # Given
    repository, source_commit, target_commit = create_deletion_repository(tmp_path, target_deletes=True)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "commits": {source_commit: {"status": "transferred", "target_commit": target_commit}},
            "paths": {"deleted.txt": {"status": "transferred", "target_paths": ["unrelated.txt"]}},
        }),
        encoding="utf-8",
    )

    # When
    result = run_guard(repository, manifest)

    # Then
    assert result.returncode == 1
    assert json.loads(result.stdout)["missing"]["paths"] == ["deleted.txt"]
