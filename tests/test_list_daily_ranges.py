"""Focused regression checks for the daily-release range default."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).parents[1] / ".claude/skills/daily-releases/scripts/list_daily_ranges.py"
sys.path.insert(0, str(SCRIPT.parent / "daily_releases_lib"))
spec = importlib.util.spec_from_file_location("list_daily_ranges", SCRIPT)
assert spec
assert spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_default_start_uses_latest_daily_release_and_explicit_start_wins() -> None:
    repo = SimpleNamespace(
        get_releases=lambda: [
            SimpleNamespace(tag_name="unrelated"),
            SimpleNamespace(tag_name="v2026.05.22"),
            SimpleNamespace(tag_name="v2026.08.01-r2"),
            SimpleNamespace(tag_name="v2026.13.40"),
        ]
    )

    assert module._resolve_start_date(None, repo) == date(2026, 8, 1)
    assert module._resolve_start_date(date(2025, 1, 2), repo) == date(2025, 1, 2)
    assert module._resolve_start_date(None, SimpleNamespace(get_releases=list)) is None
