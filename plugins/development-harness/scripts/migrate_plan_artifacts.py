#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml",
# ]
# ///
"""Migrate existing plan artifacts into the GitHub Issue artifact manifest system.

Scans ~/.dh/projects/-home-ubuntulinuxqa2-repos-claude_skills/plan/ for
artifact files, classifies them by filename pattern, resolves the linked
GitHub issue number, then registers each artifact via GitHubArtifactProvider.

Usage:
    uv run scripts/migrate_plan_artifacts.py --dry-run   # preview only
    uv run scripts/migrate_plan_artifacts.py             # live run

Output written to /tmp/artifact-migration-results.txt in addition to stdout.
"""

from __future__ import annotations

import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

# ---------------------------------------------------------------------------
# Bootstrap: add plugin root to sys.path so backlog_core is importable
# ---------------------------------------------------------------------------

_PLUGIN_ROOT = Path(__file__).parent.parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from backlog_core import models as _models
from backlog_core.artifact_provider import GitHubArtifactProvider
from backlog_core.artifact_registry import ArtifactRegistry
from backlog_core.models import ArtifactEntry, ArtifactStatus, ArtifactType

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from ruamel.yaml import YAML
except ImportError:
    print("ERROR: ruamel.yaml not available. Run: uv add ruamel.yaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_DIR = "/home/ubuntulinuxqa2/repos/claude_skills"
DH_STATE_ROOT = Path.home() / ".dh" / "projects" / "-home-ubuntulinuxqa2-repos-claude_skills"
PLAN_DIR = DH_STATE_ROOT / "plan"
RESULTS_FILE = Path(tempfile.gettempdir()) / "artifact-migration-results.txt"

# Filename → ArtifactType patterns (first match wins)
_FILENAME_PATTERNS: list[tuple[re.Pattern[str], ArtifactType]] = [
    (re.compile(r"^feature-context-(.+)\.md$"), ArtifactType.FEATURE_CONTEXT),
    (re.compile(r"^architect-(.+)\.md$"), ArtifactType.ARCHITECT),
    (re.compile(r"^P\d+-(.+)\.yaml$"), ArtifactType.TASK_PLAN),
    (re.compile(r"^T0-baseline-(.+)\.yaml$"), ArtifactType.T0_BASELINE),
    (re.compile(r"^TN-verification-(.+)\.yaml$"), ArtifactType.TN_VERIFICATION),
    (re.compile(r"^milestone-\d+-dispatch\.yaml$"), ArtifactType.DISPATCH_PLAN),
]

# Filenames / suffixes / prefixes to skip entirely
_SKIP_SUFFIXES = {".backup", ".original"}
_SKIP_SUFFIX_PARTS = {".pre-migration-backup", ".md.original"}
_SKIP_NAME_PREFIXES = (
    "CONTEXT_MANIFEST-",
    "alignment-review-",
    "audit-",
    "compatibility-",
    "D1-",
    "integration-verification-",
    "plan-dh-",
    "taxonomy-",
    "test-",
    "validation-",
    "dh-doc-audit-",
    "T1-",
)
_SKIP_SUBDIRS = {
    "research",
    "tasks-1-plugin-linter",
    "tasks-11-merge-same-file-tasks",
    "tasks-15-fix-multi-yaml-fence",
    "tasks-15-process-quality-discipline",
    "tasks-16-audit-tests-limitation-patterns",
    "tasks-4-validate-orchestrator-discipline",
    "tasks-6-plan-artifact-lifecycle",
}

# Agent names by artifact type
_AGENT_BY_TYPE: dict[ArtifactType, str] = {
    ArtifactType.FEATURE_CONTEXT: "feature-researcher",
    ArtifactType.ARCHITECT: "python-cli-design-spec",
    ArtifactType.TASK_PLAN: "swarm-task-planner",
    ArtifactType.T0_BASELINE: "t0-baseline-capture",
    ArtifactType.TN_VERIFICATION: "tn-verification-gate",
    ArtifactType.CODEBASE_ANALYSIS: "codebase-analyzer",
    ArtifactType.DISPATCH_PLAN: "swarm-task-planner",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_yaml = YAML()
_yaml.preserve_quotes = True


def _should_skip(file_path: Path) -> str | None:
    """Return skip reason string, or None if file should be processed."""
    name = file_path.name

    # Suffix-based skips
    for suffix in _SKIP_SUFFIXES:
        if name.endswith(suffix):
            return f"skipped suffix {suffix!r}"
    for part in _SKIP_SUFFIX_PARTS:
        if part in name:
            return f"skipped suffix part {part!r}"

    # Prefix-based skips
    for prefix in _SKIP_NAME_PREFIXES:
        if name.startswith(prefix):
            return f"skipped prefix {prefix!r}"

    return None


def _classify(file_path: Path) -> ArtifactType | None:
    """Return ArtifactType for a plan-dir file, or None if not recognized."""
    name = file_path.name
    for pattern, atype in _FILENAME_PATTERNS:
        if pattern.match(name):
            return atype
    return None


def _classify_codebase(file_path: Path) -> ArtifactType | None:
    """Classify a file inside plan/codebase/ — all .md files are codebase-analysis.

    Returns:
        ArtifactType.CODEBASE_ANALYSIS for .md files, None otherwise.
    """
    if file_path.suffix == ".md":
        return ArtifactType.CODEBASE_ANALYSIS
    return None


def _extract_issue_from_file(file_path: Path) -> int | None:
    """Read issue number from YAML frontmatter or bare YAML.

    Returns:
        Positive issue number if found, None otherwise.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    raw_data: object = None
    if file_path.suffix in {".yaml", ".yml"}:
        try:
            raw_data = _yaml.load(text)
        except Exception:  # noqa: BLE001
            return None
    else:
        fm_match = re.match(r"^---\r?\n(.*?)\r?\n(?:---|\.\.\.)(?:\r?\n|$)", text, re.DOTALL)
        if fm_match:
            try:
                raw_data = _yaml.load(fm_match.group(1))
            except Exception:  # noqa: BLE001
                return None

    if isinstance(raw_data, dict):
        for key in ("github_issue", "issue", "issue_number"):
            val = raw_data.get(key)
            if val is not None:
                try:
                    n = int(str(val))
                    if n > 0:
                        return n
                except (ValueError, TypeError):
                    pass
    return None


def _slug_from_path(file_path: Path) -> str:
    """Extract feature slug from filename.

    Returns:
        Feature slug string extracted from the filename stem.
    """
    name = file_path.stem
    for prefix in ("feature-context-", "architect-", "T0-baseline-", "TN-verification-"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    p_match = re.match(r"^P\d+-(.+)$", name)
    if p_match:
        return p_match.group(1)
    m_match = re.match(r"^milestone-\d+-dispatch$", name)
    if m_match:
        return ""
    return name


def _find_issue_via_slug(slug: str, backlog_items: list[dict]) -> int | None:
    """Fuzzy-match slug against backlog item titles/plan paths.

    Returns:
        Matched issue number if a backlog item matches the slug, None otherwise.
    """
    if not slug:
        return None
    slug_words = set(slug.replace("-", " ").replace("_", " ").lower().split())
    for item in backlog_items:
        title: str = item.get("title", "") or ""
        plan_path: str = item.get("plan", "") or ""
        issue_number = item.get("number")
        if issue_number is None:
            continue
        try:
            n = int(str(issue_number))
        except (ValueError, TypeError):
            continue
        if n <= 0:
            continue
        if slug in plan_path:
            return n
        title_words = set(title.replace("-", " ").replace("_", " ").lower().split())
        overlap = slug_words & title_words
        if len(overlap) >= max(1, len(slug_words) // 2):
            return n
    return None


def _resolve_issue(file_path: Path, backlog_items: list[dict]) -> int | None:
    """Resolve issue number: frontmatter first, then sibling files, then slug match.

    Returns:
        Resolved issue number or None if no match found.
    """
    issue = _extract_issue_from_file(file_path)
    if issue is not None:
        return issue

    # For task-plans, check sibling feature-context or architect files
    stem = file_path.stem
    p_match = re.match(r"^P\d+-(.+)$", stem)
    if p_match:
        slug = p_match.group(1)
        for sibling_prefix in ("feature-context-", "architect-"):
            sibling = file_path.parent / f"{sibling_prefix}{slug}.md"
            if sibling.exists():
                issue = _extract_issue_from_file(sibling)
                if issue is not None:
                    return issue

    slug = _slug_from_path(file_path)
    return _find_issue_via_slug(slug, backlog_items)


# ---------------------------------------------------------------------------
# Candidate discovery
# ---------------------------------------------------------------------------


class Candidate(NamedTuple):
    """A discovered plan artifact candidate."""

    file_path: Path
    artifact_type: ArtifactType
    rel_path: str  # relative to DH_STATE_ROOT, e.g. "plan/feature-context-foo.md"
    issue: int | None
    skip_reason: str | None


def discover_candidates(backlog_items: list[dict]) -> list[Candidate]:
    """Scan plan/ directory and return all artifact candidates.

    Returns:
        List of Candidate namedtuples representing discovered plan artifacts.
    """
    candidates: list[Candidate] = []

    if not PLAN_DIR.is_dir():
        print(f"ERROR: plan directory not found: {PLAN_DIR}", file=sys.stderr)
        return candidates

    for file_path in PLAN_DIR.iterdir():
        if file_path.is_dir():
            if file_path.name == "codebase":
                for child in file_path.iterdir():
                    if not (child.is_file() and child.suffix == ".md"):
                        continue
                    skip = _should_skip(child)
                    rel_path = child.relative_to(DH_STATE_ROOT).as_posix()
                    if skip:
                        candidates.append(Candidate(child, ArtifactType.CODEBASE_ANALYSIS, rel_path, None, skip))
                        continue
                    atype = _classify_codebase(child)
                    if atype is None:
                        continue
                    issue = _resolve_issue(child, backlog_items)
                    candidates.append(Candidate(child, atype, rel_path, issue, None))
            # Skip all other subdirectories (tasks-* etc)
            continue

        if not file_path.is_file():
            continue

        skip = _should_skip(file_path)
        rel_path = file_path.relative_to(DH_STATE_ROOT).as_posix()

        if skip:
            atype = _classify(file_path) or ArtifactType.FEATURE_CONTEXT
            candidates.append(Candidate(file_path, atype, rel_path, None, skip))
            continue

        atype = _classify(file_path)
        if atype is None:
            # Not a recognized artifact pattern — silently skip
            continue

        issue = _resolve_issue(file_path, backlog_items)
        candidates.append(Candidate(file_path, atype, rel_path, issue, None))

    return candidates


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_one(
    provider: GitHubArtifactProvider | None, registry: ArtifactRegistry, candidate: Candidate, dry_run: bool
) -> str:
    """Register a single artifact.

    Returns:
        Human-readable outcome string describing the registration result.
    """
    assert candidate.issue is not None  # caller must check  # noqa: S101

    agent = _AGENT_BY_TYPE.get(candidate.artifact_type, "migration-script")
    entry = ArtifactEntry(
        artifact_type=candidate.artifact_type,
        path=candidate.rel_path,
        status=ArtifactStatus.CURRENT,
        created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        agent=agent,
    )

    # Read content from local file
    content: str | None = None
    try:
        content = candidate.file_path.read_text(encoding="utf-8")
    except OSError as exc:
        content = None
        content_note = f" [content read failed: {exc}]"
    else:
        content_note = f" [content: {len(content)} chars]"

    if dry_run:
        return f"DRY-RUN: would register {candidate.artifact_type} -> issue #{candidate.issue}{content_note}"

    # Get current manifest, upsert entry, persist
    assert provider is not None  # noqa: S101 — guarded by dry_run early return above
    manifest = provider.get_manifest(candidate.issue)
    updated = registry.register(manifest, entry)
    provider.set_manifest(candidate.issue, updated)

    existed = any(
        e.artifact_type == candidate.artifact_type and e.path == candidate.rel_path for e in manifest.artifacts
    )
    action = "updated" if existed else "added"

    # Store content as GitHub comment
    if content is not None:
        provider.store_artifact_content(candidate.issue, str(candidate.artifact_type), candidate.rel_path, content)
        return f"{action.upper()} manifest entry + stored content ({len(content)} chars) -> issue #{candidate.issue}"
    return f"{action.upper()} manifest entry only (no local content){content_note} -> issue #{candidate.issue}"


# ---------------------------------------------------------------------------
# Main helpers
# ---------------------------------------------------------------------------


def _load_backlog_items() -> list[dict]:
    """Load backlog item frontmatter dicts from the DH state backlog directory.

    Returns:
        List of frontmatter dicts parsed from backlog *.md files.
    """
    backlog_dir = DH_STATE_ROOT / "backlog"
    items: list[dict] = []
    if not backlog_dir.is_dir():
        return items
    fm_yaml = YAML()
    for bf in backlog_dir.glob("*.md"):
        try:
            text = bf.read_text(encoding="utf-8")
            fm_match = re.match(r"^---\r?\n(.*?)\r?\n(?:---|\.\.\.)(?:\r?\n|$)", text, re.DOTALL)
            if fm_match:
                data = fm_yaml.load(fm_match.group(1))
                if isinstance(data, dict):
                    items.append(data)
        except Exception:  # noqa: BLE001, S110
            pass
    return items


def _log_candidate_summary(
    log: Callable[[str], None], actionable: list[Candidate], no_issue: list[Candidate], skipped: list[Candidate]
) -> None:
    """Log candidate tally and list files with no resolved issue."""
    log(f"Actionable (have issue): {len(actionable)}")
    log(f"No issue found (will skip): {len(no_issue)}")
    log(f"Explicitly skipped: {len(skipped)}")
    log("")

    if no_issue:
        log("--- Files with no issue resolved ---")
        for c in no_issue:
            log(f"  NO-ISSUE: {c.rel_path} [{c.artifact_type}]")
        log("")


def _run_registrations(
    log: Callable[[str], None],
    actionable: list[Candidate],
    provider: GitHubArtifactProvider | None,
    registry: ArtifactRegistry,
    dry_run: bool,
) -> tuple[int, int]:
    """Iterate actionable candidates and register each artifact.

    Returns:
        Tuple of (registered_count, failed_count).
    """
    registered = 0
    failed = 0
    log("--- Registration ---")
    for c in actionable:
        assert c.issue is not None  # ensured by caller filter  # noqa: S101
        try:
            if dry_run:
                outcome = register_one(None, registry, c, dry_run=True)  # type: ignore[arg-type]
            else:
                assert provider is not None  # noqa: S101
                outcome = register_one(provider, registry, c, dry_run=False)
            log(f"  {c.rel_path}: {outcome}")
            registered += 1
        except Exception as exc:  # noqa: BLE001
            log(f"  FAILED: {c.rel_path}: {exc}")
            failed += 1
    return registered, failed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(dry_run: bool) -> None:
    """Run migration and write results to stdout and results file."""
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    mode = "DRY-RUN" if dry_run else "LIVE"
    log(f"=== Artifact Migration ({mode}) ===")
    log(f"Plan dir: {PLAN_DIR}")
    log(f"Timestamp: {datetime.now(UTC).isoformat()}")
    log("")

    _models.init(project_dir=PROJECT_DIR)
    log(f"Repo: {_models.DEFAULT_REPO}")
    log(f"Repo root: {_models.get_repo_root()}")
    log("")

    log("Fetching backlog items for slug matching...")
    backlog_items = _load_backlog_items()
    log(f"Loaded {len(backlog_items)} backlog items")
    log("")

    candidates = discover_candidates(backlog_items)
    log(f"Discovered {len(candidates)} candidate files")
    log("")

    actionable = [c for c in candidates if c.skip_reason is None and c.issue is not None]
    no_issue = [c for c in candidates if c.skip_reason is None and c.issue is None]
    skipped = [c for c in candidates if c.skip_reason is not None]

    _log_candidate_summary(log, actionable, no_issue, skipped)

    registry = ArtifactRegistry()
    provider: GitHubArtifactProvider | None = None
    if not dry_run:
        provider = GitHubArtifactProvider(repo=_models.DEFAULT_REPO, root_worktree=DH_STATE_ROOT)

    registered_count, failed_count = _run_registrations(log, actionable, provider, registry, dry_run)

    log("")
    log("=== Summary ===")
    log(f"REGISTERED: {registered_count}")
    log(f"SKIPPED (no issue): {len(no_issue)}")
    log(f"SKIPPED (pattern): {len(skipped)}")
    log(f"FAILED: {failed_count}")

    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"\nResults written to {RESULTS_FILE}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    main(dry_run=dry_run)
