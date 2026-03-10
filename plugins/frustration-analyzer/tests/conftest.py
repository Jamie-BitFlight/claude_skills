"""Shared pytest fixtures for frustration-analyzer tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def render(tmp_path: Path):
    """Return a helper that calls _render_card into tmp_path."""
    from _server import ASSISTANT, TASK, USER, render_card

    def _render(filename: str = "card.svg", **kwargs):
        out = tmp_path / filename
        result = render_card(TASK, ASSISTANT, USER, str(out), **kwargs)
        return out, result

    return _render
