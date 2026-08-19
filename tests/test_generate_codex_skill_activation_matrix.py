"""Tests for the deterministic Codex skill activation-matrix scaffold."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import generate_codex_skill_activation_matrix as generator


def test_checked_in_matrix_matches_declared_plugin_skills() -> None:
    """Keep every declared Codex skill visible until it gains real test evidence."""
    rows = generator.apply_overrides(generator.build_rows(), generator.load_overrides())
    checked_in = generator.MATRIX_PATH.read_text(encoding="utf-8")

    assert len(rows) == 244
    assert checked_in == generator.render_rows(rows)
    assert all(row["status"] in {"NO_ORACLE", "MAPPED", "BLOCKED", "PASSED", "FAILED"} for row in rows)
    for row in rows:
        if row["status"] == "NO_ORACLE":
            assert row["task_source"] is None
            assert row["task_text"] is None
            assert row["expected_outcome"] is None
            assert row["safety_class"] == "UNCLASSIFIED"
        if row["status"] == "MAPPED":
            assert isinstance(row["task_source"], str)
            assert isinstance(row["task_text"], str)
            assert isinstance(row["expected_outcome"], str)
            assert row["safety_class"] != "UNCLASSIFIED"

    parsed_rows = [json.loads(line) for line in checked_in.splitlines()]
    targets = [row["target"] for row in parsed_rows]
    assert targets == sorted(targets)
    assert len({row["target"] for row in parsed_rows}) == 244
