#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic BFS crawl of DH workflow entry points into a scope file.

Crawls from the hardcoded DH entry-point skills, following four reference
patterns (Mermaid node ``.md`` labels, ``/dh:skill`` invocations,
``subagent_type="dh:agent"`` dispatches, and prose file references) to
build the full in-scope file set for workflow extraction. The crawl is
purely deterministic (no LLM calls, no hallucination risk) — see ADR-1 in
``plan/architect-dh-workflow-extractor-system.md``.

This module owns scope crawl logic, reference pattern detection, and
``SCOPE.md`` serialization. It does NOT own extraction logic, layer JSON
files, or LLM calls — those belong to ``merge_layer.py`` and
``workflows/dh-extract-file.js``.

Usage:
    uv run plugins/development-harness/scripts/enumerate_scope.py
"""

from __future__ import annotations

import logging
import os
import re
import sys
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

logger = logging.getLogger(__name__)

__all__ = ["ResolvedRef", "ScopeEntry", "enumerate_scope", "extract_references", "write_scope_md"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_DEPTH: Final[int] = 15
SCOPE_MD_RELATIVE_PATH: Final[Path] = Path("docs/workflow-layers/SCOPE.md")

# Hardcoded DH entry-point skill names. Each resolves to
# ``<plugin_root>/skills/<name>/SKILL.md``.
ENTRY_POINT_SKILL_NAMES: Final[tuple[str, ...]] = (
    "work-backlog-item",
    "groom-milestone",
    "work-milestone",
    "complete-milestone",
    "create-milestone",
    "start-milestone",
    "group-items-to-milestone",
)

# The 4 reference types `extract_references` can produce, per architect
# spec Section 2.9 / Section 3.3.
ReferenceType = Literal["mermaid_node", "prose_skill", "agent_dispatch", "prose_file"]
_KNOWN_REFERENCE_TYPES: Final[tuple[ReferenceType, ...]] = (
    "mermaid_node",
    "prose_skill",
    "agent_dispatch",
    "prose_file",
)

# ---------------------------------------------------------------------------
# Reference detection patterns (architect spec Section 1.1 pattern table)
# ---------------------------------------------------------------------------

_MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
_MD_PATH_IN_LABEL_RE = re.compile(r"(?:\.{1,2}/)?[A-Za-z0-9_][A-Za-z0-9_./-]*\.md")
_SLASH_SKILL_RE = re.compile(r"/dh:([a-z][a-z0-9-]*)")
_SKILL_CALL_RE = re.compile(r"Skill\(\s*skill\s*=\s*[\"']dh:([a-z][a-z0-9-]*)[\"']")
_AGENT_DISPATCH_RE = re.compile(r"subagent_type\s*=\s*[\"']dh:([a-z][a-z0-9-]*)[\"']")

# Prose file references: "Load X.md" / "Read references/..." (architect spec Section
# 1.1 pattern table). Observed real-world usage (e.g.
# skills/work-backlog-item/references/workflows/work/start.md) uses markdown-link
# syntax — "Load [scope.md](./scope.md)" — in addition to the bare form shown in the
# architect spec's illustrative fixture, so both forms are matched here. URL fragments
# (`#anchor`) on the link target are stripped before resolution.
_PROSE_FILE_RE = re.compile(
    r"\b(?:Load|Read)\s+(?:"
    r"\[[^\]]*\]\((?P<link_target>[^)#\s]+)(?:#[^)\s]*)?\)"
    r"|(?P<bare_target>references/[A-Za-z0-9_./-]+|[A-Za-z0-9_./-]+\.md)"
    r")"
)


# ---------------------------------------------------------------------------
# Types (architect spec Section 2.1 / Section 2.9)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScopeEntry:
    """One reachable file discovered by the scope crawl.

    Attributes:
        file_path: Plugin-root-relative path to the reachable file.
        entry_point: Name of the entry-point skill this file was reached
            from (e.g. ``"work-backlog-item"``).
        reference_type: One of ``"entry_point"``, ``"mermaid_node"``,
            ``"prose_skill"``, ``"agent_dispatch"``, ``"prose_file"``.
        depth: BFS depth from the entry point (0 for the entry point
            itself).
    """

    file_path: Path
    entry_point: str
    reference_type: str
    depth: int


@dataclass(frozen=True, slots=True)
class ResolvedRef:
    """A single reference resolved from within one source file.

    Attributes:
        source_file: Plugin-root-relative path to the file containing the
            reference.
        target_file: Plugin-root-relative path to the resolved target
            file. Always an existing file within ``plugin_root``.
        reference_type: The pattern category that matched.
        raw_pattern: The verbatim substring that triggered resolution,
            kept for diagnostics.
    """

    source_file: Path
    target_file: Path
    reference_type: ReferenceType
    raw_pattern: str


# ---------------------------------------------------------------------------
# Regex-match boundary narrowing
# ---------------------------------------------------------------------------


def _require_group(match: re.Match[str], index: int) -> str:
    """Narrow an optional regex capture group to ``str``.

    This is the sole boundary in this module where a value of uncertain
    shape (``str | Any`` per ``re.Match.group`` typeshed stubs) enters
    typed code; the ``isinstance`` check below performs the narrowing.

    Args:
        match: A successful regex match.
        index: The capture group index to read.

    Returns:
        The matched text for the given group.

    Raises:
        TypeError: If the group did not participate in the match. This
            indicates a pattern/group-index mismatch in this module, not
            malformed input — patterns here never have optional groups at
            the indices we read.
    """
    value = match.group(index)
    if not isinstance(value, str):
        message = f"regex group {index} did not participate in match {match!r}"
        raise TypeError(message)
    return value


def _require_one_of_groups(match: re.Match[str], *names: str) -> str:
    """Narrow the first participating group out of a set of alternatives.

    Used for regex patterns with alternation where exactly one of several
    named groups participates per match (e.g. a markdown-link form vs. a
    bare-path form of the same reference).

    Args:
        match: A successful regex match.
        names: Candidate group names, checked in order.

    Returns:
        The matched text for the first name that participated.

    Raises:
        TypeError: If none of the named groups participated. This
            indicates the alternation in the pattern has a branch with no
            corresponding named group here — a pattern/helper mismatch,
            not malformed input.
    """
    for name in names:
        value = match.group(name)
        if isinstance(value, str):
            return value
    message = f"none of the groups {names} participated in match {match!r}"
    raise TypeError(message)


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------


def _resolve_target(
    *, source_file: Path, raw_pattern: str, reference_type: ReferenceType, absolute_target: Path, plugin_root: Path
) -> ResolvedRef | None:
    """Resolve a candidate absolute target path into a `ResolvedRef`.

    Args:
        source_file: Plugin-root-relative path to the referencing file.
        raw_pattern: The verbatim matched text, kept for diagnostics.
        reference_type: The pattern category that matched.
        absolute_target: The candidate absolute filesystem path.
        plugin_root: Absolute path to the plugin root directory.

    Returns:
        A `ResolvedRef` when the target exists and is inside
        `plugin_root`; `None` when unresolvable. Unresolvable targets are
        logged as warnings, never raised.
    """
    resolved = absolute_target.resolve()
    if not resolved.is_file():
        logger.warning(
            "Unresolvable %s reference in %s: %r -> %s (file does not exist)",
            reference_type,
            source_file,
            raw_pattern,
            resolved,
        )
        return None
    try:
        relative_target = resolved.relative_to(plugin_root)
    except ValueError:
        logger.warning(
            "Unresolvable %s reference in %s: %r -> %s (outside plugin root %s)",
            reference_type,
            source_file,
            raw_pattern,
            resolved,
            plugin_root,
        )
        return None
    return ResolvedRef(
        source_file=source_file, target_file=relative_target, reference_type=reference_type, raw_pattern=raw_pattern
    )


def _extract_mermaid_refs(text: str, source_file: Path, source_dir: Path, plugin_root: Path) -> list[ResolvedRef]:
    """Detect `.md` paths inside Mermaid node labels.

    Args:
        text: Full text content of the source file.
        source_file: Plugin-root-relative path to the source file.
        source_dir: Absolute directory containing the source file, used
            as the resolution base (architect spec Section 1.1: "Resolve
            relative to the referencing file's directory").
        plugin_root: Absolute path to the plugin root directory.

    Returns:
        Resolved references for every `.md` path found inside a
        ` ```mermaid ` fenced block.
    """
    refs: list[ResolvedRef] = []
    for block_match in _MERMAID_FENCE_RE.finditer(text):
        block_text = _require_group(block_match, 1)
        for path_match in _MD_PATH_IN_LABEL_RE.finditer(block_text):
            raw_path = path_match.group(0)
            resolved = _resolve_target(
                source_file=source_file,
                raw_pattern=raw_path,
                reference_type="mermaid_node",
                absolute_target=source_dir / raw_path,
                plugin_root=plugin_root,
            )
            if resolved is not None:
                refs.append(resolved)
    return refs


def _extract_skill_refs(text: str, source_file: Path, plugin_root: Path) -> list[ResolvedRef]:
    """Detect `/dh:skill-name` and `Skill(skill='dh:...')` invocations.

    Args:
        text: Full text content of the source file.
        source_file: Plugin-root-relative path to the source file.
        plugin_root: Absolute path to the plugin root directory.

    Returns:
        Resolved references to `skills/<name>/SKILL.md` for each match.
    """
    refs: list[ResolvedRef] = []
    for pattern in (_SLASH_SKILL_RE, _SKILL_CALL_RE):
        for match in pattern.finditer(text):
            name = _require_group(match, 1)
            target = plugin_root / "skills" / name / "SKILL.md"
            resolved = _resolve_target(
                source_file=source_file,
                raw_pattern=match.group(0),
                reference_type="prose_skill",
                absolute_target=target,
                plugin_root=plugin_root,
            )
            if resolved is not None:
                refs.append(resolved)
    return refs


def _extract_agent_refs(text: str, source_file: Path, plugin_root: Path) -> list[ResolvedRef]:
    """Detect `subagent_type="dh:agent-name"` dispatches.

    Args:
        text: Full text content of the source file.
        source_file: Plugin-root-relative path to the source file.
        plugin_root: Absolute path to the plugin root directory.

    Returns:
        Resolved references to `agents/<name>.md` for each match.
    """
    refs: list[ResolvedRef] = []
    for match in _AGENT_DISPATCH_RE.finditer(text):
        name = _require_group(match, 1)
        target = plugin_root / "agents" / f"{name}.md"
        resolved = _resolve_target(
            source_file=source_file,
            raw_pattern=match.group(0),
            reference_type="agent_dispatch",
            absolute_target=target,
            plugin_root=plugin_root,
        )
        if resolved is not None:
            refs.append(resolved)
    return refs


def _extract_prose_file_refs(text: str, source_file: Path, source_dir: Path, plugin_root: Path) -> list[ResolvedRef]:
    """Detect prose file references: `Load X.md` and `Read references/...`.

    Matches both the bare form (`Load references/workflows/groom/swarm.md`)
    and the markdown-link form (`Load [scope.md](./scope.md)`) — the latter
    is the dominant convention in real DH reference files.

    Args:
        text: Full text content of the source file.
        source_file: Plugin-root-relative path to the source file.
        source_dir: Absolute directory containing the source file, used
            as the resolution base.
        plugin_root: Absolute path to the plugin root directory.

    Returns:
        Resolved references for each prose match.
    """
    refs: list[ResolvedRef] = []
    for match in _PROSE_FILE_RE.finditer(text):
        raw_target = _require_one_of_groups(match, "link_target", "bare_target")
        resolved = _resolve_target(
            source_file=source_file,
            raw_pattern=match.group(0),
            reference_type="prose_file",
            absolute_target=source_dir / raw_target,
            plugin_root=plugin_root,
        )
        if resolved is not None:
            refs.append(resolved)
    return refs


def extract_references(file_path: Path, plugin_root: Path) -> list[ResolvedRef]:
    """Detect all 4 reference patterns in one file.

    Args:
        file_path: Plugin-root-relative path to the file to scan.
        plugin_root: Absolute path to the plugin root directory.

    Returns:
        All resolved references found in the file, across all 4 pattern
        categories. Unresolvable candidate matches (target file missing,
        or resolving outside `plugin_root`) are excluded here and logged
        as warnings — never raised.
    """
    resolved_root = plugin_root.resolve()
    absolute_source = (resolved_root / file_path).resolve()
    text = absolute_source.read_text(encoding="utf-8")
    source_dir = absolute_source.parent

    refs: list[ResolvedRef] = []
    refs.extend(_extract_mermaid_refs(text, file_path, source_dir, resolved_root))
    refs.extend(_extract_skill_refs(text, file_path, resolved_root))
    refs.extend(_extract_agent_refs(text, file_path, resolved_root))
    refs.extend(_extract_prose_file_refs(text, file_path, source_dir, resolved_root))
    return refs


# ---------------------------------------------------------------------------
# BFS crawl
# ---------------------------------------------------------------------------


# A `skills/<name>/...` path has at least 2 segments: the "skills"
# directory itself and the skill's own directory name.
_SKILLS_PATH_MIN_PARTS: Final[int] = 2


def _derive_entry_point_name(relative_path: Path) -> str:
    """Derive the entry-point skill name from a `skills/<name>/SKILL.md` path.

    Args:
        relative_path: Plugin-root-relative path to an entry-point file.

    Returns:
        The skill directory name when the path follows the
        `skills/<name>/...` convention; otherwise the file stem as a
        best-effort fallback.
    """
    parts = relative_path.parts
    if len(parts) >= _SKILLS_PATH_MIN_PARTS and parts[0] == "skills":
        return parts[1]
    return relative_path.stem


def enumerate_scope(
    entry_points: list[Path], plugin_root: Path, max_depth: int = DEFAULT_MAX_DEPTH
) -> list[ScopeEntry]:
    """Deterministically BFS-crawl the reachable file set from entry points.

    See ADR-1 in ``plan/architect-dh-workflow-extractor-system.md`` for
    why this crawl is fully deterministic (no LLM involvement).

    Args:
        entry_points: Absolute (or CWD-relative) paths to entry-point
            files, e.g. `plugin_root / "skills" / name / "SKILL.md"`.
        plugin_root: Absolute path to the plugin root directory. All
            `ScopeEntry.file_path` values are relative to this root.
        max_depth: Maximum BFS depth to traverse. A node at exactly
            `max_depth` is included in the result, but its own
            references are not expanded — this bounds circular reference
            chains to at most `max_depth + 1` depth levels.

    Returns:
        One `ScopeEntry` per reachable file, visited at most once,
        ordered by BFS discovery order (entry points first, in the order
        given).
    """
    resolved_root = plugin_root.resolve()
    visited: set[Path] = set()
    entries: list[ScopeEntry] = []
    queue: deque[tuple[Path, str, str, int]] = deque()

    for entry_point in entry_points:
        absolute_entry = entry_point.resolve()
        if not absolute_entry.is_file():
            logger.warning("Entry point file does not exist: %s", entry_point)
            continue
        try:
            relative_entry = absolute_entry.relative_to(resolved_root)
        except ValueError:
            logger.warning("Entry point %s is outside plugin root %s", entry_point, resolved_root)
            continue
        if relative_entry in visited:
            continue
        visited.add(relative_entry)
        queue.append((relative_entry, _derive_entry_point_name(relative_entry), "entry_point", 0))

    while queue:
        current_path, entry_point_name, reference_type, depth = queue.popleft()
        entries.append(
            ScopeEntry(file_path=current_path, entry_point=entry_point_name, reference_type=reference_type, depth=depth)
        )
        if depth >= max_depth:
            continue
        for ref in extract_references(current_path, resolved_root):
            if ref.target_file in visited:
                continue
            visited.add(ref.target_file)
            queue.append((ref.target_file, entry_point_name, ref.reference_type, depth + 1))

    return entries


# ---------------------------------------------------------------------------
# SCOPE.md serialization (architect spec Section 3.3)
# ---------------------------------------------------------------------------


def write_scope_md(entries: list[ScopeEntry], output_path: Path) -> None:
    """Write the SCOPE.md markdown table described in architect spec Section 3.3.

    Downstream consumers must locate columns via the header row, not
    hardcoded positions — this function is the sole producer of the
    format and may reorder or add columns in the future.

    Args:
        entries: Scope entries to write, in the order they should appear
            in the output table.
        output_path: Destination path for `SCOPE.md`. Parent directories
            are created if missing.
    """
    entry_point_names: list[str] = list(
        dict.fromkeys(entry.entry_point for entry in entries if entry.reference_type == "entry_point")
    )
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# DH Workflow Extraction Scope",
        "",
        "Generated by enumerate_scope.py. Do not edit manually.",
        f"Last generated: {timestamp}  ",
        f"Entry points: {', '.join(entry_point_names)}",
        "",
        "| file_path | entry_point | reference_type | depth |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {entry.file_path.as_posix()} | {entry.entry_point} | {entry.reference_type} | {entry.depth} |"
        for entry in entries
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _resolve_plugin_root() -> Path:
    """Resolve the plugin root from `CLAUDE_PLUGIN_ROOT` or the CWD.

    Returns:
        `CLAUDE_PLUGIN_ROOT` as a `Path` when set; otherwise `Path.cwd()`
        (architect spec Section 1.1: "`plugin_root` resolved from
        `CLAUDE_PLUGIN_ROOT` env var or CWD").
    """
    env_value = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_value:
        return Path(env_value)
    return Path.cwd()


def _warn_on_missing_reference_types(entries: list[ScopeEntry]) -> None:
    """Log a warning for each known reference type absent from a crawl.

    Args:
        entries: The full result of one `enumerate_scope` run.
    """
    observed = {entry.reference_type for entry in entries}
    for reference_type in _KNOWN_REFERENCE_TYPES:
        if reference_type not in observed:
            logger.warning(
                "No scope entries were detected with reference_type=%r in this crawl; "
                "either no such reference exists in the crawled file set, or the "
                "detection pattern needs review.",
                reference_type,
            )


def main() -> int:
    """Crawl the DH plugin's entry points and write `SCOPE.md`.

    Returns:
        Process exit code; always `0` (unresolvable references are
        logged as warnings, never fatal).
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    plugin_root = _resolve_plugin_root()
    entry_points = [plugin_root / "skills" / name / "SKILL.md" for name in ENTRY_POINT_SKILL_NAMES]

    entries = enumerate_scope(entry_points=entry_points, plugin_root=plugin_root)
    _warn_on_missing_reference_types(entries)

    output_path = plugin_root / SCOPE_MD_RELATIVE_PATH
    write_scope_md(entries, output_path)
    print(f"Wrote {len(entries)} scope entries to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
