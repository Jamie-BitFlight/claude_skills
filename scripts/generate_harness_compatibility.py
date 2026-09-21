#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.12.5"]
# ///
"""Generate the ignored harness_compatibility.json view from tracked inputs.

Objective fields (manifests present, runtime-escape blockers) are re-derived from the
filesystem on every run. Verification evidence is merged from the sparse tracked
harness_compatibility_verification.json source. The generated output is never an input.

Usage:
    uv run --script scripts/generate_harness_compatibility.py [--check]

Exit codes:
    0: table written (or --check: tracked inputs produce a valid table)
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
TABLE_PATH = ROOT / "harness_compatibility.json"
VERIFICATION_PATH = ROOT / "harness_compatibility_verification.json"

HARNESSES = ["claude-code", "codex", "hermes", "kimi"]


class VerificationRecord(BaseModel):
    """One durable, non-default smoke-test result."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["verified"]
    date: dt.date
    notes: str = Field(min_length=1)


class VerificationSource(BaseModel):
    """Sparse verification evidence keyed by plugin and harness."""

    model_config = ConfigDict(extra="forbid")

    plugins: dict[str, dict[str, VerificationRecord]]


def count_token_uses(plugin_dir: Path, token: str) -> int:
    """Count occurrences of a substitution token in runtime text.

    Args:
        plugin_dir: Plugin root directory.
        token: Literal token to count (e.g. ``${CLAUDE_PLUGIN_ROOT}``).

    Returns:
        Total occurrences across ``skills/``, ``agents/``, and ``commands/`` markdown.
    """
    total = 0
    for subdir in ("skills", "agents", "commands"):
        d = plugin_dir / subdir
        if not d.is_dir():
            continue
        for f in d.rglob("*.md"):
            with contextlib.suppress(OSError, UnicodeDecodeError):
                total += f.read_text(encoding="utf-8").count(token)
    return total


def scan_plugin(plugin_dir: Path) -> dict:
    """Derive the objective table entry for one plugin from the filesystem.

    Returns:
        Mapping with ``manifests``, ``components``, and ``blockers`` sections.
    """
    mcp_server_count = 0
    for p in (plugin_dir / ".mcp.json", plugin_dir / "mcp.json"):
        if p.exists():
            try:
                mcp_server_count += len(json.loads(p.read_text(encoding="utf-8")).get("mcpServers", {}))
            except (json.JSONDecodeError, OSError) as exc:
                print(
                    f"warning: {plugin_dir.name}: cannot parse {p.name} ({exc}); counting 0 MCP servers",
                    file=sys.stderr,
                )
    return {
        "manifests": {
            "claude": (plugin_dir / ".claude-plugin" / "plugin.json").exists(),
            "codex": (plugin_dir / ".codex-plugin" / "plugin.json").exists(),
            "portable": (plugin_dir / "plugin.json").exists(),
            "hermes_native": (plugin_dir / "plugin.yaml").exists(),
        },
        "components": {
            "skills": len(list((plugin_dir / "skills").glob("*/SKILL.md"))) if (plugin_dir / "skills").is_dir() else 0,
            "agents": len(list((plugin_dir / "agents").glob("*.md"))) if (plugin_dir / "agents").is_dir() else 0,
            "mcp_servers": mcp_server_count,
            "hooks": (plugin_dir / "hooks").is_dir() and any((plugin_dir / "hooks").iterdir()),
        },
        "blockers": {
            "claude_plugin_root_uses": count_token_uses(plugin_dir, "${CLAUDE_PLUGIN_ROOT}"),
            "claude_skill_dir_uses": count_token_uses(plugin_dir, "${CLAUDE_SKILL_DIR}"),
        },
    }


def load_verification_source(plugin_names: set[str]) -> VerificationSource:
    """Load and validate the tracked sparse verification evidence.

    Args:
        plugin_names: Plugin directory names included in the generated view.

    Returns:
        Validated sparse verification evidence.

    Raises:
        ValueError: The source names a plugin or harness absent from the generated matrix.
    """
    source = VerificationSource.model_validate_json(VERIFICATION_PATH.read_text(encoding="utf-8"))
    unknown_plugins = set(source.plugins) - plugin_names
    if unknown_plugins:
        raise ValueError(f"verification source contains unknown plugins: {sorted(unknown_plugins)}")
    for plugin_name, harnesses in source.plugins.items():
        unknown_harnesses = set(harnesses) - set(HARNESSES)
        if unknown_harnesses:
            raise ValueError(
                f"verification source for {plugin_name} contains unknown harnesses: {sorted(unknown_harnesses)}"
            )
    return source


def merge_verification(source: VerificationSource, name: str) -> dict[str, dict[str, Any]]:
    """Merge sparse evidence with defaults for every supported harness.

    Args:
        source: Validated tracked verification evidence.
        name: Plugin name whose verification mapping is needed.

    Returns:
        Complete per-harness verification mapping.
    """
    evidence = source.plugins.get(name, {})
    default = {"status": "unverified", "date": None, "notes": None}
    return {
        harness: evidence[harness].model_dump(mode="json") if harness in evidence else dict(default)
        for harness in HARNESSES
    }


def build_table() -> dict[str, Any]:
    """Scan every plugin and assemble the full table from tracked inputs.

    Returns:
        The complete table document as a JSON-serializable mapping.
    """
    plugin_dirs = [
        plugin_dir
        for plugin_dir in sorted(
            path for path in PLUGINS_DIR.iterdir() if path.is_dir() and not path.name.startswith((".", "_"))
        )
        if (plugin_dir / ".claude-plugin").is_dir() or (plugin_dir / "skills").is_dir()
    ]
    verification = load_verification_source({plugin_dir.name for plugin_dir in plugin_dirs})
    plugins = {}
    for plugin_dir in plugin_dirs:
        entry = scan_plugin(plugin_dir)
        entry["verification"] = merge_verification(verification, plugin_dir.name)
        plugins[plugin_dir.name] = entry
    return {
        "_about": (
            "Cross-harness compatibility table. 'manifests'/'components'/'blockers' are generated by "
            "scripts/generate_harness_compatibility.py from the filesystem — do not hand-edit. "
            "'verification' is merged from the tracked harness_compatibility_verification.json source; "
            "edit that source after running the smoke tests, then regenerate this ignored view."
        ),
        "harnesses": HARNESSES,
        "plugins": plugins,
    }


def main(argv: list[str] | None = None) -> int:
    """Entry point: write the view, or validate tracked inputs with ``--check``.

    Args:
        argv: Optional command-line arguments. Defaults to ``sys.argv``.

    Returns:
        Process exit code: 0 on success.
    """
    parser = argparse.ArgumentParser(description="Generate harness_compatibility.json from the plugins/ tree.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate tracked inputs without reading or writing the ignored generated view",
    )
    args = parser.parse_args(argv)

    table = build_table()
    if args.check:
        print(f"validated harness compatibility inputs ({len(table['plugins'])} plugins)")
        return 0
    rendered = json.dumps(table, indent=2, ensure_ascii=False) + "\n"
    TABLE_PATH.write_text(rendered, encoding="utf-8")
    n = len(table["plugins"])
    print(f"wrote {TABLE_PATH.relative_to(ROOT)} ({n} plugins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
