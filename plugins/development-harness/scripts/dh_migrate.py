#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.2",
#   "ruamel.yaml>=0.18.0",
#   "pydantic>=2.12.3",
#   "pygithub>=2.8.1",
#   "gitpython>=3.1.0",
#   "marko>=2.0.0",
# ]
# ///
"""dh_migrate — migrate project state from legacy .claude/ layout to ~/.dh/.

Commands
--------
verify              Report current layout state without modifying anything.
migrate             Move files from the old layout to the new one.
register-artifacts  Register plan artifacts in their backlog item manifests.

Usage
-----
    uv run plugins/development-harness/scripts/dh_migrate.py verify
    uv run plugins/development-harness/scripts/dh_migrate.py migrate --dry-run
    uv run plugins/development-harness/scripts/dh_migrate.py migrate
    uv run plugins/development-harness/scripts/dh_migrate.py register-artifacts
    uv run plugins/development-harness/scripts/dh_migrate.py register-artifacts --dry-run
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypeGuard

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if TYPE_CHECKING:
    from backlog_core.artifact_provider import GitHubArtifactProvider


def _is_str_dict(obj: object) -> TypeGuard[dict[str, object]]:
    """Return True when *obj* is a dict with exclusively string keys."""
    return isinstance(obj, dict) and all(isinstance(k, str) for k in obj)


# ---------------------------------------------------------------------------
# Bootstrap: make the development-harness package importable from within the
# PEP 723 isolated environment.  The script lives at:
#   plugins/development-harness/scripts/dh_migrate.py
# so parents[1] is plugins/development-harness/.
# ---------------------------------------------------------------------------
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

import dh_paths
import typer
from ruamel.yaml import YAML, YAMLError

from cli_output import err, output_json

app = typer.Typer(
    name="dh_migrate", help="Migrate DH project state from legacy .claude/ layout to ~/.dh/.", no_args_is_help=True
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Mapping: old repo-relative path (relative to project root) → dh_paths fn name
_OLD_TO_NEW: dict[str, str] = {
    ".claude/backlog": "backlog_dir",
    ".claude/context": "context_dir",
    ".claude/reports": "reports_dir",
    "plan": "plan_dir",
}


def _project_root() -> Path:
    """Resolve git project root; exit with message on failure.

    Returns:
        Absolute path to the git project root.

    Raises:
        typer.Exit: With code 1 if git is unavailable or not in a repo.
    """
    try:
        return dh_paths.git_project_root()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        err(f"Cannot determine git project root: {exc}")


def _old_dirs(project_root: Path) -> dict[str, Path]:
    """Return mapping of old-relative-path → absolute path for each legacy directory."""
    return {old: project_root / old for old in _OLD_TO_NEW}


def _detect_layout(project_root: Path) -> dict[str, bool]:
    """Return presence flags for old and new layout indicators.

    Returns:
        Dict with keys ``old_present`` and ``new_present``.
    """
    old_present = any((project_root / old).exists() for old in _OLD_TO_NEW)
    new_present = dh_paths.backlog_dir(project_root).exists()
    return {"old_present": old_present, "new_present": new_present}


# ---------------------------------------------------------------------------
# verify command
# ---------------------------------------------------------------------------


@app.command()
def verify() -> None:
    """Scan the current project and report layout state.

    Exits 0 if the project is on the new layout (or already migrated).
    Exits 1 if old layout directories are detected (action required).
    """
    project_root = _project_root()
    slug = dh_paths.compute_slug(project_root)
    state = _detect_layout(project_root)

    old_layout = [
        {"label": label, "path": str(old_path), "present": old_path.exists()}
        for label, old_path in _old_dirs(project_root).items()
    ]
    new_backlog = dh_paths.backlog_dir(project_root)
    new_layout = {"path": str(new_backlog), "present": state["new_present"]}

    if state["old_present"] and not state["new_present"]:
        status = "action_required"
    elif state["old_present"] and state["new_present"]:
        status = "partial_migration"
    else:
        status = "migrated"

    output_json({"project_slug": slug, "status": status, "old_layout": old_layout, "new_layout": new_layout})

    if status in {"action_required", "partial_migration"}:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# migrate command
# ---------------------------------------------------------------------------


@app.command()
def migrate(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be moved without making any changes.")
    ] = False,
) -> None:
    """Move state directories from the old layout to the new DH layout.

    Moves .claude/backlog/, .claude/context/, .claude/reports/, and plan/
    to ~/.dh/projects/{slug}/. Removes old directories only when empty
    after migration. Creates .dh/.gitkeep in-repo. Does NOT touch
    .claude/CLAUDE.md or other project config files.

    Use --dry-run to preview without making changes.
    """
    project_root = _project_root()
    state = _detect_layout(project_root)
    state_root = dh_paths.state_root(project_root)

    if not state["old_present"]:
        output_json({
            "project_root": project_root,
            "state_root": state_root,
            "status": "nothing_to_migrate",
            "moves": [],
        })
        return

    # Build move plan
    move_plan: list[tuple[Path, Path]] = []  # (src, dest)
    new_fn_map = {
        ".claude/backlog": dh_paths.backlog_dir,
        ".claude/context": dh_paths.context_dir,
        ".claude/reports": dh_paths.reports_dir,
        "plan": dh_paths.plan_dir,
    }
    for label, fn in new_fn_map.items():
        src = project_root / label
        if src.exists():
            dest = fn(project_root)
            move_plan.append((src, dest))

    if dry_run:
        moves = [{"source": src, "destination": dest} for src, dest in move_plan]
        output_json({"project_root": project_root, "state_root": state_root, "status": "dry_run", "moves": moves})
        return

    # Execute moves
    errors: list[str] = []
    executed_moves: list[dict[str, object]] = []
    for src, dest in move_plan:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # Merge: copy individual items from src into existing dest
                merged_items = _merge_dir(src, dest)
            else:
                shutil.move(str(src), str(dest))
                merged_items = []
        except OSError as exc:
            errors.append(f"Failed to move {src} → {dest}: {exc}")
        else:
            executed_moves.append({"source": src, "destination": dest, "merged_items": merged_items})

    if errors:
        output_json({
            "project_root": project_root,
            "state_root": state_root,
            "status": "error",
            "moves": executed_moves,
            "errors": errors,
        })
        raise typer.Exit(code=1)

    # Remove old empty directories (only if now empty)
    removed_dirs, skipped_dirs = _remove_empty_old_dirs(project_root)

    # Create .dh/.gitkeep in-repo (Tier 1 marker)
    dh_dir = dh_paths.project_dh_dir(project_root)
    dh_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = dh_dir / ".gitkeep"
    gitkeep_created = not gitkeep.exists()
    gitkeep.touch(exist_ok=True)

    output_json({
        "project_root": project_root,
        "state_root": state_root,
        "status": "success",
        "moves": executed_moves,
        "removed_empty_dirs": removed_dirs,
        "skipped_non_empty_dirs": skipped_dirs,
        "gitkeep_created": gitkeep_created,
        "gitkeep_path": gitkeep,
        "artifact_manifest_instructions": _artifact_manifest_instructions(project_root),
    })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _merge_dir(src: Path, dest: Path) -> list[str]:
    """Copy all items from src into dest, then remove src.

    Args:
        src: Source directory.
        dest: Destination directory (must already exist).

    Returns:
        Names of the items merged into *dest*.
    """
    merged: list[str] = []
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(target), dirs_exist_ok=True)
        else:
            shutil.copy2(str(item), str(target))
        merged.append(item.name)
    shutil.rmtree(src)
    return merged


def _remove_empty_old_dirs(project_root: Path) -> tuple[list[str], list[str]]:
    """Remove legacy directories if they are now empty.

    Does NOT remove .claude/ itself — other config files (CLAUDE.md, rules/,
    hooks/) may still live there.

    Args:
        project_root: Absolute project root path.

    Returns:
        Tuple of ``(removed_paths, skipped_non_empty_paths)``.
    """
    # Order matters: remove children before parents
    candidates = [
        project_root / ".claude" / "backlog",
        project_root / ".claude" / "context",
        project_root / ".claude" / "reports",
        project_root / "plan",
    ]
    removed: list[str] = []
    skipped: list[str] = []
    for candidate in candidates:
        if candidate.exists() and not any(candidate.iterdir()):
            candidate.rmdir()
            removed.append(str(candidate))
        elif candidate.exists():
            skipped.append(str(candidate))
    return removed, skipped


def _artifact_manifest_instructions(project_root: Path) -> dict[str, object]:
    """Build artifact manifest update instructions for the calling agent.

    Artifact manifests are stored in GitHub Issue bodies and managed by the
    backlog MCP server.  Path updates must be applied via the MCP
    ``artifact_register`` tool — this CLI script cannot call MCP tools directly,
    so this returns actionable, structured instructions for the caller to act
    on using the MCP tools after migration.

    Args:
        project_root: Absolute project root path.

    Returns:
        Dict describing the required follow-up steps.
    """
    return {
        "warning": "Artifact manifests in GitHub Issue bodies may contain old path prefixes.",
        "steps": [
            "artifact_list(item_id=N) — find entries with old prefixes",
            (
                "artifact_register(item_id=N, artifact_type=T, artifact_id=<new_relative_path>, content=<artifact body>)"
                " — re-register with new path"
            ),
        ],
        "old_prefixes": [".claude/backlog/", ".claude/context/", ".claude/reports/", "plan/"],
        "new_base_directory": dh_paths.state_root(project_root),
        "note": (
            "New relative paths are relative to the state root shown above. Filenames are "
            "unchanged; only the resolution base changes (e.g. plan/P981-foo.yaml stays "
            "plan/P981-foo.yaml)."
        ),
    }


# ---------------------------------------------------------------------------
# register-artifacts command
# ---------------------------------------------------------------------------

# Filename patterns: (compiled regex, artifact_type string)
_ARTIFACT_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^feature-context-(.+)\.md$"), "feature-context"),
    (re.compile(r"^architect-(.+)\.md$"), "architect"),
    (re.compile(r"^P\d+-(.+)\.yaml$"), "task-plan"),
    (re.compile(r"^T0-baseline-(.+)\.yaml$"), "T0-baseline"),
    (re.compile(r"^TN-verification-(.+)\.yaml$"), "TN-verification"),
    (re.compile(r"^milestone-(\d+)-dispatch\.yaml$"), "dispatch-plan"),
]

# File name prefixes and patterns to skip (exact prefix or fnmatch-style).
_SKIP_PREFIXES: tuple[str, ...] = (
    ".backup",
    ".original",
    ".pre-migration-backup",
    "tasks-",
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

# Subdirectories inside plan/ to skip entirely.
_SKIP_SUBDIRS: frozenset[str] = frozenset({"research"})


def _should_skip_file(filename: str) -> bool:
    """Return True when *filename* matches a skip rule.

    Args:
        filename: Bare filename (no directory component).

    Returns:
        True when the file should be excluded from artifact registration.
    """
    for suffix in (".backup", ".original", ".pre-migration-backup"):
        if filename.endswith(suffix):
            return True
    return any(filename.startswith(prefix) for prefix in _SKIP_PREFIXES)


def _detect_artifact_type(filename: str, parent_name: str) -> str | None:
    """Classify *filename* into an artifact type string.

    Checks the ``codebase/`` subdirectory rule first, then the filename
    patterns.  Returns ``None`` when no pattern matches (file should be
    skipped).

    Args:
        filename: Bare filename of the artifact file.
        parent_name: Name of the immediate parent directory (e.g. ``"codebase"``
            when the file is inside ``plan/codebase/``).

    Returns:
        Artifact type string, or ``None`` when the file does not match any
        known pattern.
    """
    if parent_name == "codebase":
        return "codebase-analysis"
    for pattern, artifact_type in _ARTIFACT_TYPE_PATTERNS:
        if pattern.match(filename):
            return artifact_type
    return None


def _read_issue_number_from_yaml(path: Path) -> int | None:
    """Attempt to read an issue number from YAML top-level fields.

    Checks ``github_issue``, ``issue``, and ``issue_number`` keys using
    ruamel.yaml.  Returns ``None`` on any parse error or when none of the
    fields is present.

    Args:
        path: Absolute path to the YAML file.

    Returns:
        Positive integer issue number, or ``None``.
    """
    try:
        yaml = YAML(typ="safe")
        data = yaml.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return None
    else:
        if not isinstance(data, dict):
            return None
        for key in ("github_issue", "issue", "issue_number"):
            val = data.get(key)
            if isinstance(val, int) and val > 0:
                return val
        return None


def _read_issue_number_from_markdown_frontmatter(path: Path) -> int | None:
    """Parse YAML frontmatter from a Markdown file and extract issue number.

    Looks for ``issue`` or ``github_issue`` frontmatter keys.  Returns
    ``None`` when frontmatter is absent or unparseable.

    Args:
        path: Absolute path to the Markdown file.

    Returns:
        Positive integer issue number, or ``None``.
    """
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return None
        end = text.find("\n---", 3)
        if end == -1:
            return None
        fm_text = text[3:end].strip()
        yaml = YAML(typ="safe")
        data = yaml.load(fm_text)
    except (OSError, YAMLError):
        return None
    else:
        if not isinstance(data, dict):
            return None
        for key in ("issue", "github_issue"):
            val = data.get(key)
            if isinstance(val, int) and val > 0:
                return val
        return None


def _infer_issue_from_plan_filename(filename: str, backlog_dir: Path) -> int | None:
    """For ``P{NNN}-{slug}.yaml`` files, check whether NNN is a backlog issue.

    Checks whether a backlog file exists at *backlog_dir* whose filename
    contains the numeric component NNN, treating NNN as the issue number.

    Args:
        filename: Bare filename, e.g. ``P981-foo.yaml``.
        backlog_dir: Absolute path to the ``backlog/`` directory.

    Returns:
        NNN as an integer when a matching backlog file exists, else ``None``.
    """
    m = re.match(r"^P(\d+)-", filename)
    if not m:
        return None
    candidate = int(m.group(1))
    if not backlog_dir.is_dir():
        return None
    # Backlog files are named like ``{issue_number}-*.md`` or contain the number.
    for f in backlog_dir.iterdir():
        if f.is_file() and f.name.startswith(f"{candidate}-"):
            return candidate
    return None


# Priority prefixes used in backlog filenames that must be stripped before slug comparison.
_BACKLOG_PRIORITY_PREFIXES: tuple[str, ...] = (
    "p0-",
    "p1-",
    "p2-",
    "completed-",
    "complete-",
    "idea-",
    "ideas-",
    "medium-",
)

# Plan filename P{NNN} numbers at or above this threshold are treated as GitHub
# issue numbers directly (not plan-internal sequence numbers).
_HIGH_NUMBER_PLAN_PREFIX_THRESHOLD = 500


def _strip_backlog_priority_prefix(stem: str) -> str:
    """Remove the priority prefix (``p0-``, ``p1-``, etc.) from a backlog filename stem.

    Args:
        stem: Filename stem without extension, e.g. ``p0-some-feature``.

    Returns:
        Stem with priority prefix removed, or the original stem if no prefix matches.
    """
    for prefix in _BACKLOG_PRIORITY_PREFIXES:
        if stem.startswith(prefix):
            return stem[len(prefix) :]
    return stem


def _parse_backlog_file_data(text: str) -> dict[str, object] | None:
    """Parse YAML frontmatter from a backlog ``.md`` file using ruamel.yaml.

    Args:
        text: Full file text.

    Returns:
        Parsed YAML dict, or ``None`` when frontmatter is absent or unparseable.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_text = text[3:end].strip()
    yaml = YAML(typ="safe")
    data = yaml.load(fm_text)
    return data if isinstance(data, dict) else None


