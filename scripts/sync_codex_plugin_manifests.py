#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Synchronize Codex plugin manifests from their Claude plugin metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_utils import title_case_from_kebab

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
SHORT_DESCRIPTION_LIMIT = 240

# Codex resolves a relative "cwd" against the installed plugin bundle and never expands
# $VAR/${VAR} placeholders in args/env at runtime (see docs/codex-mcp-runtime.md). This is the
# one Claude placeholder with a mechanical Codex-compatible rewrite: strip the prefix and pair it
# with an explicit cwd: ".".
_CODEX_PLUGIN_ROOT_PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}/"

# Interface fields a maintainer may hand-tune to read better than the derived default. Re-synced
# only when missing/empty on the existing manifest. Every other computed field is a pure, always
# up-to-date derivation of Claude source data with no independent curated meaning of its own:
# "shortDescription"/"longDescription" are truncated/verbatim copies of "description",
# "developerName" mirrors "author.name", and "capabilities" reflects the plugin's actual
# directory structure (skills/, hooks.json, etc.) — preserving a stale copy of any of these would
# silently mask real source-of-truth changes (for example, the SHORT_DESCRIPTION_LIMIT
# truncation) behind a manifest that looks "already set".
_PRESERVED_INTERFACE_FIELDS = ("displayName", "category")


class UnexpandablePlaceholderError(ValueError):
    """Raised when a Claude MCP config value has no Codex-compatible expansion."""


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


def _codexify_mcp_value(value: object, *, plugin_name: str, server_name: str) -> object:
    """Rewrite one Claude MCP config value into its Codex-compatible equivalent.

    ``${CLAUDE_PLUGIN_ROOT}/`` is rewritten to the empty string, relying on the accompanying
    ``cwd: "."`` set by :func:`_codexify_server`. Any other unresolved ``${...}`` placeholder
    (for example ``${CLAUDE_PROJECT_DIR}``) has no Codex runtime expansion and is rejected rather
    than copied into the generated manifest verbatim.

    Args:
        value: A raw value from a Claude ``mcpServers`` entry (string, list, dict, or scalar).
        plugin_name: Owning plugin directory name, used only for the error message.
        server_name: MCP server key, used only for the error message.

    Returns:
        The Codex-compatible value.

    Raises:
        UnexpandablePlaceholderError: If a string value contains a placeholder Codex cannot expand.
    """
    if isinstance(value, str):
        rewritten = value.replace(_CODEX_PLUGIN_ROOT_PLACEHOLDER, "")
        if "${" in rewritten:
            raise UnexpandablePlaceholderError(
                f"{plugin_name}.{server_name}: Codex does not expand {rewritten!r} at runtime "
                "(see docs/codex-mcp-runtime.md); resolve it to a literal value or a name "
                "forwarded via env_vars before regenerating .mcp.json."
            )
        return rewritten
    if isinstance(value, list):
        return [_codexify_mcp_value(item, plugin_name=plugin_name, server_name=server_name) for item in value]
    if isinstance(value, dict):
        return {
            key: _codexify_mcp_value(item, plugin_name=plugin_name, server_name=server_name)
            for key, item in value.items()
        }
    return value


def _codexify_server(plugin_name: str, server_name: str, server_config: dict) -> dict:
    """Rewrite one Claude ``mcpServers`` entry for Codex placeholder and ``cwd`` rules.

    Returns:
        The Codex-compatible server configuration.
    """
    # Recurse through _codexify_mcp_value's dict branch would type this as `object`, forcing an
    # isinstance-narrowing dance ty cannot resolve on a bare `dict` (a known ty limitation, not a
    # real ambiguity here: server_config is always a dict). Iterate directly instead.
    rewritten = {
        key: _codexify_mcp_value(value, plugin_name=plugin_name, server_name=server_name)
        for key, value in server_config.items()
    }
    if _CODEX_PLUGIN_ROOT_PLACEHOLDER in json.dumps(server_config):
        rewritten.setdefault("cwd", ".")
    return rewritten


