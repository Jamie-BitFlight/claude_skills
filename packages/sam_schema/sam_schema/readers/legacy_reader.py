"""Legacy markdown reader for SAM task/plan files.

Reads ``.md`` files using the deprecated ``## Task N: Title`` heading format
with ``**Field**: Value`` inline markers. This format predates the YAML
frontmatter standard and is supported as read-only for backward compatibility.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sam_schema.readers.detect import FormatType

if TYPE_CHECKING:
    from pathlib import Path

# Pattern for ``## Task N: Title`` headings (e.g., ``## Task 1: Create Models``)
_TASK_HEADING_RE = re.compile(r"^##\s+Task\s+(\d+(?:\.\d+)?)\s*:?\s*(.*?)$", re.MULTILINE)

# Pattern for ``**FieldName**: value`` inline markers
_FIELD_MARKER_RE = re.compile(r"^\*\*([A-Za-z][A-Za-z0-9 _-]*)\*\*\s*:\s*(.+)$", re.MULTILINE)

# Plan-level heading patterns
_PLAN_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Map from bold-marker field names to canonical YAML field names
_FIELD_NAME_MAP: dict[str, str] = {
    "Status": "status",
    "Agent": "agent",
    "Dependencies": "dependencies",
    "Priority": "priority",
    "Complexity": "complexity",
    "Skills": "skills",
    "Started": "started",
    "Completed": "completed",
    "Last Activity": "last-activity",
    "LastActivity": "last-activity",
    "Blocked By": "blocked-by",
    "Parallelize With": "parallelize-with",
    "Issue Classification": "issue-classification",
    "Scenario Target": "scenario-target",
    "Analysis Method": "analysis-method",
    "Divergence Notes": "divergence-notes",
    "GitHub Issue": "github-issue",
}


def _parse_field_value(field_name: str, raw_value: str) -> object:  # noqa: PLR0911
    """Convert a raw inline field value to the appropriate Python type.

    Args:
        field_name: Canonical field name (e.g., ``"dependencies"``).
        raw_value: Raw string value from the markdown marker.

    Returns:
        Parsed value: list for list-like fields, int for integer fields,
        None for explicit "none"/"n/a" values, otherwise the string as-is.
    """
    raw = raw_value.strip()

    # List fields
    if field_name in {"dependencies", "skills", "blocked-by", "parallelize-with"}:
        if raw.lower() in {"none", "n/a", "-", "[]", ""}:
            return []
        # Handle inline lists: ``T1, T2`` or ``Task 1, Task 2`` or ``[T1, T2]``
        raw = raw.strip("[]")
        return [item.strip() for item in re.split(r"[,;]", raw) if item.strip()]

    # Integer fields
    if field_name == "divergence-notes":
        try:
            return int(raw)
        except ValueError:
            return 0

    # Priority: convert string "1" to int
    if field_name == "priority":
        try:
            return int(raw)
        except ValueError:
            return raw

    # Complexity is a StrEnum with lowercase values — normalize title-case from legacy files
    if field_name == "complexity":
        return raw.lower()

    # Null-like values
    if raw.lower() in {"none", "n/a", "-"}:
        return None

    return raw


_PROSE_HEADING_RE = re.compile(r"^(?:#{3,4})\s+(.+)$", re.MULTILINE)

# Map heading names (lowercase) to canonical task field names
_PROSE_HEADING_TO_FIELD: dict[str, str] = {
    "context": "description",
    "background": "description",
    "problem": "description",
    "objective": "objective",
    "requirements": "requirements",
    "constraints": "constraints",
    "expected outputs": "expected-outputs",
    "expected output": "expected-outputs",
    "acceptance criteria": "acceptance-criteria",
    "acceptance": "acceptance-criteria",
    "verification steps": "verification-steps",
    "verification": "verification-steps",
    "cove checks": "verification-steps",
    "cove": "verification-steps",
    "context notes": "context-notes",
    "handoff": "handoff",
    "test requirements": "acceptance-criteria",
    "changes required": "requirements",
}


def _extract_prose_subsections(section_body: str) -> dict[str, str]:
    """Extract named prose subsections from a legacy task section body.

    Looks for ``###`` and ``####`` headings and maps their content to canonical
    task field names.  ``##`` headings are intentionally excluded because those
    mark the boundaries between tasks in the legacy format.

    Args:
        section_body: The raw text of a ``## Task N:`` section (excluding the
            task heading line itself).

    Returns:
        Dict of canonical field name → text content.  Only non-empty sections
        are included.
    """
    matches = list(_PROSE_HEADING_RE.finditer(section_body))
    result: dict[str, str] = {}

    for idx, match in enumerate(matches):
        heading_text = match.group(1).strip()
        field = _PROSE_HEADING_TO_FIELD.get(heading_text.lower())
        if field is None:
            continue

        section_start = match.end()
        section_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_body)
        content = section_body[section_start:section_end].strip()
        if not content:
            continue

        if field in result:
            result[field] = result[field] + "\n\n" + content
        else:
            result[field] = content

    return result


def _extract_section_task(content: str, heading_matches: list, idx: int) -> dict:
    """Extract a raw task dict from a single ``## Task N:`` section.

    Args:
        content: Full file content.
        heading_matches: All ``## Task N:`` regex matches.
        idx: Index of the current match.

    Returns:
        Raw task dict with ``task``, ``title``, ``status``, and any other
        extracted fields, including prose subsection content fields.
    """
    match = heading_matches[idx]
    task_num: str = match.group(1)
    task_title: str = match.group(2).strip()

    section_start = match.end()
    next_idx = idx + 1
    section_end = heading_matches[next_idx].start() if next_idx < len(heading_matches) else len(content)
    section_body = content[section_start:section_end]

    task_dict: dict = {"task": task_num, "title": task_title}
    for field_match in _FIELD_MARKER_RE.finditer(section_body):
        display_name = field_match.group(1).strip()
        raw_value = field_match.group(2).strip()
        canonical = _FIELD_NAME_MAP.get(display_name)
        if canonical:
            parsed_value = _parse_field_value(canonical, raw_value)
            if parsed_value is not None:
                task_dict[canonical] = parsed_value

    # Extract prose subsections (### Acceptance Criteria, ### Problem, etc.)
    for field, value in _extract_prose_subsections(section_body).items():
        task_dict.setdefault(field, value)

    task_dict.setdefault("status", "not-started")
    return task_dict


def read_legacy_plan(path: Path) -> tuple[dict, list[dict], FormatType]:
    """Read a legacy ``## Task N:`` markdown plan file.

    Extracts tasks using heading detection (``## Task {N}: {Title}``) and
    field extraction (``**{Field}**: {Value}``). Returns raw dicts with
    field names normalized to the canonical YAML schema names where possible.

    Fields extracted per task:
    - ``task`` (from heading number)
    - ``title`` (from heading text)
    - ``status`` (from ``**Status**:`` marker)
    - ``dependencies`` (from ``**Dependencies**:`` marker)
    - ``agent`` (from ``**Agent**:`` marker)
    - ``priority`` (from ``**Priority**:`` marker)
    - ``complexity`` (from ``**Complexity**:`` marker)

    Args:
        path: Path to a ``.md`` file with legacy ``## Task N:`` structure.

    Returns:
        A tuple of ``(plan_meta_dict, task_dicts, FormatType.LEGACY_MARKDOWN)``.
        ``plan_meta_dict`` will have ``feature`` derived from the filename if no
        explicit plan header is found.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If no task headings are found.
    """
    if not path.exists():
        msg = f"Path does not exist: {path}"
        raise FileNotFoundError(msg)

    content = path.read_text(encoding="utf-8")

    # Extract plan-level metadata from the first # heading
    plan_meta: dict = {}
    title_match = _PLAN_TITLE_RE.search(content)
    if title_match:
        plan_meta["feature"] = title_match.group(1).strip()
    else:
        # Synthesize feature name from filename by stripping "tasks-N-" prefix
        slug = re.sub(r"^tasks-\d+-", "", path.stem)
        plan_meta["feature"] = slug

    # Find all task headings and their positions
    heading_matches = list(_TASK_HEADING_RE.finditer(content))
    if not heading_matches:
        msg = f"No '## Task N:' headings found in {path}"
        raise ValueError(msg)

    task_dicts = [_extract_section_task(content, heading_matches, idx) for idx in range(len(heading_matches))]

    return plan_meta, task_dicts, FormatType.LEGACY_MARKDOWN
