#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Synchronize Codex plugin manifests from their Claude plugin metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_utils import title_case_from_kebab

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
SHORT_DESCRIPTION_LIMIT = 240


def _short_description(description: str) -> str:
    if len(description) <= SHORT_DESCRIPTION_LIMIT:
        return description
    return f"{description[:237].rsplit(' ', 1)[0]}..."


def detect_capabilities(plugin_dir: Path) -> list[str]:
    """Return interface capabilities implied by plugin components."""
    capabilities = ["Interactive"]
    if (plugin_dir / "skills").is_dir():
        capabilities.append("Read")
    if any((
        (plugin_dir / "commands").is_dir(),
        (plugin_dir / "hooks").is_dir(),
        (plugin_dir / "hooks.json").is_file(),
        (plugin_dir / ".mcp.json").is_file(),
        (plugin_dir / ".app.json").is_file(),
    )):
        capabilities.append("Write")
    return list(dict.fromkeys(capabilities))


def load_json(path: Path) -> dict:
    """Load a JSON object from a UTF-8 file.

    Returns:
        The decoded JSON object.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def sync_mcp_file(plugin_dir: Path) -> bool:
    """Normalize a plugin MCP file to the canonical wrapped ``mcpServers`` shape.

    Returns:
        Whether the file was written.
    """
    claude_manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    mcp_path = plugin_dir / ".mcp.json"

    source_servers = None
    if claude_manifest_path.is_file():
        claude_manifest = load_json(claude_manifest_path)
        candidate = claude_manifest.get("mcpServers") or claude_manifest.get("mcp_servers")
        if isinstance(candidate, dict):
            source_servers = candidate

    if mcp_path.is_file():
        current = load_json(mcp_path)
        if "mcpServers" in current and isinstance(current["mcpServers"], dict):
            return False
        if "mcp_servers" in current and isinstance(current["mcp_servers"], dict):
            mcp_path.write_text(json.dumps({"mcpServers": current["mcp_servers"]}, indent=2) + "\n")
            return True
        return False

    if source_servers is not None:
        mcp_path.write_text(json.dumps({"mcpServers": source_servers}, indent=2) + "\n")
        return True

    return False


def sync_manifest(plugin_dir: Path) -> bool:
    """Synchronize one Codex manifest and report whether it changed.

    Returns:
        Whether the manifest was changed.
    """
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return False

    manifest = load_json(manifest_path)
    changed = False

    if (plugin_dir / "skills").is_dir() and manifest.get("skills") != "./skills/":
        manifest["skills"] = "./skills/"
        changed = True

    mcp_manifest = manifest.get("mcpServers")
    mcp_path = mcp_manifest if isinstance(mcp_manifest, str) else "./.mcp.json"
    if (plugin_dir / mcp_path).is_file() and manifest.get("mcpServers") != mcp_path:
        manifest["mcpServers"] = mcp_path
        changed = True

    if (plugin_dir / ".app.json").is_file() and manifest.get("apps") != "./.app.json":
        manifest["apps"] = "./.app.json"
        changed = True

    # Codex auto-detects ./hooks/hooks.json, but plugins with a root-level hooks.json
    # need an explicit manifest path.
    if (plugin_dir / "hooks.json").is_file() and manifest.get("hooks") != "./hooks.json":
        manifest["hooks"] = "./hooks.json"
        changed = True

    display_name = title_case_from_kebab(manifest["name"])
    description = manifest.get("description") or f"{display_name} plugin"
    author = manifest.get("author")
    developer_name = author.get("name") if isinstance(author, dict) and author.get("name") else "Unknown"

    interface = {
        "displayName": display_name,
        "shortDescription": _short_description(description),
        "longDescription": description,
        "developerName": developer_name,
        "category": "Developer Tools",
        "capabilities": detect_capabilities(plugin_dir),
    }
    existing_interface = manifest.get("interface")
    if isinstance(existing_interface, dict) and "defaultPrompt" in existing_interface:
        interface["defaultPrompt"] = existing_interface["defaultPrompt"]

    if manifest.get("interface") != interface:
        manifest["interface"] = interface
        changed = True

    if changed:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return changed


def main() -> int:
    """Synchronize every Codex plugin manifest in the repository.

    Returns:
        Process exit status.
    """
    changed = 0
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        plugin_changed = sync_mcp_file(plugin_dir)
        plugin_changed = sync_manifest(plugin_dir) or plugin_changed
        if plugin_changed:
            changed += 1
    print(f"Updated {changed} plugin manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
