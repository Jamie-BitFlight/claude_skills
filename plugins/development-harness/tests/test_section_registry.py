"""General-mechanism tests for the canonical section/subsection registry (#2970).

Narrowly-scoped regression tests for specific historical bug *names* already exist
elsewhere (``test_section_name_registry_drift.py``, ``test_section_roundtrip_integrity.py``).
This suite proves the *mechanism* itself — alias resolution, the write-boundary
stderr diagnostic, and the subsection-level registry — holds for names never
seen anywhere in this repo, not just the specific names #2956/#2970 named.
"""

from __future__ import annotations

import re
from pathlib import Path

import backlog_core.operations as ops
import pytest
from backlog_core import github_sync, rendering, section_registry
from backlog_core.models import BacklogItem, Entry, GroomedData, Output, Section

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

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


@pytest.mark.parametrize("canonical", sorted(section_registry.SECTION_HEADING))
def test_resolve_section_name_accepts_canonical_snake_case_value(canonical: str) -> None:
    """resolve_section_name accepts every canonical SectionKey value verbatim (#2987 finding 1).

    Tests: section_registry.resolve_section_name canonical-value acceptance,
           parametrized over every live SECTION_HEADING key so the mechanism
           is proven for all registered sections, not just one example.
    Why: The resolver previously checked only aliases and display headings —
         a caller supplying the storage key itself (e.g. "fact_check", which
         is already the exact value SECTION_HEADING stores under that name)
         got None instead of the key back.
    """
    assert section_registry.resolve_section_name(canonical) == canonical


def test_resolve_section_name_accepts_canonical_value_case_insensitively() -> None:
    """Canonical-value acceptance is case-insensitive, matching every other lookup here."""
    assert section_registry.resolve_section_name("FACT_CHECK") == "fact_check"


def test_normalize_section_key_persists_under_canonical_never_alias_spelling() -> None:
    """A caller-supplied alias persists under its resolved canonical key, never the alias spelling.

    Tests: operations._normalize_section_key alias resolution (#2970 point 3)
    Why: The item's explicit requirement — an alias must never leak into storage
         as its own spelling, and never fall through to unknown__.
    """
    assert ops._normalize_section_key("Facts check") == "fact_check"
    assert ops._normalize_section_key("Fact Checker") == "fact_check"


@pytest.mark.parametrize("canonical", sorted(section_registry.SECTION_HEADING))
def test_normalize_section_key_recovers_registered_name_from_unknown_prefix(canonical: str) -> None:
    """A caller-supplied 'unknown__{name}' key heals to its canonical key (#2987 finding 8).

    Tests: operations._normalize_section_key unknown__-prefix recovery,
           parametrized over every live canonical section name.
    Why: A caller writing back a previously-stored storage key (e.g. a
         round-trip through view_item -> groom_item) must heal the exact
         duplication write-boundary validation exists to prevent — echoing
         the stored unknown__ key back unchanged preserves the duplication
         this whole registry (#2970) exists to close.
    """
    assert ops._normalize_section_key(f"unknown__{canonical}") == canonical


def test_normalize_section_key_unknown_prefix_stays_prefixed_when_unregistered() -> None:
    """An 'unknown__{name}' key for a genuinely unregistered name is unchanged — falsification check."""
    assert ops._normalize_section_key("unknown__zzyx_quantum_probe") == "unknown__zzyx_quantum_probe"


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


def test_normalize_groomed_subsections_equal_length_tie_first_value_wins() -> None:
    """On an exact length tie, the first-seen (canonical) value wins, not the second (#2987 finding 6).

    Tests: rendering.normalize_groomed_subsections tie-break rule
    Why: Must match github_sync._merge_groomed's strict '>' comparison — the
         already-present value is kept unless the incoming value is *strictly*
         longer. A '>=' tie-break instead let an alias spelling silently
         overwrite the canonical value whenever content length happened to
         match exactly.
    """
    folded = rendering.normalize_groomed_subsections({"Priority": "AAAAA", "priority": "BBBBB"})

    assert folded == {"Priority": "AAAAA"}


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


