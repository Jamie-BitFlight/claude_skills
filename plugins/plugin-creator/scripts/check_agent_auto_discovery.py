#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Regression guard: detect plugin.json files that mask auto-discovered components.

Claude Code auto-discovers every ``.md`` file in a plugin's ``agents/``,
``commands/``, and ``skills/`` directories — but ONLY when the corresponding
``agents`` / ``commands`` / ``skills`` key is ABSENT from ``plugin.json``.

Writing the key (even to add a single entry) overrides auto-discovery: the
declared list becomes the *complete* list and every file not named in it
becomes invisible. Two production incidents have hit this trap:

- **2026-03-17**: ``python3-development`` committed
  ``"agents": ["./agents/t0-baseline-capture.md", "./agents/tn-verification-gate.md"]``
  and 17 of 19 agents disappeared.
- **2026-04-12** (commit ``30260566``): ``development-harness`` had a buggy
  pre-commit hook auto-add a 2-entry ``agents`` array, which would have
  masked 21 of 23 agents.

This guard fails the commit when any of the following conditions are true
for any ``plugin.json`` under ``plugins/``:

1. The plugin.json contains an ``agents`` / ``commands`` / ``skills`` key
   AND that key is a strict subset of the corresponding default-location
   files on disk. This is the classic "registered some but not all"
   silent-mask bug.
2. The plugin.json contains the key as an empty list. This is always wrong:
   either omit the key (use auto-discovery) or list every file.

Fixing the violation:

- If every file is in the default location, **remove the key entirely**.
  Auto-discovery will register everything.
- If some files are intentionally in non-default paths, list **every** file
  (default-path and non-default-path alike) so the manual allowlist stays
  complete.

See ``.claude/rules/plugin-development.md`` for the canonical rule.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Map from plugin.json field name to the default directory, the file kind,
# and the discovery shape ("md-file" for agents/commands or "skill-dir" for
# skills). Discovery shape governs both how paths are discovered on disk and
# how registered paths in plugin.json are normalized for comparison.
_AUTO_DISCOVERED: dict[str, tuple[str, str, str]] = {
    # field_name: (default_subdir, kind, shape)
    "agents": ("agents", "agent", "md-file"),
    "commands": ("commands", "command", "md-file"),
    "skills": ("skills", "skill", "skill-dir"),
}

# Maximum sample size shown in violation messages before truncating to "+N more"
_VIOLATION_SAMPLE_LIMIT = 5


def _discover_default_files(plugin_dir: Path, subdir: str, shape: str) -> set[str]:
    """Return the set of relative paths that auto-discovery would register.

    Each path is in the same canonical form that ``auto_sync_manifests.py``
    emits.

    Args:
        plugin_dir: Plugin root directory.
        subdir: Default auto-discovery subdirectory name.
        shape: Either ``"md-file"`` (agents/commands — every ``*.md`` file
            directly under ``subdir``) or ``"skill-dir"`` (skills — every
            one-level subdirectory containing a ``SKILL.md``).

    Returns:
        Set of canonical ``./<subdir>/<name>`` paths. For ``md-file`` shape
        the name includes the ``.md`` suffix; for ``skill-dir`` shape it is
        the bare directory name.
    """
    target = plugin_dir / subdir
    if not target.is_dir():
        return set()

    if shape == "md-file":
        return {
            f"./{subdir}/{p.name}"
            for p in sorted(target.iterdir())
            if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")
        }

    if shape == "skill-dir":
        # Skills are one-level-deep subdirectories under skills/ containing
        # a SKILL.md file. Skill directories with no SKILL.md are not
        # auto-discovered and therefore not considered masked.
        return {
            f"./{subdir}/{p.name}"
            for p in sorted(target.iterdir())
            if p.is_dir() and not p.name.startswith(".") and (p / "SKILL.md").is_file()
        }

    msg = f"unknown discovery shape: {shape!r}"
    raise ValueError(msg)


def _normalize_registered(entry: str, shape: str) -> str:
    """Normalize a plugin.json array entry to the canonical discovery form.

    Handles the two-form equivalence for skills (``./skills/foo`` and
    ``./skills/foo/SKILL.md`` refer to the same skill) and missing ``./``
    prefixes.

    Args:
        entry: Raw string from the plugin.json array.
        shape: Discovery shape — ``"md-file"`` or ``"skill-dir"``.

    Returns:
        Canonical path string matching what ``_discover_default_files``
        emits for the same component.
    """
    normalized = entry if entry.startswith("./") else f"./{entry.lstrip('/')}"
    if shape == "skill-dir" and normalized.endswith("/SKILL.md"):
        normalized = normalized[: -len("/SKILL.md")]
    return normalized


