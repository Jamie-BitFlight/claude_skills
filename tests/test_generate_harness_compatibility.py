"""Drift gate for the generated cross-harness compatibility table.

`harness_compatibility.json` says its `manifests`, `components` and `blockers` fields are
generated and must not be hand-edited, but nothing enforced that. Its two sibling generated
artifacts — the Codex plugin manifests and the Codex skill activation matrix — each have a
pytest that fails when the committed copy stops matching its generator. This supplies the
same gate here, so a plugin added, renamed or retired without regenerating the table fails
CI instead of shipping a table that AGENTS.md tells agents to trust.

Parsed content is compared, not bytes: the repo's JSON formatter hooks reflow the committed
file, and cosmetic reflow is not staleness. This mirrors the generator's own `--check`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import generate_harness_compatibility as generator


def test_checked_in_table_matches_generated_table() -> None:
    """Fail when the committed table's generated fields drift from the plugins/ tree."""
    committed = json.loads(generator.TABLE_PATH.read_text(encoding="utf-8"))

    assert generator.build_table() == committed, (
        "harness_compatibility.json is stale; regenerate with: "
        "uv run --script scripts/generate_harness_compatibility.py"
    )