@pytest.mark.parametrize(
    ("first_heading", "first_body", "second_heading", "second_body"),
    [
        ("Priority", "This is a much longer and more detailed priority justification.", "priority", "Short."),
        ("priority", "Short.", "Priority", "This is a much longer and more detailed priority justification."),
    ],
    ids=["canonical-first", "alias-first"],
)
def test_github_sync_parse_groomed_section_longer_content_wins_regardless_of_order(
    first_heading: str, first_body: str, second_heading: str, second_body: str
) -> None:
    """Two ### headings colliding onto one subsection key: LONGER content wins (#2987 finding 5).

    Tests: github_sync._parse_groomed_section merge rule, both source orderings
    Why: Must match github_sync._merge_groomed's documented longer-content-wins
         rule. A naive last-write-wins assignment silently discards longer,
         earlier content whenever a shorter alias heading happens to appear
         second in the source body.
    """
    body = f"## Groomed (2026-08-18)\n\n### {first_heading}\n\n{first_body}\n\n### {second_heading}\n\n{second_body}\n"

    item = github_sync.parse_issue_body(body)

    groomed = item.sections["groomed"]
    assert isinstance(groomed, GroomedData)
    assert groomed.subsections["Priority"] == "This is a much longer and more detailed priority justification."


# ---------------------------------------------------------------------------
# normalize_unknown_sections routes through the alias-aware resolver (#2987 finding 2)
# ---------------------------------------------------------------------------


def test_normalize_unknown_sections_folds_via_alias_with_punctuation() -> None:
    """An unknown__{name} key whose reconstructed heading matches a registered ALIAS still folds.

    Tests: rendering.normalize_unknown_sections alias-aware fold
    Why: The private display-title-only map this function used before never
         consulted SECTION_NAME_ALIASES, so a legacy "unknown__facts_check"
         key (reconstructed title "Facts Check") never folded even though
         "facts check" is a registered alias for fact_check.
    """
    sections: dict[str, Section | GroomedData] = {
        "unknown__facts_check": Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Legacy content.")])
    }

    folded = rendering.normalize_unknown_sections(sections)

    assert "unknown__facts_check" not in folded
    assert "fact_check" in folded
    folded_section = folded["fact_check"]
    assert isinstance(folded_section, Section)
    assert folded_section.entries[0].content == "Legacy content."


@pytest.mark.parametrize("canonical", sorted(section_registry.SECTION_HEADING))
def test_normalize_unknown_sections_folds_stripped_snake_case_key(canonical: str) -> None:
    """An unknown__{snake_case_key} whose stripped form IS the canonical key folds directly.

    Tests: rendering.normalize_unknown_sections raw-stripped-key resolution,
           parametrized over every live canonical section name.
    Why: heading_to_unknown_key's normalisation produces a stripped form that
         is usually already snake_case (e.g. "unknown__root_cause_analysis"),
         so the fold must try the raw stripped key directly, not only the
         reconstructed Title Case heading.
    """
    sections: dict[str, Section | GroomedData] = {
        f"unknown__{canonical}": Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Content.")])
    }

    folded = rendering.normalize_unknown_sections(sections)

    assert f"unknown__{canonical}" not in folded
    assert canonical in folded


# ---------------------------------------------------------------------------
# Legacy Markdown parser routes both heading levels through the registry (#2987 finding 3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("display_name", sorted(rendering.SECTION_HEADING.values()))
def test_parse_md_body_sections_canonicalizes_every_registered_display_heading(display_name: str) -> None:
    """Every registered SECTION_HEADING display heading resolves to its snake_case key.

    Tests: parsing.parse_md_body_sections '## ' heading canonicalization,
           parametrized over every live registered display heading so the
           mechanism is proven generally, not for one example name.
    Why: The legacy Markdown parser consulted only SECTION_NAME_ALIASES
         directly, not the full resolve_section_name registry lookup, so a
         heading like "## Impact Radius" was keyed as "impact radius"
         (lowercased, space-separated) instead of canonical "impact_radius".
    """
    from backlog_core.parsing import parse_md_body_sections

    result = parse_md_body_sections(f"## {display_name}\n\nContent.\n")

    expected_key = section_registry.resolve_section_name(display_name)
    assert expected_key is not None, f"fixture bug: {display_name!r} must resolve via the registry"
    assert expected_key in result
    if display_name.lower() != expected_key:
        assert display_name.lower() not in result, (
            f"{display_name!r} must resolve to {expected_key!r} only, not also stay under its raw lowercased form"
        )


