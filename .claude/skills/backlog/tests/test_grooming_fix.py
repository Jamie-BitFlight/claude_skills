"""Tests for the grooming fix (T3) — atomic label transitions and local status updates.

Tests: Grooming workflow in backlog.py after the T3 fix replaced manual
       label removal with apply_github_transition and added local status updates.
How: Mock GitHub API interactions and verify function call arguments for both
     the GitHub transition and local frontmatter update.
Why: The grooming bug (stateless void) was the primary source of items with no
     status label on GitHub. These tests ensure the fix produces atomic transitions.

Covers:
- apply_github_transition called with from_state="needs-grooming", to_state="groomed"
- _write_groomed_to_item_file updates local frontmatter status to "groomed"
- No manual remove_from_labels call occurs during grooming
- Issue has exactly one status:* label after grooming (status:groomed)
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    import pytest

# Ensure backlog scripts are importable
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


class TestGroomingApplyGithubTransition:
    """Verify apply_github_transition is called with correct arguments during grooming.

    Tests: The _write_groomed_to_github function delegates label management
    to apply_github_transition rather than manually manipulating labels.
    """

    def test_apply_github_transition_called_with_groomed_target(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After grooming approval, apply_github_transition is called with to_state="groomed".

        Tests: apply_github_transition receives correct to_state argument.
        How: Mock _try_get_github, _sync_groomed_to_github_issue, repo.get_issue,
             and apply_github_transition. Call _write_groomed_to_github and inspect
             the call arguments.
        Why: The T3 fix replaced manual label removal with apply_github_transition.
             Incorrect to_state would leave the item in a wrong lifecycle position.
        """
        import backlog as backlog_mod
        from state_handler import BacklogState

        # Arrange
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_label_needs_grooming = MagicMock()
        mock_label_needs_grooming.name = "status:needs-grooming"
        mock_issue.labels = [mock_label_needs_grooming]
        mock_repo.get_issue.return_value = mock_issue

        mock_transition = MagicMock()

        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)
        monkeypatch.setattr(backlog_mod, "_sync_groomed_to_github_issue", lambda *_a, **_kw: True)
        monkeypatch.setattr(backlog_mod, "apply_github_transition", mock_transition)

        # Act
        backlog_mod._write_groomed_to_github("#42", "groomed content", None, "test/repo")

        # Assert
        mock_transition.assert_called_once()
        call_args = mock_transition.call_args
        assert call_args[0][0] is mock_repo, "First arg should be the repository object"
        assert call_args[0][1] is mock_issue, "Second arg should be the issue object"
        assert call_args[0][2] == "needs-grooming", "Third arg (current_status) should be 'needs-grooming'"
        assert call_args[0][3] == BacklogState.GROOMED.value, (
            f"Fourth arg (to_state) should be '{BacklogState.GROOMED.value}'"
        )

    def test_apply_github_transition_called_with_correct_from_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """apply_github_transition receives the current label as from_state.

        Tests: from_state is extracted from the issue's existing status:* label.
        How: Set up an issue with status:needs-grooming label and verify the
             extracted value is passed as from_state.
        Why: The state handler validates transitions — wrong from_state causes
             StateTransitionError, leaving the item in limbo.
        """
        import backlog as backlog_mod

        # Arrange
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_label = MagicMock()
        mock_label.name = "status:needs-grooming"
        mock_issue.labels = [mock_label]
        mock_repo.get_issue.return_value = mock_issue

        mock_transition = MagicMock()

        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)
        monkeypatch.setattr(backlog_mod, "_sync_groomed_to_github_issue", lambda *_a, **_kw: True)
        monkeypatch.setattr(backlog_mod, "apply_github_transition", mock_transition)

        # Act
        backlog_mod._write_groomed_to_github("#10", "content", None, "test/repo")

        # Assert
        call_args = mock_transition.call_args[0]
        assert call_args[2] == "needs-grooming", (
            "from_state should be extracted from the issue's status:needs-grooming label"
        )

    def test_apply_github_transition_handles_no_status_label(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When issue has no status:* label, from_state is None.

        Tests: The status extraction logic handles missing labels gracefully.
        How: Set up an issue with no status:* labels and verify None is passed
             as from_state to apply_github_transition.
        Why: Items created before the label system was introduced may lack labels.
        """
        import backlog as backlog_mod

        # Arrange
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_non_status_label = MagicMock()
        mock_non_status_label.name = "priority:P1"
        mock_issue.labels = [mock_non_status_label]
        mock_repo.get_issue.return_value = mock_issue

        mock_transition = MagicMock()

        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)
        monkeypatch.setattr(backlog_mod, "_sync_groomed_to_github_issue", lambda *_a, **_kw: True)
        monkeypatch.setattr(backlog_mod, "apply_github_transition", mock_transition)

        # Act
        backlog_mod._write_groomed_to_github("#5", "content", None, "test/repo")

        # Assert
        call_args = mock_transition.call_args[0]
        assert call_args[2] is None, "from_state should be None when no status:* label exists"


class TestGroomingLocalStatusUpdate:
    """Verify _write_groomed_to_item_file updates local frontmatter status to 'groomed'.

    Tests: The local file update sets status field in frontmatter metadata.
    """

    def test_write_groomed_updates_status_in_frontmatter(self, tmp_path: Path) -> None:
        """After grooming, local frontmatter status field is set to 'groomed'.

        Tests: _write_groomed_to_item_file sets metadata.status to "groomed".
        How: Create a test item file with needs-grooming status, call
             _write_groomed_to_item_file, and read back the frontmatter.
        Why: Without local status update, the item remains in needs-grooming
             locally even though GitHub shows groomed — causing divergence.
        """
        import backlog as backlog_mod

        # Arrange
        item_file = tmp_path / "p1-test-item.md"
        item_file.write_text(
            "---\n"
            "title: Test Item\n"
            "metadata:\n"
            "  status: needs-grooming\n"
            "  priority: P1\n"
            "---\n\n"
            "## Description\n\nTest item body\n",
            encoding="utf-8",
        )

        # Act
        backlog_mod._write_groomed_to_item_file(item_file, "Groomed analysis content")

        # Assert
        content = item_file.read_text(encoding="utf-8")
        assert "status: groomed" in content, "Frontmatter should contain 'status: groomed' after grooming"
        assert "status: needs-grooming" not in content, "Old status 'needs-grooming' should be replaced"

    def test_write_groomed_updates_groomed_date(self, tmp_path: Path) -> None:
        """After grooming, local frontmatter contains a groomed date.

        Tests: _write_groomed_to_item_file sets the groomed date field.
        How: Create a test item file, call _write_groomed_to_item_file,
             and check the frontmatter for a groomed date entry.
        Why: The groomed date tracks when the item was last reviewed.
        """
        import backlog as backlog_mod

        # Arrange
        item_file = tmp_path / "p1-groomed-date.md"
        item_file.write_text(
            "---\ntitle: Date Test\nmetadata:\n  status: needs-grooming\n---\n\n## Description\n\nBody\n",
            encoding="utf-8",
        )

        # Act
        backlog_mod._write_groomed_to_item_file(item_file, "Groomed content")

        # Assert
        content = item_file.read_text(encoding="utf-8")
        assert "groomed:" in content, "Frontmatter should contain a 'groomed' date field"


class TestNoManualLabelRemoval:
    """Verify no manual remove_from_labels call exists in grooming code path.

    Tests: The T3 fix fully removed manual label manipulation from grooming.
    """

    def test_no_remove_from_labels_in_write_groomed_to_github(self) -> None:
        """_write_groomed_to_github does not call remove_from_labels.

        Tests: Source code of _write_groomed_to_github has no remove_from_labels.
        How: Inspect the function source code via AST for any attribute access
             to 'remove_from_labels'.
        Why: Manual label removal was the root cause of the stateless void bug.
             The T3 fix replaced it with apply_github_transition, which atomically
             removes the old label and adds the new one.
        """
        import backlog as backlog_mod

        source = inspect.getsource(backlog_mod._write_groomed_to_github)
        tree = ast.parse(source)

        remove_calls: list[str] = [
            f"line {node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "remove_from_labels"
        ]

        assert remove_calls == [], (
            f"_write_groomed_to_github should not call remove_from_labels, found at: {remove_calls}"
        )

    def test_no_remove_from_labels_in_write_groomed_to_item_file(self) -> None:
        """_write_groomed_to_item_file does not call remove_from_labels.

        Tests: Source code has no remove_from_labels in the local update path.
        How: Inspect the function source via AST.
        Why: Local file updates should never manipulate GitHub labels.
        """
        import backlog as backlog_mod

        source = inspect.getsource(backlog_mod._write_groomed_to_item_file)
        tree = ast.parse(source)

        remove_calls: list[str] = [
            f"line {node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "remove_from_labels"
        ]

        assert remove_calls == [], (
            f"_write_groomed_to_item_file should not call remove_from_labels, found at: {remove_calls}"
        )


class TestGroomingLabelOutcome:
    """Verify that after grooming, the issue ends up with exactly one status label.

    Tests: The apply_github_transition call produces the correct label state.
    """

    def test_apply_github_transition_produces_single_status_label(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After grooming, the issue should have exactly one status:* label.

        Tests: apply_github_transition is the sole mechanism for label changes.
        How: Mock apply_github_transition to simulate its effect (remove old label,
             add new one), then verify the resulting label set.
        Why: Multiple status labels or zero status labels both indicate bugs.
             The atomic transition guarantees exactly one status label.
        """
        import backlog as backlog_mod
        from state_handler import BacklogState

        # Arrange
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        old_label = MagicMock()
        old_label.name = "status:needs-grooming"
        priority_label = MagicMock()
        priority_label.name = "priority:P1"
        mock_issue.labels = [old_label, priority_label]
        mock_repo.get_issue.return_value = mock_issue

        # Track the actual label state after transition
        resulting_labels: list[str] = []

        def fake_transition(repo: object, issue: object, from_state: str | None, to_state: str) -> None:
            """Simulate apply_github_transition behavior."""
            # Remove old status label, add new one (what the real function does)
            labels_after = [lbl for lbl in mock_issue.labels if not lbl.name.startswith("status:")]
            new_label = MagicMock()
            new_label.name = f"status:{to_state}"
            labels_after.append(new_label)
            mock_issue.labels = labels_after
            resulting_labels.extend(lbl.name for lbl in labels_after if lbl.name.startswith("status:"))

        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)
        monkeypatch.setattr(backlog_mod, "_sync_groomed_to_github_issue", lambda *_a, **_kw: True)
        monkeypatch.setattr(backlog_mod, "apply_github_transition", fake_transition)

        # Act
        backlog_mod._write_groomed_to_github("#42", "content", None, "test/repo")

        # Assert
        assert len(resulting_labels) == 1, (
            f"Expected exactly 1 status label, got {len(resulting_labels)}: {resulting_labels}"
        )
        assert resulting_labels[0] == f"status:{BacklogState.GROOMED.value}", (
            f"Expected status:groomed, got {resulting_labels[0]}"
        )