def _extract_issue_int_from_backlog_data(data: dict[str, object]) -> int | None:
    """Pull the issue number from a parsed backlog frontmatter dict.

    Checks ``metadata.issue`` first, then top-level ``issue``.
    Accepts both ``'#NNN'`` and ``'NNN'`` string forms.

    Args:
        data: Parsed YAML frontmatter dict from a backlog file.

    Returns:
        Positive integer issue number, or ``None``.
    """
    meta_raw = data.get("metadata")
    meta: dict[str, object] = meta_raw if _is_str_dict(meta_raw) else {}
    issue_raw: object = meta.get("issue") or data.get("issue")
    if issue_raw is None:
        return None
    issue_str = str(issue_raw).lstrip("#").strip()
    if not issue_str.isdigit():
        return None
    issue_number = int(issue_str)
    return issue_number if issue_number > 0 else None


def _extract_plan_field_slug(data: dict[str, object]) -> str | None:
    """Extract the artifact slug from the backlog item's ``plan`` frontmatter field.

    The ``plan`` field contains a relative path like
    ``plan/P979-agent-profile-mcp-tool.yaml`` or
    ``plan/tasks-1-backlog-cli-dedup.md``.  This function extracts the
    filename stem and applies :func:`_extract_artifact_slug` to derive the
    feature slug portion (e.g. ``agent-profile-mcp-tool`` or
    ``backlog-cli-dedup``).

    Args:
        data: Parsed YAML frontmatter dict from a backlog file.

    Returns:
        Extracted slug string, or ``None`` when not derivable.
    """
    meta_raw = data.get("metadata")
    meta: dict[str, object] = meta_raw if _is_str_dict(meta_raw) else {}
    plan_raw = meta.get("plan") or data.get("plan")
    if plan_raw is None:
        return None
    plan_str = str(plan_raw).strip()
    # Extract bare filename from path like "plan/P979-agent-profile-mcp-tool.yaml".
    plan_filename = plan_str.rsplit("/", 1)[-1]
    return _extract_artifact_slug(plan_filename)