def test_parse_md_body_sections_unregistered_heading_falls_back_to_raw_lowercase() -> None:
    """A genuinely unregistered '## ' heading keeps the legacy raw-lowercased fallback.

    Tests: parsing.parse_md_body_sections unregistered-name passthrough —
           falsification check proving the fix does not unknown__-prefix
           names this legacy path has never prefixed.
    """
    from backlog_core.parsing import parse_md_body_sections

    result = parse_md_body_sections("## Zzyx Quantum Analysis 9000\n\nContent.\n")

    assert "zzyx quantum analysis 9000" in result
    assert not any(k.startswith("unknown__") for k in result)


@pytest.mark.parametrize("subsection_name", sorted(section_registry.SubsectionKey))
def test_parse_md_body_sections_groomed_subsection_canonicalizes_every_registered_name(subsection_name: str) -> None:
    """Every registered subsection name round-trips through the legacy '### ' parser.

    Tests: parsing.parse_md_body_sections / _split_h3_subsections subsection
           canonicalization, parametrized over every live SubsectionKey value.
    Why: _split_h3_subsections stored '### ' heading text verbatim with no
         registry lookup at all, so a lowercase variant like "### priority"
         never folded to the canonical "Priority" key the way the
         GitHub-parse boundary (github_sync._parse_groomed_section) already did.
    """
    from backlog_core.parsing import parse_md_body_sections

    body = f"## Groomed (2026-08-18)\n\n### {subsection_name.lower()}\n\nContent.\n"
    result = parse_md_body_sections(body)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)
    assert subsection_name in groomed.subsections


# ---------------------------------------------------------------------------
# Subsection registry completeness against real producers (#2987 finding 4)
# ---------------------------------------------------------------------------

_H3_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)


def _producer_subsection_names() -> set[str]:
    """Return every '### ' subsection heading emitted by the real producer files.

    Reads the live producer files instead of a hardcoded copy, so this test
    tracks the producers rather than drifting from them (see AGENTS.md "No
    Derived Data in Documentation").

    Returns:
        Set of subsection heading names as they appear in the producers,
        with the leading '### ' stripped.
    """
    groomer_text = (_PLUGIN_ROOT / "agents" / "backlog-item-groomer.md").read_text(encoding="utf-8")
    template_text = (_PLUGIN_ROOT / "skills" / "backlog" / "templates" / "item.md").read_text(encoding="utf-8")
    # Only the fenced "Output Format" markdown block in the groomer doc names
    # real subsection content — every other '### ' in that file is one of its
    # own instructional section headers, not a subsection name it produces.
    fence_match = re.search(r"```markdown\n(.*?)\n```", groomer_text, re.DOTALL)
    groomer_block = fence_match.group(1) if fence_match else ""
    return set(_H3_HEADING_RE.findall(groomer_block)) | set(_H3_HEADING_RE.findall(template_text))


@pytest.mark.parametrize("name", sorted(_producer_subsection_names()))
def test_producer_subsection_name_resolves_through_registry(name: str) -> None:
    """Every subsection name a real producer emits resolves to itself through the registry.

    Tests: section_registry SubsectionKey completeness
    How: Reads the live producer files (backlog-item-groomer.md Output Format
         block, skills/backlog/templates/item.md Groomed subsections) rather
         than a hardcoded name list, so this test tracks the producers
         instead of drifting from them.
    Why: A subsection name a producer emits on every real grooming run should
         resolve to a stable canonical key like every other registered
         subsection — an unrecognised passthrough is correct only for
         genuinely novel free text, not for names the repo's own tooling
         produces routinely.
    """
    assert section_registry.resolve_subsection_name(name) == name


# ---------------------------------------------------------------------------
# Top-level '## ' heading parse routes through the alias-aware resolver too
# (post-#2987 Copilot pass finding: only the '### ' subsection parser and the
# legacy .md '## ' parser were fixed — github_sync.parse_issue_body's '## '
# lookup still bypassed SECTION_NAME_ALIASES via the raw _HEADING_TO_KEY map)
# ---------------------------------------------------------------------------


