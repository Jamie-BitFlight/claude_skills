from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "discover_cross_harness_mcp_candidates.py"
_SPEC = importlib.util.spec_from_file_location("discover_cross_harness_mcp_candidates", _SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load module from {_SCRIPT_PATH}")
discovery = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = discovery
_SPEC.loader.exec_module(discovery)


def test_checkpoint_rejects_changed_page_size(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    discovery.write_checkpoint(checkpoint, [], {}, {}, 100)

    with pytest.raises(RuntimeError, match="page size"):
        discovery.load_checkpoint(checkpoint, 50)


def test_checkpoint_persists_page_size(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    discovery.write_checkpoint(checkpoint, [], {}, {}, 100)

    hits, summaries, metadata = discovery.load_checkpoint(checkpoint, 100)

    assert (hits, summaries, metadata) == ([], {}, {})
