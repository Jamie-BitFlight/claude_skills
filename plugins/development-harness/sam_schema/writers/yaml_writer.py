"""Pure YAML writer for SAM task/plan files.

Writes ``Plan`` models to ``.yaml`` files using ``ruamel.yaml`` round-trip mode
to preserve comments and field order. Supports single-file and directory output
layouts. All writes use atomic rename to prevent partial files on crash.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

if TYPE_CHECKING:
    from sam_schema.core.models import Plan, Task

# Plans whose YAML serialization exceeds this line count are split into a
# directory of per-task files instead of a single flat file.
LINE_THRESHOLD: int = 500

# Fields that contain markdown prose — serialized as YAML literal block scalars (|).
# Includes both task-level and plan-level markdown fields.
_MARKDOWN_FIELDS: frozenset[str] = frozenset({
    # Task-level markdown fields
    "description",
    "objective",
    "requirements",
    "constraints",
    "expected-outputs",
    "acceptance-criteria",
    "verification-steps",
    "context-notes",
    "handoff",
    # Plan-level markdown fields
    "goal",
    "context",
})

# field-specific defaults: omit these from YAML output when the value equals the default.
_SKIP_IF_DEFAULT: dict[str, Any] = {
    "analysis-method": "none",
    "divergence-notes": 0,
    # Bookend fields: omit when task is not a bookend (default values)
    "is-bookend": False,
    "bookend-type": None,
}


def _make_yaml() -> YAML:
    """Create a ruamel.yaml instance configured for round-trip mode.

    Returns:
        Configured ``YAML`` instance with round-trip mode enabled and
        default settings for human-readable output.
    """
    y = YAML(typ="rt")
    y.default_flow_style = False
    return y


def _task_to_dict(task: Task) -> dict[str, Any]:
    """Convert a ``Task`` model to a clean dict for YAML serialization.

    Excludes empty/default values to keep YAML output concise.
    Converts multiline string fields to ``LiteralScalarString`` so ruamel.yaml
    emits them as YAML literal block scalars (``|``).

    Args:
        task: A ``Task`` model instance.

    Returns:
        Ordered dict with kebab-case field names, ready for YAML serialization.
    """
    raw: dict[str, Any] = task.model_dump(by_alias=True, mode="json")

    result: dict[str, Any] = {}
    for key, value in raw.items():
        # Skip source/internal fields not stored in YAML
        if key in {"source_path", "source_format"}:
            continue
        # Skip None
        if value is None:
            continue
        # Skip empty strings and empty lists
        if isinstance(value, str) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        # Skip field-specific defaults
        if key in _SKIP_IF_DEFAULT and value == _SKIP_IF_DEFAULT[key]:
            continue
        # Convert multiline markdown fields to literal block scalars
        if key in _MARKDOWN_FIELDS and isinstance(value, str) and value:
            result[key] = LiteralScalarString(value)
        else:
            result[key] = value
    return result


def _plan_metadata_dict(plan: Plan) -> dict[str, Any]:
    """Extract plan-level metadata as a dict for YAML serialization.

    Applies ``LiteralScalarString`` to plan-level markdown fields (``goal``,
    ``context``, ``acceptance-criteria``) so ruamel.yaml emits them as YAML
    literal block scalars (``|``).

    Args:
        plan: The ``Plan`` model.

    Returns:
        Dict with plan metadata fields, excluding task list and internal fields.
        Multiline markdown fields are wrapped in ``LiteralScalarString``.
    """
    raw = plan.model_dump(
        by_alias=True, mode="json", exclude={"tasks", "source_path", "source_format"}, exclude_none=True
    )
    for key in list(raw.keys()):
        value = raw[key]
        # Omit empty lists (e.g., acceptance-criteria-structured: [] adds noise)
        if isinstance(value, list) and not value:
            del raw[key]
            continue
        if key in _MARKDOWN_FIELDS and isinstance(value, str) and value:
            raw[key] = LiteralScalarString(value)
    return raw


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` using an atomic rename.

    Creates a temporary file in the same directory as ``path``, writes
    the content, then calls ``Path.replace`` to rename it atomically.
    On Linux, ``Path.replace`` wraps ``rename(2)`` which is atomic when
    source and destination are on the same filesystem.

    Args:
        path: Destination file path.
        content: Text content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        tmp_path.replace(path)
    except Exception:
        # Clean up temp file on failure; propagate the original exception.
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise


def _serialize_to_string(data: dict[str, Any]) -> str:
    """Serialize a dict to a YAML string using ruamel.yaml round-trip mode.

    Args:
        data: Dict to serialize.

    Returns:
        YAML string representation.
    """
    y = _make_yaml()
    buf = io.StringIO()
    y.dump(data, buf)
    return buf.getvalue()


def _estimate_line_count(plan: Plan) -> int:
    """Estimate the number of YAML lines a plan would produce as a single file.

    Serializes the full plan and counts lines. Used to decide between
    single-file and directory output.

    Args:
        plan: Plan to estimate.

    Returns:
        Estimated line count of the full serialized YAML.
    """
    meta = _plan_metadata_dict(plan)
    task_list = [_task_to_dict(t) for t in plan.tasks]
    full: dict[str, Any] = {**meta, "tasks": task_list}
    serialized = _serialize_to_string(full)
    return serialized.count("\n")


def _write_single_file(plan: Plan, output_path: Path) -> Path:
    """Write the plan as a single YAML file.

    Args:
        plan: Plan to serialize.
        output_path: Destination ``.yaml`` file path.

    Returns:
        Path to the written file.
    """
    meta = _plan_metadata_dict(plan)
    task_list = [_task_to_dict(t) for t in plan.tasks]
    full: dict[str, Any] = {**meta, "tasks": task_list}
    content = _serialize_to_string(full)
    _atomic_write(output_path, content)
    return output_path


def _write_directory(plan: Plan, output_path: Path) -> Path:
    """Write the plan as a directory of YAML files.

    Creates ``output_path/plan.yaml`` with plan metadata and a ``task_files``
    list, plus one ``output_path/task-{id}.yaml`` per task.

    Args:
        plan: Plan to serialize.
        output_path: Destination directory path.

    Returns:
        Path to the written directory.
    """
    output_path.mkdir(parents=True, exist_ok=True)

    task_file_names = [f"task-{t.id}.yaml" for t in plan.tasks]
    meta = _plan_metadata_dict(plan)
    plan_meta: dict[str, Any] = {**meta, "task_files": task_file_names}
    plan_meta_content = _serialize_to_string(plan_meta)
    _atomic_write(output_path / "plan.yaml", plan_meta_content)

    for task in plan.tasks:
        task_dict = _task_to_dict(task)
        task_content = _serialize_to_string(task_dict)
        _atomic_write(output_path / f"task-{task.id}.yaml", task_content)

    return output_path


def write_plan(plan: Plan, output_path: Path, *, force_single: bool = False) -> Path:
    """Write a plan to pure YAML.

    Chooses between single-file and directory output based on the estimated
    serialized line count versus ``LINE_THRESHOLD``, unless ``force_single``
    overrides the threshold.

    **Single-file output** (``output_path`` is a ``.yaml`` file):
    All plan metadata and tasks are serialized to one file.

    **Directory output** (``output_path`` is a directory):
    Creates ``output_path/plan.yaml`` with plan metadata and a ``task_files``
    list, plus one ``task-{id}.yaml`` per task.

    Uses atomic rename (``tempfile`` + ``Path.replace``) for safe writes.
    Multiline markdown content fields are serialized as YAML literal block
    scalars (``|``).

    Args:
        plan: The plan to serialize.
        output_path: Destination path. Use a ``.yaml`` extension for single-file
                     output or a directory path for directory output.
        force_single: If ``True``, always write a single file regardless of size.

    Returns:
        The path that was written (file or directory).

    Raises:
        ValueError: If path traversal is detected (output_path contains ``..``
                    components after resolution).
    """
    # Security: reject paths with .. traversal components
    if ".." in output_path.parts:
        msg = f"Path traversal detected in output_path: {output_path}"
        raise ValueError(msg)
    resolved = output_path.resolve()

    if force_single:
        # Force single file — ensure .yaml extension
        target = resolved if resolved.suffix == ".yaml" else resolved.with_suffix(".yaml")
        return _write_single_file(plan, target)

    # Serialize once; use the result for both the threshold check and the write.
    # This avoids the double serialization that occurred when _estimate_line_count
    # serialized the plan and _write_single_file then serialized it again.
    meta = _plan_metadata_dict(plan)
    task_list = [_task_to_dict(t) for t in plan.tasks]
    full: dict[str, Any] = {**meta, "tasks": task_list}
    content = _serialize_to_string(full)
    line_count = content.count("\n")

    if line_count < LINE_THRESHOLD:
        target = resolved if resolved.suffix == ".yaml" else resolved.with_suffix(".yaml")
        _atomic_write(target, content)
        return target

    return _write_directory(plan, resolved)


# ---------------------------------------------------------------------------
# All known YAML field names (kebab-case aliases and snake_case names) for Task.
# Used by update_field validation.
# ---------------------------------------------------------------------------

_KNOWN_TASK_FIELDS: frozenset[str] = frozenset({
    # Identity
    "task",
    "id",
    "title",
    "status",
    # Workflow
    "agent",
    "dependencies",
    "priority",
    "complexity",
    "skills",
    "blocked-by",
    "parallelize-with",
    # Timestamps
    "created",
    "started",
    "completed",
    "last-activity",
    # Analytical
    "issue-classification",
    "scenario-target",
    "analysis-method",
    "divergence-notes",
    "reason",
    # Markdown content
    "description",
    "objective",
    "requirements",
    "constraints",
    "expected-outputs",
    "acceptance-criteria",
    "verification-steps",
    "context-notes",
    "handoff",
    # Bookend fields
    "is-bookend",
    "bookend-type",
    # GitHub integration
    "github-issue",
    # snake_case aliases (also accepted)
    "is_bookend",
    "bookend_type",
    "blocked_by",
    "parallelize_with",
    "last_activity",
    "issue_classification",
    "scenario_target",
    "analysis_method",
    "divergence_notes",
    "expected_outputs",
    "acceptance_criteria",
    "verification_steps",
    "context_notes",
    "github_issue",
})


def _is_yaml_frontmatter(raw_text: str) -> bool:
    r"""Return True if ``raw_text`` uses YAML-frontmatter format.

    YAML-frontmatter files start with ``---\\n`` and contain a closing
    ``\\n---`` delimiter that separates the YAML block from the prose body.
    ruamel.yaml's ``load()`` cannot parse these as a single document because
    the second ``---`` starts a new YAML document.

    Args:
        raw_text: Full file content.

    Returns:
        ``True`` if the file uses yaml_frontmatter format.
    """
    if not raw_text.startswith(("---\n", "---\r\n")):
        return False
    after_open = raw_text[4:]
    return bool(re.search(r"\n---", after_open))


def _split_frontmatter(raw_text: str) -> tuple[str, str, str]:
    r"""Split a yaml_frontmatter file into its three parts.

    Args:
        raw_text: Full file content starting with ``---\\n``.

    Returns:
        A tuple of ``(open_delimiter, yaml_block, rest)`` where:

        - ``open_delimiter`` is ``"---\\n"``
        - ``yaml_block`` is the raw YAML text between the first ``---``
          and the closing ``\\n---``
        - ``rest`` is everything from the closing ``\\n---`` to end-of-file
          (includes the ``\\n---`` itself so reassembly is lossless)

    Raises:
        ValueError: If no closing ``---`` delimiter is found.
    """
    open_delim = "---\n"
    after_open = raw_text[len(open_delim) :]
    close_match = re.search(r"\n---", after_open)
    if not close_match:
        msg = "No closing '---' found for YAML frontmatter block"
        raise ValueError(msg)
    yaml_block = after_open[: close_match.start()]
    rest = after_open[close_match.start() :]
    return open_delim, yaml_block, rest


def _locate_task_entry(data: dict, task_id: str, file_path: Path) -> dict:
    """Locate and return the mutable task dict within a loaded YAML document.

    Handles two file layouts:

    - **Multi-task file**: top-level ``tasks`` list; searches for the entry
      whose ``task`` or ``id`` key matches ``task_id``.
    - **Single-task file**: top-level dict with a ``task`` or ``id`` key.

    Args:
        data: Loaded YAML document (ruamel.yaml round-trip dict).
        task_id: Task ID to locate (e.g., ``"T1"``).
        file_path: Source path — used only in ``KeyError`` messages.

    Returns:
        The mutable task dict (a reference into ``data``) for the caller to modify.

    Raises:
        KeyError: If ``task_id`` cannot be found in the document.
    """
    if "tasks" in data and isinstance(data["tasks"], list):
        for task_entry in data["tasks"]:
            entry_id = task_entry.get("task") or task_entry.get("id")
            if str(entry_id) == task_id:
                return task_entry
        msg = f"Task ID '{task_id}' not found in {file_path}"
        raise KeyError(msg)

    if data.get("task") == task_id or data.get("id") == task_id:
        return data

    msg = f"Task ID '{task_id}' not found in {file_path}"
    raise KeyError(msg)


def _validate_field_name(field: str) -> None:
    """Validate that ``field`` is a known task field name.

    Args:
        field: Field name to validate (kebab-case or snake_case).

    Raises:
        ValueError: If the field name is not in the known task schema.
    """
    if field not in _KNOWN_TASK_FIELDS:
        msg = f"Unknown field '{field}'. Must be a known task field name (kebab-case preferred, e.g., 'last-activity')."
        raise ValueError(msg)


def update_field(file_path: Path, task_id: str, field: str, value: str | int | list[str]) -> None:
    """Update a single field in a YAML task file without full re-serialization.

    Loads the YAML using ``ruamel.yaml`` round-trip mode, locates the task
    section by ``task_id``, modifies the specified ``field``, and dumps back
    using an atomic write. Comments, field order, and all other fields are
    preserved.

    Supports two file layouts:

    - **Single-task file**: Top-level dict with a ``task`` key.
    - **Multi-task file**: Top-level dict with a ``tasks`` list; each element
      has a ``task`` key matching ``task_id``.

    Args:
        file_path: Path to the ``.yaml`` task file to modify.
        task_id: ID of the task whose field should be updated (e.g., ``"T1"``).
        field: YAML field name to update. Use kebab-case for aliased fields
               (e.g., ``"last-activity"`` not ``"last_activity"``).
        value: New value for the field. If the field is a markdown content
               field, multiline strings are automatically wrapped in
               ``LiteralScalarString`` to preserve ``|`` block scalar format.

    Raises:
        FileNotFoundError: If ``file_path`` does not exist.
        KeyError: If ``task_id`` is not found in the file.
        ValueError: If the field name is not valid for the task schema.
    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    # Validate field name: must be a known kebab-case alias or snake_case field.
    _validate_field_name(field)

    y = _make_yaml()
    raw_text = file_path.read_text(encoding="utf-8")

    # Wrap markdown content field values as literal block scalars.
    if field in _MARKDOWN_FIELDS and isinstance(value, str) and "\n" in value:
        actual_value: Any = LiteralScalarString(value)
    else:
        actual_value = value

    if _is_yaml_frontmatter(raw_text):
        # yaml_frontmatter format: extract only the YAML block, parse it,
        # update the field, and reassemble with the original body.
        open_delim, yaml_block, rest = _split_frontmatter(raw_text)
        data = y.load(yaml_block)
        if "tasks" in data and isinstance(data["tasks"], list):
            # Multi-task plan in frontmatter format: locate the task entry within
            # the tasks list rather than treating the plan root as the task.
            task_entry = _locate_task_entry(data, task_id, file_path)
            task_entry[field] = actual_value
        else:
            entry_id = data.get("task") or data.get("id")
            if str(entry_id) != task_id:
                msg = f"Task ID '{task_id}' not found in {file_path}"
                raise KeyError(msg)
            data[field] = actual_value
        buf = io.StringIO()
        y.dump(data, buf)
        _atomic_write(file_path, open_delim + buf.getvalue() + rest)
        return

    data = y.load(raw_text)
    task_entry = _locate_task_entry(data, task_id, file_path)
    task_entry[field] = actual_value
    buf = io.StringIO()
    y.dump(data, buf)
    _atomic_write(file_path, buf.getvalue())


