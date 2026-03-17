"""Global-manifest reader for SAM task/plan files.

Reads ``.md`` files with a global YAML frontmatter header containing plan
metadata (``feature:``, ``tasks:`` list) and per-task prose sections structured
as task headings in the markdown body.

This is the format that triggered issue #715 — the previous implementation
returned zero tasks for this format because no per-task YAML blocks were found.

The manifest format has a global frontmatter block containing:
- Plan-level metadata (feature, version, description, etc.)
- A ``tasks:`` list that holds task metadata in two possible structures:
  1. Simple ``{TN: "title"}`` mapping entries: ``- T1: State handler helper functions``
  2. Full task dicts: ``- {id: T1, title: "...", status: "not-started", ...}``
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sam_schema.core.models import TASK_ID_PATTERN
from sam_schema.readers._yaml_utils import coerce_to_plain, load_yaml, parse_prose_fields, split_outside_fences
from sam_schema.readers.detect import FormatType

if TYPE_CHECKING:
    from pathlib import Path

# Heading patterns for task prose sections in the body
# Matches: ## TN:, ## TN -, ### TN:, ### Task N:, #### TN
_TASK_SECTION_RE = re.compile(r"^(?:#{1,4})\s+(?:Task\s+)?([A-Za-z]?\d+(?:\.\d+)?)\s*[:\-]\s*(.*?)$", re.MULTILINE)

# Delimiter for splitting body into segments (same logic as frontmatter_reader)
_DELIMITER_RE = re.compile(r"^---+\s*$", re.MULTILINE)


def _extract_task_id_title_from_entry(entry: dict) -> tuple[str, str] | None:
    """Extract task ID and title from a ``tasks:`` list entry.

    Handles two entry formats:
    1. Simple single-key mapping: ``{T1: "State handler helper functions"}``
       YAML representation: ``- T1: State handler helper functions``
    2. Full task dict: ``{id: T1, title: "...", status: "not-started"}``

    Args:
        entry: A single item from the ``tasks:`` YAML list.

    Returns:
        ``(task_id, title)`` tuple, or ``None`` if the entry cannot be parsed.
    """
    if not isinstance(entry, dict):
        return None

    # Full task dict format: has ``id:`` or ``task:`` field
    if "id" in entry or "task" in entry:
        raw_id = str(entry.get("id") or entry.get("task") or "")
        if not raw_id:
            return None
        # If the value matches the task ID pattern, use it as the ID.
        # Otherwise treat the value as the title (single-task follow-up format:
        # ``task: "Constrain bookend_type to enum"``) and synthesise "T1".
        if TASK_ID_PATTERN.match(raw_id):
            task_id = raw_id
            title = str(entry.get("title") or "")
        else:
            task_id = "T1"
            title = str(entry.get("title") or raw_id)
        return (task_id, title)

    # Simple mapping format: ``{TN: "title"}`` — exactly one key
    if len(entry) == 1:
        key, value = next(iter(entry.items()))
        task_id = str(key)
        title = str(value) if value else ""
        return (task_id, title)

    return None


def _extract_prose_sections(body: str) -> dict[str, str]:
    """Extract prose content per task from the markdown body.

    Looks for headings matching task ID patterns (e.g., ``## T1:``, ``### T1 -``).

    Args:
        body: Markdown body text after the closing ``---`` of the frontmatter.

    Returns:
        Dict mapping task ID string to the prose body text for that task section.
    """
    section_matches = list(_TASK_SECTION_RE.finditer(body))
    sections: dict[str, str] = {}

    for idx, match in enumerate(section_matches):
        task_id = match.group(1)
        section_start = match.end()
        section_end = section_matches[idx + 1].start() if idx + 1 < len(section_matches) else len(body)
        prose = body[section_start:section_end].strip()
        sections[task_id] = prose

    return sections


def _split_body_outside_fences(body: str) -> list[str]:
    """Split a markdown body on ``---`` delimiters, ignoring those inside code fences.

    Delegates to the shared implementation in ``readers._yaml_utils``.

    Args:
        body: Markdown text that may contain YAML blocks separated by ``---`` lines.

    Returns:
        List of text segments split on delimiter lines outside code fences.
    """
    return split_outside_fences(body)


def _parse_body_prose_fields(prose: str) -> dict[str, str]:
    """Extract named content sections from a markdown prose segment.

    Delegates to the shared implementation in ``readers._yaml_utils``.

    Args:
        prose: Raw markdown text, possibly starting with section headings.

    Returns:
        Dict of canonical field name → text content.  Only non-empty sections
        are included.
    """
    return parse_prose_fields(prose)


def _try_parse_yaml_dict(text: str) -> dict | None:
    """Attempt to parse ``text`` as a YAML mapping.

    Returns the coerced plain dict on success, or ``None`` if parsing fails or
    the result is not a dict.  Used to classify body segments without raising.

    Args:
        text: Raw text that may or may not be valid YAML.

    Returns:
        Coerced plain dict, or ``None`` if not parseable as a YAML mapping.
    """
    try:
        result = load_yaml(text)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(result, dict):
        return None
    return coerce_to_plain(result)


def _extract_body_task_blocks(body: str) -> dict[str, dict]:
    """Extract per-task YAML blocks and their prose bodies from the markdown body.

    Used when a global-manifest file also embeds per-task YAML blocks in the
    body (each surrounded by ``---`` delimiters).  This is the hybrid format
    where the global frontmatter ``tasks:`` list provides the task registry and
    the body YAML blocks provide extended structured metadata plus prose content
    (Context, Acceptance Criteria, Verification Steps, etc.).

    The function splits the body into segments, identifies YAML blocks that
    contain a ``task:`` field, and captures the immediately following prose
    segment for content field extraction.

    Args:
        body: Markdown body text after the closing ``---`` of the frontmatter.

    Returns:
        Dict mapping task ID string to a merged dict containing:
        - All YAML fields from the task block (e.g., ``agent``, ``priority``,
          ``status``, ``dependencies``)
        - Prose content fields (e.g., ``description``, ``acceptance-criteria``,
          ``verification-steps``) extracted from the following prose segment.
        Returns an empty dict if no task YAML blocks are found.
    """
    segments = _split_body_outside_fences(body)

    # Parse each segment: classify as task YAML block, other YAML, or prose
    parsed: list[tuple[bool, object]] = []
    for raw_segment in segments:
        segment = raw_segment.strip()
        if not segment:
            parsed.append((False, ""))
            continue
        block = _try_parse_yaml_dict(segment)
        if block is not None:
            is_task = bool(block.get("task") or block.get("task_id"))
            parsed.append((is_task, block))
        else:
            parsed.append((False, segment))

    task_blocks: dict[str, dict] = {}

    for idx, (is_task, payload) in enumerate(parsed):
        if not is_task:
            continue

        block = dict(payload)  # type: ignore[arg-type]
        task_id = str(block.get("task") or block.get("task_id") or "")
        if not task_id:
            continue

        # Ensure the canonical ``task`` key is set
        block["task"] = task_id

        # Look ahead for a prose segment immediately following this task block
        next_idx = idx + 1
        while next_idx < len(parsed):
            next_is_task, next_payload = parsed[next_idx]
            if isinstance(next_payload, str) and not next_payload:
                next_idx += 1
                continue
            if not next_is_task and isinstance(next_payload, str) and next_payload:
                prose_fields = _parse_body_prose_fields(next_payload)
                for field, value in prose_fields.items():
                    block.setdefault(field, value)
            break

        task_blocks[task_id] = block

    return task_blocks


def _resolve_task_id_from_dict(task_dict: dict) -> str | None:
    """Extract or synthesise a task ID from a full task dict entry.

    When the ``id:`` or ``task:`` value matches ``TASK_ID_PATTERN``, it is used
    as-is.  When it is a description string (single-task follow-up format), the
    synthetic ID ``"T1"`` is returned and the description string is promoted to
    ``title`` in ``task_dict`` (mutates in place).

    Args:
        task_dict: Mutable copy of a raw task entry dict.

    Returns:
        Task ID string, or ``None`` if no usable ID can be extracted.
    """
    raw_id = str(task_dict.get("id") or task_dict.get("task") or "")
    if not raw_id:
        return None
    if TASK_ID_PATTERN.match(raw_id):
        return raw_id
    # Description string used as task: value — synthesise "T1"
    if not task_dict.get("title"):
        task_dict["title"] = raw_id
    task_dict["task"] = "T1"
    return "T1"


def _build_task_dict(
    entry: dict, prose_by_task: dict[str, str], body_task_blocks: dict[str, dict] | None = None
) -> dict | None:
    """Build a raw task dict from a manifest ``tasks:`` entry.

    Merges structured fields from three sources, in priority order:

    1. **Frontmatter entry** — provides task ID, title, and any fields explicitly
       set in the ``tasks:`` list.  These values take precedence because the
       frontmatter is the authoritative registry.
    2. **Body YAML block** — if the body contains a per-task YAML block matching
       this task ID (the hybrid format used by some plan files), its structured
       fields (``agent``, ``priority``, ``dependencies``, ``status``, etc.) and
       prose content fields (``description``, ``acceptance-criteria``, etc.) fill
       in any gaps not covered by the frontmatter entry.
    3. **Prose section** — if the body contains a ``## TN:`` prose section, its
       text is used as ``description`` if no other source provided it.

    Args:
        entry: A coerced dict entry from the ``tasks:`` YAML list.
        prose_by_task: Map from task ID to prose text from ``## TN:`` sections.
        body_task_blocks: Optional map from task ID to merged dict from
            ``_extract_body_task_blocks``.  Pass ``None`` to skip body block lookup.

    Returns:
        Raw task dict, or ``None`` if the entry cannot be parsed.
    """
    if not isinstance(entry, dict):
        return None

    # Full task dict: has ``id:`` or ``task:`` field
    if "id" in entry or "task" in entry:
        task_dict = dict(entry)
        task_id = _resolve_task_id_from_dict(task_dict)
        if not task_id:
            return None
        task_dict.setdefault("task", task_id)
        # Merge body YAML block fields (fill gaps not set in the frontmatter entry)
        if body_task_blocks:
            for field, value in body_task_blocks.get(task_id, {}).items():
                task_dict.setdefault(field, value)
        # Fall back to prose section for description
        prose = prose_by_task.get(task_id, "")
        if prose:
            task_dict.setdefault("description", prose)
        return task_dict

    # Simple single-key mapping: {TN: "title"}
    parsed = _extract_task_id_title_from_entry(entry)
    if not parsed:
        return None
    task_id, title = parsed
    task_dict: dict = {"task": task_id, "title": title}
    # Merge body YAML block fields (provides full structured metadata + prose content).
    # Body blocks may contain per-task status, timestamps, and other fields that
    # override the simple-mapping defaults.
    if body_task_blocks:
        for field, value in body_task_blocks.get(task_id, {}).items():
            task_dict.setdefault(field, value)
    # Default status only if neither the entry nor the body block provided one
    task_dict.setdefault("status", "not-started")
    # Fall back to prose section for description
    prose = prose_by_task.get(task_id, "")
    if prose:
        task_dict.setdefault("description", prose)
    return task_dict


def _is_single_followup_format(
    tasks_raw: list, body: str, prose_by_task: dict[str, str], body_task_blocks: dict[str, dict]
) -> bool:
    """Return True when the file is a single-task follow-up with flat body prose.

    A single-task follow-up file has exactly one entry in ``tasks:`` where the
    ``task:`` value is a description string (not a structured ID like ``T1``).
    The body is flat prose (e.g. ``## Description``, ``## Acceptance Criteria``)
    that belongs to that one task rather than multi-task structured content.

    Args:
        tasks_raw: Raw ``tasks:`` list from frontmatter.
        body: Markdown body text after the closing ``---``.
        prose_by_task: Map from task ID to prose from ``## TN:`` headings.
        body_task_blocks: Map from task ID to YAML blocks in the body.

    Returns:
        ``True`` when the file matches the single-task follow-up format.
    """
    if len(tasks_raw) != 1 or not body or prose_by_task or body_task_blocks:
        return False
    first = tasks_raw[0]
    if not isinstance(first, dict):
        return False
    raw_val = str(first.get("task") or first.get("task_id") or "")
    return bool(raw_val) and not TASK_ID_PATTERN.match(raw_val)


def _parse_manifest_frontmatter(path: Path, content: str) -> tuple[dict, list, str]:
    """Split a manifest file into plan metadata, raw task list, and body.

    Args:
        path: Source path (used in error messages only).
        content: Full file text.

    Returns:
        ``(plan_meta, tasks_raw, body)`` where ``plan_meta`` is the frontmatter
        dict (without ``tasks:``), ``tasks_raw`` is the raw ``tasks:`` list, and
        ``body`` is the markdown text after the closing ``---``.

    Raises:
        ValueError: If frontmatter delimiters are missing or ``tasks:`` is absent.
        TypeError: If frontmatter is not a mapping or ``tasks:`` is not a list.
    """
    if not content.startswith(("---\n", "---\r\n")):
        msg = f"Expected file to start with '---' frontmatter: {path}"
        raise ValueError(msg)

    after_open = content[4:]
    close_match = re.search(r"\n---\s*\n", after_open)
    if not close_match:
        msg = f"No closing '---' found for frontmatter block in {path}"
        raise ValueError(msg)

    parsed_fm = load_yaml(after_open[: close_match.start()])
    if not isinstance(parsed_fm, dict):
        msg = f"Expected a YAML mapping in frontmatter of {path}, got {type(parsed_fm).__name__}"
        raise TypeError(msg)

    parsed_fm = coerce_to_plain(parsed_fm)
    tasks_raw = parsed_fm.pop("tasks", None)

    plan_meta = dict(parsed_fm)
    if "feature" not in plan_meta and "slug" in plan_meta:
        plan_meta["feature"] = plan_meta.pop("slug")
    if "feature" not in plan_meta:
        plan_meta["feature"] = re.sub(r"^tasks-\d+-", "", path.stem)

    if not tasks_raw:
        msg = f"No 'tasks:' list found in frontmatter of {path}"
        raise ValueError(msg)
    if not isinstance(tasks_raw, list):
        msg = f"Expected 'tasks:' to be a list in {path}"
        raise TypeError(msg)

    return plan_meta, tasks_raw, after_open[close_match.end() :]


def read_manifest_plan(path: Path) -> tuple[dict, list[dict], FormatType]:
    """Read a global-manifest format plan file.

    The global manifest format has:
    - A single YAML frontmatter block at the top with plan-level metadata
      and a ``tasks:`` list containing task metadata (simple or full dicts).
    - A markdown body with optional task prose sections.

    The reader merges the structured task metadata from the YAML ``tasks:`` list
    with any prose content from the matching body sections.

    Args:
        path: Path to a ``.md`` file with a global manifest frontmatter structure.

    Returns:
        A tuple of ``(plan_meta_dict, task_dicts, FormatType.GLOBAL_MANIFEST)``
        where each task dict contains both the structured fields from the YAML
        ``tasks:`` list and any prose content from the body sections.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the frontmatter cannot be parsed or has no recognized task list.
    """
    if not path.exists():
        msg = f"Path does not exist: {path}"
        raise FileNotFoundError(msg)

    plan_meta, tasks_raw, body = _parse_manifest_frontmatter(path, path.read_text(encoding="utf-8"))

    # Extract prose sections from body keyed by task ID (## TN: heading format)
    prose_by_task = _extract_prose_sections(body)

    # Extract per-task YAML blocks from body (hybrid format: global frontmatter +
    # embedded per-task YAML blocks with prose).  Returns empty dict when absent.
    body_task_blocks = _extract_body_task_blocks(body)

    # For single-task follow-up files (task: value is a description string, not a
    # structured ID), parse the full body as flat prose so that ## Description,
    # ## Acceptance Criteria, etc. are captured.  Guard: only when prose_by_task
    # and body_task_blocks are both empty (no multi-task structured content).
    flat_body_prose: dict[str, str] = (
        _parse_body_prose_fields(body)
        if _is_single_followup_format(tasks_raw, body, prose_by_task, body_task_blocks)
        else {}
    )

    # Build per-task dicts by merging frontmatter entry + body YAML block + prose
    task_dicts: list[dict] = []
    for entry in (coerce_to_plain(raw) for raw in tasks_raw):
        task_dict = _build_task_dict(entry, prose_by_task, body_task_blocks or None)
        if task_dict is not None:
            # Inject flat body prose fields for synthesised single-task files
            if flat_body_prose:
                for field, value in flat_body_prose.items():
                    task_dict.setdefault(field, value)
            task_dicts.append(task_dict)

    return plan_meta, task_dicts, FormatType.GLOBAL_MANIFEST
