"""Pure YAML reader for canonical SAM task/plan files.

Reads ``.yaml`` files in canonical format (single-file or directory layout)
and returns raw dicts for normalization.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sam_schema.readers._yaml_utils import coerce_to_plain, load_yaml
from sam_schema.readers.detect import FormatType

if TYPE_CHECKING:
    from pathlib import Path


def read_yaml_plan(path: Path) -> tuple[dict, list[dict], FormatType]:
    """Read a canonical pure-YAML plan file or directory.

    Handles two layouts:
    - Single ``.yaml`` file with ``feature:`` header and ``tasks:`` list.
    - Directory with ``plan.yaml`` (plan metadata) and ``task-{id}.yaml`` per-task files.

    Uses ``ruamel.yaml`` (round-trip mode) for parsing to preserve comments
    and field order for later write-back.

    Args:
        path: Path to a ``.yaml`` file or a directory containing per-task files.

    Returns:
        A tuple of ``(plan_meta_dict, task_dicts, FormatType.PURE_YAML)``.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the YAML cannot be parsed or the structure is unexpected.
    """
    if not path.exists():
        msg = f"Path does not exist: {path}"
        raise FileNotFoundError(msg)

    if path.is_dir():
        return _read_directory(path)

    return _read_single_file(path)


def _read_single_file(path: Path) -> tuple[dict, list[dict], FormatType]:
    """Read a single ``.yaml`` plan file.

    Args:
        path: Path to a single ``.yaml`` file.

    Returns:
        ``(plan_meta_dict, task_dicts, FormatType.PURE_YAML)``.

    Raises:
        ValueError: If the file structure is unexpected.
    """
    content = path.read_text(encoding="utf-8")
    parsed = load_yaml(content)

    if not isinstance(parsed, dict):
        msg = f"Expected a YAML mapping at the top level of {path}, got {type(parsed).__name__}"
        raise TypeError(msg)

    parsed = coerce_to_plain(parsed)

    tasks_raw = parsed.pop("tasks", []) or []
    if not isinstance(tasks_raw, list):
        msg = f"Expected 'tasks' to be a list in {path}, got {type(tasks_raw).__name__}"
        raise TypeError(msg)

    task_dicts: list[dict] = [item for item in tasks_raw if isinstance(item, dict)]

    return parsed, task_dicts, FormatType.PURE_YAML


def _read_directory(path: Path) -> tuple[dict, list[dict], FormatType]:
    """Read a directory-based plan (one task per ``.yaml`` or ``.md`` file).

    Looks for:
    1. ``plan.yaml`` for plan-level metadata.
    2. ``task-{id}.yaml`` or ``task-*.yaml`` for per-task files.
    3. If no ``plan.yaml``, synthesizes plan metadata from directory name.

    Args:
        path: Directory path containing per-task files.

    Returns:
        ``(plan_meta_dict, task_dicts, FormatType.PURE_YAML)``.
    """
    plan_meta: dict = {}

    plan_yaml_path = path / "plan.yaml"
    if plan_yaml_path.exists():
        content = plan_yaml_path.read_text(encoding="utf-8")
        parsed = load_yaml(content)
        if isinstance(parsed, dict):
            plan_meta = coerce_to_plain(parsed)
            # Remove task_files list — individual files are discovered by glob
            plan_meta.pop("task_files", None)

    if "feature" not in plan_meta:
        # Synthesize feature name from directory name, stripping "tasks-N-" prefix
        slug = re.sub(r"^tasks-\d+-", "", path.name)
        plan_meta.setdefault("feature", slug)

    # Discover per-task YAML files in task-{id}.yaml naming convention
    task_files = sorted(path.glob("task-*.yaml"))
    if not task_files:
        # Fall back to any .yaml file that is not plan.yaml
        task_files = sorted(f for f in path.glob("*.yaml") if f.name != "plan.yaml")

    task_dicts: list[dict] = []
    for task_file in task_files:
        content = task_file.read_text(encoding="utf-8")
        parsed = load_yaml(content)
        if isinstance(parsed, dict):
            task_dicts.append(coerce_to_plain(parsed))

    return plan_meta, task_dicts, FormatType.PURE_YAML
