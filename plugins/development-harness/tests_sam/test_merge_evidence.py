"""Immutable merge evidence public-seam tests."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dh_core.ledger import store
from dh_core.merge_evidence import MergeEvidenceStore


def test_f10_put_hashes_and_stores_one_captured_buffer(tmp_path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    source = bytearray(b"complete evidence\x00\xff")
    expected = bytes(source)

    saved = evidence.put(source, "application/octet-stream")
    source[:] = b"changed"
    loaded = evidence.get(saved.digest)

    assert saved.digest == "sha256:" + hashlib.sha256(expected).hexdigest()
    assert loaded.content == expected
    assert loaded.byte_length == len(expected)


def test_f10_duplicate_put_is_immutable(tmp_path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    first = evidence.put(b"same", "application/json")
    second = evidence.put(b"same", "application/json")

    assert second == first
    with pytest.raises(store.Refusal, match="evidence-collision"):
        evidence.put(b"same", "text/plain")


def test_f10_parser_receives_the_verified_buffer(tmp_path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    saved = evidence.put(b'{"schema_version":1}', "application/json")
    observed = None

    def parser(content: bytes) -> int:
        nonlocal observed
        observed = content
        return len(content)

    loaded, parsed = evidence.parse(saved.digest, parser)

    assert observed is loaded.content
    assert parsed == loaded.byte_length


def test_f10_missing_truncated_bad_digest_and_metadata_refuse(tmp_path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    saved = evidence.put(b"complete", "application/json")

    with pytest.raises(store.Refusal, match="evidence-invalid-digest"):
        evidence.get("sha256:BAD")
    with pytest.raises(store.Refusal, match="evidence-not-found"):
        evidence.get("sha256:" + "0" * 64)
    connection.execute(
        "UPDATE merge_evidence_blobs SET content = x'00', byte_length = 1 WHERE digest = ?", (saved.digest,)
    )
    with pytest.raises(store.Refusal, match="evidence-corrupt"):
        evidence.get(saved.digest)


def test_f18_rebuild_retains_blob_source_rows(tmp_path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    saved = evidence.put(b"root", "application/json")

    store.rebuild(connection)

    assert evidence.get(saved.digest).content == b"root"
    assert "merge_evidence_blobs" not in store.TABLES
    assert "merge_evidence_blobs" in store.SOURCE_TABLES


def test_f10_process_death_during_blob_transaction_is_old_or_complete(tmp_path: Path) -> None:
    database = tmp_path / "dh.db"
    connection = store.open_ledger(database)
    connection.close()
    plugin = Path(__file__).parents[1]
    content = b"crash-evidence"
    digest = "sha256:" + hashlib.sha256(content).hexdigest()
    script = (
        "import os,sqlite3,sys; db,digest,mode=sys.argv[1:]; c=sqlite3.connect(db); c.execute('BEGIN IMMEDIATE'); "
        "c.execute(\"INSERT INTO merge_evidence_blobs VALUES (?,14,'application/octet-stream',?,'now')\","
        "(digest,b'crash-evidence')); "
        "c.commit() if mode=='commit' else None; os._exit(0)"
    )
    environment = {**os.environ, "PYTHONPATH": str(plugin)}

    subprocess.run((sys.executable, "-c", script, str(database), digest, "crash"), env=environment, check=True)
    verify = store.open_ledger(database)
    assert verify.execute("SELECT COUNT(*) FROM merge_evidence_blobs").fetchone()[0] == 0
    verify.close()
    subprocess.run((sys.executable, "-c", script, str(database), digest, "commit"), env=environment, check=True)
    verify = store.open_ledger(database)
    assert MergeEvidenceStore(verify).get(digest).content == content
