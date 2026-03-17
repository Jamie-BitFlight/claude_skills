"""Tests for state_handler helper functions — is_terminal_state and find_valid_path.

Tests: Pure helper functions added by T1 for the backlog state reconciliation feature.
How: Direct calls against the VALID_TRANSITIONS DAG with known expected outcomes.
Why: These functions underpin reconciliation logic (T2) — correctness is critical.

Covers:
- is_terminal_state: terminal detection for done, resolved, closed; non-terminal rejection
- find_valid_path: single-hop, multi-hop, unreachable, identity, and invalid state handling
"""

from __future__ import annotations

import sys
from pathlib import Path

# state_handler.py lives in .claude/skills/backlog/scripts/ which is not a package.
# Add the scripts directory to sys.path so the module is directly importable.
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import pytest

from state_handler import VALID_TRANSITIONS, BacklogState, find_valid_path, is_terminal_state

# ---------------------------------------------------------------------------
# is_terminal_state
# ---------------------------------------------------------------------------


class TestIsTerminalState:
    """Verify is_terminal_state identifies done/resolved/closed as terminal.

    The architecture spec Section 4.3 defines terminal states as those
    representing final outcomes — items excluded from default list views.
    """

    @pytest.mark.parametrize("state", ["done", "resolved", "closed"])
    def test_terminal_states_return_true(self, state: str) -> None:
        """Terminal states (done, resolved, closed) return True.

        Tests: is_terminal_state recognizes all three terminal states.
        How: Call with each terminal state string.
        Why: Reconciliation filtering depends on accurate terminal detection.
        """
        assert is_terminal_state(state) is True

    @pytest.mark.parametrize("state", ["needs-grooming", "groomed", "blocked", "in-milestone", "in-progress"])
    def test_non_terminal_states_return_false(self, state: str) -> None:
        """Non-terminal states return False.

        Tests: is_terminal_state rejects all active lifecycle states.
        How: Call with each non-terminal state string.
        Why: Active items must not be filtered from default views.
        """
        assert is_terminal_state(state) is False

    def test_unknown_state_returns_false(self) -> None:
        """Unknown state strings return False rather than raising.

        Tests: is_terminal_state handles invalid input gracefully.
        How: Call with a string that is not a valid BacklogState value.
        Why: Reconciliation may encounter unexpected state values from GitHub.
        """
        assert is_terminal_state("nonexistent-state") is False

    def test_empty_string_returns_false(self) -> None:
        """Empty string returns False.

        Tests: is_terminal_state handles edge case of empty input.
        How: Call with empty string.
        Why: Missing status fields may produce empty strings.
        """
        assert is_terminal_state("") is False


# ---------------------------------------------------------------------------
# find_valid_path
# ---------------------------------------------------------------------------


class TestFindValidPathIdentity:
    """Verify find_valid_path identity case — same start and end state."""

    @pytest.mark.parametrize("state", [s.value for s in BacklogState])
    def test_identity_returns_single_element_list(self, state: str) -> None:
        """Same source and target returns [state] for all valid states.

        Tests: find_valid_path identity case across all 8 states.
        How: Call with from_state == to_state for each BacklogState value.
        Why: Identity is a base case that reconciliation uses for no-change detection.
        """
        result = find_valid_path(state, state)
        assert result == [state]


class TestFindValidPathSingleHop:
    """Verify find_valid_path returns direct paths for adjacent states."""

    def test_needs_grooming_to_groomed(self) -> None:
        """Direct transition needs-grooming -> groomed returns two-element path.

        Tests: find_valid_path single-hop reachability.
        How: Call with adjacent states in the DAG.
        Why: Single-hop paths are the most common reconciliation case.
        """
        result = find_valid_path("needs-grooming", "groomed")
        assert result is not None
        assert result == ["needs-grooming", "groomed"]

    def test_groomed_to_in_milestone(self) -> None:
        """Direct transition groomed -> in-milestone returns two-element path.

        Tests: find_valid_path for groomed to in-milestone hop.
        How: Call with groomed and in-milestone.
        Why: Validates DAG adjacency for milestone assignment flow.
        """
        result = find_valid_path("groomed", "in-milestone")
        assert result is not None
        assert result == ["groomed", "in-milestone"]

    def test_in_progress_to_done(self) -> None:
        """Direct transition in-progress -> done returns two-element path.

        Tests: find_valid_path for completion transition.
        How: Call with in-progress and done.
        Why: Validates the work completion path in the DAG.
        """
        result = find_valid_path("in-progress", "done")
        assert result is not None
        assert result == ["in-progress", "done"]

    def test_done_to_closed(self) -> None:
        """Direct transition done -> closed returns two-element path.

        Tests: find_valid_path for terminal closure.
        How: Call with done and closed.
        Why: Validates the archival transition path.
        """
        result = find_valid_path("done", "closed")
        assert result is not None
        assert result == ["done", "closed"]


