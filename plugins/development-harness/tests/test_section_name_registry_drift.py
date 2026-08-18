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
from backlog_core.models import Entry, GroomedData, Section
from backlog_core.rendering import SECTION_HEADING, heading_to_unknown_key, normalize_unknown_sections

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

_WRITE_RE = re.compile(r"""section=["']([^"']+)["']""")
_READ_RE = re.compile(r"""sections(?:\[|\.get\()["']([^"']+)["']""")


def _iter_doc_files() -> list[Path]:
    return sorted((_PLUGIN_ROOT / "agents").rglob("*.md")) + sorted((_PLUGIN_ROOT / "skills").rglob("*.md"))


def _referenced_section_names(text: str) -> set[str]:
    names = set(_WRITE_RE.findall(text)) | set(_READ_RE.findall(text))
    # Template placeholders (e.g. "{name}", "{section-name}") and pure-punctuation
    # placeholders (e.g. `section="..."` in a CLI-flag mapping table) are not
    # literal section names — a real one always contains at least one letter.
    return {n for n in names if "{" not in n and "}" not in n and any(c.isalpha() for c in n)}


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


def test_heading_to_unknown_key_sanitizes_punctuation_not_just_spaces() -> None:
    """heading_to_unknown_key must collapse ALL punctuation, not only spaces.

    Before the fix, only " " -> "_" was sanitized, so "Output / Evidence" produced
    "unknown__output_/_evidence" — a key containing a literal "/" that can never
    equal a later-registered SECTION_HEADING key like "output_evidence" under plain
    string equality (found live in issue #1726's cache; see the retroactive-fold
    test below).
    """
    assert heading_to_unknown_key("Output / Evidence") == "unknown__output_evidence"
    # General case: any run of non-alphanumeric characters collapses to one "_".
    assert heading_to_unknown_key("A/B  C!!D") == "unknown__a_b_c_d"


def test_unknown_fold_retroactively_matches_issue_1726s_stuck_key() -> None:
    """normalize_unknown_sections must fold a legacy malformed key by display title.

    Reproduces the exact key spelling found live in
    ``~/.dh/projects/-Users-jamienelson-repos-claude_skills/github-cache/items/issues/1726.yaml``
    (a real evidence-collection procedure written during grooming, stuck under
    ``unknown__output_/_evidence`` because the pre-fix heading_to_unknown_key never
    sanitized the "/"). Fixing heading_to_unknown_key alone only prevents new writes
    from producing this shape — it does not change bytes already on disk, so the
    fold must match by display title (unknown_key_to_heading output), not by raw
    key-string equality against the newly-sanitized "output_evidence" key.
    """
    assert "output_evidence" in SECTION_HEADING, "output_evidence must be registered for this fold to apply"
    stuck_key = "unknown__output_/_evidence"
    sections: dict[str, Section | GroomedData] = {
        stuck_key: Section(
            entries=[
                Entry(
                    id="2026-05-08T00:00:00Z",
                    content="The exact `gh api` commands run, with full response JSON recorded verbatim",
                )
            ]
        )
    }

    folded = normalize_unknown_sections(sections)

    assert stuck_key not in folded, "legacy malformed key must not survive the fold"
    assert "output_evidence" in folded, "content must fold into the canonical registered key"
    folded_section = folded["output_evidence"]
    assert isinstance(folded_section, Section)
    assert folded_section.entries[0].content.startswith("The exact `gh api` commands")
