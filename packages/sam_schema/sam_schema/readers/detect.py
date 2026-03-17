"""Format detection and plan read routing for SAM task/plan files.

The ``detect_format`` function inspects a file or directory path and returns
a ``FormatType`` enum value. The ``read_plan`` function routes to the correct
format-specific reader based on the detected format.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class FormatType(StrEnum):
    """Supported task/plan file formats."""

    PURE_YAML = "pure_yaml"
    """Canonical ``.yaml`` file(s). Single file or directory of per-task files."""

    YAML_FRONTMATTER = "yaml_frontmatter"
    """``.md`` file with ``---`` delimited YAML blocks per task."""

    LEGACY_MARKDOWN = "legacy_markdown"
    """``.md`` file with ``## Task N:`` headings and ``**Field**: Value`` markers."""

    GLOBAL_MANIFEST = "global_manifest"
    """``.md`` file with a global frontmatter header (``feature:`` + ``tasks:`` list)
    and per-task content in ``### T{N}:`` prose sections."""

    DIRECTORY = "directory"
    """Directory containing one ``.yaml`` or ``.md`` file per task."""


class FormatDetectionError(Exception):
    """Raised when no known format can be identified for a path.

    Args:
        path: File or directory that could not be classified.
        first_lines: First few lines of the file that were inspected.
    """

    def __init__(self, path: Path, first_lines: str) -> None:
        """Initialize FormatDetectionError with path and inspected content."""
        self.path = path
        self.first_lines = first_lines
        super().__init__(f"Cannot detect task file format for '{path}'.\nFirst 20 lines inspected:\n{first_lines}")


# Compiled patterns for format detection
_TASK_FIELD_RE = re.compile(r"^task\s*:", re.MULTILINE)
_FEATURE_FIELD_RE = re.compile(r"^(?:feature|slug)\s*:", re.MULTILINE)
_TASKS_LIST_RE = re.compile(r"^tasks\s*:", re.MULTILINE)
_LEGACY_HEADING_RE = re.compile(r"^##\s+Task\s+\d", re.MULTILINE)


def _classify_frontmatter(frontmatter_text: str) -> FormatType | None:
    """Classify a YAML frontmatter block into a FormatType.

    Returns ``None`` when the frontmatter content does not match any known
    frontmatter-based format (caller falls through to legacy heading check).

    Detection order:
    1. ``task:`` field present -> ``YAML_FRONTMATTER`` (single-task)
    2. ``feature:``/``slug:`` + ``tasks:`` present -> ``GLOBAL_MANIFEST``
    3. ``feature:``/``slug:`` without ``tasks:`` -> ``YAML_FRONTMATTER``
       (multi-task; per-task blocks are embedded in the body)
    4. ``tasks:`` without ``feature:``/``slug:`` -> ``YAML_FRONTMATTER``
       (tasks-list variant; tasks are inside the frontmatter list itself)

    Args:
        frontmatter_text: Raw YAML text between the opening and closing ``---``
            delimiters (the delimiters themselves are excluded).

    Returns:
        A ``FormatType`` value, or ``None`` if no match.
    """
    if _TASK_FIELD_RE.search(frontmatter_text):
        return FormatType.YAML_FRONTMATTER

    has_feature_or_slug = bool(_FEATURE_FIELD_RE.search(frontmatter_text))
    has_tasks_list = bool(_TASKS_LIST_RE.search(frontmatter_text))

    if has_feature_or_slug and has_tasks_list:
        return FormatType.GLOBAL_MANIFEST

    if has_feature_or_slug:
        return FormatType.YAML_FRONTMATTER

    # Tasks-list variant: ``tasks:`` list without a ``feature:``/``slug:`` field.
    # About 20 follow-up task files in ``plan/`` use this structure where the
    # entire task definition lives inside the frontmatter ``tasks:`` list and the
    # body below the closing ``---`` is human-readable prose only.
    if has_tasks_list:
        return FormatType.YAML_FRONTMATTER

    return None


