"""Tests for _check_ac_overlap and its wiring in both groomed write paths.

Covers:
- Both regex patterns (checkbox and Acceptance header)
- Warning message matches the architecture spec exactly
- Both call sites: _handle_update_groomed and _handle_batch_groomed
- No-match (no warning) paths
- Advisory-only: write proceeds even when patterns match
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlog_core.models as models
import backlog_core.operations as ops
import pytest
from backlog_core.models import BacklogConfig, BacklogItem, Output

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: {title}
description: A test item
metadata:
  priority: P1
  status: open
  source: test
  added: '2026-01-01'
  type: Feature
  topic: {topic}
  issue: '{issue}'
---
"""

_AC_OVERLAP_MSG = (
    "Description contains AC-like content (checkboxes or Acceptance header found). "
    "Verify the Acceptance Criteria section does not duplicate the description."
)


def _write_item_file(
    directory: Path, *, title: str = "AC Overlap Item", topic: str = "ac-overlap-item", issue: str = ""
) -> Path:
    """Write a minimal per-item file and return its path."""
    filepath = directory / f"p1-{topic}.md"
    content = _MINIMAL_FRONTMATTER.format(title=title, topic=topic, issue=issue)
    filepath.write_text(content, encoding="utf-8")
    return filepath


def _backlog_dir() -> Path:
    return models.get_backlog_dir()


# ---------------------------------------------------------------------------
# Autouse fixture: filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect BACKLOG_DIR to tmp_path for test isolation."""
    import dh_paths

    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))

    fake_project_root = tmp_path / "project"
    fake_project_root.mkdir(parents=True, exist_ok=True)

    fake_dir = dh_paths.backlog_dir(project_root=fake_project_root)
    fake_dir.mkdir(parents=True, exist_ok=True)

    existing = models._config
    monkeypatch.setattr(
        models,
        "_config",
        BacklogConfig(
            repo_root=fake_project_root,
            backlog_dir=fake_dir,
            default_repo=existing.default_repo if existing is not None else "",
        ),
    )


# ---------------------------------------------------------------------------
# _check_ac_overlap: detection patterns
# ---------------------------------------------------------------------------