def test_parse_issue_body_top_level_heading_resolves_registered_alias() -> None:
    """A GitHub issue '## Facts check' heading resolves to 'fact_check', not unknown__facts_check.

    Tests: github_sync.parse_issue_body top-level '## ' heading resolution
    Why: parse_issue_body's subsection parser (_parse_groomed_section) and the
         legacy .md parser (parse_md_body_sections) both route through
         resolve_section_name, but the top-level '## ' lookup still used the
         raw _HEADING_TO_KEY map (exact SECTION_HEADING display text only),
         so a registered alias spelling split from the canonical section on a
         real GitHub round-trip.
    """
    body = "## Facts check\n\n<div><sub>2026-01-01T00:00:00Z</sub>\n\nSome content.\n</div>\n"

    item = github_sync.parse_issue_body(body)

    assert "fact_check" in item.sections
    assert not any(key.startswith("unknown__facts_check") for key in item.sections)


def test_heading_to_section_key_resolves_registered_alias() -> None:
    """heading_to_section_key resolves a registered alias, not only exact display text."""
    assert github_sync.heading_to_section_key("Facts check") == "fact_check"


# ---------------------------------------------------------------------------
# Two headings resolving to the same section merge, not overwrite
# (#3015 Greptile review finding: "## Fact-Check" and its alias "## Facts
# check" both resolve to "fact_check" via resolve_section_name, but the
# second heading's dict assignment previously replaced the first heading's
# Section outright — permanently dropping its entries on reconciliation)
# ---------------------------------------------------------------------------


def test_parse_issue_body_canonical_heading_and_alias_merge_not_overwrite() -> None:
    """A canonical heading and a same-key alias heading in one body merge, not overwrite.

    Tests: github_sync.parse_issue_body two-heading collision on one section_key
    Why: "## Fact-Check" and "## Facts check" both resolve to "fact_check".
         Assigning ``parsed_sections[section_key] = Section(entries=entries)``
         unconditionally for the second heading discarded the first heading's
         entries outright instead of merging them.
    """
    body = (
        "## Fact-Check\n\n<div><sub>2026-01-01T00:00:00Z</sub>\n\nFirst entry.\n</div>\n\n"
        "## Facts check\n\n<div><sub>2026-01-02T00:00:00Z</sub>\n\nSecond entry.\n</div>\n"
    )

    item = github_sync.parse_issue_body(body)

    section = item.sections["fact_check"]
    assert isinstance(section, Section)
    assert {e.content for e in section.entries} == {"First entry.", "Second entry."}


# ---------------------------------------------------------------------------
# Write-back unknown__-prefix healing tries the reconstructed heading too
# (post-#2987 Copilot pass finding: the write boundary's unknown__ recovery
# tried only the raw stripped key, missing multi-word aliases whose stripped
# form uses underscores where the alias map uses spaces)
# ---------------------------------------------------------------------------


def test_normalize_section_key_recovers_multiword_alias_from_unknown_prefix() -> None:
    """'unknown__facts_check' heals to 'fact_check' on write-back, mirroring the read-time fold.

    Tests: operations._normalize_section_key unknown__-prefix recovery via the
           reconstructed-heading fallback (mirrors
           rendering.normalize_unknown_sections, see
           test_normalize_unknown_sections_folds_via_alias_with_punctuation).
    Why: "unknown__facts_check" strips to "facts_check", which matches
         neither a SectionKey value nor the "facts check" alias spelling
         (space, not underscore) — only its reconstructed heading
         "Facts Check" resolves via the alias map. Without the reconstructed-
         heading fallback, a round-trip through view_item -> groom_item never
         heals this key even though the read path already folds it.
    """
    assert ops._normalize_section_key("unknown__facts_check") == "fact_check"


