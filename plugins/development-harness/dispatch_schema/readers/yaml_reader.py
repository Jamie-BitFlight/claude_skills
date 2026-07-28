"""YAML reader for dispatch plan files.

Reads ``plan/milestone-{N}-dispatch.yaml`` files and returns validated
``DispatchPlan`` Pydantic models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from ruamel.yaml import YAML

from dispatch_schema.core.models import DispatchPlan

if TYPE_CHECKING:
    from pathlib import Path

_YAML_RT: YAML = YAML(typ="rt")
_YAML_RT.preserve_quotes = True


def _load_yaml(content: str) -> Any:  # ruff: ignore[any-type]
    """Parse YAML text using ruamel.yaml round-trip mode.

    Args:
        content: Raw YAML text to parse.

    Returns:
        Parsed YAML structure (dict or list).

    Raises:
        ValueError: If the content cannot be parsed as valid YAML.
    """
    try:
        return _YAML_RT.load(content)
    except Exception as exc:
        msg = f"Failed to parse YAML: {exc}"
        raise ValueError(msg) from exc


def _coerce_to_plain(obj: Any) -> Any:  # ruff: ignore[any-type]
    """Recursively coerce ruamel.yaml CommentedMap/CommentedSeq to plain Python types.

    ruamel.yaml round-trip mode returns ``CommentedMap`` and ``CommentedSeq``
    instead of plain ``dict``/``list``. Pydantic ``model_validate`` works with
    plain Python types only.

    Args:
        obj: Any value from a ruamel.yaml parse result.

    Returns:
        Plain Python ``dict``, ``list``, or scalar (unchanged).
    """
    if hasattr(obj, "items"):  # dict-like (CommentedMap)
        return {str(k): _coerce_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_to_plain(item) for item in obj]
    return obj


def read_dispatch_plan(path: Path) -> DispatchPlan:
    """Read and validate a dispatch plan YAML file.

    Args:
        path: Path to a ``milestone-{N}-dispatch.yaml`` file.

    Returns:
        Validated ``DispatchPlan`` model.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the YAML is malformed or fails Pydantic validation.
    """
    if not path.exists():
        msg = f"Dispatch plan file not found: {path}"
        raise FileNotFoundError(msg)

    content = path.read_text(encoding="utf-8")
    parsed = _load_yaml(content)

    if not isinstance(parsed, dict):
        msg = f"Expected a YAML mapping at the top level of {path}, got {type(parsed).__name__}"
        raise ValueError(msg)  # ruff: ignore[type-check-without-type-error] -- structural parse error, not a caller type error

    plain = _coerce_to_plain(parsed)

    try:
        return DispatchPlan.model_validate(plain)
    except ValidationError as exc:
        msg = f"Dispatch plan validation failed for {path}: {exc}"
        raise ValueError(msg) from exc
