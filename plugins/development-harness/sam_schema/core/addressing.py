"""Plan addressing module for SAM task/plan files.

Resolves human-readable address strings (``P1/T3``, ``P1``, ``QG3``,
``QG3/T1``, ``my-slug/T3``) to file system paths, and parses address
components for use by the CLI and MCP server.

Address format:
    ``P{N}``         — plan by sequence number (matches ``P{NNN}-{slug}.*`` filename)
    ``QG{N}``        — quality-gate plan (matches ``QG{NNN}-{slug}.*`` filename)
    ``{slug}``       — plan by slug substring match (matches ``P*-{slug}.*``)
    ``P{N}/T{M}``    — task within a plan
    ``QG{N}/T{M}``   — task within a quality-gate plan
    ``{slug}/T{M}``  — task within a plan by slug

Backward compatibility:
    If no ``P{NNN}-*`` pattern matches, falls back to ``tasks-{N}-{slug}``
    naming for unmigrated files. This fallback is explicitly temporary and
    will be removed after all plan files are renamed.
"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Pattern: P{NNN}-{slug}.yaml or P{hex8}-{slug}.yaml (UUID-derived IDs).
# Matches both legacy zero-padded numeric IDs (P001, P042) and the new
# UUID-derived hex IDs (Pa1b2c3d4). Captured group is the ID suffix (digits or hex).
_P_NUMERIC_RE = re.compile(r"^P([0-9a-f]+)-", re.IGNORECASE)

# Pattern: QG{NNN}-{slug}.yaml / QG{NNN}-{slug}.md / QG{NNN}-{slug}/
_QG_NUMERIC_RE = re.compile(r"^QG(\d+)-", re.IGNORECASE)

# Backward-compat pattern: tasks-{N}-{slug}.yaml / .md / directory
_TASKS_NUMERIC_RE = re.compile(r"^tasks-(\d+)-")

# Maps uppercase address prefix to the corresponding filename regex.
# Used by resolve_plan_address for multi-character prefix resolution.
# When adding a new plan type, add its prefix and regex here.
_PREFIX_REGEX_MAP: dict[str, re.Pattern[str]] = {"P": _P_NUMERIC_RE, "QG": _QG_NUMERIC_RE}

# Regex that matches any known multi-char address prefix followed by digits.
# Captures (prefix, digits) so parse_address can strip the prefix generically.
_KNOWN_PREFIX_RE = re.compile(r"^(QG)(\d+)$", re.IGNORECASE)


def _yaml_first_key(p: Path) -> tuple[str, int]:
    """Sort key that places ``.yaml`` files before ``.md`` for the same stem.

    Args:
        p: Path to sort.

    Returns:
        Tuple of (stem, priority) where .yaml maps to 0 and all other
        extensions map to 1, ensuring .yaml sorts before .md.
    """
    return (p.stem, 0 if p.suffix == ".yaml" else 1)


def _parse_prefix(address: str) -> tuple[str, str, re.Pattern[str]]:
    """Extract the plan-type prefix, numeric/slug ref, and filename regex from an address.

    Handles multi-character prefixes (e.g. ``QG``), single-char ``P``/``p``,
    and bare numeric or slug addresses.

    Args:
        address: Raw address string (path traversal already rejected by caller).

    Returns:
        A 3-tuple ``(active_prefix, ref, numeric_re)`` where:
        - ``active_prefix`` is the uppercase prefix string (``"P"`` or ``"QG"``).
        - ``ref`` is the portion after the prefix (digits or slug).
        - ``numeric_re`` is the compiled regex for matching filenames of this type.
    """
    multi_match = _KNOWN_PREFIX_RE.match(address)
    if multi_match:
        prefix = multi_match.group(1).upper()
        return prefix, multi_match.group(2), _PREFIX_REGEX_MAP.get(prefix, _P_NUMERIC_RE)
    if address and address[0] in {"P", "p"} and len(address) > 1:
        return "P", address[1:], _P_NUMERIC_RE
    return "P", address, _P_NUMERIC_RE


def _warn_legacy_shadow(ref: str, canonical_name: str, all_entries: list[Path]) -> None:
    """Emit a stderr warning when a P-prefix plan shadows a legacy ``tasks-*`` file.

    Only called for P-type plans; QG plans never have a legacy equivalent.

    Args:
        ref: Numeric reference string (e.g. ``"001"``).
        canonical_name: Filename of the canonical P-file that was resolved.
        all_entries: All entries in the plan directory (pre-sorted).
    """
    target_num = int(ref)
    legacy_shadow = [
        p
        for p in all_entries
        if p.name.startswith("tasks-") and (m := _TASKS_NUMERIC_RE.match(p.name)) and int(m.group(1)) == target_num
    ]
    if legacy_shadow:
        shadow_names = ", ".join(p.name for p in legacy_shadow)
        print(
            f"WARNING: P{ref} resolved to '{canonical_name}' but a legacy file also exists "
            f"with the same number: {shadow_names}. "
            f"Run 'sam migrate P{ref}' to remove the legacy file.",
            file=sys.stderr,
        )


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
    2. Detect prefix: ``QG{N}`` → use ``_QG_NUMERIC_RE``; ``P{N}`` or bare numeric
       → use ``_P_NUMERIC_RE``; anything else treated as a slug.
    3. If the ref part is numeric (``"1"``, ``"719"``, ``"003"``), glob
       ``{PREFIX}{NNN}-*`` files/directories where the numeric portion matches.
       Zero-padding is flexible: ``"1"`` matches ``P001-``, ``P01-``, ``P1-``.
    4. Collision: if multiple entries share the same numeric value, raise
       ``AddressingError`` with the list of matches.
    5. If the ref is a slug (non-numeric, no recognised prefix), glob
       ``{PREFIX}*-{slug}*`` among prefix-pattern entries.
    6. For ``P``-type addresses only: if no ``P{NNN}-*`` match found, fall back
       to legacy ``tasks-{N}-{slug}`` pattern (backward compatibility).
       ``QG`` plans have no legacy equivalent and raise immediately.
    7. If still no match, raise ``AddressingError``.

    Args:
        address: Plan address string. May be passed with or without prefix:
                 ``"P1"``, ``"1"``, ``"719"``, ``"QG003"``, ``"my-feature-slug"``.
                 ``parse_address()`` strips the ``P`` prefix before calling here,
                 but passes ``QG003`` (prefix preserved) for multi-char prefixes.
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

    # Detect plan-type prefix and strip it to get the bare ref (digits or slug).
    # parse_address() already strips P but preserves QG; resolve_plan_address() is
    # also called directly with the full form, so normalisation happens here too.
    active_prefix, ref, active_numeric_re = _parse_prefix(address)

    if not plan_dir.exists():
        msg = f"Plan directory does not exist: {plan_dir}"
        raise FileNotFoundError(msg)

    all_entries: list[Path] = sorted(plan_dir.iterdir(), key=_yaml_first_key)

    # -------------------------------------------------------------------
    # Phase 1: {PREFIX}{NNN}-{slug} resolution (primary naming convention)
    # Handles both P{NNN}-* and QG{NNN}-* files via active_numeric_re.
    # -------------------------------------------------------------------
    if ref.isdigit():
        target_num = int(ref)
        p_matches = [p for p in all_entries if (m := active_numeric_re.match(p.name)) and int(m.group(1)) == target_num]
        if len(p_matches) == 1:
            if active_prefix == "P":
                _warn_legacy_shadow(ref, p_matches[0].name, all_entries)
            return p_matches[0]
        if len(p_matches) > 1:
            paths_listed = ", ".join(str(p) for p in p_matches)
            disambiguation_msg = (
                f"Address '{active_prefix}{ref}' matches multiple plans: {paths_listed}. "
                f"Disambiguate by using the full slug, e.g. '{active_prefix}{ref}-my-slug'."
            )
            raise AddressingError(address, plan_dir, disambiguation_msg)
        # No {PREFIX}{NNN}-* match — fall through.
        # QG plans have no legacy fallback and will raise AddressingError below.
    else:
        # Slug-based reference: match prefix-pattern entries containing the slug.
        p_slug_matches = [p for p in all_entries if active_numeric_re.match(p.name) and ref in p.name]
        if p_slug_matches:
            return p_slug_matches[0]
        # No prefix-pattern slug match — fall through to legacy fallback.
        # QG plans have no legacy fallback and will raise AddressingError below.

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
                 - ``"P1/T3"``    → plan reference ``"1"``, task reference ``"3"``
                 - ``"P1"``       → plan reference ``"1"``, task reference ``None``
                 - ``"QG3/T1"``   → plan reference ``"QG3"``, task reference ``"1"``
                 - ``"QG003"``    → plan reference ``"QG003"``, task reference ``None``
                 - ``"my-slug/T3"`` → plan reference ``"my-slug"``, task ``"3"``
                 - ``"my-slug"``  → plan reference ``"my-slug"``, task ``None``
                 - ``"P719/T3"``  → plan reference ``"719"``, task reference ``"3"``

    Returns:
        A tuple ``(plan_ref, task_ref)`` where ``task_ref`` is ``None`` if no
        task component is present.

        For ``P``-prefix addresses the ``P`` is stripped so ``resolve_plan_address``
        receives a bare numeric ref (e.g. ``"719"``).

        For multi-character prefixes (e.g. ``QG``), the prefix is **preserved**
        in ``plan_ref`` (e.g. ``"QG003"``) so that ``resolve_plan_address`` can
        detect the prefix and use the correct filename regex.

        The ``T`` prefix is stripped from the task component in all cases.

    Raises:
        ValueError: If the address string cannot be parsed, or if it contains
                    path traversal sequences or absolute paths.
    """
    if not address or not address.strip():
        msg = f"Address cannot be empty: {address!r}"
        raise ValueError(msg)

    # Reject file paths: addresses that contain file extensions are almost certainly
    # file paths passed by mistake (e.g. plan/tasks-698-foo.md instead of P698).
    file_ext_re = re.compile(r"\.(md|yaml|yml)$", re.IGNORECASE)
    if file_ext_re.search(address):
        msg = (
            f"Address looks like a file path (contains a file extension): {address!r}. "
            f"Use a plan address like 'P698' or 'P698/T1' instead."
        )
        raise ValueError(msg)

    # Security: reject path traversal before any parsing
    _reject_path_traversal(address)

    # Split on "/" to separate plan and task components
    parts = address.split("/", 1)
    plan_part = parts[0].strip()

    if not plan_part:
        msg = f"Address has empty plan component: {address!r}"
        raise ValueError(msg)

    # Strip prefix from plan component.
    #
    # Multi-character known prefixes (e.g. QG): preserve the full plan_part so
    # that resolve_plan_address can detect the QG prefix and use the correct regex.
    # _KNOWN_PREFIX_RE matches "QG003" → keeps "QG003" as plan_ref.
    #
    # Single-character P/p prefix: strip it so resolve_plan_address receives "719"
    # (its longstanding contract for P-type addresses).
    #
    # Anything else (slug, bare number): pass through unchanged.
    if _KNOWN_PREFIX_RE.match(plan_part):
        # Multi-char prefix plan (QG…): pass full address to resolve_plan_address
        plan_ref = plan_part
    elif plan_part.upper().startswith("P") and len(plan_part) > 1:
        # Single-char P/p prefix: strip it (backward-compatible contract)
        plan_ref = plan_part[1:]
    else:
        plan_ref = plan_part

    if len(parts) == 1:
        return plan_ref, None

    task_part = parts[1].strip()
    if not task_part:
        msg = f"Address has empty task component: {address!r}"
        raise ValueError(msg)

    # Strip leading T/t prefix from task component
    task_ref = task_part[1:] if task_part.upper().startswith("T") and len(task_part) > 1 else task_part

    return plan_ref, task_ref
