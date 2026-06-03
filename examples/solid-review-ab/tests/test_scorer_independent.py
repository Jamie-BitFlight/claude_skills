"""Independent correctness tests for runner/scorer.py.

Authorship note
---------------
These tests were authored from first-principles definitions, NOT derived from
the scorer's output or the existing test_scorer.py.  Expected values are
hand-computed from the definitions below and then verified against the scorer.
Any discrepancy between the hand value and the scorer output is a FINDING to
report, not a reason to adjust the expected value.

Definitions encoded as expected values
---------------------------------------
Match rule
    A reported (group, location) matches a gold positive when both the group
    field equals the gold entry's group AND
    normalize_location(location) equals the gold entry's normalised location
    AND the finding's verdict is VIOLATION (non-PASS).

Precision  = TP / (TP + FP)
Recall     = TP / (TP + FN)
F1         = 2 * P * R / (P + R)  -- defined as 0.0 when P + R == 0

Positives for recall
    Gold entries whose kind is ``true_violation`` or ``systematic_miss``.

Decoy entries (kind ``decoy_false_positive``)
    These are NEGATIVES.  Reporting a (group, location) that coincides with
    a decoy entry is a false positive and is counted in the decoy FP rate.

normalize_location contract
    - Strips a leading ``/`` from the path component (absolute → repo-relative).
    - Trims surrounding whitespace.
    - Keeps the full directory prefix; same-basename files in different
      directories remain DISTINCT.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest
from runner.scorer import ArmBExtras, ArmMetrics, compute_metrics, normalize_location, score_arm_a, score_arm_b

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sets(
    tp_keys: list[tuple[str, str]], fp_keys: list[tuple[str, str]], fn_keys: list[tuple[str, str]]
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    """Build (reported, gold_positives, gold_decoys) sets from TP/FP/FN lists.

    Returns:
        A triple of (reported, gold_positives, gold_decoys).
        gold_decoys is always empty — callers add decoys separately when needed.
    """
    reported: set[tuple[str, str]] = set(tp_keys) | set(fp_keys)
    gold_positives: set[tuple[str, str]] = set(tp_keys) | set(fn_keys)
    return reported, gold_positives, set()


def _arm_a_text(entries: list[dict[str, str]]) -> str:
    """Build a fixed-schema findings text for a list of field dicts.

    Each dict must have keys: group, rule, location, verdict, severity.

    Args:
        entries: List of field mappings, one per finding block.

    Returns:
        Multi-line text in the fixed candidate schema understood by parse_report.
    """
    blocks: list[str] = []
    for e in entries:
        block = textwrap.dedent(f"""\
            - group: {e["group"]}
              rule: {e["rule"]}
              location: {e["location"]}
              verdict: {e["verdict"]}
              severity: {e["severity"]}
              evidence: "synthetic"
        """)
        blocks.append(block)
    return "\n".join(blocks)


def _worker_text(entries: list[dict[str, str]]) -> str:
    """Build worker-report text identical to _arm_a_text.

    Args:
        entries: List of field mappings, one per finding block.

    Returns:
        Multi-line text in the fixed candidate schema understood by parse_report.
    """
    return _arm_a_text(entries)


# ---------------------------------------------------------------------------
# Test 1 — Synthetic gold set with known TP/FP/FN
# ---------------------------------------------------------------------------


def test_compute_metrics_mixed_tp_fp_fn_expected_values() -> None:
    """Verify exact P/R/F1 for a hand-specified mix of TP, FP, and FN.

    Setup
    -----
    Gold positives (3 entries):
        (S, corpus/cases/f1.py:10)
        (S, corpus/cases/f2.py:20)
        (O, corpus/cases/f3.py:30)

    Gold decoys (1 entry):
        (S, corpus/cases/decoy.py:99)

    Reported (3 findings):
        (S, corpus/cases/f1.py:10)   -- TP
        (S, corpus/cases/decoy.py:99)  -- FP and decoy hit
        (O, corpus/cases/f4.py:40)   -- FP (unknown, not a gold positive)

    Hand-computed
    -------------
    TP = 1  FP = 2  FN = 2
    Precision = 1 / (1+2) = 1/3
    Recall    = 1 / (1+2) = 1/3
    F1        = 2*(1/3)*(1/3) / ((1/3)+(1/3)) = (2/9)/(2/3) = 1/3
    decoys_flagged = 1  total_gold_decoys = 1  decoy_rate = 1.0
    """
    # Arrange
    gold_positives = {("S", "corpus/cases/f1.py:10"), ("S", "corpus/cases/f2.py:20"), ("O", "corpus/cases/f3.py:30")}
    gold_decoys = {("S", "corpus/cases/decoy.py:99")}
    reported = {("S", "corpus/cases/f1.py:10"), ("S", "corpus/cases/decoy.py:99"), ("O", "corpus/cases/f4.py:40")}

    # Act
    metrics = compute_metrics(reported, gold_positives, gold_decoys)

    # Assert — hand-computed values
    assert metrics.true_positives == 1
    assert metrics.false_positives == 2
    assert metrics.false_negatives == 2
    assert metrics.decoys_flagged == 1
    assert metrics.total_gold_decoys == 1
    assert metrics.precision == pytest.approx(1 / 3, rel=1e-6)
    assert metrics.recall == pytest.approx(1 / 3, rel=1e-6)
    assert metrics.f1 == pytest.approx(1 / 3, rel=1e-6)
    assert metrics.decoy_false_positive_rate == pytest.approx(1.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 2 — Perfect recall / perfect precision cases
# ---------------------------------------------------------------------------


def test_compute_metrics_perfect_recall_imperfect_precision() -> None:
    """Perfect recall (all positives found) with one spurious FP lowers precision.

    Hand-computed
    -------------
    Gold positives: {(S,f1:10),(S,f2:20)}
    Reported:       {(S,f1:10),(S,f2:20),(O,extra:50)}

    TP=2  FP=1  FN=0
    Precision = 2/(2+1) = 2/3
    Recall    = 2/(2+0) = 1.0
    F1        = 2*(2/3)*1 / ((2/3)+1) = (4/3) / (5/3) = 4/5 = 0.8
    """
    # Arrange
    gold_positives = {("S", "f1.py:10"), ("S", "f2.py:20")}
    reported = {("S", "f1.py:10"), ("S", "f2.py:20"), ("O", "extra.py:50")}

    # Act
    metrics = compute_metrics(reported, gold_positives, set())

    # Assert
    assert metrics.precision == pytest.approx(2 / 3, rel=1e-6)
    assert metrics.recall == pytest.approx(1.0, rel=1e-6)
    assert metrics.f1 == pytest.approx(0.8, rel=1e-6)


def test_compute_metrics_perfect_precision_imperfect_recall() -> None:
    """Perfect precision (no spurious findings) with one missed positive lowers recall.

    Hand-computed
    -------------
    Gold positives: {(S,f1:10),(S,f2:20)}
    Reported:       {(S,f1:10)}

    TP=1  FP=0  FN=1
    Precision = 1/(1+0) = 1.0
    Recall    = 1/(1+1) = 0.5
    F1        = 2*1*0.5 / (1+0.5) = 1 / 1.5 = 2/3
    """
    # Arrange
    gold_positives = {("S", "f1.py:10"), ("S", "f2.py:20")}
    reported = {("S", "f1.py:10")}

    # Act
    metrics = compute_metrics(reported, gold_positives, set())

    # Assert
    assert metrics.precision == pytest.approx(1.0, rel=1e-6)
    assert metrics.recall == pytest.approx(0.5, rel=1e-6)
    assert metrics.f1 == pytest.approx(2 / 3, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 3 — Empty findings: no ZeroDivisionError, F1 == 0.0
# ---------------------------------------------------------------------------


def test_compute_metrics_empty_findings_produces_zero_scores_no_error() -> None:
    """Empty reported set must yield F1 == 0.0 without raising ZeroDivisionError.

    With TP=FP=0, P+R==0 guard applies: F1 defined as 0.0, not division by zero.

    Hand-computed
    -------------
    Reported: {}
    Gold positives: {(S,f1:10),(O,f2:20)}

    TP=0  FP=0  FN=2
    Precision: (TP+FP)==0 → 0.0 (guard)
    Recall   = 0 / (0+2) = 0.0
    F1: (P+R)==0 → 0.0 (guard)
    """
    # Arrange
    gold_positives = {("S", "cases/f1.py:10"), ("O", "cases/f2.py:20")}
    reported: set[tuple[str, str]] = set()

    # Act — must not raise
    metrics = compute_metrics(reported, gold_positives, set())

    # Assert
    assert metrics.true_positives == 0
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 2
    assert metrics.precision == pytest.approx(0.0, abs=1e-9)
    assert metrics.recall == pytest.approx(0.0, abs=1e-9)
    assert metrics.f1 == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Test 4 — Decoy handling
# ---------------------------------------------------------------------------


def test_compute_metrics_decoy_flagged_increases_decoy_fp_rate() -> None:
    """A finding at a decoy (group, location) is counted as FP and raises decoy rate.

    Hand-computed
    -------------
    Gold positives: {(S,pos.py:10)}
    Gold decoys:    {(O,decoy.py:5)}
    Reported:       {(O,decoy.py:5)}  -- hits decoy, misses positive

    TP=0  FP=1  FN=1  decoys_flagged=1  total_gold_decoys=1
    decoy_false_positive_rate = 1/1 = 1.0
    """
    # Arrange
    gold_positives = {("S", "cases/pos.py:10")}
    gold_decoys = {("O", "cases/decoy.py:5")}
    reported = {("O", "cases/decoy.py:5")}

    # Act
    metrics = compute_metrics(reported, gold_positives, gold_decoys)

    # Assert
    assert metrics.true_positives == 0
    assert metrics.false_positives == 1
    assert metrics.decoys_flagged == 1
    assert metrics.total_gold_decoys == 1
    assert metrics.decoy_false_positive_rate == pytest.approx(1.0, rel=1e-6)


def test_compute_metrics_true_positive_leaves_decoy_rate_zero() -> None:
    """A finding at a gold positive that does NOT touch any decoy leaves decoy rate at 0.

    Hand-computed
    -------------
    Gold positives: {(S,pos.py:10)}
    Gold decoys:    {(O,decoy.py:5)}
    Reported:       {(S,pos.py:10)}  -- hits positive, not decoy

    TP=1  FP=0  FN=0  decoys_flagged=0
    decoy_false_positive_rate = 0/1 = 0.0
    """
    # Arrange
    gold_positives = {("S", "cases/pos.py:10")}
    gold_decoys = {("O", "cases/decoy.py:5")}
    reported = {("S", "cases/pos.py:10")}

    # Act
    metrics = compute_metrics(reported, gold_positives, gold_decoys)

    # Assert
    assert metrics.true_positives == 1
    assert metrics.decoys_flagged == 0
    assert metrics.decoy_false_positive_rate == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Test 5 — normalize_location equivalence
# ---------------------------------------------------------------------------


def test_normalize_location_absolute_path_equals_relative_path() -> None:
    """An absolute path and a repo-relative path for the same file+line normalise equal.

    The leading '/' on the absolute form must be stripped so the two keys match.
    """
    # Arrange
    absolute_form = "/corpus/cases/01_srp_god_object.py:12"
    relative_form = "corpus/cases/01_srp_god_object.py:12"

    # Act
    norm_abs = normalize_location(absolute_form)
    norm_rel = normalize_location(relative_form)

    # Assert — same normalised key
    assert norm_abs == norm_rel
    assert norm_abs == "corpus/cases/01_srp_god_object.py:12"


def test_normalize_location_same_basename_different_dirs_remain_distinct() -> None:
    """Files with identical basenames in different directories must NOT collapse.

    Collapsing them would fabricate false corroboration across unrelated files.
    """
    # Arrange
    src_path = "src/foo/config.py:10"
    test_path = "tests/foo/config.py:10"

    # Act
    norm_src = normalize_location(src_path)
    norm_test = normalize_location(test_path)

    # Assert — they must differ
    assert norm_src != norm_test
    assert norm_src == "src/foo/config.py:10"
    assert norm_test == "tests/foo/config.py:10"


def test_normalize_location_whitespace_is_trimmed() -> None:
    """Leading/trailing whitespace in the raw location must be stripped.

    This prevents phantom mismatches when a worker report has trailing spaces.
    """
    # Arrange — whitespace around the path:line token
    raw_with_spaces = "  corpus/cases/02_ocp.py:25  "

    # Act
    result = normalize_location(raw_with_spaces)

    # Assert
    assert result == "corpus/cases/02_ocp.py:25"


# ---------------------------------------------------------------------------
# Test 6 — E1 ablation via score_arm_b: threshold 1 vs 2
# ---------------------------------------------------------------------------


def test_score_arm_b_e1_ablation_threshold_2_drops_lone_true_positive(tmp_path: Path) -> None:
    """keep_threshold=2 drops lone findings even when they are true positives.

    Setup
    -----
    Gold positives: {(S,c1:10),(O,c2:20),(D,c3:30)}
    Gold decoys:    {(L,d1:1)}

    Worker 1 reports: (S,c1:10) and (O,c2:20)   -- two TPs
    Worker 2 reports: (S,c1:10) only             -- corroborates c1

    After reduce:
        (S,c1:10)  weight=2  (corroborated by workers 1 and 2)
        (O,c2:20)  weight=1  (lone — only worker 1)

    At threshold=1 (keep all): reported = {(S,c1:10),(O,c2:20)}
        TP=2  FP=0  FN=1
        Precision=1.0  Recall=2/3  F1=2*1*(2/3)/(1+2/3)=(4/3)/(5/3)=4/5=0.8

    At threshold=2 (require corroboration): reported = {(S,c1:10)}
        TP=1  FP=0  FN=2
        Precision=1.0  Recall=1/3  F1=2*1*(1/3)/(1+1/3)=(2/3)/(4/3)=0.5

    f1_delta = 0.5 - 0.8 = -0.3
    (The corroboration gate hurts F1 here because it drops a true positive.)
    """
    # Arrange — worker report files in tmp_path
    worker1_entries = [
        {"group": "S", "rule": "SRP-1", "location": "corpus/c1.py:10", "verdict": "VIOLATION", "severity": "high"},
        {"group": "O", "rule": "OCP-1", "location": "corpus/c2.py:20", "verdict": "VIOLATION", "severity": "high"},
    ]
    worker2_entries = [
        {"group": "S", "rule": "SRP-1", "location": "corpus/c1.py:10", "verdict": "VIOLATION", "severity": "high"}
    ]

    (tmp_path / "worker-1.md").write_text(_worker_text(worker1_entries), encoding="utf-8")
    (tmp_path / "worker-2.md").write_text(_worker_text(worker2_entries), encoding="utf-8")

    gold_positives = {("S", "corpus/c1.py:10"), ("O", "corpus/c2.py:20"), ("D", "corpus/c3.py:30")}
    gold_decoys = {("L", "corpus/d1.py:1")}

    # Act
    metrics, extras, _warnings = score_arm_b(tmp_path, gold_positives, gold_decoys)

    # Assert — ArmBExtras carries the E1 ablation values
    assert isinstance(extras, ArmBExtras)
    assert extras.f1_at_threshold_1 == pytest.approx(0.8, rel=1e-6)
    assert extras.f1_at_threshold_2 == pytest.approx(0.5, rel=1e-6)
    assert extras.f1_delta == pytest.approx(-0.3, rel=1e-6)

    # The primary metrics (at threshold=2) match the hand-computed values
    assert metrics.true_positives == 1
    assert metrics.false_negatives == 2
    assert metrics.f1 == pytest.approx(0.5, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 7 — Parametrised (TP, FP, FN) → (precision, recall, F1) table
# ---------------------------------------------------------------------------

# Hand-computed expected values:
#
#  tp fp fn | precision         recall             f1
#  2  1  1  | 2/3 ≈ 0.6667      2/3 ≈ 0.6667       2/3 ≈ 0.6667
#  3  0  0  | 1.0               1.0                1.0
#  0  0  2  | 0.0 (P+R guard)   0.0                0.0
#  0  2  2  | 0.0               0.0                0.0
#  1  3  0  | 0.25              1.0                0.4
#
# Row derivations:
#  (2,1,1): P=2/3, R=2/3, F1=2*(4/9)/(4/3)=2/3
#  (3,0,0): P=1, R=1, F1=1
#  (0,0,2): no findings → P guard=0, R=0/2=0, F1=P+R guard=0
#  (0,2,2): P=0/(0+2)=0, R=0/(0+2)=0, F1=0+0 guard=0
#  (1,3,0): P=1/4=0.25, R=1/1=1.0, F1=2*0.25*1/(0.25+1)=0.5/1.25=0.4


@pytest.mark.parametrize(
    ("tp", "fp", "fn", "expected_precision", "expected_recall", "expected_f1"),
    [
        (2, 1, 1, 2 / 3, 2 / 3, 2 / 3),
        (3, 0, 0, 1.0, 1.0, 1.0),
        (0, 0, 2, 0.0, 0.0, 0.0),
        (0, 2, 2, 0.0, 0.0, 0.0),
        (1, 3, 0, 0.25, 1.0, 0.4),
    ],
)
def test_compute_metrics_parametrised_prf1_table(
    tp: int, fp: int, fn: int, expected_precision: float, expected_recall: float, expected_f1: float
) -> None:
    """Verify P/R/F1 for tabulated (TP, FP, FN) scenarios computed by hand.

    Each expected value was derived algebraically from the definitions before
    running the scorer.  A mismatch here is a scorer bug, not a test bug.

    Args:
        tp: Number of true positives.
        fp: Number of false positives (non-decoy for simplicity).
        fn: Number of false negatives.
        expected_precision: Hand-computed precision.
        expected_recall: Hand-computed recall.
        expected_f1: Hand-computed F1.
    """
    # Arrange — build synthetic keys to get the right set sizes
    tp_keys = [("S", f"tp_file_{i}.py:1") for i in range(tp)]
    fp_keys = [("O", f"fp_file_{i}.py:1") for i in range(fp)]
    fn_keys = [("D", f"fn_file_{i}.py:1") for i in range(fn)]

    reported, gold_positives, gold_decoys = _make_sets(tp_keys, fp_keys, fn_keys)

    # Act
    metrics = compute_metrics(reported, gold_positives, gold_decoys)

    # Assert — hand-computed literals
    assert metrics.precision == pytest.approx(expected_precision, rel=1e-6, abs=1e-9)
    assert metrics.recall == pytest.approx(expected_recall, rel=1e-6, abs=1e-9)
    assert metrics.f1 == pytest.approx(expected_f1, rel=1e-6, abs=1e-9)


# ---------------------------------------------------------------------------
# Bonus — score_arm_a end-to-end: parses file, normalises paths, computes P/R/F1
# ---------------------------------------------------------------------------


def test_score_arm_a_end_to_end_matches_hand_computed_values(tmp_path: Path) -> None:
    """score_arm_a reads a real file, normalises locations, and scores correctly.

    Verifies the full stack from file text → parse_report → reported_keys →
    compute_metrics, independent of compute_metrics tests above.

    Setup
    -----
    File contains two VIOLATION findings:
        (S, corpus/cases/pos1.py:10)  -- matches gold positive (TP)
        (O, corpus/cases/unknown.py:5)  -- not in gold (FP)

    Gold positives: {(S, corpus/cases/pos1.py:10), (D, corpus/cases/pos2.py:30)}
    Gold decoys: empty

    Hand-computed
    -------------
    TP=1  FP=1  FN=1
    Precision = 1/2 = 0.5
    Recall    = 1/2 = 0.5
    F1        = 2*0.5*0.5/(0.5+0.5) = 0.5
    """
    # Arrange
    findings_text = _arm_a_text([
        {
            "group": "S",
            "rule": "SRP-1",
            "location": "corpus/cases/pos1.py:10",
            "verdict": "VIOLATION",
            "severity": "high",
        },
        {
            "group": "O",
            "rule": "OCP-1",
            "location": "corpus/cases/unknown.py:5",
            "verdict": "VIOLATION",
            "severity": "medium",
        },
    ])
    findings_file = tmp_path / "arm_a_findings.md"
    findings_file.write_text(findings_text, encoding="utf-8")

    gold_positives = {("S", "corpus/cases/pos1.py:10"), ("D", "corpus/cases/pos2.py:30")}
    gold_decoys: set[tuple[str, str]] = set()

    # Act
    metrics, warnings = score_arm_a(findings_file, gold_positives, gold_decoys)

    # Assert — hand-computed values
    assert isinstance(metrics, ArmMetrics)
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(0.5, rel=1e-6)
    assert metrics.recall == pytest.approx(0.5, rel=1e-6)
    assert metrics.f1 == pytest.approx(0.5, rel=1e-6)
    assert isinstance(warnings, list)


def test_score_arm_a_pass_verdict_is_excluded_from_reported_set(tmp_path: Path) -> None:
    """PASS verdicts must NOT contribute to the reported set.

    A finding at a gold positive with verdict PASS must NOT count as TP.
    Only VIOLATION (non-PASS) findings contribute.

    Hand-computed
    -------------
    Reported VIOLATION at pos2 only; pos1 has PASS (excluded).
    Gold positives: {pos1, pos2}

    TP=1  FP=0  FN=1
    Precision=1.0  Recall=0.5  F1=2/3
    """
    # Arrange
    findings_text = _arm_a_text([
        {"group": "S", "rule": "SRP-1", "location": "corpus/pos1.py:5", "verdict": "PASS", "severity": "low"},
        {"group": "O", "rule": "OCP-1", "location": "corpus/pos2.py:9", "verdict": "VIOLATION", "severity": "high"},
    ])
    findings_file = tmp_path / "arm_a.md"
    findings_file.write_text(findings_text, encoding="utf-8")

    gold_positives = {("S", "corpus/pos1.py:5"), ("O", "corpus/pos2.py:9")}

    # Act
    metrics, _warnings = score_arm_a(findings_file, gold_positives, set())

    # Assert — pos1 PASS excluded: TP=1, FN=1, FP=0
    assert metrics.true_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.false_positives == 0
    assert metrics.precision == pytest.approx(1.0, rel=1e-6)
    assert metrics.recall == pytest.approx(0.5, rel=1e-6)
    assert metrics.f1 == pytest.approx(2 / 3, rel=1e-6)