# ---------------------------------------------------------------------------
# AC-overlap check keys off the resolved canonical section, not raw spelling
# (post-#2987 Copilot pass finding: canonicalization made "acceptance_criteria"
# a valid section input, but the overlap checks still compared against the
# literal "Acceptance Criteria" display string)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("section_name", ["Acceptance Criteria", "acceptance_criteria", "ACCEPTANCE_CRITERIA"])
def test_handle_update_groomed_ac_overlap_check_fires_for_every_ac_spelling(
    section_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_handle_update_groomed's AC-overlap warning fires for the canonical key too, not only the display string.

    Tests: operations._handle_update_groomed -> _check_ac_overlap gating,
           parametrized over the display heading, the canonical snake_case
           key, and an uppercase variant of the canonical key.
    Why: A caller supplying the now-valid canonical key "acceptance_criteria"
         silently skipped the dedicated AC-overlap warning because the gate
         compared ``section_name == "Acceptance Criteria"`` verbatim instead
         of the resolved section key.
    """
    item = BacklogItem(description="- [ ] Looks like an AC checkbox", reference="p1-demo")
    monkeypatch.setattr(ops, "_write_groomed_to_reference", lambda *a, **k: None)
    monkeypatch.setattr(ops, "_reconcile_groomed_item", lambda *a, **k: None)
    out = Output()

    ops._handle_update_groomed(item, "AC content", section_name, "owner/repo", output=out)

    assert any("Acceptance Criteria" in w for w in out.warnings)


@pytest.mark.parametrize("section_name", ["unknown__acceptance_criteria", " acceptance_criteria "])
def test_handle_update_groomed_ac_overlap_check_fires_for_recoverable_spellings(
    section_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The AC-overlap gate also fires for forms only _normalize_section_key recovers.

    Tests: operations._handle_update_groomed -> _check_ac_overlap gating,
           parametrized over a legacy ``unknown__`` key and a whitespace-padded
           canonical key — both of which ``_write_groomed_to_reference`` below
           (via ``_normalize_section_key``) routes to ``acceptance_criteria``.
    Why: The gate previously called the narrower ``resolve_section_name``
         directly on the raw ``section_name``, which does not strip whitespace
         and does not recover ``unknown__``-prefixed keys — so content that
         the write path actually stored under ``acceptance_criteria`` silently
         skipped the overlap warning (#3015 Greptile review finding).
    """
    item = BacklogItem(description="- [ ] Looks like an AC checkbox", reference="p1-demo")
    monkeypatch.setattr(ops, "_write_groomed_to_reference", lambda *a, **k: None)
    monkeypatch.setattr(ops, "_reconcile_groomed_item", lambda *a, **k: None)
    out = Output()

    ops._handle_update_groomed(item, "AC content", section_name, "owner/repo", output=out)

    assert any("Acceptance Criteria" in w for w in out.warnings)


def test_handle_batch_groomed_ac_overlap_check_fires_for_recoverable_spelling() -> None:
    """The batch AC-overlap gate fires when the batch keys, not raw input names, contain the AC key.

    Tests: operations._handle_batch_groomed -> _check_ac_overlap gating
    Why: The gate previously re-resolved the raw ``sections`` keys via
         ``resolve_section_name`` instead of checking the already-normalized
         ``written`` keys, so a legacy ``unknown__acceptance_criteria`` input
         key silently skipped the overlap warning even though the batch write
         above it stored the content under ``acceptance_criteria``
         (#3015 Greptile review finding).
    """
    item = BacklogItem(description="- [ ] Looks like an AC checkbox", reference="p1-demo")
    ops.get_config().backend.put_work_item(item)
    out = Output()

    ops._handle_batch_groomed(item, {"unknown__acceptance_criteria": "AC content"}, "owner/repo", output=out)

    assert any("Acceptance Criteria" in w for w in out.warnings)


# ---------------------------------------------------------------------------
# unknown__/canonical fold merges same-id entries via the shared merge rule,
# not a first-seen-wins dedup (post-#2987 Copilot pass finding: the fold in
# normalize_unknown_sections dropped the second copy of a colliding entry id
# outright instead of applying the struck-wins/longer-content-wins rule
# github_sync.merge_item already uses for local/remote reconciliation)
# ---------------------------------------------------------------------------


def test_normalize_unknown_sections_fold_prefers_struck_entry_on_id_collision() -> None:
    """A struck entry wins over an active entry sharing the same id across the two folding keys."""
    active = Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Active copy.")])
    struck = Section(
        entries=[
            Entry(
                id="2026-01-01T00:00:00Z",
                content="Struck copy.",
                struck=True,
                struck_at="2026-01-02T00:00:00Z",
                struck_reason="superseded",
            )
        ]
    )
    sections: dict[str, Section | GroomedData] = {"unknown__story": active, "story": struck}

    folded = rendering.normalize_unknown_sections(sections)

    folded_section = folded["story"]
    assert isinstance(folded_section, Section)
    assert len(folded_section.entries) == 1
    assert folded_section.entries[0].struck is True
    assert folded_section.entries[0].content == "Struck copy."


def test_normalize_unknown_sections_fold_prefers_longer_content_on_id_collision() -> None:
    """The longer-content copy wins over a shorter one sharing the same id and struck state."""
    short = Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Short.")])
    long_ = Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="This is a much longer entry body.")])
    sections: dict[str, Section | GroomedData] = {"unknown__story": short, "story": long_}

    folded = rendering.normalize_unknown_sections(sections)

    folded_section = folded["story"]
    assert isinstance(folded_section, Section)
    assert len(folded_section.entries) == 1
    assert folded_section.entries[0].content == "This is a much longer entry body."


