"""Guards against section-name drift between doc references and SECTION_HEADING (#2979).

A `backlog_groom(section="X")` write directive or `sections["X"]` read lookup in a skill
or agent doc is only correct if writing under name X and reading it back produces the same
X — i.e. it round-trips through the same `_normalize_section_key` / `_section_display_title`
machinery `backlog_core.operations` uses at runtime. #2979 found three docs referencing a
third, uncodified key format ("acceptance criteria", lowercase-with-spaces) that matched
neither the snake_case storage key nor the Title Case display key, so every such read
silently returned nothing. This test parses every agent/skill doc for `section=`/`sections[...]`
references and fails if any referenced name does not round-trip.
"""

from __future__ import annotations

import re
from pathlib import Path

import backlog_core.operations as ops

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

_WRITE_RE = re.compile(r"""section=["']([^"']+)["']""")
_READ_RE = re.compile(r"""sections(?:\[|\.get\()["']([^"']+)["']""")


def _iter_doc_files() -> list[Path]:
    return sorted((_PLUGIN_ROOT / "agents").rglob("*.md")) + sorted((_PLUGIN_ROOT / "skills").rglob("*.md"))


def _referenced_section_names(text: str) -> set[str]:
    names = set(_WRITE_RE.findall(text)) | set(_READ_RE.findall(text))
    # Template placeholders (e.g. "{name}", "{section-name}") are not literal section names.
    return {n for n in names if "{" not in n and "}" not in n}


def test_doc_section_names_round_trip_through_section_heading() -> None:
    """Every section= write directive and sections[...] read lookup in agent/skill docs
    must resolve to the same string once written and displayed back — proving the doc
    references a name that backlog_core's SECTION_HEADING registry (or its generic
    unknown__ fallback) actually produces, not a third uncodified format.
    """
    mismatches: list[tuple[str, str, str]] = []
    for path in _iter_doc_files():
        text = path.read_text(encoding="utf-8")
        for name in _referenced_section_names(text):
            key = ops._normalize_section_key(name)
            display_title = ops._section_display_title(key)
            if display_title != name:
                mismatches.append((str(path.relative_to(_PLUGIN_ROOT)), name, display_title))

    assert not mismatches, (
        "Section name(s) referenced in docs do not round-trip through "
        "backlog_core.rendering.SECTION_HEADING (write name -> storage key -> display title "
        "!= original name), so a consumer reading that exact key would get nothing back. "
        "Each entry is (file, referenced_name, actual_display_title) — fix the doc to use "
        "actual_display_title, or register referenced_name in SECTION_HEADING if it needs "
        "different display text: " + repr(mismatches)
    )