class TestFindValidPathMultiHop:
    """Verify find_valid_path returns multi-hop paths through the DAG."""

    def test_needs_grooming_to_in_progress(self) -> None:
        """Multi-hop path needs-grooming -> in-progress traverses 4+ states.

        Tests: find_valid_path BFS finds multi-hop paths.
        How: Call with non-adjacent states that require traversing intermediate nodes.
        Why: Reconciliation must detect DAG-valid divergences spanning multiple hops.
        """
        result = find_valid_path("needs-grooming", "in-progress")
        assert result is not None
        assert len(result) >= 4
        assert result[0] == "needs-grooming"
        assert result[-1] == "in-progress"
        # Verify each step is a valid transition
        for i in range(len(result) - 1):
            from_s = BacklogState(result[i])
            to_s = BacklogState(result[i + 1])
            assert to_s in VALID_TRANSITIONS[from_s], f"Invalid step in path: {result[i]} -> {result[i + 1]}"

    def test_needs_grooming_to_closed(self) -> None:
        """Multi-hop path needs-grooming -> closed traverses multiple states.

        Tests: find_valid_path can reach terminal states from the beginning.
        How: Call with the initial and final states of the lifecycle.
        Why: Full lifecycle traversal validates BFS correctness across the entire DAG.
        """
        result = find_valid_path("needs-grooming", "closed")
        assert result is not None
        assert result[0] == "needs-grooming"
        assert result[-1] == "closed"
        assert len(result) >= 3  # At minimum: needs-grooming -> resolved -> closed


class TestFindValidPathUnreachable:
    """Verify find_valid_path returns None for unreachable state pairs."""

    def test_done_to_needs_grooming_returns_none(self) -> None:
        """Backward path done -> needs-grooming is unreachable in the DAG.

        Tests: find_valid_path correctly identifies unreachable backward transitions.
        How: Call with terminal state as source and initial state as target.
        Why: Reconciliation must distinguish valid auto-corrections from invalid divergences.
        """
        assert find_valid_path("done", "needs-grooming") is None

    def test_closed_to_any_returns_none(self) -> None:
        """Closed has no outgoing transitions — cannot reach any other state.

        Tests: find_valid_path returns None from the truly terminal state.
        How: Call with closed as source and every non-closed state as target.
        Why: Closed is the only state with an empty transition set in the DAG.
        """
        for state in BacklogState:
            if state != BacklogState.CLOSED:
                assert find_valid_path("closed", state.value) is None, f"Expected None for closed -> {state.value}"

    def test_in_progress_to_groomed_is_reachable_via_blocked(self) -> None:
        """in-progress CAN reach groomed via blocked -> needs-grooming -> groomed.

        Tests: find_valid_path correctly finds backward paths through blocked state.
        How: Call with in-progress to groomed; verify the path goes through blocked.
        Why: The DAG allows regression through the blocked state — this is intentional
             so blocked items can be re-groomed after unblocking.
        """
        result = find_valid_path("in-progress", "groomed")
        assert result is not None
        assert result[0] == "in-progress"
        assert result[-1] == "groomed"
        assert "blocked" in result

    def test_done_to_in_progress_returns_none(self) -> None:
        """done cannot reach in-progress — no path exists from terminal states back.

        Tests: find_valid_path rejects backward transitions from terminal states.
        How: Call with done to in-progress.
        Why: Terminal states should not allow regression to active states.
        """
        assert find_valid_path("done", "in-progress") is None


class TestFindValidPathInvalidInput:
    """Verify find_valid_path handles invalid state strings gracefully."""

    def test_unknown_from_state_returns_none(self) -> None:
        """Unknown source state returns None.

        Tests: find_valid_path rejects invalid from_state input.
        How: Call with a non-existent state as source.
        Why: Reconciliation may encounter unexpected state values from GitHub.
        """
        assert find_valid_path("nonexistent", "groomed") is None

    def test_unknown_to_state_returns_none(self) -> None:
        """Unknown target state returns None.

        Tests: find_valid_path rejects invalid to_state input.
        How: Call with a non-existent state as target.
        Why: Defensive handling prevents crashes on corrupted data.
        """
        assert find_valid_path("groomed", "nonexistent") is None

    def test_both_unknown_returns_none(self) -> None:
        """Both states unknown returns None.

        Tests: find_valid_path rejects doubly invalid input.
        How: Call with two non-existent states.
        Why: Edge case where both local and GitHub states are corrupted.
        """
        assert find_valid_path("foo", "bar") is None
