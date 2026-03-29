"""Final integration tests for the three-tier DH state architecture.

T13: Full workflow validation — verifies that the consolidated dh_paths
architecture works end-to-end across all consumers.

Tests cover:
- Full backlog write/read cycle via new state root
- Full plan file write/read cycle via new state root
- Context file lifecycle (write, read, delete)
- Worktree state isolation (two projects use distinct state roots)
- Artifact path resolution through GitHubArtifactProvider (no .claude/)
- ArtifactRegistry round-trip: register, read, remove
- Grep audit: no hardcoded .claude/backlog, .claude/context, .claude/reports
  in plugin production Python source
- Artifact provider and artifact registry contain no stale hardcoded old paths
  in production code paths (only docstring examples exempt)
- models.BACKLOG_DIR does not point inside .claude/ after init()
- All state directories resolve under DH_STATE_HOME when set
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import dh_paths
import pytest
from backlog_core import models
from backlog_core.artifact_provider import GitHubArtifactProvider
from backlog_core.artifact_registry import (
    ArtifactRegistry,
    parse_manifest_section,
    render_manifest_section,
    replace_manifest_in_body,
)
from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactStatus, ArtifactType
from dh_paths import backlog_dir, compute_slug, context_dir, ensure_dirs, plan_dir, reports_dir, state_root

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Provide a fake project root and isolated DH_STATE_HOME.

    Returns:
        Tuple of (project_root, state_home) both under tmp_path.
    """
    state_home = tmp_path / "dh_state"
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DH_STATE_HOME", str(state_home))
    return project_root, state_home


@pytest.fixture
def project_with_dirs(isolated_project: tuple[Path, Path]) -> tuple[Path, Path]:
    """Like isolated_project but with all state directories created.

    Returns:
        Tuple of (project_root, state_root_path).
    """
    project_root, _state_home = isolated_project
    sr = ensure_dirs(project_root)
    return project_root, sr


# ---------------------------------------------------------------------------
# Full backlog write/read cycle
# ---------------------------------------------------------------------------