def sync_mcp_file(plugin_dir: Path, *, check_only: bool = False) -> bool:
    """Normalize a plugin MCP file to the canonical wrapped ``mcpServers`` shape.

    Args:
        plugin_dir: The plugin directory to synchronize.
        check_only: When ``True``, report whether the file would change without writing it.

    Returns:
        Whether the file changed (or, in check mode, would change).

    Raises:
        UnexpandablePlaceholderError: If a fresh copy from the Claude manifest contains a
            placeholder Codex cannot expand at runtime.
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
            if not check_only:
                mcp_path.write_text(json.dumps({"mcpServers": current["mcp_servers"]}, indent=2) + "\n")
            return True
        return False

    if source_servers is not None:
        codexified_servers = {
            name: _codexify_server(plugin_dir.name, name, config) for name, config in source_servers.items()
        }
        if not check_only:
            mcp_path.write_text(json.dumps({"mcpServers": codexified_servers}, indent=2) + "\n")
        return True

    return False


def _merge_interface(existing_interface: object, computed_interface: dict) -> dict:
    """Merge freshly derived interface defaults with hand-curated overrides.

    Fields listed in ``_PRESERVED_INTERFACE_FIELDS`` keep a non-empty hand-set value from the
    existing manifest and only fall back to the computed default when missing or empty.
    ``defaultPrompt`` has no computed default and is carried over verbatim when present. Every
    other computed field (currently ``capabilities``) always takes the freshly derived value.

    Returns:
        The merged interface object to write to the Codex manifest.
    """
    merged = dict(computed_interface)
    if not isinstance(existing_interface, dict):
        return merged
    for field in _PRESERVED_INTERFACE_FIELDS:
        existing_value = existing_interface.get(field)
        if existing_value:
            merged[field] = existing_value
    if "defaultPrompt" in existing_interface:
        merged["defaultPrompt"] = existing_interface.get("defaultPrompt")
    return merged


def sync_manifest(plugin_dir: Path, *, check_only: bool = False) -> bool:
    """Synchronize one Codex manifest and report whether it changed.

    Args:
        plugin_dir: The plugin directory to synchronize.
        check_only: When ``True``, report whether the manifest would change without writing it.

    Returns:
        Whether the manifest changed (or, in check mode, would change).
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

    # Codex's plugin validator rejects a top-level "hooks" field outright (see
    # research/design-notes/2026-06-14-plugin-creator-packaging-assessment.md) and
    # auto-detects ./hooks/hooks.json on its own -- never write this field.
    if "hooks" in manifest:
        del manifest["hooks"]
        changed = True

    display_name = title_case_from_kebab(manifest["name"])
    description = manifest.get("description") or f"{display_name} plugin"
    author = manifest.get("author")
    developer_name = author.get("name") if isinstance(author, dict) and author.get("name") else "Unknown"

    computed_interface = {
        "displayName": display_name,
        "shortDescription": _short_description(description),
        "longDescription": description,
        "developerName": developer_name,
        "category": "Developer Tools",
        "capabilities": detect_capabilities(plugin_dir),
    }
    interface = _merge_interface(manifest.get("interface"), computed_interface)

    if manifest.get("interface") != interface:
        manifest["interface"] = interface
        changed = True

    if changed and not check_only:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return changed


def main(argv: list[str] | None = None) -> int:
    """Synchronize, or in ``--check`` mode verify, every Codex plugin manifest.

    Args:
        argv: Command-line arguments, defaulting to ``sys.argv[1:]``.

    Returns:
        Process exit status: in ``--check`` mode, ``1`` if any manifest is stale; otherwise
        always ``0``.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale Codex manifests without writing them; exit non-zero if any are stale.",
    )
    args = parser.parse_args(argv)

    stale_plugins: list[str] = []
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        mcp_changed = sync_mcp_file(plugin_dir, check_only=args.check)
        manifest_changed = sync_manifest(plugin_dir, check_only=args.check)
        if mcp_changed or manifest_changed:
            stale_plugins.append(plugin_dir.name)

    if args.check:
        if stale_plugins:
            print(f"Stale Codex manifest(s): {', '.join(stale_plugins)}")
            return 1
        print("Codex manifests are up to date.")
        return 0

    print(f"Updated {len(stale_plugins)} plugin manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
