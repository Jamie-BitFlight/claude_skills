"""Contract tests for the plugin isolation checker."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_plugin_isolation.py"
spec = importlib.util.spec_from_file_location("check_plugin_isolation", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_isolation_accepts_plugin_relative_content(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "tool.py").write_text('Path(__file__).parent / "scripts"\n')
    assert mod.violations(plugin) == []


def test_isolation_rejects_repository_escape(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "tool.py").write_text('"../../scripts/helper.py"\n')
    assert mod.violations(plugin)