def _build_slug_index(backlog_dir: Path) -> dict[str, int]:
    """Scan the backlog directory and build a ``slug → issue_number`` map.

    Reads every ``.md`` file in *backlog_dir*, parses its YAML frontmatter
    using ruamel.yaml, and extracts the issue number from the
    ``metadata.issue`` field (stored as ``'#NNN'`` or ``'NNN'``).  Three slug
    keys are stored per item:

    - ``title_to_slug(name)`` — canonical slug derived from the item title.
    - Filename stem after stripping the priority prefix — secondary fallback
      when the canonical slug differs from the filename.
    - Plan field slug — extracted from the ``plan`` frontmatter field path
      (e.g. ``plan/P979-agent-profile-mcp-tool.yaml`` → ``agent-profile-mcp-tool``).
      This is the primary way to match ``P{NNN}-{slug}.yaml`` plan files whose
      NNN is below the high-number threshold.

    Args:
        backlog_dir: Absolute path to the ``~/.dh/…/backlog/`` directory.

    Returns:
        Mapping from slug string to positive integer issue number.  Files
        without a parseable issue number are silently skipped.
    """
    from backlog_core.parsing import title_to_slug  # ruff: ignore[import-outside-top-level]

    index: dict[str, int] = {}
    if not backlog_dir.is_dir():
        return index

    for md_file in backlog_dir.glob("*.md"):
        try:
            data = _parse_backlog_file_data(md_file.read_text(encoding="utf-8"))
        except (OSError, YAMLError):
            continue

        if data is None:
            continue

        issue_number = _extract_issue_int_from_backlog_data(data)
        if issue_number is None:
            continue

        name: str = str(data.get("name") or data.get("title") or "").strip()
        if name:
            canonical_slug = title_to_slug(name)
            if canonical_slug:
                index[canonical_slug] = issue_number

        # Also index by filename stem (after stripping priority prefix).
        filename_slug = _strip_backlog_priority_prefix(md_file.stem)
        if filename_slug:
            index.setdefault(filename_slug, issue_number)

        # Index by plan field slug (e.g. "agent-profile-mcp-tool" from
        # "plan/P979-agent-profile-mcp-tool.yaml").
        plan_slug = _extract_plan_field_slug(data)
        if plan_slug:
            index.setdefault(plan_slug, issue_number)

    return index


