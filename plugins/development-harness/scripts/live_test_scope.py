"""Safety and ownership contract shared by live tests and emergency cleanup."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Protocol

from pydantic import BaseModel, ConfigDict

PRODUCTION_REPOSITORY = "Jamie-BitFlight/claude_skills"
SANDBOX_MARKER_PATH = ".dh-e2e-sandbox"
SANDBOX_MARKER = b"development-harness live-test sandbox\n"
_REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+")
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_TYPE_PREFIX = r"(?:[a-z][a-z0-9-]*(?:\([^()\n]*\))?!?: )?"


class LiveTestScope(BaseModel):
    """Explicit non-secret identity of one authorized sandbox run."""

    model_config = ConfigDict(frozen=True)

    repository: str
    run_id: str
    source_repository: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> LiveTestScope:
        """Validate every target before a caller constructs an authenticated client.

        Returns:
            The scope shared by test execution and cleanup.
        """
        repository = environment.get("DH_E2E_REPOSITORY", "")
        run_id = environment.get("DH_E2E_RUN_ID", "")
        if not _REPOSITORY.fullmatch(repository) or repository.split("/")[-1] in {".", ".."}:
            raise ValueError("DH_E2E_REPOSITORY must explicitly name a sandbox as owner/repository")
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("DH_E2E_RUN_ID must be a nonempty alphanumeric run identity (hyphens/underscores allowed)")
        if environment.get("DH_ALLOW_TEST_NETWORK") != "1":
            raise ValueError("Live validation requires DH_ALLOW_TEST_NETWORK=1")
        if not environment.get("GITHUB_TOKEN"):
            raise ValueError("GITHUB_TOKEN must contain the dedicated sandbox credential (CI: DH_E2E_TOKEN)")
        scope = cls(
            repository=repository,
            run_id=run_id,
            source_repository=environment.get("GITHUB_REPOSITORY", PRODUCTION_REPOSITORY),
        )
        scope.check_repository(repository)
        for variable in ("GITHUB_REPO", "REPO"):
            selected = environment.get(variable)
            if selected and selected.casefold() != repository.casefold():
                raise ValueError(f"{variable} disagrees with DH_E2E_REPOSITORY; refusing mixed test/cleanup targets")
        return scope

    @property
    def title_prefix(self) -> str:
        """Return the exact title marker, including its closing delimiter."""
        return f"[MCP-TEST-{self.run_id}]"

    @property
    def body_marker(self) -> str:
        """Return the independent body marker required for resource ownership."""
        return f"<!-- dh-e2e-run:{self.run_id} -->"

    def check_repository(self, observed: str) -> None:
        """Reject production, source-repository aliases, and unexpected redirects."""
        protected = {PRODUCTION_REPOSITORY.casefold(), self.source_repository.casefold()}
        if observed.casefold() in protected:
            raise ValueError(f"Refusing live test mutation in the source/production repository: {observed}")
        if observed.casefold() != self.repository.casefold():
            raise ValueError(f"Sandbox identity changed: expected {self.repository}, received {observed}")

    def owns(self, title: str, body: str | None, pull_request: object | None = None) -> bool:
        """Recognize only an issue bearing both exact markers for this run.

        Returns:
            Whether the issue is owned by this run, never a pull request.
        """
        title_pattern = _TYPE_PREFIX + re.escape(self.title_prefix) + r"(?: |$)"
        return (
            pull_request is None
            and re.match(title_pattern, title) is not None
            and self.body_marker in (body or "").splitlines()
        )


class _Issue(Protocol):
    """The native issue surface needed for ownership-checked cleanup."""

    @property
    def number(self) -> int: ...

    @property
    def title(self) -> str: ...

    @property
    def body(self) -> str | None: ...

    @property
    def state(self) -> str: ...

    @property
    def pull_request(self) -> object | None: ...

    def edit(self, *, state: str) -> None: ...


class _IssueRepository(Protocol):
    """Minimal repository seam; production clients and test doubles can satisfy it."""

    @property
    def full_name(self) -> str: ...

    def get_issues(self, *, state: str) -> Iterable[_Issue]: ...
    def get_issue(self, number: int) -> _Issue: ...


def cleanup_run(scope: LiveTestScope, repository: _IssueRepository) -> list[int]:
    """Close only this run's open issues and verify their resulting remote state.

    Re-read ownership before mutation, rather than trusting a stale listing.
    A refusal, transport error, or unchanged state propagates: cleanup must never
    report success while resources are still open. Repeating after a partial
    failure is safe because already-closed issues are not selected again.

    Returns:
        The issue numbers whose closed state was independently read back.
    """
    scope.check_repository(repository.full_name)
    candidates = [
        issue.number
        for issue in repository.get_issues(state="open")
        if scope.owns(issue.title, issue.body, issue.pull_request)
    ]
    closed: list[int] = []
    for number in candidates:
        issue = repository.get_issue(number)
        if not scope.owns(issue.title, issue.body, issue.pull_request):
            raise RuntimeError(f"Cleanup ownership changed for #{number}; refusing mutation")
        if issue.state != "closed":
            issue.edit(state="closed")
        observed = repository.get_issue(number)
        if observed.state != "closed":
            raise RuntimeError(f"Cleanup did not close #{number}: observed state {observed.state!r}")
        closed.append(number)
    return closed