def detect_format(path: Path) -> FormatType:
    """Detect the task/plan file format for a given path.

    Detection flowchart:
    1. If directory -> DIRECTORY (if contains plan.yaml or task files)
    2. If .yaml extension -> PURE_YAML
    3. If .md extension:
       a. Read first 20 lines
       b. If starts with ``---``: classify frontmatter via ``_classify_frontmatter``
       c. If contains ``## Task N:`` headings -> LEGACY_MARKDOWN
       d. Otherwise -> FormatDetectionError

    Args:
        path: Path to a task file or directory to inspect.

    Returns:
        A ``FormatType`` value identifying the file format.

    Raises:
        FormatDetectionError: If the path does not match any known format,
            with the file path and first 20 lines included in the message.
        FileNotFoundError: If the path does not exist.
    """
    if not path.exists():
        msg = f"Path does not exist: {path}"
        raise FileNotFoundError(msg)

    if path.is_dir():
        has_plan_yaml = (path / "plan.yaml").exists()
        has_yaml_files = bool(list(path.glob("*.yaml")))
        has_md_files = bool(list(path.glob("*.md")))
        if has_plan_yaml or has_yaml_files or has_md_files:
            return FormatType.DIRECTORY
        msg = f"Directory has no recognized task files: {path}"
        raise FormatDetectionError(path, msg)

    if path.suffix == ".yaml":
        return FormatType.PURE_YAML

    if path.suffix == ".md":
        content = path.read_text(encoding="utf-8")
        first_20_lines = "\n".join(content.splitlines()[:20])

        if content.startswith(("---\n", "---\r\n")):
            rest = content[4:]  # skip opening ---\n
            close_idx = rest.find("\n---")
            if close_idx >= 0:
                fmt = _classify_frontmatter(rest[:close_idx])
                if fmt is not None:
                    return fmt

        if _LEGACY_HEADING_RE.search(content):
            return FormatType.LEGACY_MARKDOWN

        raise FormatDetectionError(path, first_20_lines)

    raise FormatDetectionError(path, f"Unrecognized file extension: {path.suffix}")


def read_plan(path: Path) -> tuple[dict, list[dict], FormatType]:
    """Read a plan from any supported format.

    Detects the format via ``detect_format``, then delegates to the appropriate
    format-specific reader. Returns raw dicts — no Pydantic model construction.

    Args:
        path: Path to a task file or directory.

    Returns:
        A tuple of ``(plan_metadata_dict, task_dicts, format_type)`` where
        ``plan_metadata_dict`` contains plan-level fields (feature, version,
        description) and ``task_dicts`` is a list of raw per-task dicts.

    Raises:
        FormatDetectionError: If the format cannot be identified.
        FileNotFoundError: If the path does not exist.
    """
    # Import readers here to avoid circular imports — detect.py is the root
    # module that all readers import from, so top-level imports would create
    # a circular dependency.
    from sam_schema.readers.frontmatter_reader import read_frontmatter_plan  # noqa: PLC0415
    from sam_schema.readers.legacy_reader import read_legacy_plan  # noqa: PLC0415
    from sam_schema.readers.manifest_reader import read_manifest_plan  # noqa: PLC0415
    from sam_schema.readers.yaml_reader import read_yaml_plan  # noqa: PLC0415

    fmt = detect_format(path)

    if fmt in {FormatType.PURE_YAML, FormatType.DIRECTORY}:
        return read_yaml_plan(path)

    if fmt == FormatType.YAML_FRONTMATTER:
        return read_frontmatter_plan(path)

    if fmt == FormatType.GLOBAL_MANIFEST:
        return read_manifest_plan(path)

    if fmt == FormatType.LEGACY_MARKDOWN:
        return read_legacy_plan(path)

    # Should never reach here — detect_format raises for unknowns
    raise FormatDetectionError(path, f"Unhandled format type: {fmt}")  # pragma: no cover