def test_normalize_unknown_sections_fold_prefers_canonical_entry_on_exact_tie() -> None:
    """On an exact tie (same struck state, same content length), the canonical key wins regardless of dict order.

    Tests: rendering.normalize_unknown_sections tie-break determinism
           (post-#3015 Copilot review finding: merge_entries' documented
           tie-break is "local wins" — its first positional argument. The
           fold previously passed (existing.entries, value.entries) where
           `existing` was whichever key the loop reached the ``target`` dict
           slot for *first* in ``sections.items()`` order, not necessarily
           the canonical (non-``unknown__``) key. Two sections dicts that
           differ only in which key comes first then folded to different
           winners for the exact same logical collision, so the canonical
           entry could lose to its own legacy ``unknown__`` copy purely
           because of dict insertion order.
    """
    canonical_entry = Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Canonical copy.")])
    legacy_entry = Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Legacy variant.")])
    assert len(canonical_entry.entries[0].content) == len(legacy_entry.entries[0].content), (
        "fixture bug: contents must be equal length to exercise the tie branch"
    )

    canonical_first = rendering.normalize_unknown_sections({"story": canonical_entry, "unknown__story": legacy_entry})
    legacy_first = rendering.normalize_unknown_sections({"unknown__story": legacy_entry, "story": canonical_entry})

    canonical_first_section = canonical_first["story"]
    legacy_first_section = legacy_first["story"]
    assert isinstance(canonical_first_section, Section)
    assert isinstance(legacy_first_section, Section)
    assert canonical_first_section.entries[0].content == "Canonical copy."
    assert legacy_first_section.entries[0].content == "Canonical copy."


# ---------------------------------------------------------------------------
# SubsectionKey registers the "content" storage shape written by the
# no-section_name groomed-content path (post-#2987 Copilot pass finding: the
# producer-completeness test above only scans two Markdown template/doc
# files, so it never covered the "content" key operations.py writes directly
# in Python — a real, unregistered producer the test suite couldn't see)
# ---------------------------------------------------------------------------


def test_subsection_key_registers_write_groomed_to_item_content_key() -> None:
    """The literal 'content' key operations._write_groomed_to_item writes is a registered SubsectionKey.

    Tests: section_registry.SubsectionKey completeness against the Python
           producer at operations._write_groomed_to_item (the section_name=None
           branch), which is invisible to the Markdown-template-scanning
           test_producer_subsection_name_resolves_through_registry above.
    Why: An unregistered "content" key rendered as an unordered, alphabetically
         -sorted "extra" instead of the canonical registry's ordered position —
         the same accumulation-of-unregistered-names failure mode #2970 exists
         to close, just for a Python producer instead of a Markdown one.
    """
    assert section_registry.SubsectionKey.CONTENT == "content"
    assert section_registry.resolve_subsection_name("content") == "content"
