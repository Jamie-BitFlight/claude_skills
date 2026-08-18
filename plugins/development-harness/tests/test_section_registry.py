"""General-mechanism tests for the canonical section/subsection registry (#2970).

Narrowly-scoped regression tests for specific historical bug *names* already exist
elsewhere (``test_section_name_registry_drift.py``, ``test_section_roundtrip_integrity.py``).
This suite proves the *mechanism* itself — alias resolution, the write-boundary
stderr diagnostic, and the subsection-level registry — holds for names never
seen anywhere in this repo, not just the specific names #2956/#2970 named.
"""

from __future__ import annotations

import backlog_core.operations as ops
import pytest
from backlog_core import github_sync, rendering, section_registry
from backlog_core.models import GroomedData, Output

# ---------------------------------------------------------------------------
# Section-level alias resolution (section_registry.resolve_section_name)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("Facts check", "fact_check"),
        ("Fact Checker", "fact_check"),
        ("FACT CHECKER", "fact_check"),
        ("fact-check", "fact_check"),
    ],
)
def test_resolve_section_name_matches_registered_alias_case_insensitively(alias: str, expected: str) -> None:
    """resolve_section_name resolves every registered historic alias, any case.

    Tests: section_registry.resolve_section_name alias-map lookup
    Why: The alias map is distinct from SECTION_HEADING (#2970 point 2) — this
         proves it is actually consulted, not merely present and unused.
    """
    assert section_registry.resolve_section_name(alias) == expected


def test_resolve_section_name_novel_name_returns_none() -> None:
    """A name matching neither the alias map nor SECTION_HEADING resolves to None.

    Tests: section_registry.resolve_section_name miss path
    Why: Falsification target — proves the resolver doesn't silently invent a
         match for input it doesn't recognise.
    """
    assert section_registry.resolve_section_name("Zzyx Quantum Analysis 9000") is None


def test_normalize_section_key_persists_under_canonical_never_alias_spelling() -> None:
    """A caller-supplied alias persists under its resolved canonical key, never the alias spelling.

    Tests: operations._normalize_section_key alias resolution (#2970 point 3)
    Why: The item's explicit requirement — an alias must never leak into storage
         as its own spelling, and never fall through to unknown__.
    """
    assert ops._normalize_section_key("Facts check") == "fact_check"
    assert ops._normalize_section_key("Fact Checker") == "fact_check"


# ---------------------------------------------------------------------------
# Write-boundary stderr diagnostic (#2970 point 4)
# ---------------------------------------------------------------------------


def test_unregistered_section_name_emits_stderr_diagnostic(capsys: pytest.CaptureFixture[str]) -> None:
    """A genuinely novel, unregistered section name triggers a stderr diagnostic.

    Tests: operations._normalize_section_key -> _warn_unregistered_section
    How: Call _normalize_section_key with a name that resolves through neither
         the registry nor the alias map (never seen anywhere in this repo).
    Why: The direct root cause #2970 exists to close — unregistered names must
         be visible immediately, not silently accumulate under unknown__.
    """
    novel_name = "Never Before Seen Diagnostic Probe"
    key = ops._normalize_section_key(novel_name)

    assert key.startswith("unknown__")
    captured = capsys.readouterr()
    assert novel_name in captured.err
    assert "section_registry.py" in captured.err


def test_unregistered_section_name_records_output_warning() -> None:
    """The same fallback also records a structured warning on the Output aggregator.

    Tests: operations._normalize_section_key(output=...) -> Output.warnings
    Why: An MCP caller reads Output.warnings, not stderr — both channels must
         carry the diagnostic (see ARCHITECTURE.md "Module: section_registry.py").
    """
    out = Output()
    novel_name = "Another Never Before Seen Probe"

    ops._normalize_section_key(novel_name, output=out)

    assert any(novel_name in w for w in out.warnings)


def test_registered_section_name_emits_no_stderr_diagnostic(capsys: pytest.CaptureFixture[str]) -> None:
    """A canonical or aliased name never triggers the unregistered-name diagnostic.

    Tests: operations._normalize_section_key resolved path — falsification check
    Why: Proves the diagnostic fires only on a genuine fallback, not on every
         call — a diagnostic that fires unconditionally would be noise, not signal.
    """
    ops._normalize_section_key("RT-ICA")
    ops._normalize_section_key("Facts check")

    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Subsection-level registry (#2970 point 6 — same mechanism, one level deeper)
# ---------------------------------------------------------------------------


def test_resolve_subsection_name_case_insensitive() -> None:
    """resolve_subsection_name matches a registered subsection regardless of case.

    Tests: section_registry.resolve_subsection_name
    """
    assert section_registry.resolve_subsection_name("priority") == "Priority"
    assert section_registry.resolve_subsection_name("PRIORITY") == "Priority"
    assert section_registry.resolve_subsection_name("Priority") == "Priority"


def test_resolve_subsection_name_novel_name_returns_none() -> None:
    """An unregistered subsection name resolves to None — it is legitimate free text.

    Tests: section_registry.resolve_subsection_name miss path — falsification check
    """
    assert section_registry.resolve_subsection_name("Zzyx Subsection Probe") is None


def test_normalize_groomed_subsections_folds_miscased_key_longer_content_wins() -> None:
    """Two spellings of one canonical subsection fold to one key; longer content wins.

    Tests: rendering.normalize_groomed_subsections
    Why: Mirrors normalize_unknown_sections one level deeper (#2970 point 6) —
         reuses github_sync._merge_groomed's "longer content wins" per-key rule
         rather than inventing a second merge policy (#2970 point 10).
    """
    folded = rendering.normalize_groomed_subsections({"priority": "short", "Priority": "much longer canonical content"})

    assert folded == {"Priority": "much longer canonical content"}


def test_normalize_groomed_subsections_unregistered_name_passes_through() -> None:
    """An unregistered subsection name is preserved verbatim, not dropped or renamed.

    Tests: rendering.normalize_groomed_subsections — falsification check
    """
    folded = rendering.normalize_groomed_subsections({"Zzyx Subsection Probe": "content"})

    assert folded == {"Zzyx Subsection Probe": "content"}


def test_github_sync_parse_groomed_section_canonicalizes_subsection_key() -> None:
    """A GitHub-authored ### heading with non-canonical case still lands under the canonical key.

    Tests: github_sync._parse_groomed_section (the subsection write boundary) via
           parse_issue_body's public entry point
    Why: This is the write-boundary analogue of normalize_groomed_subsections'
         read-boundary fold — a GitHub-authored "### priority" and a locally
         written "Priority" must collide on one key, not diverge into two.
    """
    body = "## Groomed (2026-08-18)\n\n### priority\n\nHigh priority content.\n"

    item = github_sync.parse_issue_body(body)

    groomed = item.sections["groomed"]
    assert isinstance(groomed, GroomedData)
    assert "Priority" in groomed.subsections
    assert "priority" not in groomed.subsections
    assert groomed.subsections["Priority"] == "High priority content."


def test_github_sync_parse_groomed_section_preserves_novel_subsection_name() -> None:
    """A never-before-seen ### subsection heading is preserved verbatim — falsification check.

    Tests: github_sync._parse_groomed_section unregistered-name passthrough
    """
    body = "## Groomed (2026-08-18)\n\n### Zzyx Subsection Probe\n\nSome content.\n"

    item = github_sync.parse_issue_body(body)

    groomed = item.sections["groomed"]
    assert isinstance(groomed, GroomedData)
    assert groomed.subsections == {"Zzyx Subsection Probe": "Some content."}