class TestCheckAcOverlapDetection:
    """_check_ac_overlap detects the two AC-like patterns in item.description."""

    def test_checkbox_unchecked_triggers_warning(self) -> None:
        """Verify an unchecked markdown checkbox triggers the advisory warning.

        Tests: _check_ac_overlap checkbox regex with space.
        How: Set description containing '- [ ] some task'; call; inspect warnings.
        Why: Unchecked boxes indicate informal AC embedded in the description.
        """
        item = BacklogItem(title="Checkbox Item", description="- [ ] something to verify")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_checkbox_checked_lowercase_x_triggers_warning(self) -> None:
        """Verify a checked checkbox with lowercase 'x' triggers the warning.

        Tests: _check_ac_overlap checkbox regex with 'x'.
        How: Set description containing '- [x] done'; call; inspect warnings.
        Why: Checked boxes are equally indicative of informal AC.
        """
        item = BacklogItem(title="Checkbox Checked", description="- [x] done already")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_checkbox_checked_uppercase_x_triggers_warning(self) -> None:
        """Verify a checked checkbox with uppercase 'X' triggers the warning.

        Tests: _check_ac_overlap checkbox regex with 'X'.
        How: Set description containing '- [X] Done'; call; inspect warnings.
        Why: Character class includes both 'x' and 'X'; must not miss uppercase.
        """
        item = BacklogItem(title="Checkbox Upper", description="- [X] Done")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_h2_acceptance_header_triggers_warning(self) -> None:
        """Verify an H2 Acceptance header triggers the warning.

        Tests: _check_ac_overlap H2 Acceptance header regex.
        How: Set description containing '## Acceptance'; call; inspect warnings.
        Why: H2 Acceptance is the informal header pattern to detect.
        """
        item = BacklogItem(title="H2 Header Item", description="## Acceptance\nsome criteria here")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_h3_acceptance_criteria_header_triggers_warning(self) -> None:
        """Verify an H3 Acceptance Criteria header triggers the warning.

        Tests: _check_ac_overlap H3 Acceptance Criteria header regex.
        How: Set description containing '### Acceptance Criteria'; call; inspect warnings.
        Why: H3 is the formal groomed section name — duplicate in description is a conflict.
        """
        item = BacklogItem(title="H3 Header Item", description="### Acceptance Criteria\nsome text")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_acceptance_header_case_insensitive(self) -> None:
        """Verify the Acceptance header pattern matches case-insensitively.

        Tests: _check_ac_overlap re.IGNORECASE on header regex.
        How: Set description containing '## acceptance' (lowercase); inspect warnings.
        Why: Real items may use any capitalisation — must not miss them.
        """
        item = BacklogItem(title="Lower Case Header", description="## acceptance\ncriteria text")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_no_warning_when_no_patterns_match(self) -> None:
        """Verify no warning is emitted when description has no AC-like content.

        Tests: _check_ac_overlap negative path.
        How: Set description with plain prose and no checkboxes or Acceptance headers.
        Why: The warning must not fire on clean descriptions.
        """
        item = BacklogItem(title="Clean Description", description="This is a clean description.\nNo AC content here.")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == []

    def test_no_warning_when_description_is_empty(self) -> None:
        """Verify no warning is emitted when description is empty.

        Tests: _check_ac_overlap empty description guard.
        How: Set description to empty string; call; inspect warnings.
        Why: Empty descriptions are valid; must not raise or warn.
        """
        item = BacklogItem(title="Empty Body", description="")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == []

    def test_no_warning_when_description_is_absent(self) -> None:
        """Verify no warning is emitted when description is absent.

        Tests: _check_ac_overlap absent description guard.
        How: Construct BacklogItem without description; call; inspect warnings.
        Why: Items without descriptions are valid; must not raise or warn.
        """
        item = BacklogItem(title="None Body")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == []

    def test_warning_message_matches_spec_exactly(self) -> None:
        """Verify the warning message matches the architecture spec character-for-character.

        Tests: _check_ac_overlap exact warning text.
        How: Trigger warning with checkbox; compare warning string to spec literal.
        Why: MCP callers and groomer agents rely on stable warning text for detection.
        """
        item = BacklogItem(title="Msg Check", description="- [ ] some item")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == [_AC_OVERLAP_MSG]

    def test_only_one_warning_emitted_even_when_both_patterns_match(self) -> None:
        """Verify only one warning is emitted when both patterns are present.

        Tests: _check_ac_overlap single-warn deduplication.
        How: description contains both checkbox and Acceptance header; inspect warning count.
        Why: Duplicate warnings pollute the output; one advisory is sufficient.
        """
        item = BacklogItem(title="Both Patterns", description="## Acceptance\n- [ ] verify behaviour\n")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings.count(_AC_OVERLAP_MSG) == 1


# ---------------------------------------------------------------------------
# _handle_update_groomed: call-site wiring
# ---------------------------------------------------------------------------


