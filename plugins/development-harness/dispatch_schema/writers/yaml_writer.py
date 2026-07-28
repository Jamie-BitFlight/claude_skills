"""YAML writer for dispatch plan files.

Writes ``DispatchPlan`` models to YAML files using ``ruamel.yaml`` round-trip
mode with kebab-case keys. All writes use atomic rename (temp file in same
directory then ``os.rename``) to prevent partial files on crash.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from dispatch_schema.core.models import DispatchPlan


def _make_yaml() -> YAML:
    """Create a ruamel.yaml instance for round-trip serialization.

    Returns:
        Configured ``YAML`` instance with round-trip mode and human-readable
        default settings.
    """
    y = YAML(typ="rt")
    y.default_flow_style = False
    return y


def _snake_to_kebab(value: str) -> str:
    """Convert a snake_case string to kebab-case.

    Args:
        value: snake_case string (e.g. ``conflict_groups``).

    Returns:
        kebab-case string (e.g. ``conflict-groups``).
    """
    return value.replace("_", "-")


def _keys_to_kebab(obj: Any) -> Any:  # ruff: ignore[any-type]
    """Recursively convert all dict keys from snake_case to kebab-case.

    Args:
        obj: Arbitrary Python object (dict, list, scalar).

    Returns:
        Object with all dict string keys converted to kebab-case. Non-dict
        values are returned unchanged.
    """
    if isinstance(obj, dict):
        return {(_snake_to_kebab(k) if isinstance(k, str) else k): _keys_to_kebab(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_keys_to_kebab(item) for item in obj]
    return obj


def write_dispatch_plan(plan: DispatchPlan, path: Path) -> Path:
    """Write a dispatch plan to YAML using atomic rename.

    Serializes the plan with kebab-case keys. Writes to a temp file in the
    same directory as ``path``, then renames atomically to prevent partial
    writes on crash. Creates parent directories if they do not exist.

    The target path must not be a symlink (path traversal prevention).

    Args:
        plan: Validated ``DispatchPlan`` model to serialize.
        path: Target file path (e.g. ``plan/milestone-3-dispatch.yaml``).

    Returns:
        The path written to (same as the input ``path`` on success).

    Raises:
        ValueError: If ``path`` resolves to a symlink.
        OSError: If the write or rename fails.
    """
    path = Path(path)

    # Security: reject symlinks to prevent path traversal
    if path.exists() and path.is_symlink():
        msg = f"Target path must not be a symlink: {path}"
        raise ValueError(msg)

    # Create parent directories if they do not exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize model to dict with snake_case keys, then convert to kebab-case
    raw: dict[str, Any] = plan.model_dump(by_alias=True, mode="json")
    kebab_dict = _keys_to_kebab(raw)

    # Render YAML to a string buffer first so ruamel.yaml produces clean output
    y = _make_yaml()
    buf = io.StringIO()
    y.dump(kebab_dict, buf)
    yaml_content = buf.getvalue()

    # Atomic write: temp file in same directory, then os.rename
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}-", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(yaml_content)
        Path(tmp_path).rename(path)
    except Exception:
        # Clean up temp file on any failure so no partial file remains
        with _suppress_os_error():
            Path(tmp_path).unlink()
        raise

    return path


class _suppress_os_error:
    """Context manager that suppresses ``OSError`` exceptions."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *_: object) -> bool:
        return exc_type is not None and issubclass(exc_type, OSError)
