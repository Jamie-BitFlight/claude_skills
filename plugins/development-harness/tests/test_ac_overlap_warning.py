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
from backlog_core.backend_protocol import get_config, set_config
from backlog_core.backend_types import BacklogConfig as ProviderConfig
from backlog_core.backends.memory_backend import InMemoryBackend
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
    filepath = directory / f"p1-{topic}.md"
    content = _MINIMAL_FRONTMATTER.format(title=title, topic=topic, issue=issue)
    filepath.write_text(content, encoding="utf-8")
    get_config().backend.put_work_item(
        BacklogItem(title=title, description="A test item", reference=str(filepath), issue=issue, added="2026-01-01")
    )
    return filepath


def _backlog_dir() -> Path:
    return models.get_backlog_dir()


# ---------------------------------------------------------------------------
# Autouse fixture: filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    set_config(ProviderConfig(backend=InMemoryBackend()))


# ---------------------------------------------------------------------------
# _check_ac_overlap: detection patterns
# ---------------------------------------------------------------------------


class TestCheckAcOverlapDetection:
    def test_checkbox_unchecked_triggers_warning(self) -> None:
        item = BacklogItem(title="Checkbox Item", description="- [ ] something to verify")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_checkbox_checked_lowercase_x_triggers_warning(self) -> None:
        item = BacklogItem(title="Checkbox Checked", description="- [x] done already")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_checkbox_checked_uppercase_x_triggers_warning(self) -> None:
        item = BacklogItem(title="Checkbox Upper", description="- [X] Done")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_h2_acceptance_header_triggers_warning(self) -> None:
        item = BacklogItem(title="H2 Header Item", description="## Acceptance\nsome criteria here")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_h3_acceptance_criteria_header_triggers_warning(self) -> None:
        item = BacklogItem(title="H3 Header Item", description="### Acceptance Criteria\nsome text")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_acceptance_header_case_insensitive(self) -> None:
        item = BacklogItem(title="Lower Case Header", description="## acceptance\ncriteria text")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_no_warning_when_no_patterns_match(self) -> None:
        item = BacklogItem(title="Clean Description", description="This is a clean description.\nNo AC content here.")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == []

    def test_no_warning_when_description_is_empty(self) -> None:
        item = BacklogItem(title="Empty Body", description="")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == []

    def test_no_warning_when_description_is_absent(self) -> None:
        item = BacklogItem(title="None Body")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == []

    def test_warning_message_matches_spec_exactly(self) -> None:
        item = BacklogItem(title="Msg Check", description="- [ ] some item")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings == [_AC_OVERLAP_MSG]

    def test_only_one_warning_emitted_even_when_both_patterns_match(self) -> None:
        item = BacklogItem(title="Both Patterns", description="## Acceptance\n- [ ] verify behaviour\n")
        out = Output()

        ops._check_ac_overlap(item, out)

        assert out.warnings.count(_AC_OVERLAP_MSG) == 1


# ---------------------------------------------------------------------------
# _handle_update_groomed: call-site wiring
# ---------------------------------------------------------------------------


class TestHandleUpdateGroomedAcWiring:
    def test_warning_fires_when_section_is_acceptance_criteria(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="AC Section Item", topic="ac-section-item")
        item = BacklogItem(title="AC Section Item", reference=str(filepath), added="2026-01-01")

        ops._handle_update_groomed(item, "Some AC content.", "Acceptance Criteria", repo="owner/repo")

        spy.assert_called_once_with(item, mocker.ANY)

    def test_no_warning_for_non_ac_section(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="Plan Section Item", topic="plan-section-item")
        item = BacklogItem(title="Plan Section Item", reference=str(filepath), added="2026-01-01")

        ops._handle_update_groomed(item, "Plan content.", "Plan", repo="owner/repo")

        spy.assert_not_called()

    def test_warning_appears_in_output_when_description_has_checkboxes(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="E2E Warn Item", topic="e2e-warn-item")
        item = BacklogItem(
            title="E2E Warn Item",
            reference=str(filepath),
            added="2026-01-01",
            description="- [ ] informal acceptance criterion",
        )
        out = Output()

        ops._handle_update_groomed(item, "Formal AC here.", "Acceptance Criteria", repo="owner/repo", output=out)

        assert _AC_OVERLAP_MSG in out.warnings

    def test_write_proceeds_when_overlap_warning_fires(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Write Proceeds Item", topic="write-proceeds-item")
        item = BacklogItem(
            title="Write Proceeds Item",
            reference=str(filepath),
            added="2026-01-01",
            description="- [ ] criterion in description",
        )

        ops._handle_update_groomed(item, "Formal criterion here.", "Acceptance Criteria", repo="owner/repo")

        content = get_config().backend.get_work_item(str(filepath)).model_dump_json()
        assert "Formal criterion here." in content


# ---------------------------------------------------------------------------
# _handle_batch_groomed: call-site wiring
# ---------------------------------------------------------------------------


class TestHandleBatchGroomedAcWiring:
    def test_warning_fires_when_acceptance_criteria_in_batch(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="Batch AC Item", topic="batch-ac-item")
        item = BacklogItem(title="Batch AC Item", reference=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(item, {"Acceptance Criteria": "Some ACs.", "Plan": "Plan."}, repo="owner/repo")

        spy.assert_called_once_with(item, mocker.ANY)

    def test_no_warning_when_acceptance_criteria_absent_from_batch(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._check_ac_overlap")
        filepath = _write_item_file(tmp_path, title="No AC Batch Item", topic="no-ac-batch-item")
        item = BacklogItem(title="No AC Batch Item", reference=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Plan text.", "Research": "Research text."}, repo="owner/repo")

        spy.assert_not_called()

    def test_warning_appears_in_output_when_description_has_acceptance_header(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Batch E2E Warn", topic="batch-e2e-warn")
        item = BacklogItem(
            title="Batch E2E Warn",
            reference=str(filepath),
            added="2026-01-01",
            description="## Acceptance\nOld informal criteria.",
        )
        out = Output()

        ops._handle_batch_groomed(
            item, {"Acceptance Criteria": "Formal ACs.", "Plan": "Plan."}, repo="owner/repo", output=out
        )

        assert _AC_OVERLAP_MSG in out.warnings

    def test_batch_write_proceeds_when_overlap_warning_fires(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Batch Proceeds Item", topic="batch-proceeds-item")
        item = BacklogItem(
            title="Batch Proceeds Item",
            reference=str(filepath),
            added="2026-01-01",
            description="- [ ] informal AC in description",
        )

        ops._handle_batch_groomed(
            item, {"Acceptance Criteria": "Formal AC content.", "Plan": "Plan content."}, repo="owner/repo"
        )

        content = get_config().backend.get_work_item(str(filepath)).model_dump_json()
        assert "Formal AC content." in content
        assert "Plan content." in content
