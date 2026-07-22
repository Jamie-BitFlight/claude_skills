"""Artifact manifest migration helpers independent of the MCP server."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import dh_paths
from github import GithubException
from ruamel.yaml import YAML, YAMLError

from . import models as _models
from .artifact_provider import ArtifactBackend, ItemId, create_artifact_provider
from .artifact_provider_local import LocalFilesystemArtifactProvider
from .artifact_registry import ArtifactRegistry
from .models import ArtifactEntry, ArtifactStatus, ArtifactType, BacklogError, GitHubUnavailableError, Output
from .parsing import parse_backlog

_MIGRATE_ARTIFACT_REGISTRY = ArtifactRegistry()


def _get_migrate_artifact_provider() -> ArtifactBackend:
    """Create the artifact provider used by a migration run.

    Returns:
        An artifact provider, falling back to local storage when remote setup is unavailable.
    """
    repo = _models.get_default_repo()
    if not repo:
        return LocalFilesystemArtifactProvider(root_worktree=dh_paths.git_project_root())
    try:
        return create_artifact_provider(repo=repo, root_worktree=_models.get_repo_root())
    except (GitHubUnavailableError, BacklogError):
        return LocalFilesystemArtifactProvider(root_worktree=dh_paths.git_project_root())


def _migration_backlog_items() -> list[dict[str, str]]:
    """Return the minimal backlog data used for slug-based migration matching.

    Returns:
        Backlog item titles, plans, and issue numbers under migration field names.
    """
    return [{"title": item.title, "plan": item.plan, "number": item.issue} for item in parse_backlog()]


# ---------------------------------------------------------------------------
# artifact_migrate helpers
# ---------------------------------------------------------------------------


def _get_migrate_yaml() -> YAML:
    """Return a YAML parser configured for migration frontmatter.

    Returns:
        Configured ``YAML`` instance with ``preserve_quotes=True``.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


#: Filename pattern → ArtifactType mapping (ordered — first match wins).
_MIGRATE_FILENAME_PATTERNS: list[tuple[re.Pattern[str], ArtifactType]] = [
    (re.compile(r"^feature-context-(.+)\.md$"), ArtifactType.FEATURE_CONTEXT),
    (re.compile(r"^architect-(.+)\.md$"), ArtifactType.ARCHITECT),
    (re.compile(r"^P\d+-(.+)\.yaml$"), ArtifactType.TASK_PLAN),
    (re.compile(r"^T0-baseline-(.+)\.yaml$"), ArtifactType.T0_BASELINE),
    (re.compile(r"^TN-verification-(.+)\.yaml$"), ArtifactType.TN_VERIFICATION),
]

#: Pattern matching markdown files in plan/codebase/ → codebase-analysis.
_MIGRATE_CODEBASE_PATTERN = re.compile(r"^.+\.md$")


