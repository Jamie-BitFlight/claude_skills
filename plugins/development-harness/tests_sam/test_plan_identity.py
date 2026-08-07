"""Tests for plan identity: plan_id_from_path returns the full stem, never a prefix.

Regression: _P_STEM_RE truncated at the first hyphen, aliasing 14 distinct plans
to ``P001``. This test suite enforces that ``plan_id_from_path`` returns the
complete filename stem — the unique identifier — and that the path is
authoritative over any stored ``plan_id`` field in the payload.
"""

from __future__ import annotations

from pathlib import Path

from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider, plan_id_from_path
from sam_schema.core.models import Plan
from sam_schema.writers.yaml_writer import create_plan_file


def test_plan_id_is_the_whole_stem() -> None:
    """The unique identifier is the full filename minus extension. Never a prefix."""
    assert plan_id_from_path(Path("/x/P001-backlog-cli-dedup.json")) == "P001-backlog-cli-dedup"
    assert plan_id_from_path(Path("/x/Pa1b2c3d4-auth.json")) == "Pa1b2c3d4-auth"
    assert plan_id_from_path(Path("/x/QG003-rename.json")) == "QG003-rename"


def test_hyphenated_ids_do_not_collide() -> None:
    """Regression: _P_STEM_RE truncated at the first hyphen, aliasing 14 plans to P001."""
    ids = {plan_id_from_path(Path(f"/x/P001-{s}.json")) for s in ("alpha", "beta", "gamma")}
    assert len(ids) == 3


def test_non_prefix_stems_are_preserved() -> None:
    """Stems without the canonical P/QG prefix are returned verbatim."""
    assert plan_id_from_path(Path("/x/random-plan")) == "random-plan"


def test_directory_stems_are_preserved() -> None:
    """Directory stems (no extension) are returned verbatim."""
    assert plan_id_from_path(Path("/x/P001-backlog-cli-dedup")) == "P001-backlog-cli-dedup"


def test_path_wins_when_payload_disagrees(tmp_path: Path) -> None:
    """Three live files carry a copy-pasted plan-id. The path is authoritative."""
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    plan_path = plan_dir / "Pd43cb089-other.yaml"
    plan = Plan(
        feature="test",
        plan_id="Pabda39b5",  # copy-pasted wrong id — path should win
        tasks=[],
    )
    create_plan_file(plan_path, plan)

    backend = LocalYamlTaskProvider(plan_dir)
    plan_data = backend.read_plan("Pd43cb089-other")
    assert plan_data["plan_id"] == "Pd43cb089-other"