def _extract_artifact_slug(filename: str) -> str | None:
    """Extract the feature slug portion from an artifact filename.

    Handles the following artifact filename patterns:

    - ``feature-context-{slug}.md``
    - ``architect-{slug}.md``
    - ``P{NNN}-{slug}.yaml``
    - ``T0-baseline-{slug}.yaml``
    - ``TN-verification-{slug}.yaml``
    - ``tasks-{N}-{slug}.md`` (legacy plan files, slug portion extracted)
    - ``milestone-{N}-dispatch.yaml``
    - ``{FOCUS}.md`` (codebase analysis files — no extractable slug)

    Args:
        filename: Bare filename including extension.

    Returns:
        The extracted slug string, or ``None`` when no slug is present.
    """
    # Strip extension.
    stem = re.sub(r"\.[^.]+$", "", filename)
    for prefix in ("feature-context-", "architect-", "T0-baseline-", "TN-verification-"):
        if stem.startswith(prefix):
            return stem[len(prefix) :]
    # P{NNN}-{slug} plan files.
    m = re.match(r"^P\d+-(.+)$", stem)
    if m:
        return m.group(1)
    # tasks-{N}-{slug} legacy plan files.
    m = re.match(r"^tasks-\d+-(.+)$", stem)
    if m:
        return m.group(1)
    return None


