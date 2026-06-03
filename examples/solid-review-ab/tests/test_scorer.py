"""Unit tests for the pure scoring engine.

Tests authored independently of the scorer implementation, against known
desired behaviour — each test states the expected outcome before any code
is referenced.  The test is the specification; the scorer is the implementation.

These tests are NOT end-to-end: they do not call claude -p, do not read real
arm output files, and do not touch the network.  The scorer is pure by design.
"""

from __future__ import annotations

import textwrap
from itertools import starmap
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers to build synthetic findings text in the fixed schema
# ---------------------------------------------------------------------------


def _finding(group: str, location: str, verdict: str = "VIOLATION", severity: str = "high") -> str:
    """Build one finding block in the fixed arm output schema.

    Args:
        group: SOLID group letter.
        location: Raw location string (may be absolute or relative).
        verdict: VIOLATION or PASS.
        severity: critical | high | medium | low.

    Returns:
        One findings block as a string.
    """
    return textwrap.dedent(f"""\
        - group: {group}
          rule: some-rule-slug
          location: {location}
          verdict: {verdict}
          severity: {severity}
          evidence: "some code snippet"
    """)


def _findings_text(*blocks: str) -> str:
    """Concatenate findings blocks with blank-line separators.

    Args:
        *blocks: Individual finding block strings.

    Returns:
        Combined findings file content.
    """
    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gold_positives() -> set[tuple[str, str]]:
    """Four gold positive (group, location) keys."""
    return {
        ("S", "corpus/cases/01_srp_god_object.py:17"),
        ("S", "corpus/cases/01_srp_god_object.py:57"),
        ("O", "corpus/cases/02_ocp_type_dispatch.py:19"),
        ("L", "corpus/cases/03_lsp_precondition.py:62"),
    }


@pytest.fixture
def gold_decoys() -> set[tuple[str, str]]:
    """Two gold decoy (group, location) keys."""
    return {("D", "corpus/cases/01_srp_god_object.py:102"), ("O", "corpus/cases/02_ocp_type_dispatch.py:89")}


# ---------------------------------------------------------------------------
# normalize_location contract
# ---------------------------------------------------------------------------


def test_normalize_location_strips_leading_slash() -> None:
    """normalize_location must strip a leading / to produce repo-relative paths.

    This is the exact contract from reduce.py — the scorer must match it.
    """
    from runner.scorer import normalize_location

    assert normalize_location("/corpus/cases/01.py:17") == "corpus/cases/01.py:17"


def test_normalize_location_preserves_directory() -> None:
    """normalize_location must preserve the directory portion, not just the basename.

    Two files with the same basename in different directories must not collapse.
    """
    from runner.scorer import normalize_location

    loc_a = normalize_location("src/foo/config.py:10")
    loc_b = normalize_location("tests/foo/config.py:10")
    assert loc_a != loc_b


def test_normalize_location_trims_whitespace() -> None:
    """normalize_location must strip surrounding whitespace."""
    from runner.scorer import normalize_location

    assert normalize_location("  corpus/cases/01.py:17  ") == "corpus/cases/01.py:17"


def test_normalize_location_no_line_returns_stripped() -> None:
    """normalize_location returns stripped input when no line number is present."""
    from runner.scorer import normalize_location

    assert normalize_location("  some/path/file.py  ") == "some/path/file.py"


# ---------------------------------------------------------------------------
# compute_metrics — precision, recall, F1
# ---------------------------------------------------------------------------