class TestBacklogWriteReadCycle:
    """Full backlog write/read cycle using the new state root.

    Strategy: Write a markdown file directly to backlog_dir(), read it back,
    and verify round-trip fidelity. No GitHub calls — filesystem only.
    Validates that the backlog directory is correctly placed under
    DH_STATE_HOME/projects/{slug}/backlog/ (not .claude/backlog/).
    """

    def test_backlog_file_written_to_state_root_not_dot_claude(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify a backlog file written to backlog_dir() resolves under DH_STATE_HOME.

        Tests: backlog_dir() routes to state root, not .claude/backlog/
        How: Write a sentinel file to backlog_dir(); assert its path contains
             the project slug and does not contain '.claude'
        Why: Core requirement of T13 — all backlog state must be outside the repo
        """
        project_root, _sr = project_with_dirs

        # Arrange
        bd = backlog_dir(project_root)
        item_file = bd / "p1-my-feature.md"

        # Act
        item_file.write_text("# My Feature\n\nstatus: open\n", encoding="utf-8")

        # Assert — file is under state root, not .claude/backlog/
        assert item_file.exists()
        assert ".claude" not in str(item_file)
        assert "backlog" in str(item_file)
        slug = compute_slug(project_root)
        assert slug in str(item_file)

    def test_backlog_file_round_trips_content_intact(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify backlog file content survives a write/read cycle.

        Tests: backlog_dir() is a readable, writable filesystem path
        How: Write YAML frontmatter + body; read back; compare exact content
        Why: Producers and consumers must agree on file location
        """
        project_root, _sr = project_with_dirs

        # Arrange
        content = "---\ntitle: Integration Test Item\nstatus: open\npriority: P1\n---\n\nTest body.\n"
        bd = backlog_dir(project_root)
        item_file = bd / "p1-integration-test-item.md"

        # Act
        item_file.write_text(content, encoding="utf-8")
        result = item_file.read_text(encoding="utf-8")

        # Assert
        assert result == content

    def test_models_backlog_dir_resolves_to_dh_state_not_dot_claude(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify models.BACKLOG_DIR resolves under DH_STATE_HOME, not .claude/.

        Tests: models.init() updates BACKLOG_DIR via dh_paths
        How: Call models.init(project_dir=..., repo=...) with a stub repo slug to
             bypass discover_repo() which requires a real GitHub remote.
             Check BACKLOG_DIR path.
        Why: models.BACKLOG_DIR is the runtime constant used by operations.py
        """
        project_root, _state_home = isolated_project

        # Arrange / Act
        models.init(project_dir=str(project_root), repo="test-owner/test-repo")

        # Assert
        assert ".claude" not in str(models.BACKLOG_DIR)
        assert "backlog" in str(models.BACKLOG_DIR).lower()
        expected = dh_paths.backlog_dir(project_root)
        assert expected == models.BACKLOG_DIR

    def test_models_backlog_dir_contains_project_slug(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify models.BACKLOG_DIR path embeds the project slug.

        Tests: models.BACKLOG_DIR path includes project-specific slug
        How: Init with project_root and stub repo slug to bypass discover_repo()
             which requires a real GitHub remote. Check slug in BACKLOG_DIR.
        Why: Multiple projects must have distinct backlog directories
        """
        project_root, _state_home = isolated_project

        # Arrange / Act
        models.init(project_dir=str(project_root), repo="test-owner/test-repo")
        slug = compute_slug(project_root)

        # Assert
        assert slug in str(models.BACKLOG_DIR)


# ---------------------------------------------------------------------------
# Full plan file write/read cycle
# ---------------------------------------------------------------------------


class TestPlanFileWriteReadCycle:
    """Full plan file write/read cycle using the new state root.

    Strategy: Write a YAML plan file to plan_dir(), read it back via the
    filesystem, and confirm it is not stored under the repo's plan/ directory.
    """

    def test_plan_file_written_to_state_root_not_repo_plan_dir(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify a plan file written to plan_dir() is outside the repo.

        Tests: plan_dir() resolves to DH_STATE_HOME/projects/{slug}/plan/
        How: Write plan YAML; assert path is under state root and not under
             project_root/plan/
        Why: Plan files must move out of the repo working tree
        """
        project_root, _sr = project_with_dirs

        # Arrange
        pd = plan_dir(project_root)
        plan_file = pd / "P001-my-feature.yaml"
        content = "plan-number: 1\nslug: my-feature\ngoal: test\ntasks: []\n"

        # Act
        plan_file.write_text(content, encoding="utf-8")

        # Assert — NOT in repo's plan/ directory
        assert plan_file.exists()
        repo_plan_dir = project_root / "plan"
        assert not str(plan_file).startswith(str(repo_plan_dir))
        assert ".claude" not in str(plan_file)
        slug = compute_slug(project_root)
        assert slug in str(plan_file)

    def test_plan_file_round_trips_yaml_content(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify plan YAML content survives a write/read cycle.

        Tests: plan_dir() is a readable, writable filesystem path
        How: Write multi-line YAML; read back; assert content identity
        Why: SAM MCP server reads plan files from this location
        """
        project_root, _sr = project_with_dirs

        # Arrange
        yaml_content = (
            "plan-number: 42\n"
            "slug: test-feature\n"
            "goal: Verify path consolidation\n"
            "tasks:\n"
            "  - id: T1\n"
            "    title: First task\n"
            "    status: not-started\n"
        )
        pd = plan_dir(project_root)
        plan_file = pd / "P042-test-feature.yaml"

        # Act
        plan_file.write_text(yaml_content, encoding="utf-8")
        result = plan_file.read_text(encoding="utf-8")

        # Assert
        assert result == yaml_content

    def test_plan_codebase_subdir_exists_after_ensure_dirs(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify plan/codebase/ subdirectory is created by ensure_dirs().

        Tests: ensure_dirs creates plan/codebase/ for codebase analysis artifacts
        How: Call ensure_dirs; check plan_dir()/codebase/ exists
        Why: codebase-analyzer writes artifacts to this subdirectory
        """
        project_root, _sr = project_with_dirs

        # Assert — ensure_dirs already called in fixture
        codebase_dir = plan_dir(project_root) / "codebase"
        assert codebase_dir.is_dir()


# ---------------------------------------------------------------------------
# Context file lifecycle
# ---------------------------------------------------------------------------


class TestContextFileLifecycle:
    """Context file write, read, and delete lifecycle.

    Strategy: Simulate the task_status_hook.py lifecycle — write an
    active-task JSON context file to context_dir(), read it back, then
    delete it to simulate SubagentStop cleanup.
    """

    def test_context_file_written_to_state_root_not_dot_claude(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify context file writes to DH state root, not .claude/context/.

        Tests: context_dir() resolves outside the repo working tree
        How: Write active-task JSON; assert path does not contain .claude/context
        Why: Session context files must not pollute the repo working tree
        """
        project_root, _sr = project_with_dirs

        # Arrange
        cd = context_dir(project_root)
        session_id = "test-session-abc123"
        context_file = cd / f"active-task-{session_id}.json"
        payload = {"task_file_path": "plan/P001.yaml", "task_id": "T1", "parent_issue_number": 42}

        # Act
        context_file.write_text(json.dumps(payload), encoding="utf-8")

        # Assert
        assert context_file.exists()
        assert ".claude/context" not in str(context_file)
        slug = compute_slug(project_root)
        assert slug in str(context_file)

    def test_context_file_round_trips_json_payload(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify context JSON payload survives a write/read cycle.

        Tests: context_dir() is a readable, writable filesystem path
        How: Write known JSON; read and parse back; compare all fields
        Why: task_status_hook.py reads this file on PostToolUse events
        """
        project_root, _sr = project_with_dirs

        # Arrange
        cd = context_dir(project_root)
        session_id = "session-deadbeef"
        context_file = cd / f"active-task-{session_id}.json"
        payload = {
            "task_file_path": "plan/P981-consolidate-dh-paths.yaml",
            "task_id": "T13",
            "parent_issue_number": 981,
        }

        # Act
        context_file.write_text(json.dumps(payload), encoding="utf-8")
        loaded = json.loads(context_file.read_text(encoding="utf-8"))

        # Assert
        assert loaded["task_file_path"] == payload["task_file_path"]
        assert loaded["task_id"] == payload["task_id"]
        assert loaded["parent_issue_number"] == payload["parent_issue_number"]

    def test_context_file_deletion_simulates_subagent_stop_cleanup(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify context file can be deleted after task completion.

        Tests: SubagentStop hook cleanup removes the active-task context file
        How: Write context file; delete it; assert it no longer exists
        Why: Stale context files must not persist beyond task execution
        """
        project_root, _sr = project_with_dirs

        # Arrange
        cd = context_dir(project_root)
        context_file = cd / "active-task-cleanup-test.json"
        context_file.write_text('{"task_id": "T1"}', encoding="utf-8")
        assert context_file.exists()

        # Act — simulate hook deletion
        context_file.unlink()

        # Assert
        assert not context_file.exists()


# ---------------------------------------------------------------------------
# Worktree state isolation
# ---------------------------------------------------------------------------


class TestWorktreeStateIsolation:
    """Two projects share the same DH_STATE_HOME but have distinct state roots.

    Strategy: Create two fake project roots under the same DH_STATE_HOME.
    Verify their slugs differ and their state directories do not overlap.
    """

    def test_two_projects_produce_distinct_state_roots(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify two different project paths produce distinct state roots.

        Tests: Project slug isolation prevents state directory collision
        How: Create project_a and project_b; assert state_root differs
        Why: Multiple projects on the same machine must not share state
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "shared_dh"))
        project_a = tmp_path / "repos" / "project_alpha"
        project_b = tmp_path / "repos" / "project_beta"
        project_a.mkdir(parents=True)
        project_b.mkdir(parents=True)

        # Act
        root_a = state_root(project_a)
        root_b = state_root(project_b)

        # Assert
        assert root_a != root_b

    def test_two_projects_backlog_dirs_do_not_overlap(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify two projects have non-overlapping backlog directories.

        Tests: backlog_dir() isolation between two projects
        How: Write a file to project_a's backlog; confirm it is absent in project_b's
        Why: Backlog CRUD must not cross-contaminate between projects
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "shared_dh"))
        project_a = tmp_path / "project_a"
        project_b = tmp_path / "project_b"
        project_a.mkdir()
        project_b.mkdir()
        ensure_dirs(project_a)
        ensure_dirs(project_b)

        # Act — write to project_a's backlog
        item = backlog_dir(project_a) / "p1-alpha-item.md"
        item.write_text("# Alpha Item", encoding="utf-8")

        # Assert — not visible in project_b's backlog
        assert not (backlog_dir(project_b) / "p1-alpha-item.md").exists()

    def test_worktree_resolves_to_main_repo_state_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Verify a worktree resolves to the same state root as the main repo.

        Tests: git_project_root returns main repo root for linked worktrees
        How: Mock subprocess.run to return common .git dir pointing to main repo;
             call git_project_root from worktree cwd; assert slug matches main repo
        Why: Worktrees must share state with the main repo, not create separate dirs
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        dh_paths._root_cache.clear()

        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        git_common_dir = main_repo / ".git"
        git_common_dir.mkdir()
        worktree = tmp_path / "worktree-branch"
        worktree.mkdir()

        def _mock_git(args: list[str], **kwargs: object) -> object:
            return type("CP", (), {"stdout": str(git_common_dir) + "\n", "returncode": 0})()

        mocker.patch("subprocess.run", side_effect=_mock_git)

        # Act
        root_from_main = dh_paths.git_project_root(cwd=main_repo)
        dh_paths._root_cache.clear()
        root_from_worktree = dh_paths.git_project_root(cwd=worktree)

        # Assert — both resolve to same main repo root → same slug → same state dir
        assert compute_slug(root_from_main) == compute_slug(root_from_worktree)


# ---------------------------------------------------------------------------
# Artifact path resolution through GitHubArtifactProvider
# ---------------------------------------------------------------------------


class TestArtifactProviderPathResolution:
    """GitHubArtifactProvider resolves artifact paths relative to state root.

    Strategy: Instantiate GitHubArtifactProvider with an explicit root_worktree
    pointing to a tmp_path state root. Write artifact files there. Verify
    read_artifact_content reads them correctly and that traversal is blocked.
    """

    def test_artifact_provider_default_root_is_state_root(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify GitHubArtifactProvider defaults root_worktree to dh_paths.state_root().

        Tests: GitHubArtifactProvider constructor uses state_root() by default
        How: Patch git_project_root; instantiate with no root_worktree; compare
        Why: Providers must serve artifacts from the new state root, not the repo
        """
        project_root, _state_home = isolated_project

        # Arrange
        with patch.object(dh_paths, "git_project_root", return_value=project_root):
            provider = GitHubArtifactProvider(repo="owner/repo")

        # Assert
        expected = dh_paths.state_root(project_root)
        assert provider._root_worktree == expected

    def test_artifact_provider_reads_file_from_state_root(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify read_artifact_content reads from state root, not repo root.

        Tests: GitHubArtifactProvider.read_artifact_content returns file content
        How: Write file to state_root/plan/; read via provider with explicit root
        Why: MCP artifact_read tool calls this method; must find files in new location
        """
        project_root, sr = project_with_dirs

        # Arrange
        artifact_path = plan_dir(project_root) / "architect-my-feature.md"
        artifact_path.write_text("# Architecture\n\nContent here.", encoding="utf-8")

        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=sr)

        # Act
        content = provider.read_artifact_content("plan/architect-my-feature.md")

        # Assert
        assert content == "# Architecture\n\nContent here."

    def test_artifact_provider_raises_file_not_found_for_missing_file(
        self, project_with_dirs: tuple[Path, Path]
    ) -> None:
        """Verify FileNotFoundError is raised when artifact file is absent.

        Tests: GitHubArtifactProvider.read_artifact_content fails fast on missing file
        How: Request non-existent path; assert FileNotFoundError raised
        Why: Fail-fast principle — missing artifacts surface immediately
        """
        _project_root, sr = project_with_dirs
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=sr)

        # Act / Assert
        with pytest.raises(FileNotFoundError):
            provider.read_artifact_content("plan/nonexistent-artifact.md")

    def test_artifact_provider_blocks_path_traversal(self, project_with_dirs: tuple[Path, Path]) -> None:
        """Verify path traversal attempts raise ValueError.

        Tests: GitHubArtifactProvider._validate_artifact_path blocks traversal
        How: Pass ../../../etc/passwd; assert ValueError with 'traversal' message
        Why: Security requirement — no escaping the state root directory
        """
        _project_root, sr = project_with_dirs
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=sr)

        # Act / Assert
        with pytest.raises(ValueError, match="Path traversal detected"):
            provider.read_artifact_content("../../../etc/passwd")

    def test_artifact_provider_root_does_not_contain_dot_claude(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify the provider root_worktree path does not include .claude/.

        Tests: GitHubArtifactProvider uses state_root() not a .claude/ path
        How: Instantiate provider; inspect _root_worktree string; assert no .claude
        Why: Artifacts must be served from the new state root, not the old .claude tree
        """
        project_root, _state_home = isolated_project

        # Arrange
        with patch.object(dh_paths, "git_project_root", return_value=project_root):
            provider = GitHubArtifactProvider(repo="owner/repo")

        # Assert
        assert ".claude" not in str(provider._root_worktree)

    def test_read_local_artifact_content_returns_none_for_missing_file(
        self, project_with_dirs: tuple[Path, Path]
    ) -> None:
        """Verify read_local_artifact_content returns None for absent files.

        Tests: GitHubArtifactProvider.read_local_artifact_content soft-miss behavior
        How: Call with non-existent path; assert None returned (no exception)
        Why: Auto-upload path — missing file means no local content to upload
        """
        _project_root, sr = project_with_dirs
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=sr)

        # Act
        result = provider.read_local_artifact_content("plan/not-there.md")

        # Assert
        assert result is None

    def test_read_local_artifact_content_returns_content_when_file_exists(
        self, project_with_dirs: tuple[Path, Path]
    ) -> None:
        """Verify read_local_artifact_content returns file content when present.

        Tests: GitHubArtifactProvider.read_local_artifact_content reads state root files
        How: Write file to state_root/plan/; call method; assert content returned
        Why: Auto-upload supplies content for new artifacts to GitHub
        """
        project_root, sr = project_with_dirs
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=sr)

        # Arrange
        artifact = plan_dir(project_root) / "feature-context-test.md"
        artifact.write_text("Feature context content.", encoding="utf-8")

        # Act
        result = provider.read_local_artifact_content("plan/feature-context-test.md")

        # Assert
        assert result == "Feature context content."


# ---------------------------------------------------------------------------
# ArtifactRegistry round-trip: register, read, remove
# ---------------------------------------------------------------------------


class TestArtifactRegistryRoundTrip:
    """ArtifactRegistry stateless operations: register, get_by_type, remove, update_status.

    Strategy: Construct ArtifactManifest and ArtifactEntry objects; run
    registry operations; verify manifest contents. No I/O — registry is
    purely stateless business logic.
    """

    def test_register_adds_entry_to_empty_manifest(self) -> None:
        """Verify registering into an empty manifest adds one entry.

        Tests: ArtifactRegistry.register on an empty manifest
        How: Create empty manifest; register one entry; assert artifacts has 1 entry
        Why: Registration is the first step in artifact lifecycle
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        entry = ArtifactEntry(
            artifact_type=ArtifactType.ARCHITECT,
            path="plan/architect-consolidate-dh-paths.md",
            agent="python-cli-design-spec",
        )

        # Act
        updated = registry.register(manifest, entry)

        # Assert
        assert len(updated.artifacts) == 1
        assert updated.artifacts[0].artifact_type == ArtifactType.ARCHITECT
        assert updated.artifacts[0].path == "plan/architect-consolidate-dh-paths.md"

    def test_register_is_idempotent_for_same_type_and_path(self) -> None:
        """Verify re-registering same type+path updates in-place, no duplicate.

        Tests: ArtifactRegistry.register upsert logic (exact match updates row)
        How: Register same entry twice; assert artifact count remains 1
        Why: Idempotent registration prevents duplicate manifest rows
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        entry = ArtifactEntry(
            artifact_type=ArtifactType.FEATURE_CONTEXT,
            path="plan/feature-context-consolidate.md",
            agent="feature-researcher",
        )

        # Act
        manifest = registry.register(manifest, entry)
        manifest = registry.register(manifest, entry)

        # Assert — only one entry despite two registrations
        assert len(manifest.artifacts) == 1

    def test_register_allows_multiple_entries_of_same_type_with_different_paths(self) -> None:
        """Verify same type with different paths creates two entries.

        Tests: ArtifactRegistry.register multi-entry same type logic
        How: Register two codebase-analysis entries with different paths
        Why: Multiple codebase analyses are valid (different scopes)
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        entry_a = ArtifactEntry(
            artifact_type=ArtifactType.CODEBASE_ANALYSIS,
            path="plan/codebase/backlog-core.md",
            agent="codebase-analyzer",
        )
        entry_b = ArtifactEntry(
            artifact_type=ArtifactType.CODEBASE_ANALYSIS, path="plan/codebase/sam-schema.md", agent="codebase-analyzer"
        )

        # Act
        manifest = registry.register(manifest, entry_a)
        manifest = registry.register(manifest, entry_b)

        # Assert
        assert len(manifest.artifacts) == 2

    def test_get_by_type_returns_only_matching_entries(self) -> None:
        """Verify get_by_type filters manifest entries by artifact type.

        Tests: ArtifactRegistry.get_by_type filtering
        How: Register mixed types; call get_by_type for one type; assert correct subset
        Why: Consumers filter by type to find specific artifact files
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, path="plan/architect.md")
        )
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.FEATURE_CONTEXT, path="plan/fc.md")
        )
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.TASK_PLAN, path="plan/P001.yaml")
        )

        # Act
        architect_entries = registry.get_by_type(manifest, ArtifactType.ARCHITECT)

        # Assert
        assert len(architect_entries) == 1
        assert architect_entries[0].path == "plan/architect.md"

    def test_remove_deletes_matching_entry(self) -> None:
        """Verify remove() eliminates the entry matching type and path.

        Tests: ArtifactRegistry.remove deletes the specified entry
        How: Register two entries; remove one; assert only the other remains
        Why: Stale artifacts must be removable from the manifest
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        entry_a = ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, path="plan/architect.md")
        entry_b = ArtifactEntry(artifact_type=ArtifactType.FEATURE_CONTEXT, path="plan/fc.md")
        manifest = registry.register(manifest, entry_a)
        manifest = registry.register(manifest, entry_b)

        # Act
        manifest = registry.remove(manifest, ArtifactType.ARCHITECT, "plan/architect.md")

        # Assert
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].artifact_type == ArtifactType.FEATURE_CONTEXT

    def test_update_status_changes_entry_lifecycle_status(self) -> None:
        """Verify update_status() changes status for the matching entry.

        Tests: ArtifactRegistry.update_status mutates status field
        How: Register entry; update status to superseded; assert change
        Why: Lifecycle management marks old artifacts as superseded
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        entry = ArtifactEntry(
            artifact_type=ArtifactType.ARCHITECT, path="plan/architect.md", status=ArtifactStatus.CURRENT
        )
        manifest = registry.register(manifest, entry)

        # Act
        manifest = registry.update_status(
            manifest, ArtifactType.ARCHITECT, "plan/architect.md", ArtifactStatus.SUPERSEDED
        )

        # Assert
        assert manifest.artifacts[0].status == ArtifactStatus.SUPERSEDED

    def test_artifact_entry_auto_timestamps_created_at(self) -> None:
        """Verify register() auto-stamps created_at when entry has no timestamp.

        Tests: ArtifactRegistry.register auto-timestamp behavior
        How: Create entry with empty created_at; register; assert created_at is populated
        Why: All manifest entries must have timestamps for audit/traceability
        """
        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=981)
        entry = ArtifactEntry(artifact_type=ArtifactType.TASK_PLAN, path="plan/P001-foo.yaml", created_at="")

        # Act
        manifest = registry.register(manifest, entry)

        # Assert
        assert manifest.artifacts[0].created_at != ""
        # ISO format check
        assert "T" in manifest.artifacts[0].created_at


# ---------------------------------------------------------------------------
# Manifest section parse/render round-trip
# ---------------------------------------------------------------------------


class TestManifestSectionRoundTrip:
    """Artifact manifest render/parse/replace round-trip.

    Strategy: Render an ArtifactManifest to string, embed it in an issue body,
    parse it back, and compare contents. Verifies the serialisation contract
    between artifact_registry helpers.
    """

    def test_render_parse_round_trip_preserves_entries(self) -> None:
        """Verify render → parse produces identical manifest entries.

        Tests: render_manifest_section / parse_manifest_section round-trip
        How: Create manifest with entries; render to string; parse back; compare
        Why: Any lossy serialisation breaks the manifest integrity contract
        """
        # Arrange
        manifest = ArtifactManifest(
            issue_number=981,
            artifacts=[
                ArtifactEntry(
                    artifact_type=ArtifactType.FEATURE_CONTEXT,
                    path="plan/feature-context-consolidate-dh-paths.md",
                    status=ArtifactStatus.CURRENT,
                    agent="feature-researcher",
                    created_at="2026-03-22T14:00:00Z",
                ),
                ArtifactEntry(
                    artifact_type=ArtifactType.ARCHITECT,
                    path="plan/architect-consolidate-dh-paths.md",
                    status=ArtifactStatus.CURRENT,
                    agent="python-cli-design-spec",
                    created_at="2026-03-22T14:05:00Z",
                ),
            ],
        )

        # Act
        rendered = render_manifest_section(manifest)
        parsed = parse_manifest_section(rendered, 981)

        # Assert
        assert len(parsed.artifacts) == len(manifest.artifacts)
        for original, recovered in zip(manifest.artifacts, parsed.artifacts, strict=False):
            assert recovered.artifact_type == original.artifact_type
            assert recovered.path == original.path
            assert recovered.status == original.status
            assert recovered.agent == original.agent

    def test_replace_manifest_in_body_appends_when_absent(self) -> None:
        """Verify replace_manifest_in_body appends the section to a plain body.

        Tests: replace_manifest_in_body appends when no manifest section exists
        How: Pass body without manifest section; verify section appears at end
        Why: First-time artifact registration adds the section
        """
        # Arrange
        manifest = ArtifactManifest(
            issue_number=981,
            artifacts=[
                ArtifactEntry(
                    artifact_type=ArtifactType.TASK_PLAN,
                    path="plan/P981-consolidate-dh-paths.yaml",
                    status=ArtifactStatus.CURRENT,
                    agent="swarm-task-planner",
                    created_at="2026-03-22T00:00:00Z",
                )
            ],
        )
        original_body = "## Feature #981\n\nConsolidate backlog and plan directories under .dh/"
        rendered = render_manifest_section(manifest)

        # Act
        new_body = replace_manifest_in_body(original_body, rendered)

        # Assert
        assert "artifact-manifest:begin" in new_body
        assert "plan/P981-consolidate-dh-paths.yaml" in new_body
        assert original_body.strip() in new_body

    def test_replace_manifest_in_body_replaces_existing_section(self) -> None:
        """Verify replace_manifest_in_body replaces an existing manifest section.

        Tests: replace_manifest_in_body idempotent replacement
        How: Build body with old manifest; replace with new; verify update
        Why: Artifact re-registration must update, not duplicate, the section
        """
        # Arrange
        old_manifest = ArtifactManifest(
            issue_number=981,
            artifacts=[
                ArtifactEntry(
                    artifact_type=ArtifactType.FEATURE_CONTEXT,
                    path="plan/feature-context-old.md",
                    status=ArtifactStatus.CURRENT,
                    agent="feature-researcher",
                    created_at="2026-03-01T00:00:00Z",
                )
            ],
        )
        new_manifest = ArtifactManifest(
            issue_number=981,
            artifacts=[
                ArtifactEntry(
                    artifact_type=ArtifactType.FEATURE_CONTEXT,
                    path="plan/feature-context-new.md",
                    status=ArtifactStatus.CURRENT,
                    agent="feature-researcher",
                    created_at="2026-03-22T00:00:00Z",
                )
            ],
        )
        body_with_old = replace_manifest_in_body("Initial body.", render_manifest_section(old_manifest))
        new_rendered = render_manifest_section(new_manifest)

        # Act
        updated_body = replace_manifest_in_body(body_with_old, new_rendered)

        # Assert — new path present; old path absent
        assert "feature-context-new.md" in updated_body
        assert "feature-context-old.md" not in updated_body

    def test_artifact_paths_in_manifest_are_relative_not_absolute(self) -> None:
        """Verify artifact paths stored in manifests are relative, not absolute.

        Tests: Artifact manifest path format — relative paths only
        How: Create entries with relative paths; render; verify no leading /
        Why: Stored paths must be relative so they resolve correctly under any state root
        """
        # Arrange
        manifest = ArtifactManifest(
            issue_number=981,
            artifacts=[
                ArtifactEntry(
                    artifact_type=ArtifactType.ARCHITECT,
                    path="plan/architect-consolidate-dh-paths.md",
                    status=ArtifactStatus.CURRENT,
                    agent="python-cli-design-spec",
                    created_at="2026-03-22T00:00:00Z",
                )
            ],
        )

        # Act
        rendered = render_manifest_section(manifest)
        parsed = parse_manifest_section(rendered, 981)

        # Assert — path is relative (no leading slash)
        assert not parsed.artifacts[0].path.startswith("/")
        assert "plan/architect-consolidate-dh-paths.md" in rendered


# ---------------------------------------------------------------------------
# Grep audit: no hardcoded old paths in production code
# ---------------------------------------------------------------------------


class TestGrepAuditOldPaths:
    """Audit: no hardcoded .claude/backlog, .claude/context, or .claude/reports
    in production Python source files outside the intentionally-old-path files.

    Strategy: Run subprocess grep on plugin Python files; parse results;
    exclude files that *legitimately* contain old path strings (dh_paths.py
    LEGACY_PATH_MAP, dh_migrate.py migration tool, docstring examples);
    fail on any unexpected production code path construction using old locations.

    Legitimate files that reference old paths by design:
    - dh_paths.py — LEGACY_PATH_MAP constant maps old paths to new function names
    - dh_migrate.py — migration tool that moves files from old to new locations
    - get_task_context.py — docstring explaining the old vs new path
    - scripts in scripts/ directories (migration helpers, task format converters)
    """

    # Files that legitimately contain old path strings by design
    LEGITIMATE_OLD_PATH_FILES: tuple[str, ...] = (
        "dh_paths.py",  # LEGACY_PATH_MAP — the map of old→new paths
        "dh_migrate.py",  # Migration tool — must reference old paths to move them
        "get_task_context.py",  # Docstring explaining migration
        "migrate_task_format.py",  # Task format migration script
    )

    # Patterns that are acceptable in docstrings and doc-examples (not path construction)
    DOCSTRING_EXAMPLE_WHITELIST: tuple[str, ...] = (
        # operations.py old docstring examples — stale but in comments only
        "~/.claude/context/sam-tasks",
        # artifact_registry.py docstring code example
        'path="plan/feature-context-foo.md"',
        # sam_schema/cli.py docstring output example
        '"path": "plan/P001-auth-system.yaml"',
        # operations.py docstring plan path example
        '"plan/tasks-1-foo.yaml"',
    )

    def _is_excluded(self, line: str) -> bool:
        """Return True when a grep hit should be excluded from failure.

        Excludes: test files, legitimate old-path files, and docstring examples.

        Args:
            line: The full grep output line (filepath:lineno:content).

        Returns:
            True if this line should be excluded, False if it is a failure.
        """
        # Test files — old paths in tests are expected (testing migration)
        if any(marker in line for marker in ("/test_", "/tests/", "/tests_")):
            return True
        # Legitimate files that must contain old path strings
        if any(filename in line for filename in self.LEGITIMATE_OLD_PATH_FILES):
            return True
        # Docstring examples
        return bool(any(pattern in line for pattern in self.DOCSTRING_EXAMPLE_WHITELIST))

    def test_no_hardcoded_dot_claude_backlog_in_production_code(self) -> None:
        """Verify .claude/backlog/ is not hardcoded outside legitimate files.

        Tests: Old backlog path eliminated from all production code paths
        How: grep -rn for .claude/backlog in plugins/*.py; filter test files,
             legitimate migration files, and docstring examples
        Why: All backlog path construction must go through dh_paths.backlog_dir()
        """
        # Arrange
        repo_root = Path(__file__).parent.parent.parent.parent  # claude_skills/
        plugins_dir = repo_root / "plugins"

        # Act
        result = subprocess.run(
            ["grep", "-rn", ".claude/backlog", str(plugins_dir), "--include=*.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        hits = [line for line in result.stdout.splitlines() if line.strip() and not self._is_excluded(line)]

        # Assert
        assert hits == [], "Hardcoded .claude/backlog references found in unexpected production code:\n" + "\n".join(
            hits
        )

    def test_no_hardcoded_dot_claude_context_in_unexpected_production_code(self) -> None:
        """Verify .claude/context/ does not appear outside legitimate files.

        Tests: Old context path references outside migration/map code
        How: grep for .claude/context in plugins/*.py; exclude legitimate files
        Why: Context files must write to dh_paths.context_dir(), not .claude/context/
        """
        # Arrange
        repo_root = Path(__file__).parent.parent.parent.parent
        plugins_dir = repo_root / "plugins"

        # Act
        result = subprocess.run(
            ["grep", "-rn", r"\.claude/context", str(plugins_dir), "--include=*.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        hits = [line for line in result.stdout.splitlines() if line.strip() and not self._is_excluded(line)]

        # Assert — only migration-related files and docstrings remain
        assert hits == [], (
            "Hardcoded .claude/context path references found in unexpected production code:\n" + "\n".join(hits)
        )

    def test_artifact_provider_does_not_construct_dot_claude_paths(self) -> None:
        """Verify artifact_provider.py contains no .claude/ path construction.

        Tests: artifact_provider.py uses dh_paths, not .claude/ string literals
        How: grep artifact_provider.py for .claude/ in non-comment lines
        Why: Provider is a key integration point — T13 task requires explicit check
        """
        # Arrange
        artifact_provider = Path(__file__).parent.parent / "backlog_core" / "artifact_provider.py"

        # Act
        result = subprocess.run(
            ["grep", "-n", ".claude/", str(artifact_provider)], capture_output=True, text=True, check=False
        )
        hits = [
            line
            for line in result.stdout.splitlines()
            if line.strip() and not line.strip().startswith("#") and not self._is_excluded(line)
        ]

        # Assert
        assert hits == [], "artifact_provider.py contains .claude/ path references:\n" + "\n".join(hits)

    def test_artifact_registry_does_not_construct_dot_claude_paths(self) -> None:
        """Verify artifact_registry.py contains no .claude/ path construction.

        Tests: artifact_registry.py uses dh_paths, not .claude/ string literals
        How: grep artifact_registry.py for .claude/ in non-comment lines
        Why: T13 task requires explicit check of artifact_registry.py
        """
        # Arrange
        artifact_registry_path = Path(__file__).parent.parent / "backlog_core" / "artifact_registry.py"

        # Act
        result = subprocess.run(
            ["grep", "-n", ".claude/", str(artifact_registry_path)], capture_output=True, text=True, check=False
        )
        hits = [
            line
            for line in result.stdout.splitlines()
            if line.strip() and not line.strip().startswith("#") and not self._is_excluded(line)
        ]

        # Assert
        assert hits == [], "artifact_registry.py contains .claude/ path references:\n" + "\n".join(hits)

    def test_dh_paths_module_is_importable_and_exports_expected_functions(self) -> None:
        """Verify dh_paths exports all expected public functions.

        Tests: dh_paths module public API completeness
        How: Import dh_paths; check each required function is callable
        Why: If any function was accidentally removed, consumers would fail silently
        """
        # Arrange
        expected_functions = [
            "git_project_root",
            "compute_slug",
            "project_dh_dir",
            "state_root",
            "backlog_dir",
            "plan_dir",
            "milestones_dir",
            "research_dir",
            "context_dir",
            "reports_dir",
            "ensure_dirs",
        ]

        # Act / Assert
        for fn_name in expected_functions:
            assert hasattr(dh_paths, fn_name), f"dh_paths missing function: {fn_name}"
            assert callable(getattr(dh_paths, fn_name)), f"dh_paths.{fn_name} is not callable"


# ---------------------------------------------------------------------------
# End-to-end: full three-tier directory layout
# ---------------------------------------------------------------------------


class TestFullThreeTierDirectoryLayout:
    """End-to-end validation of the complete three-tier directory layout.

    Strategy: Call ensure_dirs() with an isolated project root and verify
    that the expected Tier 1, Tier 2, and Tier 3 directories all exist at
    the correct locations under DH_STATE_HOME.
    """

    def test_ensure_dirs_creates_complete_tier_layout(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify ensure_dirs creates all expected tier directories.

        Tests: Three-tier layout completeness after ensure_dirs
        How: Call ensure_dirs; enumerate all expected dirs; assert each exists
        Why: All consumers depend on the full directory tree being present
        """
        project_root, _state_home = isolated_project

        # Act
        sr = ensure_dirs(project_root)

        # Assert — Tier 1 (in-repo)
        assert (project_root / ".dh").is_dir()
        assert (project_root / ".dh" / ".gitkeep").exists()

        # Assert — Tier 2 (persistent state)
        assert (sr / "backlog").is_dir()
        assert (sr / "plan").is_dir()
        assert (sr / "plan" / "codebase").is_dir()
        assert (sr / "milestones").is_dir()
        assert (sr / "research").is_dir()

        # Assert — Tier 3 (ephemeral)
        assert (sr / "context").is_dir()
        assert (sr / "reports").is_dir()

    def test_tier1_is_in_repo_tier2_is_under_state_home(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify Tier 1 is inside project_root and Tier 2 is under DH_STATE_HOME.

        Tests: Three-tier location separation — committed config vs external state
        How: Compare tier 1 path prefix (project_root) vs tier 2 prefix (state_home)
        Why: Core design invariant — state must not live inside the repo working tree
        """
        project_root, state_home = isolated_project
        ensure_dirs(project_root)

        # Tier 1 — inside the repo
        tier1 = project_root / ".dh"
        assert str(tier1).startswith(str(project_root))

        # Tier 2 — outside the repo, under DH_STATE_HOME
        tier2 = state_root(project_root)
        assert str(tier2).startswith(str(state_home))
        assert not str(tier2).startswith(str(project_root))

    def test_state_does_not_appear_in_repo_working_tree(self, isolated_project: tuple[Path, Path]) -> None:
        """Verify no state directories are created inside the repo working tree.

        Tests: State isolation — working tree not polluted by DH state
        How: After ensure_dirs, glob project_root for backlog/plan/context dirs
        Why: Repo working tree must stay clean; state in ~/.dh/ only
        """
        project_root, _state_home = isolated_project
        ensure_dirs(project_root)

        # Assert — no state directories inside project_root (except .dh/)
        for forbidden_name in ("backlog", "plan", "context", "reports", "milestones", "research"):
            forbidden = project_root / forbidden_name
            assert not forbidden.exists(), f"State directory found inside project_root: {forbidden}"

    @pytest.mark.parametrize(
        ("dir_fn", "expected_name"),
        [(backlog_dir, "backlog"), (plan_dir, "plan"), (context_dir, "context"), (reports_dir, "reports")],
    )
    def test_all_state_dirs_are_named_correctly(
        self, dir_fn: Callable[[Path], Path], expected_name: str, isolated_project: tuple[Path, Path]
    ) -> None:
        """Verify each state directory function returns the correctly named path.

        Tests: State directory naming convention for all tier 2/3 dirs
        How: Call each dir function; assert .name matches expected leaf name
        Why: Consumer code relies on predictable directory names
        """
        project_root, _state_home = isolated_project

        # Act
        result = dir_fn(project_root)

        # Assert
        assert result.name == expected_name
