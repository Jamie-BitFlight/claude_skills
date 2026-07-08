"""Score-path integration tests: _load_run_meta and _score_arm.

These tests verify the full score path from on-disk artefacts to ArmMetrics.
Expected values are hand-computed from first principles before the scorer is
invoked.  Any discrepancy is a scorer bug, not a reason to adjust the expected
value.

Hand-computed expected values
-----------------------------
Prices used (from arms.yaml):
  claude-sonnet-4-5:  input_per_1k=0.003, output_per_1k=0.015
  claude-haiku-4-5:   input_per_1k=0.00025, output_per_1k=0.00125

Single arm (sonnet, input=1000, output=200):
  cost = (1000/1000 * 0.003) + (200/1000 * 0.015) = 0.003 + 0.003 = 0.006 USD

Ensemble arm (haiku, input=4000, output=800):
  cost = (4000/1000 * 0.00025) + (800/1000 * 0.00125) = 0.001 + 0.001 = 0.002 USD

Gold set: 2 positives.
  TP (reported): group=S, location=src/service.py:42
  FN (missed):  group=O, location=src/repository.py:10

Single arm findings: 1 TP, 0 FP, 1 FN (one gold positive not reported):
  P = 1/(1+0) = 1.0
  R = 1/(1+1) = 0.5
  F1 = 2*P*R/(P+R) = 2*1.0*0.5/1.5 = 2/3 ~= 0.6667

Ensemble arm findings (2 workers each report the TP; deduplicated by scorer):
  After dedup: 1 TP, 0 FP, 1 FN -> same P/R/F1 as single arm above.

Note on location format: gold keys and reported locations must both be in
path:line format (e.g. src/service.py:42) so that normalize_location() is a
no-op on both sides and the set intersection in compute_metrics() finds matches.
The ::ClassName notation normalises to a different string and must not be used.
"""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Bootstrap sys.path so runner.* imports resolve when pytest is invoked from
# the repo root (same technique as cli.py).
# ---------------------------------------------------------------------------
import sys
import textwrap
from pathlib import Path

import pytest

_EXPERIMENT_ROOT = Path(__file__).parent.parent
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

# _load_run_meta and _score_arm are module-private helpers in cli.py.
# Import them directly for white-box testing of the score path.
from runner.cli import _load_run_meta, _score_arm
from runner.manifest import ArmEntry, ArmType, ModelPrice, ModelRef

# ---------------------------------------------------------------------------
# Constants — shared across tests
# ---------------------------------------------------------------------------

# Gold positive: one (group, location) pair the arm must find.
# Location uses path:line format (the canonical form that normalize_location
# preserves unchanged) so gold keys and normalised reported keys can match.
_TP_GROUP = "S"
_TP_LOC = "src/service.py:42"

# Second gold positive that arms deliberately miss → FN.
_FN_GROUP = "O"
_FN_LOC = "src/repository.py:10"

_POS_KEYS: set[tuple[str, str]] = {(_TP_GROUP, _TP_LOC), (_FN_GROUP, _FN_LOC)}
_DEC_KEYS: set[tuple[str, str]] = set()

# Prices matching arms.yaml values (passed to _score_arm as a plain dict of ModelPrice).
_PRICES: dict[str, ModelPrice] = {
    "claude-sonnet-4-5": ModelPrice(input_per_1k=0.003, output_per_1k=0.015),
    "claude-haiku-4-5": ModelPrice(input_per_1k=0.00025, output_per_1k=0.00125),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding_block(group: str, rule: str, location: str, verdict: str, severity: str) -> str:
    """Build one finding block in the fixed schema understood by parse_report.

    Args:
        group: SOLID group letter (S/O/L/I/D).
        rule: Rule identifier string.
        location: File path and class/method.
        verdict: VIOLATION or PASS.
        severity: Severity label (e.g. high, medium).

    Returns:
        Multi-line YAML-list block for one finding.
    """
    return textwrap.dedent(f"""\
        - group: {group}
          rule: {rule}
          location: {location}
          verdict: {verdict}
          severity: {severity}
          evidence: "synthetic"
    """)


def _write_run_meta(findings_dir: Path, input_tokens: int, output_tokens: int, duration_ms: float) -> None:
    """Write a synthetic run-meta.json to findings_dir.

    Args:
        findings_dir: Directory to create and write run-meta.json into.
        input_tokens: Synthetic input token count.
        output_tokens: Synthetic output token count.
        duration_ms: Synthetic wall-clock duration in milliseconds.
    """
    findings_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "total_cost_usd_reported": 0.0,
    }
    (findings_dir / "run-meta.json").write_text(json.dumps(meta), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def single_arm_dir(tmp_path: Path) -> Path:
    """Build a minimal single-arm findings tree.

    Tree layout::

        tmp_path/
          findings/
            run-meta.json  — input=1000, output=200, duration_ms=5000
            findings.md    — 1 TP (S, src/service.py::UserService), VIOLATION

    Returns:
        tmp_path (the arm root directory).
    """
    findings_dir = tmp_path / "findings"
    _write_run_meta(findings_dir, input_tokens=1000, output_tokens=200, duration_ms=5000.0)

    tp_block = _finding_block(group=_TP_GROUP, rule="SRP-1", location=_TP_LOC, verdict="VIOLATION", severity="high")
    (findings_dir / "findings.md").write_text(tp_block, encoding="utf-8")
    return tmp_path


@pytest.fixture
def ensemble_arm_dir(tmp_path: Path) -> Path:
    """Build a minimal ensemble-arm findings tree.

    Two workers each report the same TP finding.  After deduplication by the
    scorer the result is 1 TP, 0 FP, 1 FN — identical metrics to single_arm_dir.

    Tree layout::

        tmp_path/
          findings/
            run-meta.json         — input=4000, output=800, duration_ms=8000
            workers/
              worker-0.md         — 1 TP finding
              worker-1.md         — same TP finding (duplicate; deduplicated by scorer)

    Returns:
        tmp_path (the arm root directory).
    """
    findings_dir = tmp_path / "findings"
    _write_run_meta(findings_dir, input_tokens=4000, output_tokens=800, duration_ms=8000.0)

    workers_dir = findings_dir / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)

    tp_block = _finding_block(group=_TP_GROUP, rule="SRP-1", location=_TP_LOC, verdict="VIOLATION", severity="high")
    (workers_dir / "worker-0.md").write_text(tp_block, encoding="utf-8")
    (workers_dir / "worker-1.md").write_text(tp_block, encoding="utf-8")
    return tmp_path


