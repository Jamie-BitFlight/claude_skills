"""Backlog item state machine — transition validation and atomic GitHub label updates.

Implements the 8-state lifecycle defined in
.claude/skills/backlog/references/state-machine.md.

Valid states: needs-grooming, groomed, blocked, in-milestone, in-progress,
              done, resolved, closed

Usage
-----
Validation only (no I/O):

    from state_handler import validate_transition, StateTransitionError

    try:
        validate_transition("needs-grooming", "groomed")
    except StateTransitionError as e:
        print(f"Invalid: {e}")

GitHub label update (requires PyGithub repo + issue objects):

    from state_handler import apply_github_transition

    apply_github_transition(repo, issue, from_state="needs-grooming", to_state="groomed")

"""

from __future__ import annotations

from collections import deque
from enum import StrEnum
from typing import Any

try:
    from github import GithubException
except ImportError:
    GithubException = Exception  # type: ignore[misc,assignment]


class BacklogState(StrEnum):
    """The 8 canonical backlog item lifecycle states."""

    NEEDS_GROOMING = "needs-grooming"
    GROOMED = "groomed"
    BLOCKED = "blocked"
    IN_MILESTONE = "in-milestone"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Valid transitions as a DAG: {from_state: frozenset(valid_to_states)}
# Source: .claude/skills/backlog/references/state-machine.md
VALID_TRANSITIONS: dict[BacklogState, frozenset[BacklogState]] = {
    BacklogState.NEEDS_GROOMING: frozenset({BacklogState.GROOMED, BacklogState.BLOCKED, BacklogState.RESOLVED}),
    BacklogState.GROOMED: frozenset({BacklogState.IN_MILESTONE, BacklogState.RESOLVED}),
    BacklogState.BLOCKED: frozenset({BacklogState.NEEDS_GROOMING, BacklogState.RESOLVED}),
    BacklogState.IN_MILESTONE: frozenset({BacklogState.IN_PROGRESS, BacklogState.GROOMED, BacklogState.RESOLVED}),
    BacklogState.IN_PROGRESS: frozenset({BacklogState.DONE, BacklogState.RESOLVED, BacklogState.BLOCKED}),
    BacklogState.DONE: frozenset({BacklogState.CLOSED}),
    BacklogState.RESOLVED: frozenset({BacklogState.CLOSED}),
    BacklogState.CLOSED: frozenset(),  # terminal state
}