def _resolve_high_number_p_prefix(filename: str, backlog_dir: Path, slug_index: dict[str, int] | None) -> int | None:
    """For ``P{NNN}-{slug}.yaml`` where NNN ≥ threshold, verify and return NNN as issue number.

    Args:
        filename: Bare artifact filename, e.g. ``P1015-foo.yaml``.
        backlog_dir: Absolute path to the backlog directory.
        slug_index: Pre-built slug index, or ``None`` when not available.

    Returns:
        NNN as an integer when verified, else ``None``.
    """
    m = re.match(r"^P(\d+)-", filename)
    if not m:
        return None
    candidate = int(m.group(1))
    if candidate < _HIGH_NUMBER_PLAN_PREFIX_THRESHOLD:
        return None
    if slug_index is not None:
        return candidate if candidate in slug_index.values() else None
    if backlog_dir.is_dir():
        for f in backlog_dir.iterdir():
            if f.is_file() and f.name.startswith(f"{candidate}-"):
                return candidate
    return None


def _find_issue_number(path: Path, backlog_dir: Path, slug_index: dict[str, int] | None = None) -> int | None:
    """Resolve the GitHub Issue number for an artifact file.

    Resolution order:
    1. Embedded field — YAML top-level fields (``.yaml``) or Markdown
       frontmatter (``.md``).  Used directly when present.
    2. Slug index lookup — extract the feature slug from the artifact
       filename, look it up in the pre-built ``slug → issue_number`` map.
    3. High-number P prefix — for ``P{NNN}-{slug}.yaml`` where NNN ≥
       ``_HIGH_NUMBER_PLAN_PREFIX_THRESHOLD``, treat NNN as the issue number
       when it is present in the slug index.
    4. Legacy P prefix heuristic — check whether a backlog file whose name
       starts with ``{NNN}-`` exists for any P{NNN} filename.

    Args:
        path: Absolute path to the artifact file.
        backlog_dir: Absolute path to the project's backlog directory.
        slug_index: Pre-built ``slug → issue_number`` map from
            :func:`_build_slug_index`.  Pass ``None`` to skip slug lookup.

    Returns:
        Positive integer issue number, or ``None`` when not found.
    """
    # 1. Embedded field.
    if path.suffix in {".yaml", ".yml"}:
        result = _read_issue_number_from_yaml(path)
        if result is not None:
            return result
    elif path.suffix == ".md":
        result = _read_issue_number_from_markdown_frontmatter(path)
        if result is not None:
            return result

    # 2. Slug index lookup.
    if slug_index:
        artifact_slug = _extract_artifact_slug(path.name)
        if artifact_slug and artifact_slug in slug_index:
            return slug_index[artifact_slug]

    # 3. High-number P prefix — NNN ≥ threshold treated as issue number directly.
    high = _resolve_high_number_p_prefix(path.name, backlog_dir, slug_index)
    if high is not None:
        return high

    # 4. Legacy P prefix heuristic (NNN < threshold).
    return _infer_issue_from_plan_filename(path.name, backlog_dir)


