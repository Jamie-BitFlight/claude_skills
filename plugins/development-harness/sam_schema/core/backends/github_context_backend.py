"""GitHubContextBackend — GitHub issue comment-based ContextBackend implementation.

Stores active-task session context as sticky comments on a GitHub issue.
Each session's context is a structured comment with HTML comment markers
for programmatic identification.

Comment body format::

    <!-- SAM:ACTIVE_TASK:{session_id} -->
    {JSON payload — serialized ActiveTaskContext}
    <!-- /SAM:ACTIVE_TASK:{session_id} -->

Architecture notes:

- All methods are synchronous. The MCP layer wraps calls in
  ``asyncio.to_thread()`` when needed.
- ``set_active_task`` requires ``parent_issue_number`` — there is no default
  issue; without an issue number there is nowhere to store the comment.
- ``get_active_task`` and ``clear_active_task`` rely on an in-process
  session→issue mapping populated by ``set_active_task``. If this backend
  instance is reconstructed in a new process the mapping is absent and
  ``get_active_task`` returns ``None``.
- ``list_active_tasks`` returns only sessions tracked by this process
  instance. Scanning all repository issues for active-task markers is not
  implemented.

Dependency direction (acyclic):

    github_context_backend imports from: models, dh_paths
    github_context_backend does NOT import from: server, context_config,
    context_backend (Protocol), backlog_core
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import dh_paths
from github import Auth, Github, GithubException

from sam_schema.core.models import ActiveTaskContext

if TYPE_CHECKING:
    from github.IssueComment import IssueComment
    from github.Repository import Repository

__all__ = ["GitHubContextBackend"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Marker constants
# ---------------------------------------------------------------------------

#: Namespace for all SAM active-task markers.
_MARKER_NAME = "SAM:ACTIVE_TASK"

#: Regex that extracts ``session_id`` from an opening marker tag.
#: Matches ``<!-- SAM:ACTIVE_TASK:{session_id} -->`` and captures the session_id.
_OPENING_TAG_RE: re.Pattern[str] = re.compile(r"<!-- SAM:ACTIVE_TASK:([^> ]+) -->")


def _opening_tag(session_id: str) -> str:
    """Return the opening HTML comment marker for a session.

    Args:
        session_id: Claude Code session identifier.

    Returns:
        Opening marker string, e.g. ``<!-- SAM:ACTIVE_TASK:abc123 -->``.
    """
    return f"<!-- {_MARKER_NAME}:{session_id} -->"


def _closing_tag(session_id: str) -> str:
    """Return the closing HTML comment marker for a session.

    Args:
        session_id: Claude Code session identifier.

    Returns:
        Closing marker string, e.g. ``<!-- /SAM:ACTIVE_TASK:abc123 -->``.
    """
    return f"<!-- /{_MARKER_NAME}:{session_id} -->"


# ---------------------------------------------------------------------------
# Backend implementation
# ---------------------------------------------------------------------------


class GitHubContextBackend:
    """GitHub issue comment-backed ContextBackend.

    Stores active-task session context as structured comments on a GitHub
    issue. The issue is identified by ``parent_issue_number`` passed to
    ``set_active_task``.

    Args:
        github_token: GitHub personal access token with ``repo`` scope.
        repo_name: Repository in ``owner/name`` format, e.g. ``"acme/myrepo"``.
    """

    def __init__(self, github_token: str, repo_name: str) -> None:
        """Initialise the backend with GitHub credentials.

        Args:
            github_token: GitHub personal access token with ``repo`` scope.
            repo_name: Repository in ``owner/name`` format.
        """
        self._github_token = github_token
        self._repo_name = repo_name
        # In-process mapping: session_id → parent_issue_number.
        # Populated by set_active_task; consulted by get/clear_active_task.
        self._session_issues: dict[str, str | int] = {}

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def get_active_task(self, session_id: str) -> ActiveTaskContext | None:
        """Retrieve the active task context for a session from a GitHub comment.

        Args:
            session_id: Claude Code session identifier.

        Returns:
            Parsed ``ActiveTaskContext`` if a matching comment exists, else ``None``.
        """
        issue_number = self._session_issues.get(session_id)
        if issue_number is None:
            logger.debug("get_active_task: no issue mapping for session %r — returning None", session_id)
            return None

        comment = self._find_comment(issue_number, session_id)
        if comment is None:
            return None
        return _parse_comment_body(comment.body)

    def set_active_task(
        self, session_id: str, plan: str, task: str, plan_dir: str, parent_issue_number: str | int | None = None
    ) -> ActiveTaskContext:
        """Create or update a GitHub issue comment storing the session context.

        Args:
            session_id: Claude Code session identifier.
            plan: Plan address (e.g., ``"P1601"``).
            task: Task ID within the plan (e.g., ``"T02"``).
            plan_dir: Plan directory sentinel ``"plan"`` or an absolute path.
            parent_issue_number: GitHub integer issue number to store the comment on.
                Required for ``GitHubContextBackend``; raises if absent or a beads string.

        Returns:
            The stored ``ActiveTaskContext`` instance.

        Raises:
            ValueError: If ``parent_issue_number`` is ``None``.
            TypeError: If ``parent_issue_number`` is a beads nanoid string; GitHub requires int.
        """
        if parent_issue_number is None:
            raise ValueError(
                "GitHubContextBackend.set_active_task requires parent_issue_number. "
                "Provide the GitHub issue number for the parent story."
            )
        if isinstance(parent_issue_number, str):
            raise TypeError(
                f"GitHubContextBackend.set_active_task requires an integer issue number; "
                f"got beads nanoid {parent_issue_number!r}. "
                f"Use a local or memory backend for beads-tracked tasks."
            )

        self._session_issues[session_id] = parent_issue_number

        context = ActiveTaskContext(
            task_file_path=_resolve_task_file_path(plan, plan_dir),
            task_id=task,
            plan=plan,
            task=task,
            plan_dir=plan_dir,
            parent_issue_number=parent_issue_number,
            session_id=session_id,
            started_at=datetime.now(tz=UTC).isoformat(),
        )

        comment_body = _build_comment_body(session_id, context)
        existing = self._find_comment(parent_issue_number, session_id)

        if existing is not None:
            existing.edit(comment_body)
            logger.debug("set_active_task: updated comment id=%s on issue #%d", existing.id, parent_issue_number)
        else:
            issue = self._repo.get_issue(parent_issue_number)
            issue.create_comment(comment_body)
            logger.debug(
                "set_active_task: created comment on issue #%d for session %r", parent_issue_number, session_id
            )

        return context

    def clear_active_task(self, session_id: str) -> bool:
        """Delete the GitHub issue comment for the session.

        Does not raise if no comment exists.

        Args:
            session_id: Claude Code session identifier.

        Returns:
            ``True`` if a comment was found and deleted, ``False`` otherwise.
        """
        issue_number = self._session_issues.get(session_id)
        if issue_number is None:
            logger.debug("clear_active_task: no issue mapping for session %r — nothing to clear", session_id)
            return False

        comment = self._find_comment(issue_number, session_id)
        if comment is None:
            self._session_issues.pop(session_id, None)
            return False

        comment.delete()
        self._session_issues.pop(session_id, None)
        logger.debug(
            "clear_active_task: deleted comment id=%s on issue #%d for session %r", comment.id, issue_number, session_id
        )
        return True

    def list_active_tasks(self) -> list[ActiveTaskContext]:
        """Return active task contexts for sessions tracked by this instance.

        Note:
            Only sessions registered via ``set_active_task`` in the current
            process are returned. Sessions created by other processes are not
            discovered — scanning all repository issues for markers is not
            implemented.

        Returns:
            List of ``ActiveTaskContext`` for tracked sessions with existing comments.
        """
        results: list[ActiveTaskContext] = []
        for session_id, issue_number in list(self._session_issues.items()):
            comment = self._find_comment(issue_number, session_id)
            if comment is None:
                continue
            context = _parse_comment_body(comment.body)
            if context is not None:
                results.append(context)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @cached_property
    def _repo(self) -> Repository:
        """Return a cached PyGithub Repository object.

        Returns:
            PyGithub ``Repository`` instance for ``self._repo_name``.
        """
        gh = Github(auth=Auth.Token(self._github_token), timeout=30)
        return gh.get_repo(self._repo_name)

    def _find_comment(self, issue_number: str | int, session_id: str) -> IssueComment | None:
        """Search issue comments for the session_id opening marker.

        Args:
            issue_number: GitHub integer issue number to search. Returns ``None`` immediately
                for non-int values (e.g. beads nanoid strings) — GitHub requires an int.
            session_id: Session identifier whose marker to look for.

        Returns:
            Matching ``IssueComment`` if found, else ``None``.
        """
        if not isinstance(issue_number, int):
            logger.debug("_find_comment: issue_number %r is not an int — skipping GitHub lookup", issue_number)
            return None
        opening = _opening_tag(session_id)
        try:
            issue = self._repo.get_issue(issue_number)
            for comment in issue.get_comments():
                if opening in comment.body:
                    return comment
        except GithubException as exc:
            logger.warning(
                "_find_comment: GitHub error searching issue #%d for session %r: %s", issue_number, session_id, exc
            )
        return None


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions — no GitHub I/O)
# ---------------------------------------------------------------------------


def _build_comment_body(session_id: str, context: ActiveTaskContext) -> str:
    """Build the GitHub comment body for a session context.

    Args:
        session_id: Claude Code session identifier.
        context: ``ActiveTaskContext`` to serialize.

    Returns:
        Complete comment body string with opening and closing marker tags.
    """
    payload = json.dumps(context.model_dump(exclude_none=False), indent=2, default=str)
    opening = _opening_tag(session_id)
    closing = _closing_tag(session_id)
    return f"{opening}\n{payload}\n{closing}"


def _parse_comment_body(body: str) -> ActiveTaskContext | None:
    """Extract and parse the JSON payload from a comment body.

    Args:
        body: Raw comment body text containing a SAM marker block.

    Returns:
        Parsed ``ActiveTaskContext``, or ``None`` if the body does not contain
        a valid marker block or if JSON parsing fails.
    """
    match = _OPENING_TAG_RE.search(body)
    if not match:
        return None

    session_id = match.group(1)
    opening = _opening_tag(session_id)
    closing = _closing_tag(session_id)

    start = body.find(opening)
    end = body.find(closing)
    if start == -1 or end == -1:
        return None

    json_str = body[start + len(opening) : end].strip()
    try:
        data = json.loads(json_str)
        return ActiveTaskContext.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("_parse_comment_body: failed to parse context payload: %s", exc)
        return None


def _resolve_task_file_path(plan: str, plan_dir: str) -> str:
    """Resolve the absolute path to the plan YAML file.

    Mirrors ``LocalContextBackend._resolve_task_file_path``.

    Args:
        plan: Plan address (e.g., ``"P1601"``).
        plan_dir: Plan directory sentinel ``"plan"`` or an absolute path.

    Returns:
        Absolute path string to the plan YAML file.
    """
    base: Path = dh_paths.plan_dir() if plan_dir == "plan" else Path(plan_dir)
    return str(base / f"{plan}.yaml")