def _check_one_plugin(plugin_json: Path) -> list[str]:
    """Check a single plugin.json for auto-discovery masking violations.

    Returns:
        List of human-readable violation messages. Empty when the plugin is
        clean.
    """
    plugin_dir = plugin_json.parent.parent  # .claude-plugin/plugin.json -> plugin root
    plugin_name = plugin_dir.name

    try:
        with plugin_json.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as exc:
        return [f"{plugin_json}: invalid JSON — {exc}"]

    violations: list[str] = []

    for field_name, (subdir, kind, shape) in _AUTO_DISCOVERED.items():
        if field_name not in data:
            continue  # Mode A — auto-discovery active, no risk

        registered_raw = data[field_name]
        if not isinstance(registered_raw, list):
            violations.append(
                f"{plugin_json}: '{field_name}' must be an array of file paths (got {type(registered_raw).__name__})"
            )
            continue

        if len(registered_raw) == 0:
            violations.append(
                f"{plugin_json}: '{field_name}' is an empty list. "
                f"Either omit the key entirely (auto-discovery will register everything in {subdir}/) "
                f"or list every {kind} file explicitly."
            )
            continue

        registered = {_normalize_registered(str(item), shape) for item in registered_raw}
        on_disk_default = _discover_default_files(plugin_dir, subdir, shape)

        # Files that auto-discovery WOULD register but plugin.json does NOT.
        # These are now invisible because declaring the key disabled auto-discovery.
        masked = on_disk_default - registered
        if masked:
            sample = ", ".join(sorted(masked)[:_VIOLATION_SAMPLE_LIMIT])
            more = f" (+{len(masked) - _VIOLATION_SAMPLE_LIMIT} more)" if len(masked) > _VIOLATION_SAMPLE_LIMIT else ""
            violations.append(
                f"{plugin_json}: declaring '{field_name}' overrode auto-discovery "
                f"and made {len(masked)} {kind} file(s) in {subdir}/ invisible: {sample}{more}\n"
                f"  Plugin '{plugin_name}' has {len(on_disk_default)} default-location {kind}(s) on disk "
                f"but plugin.json only registers {len(registered & on_disk_default)} of them.\n"
                f"  Fix: remove the '{field_name}' key entirely if every {kind} is in {subdir}/, "
                f"OR list every {kind} file explicitly in the array."
            )

    return violations


def main(argv: list[str]) -> int:
    """Entry point.

    Accepts an optional list of file paths from pre-commit (``pass_filenames: true``).
    When called with no arguments, scans every plugin.json under ``plugins/``.

    Args:
        argv: Process argv. ``argv[0]`` is the script name; remaining entries
            are candidate file paths from pre-commit.

    Returns:
        Exit code 0 when every scanned plugin.json is clean. Exit code 1 when
        any plugin.json declares a component array (``agents``, ``commands``,
        ``skills``) that masks files in the corresponding default
        auto-discovery directory.
    """
    if len(argv) > 1:
        # Pre-commit passes specific staged files. Filter to plugin.json files.
        candidates = [Path(p) for p in argv[1:] if p.endswith(".claude-plugin/plugin.json") and Path(p).is_file()]
    else:
        plugins_root = Path("plugins")
        if not plugins_root.is_dir():
            sys.stderr.write("Error: plugins/ directory not found (run from repo root)\n")
            return 1
        candidates = sorted(plugins_root.glob("*/.claude-plugin/plugin.json"))

    all_violations: list[str] = []
    for plugin_json in candidates:
        all_violations.extend(_check_one_plugin(plugin_json))

    if not all_violations:
        return 0

    sys.stderr.write(
        "ERROR: plugin.json auto-discovery violation detected.\n\n"
        "Claude Code auto-discovers every .md file in a plugin's agents/, commands/, and\n"
        "skills/ directories ONLY when the corresponding key is ABSENT from plugin.json.\n"
        "Writing the key — even to add one entry — overrides auto-discovery and silently\n"
        "masks every file not listed.\n\n"
        "Incident history:\n"
        "  - 2026-03-17: python3-development plugin.json had a 2-entry agents array;\n"
        "    17 of 19 agents disappeared.\n"
        "  - 2026-04-12 (commit 30260566): development-harness pre-commit hook auto-added\n"
        "    a 2-entry agents array; would have masked 21 of 23 agents.\n\n"
        "See .claude/rules/plugin-development.md for the canonical rule.\n\n"
        "Violations:\n"
    )
    for v in all_violations:
        sys.stderr.write(f"  - {v}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