def _collect_artifact_files(plan_dir: Path) -> list[tuple[Path, str]]:
    """Scan *plan_dir* and return ``(absolute_path, artifact_type)`` pairs.

    Skips subdirectories listed in ``_SKIP_SUBDIRS`` (except ``codebase/``),
    skips files matching ``_should_skip_file``, and skips files with no
    matching artifact type pattern.

    Args:
        plan_dir: Absolute path to the ``plan/`` directory.

    Returns:
        List of ``(absolute_path, artifact_type)`` pairs in alphabetical order.
    """
    results: list[tuple[Path, str]] = []

    for item in sorted(plan_dir.rglob("*")):
        if not item.is_file():
            continue
        # Check for skip subdirectory rule.
        relative = item.relative_to(plan_dir)
        parts = relative.parts
        if len(parts) > 1 and parts[0] in _SKIP_SUBDIRS:
            continue

        parent_name = item.parent.name if item.parent != plan_dir else ""
        if _should_skip_file(item.name):
            continue

        artifact_type = _detect_artifact_type(item.name, parent_name)
        if artifact_type is None:
            continue

        results.append((item, artifact_type))

    return results


def _build_registration_rows(
    artifact_files: list[tuple[Path, str]], state: Path, backlog: Path
) -> list[tuple[str, str, int | None, str]]:
    """Build the initial registration queue from collected artifact files.

    Builds a slug index from the backlog directory once, then resolves each
    artifact's issue number using the four-step lookup in
    :func:`_find_issue_number`.

    Args:
        artifact_files: List of ``(absolute_path, artifact_type)`` pairs.
        state: Absolute path to the DH state root (used for relative path computation).
        backlog: Absolute path to the backlog directory (used for issue inference).

    Returns:
        List of ``(rel_path, artifact_type, issue_number_or_None, status)`` rows.
    """
    slug_index = _build_slug_index(backlog)
    rows: list[tuple[str, str, int | None, str]] = []
    for abs_path, artifact_type in artifact_files:
        rel = str(abs_path.relative_to(state))
        issue_number = _find_issue_number(abs_path, backlog, slug_index)
        status = "UNMATCHED" if issue_number is None else "PENDING"
        rows.append((rel, artifact_type, issue_number, status))
    return rows


