"""Focused tests for dependency-audit metadata discovery."""

from __future__ import annotations

from pathlib import PurePosixPath
from types import SimpleNamespace

import pytest
from scripts import audit_dependencies


def test_console_script_is_discovered_without_platform_install_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Console entry-point metadata finds tools on Unix and Windows layouts."""
    distribution = SimpleNamespace(
        metadata={"Name": "demo-tool"},
        files=[PurePosixPath("../../../Scripts/demo-cli.exe")],
        entry_points=[],
        requires=[],
    )
    monkeypatch.setattr(audit_dependencies, "distributions", lambda path=None: [distribution])
    metadata = audit_dependencies.installed_metadata(["unused"])
    assert metadata["demo-tool"]["binaries"] == ["demo-cli"]