class TestHandleUpdateGroomedAcWiring:
    """_handle_update_groomed calls _check_ac_overlap only for Acceptance Criteria section."""

    def test_warning_fires_when_section_is_acceptance_criteria(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify _check_ac_overlap is called when section_name == 'Acceptance Criteria'.

        Tests: _handle_update_groomed AC call site.
        How: Spy on _check_ac_overlap; call with section_name='Acceptance Criteria'.
        Why: The call site must be wired — spy confirms delegation, not just warning output.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="AC Section Item", topic="ac-section-item")
        item = BacklogItem(title="AC Section Item", file_path=str(filepath), added="2026-01-01")

        ops._handle_update_groomed(item, "Some AC content.", "Acceptance Criteria", repo="owner/repo")

        spy.assert_called_once_with(item, mocker.ANY)

    def test_no_warning_for_non_ac_section(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify _check_ac_overlap is NOT called for a non-AC section.

        Tests: _handle_update_groomed non-AC section skip.
        How: Spy on _check_ac_overlap; call with section_name='Plan'; assert not called.
        Why: The overlap check must be scoped to AC sections only.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="Plan Section Item", topic="plan-section-item")
        item = BacklogItem(title="Plan Section Item", file_path=str(filepath), added="2026-01-01")

        ops._handle_update_groomed(item, "Plan content.", "Plan", repo="owner/repo")

        spy.assert_not_called()

    def test_warning_appears_in_output_when_description_has_checkboxes(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Verify output.warnings contains AC overlap message end-to-end via _handle_update_groomed.

        Tests: _handle_update_groomed AC warning propagation to Output.
        How: Item with checkbox in description; pass explicit Output; verify warnings.
        Why: End-to-end confirmation that the advisory reaches the caller's Output object.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="E2E Warn Item", topic="e2e-warn-item")
        item = BacklogItem(
            title="E2E Warn Item",
            file_path=str(filepath),
            added="2026-01-01",
            description="- [ ] informal acceptance criterion",
        )
        out = Output()

        ops._handle_update_groomed(item, "Formal AC here.", "Acceptance Criteria", repo="owner/repo", output=out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_write_proceeds_when_overlap_warning_fires(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify the local file write still completes when an overlap warning is emitted.

        Tests: _handle_update_groomed advisory-only guarantee.
        How: Item body has checkboxes; call with section 'Acceptance Criteria'; read file.
        Why: The warning must be advisory — a raised exception would block all AC grooming.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Write Proceeds Item", topic="write-proceeds-item")
        item = BacklogItem(
            title="Write Proceeds Item",
            file_path=str(filepath),
            added="2026-01-01",
            description="- [ ] criterion in description",
        )

        ops._handle_update_groomed(item, "Formal criterion here.", "Acceptance Criteria", repo="owner/repo")

        # save_item auto-migrates .md -> .yaml; the content is now at the .yaml path.
        written_path = filepath.with_suffix(".yaml")
        content = written_path.read_text(encoding="utf-8")
        assert "Formal criterion here." in content


# ---------------------------------------------------------------------------
# _handle_batch_groomed: call-site wiring
# ---------------------------------------------------------------------------


class TestHandleBatchGroomedAcWiring:
    """_handle_batch_groomed calls _check_ac_overlap only when 'Acceptance Criteria' in sections."""

    def test_warning_fires_when_acceptance_criteria_in_batch(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify _check_ac_overlap is called when 'Acceptance Criteria' is a batch section.

        Tests: _handle_batch_groomed AC call site.
        How: Spy on _check_ac_overlap; call with sections containing 'Acceptance Criteria'.
        Why: The call site must be wired — spy confirms delegation.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="Batch AC Item", topic="batch-ac-item")
        item = BacklogItem(title="Batch AC Item", file_path=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(item, {"Acceptance Criteria": "Some ACs.", "Plan": "Plan."}, repo="owner/repo")

        spy.assert_called_once_with(item, mocker.ANY)

    def test_no_warning_when_acceptance_criteria_absent_from_batch(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify _check_ac_overlap is NOT called when batch has no 'Acceptance Criteria'.

        Tests: _handle_batch_groomed non-AC batch skip.
        How: Spy on _check_ac_overlap; batch has only 'Plan' and 'Research'; assert not called.
        Why: The overlap check must be scoped to batches that include AC.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="No AC Batch Item", topic="no-ac-batch-item")
        item = BacklogItem(title="No AC Batch Item", file_path=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Plan text.", "Research": "Research text."}, repo="owner/repo")

        spy.assert_not_called()

    def test_warning_appears_in_output_when_description_has_acceptance_header(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Verify output.warnings contains AC overlap message end-to-end via _handle_batch_groomed.

        Tests: _handle_batch_groomed AC warning propagation to Output.
        How: Item with Acceptance header in description; batch includes 'Acceptance Criteria'; verify warnings.
        Why: End-to-end confirmation that the advisory reaches the caller's Output object.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Batch E2E Warn", topic="batch-e2e-warn")
        item = BacklogItem(
            title="Batch E2E Warn",
            file_path=str(filepath),
            added="2026-01-01",
            description="## Acceptance\nOld informal criteria.",
        )
        out = Output()

        ops._handle_batch_groomed(
            item, {"Acceptance Criteria": "Formal ACs.", "Plan": "Plan."}, repo="owner/repo", output=out
        )

        assert _AC_OVERLAP_MSG in out.warnings

    def test_batch_write_proceeds_when_overlap_warning_fires(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify the batch write still completes when an overlap warning is emitted.

        Tests: _handle_batch_groomed advisory-only guarantee.
        How: Item body has checkboxes; batch contains 'Acceptance Criteria'; read file after.
        Why: The warning must not abort the batch — grooming must complete.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Batch Proceeds Item", topic="batch-proceeds-item")
        item = BacklogItem(
            title="Batch Proceeds Item",
            file_path=str(filepath),
            added="2026-01-01",
            description="- [ ] informal AC in description",
        )

        ops._handle_batch_groomed(
            item, {"Acceptance Criteria": "Formal AC content.", "Plan": "Plan content."}, repo="owner/repo"
        )

        # save_item auto-migrates .md -> .yaml; the content is now at the .yaml path.
        written_path = filepath.with_suffix(".yaml")
        content = written_path.read_text(encoding="utf-8")
        assert "Formal AC content." in content
        assert "Plan content." in content