def _register_one(
    provider: GitHubArtifactProvider, rel: str, artifact_type: str, issue_number: int
) -> tuple[str, str | None]:
    """Register a single artifact and return its outcome.

    Imports model types lazily — only called after GitHub connectivity is confirmed.

    Args:
        provider: ``GitHubArtifactProvider`` instance.
        rel: State-relative path to the artifact file.
        artifact_type: Artifact type string, e.g. ``"architect"``.
        issue_number: GitHub Issue number.

    Returns:
        Tuple of ``(status, detail)``: *status* is one of ``"REGISTERED"``,
        ``"SKIPPED"``, or ``"FAILED"``; *detail* explains SKIPPED/FAILED
        outcomes, or is ``None`` for REGISTERED.
    """
    from backlog_core.models import (  # ruff: ignore[import-outside-top-level]
        ArtifactEntry,
        ArtifactManifest,
        ArtifactStatus,
        ArtifactType,
        BacklogError,
    )

    try:
        art_type_enum = ArtifactType(artifact_type)
    except ValueError:
        return "FAILED", f"Unknown artifact type {artifact_type!r}"

    try:
        manifest = provider.get_manifest(issue_number)
    except BacklogError as exc:
        return "FAILED", f"Failed to get manifest for issue #{issue_number}: {exc}"

    existing = next((e for e in manifest.artifacts if e.artifact_id == rel), None)
    if existing is not None and existing.artifact_type == art_type_enum:
        return "SKIPPED", f"already registered on #{issue_number}"

    new_entry = ArtifactEntry(
        artifact_type=art_type_enum,
        artifact_id=rel,
        status=ArtifactStatus.CURRENT,
        created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        agent="dh_migrate",
    )
    updated_artifacts = [e for e in manifest.artifacts if e.artifact_id != rel]
    updated_artifacts.append(new_entry)
    updated_manifest = ArtifactManifest(
        issue_number=issue_number, artifacts=updated_artifacts, last_updated=manifest.last_updated
    )

    try:
        provider.set_manifest(issue_number, updated_manifest)
    except BacklogError as exc:
        return "FAILED", f"Failed to register on issue #{issue_number}: {exc}"
    else:
        return "REGISTERED", None