def _migrate_extract_issue(file_path: Path) -> int | None:
    """Read the ``issue`` field from YAML frontmatter or a bare YAML file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Integer issue number when found and parseable, ``None`` otherwise.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    yaml = _get_migrate_yaml()
    raw_data: object = None
    if file_path.suffix in {".yaml", ".yml"}:
        try:
            raw_data = yaml.load(text)
        except YAMLError:
            return None
    else:
        fm_match = re.match(r"^---\r?\n(.*?)\r?\n(?:---|\.\.\.)(?:\r?\n|$)", text, re.DOTALL)
        if not fm_match:
            return None
        try:
            raw_data = yaml.load(fm_match.group(1))
        except YAMLError:
            return None

    if isinstance(raw_data, dict):
        return _migrate_coerce_issue(raw_data.get("issue"))
    return None


def _migrate_coerce_issue(value: object) -> int | None:
    """Coerce a YAML value to a positive integer issue number.

    Args:
        value: Raw value from YAML (may be int, str, or None).

    Returns:
        Positive integer, or ``None``.
    """
    if value is None:
        return None
    try:
        n = int(str(value))
    except (ValueError, TypeError):
        return None
    return n if n > 0 else None


def _migrate_slug_from_path(file_path: Path) -> str:
    r"""Extract the slug from a plan filename.

    Strips known prefixes and the file extension.

    Args:
        file_path: Path object for the plan file.

    Returns:
        Slug string (e.g. ``"my-feature"``).
    """
    name = file_path.stem
    for prefix in ("feature-context-", "architect-", "T0-baseline-", "TN-verification-"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    p_match = re.match(r"^P\d+-(.+)$", name)
    if p_match:
        return p_match.group(1)
    return name


def _migrate_find_issue_via_backlog(slug: str, backlog_items: list[dict]) -> int | None:
    """Match a slug against cached backlog items to find an issue number.

    Args:
        slug: Slug string extracted from the artifact filename.
        backlog_items: List of backlog item dicts (each has ``title``,
            ``number``, and optionally ``plan`` fields).

    Returns:
        Matched GitHub issue number, or ``None``.
    """
    slug_words = set(slug.replace("-", " ").replace("_", " ").lower().split())
    for item in backlog_items:
        title: str = item.get("title", "") or ""
        plan_path: str = item.get("plan", "") or ""
        issue_number = _migrate_coerce_issue(item.get("number"))
        if issue_number is None:
            continue
        if slug in plan_path:
            return issue_number
        title_words = set(title.replace("-", " ").replace("_", " ").lower().split())
        overlap = slug_words & title_words
        if len(overlap) >= max(1, len(slug_words) // 2):
            return issue_number
    return None


def _migrate_resolve_issue(file_path: Path, backlog_items: list[dict]) -> int | None:
    """Resolve the issue number for a file via frontmatter or slug fallback.

    Args:
        file_path: Absolute path to the artifact file.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Resolved issue number, or ``None``.
    """
    issue = _migrate_extract_issue(file_path)
    if issue is None:
        slug = _migrate_slug_from_path(file_path)
        issue = _migrate_find_issue_via_backlog(slug, backlog_items)
    return issue


def _migrate_classify_plan_file(file_path: Path) -> ArtifactType | None:
    """Classify a plan file by its filename pattern.

    Args:
        file_path: Path to the file.

    Returns:
        Matching ``ArtifactType``, or ``None``.
    """
    name = file_path.name
    for pattern, artifact_type in _MIGRATE_FILENAME_PATTERNS:
        if pattern.match(name):
            return artifact_type
    return None


_MigrateCandidate = tuple[str, ArtifactType, ItemId | None, str | None]

#: Return type for candidate discovery — (actionable candidates, filtered-out count).
_MigrateDiscoveryResult = tuple[list[_MigrateCandidate], int]


def _migrate_make_candidate(
    rel: str, atype: ArtifactType, issue: int | None, issue_filter: int | None
) -> _MigrateCandidate | None:
    """Build a candidate tuple, returning ``None`` when the file is filtered out.

    When ``issue_filter`` is set, candidates whose resolved issue does not
    match are excluded entirely (counted as filtered by the caller) rather
    than included as skipped entries.  This avoids building a 500-entry
    skipped list when a specific issue is requested.

    Args:
        rel: Repo-relative path string.
        atype: Resolved artifact type.
        issue: Resolved issue number or ``None``.
        issue_filter: When set, candidates not matching this issue are
            excluded (returns ``None``).

    Returns:
        ``(rel, atype, issue, skip_reason)`` tuple, or ``None`` when filtered.
    """
    if issue_filter is not None and (issue is None or issue != issue_filter):
        return None
    if issue is None:
        return (rel, atype, issue, "no issue number found")
    return (rel, atype, issue, None)


def _migrate_scan_codebase_dir(
    codebase_dir: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan ``plan/codebase/`` for markdown codebase-analysis files.

    Args:
        codebase_dir: Absolute path to the ``plan/codebase/`` directory.
        issue_filter: When set, non-matching files are counted but not
            included in the returned candidate list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)``.
    """
    results: list[_MigrateCandidate] = []
    filtered = 0
    for child in codebase_dir.iterdir():
        if not (child.is_file() and _MIGRATE_CODEBASE_PATTERN.match(child.name)):
            continue
        rel = f"plan/codebase/{child.relative_to(codebase_dir).as_posix()}"
        issue = _migrate_resolve_issue(child, backlog_items)
        candidate = _migrate_make_candidate(rel, ArtifactType.CODEBASE_ANALYSIS, issue, issue_filter)
        if candidate is None:
            filtered += 1
        else:
            results.append(candidate)
    return results, filtered


