"""Immutable evidence storage for merge-train decisions."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from dh_core.ledger import store

T = TypeVar("T")


@dataclass(frozen=True)
class EvidenceBlob:
    """One fully verified immutable evidence value."""

    digest: str
    byte_length: int
    media_type: str
    content: bytes
    created_at: str


class MergeEvidenceStore:
    """Store immutable evidence in the ledger database."""

    def __init__(self, ledger: sqlite3.Connection) -> None:
        """Bind to the same database as merge-train events."""
        self.ledger = ledger

    def put(self, content: bytes | bytearray, media_type: str) -> EvidenceBlob:
        """Capture and insert complete evidence bytes.

        Returns:
            The immutable stored value.
        """
        captured = bytes(content)
        if not media_type.strip():
            raise store.Refusal("evidence-invalid-media-type")
        digest = "sha256:" + hashlib.sha256(captured).hexdigest()
        created_at = store.timestamp(store.now())
        with store.transaction(self.ledger):
            found = self.ledger.execute(
                "SELECT digest, byte_length, media_type, content, created_at "
                "FROM merge_evidence_blobs WHERE digest = ?",
                (digest,),
            ).fetchone()
            if found is None:
                self.ledger.execute(
                    "INSERT INTO merge_evidence_blobs "
                    "(digest, byte_length, media_type, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (digest, len(captured), media_type, sqlite3.Binary(captured), created_at),
                )
            else:
                existing = self.row_blob(found)
                if existing.content != captured or existing.media_type != media_type:
                    raise store.Refusal("evidence-collision")
                return existing
            return self.get(digest)

    def get(self, digest: str) -> EvidenceBlob:
        """Read and verify complete evidence bytes.

        Returns:
            The immutable verified value.
        """
        if re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
            raise store.Refusal("evidence-invalid-digest")
        found = self.ledger.execute(
            "SELECT digest, byte_length, media_type, content, created_at FROM merge_evidence_blobs WHERE digest = ?",
            (digest,),
        ).fetchone()
        if found is None:
            raise store.Refusal("evidence-not-found")
        blob = self.row_blob(found)
        actual = "sha256:" + hashlib.sha256(blob.content).hexdigest()
        if actual != blob.digest or len(blob.content) != blob.byte_length or not blob.media_type.strip():
            raise store.Refusal("evidence-corrupt")
        return blob

    @staticmethod
    def row_blob(row: sqlite3.Row) -> EvidenceBlob:
        """Convert one row without rereading its content.

        Returns:
            The captured row value.
        """
        content = row[3]
        if not isinstance(content, bytes):
            raise store.Refusal("evidence-corrupt")
        return EvidenceBlob(
            digest=str(row[0]), byte_length=int(row[1]), media_type=str(row[2]), content=content, created_at=str(row[4])
        )

    def require(self, digest: str) -> EvidenceBlob:
        """Require a fully verified evidence value.

        Returns:
            The verified value.
        """
        return self.get(digest)

    def parse(self, digest: str, parser: Callable[[bytes], T]) -> tuple[EvidenceBlob, T]:
        """Parse the exact bytes returned by verification.

        Returns:
            The verified value and parser result.
        """
        blob = self.get(digest)
        return blob, parser(blob.content)
