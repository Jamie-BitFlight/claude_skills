"""Pure YAML file I/O for backlog items.

Primary read/write module for ``.yaml`` backlog item files.  Provides a
format-detecting reader that handles legacy ``.md`` files during the
transition period.
"""

from __future__ import annotations

import logging
import sys
import warnings
from io import StringIO
from pathlib import Path
from typing import Literal

from ruamel.yaml import YAML

from .models import BacklogItem
from .parsing import parse_item_file

_log = logging.getLogger(__name__)

__all__ = ["detect_format", "load_item", "load_item_text", "save_item"]


def detect_format(path: Path) -> Literal["yaml", "legacy_md"]:
    """Return the file format based on path suffix.

    Args:
        path: Path to the backlog item file.

    Returns:
        ``'yaml'`` for ``.yaml`` files, ``'legacy_md'`` for ``.md`` files.

    Raises:
        ValueError: If the suffix is neither ``.yaml`` nor ``.md``.
    """
    if path.suffix == ".yaml":
        return "yaml"
    if path.suffix == ".md":
        return "legacy_md"
    raise ValueError(f"Unsupported file extension: {path.suffix!r} — expected '.yaml' or '.md'")


def load_item(path: Path) -> BacklogItem:
    """Load a backlog item from a file.

    Detects format from the file suffix and dispatches to the appropriate
    parser.  Legacy ``.md`` files emit a ``DeprecationWarning``.

    Args:
        path: Path to the backlog item file (``.yaml`` or ``.md``).

    Returns:
        Parsed ``BacklogItem`` with ``file_path`` set to the resolved path.

    Raises:
        ValueError: If the file extension is not supported.
    """
    fmt = detect_format(path)
    if fmt == "yaml":
        yaml = YAML(typ="safe")
        with path.open(encoding="utf-8") as fh:
            data = yaml.load(fh)
        item = BacklogItem.model_validate(data)
        item.file_path = str(path.resolve())
        return item
    # fmt == "legacy_md"
    warnings.warn(
        f"Loading backlog item from legacy .md format: {path}. Migrate to .yaml format.",
        DeprecationWarning,
        stacklevel=2,
    )
    text = path.read_text(encoding="utf-8")
    item = parse_item_file(text, path)
    item.file_path = str(path.resolve())
    return item


def save_item(item: BacklogItem, path: Path | None = None) -> None:
    """Write a backlog item to a YAML file.

    Always writes ``.yaml`` format regardless of the original file extension.
    Line-wrapping is disabled so long field values are not broken.

    When *path* is ``None``, the destination is resolved from ``item.file_path``:

    - ``.yaml`` → write to that path.
    - ``.md`` → write to the same stem with ``.yaml`` suffix; rename the
      original ``.md`` to ``.md.bak`` (auto-migration on write).
    - empty / ``None`` → raises :class:`ValueError`.

    After writing, ``item.file_path`` is updated to the resolved ``.yaml`` path.

    Args:
        item: The ``BacklogItem`` to serialise.
        path: Destination path.  When ``None``, resolved from ``item.file_path``.

    Raises:
        ValueError: When *path* is ``None`` and ``item.file_path`` is empty or
            ``None``.
    """
    resolved: Path
    if path is not None:
        resolved = path
    else:
        raw = item.file_path
        if not raw:
            raise ValueError(
                "save_item: path argument is None and item.file_path is empty — cannot determine write destination."
            )
        src = Path(raw)
        if src.suffix == ".md":
            resolved = src.with_suffix(".yaml")
        else:
            resolved = src

    data = item.model_dump(exclude={"file_path", "skip"})
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.width = sys.maxsize
    with resolved.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)

    # After successful write, backup the legacy .md source (safe: YAML already written)
    if path is None:
        raw = item.file_path
        if raw:
            src = Path(raw)
            if src.suffix == ".md" and src.exists():
                bak = src.with_suffix(".md.bak")
                src.rename(bak)
                _log.warning("Auto-migrated %s to %s", src, resolved)

    item.file_path = str(resolved.resolve())


def load_item_text(text: str, path: Path) -> BacklogItem:
    """Load a backlog item from an in-memory string.

    Useful for testing without disk I/O.  Format is detected from ``path``
    suffix; the file does not need to exist on disk.

    Args:
        text: Raw file content string.
        path: Path used only to determine format via suffix (``.yaml`` or
            ``.md``).  The file is not read from disk.

    Returns:
        Parsed ``BacklogItem`` with ``file_path`` set to ``str(path)``.

    Raises:
        ValueError: If the path suffix is not supported.
    """
    fmt = detect_format(path)
    if fmt == "yaml":
        yaml = YAML(typ="safe")
        data = yaml.load(StringIO(text))
        item = BacklogItem.model_validate(data)
        item.file_path = str(path)
        return item
    # fmt == "legacy_md"
    item = parse_item_file(text, path)
    item.file_path = str(path)
    return item