def _migrate_scan_plan_dir(
    plan_dir: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan ``plan/`` (excluding subdirectories other than ``codebase/``).

    Args:
        plan_dir: Absolute path to the ``plan/`` directory.
        issue_filter: When set, non-matching files are counted but not
            included in the returned candidate list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)``.
    """
    results: list[_MigrateCandidate] = []
    filtered = 0
    for file_path in plan_dir.iterdir():
        if file_path.is_dir():
            if file_path.name == "codebase":
                sub_results, sub_filtered = _migrate_scan_codebase_dir(file_path, issue_filter, backlog_items)
                results.extend(sub_results)
                filtered += sub_filtered
            continue
        if not file_path.is_file():
            continue
        atype = _migrate_classify_plan_file(file_path)
        if atype is None:
            continue
        rel = f"plan/{file_path.relative_to(plan_dir).as_posix()}"
        issue = _migrate_resolve_issue(file_path, backlog_items)
        candidate = _migrate_make_candidate(rel, atype, issue, issue_filter)
        if candidate is None:
            filtered += 1
        else:
            results.append(candidate)
    return results, filtered


def _migrate_discover_candidates(
    repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan plan/ and research/ for artifact files.

    When ``issue_filter`` is set, only candidates linked to that issue are
    returned — non-matching files are counted in ``filtered_count`` instead
    of being included as skipped entries.  This prevents the caller from
    building a 500+ entry skipped list when a specific issue is requested.

    Args:
        repo_root: Absolute path to the repository root.
        issue_filter: When set, only candidates linked to this issue number
            are included in the returned list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)`` where ``candidates`` is a
        list of ``(rel_path, artifact_type, issue_number, skip_reason)``
        tuples and ``filtered_count`` is the number of files excluded by the
        issue filter.
    """
    candidates: list[_MigrateCandidate] = []
    filtered = 0

    plan_dir = dh_paths.plan_dir(repo_root)
    if plan_dir.is_dir():
        plan_candidates, plan_filtered = _migrate_scan_plan_dir(plan_dir, issue_filter, backlog_items)
        candidates.extend(plan_candidates)
        filtered += plan_filtered

    research_dir = repo_root / "research"
    if research_dir.is_dir():
        for file_path in research_dir.rglob("*.md"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(repo_root).as_posix()
            issue = _migrate_resolve_issue(file_path, backlog_items)
            candidate = _migrate_make_candidate(rel, ArtifactType.RESEARCH, issue, issue_filter)
            if candidate is None:
                filtered += 1
            else:
                candidates.append(candidate)

    return candidates, filtered


def _migrate_register_one(
    provider: ArtifactBackend, rel_path: str, artifact_type: ArtifactType, item_id: ItemId
) -> tuple[bool, str]:
    """Register a single artifact, uploading content when available.

    Idempotent — the registry upserts on (artifact_type, path).

    Args:
        provider: Initialised ``ArtifactBackend`` instance.
        rel_path: Repo-relative path string.
        artifact_type: Resolved artifact type.
        item_id: Issue number or beads string identifier.

    Returns:
        Tuple of ``(success: bool, message: str)``.
    """
    entry = ArtifactEntry(
        artifact_type=artifact_type,
        artifact_id=rel_path,
        status=ArtifactStatus.CURRENT,
        created_at=datetime.now(UTC).isoformat(),
        agent="artifact-migrate",
    )
    manifest = provider.get_manifest(item_id)
    existed = any(e.artifact_type == artifact_type and e.artifact_id == rel_path for e in manifest.artifacts)
    updated_manifest = _MIGRATE_ARTIFACT_REGISTRY.register(manifest, entry)
    provider.set_manifest(item_id, updated_manifest)

    local_content = provider.read_local_artifact_content(rel_path)
    if local_content is not None:
        provider.store_artifact_content(item_id, str(artifact_type), rel_path, local_content)
        content_note = " (content uploaded)"
    else:
        content_note = " (no local file — manifest-only)"

    action = "updated" if existed else "added"
    return True, f"{action}{content_note}"


# ---------------------------------------------------------------------------
# artifact_migrate helpers (dry-run / live-run)
# ---------------------------------------------------------------------------


def migrate_dry_run(issue_number: int | None) -> dict:
    """Discover candidates and return a preview without making any API calls.

    Args:
        issue_number: Optional issue filter passed to candidate discovery.

    Returns:
        Dict with ``dry_run``, ``would_register``, ``would_skip``,
        ``details``, and ``verify`` keys.  ``details`` contains only entries
        that would be registered or cannot be registered due to a missing
        issue number — filtered entries are counted in ``would_skip`` but not
        included individually.
    """
    repo_root = _models.get_repo_root()
    candidates, filtered_count = _migrate_discover_candidates(repo_root, issue_number, [])

    details: list[dict] = []
    would_register = 0
    would_skip = filtered_count  # filtered-out files count as skipped
    for rel_path, atype, issue, skip_reason in candidates:
        if skip_reason:
            # Include no-issue entries in details so the caller knows which
            # files could not be resolved — but do NOT include filter skips.
            details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": f"skip — {skip_reason}"})
            would_skip += 1
        else:
            details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": "would register"})
            would_register += 1

    verify = (
        f"Use artifact_list(item_id={issue_number}) to verify registered entries"
        if issue_number is not None
        else "Use artifact_list(item_id=<N>) per item to verify registered entries"
    )
    return {
        "dry_run": True,
        "would_register": would_register,
        "would_skip": would_skip,
        "details": details,
        "verify": verify,
    }


def _migrate_queue_manifest_only(
    provider: ArtifactBackend, item_id: ItemId, candidates: list[_MigrateCandidate], out: Output
) -> list[_MigrateCandidate]:
    """Append manifest-only entries (content_stored=False) to the candidate list.

    Called when ``item_id`` is provided so already-registered entries
    without uploaded content are re-processed to trigger the auto-upload path.

    Args:
        provider: Initialised provider used to read the manifest.
        item_id: Issue number or beads string identifier whose manifest to inspect.
        candidates: Existing candidate list (may be mutated by extension).
        out: Output accumulator for warnings.

    Returns:
        Extended candidate list.
    """
    try:
        manifest = provider.get_manifest(item_id)
    except (BacklogError, GithubException):
        out.warn(f"Could not read existing manifest for item {item_id!r}. Skipping manifest check.")
        return candidates

    result = list(candidates)
    for entry in manifest.artifacts:
        # Re-queue every registered entry so the auto-upload path can attempt
        # content upload for entries where no content was stored yet.
        # _migrate_register_one is idempotent (upserts on type+path).
        already_queued = any(
            rel == entry.artifact_id and atype == entry.artifact_type
            for rel, atype, _, skip_reason in candidates
            if skip_reason is None
        )
        if not already_queued:
            result.append((entry.artifact_id, entry.artifact_type, item_id, None))
            out.warn(f"Queued manifest-only entry for re-registration: {entry.artifact_id!r}")
    return result


def migrate_live_run(issue_number: int | None, out: Output) -> dict:
    """Execute the live migration against GitHub.

    Args:
        issue_number: Optional issue filter.
        out: Output accumulator (warnings written here).

    Returns:
        Dict with ``migrated``, ``skipped``, ``failed``, ``details``, and
        ``verify``.  ``details`` contains only migrated and failed entries —
        skipped entries are counted in ``skipped`` but not listed individually
        to keep the response compact.
    """
    repo_root = _models.get_repo_root()
    provider = _get_migrate_artifact_provider()

    try:
        backlog_items = _migration_backlog_items()
    except OSError:
        out.warn("Could not fetch backlog items for slug matching. Continuing without fallback.")
        backlog_items = []

    candidates, filtered_count = _migrate_discover_candidates(repo_root, issue_number, backlog_items)

    if issue_number is not None:
        candidates = _migrate_queue_manifest_only(provider, issue_number, candidates, out)

    migrated = 0
    skipped = filtered_count  # files excluded by issue filter count as skipped
    failed = 0
    run_details: list[dict] = []

    for rel_path, atype, issue, skip_reason in candidates:
        if skip_reason:
            # Count no-issue files as skipped; do NOT add to run_details to
            # avoid a 500-entry skipped list in the response.
            skipped += 1
            continue

        if issue is None:
            continue
        try:
            _ok, action_msg = _migrate_register_one(provider, rel_path, atype, issue)
            migrated += 1
            run_details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": action_msg})
        except (BacklogError, GithubException, OSError) as exc:
            failed += 1
            run_details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": f"FAILED: {exc}"})

    verify = (
        f"Use artifact_read(item_id={issue_number}, artifact_type='<type>') "
        f"or artifact_list(item_id={issue_number}) to verify"
        if issue_number is not None
        else "Use artifact_list(item_id=<N>) per item to verify registered entries"
    )
    return {"migrated": migrated, "skipped": skipped, "failed": failed, "details": run_details, "verify": verify}
