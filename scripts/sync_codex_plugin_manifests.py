#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"


def title_case_from_kebab(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-") if part)


def detect_capabilities(plugin_dir: Path) -> list[str]:
    capabilities = ["Interactive"]
    if (plugin_dir / "skills").is_dir():
        capabilities.append("Read")
    if any(
        (
            (plugin_dir / "commands").is_dir(),
            (plugin_dir / "hooks").is_dir(),
            (plugin_dir / "hooks.json").is_file(),
            (plugin_dir / ".mcp.json").is_file(),
            (plugin_dir / ".app.json").is_file(),
        )
    ):
        capabilities.append("Write")
    return list(dict.fromkeys(capabilities))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def sync_mcp_file(plugin_dir: Path) -> bool:
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
            mcp_path.write_text(json.dumps(current["mcpServers"], indent=2) + "\n")
            return True
        if "mcp_servers" in current and isinstance(current["mcp_servers"], dict):
            mcp_path.write_text(json.dumps(current["mcp_servers"], indent=2) + "\n")
            return True
        return False

    if source_servers is not None:
        mcp_path.write_text(json.dumps(source_servers, indent=2) + "\n")
        return True

    return False


def sync_manifest(plugin_dir: Path) -> bool:
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return False

    manifest = load_json(manifest_path)
    changed = False

    if (plugin_dir / "skills").is_dir() and manifest.get("skills") != "./skills/":
        manifest["skills"] = "./skills/"
        changed = True

    if (plugin_dir / ".mcp.json").is_file() and manifest.get("mcpServers") != "./.mcp.json":
        manifest["mcpServers"] = "./.mcp.json"
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
        "shortDescription": description,
        "longDescription": description,
        "developerName": developer_name,
        "category": "Developer Tools",
        "capabilities": detect_capabilities(plugin_dir),
    }

    if manifest.get("interface") != interface:
        manifest["interface"] = interface
        changed = True

    if changed:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return changed


def main() -> int:
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