# Color palette for auto-creating missing GitHub labels.
# Hex without leading '#'.
_STATE_LABEL_COLORS: dict[str, str] = {
    "needs-grooming": "FEF2C0",
    "groomed": "C2E0C6",
    "blocked": "B60205",
    "in-milestone": "BFD4F2",
    "in-progress": "1D76DB",
    "done": "0E8A16",
    "resolved": "6B737B",
    "closed": "EDEDED",
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


def validate_transition(from_state: str, to_state: str) -> None:
    """Validate a state transition against the DAG.

    Args:
        from_state: Current state value (e.g., "needs-grooming").
        to_state: Target state value (e.g., "groomed").

    Raises:
        StateTransitionError: If from_state or to_state are unknown, or if
            the transition from_state → to_state is not in the DAG.

    Note:
        This function is pure (no I/O). It never touches GitHub or the filesystem.
    """
    valid_values = [s.value for s in BacklogState]

    try:
        from_s = BacklogState(from_state)
    except ValueError:
        raise StateTransitionError(f"Unknown source state: {from_state!r}. Valid states: {valid_values}") from None

    try:
        to_s = BacklogState(to_state)
    except ValueError:
        raise StateTransitionError(f"Unknown target state: {to_state!r}. Valid states: {valid_values}") from None

    allowed = VALID_TRANSITIONS.get(from_s, frozenset())
    if to_s not in allowed:
        valid_targets = sorted(s.value for s in allowed) if allowed else []
        raise StateTransitionError(
            f"Invalid transition: {from_state!r} \u2192 {to_state!r}. "
            f"Allowed targets from {from_state!r}: "
            f"{valid_targets or ['none (terminal state)']}"
        )


def _ensure_label_exists(repo: Any, label_name: str) -> Any:  # noqa: ANN401
    """Fetch a GitHub label, creating it with a default color if absent.

    Args:
        repo: PyGithub Repository object.
        label_name: Full label name, e.g., ``"status:groomed"``.

    Returns:
        PyGithub Label object.
    """
    try:
        return repo.get_label(label_name)
    except GithubException:
        state_name = label_name.removeprefix("status:")
        color = _STATE_LABEL_COLORS.get(state_name, "EDEDED")
        description = f"Backlog item state: {state_name}"
        return repo.create_label(name=label_name, color=color, description=description)


def apply_github_transition(repo: Any, issue: Any, from_state: str | None, to_state: str) -> None:  # noqa: ANN401
    """Remove the old ``status:*`` label and add the new one on a GitHub issue.

    The new label is auto-created on the repo if it does not yet exist.

    Args:
        repo: PyGithub Repository object.
        issue: PyGithub Issue object.
        from_state: State to remove (``"needs-grooming"`` → removes
            ``"status:needs-grooming"``). Pass ``None`` to remove ALL
            existing ``status:*`` labels (use when prior state is unknown).
        to_state: Target state to add (``"groomed"`` → adds ``"status:groomed"``).

    Raises:
        StateTransitionError: On GitHub API failure.
    """
    try:
        current_labels = [lbl.name for lbl in issue.labels]

        # Remove old status label(s)
        if from_state:
            old_label_name = f"status:{from_state}"
            if old_label_name in current_labels:
                issue.remove_from_labels(old_label_name)
        else:
            # Prior state unknown — remove ALL status: labels to avoid orphaned labels
            for lbl_name in current_labels:
                if lbl_name.startswith("status:"):
                    issue.remove_from_labels(lbl_name)

        # Add new status label (auto-create if missing)
        new_label_name = f"status:{to_state}"
        # Re-fetch current labels after removal
        refreshed_labels = [lbl.name for lbl in issue.labels]
        if new_label_name not in refreshed_labels:
            lbl = _ensure_label_exists(repo, new_label_name)
            issue.add_to_labels(lbl)

    except GithubException as exc:
        raise StateTransitionError(f"Could not update GitHub labels for issue #{issue.number}: {exc}") from exc


def is_terminal_state(state: str) -> bool:
    """Return True if state is a terminal lifecycle state.

    Terminal states are done, resolved, and closed — items in these states
    have reached a final outcome and are excluded from default list views.

    This follows the architecture spec Section 4.3 definition: terminal states
    are those representing final outcomes, not solely those with empty transition
    sets in the DAG (done and resolved both transition to closed, yet are
    treated as terminal for filtering purposes).

    Args:
        state: State string to check (e.g., "done", "in-progress").

    Returns:
        True if state is done, resolved, or closed; False otherwise.

    Note:
        This function is pure (no I/O, no side effects).
    """
    TERMINAL_STATES = frozenset({BacklogState.DONE, BacklogState.RESOLVED, BacklogState.CLOSED})
    try:
        return BacklogState(state) in TERMINAL_STATES
    except ValueError:
        return False


def find_valid_path(from_state: str, to_state: str) -> list[str] | None:
    """Find a valid path between two states using BFS on the transition DAG.

    Args:
        from_state: Starting state value (e.g., "needs-grooming").
        to_state: Target state value (e.g., "in-progress").

    Returns:
        Ordered list of state strings representing the path from from_state
        to to_state (inclusive), or None if no path exists in the DAG.
        Returns ``[from_state]`` when from_state equals to_state (identity).

    Note:
        This function is pure (no I/O, no side effects).
        Returns None for unknown state values.
    """
    try:
        start = BacklogState(from_state)
        end = BacklogState(to_state)
    except ValueError:
        return None

    # Identity case
    if start == end:
        return [start.value]

    # BFS
    queue: deque[tuple[BacklogState, list[str]]] = deque()
    queue.append((start, [start.value]))
    visited: set[BacklogState] = {start}

    while queue:
        current, path = queue.popleft()
        for neighbour in VALID_TRANSITIONS.get(current, frozenset()):
            if neighbour == end:
                return [*path, neighbour.value]
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, [*path, neighbour.value]))

    return None
