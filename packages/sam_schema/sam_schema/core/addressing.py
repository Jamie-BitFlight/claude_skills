"""Plan addressing module for SAM task/plan files.

Resolves human-readable address strings (``P1/T3``, ``P1``, ``my-slug/T3``)
to file system paths, and parses address components for use by the CLI and
MCP server.

Address format:
    ``P{N}``         — plan by sequence number (matches ``P{NNN}-{slug}.*`` filename)
    ``{slug}``       — plan by slug substring match (matches ``P*-{slug}.*``)
    ``P{N}/T{M}``    — task within a plan
    ``{slug}/T{M}``  — task within a plan by slug

Backward compatibility:
    If no ``P{NNN}-*`` pattern matches, falls back to ``tasks-{N}-{slug}``
    naming for unmigrated files. This fallback is explicitly temporary and
    will be removed after all plan files are renamed.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Pattern: P{NNN}-{slug}.yaml / P{NNN}-{slug}.md / P{NNN}-{slug}/
_P_NUMERIC_RE = re.compile(r"^P(\d+)-")

# Backward-compat pattern: tasks-{N}-{slug}.yaml / .md / directory
_TASKS_NUMERIC_RE = re.compile(r"^tasks-(\d+)-")


class AddressingError(Exception):
    """Raised when an address cannot be resolved to a file system path.

    Args:
        address: The address string that failed to resolve.
        plan_dir: The directory that was searched.
        message: Optional override message (e.g., collision disambiguation details).
    """

    def __init__(self, address: str, plan_dir: Path, message: str | None = None) -> None:
        """Initialize AddressingError with the unresolvable address and search directory."""
        self.address = address
        self.plan_dir = plan_dir
        default = f"Cannot resolve address '{address}' in plan directory '{plan_dir}'."
        super().__init__(message or default)


def _reject_path_traversal(address: str) -> None:
    """Raise AddressingError-compatible ValueError if address contains traversal sequences.

    Args:
        address: The raw address string to validate.

    Raises:
        ValueError: If the address contains ``..`` path traversal sequences or
                    starts with ``/`` (absolute path).
    """
    if ".." in address:
        msg = f"Address contains path traversal sequence: {address!r}"
        raise ValueError(msg)
    if address.startswith("/"):
        msg = f"Address must not be an absolute path: {address!r}"
        raise ValueError(msg)


def resolve_plan_address(address: str, plan_dir: Path) -> Path:
    """Resolve a plan address string to a file system path.

    Resolution order:
    1. Reject addresses with ``..`` or absolute paths (security).
    2. If ``address`` is numeric (``"1"``, ``"719"``), glob ``P{NNN}-*`` files
       and directories where the numeric portion matches. Zero-padding is
       flexible: ``"1"`` matches ``P001-``, ``P01-``, and ``P1-``.
    3. Collision: if multiple ``P{NNN}-*`` entries share the same numeric
       value, raise ``AddressingError`` with the list of matches.
    4. If ``address`` is a slug (non-numeric, no P-prefix), glob ``P*-{slug}*``.
    5. If no ``P{NNN}-*`` match found, fall back to legacy ``tasks-{N}-{slug}``
       pattern (backward compatibility for unmigrated files).
    6. If still no match, raise ``AddressingError``.

    Args:
        address: Plan address string such as ``"1"``, ``"719"``, or ``"my-feature-slug"``.
                 The ``P`` prefix has already been stripped by ``parse_address()``.
        plan_dir: Directory to search for plan files and directories.

    Returns:
        Resolved path to the plan file or directory.

    Raises:
        AddressingError: If no plan matching the address is found, or if a
                         numeric address matches multiple files (collision).
        FileNotFoundError: If ``plan_dir`` does not exist.
        ValueError: If the address contains path traversal sequences or is absolute.
    """
    # Security: reject path traversal and absolute paths before filesystem access
    _reject_path_traversal(address)

    # Normalize: strip leading P/p prefix so callers may pass either "P1" or "1".
    # parse_address() already strips the prefix, but resolve_plan_address() is also
    # called directly (e.g. from existing tests and future callers) with the full form.
    ref = address[1:] if address and address[0] in {"P", "p"} and len(address) > 1 else address

    if not plan_dir.exists():
        msg = f"Plan directory does not exist: {plan_dir}"
        raise FileNotFoundError(msg)

    # Collect all candidate entries: .yaml files, .md files, directories.
    # Sort so .yaml sorts before .md for the same stem (preference when both coexist).
    # Achieved by sorting on (stem, suffix) with .yaml mapped to a lower sort key than .md.
    def _yaml_first_key(p: Path) -> tuple[str, int]:
        # .yaml → 0, everything else → 1 (ensures .yaml precedes .md for same stem)
        return (p.stem, 0 if p.suffix == ".yaml" else 1)

    all_entries: list[Path] = sorted(plan_dir.iterdir(), key=_yaml_first_key)

    # -------------------------------------------------------------------
    # Phase 1: P{NNN}-{slug} resolution (primary naming convention)
    # -------------------------------------------------------------------
    if ref.isdigit():
        # Numeric plan reference: "1", "001", "719" all match by integer value
        target_num = int(ref)
        p_matches = [p for p in all_entries if (m := _P_NUMERIC_RE.match(p.name)) and int(m.group(1)) == target_num]
        if len(p_matches) == 1:
            return p_matches[0]
        if len(p_matches) > 1:
            paths_listed = ", ".join(str(p) for p in p_matches)
            disambiguation_msg = (
                f"Address 'P{ref}' matches multiple plans: {paths_listed}. "
                f"Disambiguate by using the full slug, e.g. 'P{ref}-my-slug'."
            )
            raise AddressingError(address, plan_dir, disambiguation_msg)

        # No P{NNN}-* match — fall through to backward-compat fallback below
    else:
        # Slug-based reference: glob P*-{slug}* among P-prefixed entries
        p_slug_matches = [p for p in all_entries if _P_NUMERIC_RE.match(p.name) and ref in p.name]
        if p_slug_matches:
            return p_slug_matches[0]

        # No P-pattern slug match — fall through to backward-compat fallback

    # -------------------------------------------------------------------
    # Phase 2: Backward-compatible fallback for tasks-{N}-{slug} naming
    # (Temporary — removed after all plan files are renamed to P{NNN}-{slug})
    # -------------------------------------------------------------------
    legacy_candidates = [p for p in all_entries if p.name.startswith("tasks-")]

    if ref.isdigit():
        target_num = int(ref)
        legacy_numeric = [
            p for p in legacy_candidates if (m := _TASKS_NUMERIC_RE.match(p.name)) and int(m.group(1)) == target_num
        ]
        if legacy_numeric:
            return legacy_numeric[0]
    else:
        legacy_slug = [p for p in legacy_candidates if ref in p.name]
        if legacy_slug:
            return legacy_slug[0]

    raise AddressingError(address, plan_dir)


def parse_address(address: str) -> tuple[str, str | None]:
    """Parse a task address string into its plan and task components.

    Args:
        address: Address string in one of the following forms:
                 - ``"P1/T3"`` → plan reference ``"1"``, task reference ``"3"``
                 - ``"P1"`` → plan reference ``"1"``, task reference ``None``
                 - ``"my-slug/T3"`` → plan reference ``"my-slug"``, task ``"3"``
                 - ``"my-slug"`` → plan reference ``"my-slug"``, task ``None``
                 - ``"P719/T3"`` → plan reference ``"719"``, task reference ``"3"``

    Returns:
        A tuple ``(plan_ref, task_ref)`` where ``task_ref`` is ``None`` if no
        task component is present. The ``P`` prefix is stripped from the plan
        component and the ``T`` prefix is stripped from the task component.

    Raises:
        ValueError: If the address string cannot be parsed, or if it contains
                    path traversal sequences or absolute paths.
    """
    if not address or not address.strip():
        msg = f"Address cannot be empty: {address!r}"
        raise ValueError(msg)

    # Security: reject path traversal before any parsing
    _reject_path_traversal(address)

    # Split on "/" to separate plan and task components
    parts = address.split("/", 1)
    plan_part = parts[0].strip()

    if not plan_part:
        msg = f"Address has empty plan component: {address!r}"
        raise ValueError(msg)

    # Strip leading P/p prefix from plan component
    plan_ref = plan_part[1:] if plan_part.upper().startswith("P") and len(plan_part) > 1 else plan_part

    if len(parts) == 1:
        return plan_ref, None

    task_part = parts[1].strip()
    if not task_part:
        msg = f"Address has empty task component: {address!r}"
        raise ValueError(msg)

    # Strip leading T/t prefix from task component
    task_ref = task_part[1:] if task_part.upper().startswith("T") and len(task_part) > 1 else task_part

    return plan_ref, task_ref