def create_plan_file(path: Path, plan: Plan) -> None:
    """Write a new plan to ``path`` using an atomic write.

    Delegates serialization to ``write_plan`` which selects single-file or
    directory layout based on estimated line count. This function is the
    canonical entry point for *creating* a new plan file; use ``write_plan``
    when migrating or overwriting an existing plan.

    Args:
        path: Destination path for the plan. A ``.yaml`` extension is added
              automatically if the path has no suffix.
        plan: The ``Plan`` model to serialize.

    Raises:
        ValueError: If path traversal is detected.
        OSError: If the write fails.
    """
    target = path if path.suffix else path.with_suffix(".yaml")
    write_plan(plan, target, force_single=True)


def append_section(path: Path, task_id: str, section_name: str, content: str) -> None:
    """Append a named markdown section to a task's body content in a YAML file.

    For multi-task files, the task's YAML document is located by ``task_id``
    and the section is appended to the task's ``context-notes`` field (which
    stores prose body content). For single-task files the same applies.

    The section is appended in markdown heading format::

        ## {section_name}

        {content}

    If the ``context-notes`` field is empty the section becomes its full value.
    If it already has content the new section is appended with a blank-line
    separator.

    Args:
        path: Path to the ``.yaml`` task file to modify.
        task_id: ID of the task to append to (e.g., ``"T1"``).
        section_name: Heading text for the new section (e.g., ``"Context Manifest"``).
        content: Markdown body text for the section (no leading heading needed).

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        KeyError: If ``task_id`` is not found in the file.
    """
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    new_section = f"## {section_name}\n\n{content.rstrip()}\n"

    y = _make_yaml()
    raw_text = path.read_text(encoding="utf-8")

    def _append_to_context_notes(target: dict[str, object]) -> None:
        raw = target.get("context-notes") or target.get("context_notes") or ""
        existing: str = str(raw) if not isinstance(raw, str) else raw
        updated = existing.rstrip() + "\n\n" + new_section if existing.strip() else new_section
        target["context-notes"] = LiteralScalarString(updated)
        # Remove snake_case duplicate if present to avoid key collision
        target.pop("context_notes", None)

    if _is_yaml_frontmatter(raw_text):
        open_delim, yaml_block, rest = _split_frontmatter(raw_text)
        data = y.load(yaml_block)
        if "tasks" in data and isinstance(data["tasks"], list):
            # Multi-task plan in frontmatter format: locate the task entry within
            # the tasks list rather than treating the plan root as the task.
            task_entry = _locate_task_entry(data, task_id, path)
            _append_to_context_notes(task_entry)
        else:
            entry_id = data.get("task") or data.get("id")
            if str(entry_id) != task_id:
                msg = f"Task ID '{task_id}' not found in {path}"
                raise KeyError(msg)
            _append_to_context_notes(data)
        buf = io.StringIO()
        y.dump(data, buf)
        _atomic_write(path, open_delim + buf.getvalue() + rest)
        return

    data = y.load(raw_text)
    task_entry = _locate_task_entry(data, task_id, path)
    _append_to_context_notes(task_entry)
    buf = io.StringIO()
    y.dump(data, buf)
    _atomic_write(path, buf.getvalue())


