"""Revision-safe persistence for artifact manifests."""

from __future__ import annotations

from typing import Final

from .artifact_registry import ArtifactRegistry
from .backend_types import ContentProvider
from .models import (
    ArtifactEntry,
    ArtifactManifest,
    ContentConflictError,
    ContentNotFoundError,
    ContentRef,
    ContentWrite,
)

# ponytail: three CAS attempts, use provider-side atomic registration if conflicts persist.
_MANIFEST_WRITE_ATTEMPTS: Final = 3


def load_manifest(provider: ContentProvider, reference: ContentRef, item_id: int | str) -> tuple[ArtifactManifest, str]:
    """Load a manifest and the revision required for its next write.

    Returns:
        The manifest and its provider revision.
    """
    try:
        record = provider.get_content(reference)
    except ContentNotFoundError:
        return ArtifactManifest(issue_number=item_id), ""
    return ArtifactManifest.model_validate_json(record.content), record.revision


def register_manifest_entry(
    provider: ContentProvider, reference: ContentRef, item_id: int | str, entry: ArtifactEntry
) -> tuple[ArtifactManifest, bool]:
    """Register one entry with bounded compare-and-swap retries.

    Returns:
        The persisted manifest and whether the entry previously existed.
    """
    registry = ArtifactRegistry()
    for attempt in range(_MANIFEST_WRITE_ATTEMPTS):
        manifest, revision = load_manifest(provider, reference, item_id)
        existed = any(
            existing.artifact_type == entry.artifact_type and existing.artifact_id == entry.artifact_id
            for existing in manifest.artifacts
        )
        manifest = registry.register(manifest, entry)
        try:
            provider.put_content(
                ContentWrite(
                    reference=reference,
                    content=manifest.model_dump_json(),
                    expected_revision=revision,
                    create_only=not revision,
                )
            )
        except ContentConflictError:
            if attempt + 1 == _MANIFEST_WRITE_ATTEMPTS:
                raise
        else:
            return manifest, existed
    raise ContentConflictError("Content revision no longer matches")
