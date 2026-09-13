"""Tests for the ``repo_path_unresolved`` check in validate_research.py.

Covers ``_check_repo_path_citations`` and its supporting scope functions
(``_is_analysis_file``, ``collect_analysis_files``, ``validate_analysis_file``) --
the automated proxy for entry-review-rubric.md's Gate 4 "Path exists" step, scoped to
``research/insights/`` and ``research/utilization/`` gap-analysis files only. See
validation-rules.md's "Repository Path Citations" section for the scoping rationale
and the measured false-positive rate this test suite guards against regressing.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).parents[2]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_validate_research() -> Any:
    """Load validate_research.py by path so its module-level repo scan runs against this repo.

    ``importlib.util`` is required (mirrors ``_load_backlink_lib`` in the script itself)
    because the script is a PEP 723 sibling, not an installed package.
    """
    spec = importlib.util.spec_from_file_location("validate_research", _VALIDATE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vr = _load_validate_research()


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        msg = "uv binary not found on PATH -- cannot run CLI tests"
        raise RuntimeError(msg)
    return found


def _run_json(args: list[str]) -> dict[str, Any]:
    """Run ``validate_research.py main --json`` and parse the result."""
    cmd = [_uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "main", *args, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# _check_repo_path_citations: unit-level regex/logic behavior
# ---------------------------------------------------------------------------


class TestExistingStateGating:
    """Only lines carrying an existing-state assertion are scanned at all."""

    def test_bare_path_mention_without_marker_is_ignored(self) -> None:
        """A path with no 'already/local system/caller' framing produces no issue.

        This is the guard that keeps aspirational and descriptive mentions ("could add
        a skill at plugins/foo/skills/bar/") out of scope entirely.
        """
        lines = ["Integration point: `plugins/foo/skills/definitely-fake-skill/`"]
        assert vr._check_repo_path_citations(lines) == []

    def test_already_covered_with_missing_path_is_flagged(self) -> None:
        """'Already covered' framing plus a nonexistent path IS flagged."""
        lines = ["Already covered: see `.claude/skills/definitely-fake-skill/SKILL.md`"]
        issues = vr._check_repo_path_citations(lines)
        assert len(issues) == 1
        assert issues[0]["check"] == "repo_path_unresolved"
        assert issues[0]["severity"] == "warning"

    def test_local_system_field_with_real_path_is_not_flagged(self) -> None:
        """'**Local system**:' framing citing a path that genuinely exists is clean."""
        lines = ["**Local system**: `.claude/skills/research-curator/SKILL.md`"]
        assert vr._check_repo_path_citations(lines) == []

    def test_caller_field_with_missing_path_is_flagged(self) -> None:
        """'**Caller**:' framing citing a nonexistent path is flagged."""
        lines = ["**Caller**: `.claude/skills/nonexistent-thing/SKILL.md`"]
        issues = vr._check_repo_path_citations(lines)
        assert len(issues) == 1


class TestNegationAndAspirationalGuard:
    """A missing path is not a defect when the line itself says so, or proposes it."""

    def test_explicit_absence_statement_is_not_flagged(self) -> None:
        """'X does not occur' framing is a correct absence statement, not a defect.

        Regression case: research/insights/2026-05-04-waza-improvements.md pairs
        'already covered' with an explicit 'does not occur' for the same fictional path
        in the same sentence -- flagging it would penalize an entry for correctly stating
        an absence per entry-quality-standards.md Rule 3.
        """
        lines = [
            (
                "Already covered by the existing rule; the `.claude/skills/source-root/SKILL.md` "
                "variant does not occur in this repo."
            )
        ]
        assert vr._check_repo_path_citations(lines) == []

    def test_to_be_created_is_not_flagged(self) -> None:
        """A path explicitly marked '(to be created)' is a proposal, not a false claim."""
        lines = ["**Caller**: `.claude/hooks/session-start.js` (to be created)"]
        assert vr._check_repo_path_citations(lines) == []

    def test_new_skill_proposal_is_not_flagged(self) -> None:
        """'New skill' framing around a not-yet-existing path is a proposal, not a defect."""
        lines = ["Already covered elsewhere; new skill needed at `plugins/foo/skills/bar/`."]
        assert vr._check_repo_path_citations(lines) == []


class TestPathResolution:
    """Path candidates are resolved against the real repository tree."""

    def test_real_top_level_path_resolves(self) -> None:
        """A citation to this file's own real path does not get flagged."""
        lines = [f"Already covered: `{_VALIDATE_SCRIPT.relative_to(_REPO_ROOT)}`"]
        assert vr._check_repo_path_citations(lines) == []

    def test_glob_wildcard_with_a_match_resolves(self) -> None:
        """A `*` wildcard path resolves when the glob matches at least one real path."""
        lines = ["Already covered: `plugins/development-harness/skills/code-review-*/`"]
        assert vr._check_repo_path_citations(lines) == []

    def test_glob_wildcard_with_no_match_is_flagged(self) -> None:
        """A `*` wildcard path is flagged when the glob matches nothing."""
        lines = ["Already covered: `plugins/development-harness/skills/definitely-fake-*/`"]
        issues = vr._check_repo_path_citations(lines)
        assert len(issues) == 1

    def test_dotted_prefix_path_resolves(self) -> None:
        """A ``./``-prefixed path resolves the same as its bare equivalent."""
        lines = [f"Already covered: `./{_VALIDATE_SCRIPT.relative_to(_REPO_ROOT)}`"]
        assert vr._check_repo_path_citations(lines) == []

    def test_trailing_sentence_punctuation_is_stripped(self) -> None:
        """A trailing period from sentence punctuation is not treated as part of the path."""
        lines = [f"Already covered by `{_VALIDATE_SCRIPT.relative_to(_REPO_ROOT)}`."]
        assert vr._check_repo_path_citations(lines) == []


class TestBareSkillCitation:
    """Backtick-quoted `{slug}/SKILL.md` and `{slug} SKILL.md` shorthand citations."""

    def test_real_skill_slug_resolves(self) -> None:
        """A real skill directory name is not flagged."""
        lines = ["Already covered by `research-curator/SKILL.md`."]
        assert vr._check_repo_path_citations(lines) == []

    def test_fake_skill_slug_is_flagged(self) -> None:
        """A skill slug with no matching directory anywhere in the repo is flagged."""
        lines = ["Already covered: `swarm-operations SKILL.md` handles this."]
        issues = vr._check_repo_path_citations(lines)
        assert len(issues) == 1
        assert "swarm-operations" in issues[0]["message"]

    def test_unquoted_skill_mention_is_not_matched(self) -> None:
        """Without backtick quoting, prose like 'the X SKILL.md approach' is not a citation.

        This is a deliberate precision/recall tradeoff: unquoted prose produced false
        positives on ordinary adjectives during corpus measurement (e.g. 'the
        self-contained SKILL.md approach'). Requiring backticks trades recall on some
        genuine bare mentions for zero false positives on descriptive prose.
        """
        lines = ["Already covered: the self-contained SKILL.md approach handles this."]
        assert vr._check_repo_path_citations(lines) == []


# ---------------------------------------------------------------------------
# Scope: analysis files (insights/, utilization/) vs entries vs design-notes
# ---------------------------------------------------------------------------


class TestAnalysisFileScope:
    """``_is_analysis_file`` / ``collect_analysis_files`` scoping."""

    def test_insights_file_is_analysis_file(self, tmp_path: Path) -> None:
        f = tmp_path / "research" / "insights" / "2026-01-01-foo-improvements.md"
        f.parent.mkdir(parents=True)
        f.write_text("content\n", encoding="utf-8")
        assert vr._is_analysis_file(f) is True

    def test_utilization_file_is_analysis_file(self, tmp_path: Path) -> None:
        f = tmp_path / "research" / "utilization" / "2026-01-01-foo-utilization.md"
        f.parent.mkdir(parents=True)
        f.write_text("content\n", encoding="utf-8")
        assert vr._is_analysis_file(f) is True

    def test_entry_file_is_not_analysis_file(self, tmp_path: Path) -> None:
        f = tmp_path / "research" / "agent-frameworks" / "foo.md"
        f.parent.mkdir(parents=True)
        f.write_text("content\n", encoding="utf-8")
        assert vr._is_analysis_file(f) is False

    def test_design_notes_file_is_not_analysis_file(self, tmp_path: Path) -> None:
        """design-notes/ is out of scope for this check (see Gate 4's own scope)."""
        f = tmp_path / "research" / "design-notes" / "2026-01-01-status.md"
        f.parent.mkdir(parents=True)
        f.write_text("content\n", encoding="utf-8")
        assert vr._is_analysis_file(f) is False


class TestValidateAnalysisFile:
    """``validate_analysis_file`` runs only the repo-path check, not entry structure checks."""

    def test_analysis_file_with_missing_section_is_not_flagged_for_structure(self, tmp_path: Path) -> None:
        """An analysis file missing every entry-template section is still 'pass'.

        Analysis files do not follow entry-template.md's structure by design -- flagging
        section_completeness on them would be a false structural defect.
        """
        vault = tmp_path / "vault"
        f = vault / "insights" / "2026-01-01-foo-improvements.md"
        f.parent.mkdir(parents=True)
        f.write_text("No sections here at all, just prose.\n", encoding="utf-8")

        result = vr.validate_analysis_file(f, vault)
        assert result["format"] == "analysis"
        assert result["status"] == "pass"
        assert result["issues"] == []

    def test_analysis_file_with_unresolved_citation_is_reported(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        f = vault / "insights" / "2026-01-01-foo-improvements.md"
        f.parent.mkdir(parents=True)
        f.write_text("Already covered: `.claude/skills/definitely-fake-skill/SKILL.md`\n", encoding="utf-8")

        result = vr.validate_analysis_file(f, vault)
        assert len(result["issues"]) == 1
        assert result["issues"][0]["check"] == "repo_path_unresolved"
        # repo_path_unresolved is warning-severity, so status stays "pass" (only errors fail).
        assert result["status"] == "pass"


# ---------------------------------------------------------------------------
# CLI-level: main scans insights/utilization files without misclassifying them as entries
# ---------------------------------------------------------------------------


class TestCliIntegration:
    """``main`` picks up analysis files alongside entries when scanning a vault."""

    def test_insights_file_appears_in_json_output_as_analysis_format(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        insights_file = vault / "insights" / "2026-01-01-foo-improvements.md"
        insights_file.parent.mkdir(parents=True)
        insights_file.write_text("Already covered: `.claude/skills/definitely-fake-skill/SKILL.md`\n", encoding="utf-8")

        result = _run_json([str(vault)])
        matching = [e for e in result["entries"] if e["file"] == "insights/2026-01-01-foo-improvements.md"]
        assert len(matching) == 1
        assert matching[0]["format"] == "analysis"
        assert any(i["check"] == "repo_path_unresolved" for i in matching[0]["issues"])

    def test_insights_file_never_triggers_entry_structural_checks_via_cli(self, tmp_path: Path) -> None:
        """An insights file with no entry-template sections at all still passes via the CLI."""
        vault = tmp_path / "vault"
        insights_file = vault / "insights" / "2026-01-01-bar-improvements.md"
        insights_file.parent.mkdir(parents=True)
        insights_file.write_text("Just prose, no template sections.\n", encoding="utf-8")

        result = _run_json([str(vault)])
        matching = [e for e in result["entries"] if e["file"] == "insights/2026-01-01-bar-improvements.md"]
        assert len(matching) == 1
        assert matching[0]["status"] == "pass"
        assert matching[0]["issues"] == []


# ---------------------------------------------------------------------------
# Real-corpus baseline (informational, non-asserting -- mirrors
# TestRealVaultBaseline in test_validator_cli.py)
# ---------------------------------------------------------------------------


class TestRealCorpusBaseline:
    """Informational: run the check against the real corpus and report the count.

    Does NOT assert a specific count -- the corpus changes as entries are refreshed or
    fixed, and hard-coding a count here would make this test a change-detector on
    unrelated content rather than a check of this feature's behavior.
    """

    def test_repo_path_unresolved_runs_against_real_corpus(self) -> None:
        real_research = _REPO_ROOT / "research"
        if not real_research.exists():
            pytest.skip("Real research vault not present")

        result = _run_json([str(real_research)])
        hits = [(e["file"], i) for e in result["entries"] for i in e["issues"] if i["check"] == "repo_path_unresolved"]
        files_with_hits = {f for f, _ in hits}
        print(f"\nReal corpus repo_path_unresolved: {len(hits)} issues across {len(files_with_hits)} files")

        # Every hit must come from an analysis-format file (insights/ or utilization/),
        # never from an entry -- this is the scope boundary the whole design rests on.
        analysis_files = {e["file"] for e in result["entries"] if e["format"] == "analysis"}
        assert files_with_hits <= analysis_files