def update_fields(file_path: Path, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
    """Update multiple fields in a YAML task file in a single read-modify-write cycle.

    Equivalent to calling ``update_field`` for each entry in ``fields``, but
    reads and writes the file only once, regardless of how many fields are
    updated.

    Args:
        file_path: Path to the ``.yaml`` task file to modify.
        task_id: ID of the task whose fields should be updated (e.g., ``"T1"``).
        fields: Mapping of field name -> new value. Field names must be
                kebab-case (e.g., ``"last-activity"``).

    Raises:
        FileNotFoundError: If ``file_path`` does not exist.
        KeyError: If ``task_id`` is not found in the file.
        ValueError: If any field name is not valid for the task schema.
    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    for field in fields:
        _validate_field_name(field)

    y = _make_yaml()
    raw_text = file_path.read_text(encoding="utf-8")

    def _apply_fields(target: dict[str, object]) -> None:
        for field, value in fields.items():
            if field in _MARKDOWN_FIELDS and isinstance(value, str) and "\n" in value:
                target[field] = LiteralScalarString(value)
            else:
                target[field] = value

    if _is_yaml_frontmatter(raw_text):
        # yaml_frontmatter format: extract only the YAML block, parse it,
        # apply all fields, and reassemble with the original body.
        open_delim, yaml_block, rest = _split_frontmatter(raw_text)
        data = y.load(yaml_block)
        if "tasks" in data and isinstance(data["tasks"], list):
            # Multi-task plan in frontmatter format: locate the task entry within
            # the tasks list rather than treating the plan root as the task.
            task_entry = _locate_task_entry(data, task_id, file_path)
            _apply_fields(task_entry)
        else:
            entry_id = data.get("task") or data.get("id")
            if str(entry_id) != task_id:
                msg = f"Task ID '{task_id}' not found in {file_path}"
                raise KeyError(msg)
            _apply_fields(data)
        buf = io.StringIO()
        y.dump(data, buf)
        _atomic_write(file_path, open_delim + buf.getvalue() + rest)
        return

    data = y.load(raw_text)
    task_entry = _locate_task_entry(data, task_id, file_path)
    _apply_fields(task_entry)
    buf = io.StringIO()
    y.dump(data, buf)
    _atomic_write(file_path, buf.getvalue())