def _execute_registrations(
    rows: list[tuple[str, str, int | None, str]], state: Path
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Execute the registration loop and return final rows and counts.

    Args:
        rows: Pre-built registration queue from :func:`_build_registration_rows`.
        state: Absolute path to the DH state root (used to construct the provider).

    Returns:
        Tuple of ``(final_rows, counts)`` where *final_rows* is a list of
        ``{"file", "artifact_type", "issue", "status", "detail"}`` dicts and
        *counts* maps status strings to their occurrence count.
    """
    from backlog_core.artifact_provider import GitHubArtifactProvider  # ruff: ignore[import-outside-top-level]
    from backlog_core.models import RepoDiscoveryError, discover_repo  # ruff: ignore[import-outside-top-level]

    try:
        repo_slug = discover_repo()
    except RepoDiscoveryError as exc:
        err(f"Cannot discover GitHub repo slug: {exc}")

    provider = GitHubArtifactProvider(repo=repo_slug, root_worktree=state)

    final_rows: list[dict[str, object]] = []
    counts: dict[str, int] = {"REGISTERED": 0, "SKIPPED": 0, "UNMATCHED": 0, "FAILED": 0}

    for rel, artifact_type, issue_number, _ in rows:
        if issue_number is None:
            final_rows.append({"file": rel, "artifact_type": artifact_type, "issue": None, "status": "UNMATCHED"})
            counts["UNMATCHED"] += 1
            continue
        status, detail = _register_one(provider, rel, artifact_type, issue_number)
        row: dict[str, object] = {"file": rel, "artifact_type": artifact_type, "issue": issue_number, "status": status}
        if detail is not None:
            row["detail"] = detail
        final_rows.append(row)
        counts[status] += 1

    return final_rows, counts


@app.command()
def register_artifacts(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be registered without making changes.")
    ] = False,
    slug: Annotated[str | None, typer.Option("--slug", help="Override the auto-detected project slug.")] = None,
) -> None:
    """Register existing plan artifacts in their backlog item artifact manifests.

    Scans all artifact files in ~/.dh/projects/{slug}/plan/ and registers each
    one with its associated GitHub Issue via GitHubArtifactProvider.set_manifest().

    Use --dry-run to preview without making changes.
    Use --slug to override the auto-detected project slug.
    """
    project_root = _project_root()
    resolved_slug: str = slug or dh_paths.compute_slug(project_root)

    state = dh_paths.state_root(project_root)
    plan = dh_paths.plan_dir(project_root)
    backlog = dh_paths.backlog_dir(project_root)
    context = {"project_root": project_root, "slug": resolved_slug, "plan_dir": plan, "state_root": state}

    if not plan.is_dir():
        err(f"Plan directory does not exist: {plan}")

    artifact_files = _collect_artifact_files(plan)
    if not artifact_files:
        output_json({**context, "status": "no_artifacts", "plan": []})
        return

    rows = _build_registration_rows(artifact_files, state, backlog)
    plan_rows = [
        {"file": rel, "artifact_type": artifact_type, "issue": issue_number, "status": status}
        for rel, artifact_type, issue_number, status in rows
    ]

    if dry_run:
        output_json({**context, "status": "dry_run", "plan": plan_rows})
        return

    final_rows, counts = _execute_registrations(rows, state)
    output_json({
        **context,
        "status": "error" if counts["FAILED"] > 0 else "success",
        "results": final_rows,
        "summary": counts,
    })

    if counts["FAILED"] > 0:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
