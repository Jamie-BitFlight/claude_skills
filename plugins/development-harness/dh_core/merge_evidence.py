"""Immutable evidence storage for merge-train decisions."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

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
        """Capture and insert complete evidence bytes."""
        raise NotImplementedError

    def get(self, digest: str) -> EvidenceBlob:
        """Read and verify complete evidence bytes."""
        raise NotImplementedError

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
