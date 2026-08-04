"""Generate the complete, deterministic Codex skill activation matrix scaffold."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
PLUGINS_ROOT = REPO_ROOT / "plugins"
MATRIX_PATH = REPO_ROOT / "plan" / "codex-skill-activation-matrix.jsonl"
OVERRIDES_PATH = REPO_ROOT / "plan" / "codex-skill-activation-overrides.json"
FRONTMATTER_NAME = re.compile(r"^name:\s*([^\s#]+)\s*$", re.MULTILINE)


def load_plugin_id(manifest_path: Path) -> str:
    """Return the declared plugin ID from a Codex plugin manifest."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = manifest.get("name")
    if not isinstance(plugin_id, str) or not plugin_id:
        raise ValueError(f"Plugin manifest has no non-empty name: {manifest_path}")
    return plugin_id


def load_skill_name(skill_path: Path) -> str:
    """Read the declared skill name without interpreting the skill body."""
    content = skill_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError(f"Skill frontmatter is missing: {skill_path}")
    frontmatter_end = content.find("\n---\n", 4)
    if frontmatter_end == -1:
        raise ValueError(f"Skill frontmatter is incomplete: {skill_path}")
    match = FRONTMATTER_NAME.search(content[4:frontmatter_end])
    if match is None:
        raise ValueError(f"Skill frontmatter has no name: {skill_path}")
    return match.group(1)


def build_rows(repo_root: Path = REPO_ROOT) -> list[dict[str, object]]:
    """Build one unresolved evidence record for each declared plugin-surface skill."""
    rows: list[dict[str, object]] = []
    plugins_root = repo_root / "plugins"

    for manifest_path in sorted(plugins_root.glob("*/.codex-plugin/plugin.json")):
        plugin_id = load_plugin_id(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        skills_setting = manifest.get("skills")
        if not isinstance(skills_setting, str):
            continue
        skills_root = manifest_path.parent.parent / skills_setting
        if not skills_root.is_dir():
            raise ValueError(f"Declared skills directory is missing: {skills_root}")

        for skill_path in sorted(skills_root.rglob("SKILL.md")):
            skill_name = load_skill_name(skill_path)
            rows.append(
                {
                    "target": f"{plugin_id}:{skill_name}",
                    "plugin_id": plugin_id,
                    "skill": skill_name,
                    "source_path": skill_path.relative_to(repo_root).as_posix(),
                    "task_source": None,
                    "task_text": None,
                    "expected_outcome": None,
                    "safety_class": "UNCLASSIFIED",
                    "chain": [],
                    "status": "NO_ORACLE",
                    "evidence": {
                        "distribution": None,
                        "cache_provenance": None,
                        "injection": None,
                        "behavior": None,
                        "safety": None,
                    },
                }
            )

    rows.sort(key=lambda row: str(row["target"]))
    targets = [str(row["target"]) for row in rows]
    if len(targets) != len(set(targets)):
        raise ValueError("Duplicate plugin-surface skill targets found")
    return rows


def render_rows(rows: list[dict[str, object]]) -> str:
    """Render stable JSONL so matrix changes remain reviewable in Git."""
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)


def load_overrides() -> dict[str, dict[str, object]]:
    """Load reviewed evidence fields without permitting inventory changes."""
    if not OVERRIDES_PATH.is_file():
        return {}
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    if not isinstance(overrides, dict):
        raise ValueError(
            f"Activation-matrix overrides must be an object: {OVERRIDES_PATH}"
        )
    for target, override in overrides.items():
        if not isinstance(target, str) or not isinstance(override, dict):
            raise ValueError(f"Activation-matrix override is invalid: {target!r}")
    return overrides


def apply_overrides(
    rows: list[dict[str, object]],
    overrides: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Merge evidence fields while preserving the manifest-derived inventory."""
    mutable_fields = {
        "task_source",
        "task_text",
        "expected_outcome",
        "safety_class",
        "chain",
        "status",
        "evidence",
    }
    targets = {str(row["target"]) for row in rows}
    unknown_targets = sorted(set(overrides) - targets)
    if unknown_targets:
        raise ValueError(
            "Activation-matrix overrides reference unknown targets: "
            f"{unknown_targets}"
        )

    for row in rows:
        override = overrides.get(str(row["target"]), {})
        unknown_fields = sorted(set(override) - mutable_fields)
        if unknown_fields:
            raise ValueError(
                "Activation-matrix override has immutable fields: "
                f"{unknown_fields}"
            )
        row.update(override)
    return rows


def main() -> int:
    """Write the current inventory scaffold or verify the checked-in version."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the matrix is stale.",
    )
    args = parser.parse_args()

    rows = apply_overrides(build_rows(), load_overrides())
    rendered = render_rows(rows)
    if args.check:
        matrix_contents = None
        if MATRIX_PATH.is_file():
            matrix_contents = MATRIX_PATH.read_text(encoding="utf-8")
        matrix_is_current = matrix_contents == rendered
        if not matrix_is_current:
            print(f"Activation matrix is stale: {MATRIX_PATH}")
            return 1
        return 0

    MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    MATRIX_PATH.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
