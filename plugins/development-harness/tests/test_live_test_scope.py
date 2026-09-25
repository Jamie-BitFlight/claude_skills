"""Run-scope safety is tested without credentials or a remote GitHub service."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from live_test_scope import LiveTestScope, cleanup_run


def environment() -> dict[str, str]:
    return {
        "DH_E2E_REPOSITORY": "test-owner/disposable-backlog",
        "DH_E2E_RUN_ID": "123-1",
        "DH_ALLOW_TEST_NETWORK": "1",
        "GITHUB_TOKEN": "test-only-not-a-credential",
        "GITHUB_REPOSITORY": "source-owner/source-repo",
    }


@pytest.mark.parametrize("missing", ["DH_E2E_REPOSITORY", "DH_E2E_RUN_ID", "DH_ALLOW_TEST_NETWORK", "GITHUB_TOKEN"])
def test_configuration_must_be_explicit(missing: str) -> None:
    env = environment()
    del env[missing]
    with pytest.raises(ValueError, match=missing):
        LiveTestScope.from_environment(env)


@pytest.mark.parametrize("target", ["jamie-bitflight/CLAUDE_SKILLS", "SOURCE-OWNER/source-repo"])
def test_source_and_production_are_never_sandboxes(target: str) -> None:
    env = environment() | {"DH_E2E_REPOSITORY": target}
    with pytest.raises(ValueError, match="source/production"):
        LiveTestScope.from_environment(env)


@pytest.mark.parametrize("variable", ["REPO", "GITHUB_REPO"])
def test_test_and_cleanup_targets_cannot_disagree(variable: str) -> None:
    with pytest.raises(ValueError, match=variable):
        LiveTestScope.from_environment(environment() | {variable: "other/repository"})


@pytest.mark.parametrize("target", ["", "https://github.com/owner/repo", "owner/../repo", "owner/..", " owner/repo"])
def test_invalid_repository_targets_are_rejected(target: str) -> None:
    with pytest.raises(ValueError, match="DH_E2E_REPOSITORY"):
        LiveTestScope.from_environment(environment() | {"DH_E2E_REPOSITORY": target})


def test_redirect_to_another_repository_is_not_authorized() -> None:
    scope = LiveTestScope.from_environment(environment())
    with pytest.raises(ValueError, match="identity changed"):
        scope.check_repository("other/repository")


@pytest.mark.parametrize("prefix", ["", "feat: ", "fix(api)!: "])
def test_valid_type_prefix_is_not_part_of_the_ownership_oracle(prefix: str) -> None:
    scope = LiveTestScope.from_environment(environment())
    assert scope.owns(f"{prefix}[MCP-TEST-123-1] item", "<!-- dh-e2e-run:123-1 -->\nDescription")


@pytest.mark.parametrize(
    ("title", "body", "pull_request"),
    [
        ("[MCP-TEST-123-10] item", "<!-- dh-e2e-run:123-10 -->", None),
        ("[MCP-TEST-123-1] item", "<!-- dh-e2e-run:other -->", None),
        ("Discussion of [MCP-TEST-123-1]", "<!-- dh-e2e-run:123-1 -->", None),
        ("[MCP-TEST-123-1] item", "prefix <!-- dh-e2e-run:123-1 -->", None),
        ("[MCP-TEST-123-1] item", "<!-- dh-e2e-run:123-1 -->", object()),
        ("[MCP-TEST-123-1] item", None, None),
    ],
)
def test_lookalikes_and_unowned_resources_are_not_cleanup_targets(title, body, pull_request) -> None:
    scope = LiveTestScope.from_environment(environment())
    assert not scope.owns(title, body, pull_request)


@dataclass
class Issue:
    number: int
    title: str
    body: str | None
    state: str = "open"
    pull_request: object | None = None
    ignore_close: bool = False
    edits: list[str] = field(default_factory=list)

    def edit(self, *, state: str) -> None:
        self.edits.append(state)
        if not self.ignore_close:
            self.state = state


@dataclass
class Repository:
    issues: dict[int, Issue]
    full_name: str = "test-owner/disposable-backlog"
    reads: list[int] = field(default_factory=list)
    replacement: Issue | None = None

    def get_issues(self, *, state: str) -> list[Issue]:
        return [issue for issue in self.issues.values() if issue.state == state]

    def get_issue(self, number: int) -> Issue:
        self.reads.append(number)
        return self.replacement if self.replacement is not None else self.issues[number]


def test_cleanup_preserves_foreign_issues_and_reads_back_its_own_close() -> None:
    scope = LiveTestScope.from_environment(environment())
    owned = Issue(7, "feat: [MCP-TEST-123-1] item", "<!-- dh-e2e-run:123-1 -->")
    foreign = Issue(8, "[MCP-TEST-other] item", "<!-- dh-e2e-run:other -->")
    repo = Repository({7: owned, 8: foreign})

    assert cleanup_run(scope, repo) == [7]
    assert owned.state == "closed"
    assert repo.reads == [7, 7]  # Authorization read and an independent post-write read.
    assert foreign.state == "open"
    assert foreign.edits == []
    assert cleanup_run(scope, repo) == []


def test_a_successful_api_return_without_a_closed_issue_fails_cleanup() -> None:
    scope = LiveTestScope.from_environment(environment())
    issue = Issue(7, "[MCP-TEST-123-1] item", "<!-- dh-e2e-run:123-1 -->", ignore_close=True)
    with pytest.raises(RuntimeError, match="did not close #7"):
        cleanup_run(scope, Repository({7: issue}))


def test_changed_ownership_between_listing_and_write_refuses_cleanup() -> None:
    scope = LiveTestScope.from_environment(environment())
    listed = Issue(7, "[MCP-TEST-123-1] item", "<!-- dh-e2e-run:123-1 -->")
    foreign = Issue(7, "A real issue", "User content")
    with pytest.raises(RuntimeError, match="ownership changed"):
        cleanup_run(scope, Repository({7: listed}, replacement=foreign))
    assert foreign.edits == []


def test_cleanup_rechecks_repository_identity_before_any_mutation() -> None:
    scope = LiveTestScope.from_environment(environment())
    repo = Repository({}, full_name="Jamie-BitFlight/claude_skills")
    with pytest.raises(ValueError, match="source/production"):
        cleanup_run(scope, repo)
    assert repo.reads == []