def _make_single_arm(arm_dir: Path) -> ArmEntry:
    """Construct an ArmEntry for a single arm rooted at arm_dir.

    Args:
        arm_dir: Arm root directory (tmp_path from a fixture).

    Returns:
        ArmEntry with arm_type=SINGLE and a Sonnet primary model.
    """
    return ArmEntry(
        name="test-single",
        dir=arm_dir,
        enabled=True,
        arm_type=ArmType.SINGLE,
        models=[ModelRef(id="claude-sonnet-4-5", role="primary")],
    )


def _make_ensemble_arm(arm_dir: Path) -> ArmEntry:
    """Construct an ArmEntry for an ensemble arm rooted at arm_dir.

    Args:
        arm_dir: Arm root directory (tmp_path from a fixture).

    Returns:
        ArmEntry with arm_type=ENSEMBLE and a Haiku primary model.
    """
    return ArmEntry(
        name="test-ensemble",
        dir=arm_dir,
        enabled=True,
        arm_type=ArmType.ENSEMBLE,
        models=[ModelRef(id="claude-haiku-4-5", role="primary")],
    )


# ---------------------------------------------------------------------------
# _load_run_meta tests
# ---------------------------------------------------------------------------


def test_load_run_meta_present(single_arm_dir: Path) -> None:
    """_load_run_meta returns the persisted token counts and timing."""
    meta = _load_run_meta(single_arm_dir)
    assert meta["input_tokens"] == 1000
    assert meta["output_tokens"] == 200
    assert meta["duration_ms"] == pytest.approx(5000.0)
    assert meta["total_cost_usd_reported"] == pytest.approx(0.0)


def test_load_run_meta_absent(tmp_path: Path) -> None:
    """_load_run_meta returns all-zeros when run-meta.json does not exist."""
    meta = _load_run_meta(tmp_path)
    assert meta["input_tokens"] == 0
    assert meta["output_tokens"] == 0
    assert meta["duration_ms"] == pytest.approx(0.0)
    assert meta["total_cost_usd_reported"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _score_arm — single arm
# ---------------------------------------------------------------------------


def test_score_arm_single_metrics(single_arm_dir: Path) -> None:
    """Single arm: F1=2/3, cost=0.006 USD from hand-computed expected values."""
    arm = _make_single_arm(single_arm_dir)
    extras_out: dict = {}
    metrics = _score_arm(arm, _POS_KEYS, _DEC_KEYS, _PRICES, extras_out)

    assert metrics is not None
    assert metrics.true_positives == 1
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(1.0)
    assert metrics.recall == pytest.approx(0.5)
    assert metrics.f1 == pytest.approx(2 / 3)
    # cost = (1000/1000 * 0.003) + (200/1000 * 0.015) = 0.006 USD
    assert metrics.cost_usd == pytest.approx(0.006)
    assert metrics.latency_ms == pytest.approx(5000.0)
    # No ensemble extras for a single arm.
    assert extras_out == {}


def test_score_arm_single_no_findings(tmp_path: Path) -> None:
    """Single arm: returns None when findings.md is absent."""
    findings_dir = tmp_path / "findings"
    _write_run_meta(findings_dir, input_tokens=100, output_tokens=10, duration_ms=1000.0)
    # findings.md deliberately not written.

    arm = _make_single_arm(tmp_path)
    result = _score_arm(arm, _POS_KEYS, _DEC_KEYS, _PRICES, {})
    assert result is None


# ---------------------------------------------------------------------------
# _score_arm — ensemble arm
# ---------------------------------------------------------------------------


def test_score_arm_ensemble_metrics(ensemble_arm_dir: Path) -> None:
    """Ensemble arm: deduplication yields 1 TP, cost=0.002 USD from hand-computed values."""
    arm = _make_ensemble_arm(ensemble_arm_dir)
    extras_out: dict = {}
    metrics = _score_arm(arm, _POS_KEYS, _DEC_KEYS, _PRICES, extras_out)

    assert metrics is not None
    assert metrics.true_positives == 1
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(1.0)
    assert metrics.recall == pytest.approx(0.5)
    assert metrics.f1 == pytest.approx(2 / 3)
    # cost = (4000/1000 * 0.00025) + (800/1000 * 0.00125) = 0.001 + 0.001 = 0.002 USD
    assert metrics.cost_usd == pytest.approx(0.002)
    assert metrics.latency_ms == pytest.approx(8000.0)
    # Ensemble extras should be populated.
    assert arm.name in extras_out


def test_score_arm_ensemble_missing_workers(tmp_path: Path) -> None:
    """Ensemble arm: returns None and emits warning when workers/ directory is absent."""
    findings_dir = tmp_path / "findings"
    _write_run_meta(findings_dir, input_tokens=100, output_tokens=10, duration_ms=1000.0)
    # workers/ directory deliberately not created.

    arm = _make_ensemble_arm(tmp_path)
    result = _score_arm(arm, _POS_KEYS, _DEC_KEYS, _PRICES, {})
    assert result is None
