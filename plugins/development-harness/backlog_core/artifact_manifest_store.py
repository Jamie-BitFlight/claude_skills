"""Revision-safe persistence for artifact manifests."""

from __future__ import annotations

import hashlib
from typing import Final

from pydantic import ValidationError as PydanticValidationError

from .artifact_registry import ArtifactRegistry
from .backend_types import ContentProvider
from .models import (
    ArtifactEntry,
    ArtifactManifest,
    ContentConflictError,
    ContentNotFoundError,
    ContentRef,
    ContentWrite,
    ValidationError,
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


def artifact_content_reference(item_id: int | str, entry: ArtifactEntry) -> ContentRef:
    """Return the immutable content identity referenced by an artifact entry.

    The manifest reference's boundary, one model deeper: ``ContentRef``'s validator refuses an
    empty content name with ``raise ValueError``, which pydantic re-raises as
    ``pydantic.ValidationError`` -- a ``ValueError`` subclass, not a ``BacklogError``, so
    ``artifact_read``'s ``except BacklogError`` missed it and an entry stored with an empty
    ``artifact_id`` failed the tool call instead of returning the documented ``error`` response.
    Converting it here matches ``backlog_core.server._manifest_reference`` and covers all three
    call sites. ``backlog_core.server.artifact_read`` (the MCP tool) and
    ``dh_core.operations.artifact_read`` both read an entry straight out of a stored manifest, so
    an empty ``artifact_id`` reaches the validator from either. ``publish_artifact`` below cannot
    reach it: it stamps a sha256 ``content_revision`` onto the entry first, so the name this
    helper builds ends in ``@sha256:<digest>`` and is never empty.

    Returns:
        The content ``ContentRef`` for the entry.

    Raises:
        ValidationError: When *entry* does not name a usable content identity.
    """
    name = entry.artifact_id
    if entry.content_revision:
        name = f"{name}@sha256:{entry.content_revision}"
    try:
        return ContentRef(
            kind="artifact_content", namespace=str(item_id), artifact_type=entry.artifact_type.value, name=name
        )
    except PydanticValidationError as exc:
        raise ValidationError("; ".join(error["msg"] for error in exc.errors())) from exc


def publish_artifact(
    provider: ContentProvider, manifest_reference: ContentRef, item_id: int | str, entry: ArtifactEntry, content: str
) -> tuple[ArtifactManifest, bool]:
    """Publish immutable content before atomically advancing its manifest entry.

    Returns:
        The persisted manifest and whether the logical artifact previously existed.
    """
    published_entry = entry.model_copy(update={"content_revision": hashlib.sha256(content.encode()).hexdigest()})
    content_reference = artifact_content_reference(item_id, published_entry)
    try:
        provider.put_content(ContentWrite(reference=content_reference, content=content, create_only=True))
    except ContentConflictError:
        if provider.get_content(content_reference).content != content:
            raise
    return register_manifest_entry(provider, manifest_reference, item_id, published_entry)
