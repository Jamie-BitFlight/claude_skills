"""Normalizer: convert raw reader dicts to validated Pydantic models.

Takes the raw ``(plan_meta_dict, task_dicts, format_type)`` output from any
reader and produces a ``ReadResult`` containing validated ``Plan`` and
``Task`` models plus a list of ``SchemaGap`` records for any fields that are
missing or have unexpected types.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from sam_schema.core.models import STATUS_MAP, Plan, ReadResult, SchemaGap, Task, TaskStatus
from sam_schema.readers.detect import FormatType

if TYPE_CHECKING:
    from pathlib import Path

# Optional fields to check for schema gaps (field_name -> human-readable description)
_GAP_FIELDS: dict[str, str] = {
    "agent": "Agent responsible for task",
    "priority": "Priority level 1-5",
    "complexity": "Complexity: low/medium/high",
    "skills": "Skills list for sub-agent",
    "blocked-by": "External blockers",
    "parallelize-with": "Concurrent task IDs",
    "created": "ISO 8601 creation timestamp",
    "issue-classification": "Analytical classification",
    "scenario-target": "Scenario -> improvement",
    "analysis-method": "Root-cause method",
}

# Canonical formats where schema gaps are NOT reported
# (gaps are only meaningful for legacy/non-canonical formats)
_CANONICAL_FORMATS: frozenset[FormatType] = frozenset({FormatType.PURE_YAML, FormatType.DIRECTORY})

# Pre-built frozenset of canonical status string values.
# Built once at module import time instead of inside _normalize_status on every call.
_VALID_STATUSES: frozenset[str] = frozenset(s.value for s in TaskStatus)


def _normalize_status(raw: Any) -> str:  # noqa: ANN401, PLR0911
    """Normalize a raw status value to a canonical TaskStatus string.

    Args:
        raw: Raw status value from YAML or markdown.

    Returns:
        Canonical status string (e.g., ``"not-started"``).

    Raises:
        ValueError: If ``raw`` is a non-None string that cannot be mapped to a
                    known ``TaskStatus`` value. Callers must handle this explicitly
                    so that unrecognized status values are never silently accepted.
    """
    if raw is None:
        return TaskStatus.NOT_STARTED.value

    text = str(raw).strip()
    text_lower = text.lower()

    # Fast path: already a canonical lowercase value (common case for PURE_YAML).
    # Check this before paying the regex cost for emoji stripping.
    if text_lower in _VALID_STATUSES:
        return text_lower

    # Strip a leading Rich emoji token (e.g., ``:white_check_mark: COMPLETE`` -> ``COMPLETE``)
    # Legacy markdown stores status as ``**Status**: :emoji_token: LABEL``.
    emoji_stripped = re.sub(r"^:[A-Za-z0-9_]+:\s*", "", text).strip()
    if emoji_stripped and emoji_stripped != text:
        # Recurse with the stripped value so all downstream rules apply
        return _normalize_status(emoji_stripped)

    # Strip leading Unicode emoji characters (e.g., ``✅ COMPLETE`` -> ``COMPLETE``)
    # Legacy markdown authored with Unicode emoji instead of Rich colon-tokens.
    # Ranges covered:
    #   \u2300-\u27FF — Miscellaneous Technical (⏳ U+23F3), Dingbats (✅ U+2705, ❌ U+274C)
    #   \u2B00-\u2BFF — Miscellaneous Symbols and Arrows
    #   \U0001F000-\U0010FFFF — Supplementary emoji blocks (all planes above BMP)
    unicode_stripped = re.sub(r"^[\u2300-\u27FF\u2B00-\u2BFF\U0001F000-\U0010FFFF]+\s*", "", text).strip()
    if unicode_stripped and unicode_stripped != text:
        return _normalize_status(unicode_stripped)

    text_upper = text.upper()

    # STATUS_MAP lookup (handles space-separated, emoji, etc.)
    if text in STATUS_MAP:
        mapped = STATUS_MAP[text]
        # STATUS_MAP values may be canonical strings or TaskStatus-like strings
        if mapped in _VALID_STATUSES:
            return mapped
        # Try lowercase lookup after mapping
        mapped_lower = mapped.lower()
        if mapped_lower in _VALID_STATUSES:
            return mapped_lower

    # Case-insensitive space-separated match (e.g., "NOT STARTED")
    if text_upper in STATUS_MAP:
        mapped = STATUS_MAP[text_upper]
        if mapped in _VALID_STATUSES:
            return mapped

    msg = f"Unrecognized status value: {raw!r}. Valid values are: {sorted(_VALID_STATUSES)}"
    raise ValueError(msg)


def _resolve_task_id(raw: dict) -> str | None:
    """Extract task ID from a raw dict using field aliases.

    Tries ``task``, then ``task_id``, then ``id`` for backward compatibility.

    Args:
        raw: Raw task dict from a reader.

    Returns:
        Task ID string, or ``None`` if not found.
    """
    for key in ("task", "task_id", "id"):
        val = raw.get(key)
        if val is not None:
            return str(val)
    return None


def detect_gaps(raw: dict, task_id: str) -> list[SchemaGap]:
    """Compare a raw task dict against all optional canonical fields.

    Reports a ``SchemaGap`` for every optional field absent from ``raw``.
    Unlike the internal ``_detect_gaps``, this function does **not** filter by
    format — it is intended for direct callers that want unconditional gap
    analysis.

    Args:
        raw: Raw task dict (kebab-case or snake_case keys).
        task_id: Task ID to attach to each ``SchemaGap`` record.

    Returns:
        List of ``SchemaGap`` records for missing optional fields.
    """
    gaps: list[SchemaGap] = []
    for field_name, description in _GAP_FIELDS.items():
        snake = field_name.replace("-", "_")
        if field_name not in raw and snake not in raw:
            gaps.append(SchemaGap(task_id=task_id, field_name=field_name, gap_type="missing", expected=description))
    return gaps


def _detect_gaps(raw: dict, task_id: str, source_format: FormatType) -> list[SchemaGap]:
    """Compare a raw task dict against optional canonical fields.

    Only reports gaps for non-canonical formats (legacy, frontmatter, manifest).
    Canonical formats (PURE_YAML, DIRECTORY) are assumed to be complete.

    Args:
        raw: Raw task dict from a reader.
        task_id: Task ID for gap records.
        source_format: Format the task was read from.

    Returns:
        List of ``SchemaGap`` records for missing optional fields.
    """
    if source_format in _CANONICAL_FORMATS:
        return []
    return detect_gaps(raw, task_id)


_TASK_PREFIX_RE = re.compile(r"^Task\s+", re.IGNORECASE)


def _clean_dependency_list(deps: list[str]) -> list[str]:
    """Strip 'Task N' legacy prefix from dependency IDs.

    Legacy format stores dependencies as 'Task 1', 'Task 2' etc.
    Strip the 'Task ' prefix to yield bare IDs ('1', '2') that match
    the task ID validation pattern.

    Args:
        deps: Raw dependency list from a reader.

    Returns:
        Dependency list with 'Task ' prefixes stripped.
    """
    return [_TASK_PREFIX_RE.sub("", dep) for dep in deps]


def normalize_task(raw: dict, source_format: FormatType) -> tuple[Task, list[SchemaGap]]:
    """Convert a raw task dict from any reader into a validated ``Task`` model.

    The raw dict uses YAML field names (kebab-case aliases are accepted by Pydantic
    because ``populate_by_name=True`` is set and aliases are defined on the model).
    The ``status`` field is normalized before construction.

    Args:
        raw: Raw dict produced by a format-specific reader. Keys may be in
             kebab-case (YAML aliases) or snake_case.
        source_format: The format the dict was read from, used to decide which
                       fields to report as gaps.

    Returns:
        A tuple of ``(task, gaps)`` where ``task`` is a validated ``Task`` instance
        and ``gaps`` is a list of ``SchemaGap`` records for missing optional fields.

    Raises:
        ValueError: If required fields (``task``/``id``, ``title``, ``status``)
                    are missing or invalid.
    """
    task_id = _resolve_task_id(raw)
    if not task_id:
        msg = "Task dict is missing required 'task' or 'id' field"
        raise ValueError(msg)

    title = raw.get("title") or raw.get("name")
    if not title:
        msg = f"Task '{task_id}' is missing required 'title' field"
        raise ValueError(msg)

    # Build normalized dict for Pydantic construction
    # Start from the raw dict so we pass through all fields (Pydantic ignores extras by default)
    normalized: dict[str, Any] = dict(raw)

    # Normalize the ``task`` field to ``id`` so Pydantic finds it
    # The Task model uses ``id`` as the Python attribute name
    normalized["id"] = task_id
    normalized.setdefault("task", task_id)

    # Normalize status
    raw_status = normalized.get("status")
    normalized["status"] = _normalize_status(raw_status)

    # Normalize title (accept ``name`` as alias for backward compat)
    if "title" not in normalized and "name" in normalized:
        normalized["title"] = normalized.pop("name")

    # Title-based status override: ``[DEFERRED]`` or ``[SKIPPED]`` prefix in title
    # takes precedence over the stored status value (e.g., legacy tasks marked in title only)
    effective_title = str(normalized.get("title", ""))
    for marker, overridden_status in (("[DEFERRED]", "deferred"), ("[SKIPPED]", "skipped")):
        if effective_title.startswith(marker):
            normalized["status"] = overridden_status
            break

    # Clean legacy "Task N" prefix from dependency lists (legacy_reader emits raw values)
    for dep_field in ("dependencies", "blocked-by", "blocked_by"):
        if dep_field in normalized and isinstance(normalized[dep_field], list):
            normalized[dep_field] = _clean_dependency_list(normalized[dep_field])

    # Coerce task-level str fields that may arrive as YAML lists to newline-joined strings.
    # Plan files authored by agents may write acceptance_criteria and verification_steps as
    # YAML bullet lists (list[str]) rather than multiline scalars.  The Task model declares
    # these as str; Pydantic raises ValidationError on list input, causing the task to be
    # silently dropped in normalize_plan().  Joining here preserves the content.
    TASK_STR_FIELDS: tuple[str, ...] = (
        "acceptance_criteria",
        "acceptance-criteria",
        "verification_steps",
        "verification-steps",
        "description",
        "objective",
        "requirements",
        "constraints",
        "expected_outputs",
        "expected-outputs",
        "context_notes",
        "context-notes",
        "handoff",
    )
    for field in TASK_STR_FIELDS:
        if field in normalized and isinstance(normalized[field], list):
            normalized[field] = "\n".join(str(item) for item in normalized[field])

    # Detect schema gaps before constructing the model
    gaps = _detect_gaps(raw, task_id, source_format)

    # Construct the Task model — Pydantic validates all fields
    try:
        task = Task.model_validate(normalized)
    except Exception as exc:
        msg = f"Failed to construct Task for id='{task_id}': {exc}"
        raise ValueError(msg) from exc

    return task, gaps


def normalize_task_lenient(raw: dict, source_format: FormatType) -> tuple[Task | None, list[SchemaGap]]:
    """Attempt ``normalize_task`` and return ``None`` on validation failure instead of raising.

    Use this in contexts where individual task failures should not abort the
    entire plan normalization.

    Args:
        raw: Raw dict from a reader.
        source_format: Source format for gap detection.

    Returns:
        ``(task, gaps)`` on success, or ``(None, [gap])`` on validation failure
        where ``gap`` documents the failure reason. The gap list is never empty on
        failure so callers always receive diagnostic information.
    """
    try:
        return normalize_task(raw, source_format)
    except ValueError as exc:
        task_id = _resolve_task_id(raw) or "<unknown>"
        failure_gap = SchemaGap(
            task_id=task_id,
            field_name="id",
            gap_type="invalid_value",
            expected="Valid task with required fields (task id, title) and recognized status",
            actual=str(exc),
        )
        return None, [failure_gap]


def normalize_plan(plan_meta: dict, task_dicts: list[dict], source_format: FormatType, source_path: Path) -> ReadResult:
    """Normalize an entire plan from raw reader output to validated models.

    Calls ``normalize_task`` for each task dict and collects all schema gaps.

    Args:
        plan_meta: Raw plan-level metadata dict (feature, version, description).
        task_dicts: List of raw per-task dicts from a format-specific reader.
        source_format: Format type used for gap reporting logic.
        source_path: Absolute path to the source file or directory.

    Returns:
        A ``ReadResult`` containing the validated ``Plan`` and all ``SchemaGap``
        records from normalization.

    Raises:
        ValueError: If ``plan_meta`` has no ``feature`` field.
    """
    feature = plan_meta.get("feature") or plan_meta.get("slug")
    if not feature:
        # Derive slug from filename convention: tasks-{N}-{slug}.md or
        # tasks-{N}-{slug}-followup-{K}.md (auto-generated by code reviewer).
        stem = source_path.stem  # filename without extension
        slug_match = re.match(r"^tasks-\d+-(.+)$", stem)
        if slug_match:
            feature = slug_match.group(1)
        else:
            msg = f"Plan metadata has no 'feature' field and filename '{source_path.name}' does not match 'tasks-N-slug' convention: {plan_meta}"
            raise ValueError(msg)

    tasks: list[Task] = []
    all_gaps: list[SchemaGap] = []

    for raw_task in task_dicts:
        try:
            task, gaps = normalize_task(raw_task, source_format)
        except ValueError as exc:
            # Record a schema gap for the failing task instead of aborting
            raw_id = _resolve_task_id(raw_task) or "<unknown>"
            all_gaps.append(
                SchemaGap(
                    task_id=raw_id,
                    field_name="id",
                    gap_type="invalid_value",
                    expected="Task ID matching pattern ^[A-Za-z]?\\d+(\\.\\d+)?$",
                    actual=str(exc),
                )
            )
            continue
        tasks.append(task)
        all_gaps.extend(gaps)

    # Resolve acceptance-criteria-structured: accept both kebab-case and snake_case keys.
    # Each item is a dict from YAML; Pydantic coerces dicts to AcceptanceCriterion via
    # model_validate when the Plan model is constructed.
    raw_structured: list[object] = (
        plan_meta.get("acceptance-criteria-structured") or plan_meta.get("acceptance_criteria_structured") or []
    )

    def _coerce_str(value: Any) -> str | None:  # noqa: ANN401
        """Coerce a YAML value to ``str | None``.

        YAML lists (e.g. ``acceptance-criteria`` written as a bullet list) are
        joined with newlines so they satisfy ``str | None`` Plan fields.  Other
        non-None values are converted via ``str()``.  Falsy values (empty string,
        empty list) are normalised to ``None``.

        Returns:
            Coerced string, or ``None`` for absent/empty values.
        """
        if value is None:
            return None
        if isinstance(value, list):
            joined = "\n".join(str(item) for item in value)
            return joined or None
        result = str(value)
        return result or None

    ac = plan_meta.get("acceptance-criteria") or plan_meta.get("acceptance_criteria")

    plan = Plan(
        plan_id=_coerce_str(plan_meta.get("plan-id") or plan_meta.get("plan_id")),
        feature=str(feature),
        version=str(plan_meta.get("version", "1.0")),
        description=str(plan_meta.get("description", "")),
        goal=_coerce_str(plan_meta.get("goal")),
        context=_coerce_str(plan_meta.get("context")),
        acceptance_criteria=_coerce_str(ac),
        acceptance_criteria_structured=raw_structured,
        issue=plan_meta.get("issue") or None,
        architecture=_coerce_str(plan_meta.get("architecture")),
        feature_context=_coerce_str(plan_meta.get("feature-context") or plan_meta.get("feature_context")),
        codebase_patterns=_coerce_str(plan_meta.get("codebase-patterns") or plan_meta.get("codebase_patterns")),
        tasks=tasks,
        source_path=source_path,
        source_format=source_format.value,
    )

    return ReadResult(plan=plan, gaps=all_gaps, source_format=source_format.value, source_path=source_path)