def testcompute_metrics_perfect_recall_full_precision(
    gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """When reported == gold_positives exactly, P=1, R=1, F1=1, decoy_rate=0."""
    from runner.scorer import compute_metrics

    metrics = compute_metrics(gold_positives.copy(), gold_positives, gold_decoys)

    assert metrics.precision == pytest.approx(1.0)
    assert metrics.recall == pytest.approx(1.0)
    assert metrics.f1 == pytest.approx(1.0)
    assert metrics.decoys_flagged == 0
    assert metrics.decoy_false_positive_rate == pytest.approx(0.0)


def testcompute_metrics_one_tp_one_fn_one_fp(
    gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """Known TP=2, FP=1, FN=2 from a 4-positive gold and 3-element reported set.

    Reported: 2 TPs + 1 FP (not a decoy).
    Expected: P=2/3, R=2/4=0.5, F1=2*(2/3)*(0.5)/((2/3)+0.5).
    """
    from runner.scorer import compute_metrics

    reported = {
        ("S", "corpus/cases/01_srp_god_object.py:17"),  # TP
        ("O", "corpus/cases/02_ocp_type_dispatch.py:19"),  # TP
        ("D", "corpus/cases/totally_invented.py:99"),  # FP (not a decoy)
    }
    metrics = compute_metrics(reported, gold_positives, gold_decoys)

    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 2
    assert metrics.decoys_flagged == 0
    assert metrics.precision == pytest.approx(2 / 3)
    assert metrics.recall == pytest.approx(2 / 4)
    expected_f1 = 2 * (2 / 3) * 0.5 / ((2 / 3) + 0.5)
    assert metrics.f1 == pytest.approx(expected_f1)


def testcompute_metrics_decoy_flagged(gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]) -> None:
    """Flagging a decoy counts as FP and increments decoys_flagged."""
    from runner.scorer import compute_metrics

    reported = {
        ("S", "corpus/cases/01_srp_god_object.py:17"),  # TP
        ("D", "corpus/cases/01_srp_god_object.py:102"),  # decoy FP
    }
    metrics = compute_metrics(reported, gold_positives, gold_decoys)

    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.decoys_flagged == 1
    assert metrics.decoy_false_positive_rate == pytest.approx(1 / len(gold_decoys))


def testcompute_metrics_no_findings_all_zero(
    gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """Empty reported set yields P=0, R=0, F1=0."""
    from runner.scorer import compute_metrics

    metrics = compute_metrics(set(), gold_positives, gold_decoys)

    assert metrics.precision == pytest.approx(0.0)
    assert metrics.recall == pytest.approx(0.0)
    assert metrics.f1 == pytest.approx(0.0)
    assert metrics.true_positives == 0
    assert metrics.false_negatives == len(gold_positives)


# ---------------------------------------------------------------------------
# reported_keys — schema parsing + normalization
# ---------------------------------------------------------------------------


def testreported_keys_repo_relative_path(gold_positives: set[tuple[str, str]]) -> None:
    """A VIOLATION finding with repo-relative location must produce a matching key."""
    from runner.scorer import reported_keys

    text = _finding("S", "corpus/cases/01_srp_god_object.py:17")
    keys = reported_keys(text)

    assert ("S", "corpus/cases/01_srp_god_object.py:17") in keys


def testreported_keys_absolute_path_normalised(gold_positives: set[tuple[str, str]]) -> None:
    """A VIOLATION finding with an absolute path is normalised to repo-relative."""
    from runner.scorer import reported_keys

    text = _finding("S", "/home/user/repos/claude_skills/corpus/cases/01_srp_god_object.py:17")
    keys = reported_keys(text)

    # After normalize_location strips leading /, the key matches gold
    assert any(loc.endswith("corpus/cases/01_srp_god_object.py:17") for _, loc in keys)


def testreported_keys_pass_verdict_excluded() -> None:
    """PASS verdicts must not appear in the reported keys."""
    from runner.scorer import reported_keys

    text = _finding("S", "corpus/cases/01_srp_god_object.py:17", verdict="PASS")
    keys = reported_keys(text)

    assert len(keys) == 0


def testreported_keys_multiple_findings() -> None:
    """Multiple finding blocks are all parsed and normalised."""
    from runner.scorer import reported_keys

    text = _findings_text(
        _finding("S", "corpus/cases/01_srp_god_object.py:17"),
        _finding("O", "corpus/cases/02_ocp_type_dispatch.py:19"),
        _finding("L", "corpus/cases/03_lsp_precondition.py:62", verdict="PASS"),
    )
    keys = reported_keys(text)

    assert len(keys) == 2
    assert ("S", "corpus/cases/01_srp_god_object.py:17") in keys
    assert ("O", "corpus/cases/02_ocp_type_dispatch.py:19") in keys
    assert ("L", "corpus/cases/03_lsp_precondition.py:62") not in keys


# ---------------------------------------------------------------------------
# score_arm_a — file-level integration (no LLM)
# ---------------------------------------------------------------------------


def test_score_arm_a_perfect(
    tmp_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """score_arm_a with perfect findings yields F1=1.0."""
    from runner.scorer import score_arm_a

    # Write a findings file that exactly matches all gold positives
    blocks = list(starmap(_finding, sorted(gold_positives)))
    findings_file = tmp_path / "arm-a-perfect.md"
    findings_file.write_text(_findings_text(*blocks), encoding="utf-8")

    metrics, _warnings = score_arm_a(findings_file, gold_positives, gold_decoys)

    assert metrics.f1 == pytest.approx(1.0)
    assert metrics.decoys_flagged == 0


def test_score_arm_a_missed_fn(
    tmp_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """score_arm_a with one missed gold positive produces R < 1."""
    from runner.scorer import score_arm_a

    # Report only 3 of 4 gold positives
    reported_positives = list(gold_positives)[:3]
    blocks = list(starmap(_finding, reported_positives))
    findings_file = tmp_path / "arm-a-partial.md"
    findings_file.write_text(_findings_text(*blocks), encoding="utf-8")

    metrics, _warnings = score_arm_a(findings_file, gold_positives, gold_decoys)

    assert metrics.recall < 1.0
    assert metrics.false_negatives == 1


def test_score_arm_a_decoy_flagged(
    tmp_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """score_arm_a counts a decoy hit correctly in decoy_false_positive_rate."""
    from runner.scorer import score_arm_a

    # Report all gold positives PLUS one decoy
    all_blocks = list(starmap(_finding, gold_positives))
    decoy_grp, decoy_loc = next(iter(gold_decoys))
    all_blocks.append(_finding(decoy_grp, decoy_loc))
    findings_file = tmp_path / "arm-a-decoy.md"
    findings_file.write_text(_findings_text(*all_blocks), encoding="utf-8")

    metrics, _warnings = score_arm_a(findings_file, gold_positives, gold_decoys)

    assert metrics.decoys_flagged == 1
    assert metrics.decoy_false_positive_rate > 0.0
    # Recall still 1.0 (all positives reported) but precision < 1 (one FP)
    assert metrics.recall == pytest.approx(1.0)
    assert metrics.precision < 1.0


# ---------------------------------------------------------------------------
# score_arm_b — ensemble E1 ablation
# ---------------------------------------------------------------------------


def test_score_arm_b_e1_ablation(
    tmp_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """E1 ablation: when one finding is only reported by a single worker, it
    survives threshold=1 but is dropped at threshold=2, reducing recall.

    Setup:
      - worker-A reports all 4 gold positives.
      - worker-B reports only 2 of 4 gold positives (the others are lone).
    At threshold=1: all 4 reported -> R=1.
    At threshold=2: only 2 reported by both workers -> R=0.5.
    f1_delta must be negative (precision gate hurts recall here).
    """
    from runner.scorer import score_arm_b

    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    all_pos = sorted(gold_positives)

    # worker-A: all 4
    worker_a = report_dir / "worker-A.md"
    worker_a.write_text(_findings_text(*list(starmap(_finding, all_pos))), encoding="utf-8")

    # worker-B: only first 2
    worker_b = report_dir / "worker-B.md"
    worker_b.write_text(_findings_text(*list(starmap(_finding, all_pos[:2]))), encoding="utf-8")

    metrics, extras, _warnings = score_arm_b(report_dir, gold_positives, gold_decoys, glob="worker-*.md")

    # At threshold=2: only the 2 findings reported by both workers survive
    assert metrics.true_positives == 2
    assert extras.f1_at_threshold_1 > extras.f1_at_threshold_2
    assert extras.f1_delta < 0


def test_score_arm_b_decoy_weight_tracked(
    tmp_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """E0: when multiple workers flag a decoy, per_decoy_weight records the count."""
    from runner.scorer import score_arm_b

    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    decoy_grp, decoy_loc = next(iter(gold_decoys))

    # Both workers flag the same decoy
    for name in ("worker-A.md", "worker-B.md"):
        (report_dir / name).write_text(_findings_text(_finding(decoy_grp, decoy_loc)), encoding="utf-8")

    _metrics, extras, _warnings = score_arm_b(report_dir, gold_positives, gold_decoys, glob="worker-*.md")

    assert (decoy_grp, decoy_loc) in extras.per_decoy_weight
    assert extras.per_decoy_weight[decoy_grp, decoy_loc] == 2


def test_score_arm_b_no_reports_raises(
    tmp_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> None:
    """score_arm_b raises ValueError when no worker files match the glob."""
    from runner.scorer import score_arm_b

    (tmp_path / "reports").mkdir()

    with pytest.raises(ValueError, match="No worker reports"):
        score_arm_b(tmp_path / "reports", gold_positives, gold_decoys)
