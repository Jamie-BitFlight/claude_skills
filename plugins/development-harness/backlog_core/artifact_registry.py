"""Business logic for the artifact manifest registry.

This module is purely stateless — all methods accept and return
``ArtifactManifest`` objects without internal state.  No I/O is performed
here; all GitHub interaction is in :mod:`backlog_core.artifact_provider`.

Manifest section format stored in GitHub Issue bodies::

    ## Artifact Manifest

    <!-- artifact-manifest:begin -->
    | Type | Path | Status | Agent | Created |
    |------|------|--------|-------|---------|
    | feature-context | plan/feature-context-foo.md | current | feature-researcher | 2026-03-21T10:00:00Z |
    <!-- artifact-manifest:end -->

Module-level parse/render helpers:
    - :func:`parse_manifest_section` — extract ``ArtifactManifest`` from issue body
    - :func:`render_manifest_section` — produce full markdown section from manifest
    - :func:`replace_manifest_in_body` — update section in-place or append

Registry operations (all via ``ArtifactRegistry``):
    - :meth:`~ArtifactRegistry.register` — idempotent upsert by (type, artifact_id)
    - :meth:`~ArtifactRegistry.remove` — delete entry by type and artifact_id
    - :meth:`~ArtifactRegistry.get_by_type` — filter entries by artifact type
    - :meth:`~ArtifactRegistry.update_status` — set lifecycle status on a specific entry
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .models import ArtifactEntry, ArtifactManifest, ArtifactStatus, ArtifactType

if TYPE_CHECKING:
    from .artifact_provider import ItemId

# ---------------------------------------------------------------------------
# Manifest section constants
# ---------------------------------------------------------------------------

_MANIFEST_BEGIN = "<!-- artifact-manifest:begin -->"
_MANIFEST_END = "<!-- artifact-manifest:end -->"

_MANIFEST_HEADER = "## Artifact Manifest"

#: Regex that matches the complete manifest section including delimiters.
_MANIFEST_SECTION_RE = re.compile(r"<!-- artifact-manifest:begin -->.*?<!-- artifact-manifest:end -->", re.DOTALL)

#: Number of columns in the markdown table (Type | Path | Status | Agent | Created).
_TABLE_COLUMN_COUNT = 5

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_table_row(row: str) -> ArtifactEntry | None:
    """Parse one markdown table row into an ``ArtifactEntry``, or return ``None``.

    Args:
        row: A single markdown table row string, e.g.
            ``"| feature-context | plan/fc.md | current | agent | 2026… |"``.

    Returns:
        Parsed ``ArtifactEntry``, or ``None`` when the row is a header,
        separator, or otherwise unparseable.
    """
    stripped = row.strip()
    if not stripped.startswith("|"):
        return None
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if len(cells) < _TABLE_COLUMN_COUNT:
        return None
    type_cell, path_cell, status_cell, agent_cell, created_cell = cells[:5]
    # Skip header row ("Type") and separator row ("---")
    if type_cell.lower() in {"type", "---", "------"} or type_cell.startswith("-"):
        return None
    try:
        artifact_type = ArtifactType(type_cell)
    except ValueError:
        return None
    try:
        status = ArtifactStatus(status_cell)
    except ValueError:
        status = ArtifactStatus.CURRENT
    return ArtifactEntry(
        artifact_type=artifact_type, artifact_id=path_cell, status=status, created_at=created_cell, agent=agent_cell
    )


def _extract_table_from_rendered(rendered: str) -> str:
    """Return the table rows from a rendered section (without heading or delimiters).

    Args:
        rendered: Output of :func:`render_manifest_section`.

    Returns:
        Lines between the begin and end delimiters, joined by newlines.
    """
    lines = rendered.splitlines()
    inside = False
    table_lines: list[str] = []
    for line in lines:
        if _MANIFEST_BEGIN in line:
            inside = True
            continue
        if _MANIFEST_END in line:
            break
        if inside:
            table_lines.append(line)
    return "\n".join(table_lines)


# ---------------------------------------------------------------------------
# Public parse / render helpers
# ---------------------------------------------------------------------------


def parse_manifest_section(issue_body: str, item_id: ItemId) -> ArtifactManifest:
    """Extract and parse the artifact manifest section from an issue body.

    Returns an empty ``ArtifactManifest`` when no manifest section is found —
    this is not an error condition; it simply means no artifacts have been
    registered yet.

    Args:
        issue_body: Full GitHub Issue body text.
        item_id: Item identifier for the returned manifest object (``str | int``).

    Returns:
        ``ArtifactManifest`` parsed from the delimited section, or an empty
        manifest when the section is absent.
    """
    match = _MANIFEST_SECTION_RE.search(issue_body)
    if not match:
        return ArtifactManifest(issue_number=item_id)

    section = match.group(0)
    artifacts: list[ArtifactEntry] = []
    for line in section.splitlines():
        entry = _parse_table_row(line)
        if entry is not None:
            artifacts.append(entry)
    return ArtifactManifest(issue_number=item_id, artifacts=artifacts)


def render_manifest_section(manifest: ArtifactManifest) -> str:
    """Render an ``ArtifactManifest`` as a delimited markdown section.

    Produces the complete section including the heading, HTML comment
    delimiters, and markdown table.

    Args:
        manifest: The manifest to render.

    Returns:
        Multi-line string with heading, begin delimiter, table, end delimiter.
    """
    header_row = "| Type | Path | Status | Agent | Created |"
    separator_row = "|------|------|--------|-------|---------|"
    rows = [header_row, separator_row]
    rows.extend(
        f"| {entry.artifact_type} | {entry.artifact_id} | {entry.status} | {entry.agent} | {entry.created_at} |"
        for entry in manifest.artifacts
    )
    table = "\n".join(rows)
    return f"{_MANIFEST_HEADER}\n\n{_MANIFEST_BEGIN}\n{table}\n{_MANIFEST_END}"


def replace_manifest_in_body(issue_body: str, rendered_section: str) -> str:
    """Replace the manifest section in an issue body, or append it if absent.

    Preserves all content outside the manifest section.  When no section
    exists the rendered section is appended with a preceding blank line.

    Args:
        issue_body: Current full issue body text.
        rendered_section: New manifest section produced by
            :func:`render_manifest_section`.

    Returns:
        Updated issue body with the manifest section inserted or replaced.
    """
    if _MANIFEST_SECTION_RE.search(issue_body):
        # Replace both the heading (if immediately before the begin delimiter)
        # and the delimited block in one pass.
        heading_and_section_re = re.compile(
            r"##\s+Artifact Manifest\s*\n\s*\n?" + re.escape(_MANIFEST_BEGIN) + r".*?" + re.escape(_MANIFEST_END),
            re.DOTALL,
        )
        if heading_and_section_re.search(issue_body):
            return heading_and_section_re.sub(rendered_section, issue_body)
        # Fallback: replace only the delimited block (heading may be elsewhere)
        table_only = _extract_table_from_rendered(rendered_section)
        return _MANIFEST_SECTION_RE.sub(f"{_MANIFEST_BEGIN}\n{table_only}\n{_MANIFEST_END}", issue_body)
    return issue_body.rstrip() + "\n\n" + rendered_section + "\n"


# ---------------------------------------------------------------------------
# ArtifactRegistry — stateless business logic
# ---------------------------------------------------------------------------


class ArtifactRegistry:
    """Stateless business-logic layer for artifact manifest operations.

    All methods accept an ``ArtifactManifest`` object and return a new or
    modified ``ArtifactManifest``.  No I/O is performed; callers are
    responsible for loading and persisting manifests via an
    :class:`~backlog_core.artifact_provider.ArtifactBackend` implementation.

    Example::

        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=965)
        entry = ArtifactEntry(artifact_type=ArtifactType.FEATURE_CONTEXT, artifact_id="plan/feature-context-foo.md")
        manifest = registry.register(manifest, entry)
        # manifest.artifacts now contains one entry
    """

    def register(self, manifest: ArtifactManifest, entry: ArtifactEntry) -> ArtifactManifest:
        """Upsert an artifact entry into the manifest.

        Upsert logic:

        - If an existing entry matches on both ``artifact_type`` **and** ``path``,
          update its ``status``, ``agent``, and ``created_at`` in-place (idempotent
          re-registration updates the existing row rather than duplicating it).
        - If an existing entry matches on ``artifact_type`` but with a **different**
          ``path``, add a new row (multiple artifacts of the same type are allowed,
          e.g. two codebase-analysis artifacts for different scopes).
        - If no entry matches on ``artifact_type``, append a new row.

        A ``created_at`` timestamp is generated automatically when the provided
        entry has an empty ``created_at`` field.

        Args:
            manifest: Current manifest to update.
            entry: Artifact entry to register.  Must have ``artifact_type`` and
                ``path`` set.

        Returns:
            New ``ArtifactManifest`` with the entry upserted.
        """
        # Auto-stamp created_at when the caller did not supply one.
        if not entry.created_at:
            entry = entry.model_copy(update={"created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})

        updated: list[ArtifactEntry] = []
        upserted = False

        for existing in manifest.artifacts:
            if existing.artifact_type == entry.artifact_type and existing.artifact_id == entry.artifact_id:
                # Exact match — update in-place.
                updated.append(
                    existing.model_copy(
                        update={"status": entry.status, "agent": entry.agent, "created_at": entry.created_at}
                    )
                )
                upserted = True
            else:
                updated.append(existing)

        if not upserted:
            updated.append(entry)

        return manifest.model_copy(update={"artifacts": updated})

    def remove(self, manifest: ArtifactManifest, artifact_type: ArtifactType, path: str) -> ArtifactManifest:
        """Remove an artifact entry from the manifest by type and path.

        If no matching entry exists the manifest is returned unchanged.

        Args:
            manifest: Current manifest.
            artifact_type: Type of the artifact to remove.
            path: Repo-relative path of the artifact to remove.

        Returns:
            New ``ArtifactManifest`` with the matching entry removed.
        """
        remaining = [e for e in manifest.artifacts if not (e.artifact_type == artifact_type and e.artifact_id == path)]
        return manifest.model_copy(update={"artifacts": remaining})

    def get_by_type(self, manifest: ArtifactManifest, artifact_type: ArtifactType) -> list[ArtifactEntry]:
        """Return all entries matching *artifact_type*.

        Args:
            manifest: Manifest to query.
            artifact_type: Artifact type to filter by.

        Returns:
            List of matching ``ArtifactEntry`` objects, possibly empty.
        """
        return [e for e in manifest.artifacts if e.artifact_type == artifact_type]

    def update_status(
        self, manifest: ArtifactManifest, artifact_type: ArtifactType, path: str, status: ArtifactStatus
    ) -> ArtifactManifest:
        """Update the lifecycle status of a specific artifact entry.

        Matches on both ``artifact_type`` and ``path``.  If no matching entry
        exists the manifest is returned unchanged (the caller can detect this
        by comparing ``manifest.artifacts`` lengths or checking whether the
        target entry exists before calling).

        Args:
            manifest: Current manifest.
            artifact_type: Type of the artifact to update.
            path: Repo-relative path of the artifact to update.
            status: New lifecycle status to set.

        Returns:
            New ``ArtifactManifest`` with the matching entry's status updated.
        """
        updated = [
            e.model_copy(update={"status": status})
            if (e.artifact_type == artifact_type and e.artifact_id == path)
            else e
            for e in manifest.artifacts
        ]
        return manifest.model_copy(update={"artifacts": updated})
