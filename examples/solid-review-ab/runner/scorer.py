"""Pure scoring engine for the SOLID judgement system.

All public functions are pure (no LLM calls, no subprocess, no I/O beyond reading
findings files).  Import and call directly from tests or from the CLI layer.

Matching is keyed on (group, normalize_location(location)).

normalize_location delegates to reduce.py's implementation and then strips any
leading ../ segments.  reduce.py strips only a leading /, not ../; the scorer
layer adds ../ stripping because arm agents may emit arm-directory-relative paths
(e.g. ../corpus/cases/file.py:12) even though the skill instructs corpus-root-
relative paths.  The gold set always uses corpus/cases/<file>:<line>.

normalize_location is imported from reduce.py via importlib; the import is the
contract.  If reduce.py moves, update _REDUCE_PATH in this file.

Public API
----------
normalize_location(raw)                              — normalise a raw location string
parse_report(text)                                   — parse findings text -> list[Finding]
reduce_findings(reports, threshold)                  — reduce with corroboration weighting
compute_metrics(reported, pos, decoys)               — compute P/R/F1 and decoy rate
reported_keys(text)                                  — parse text -> set[(group, location)]
score_arm_a(findings_path, pos, decoys)              -> (ArmMetrics, list[str])
score_arm_a_dir(arm_dir, glob, pos, decoys)          -> (ArmMetrics, list[str])
score_arm_b(report_dir, pos, decoys[, glob])         -> (ArmMetrics, ArmBExtras, list[str])
compute_payoff_per_cost(arm_f1, baseline_f1, cost)   -> float | None
rank_arms(scored_arms)                               -> list[ArmRanking]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

# ---------------------------------------------------------------------------
# Import normalize_location and parse_report from reduce.py exactly.
# Replicating them would introduce drift — importlib is the only safe approach.
# ---------------------------------------------------------------------------
_REDUCE_PATH = (
    Path(__file__).parents[3]
    / "plugins"
    / "plugin-creator"
    / "skills"
    / "ensemble-rule-review"
    / "scripts"
    / "reduce.py"
)

# Unique sys.modules key prevents collisions with any other "reduce" module in the
# process (e.g. pytest workers loading unrelated plugins).
_REDUCE_MODULE_KEY = "_solid_ab_reduce"


def _load_reduce() -> ModuleType:
    """Load reduce.py as a module without executing __main__.

    Returns:
        The loaded reduce module with normalize_location and parse_report available.

    Raises:
        ImportError: When reduce.py cannot be found at the expected path.
    """
    if not _REDUCE_PATH.is_file():
        msg = f"reduce.py not found at {_REDUCE_PATH}; check _REDUCE_PATH in scorer.py"
        raise ImportError(msg)
    spec = spec_from_file_location(_REDUCE_MODULE_KEY, _REDUCE_PATH)
    if spec is None or spec.loader is None:
        msg = f"Cannot create module spec for {_REDUCE_PATH}"
        raise ImportError(msg)

    mod = module_from_spec(spec)
    # Register before exec_module so @dataclass decorators can resolve
    # cls.__module__ through sys.modules during module initialisation.
    sys.modules[_REDUCE_MODULE_KEY] = mod
    loader = spec.loader
    loader.exec_module(mod)
    return mod


_reduce: ModuleType = _load_reduce()


# ---------------------------------------------------------------------------
# Typed boundary wrappers for reduce.py functions.
# Thin wrappers give callers precise signatures and avoid TC001 relocation
# of Callable under TYPE_CHECKING (which would make them unavailable at runtime).
# ---------------------------------------------------------------------------


def normalize_location(raw: str) -> str:
    """Normalise a raw location string from a findings file.

    Delegates to reduce.py's normalize_location (which strips a leading /)
    then strips any leading ../ segments.  reduce.py does not strip ../
    because the ensemble-review skill operates within a single working
    directory; the scorer adds ../ stripping because arm agents may emit
    arm-directory-relative paths even though the skill instructs corpus-
    root-relative ones (corpus/cases/<file>:<line>).

    Args:
        raw: Raw location string (may contain leading /, ../, or be
            already normalised as corpus/cases/<file>:<line>).

    Returns:
        Normalised repo-relative path:line string.
    """
    result: str = _reduce.normalize_location(raw)
    while result.startswith("../"):
        result = result[3:]
    return result


def parse_report(text: str) -> list:
    """Parse one arm findings file text into a list of Finding objects.

    Args:
        text: Raw text of an arm findings file in the fixed schema.

    Returns:
        List of Finding namedtuple/dataclass instances from reduce.py.
    """
    return list(_reduce.parse_report(text))


def reduce_findings(reports: dict, keep_threshold: int) -> list:
    """Reduce per-worker findings to a merged list with corroboration weighting.

    Args:
        reports: Mapping of worker_id to list of Finding objects.
        keep_threshold: Minimum corroboration weight a finding must reach to survive.

    Returns:
        List of Merged finding objects with .group, .location, .weight.
    """
    return list(_reduce.reduce_findings(reports, keep_threshold))


# ---------------------------------------------------------------------------
# Scoring data structures
# ---------------------------------------------------------------------------


@dataclass
class ArmMetrics:
    """Precision/Recall/F1 and false-positive breakdown for one arm.

    Attributes:
        true_positives: Reported (group, loc) that match a gold positive key.
        false_positives: Reported (group, loc) not in gold positives (includes decoys).
        false_negatives: Gold positive keys not reported by the arm.
        decoys_flagged: Subset of false_positives that hit a gold decoy key.
        total_gold_decoys: Count of gold decoy entries.
        precision: TP / (TP + FP), or 0.0 when no findings.
        recall: TP / (TP + FN), or 0.0 when no gold positives.
        f1: Harmonic mean of precision and recall.
        decoy_false_positive_rate: decoys_flagged / total_gold_decoys, or 0.0.
        latency_ms: Wall-clock time the arm took (populated by the runner layer).
        cost_usd: Reported token cost (populated by the runner layer).
    """

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    decoys_flagged: int = 0
    total_gold_decoys: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    decoy_false_positive_rate: float = 0.0
    latency_ms: float = 0.0
    cost_usd: float = 0.0


@dataclass
class ArmBExtras:
    """Arm-B-specific corroboration diagnostics.

    Attributes:
        per_decoy_weight: Mapping of (group, normalised_location) to corroboration weight
            for each gold decoy key reported by at least one worker.
        f1_at_threshold_1: F1 when reduce is run with keep_threshold=1 (dedup only).
        f1_at_threshold_2: F1 when reduce is run with keep_threshold=2 (corroboration gate).
        f1_delta: f1_at_threshold_2 - f1_at_threshold_1 (E1 ablation signal).
    """

    per_decoy_weight: dict[tuple[str, str], int] = field(default_factory=dict)
    f1_at_threshold_1: float = 0.0
    f1_at_threshold_2: float = 0.0
    f1_delta: float = 0.0


# ---------------------------------------------------------------------------
# Public scoring logic
# ---------------------------------------------------------------------------


def compute_metrics(
    reported: set[tuple[str, str]], gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> ArmMetrics:
    """Compute precision/recall/F1 and decoy false-positive rate.

    Args:
        reported: Set of (group, normalised_location) pairs the arm emitted.
        gold_positives: Gold true_violation + systematic_miss keys.
        gold_decoys: Gold decoy_false_positive keys.

    Returns:
        Populated ArmMetrics (latency_ms and cost_usd default to 0.0).
    """
    tp_set = reported & gold_positives
    fp_set = reported - gold_positives
    fn_set = gold_positives - reported
    decoys_hit = reported & gold_decoys

    tp = len(tp_set)
    fp = len(fp_set)
    fn = len(fn_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    decoy_rate = len(decoys_hit) / len(gold_decoys) if gold_decoys else 0.0

    return ArmMetrics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        decoys_flagged=len(decoys_hit),
        total_gold_decoys=len(gold_decoys),
        precision=precision,
        recall=recall,
        f1=f1,
        decoy_false_positive_rate=decoy_rate,
    )


def reported_keys(findings_text: str) -> set[tuple[str, str]]:
    """Parse one arm findings file into a set of (group, normalised_location) keys.

    PASS verdicts are dropped, matching reduce.py's dedup logic.

    Args:
        findings_text: Raw text of an arm findings file in the fixed schema.

    Returns:
        Set of (group, normalised_location) tuples for VIOLATION findings.
    """
    findings = parse_report(findings_text)
    return {(f.group, normalize_location(f.location)) for f in findings if f.verdict != "PASS"}


def _path_mismatch_warning(
    arm_reported: set[tuple[str, str]], gold_positives: set[tuple[str, str]], source: Path
) -> str | None:
    """Return a warning string when no reported key matches any gold positive.

    A zero-match result almost always indicates a path-root mismatch (arm emits
    absolute paths, gold uses repo-relative).

    Args:
        arm_reported: Reported (group, location) keys from the arm.
        gold_positives: Expected positive keys from gold.
        source: Path to the findings file or directory (for the warning message).

    Returns:
        Warning string when a mismatch is detected, None otherwise.
    """
    if arm_reported and not (arm_reported & gold_positives):
        return (
            f"WARNING: zero gold-positive matches from {source}. "
            "Check that arm output uses repo-relative paths (corpus/cases/file.py:N), "
            "not absolute paths. All metrics will be zero until paths align."
        )
    return None


def score_arm_a(
    findings_path: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> tuple[ArmMetrics, list[str]]:
    """Score arm A (single-agent) from one findings file against the gold set.

    Args:
        findings_path: Path to the arm A output file (fixed schema).
        gold_positives: Gold true_violation + systematic_miss keys.
        gold_decoys: Gold decoy_false_positive keys.

    Returns:
        Tuple of (ArmMetrics, warnings).  warnings is empty when paths align.

    Raises:
        FileNotFoundError: When findings_path does not exist.
    """
    text = findings_path.read_text(encoding="utf-8")
    arm_reported = reported_keys(text)
    warnings: list[str] = []
    warning = _path_mismatch_warning(arm_reported, gold_positives, findings_path)
    if warning is not None:
        warnings.append(warning)
    return compute_metrics(arm_reported, gold_positives, gold_decoys), warnings


def score_arm_a_dir(
    arm_dir: Path, glob: str, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]]
) -> tuple[ArmMetrics, list[str]]:
    """Score arm A by aggregating all findings files in a directory.

    Aggregates all arm A files into a single set of reported keys before computing
    metrics, so the score reflects the full arm's coverage across multiple outputs.
    Mirrors the directory-level interface of score_arm_b.

    Args:
        arm_dir: Directory to search for findings files.
        glob: Glob pattern matching arm A output files.
        gold_positives: Gold true_violation + systematic_miss keys.
        gold_decoys: Gold decoy_false_positive keys.

    Returns:
        Tuple of (ArmMetrics, warnings).  warnings is empty when paths align.

    Raises:
        FileNotFoundError: When arm_dir does not exist.
        ValueError: When no findings files match glob in arm_dir.
    """
    if not arm_dir.is_dir():
        msg = f"arm_dir does not exist: {arm_dir}"
        raise FileNotFoundError(msg)

    findings_files = sorted(arm_dir.glob(glob))
    if not findings_files:
        msg = f"No findings files matching {glob!r} in {arm_dir}"
        raise ValueError(msg)

    all_reported: set[tuple[str, str]] = set()
    for f in findings_files:
        all_reported |= reported_keys(f.read_text(encoding="utf-8"))

    warnings: list[str] = []
    warning = _path_mismatch_warning(all_reported, gold_positives, arm_dir)
    if warning is not None:
        warnings.append(warning)
    return compute_metrics(all_reported, gold_positives, gold_decoys), warnings


def score_arm_b(
    report_dir: Path, gold_positives: set[tuple[str, str]], gold_decoys: set[tuple[str, str]], glob: str = "worker-*.md"
) -> tuple[ArmMetrics, ArmBExtras, list[str]]:
    """Score arm B (ensemble) against the gold set, with E1 ablation and decoy weights.

    Runs reduce_findings at keep_threshold=1 (dedup only) and keep_threshold=2
    (corroboration gate) to compute the E1 ablation.  Reports per-decoy corroboration
    weight for the E0 diagnostic.

    Args:
        report_dir: Directory containing one worker report file per Haiku agent.
        gold_positives: Gold true_violation + systematic_miss keys.
        gold_decoys: Gold decoy_false_positive keys.
        glob: Filename glob for worker report files.

    Returns:
        Tuple of (ArmMetrics at keep_threshold=2, ArmBExtras with E1 and E0 data, warnings).

    Raises:
        FileNotFoundError: When report_dir does not exist.
        ValueError: When no worker reports are found matching glob.
    """
    if not report_dir.is_dir():
        msg = f"report_dir does not exist: {report_dir}"
        raise FileNotFoundError(msg)

    reports: dict[str, list] = {}
    for path in sorted(report_dir.glob(glob)):
        worker_id = path.stem.rsplit("-", 1)[-1] if "-" in path.stem else path.stem
        reports[worker_id] = parse_report(path.read_text(encoding="utf-8"))

    if not reports:
        msg = f"No worker reports matching {glob!r} in {report_dir}"
        raise ValueError(msg)

    # E1 ablation: run reduce at both thresholds and compare F1
    merged_t1 = reduce_findings(reports, 1)
    merged_t2 = reduce_findings(reports, 2)

    reported_t2 = {(m.group, m.location) for m in merged_t2}
    reported_t1 = {(m.group, m.location) for m in merged_t1}

    warnings: list[str] = []
    warning = _path_mismatch_warning(reported_t2, gold_positives, report_dir)
    if warning is not None:
        warnings.append(warning)

    metrics = compute_metrics(reported_t2, gold_positives, gold_decoys)
    f1_t1 = compute_metrics(reported_t1, gold_positives, gold_decoys).f1
    f1_t2 = metrics.f1

    # E0: per-decoy corroboration weight — how many workers flagged each decoy
    merged_by_key: dict[tuple[str, str], int] = {(m.group, m.location): m.weight for m in merged_t1}
    per_decoy_weight = {key: merged_by_key[key] for key in gold_decoys if key in merged_by_key}

    extras = ArmBExtras(
        per_decoy_weight=per_decoy_weight, f1_at_threshold_1=f1_t1, f1_at_threshold_2=f1_t2, f1_delta=f1_t2 - f1_t1
    )

    return metrics, extras, warnings


# ---------------------------------------------------------------------------
# Judgement system — multi-arm ranking
# ---------------------------------------------------------------------------


@dataclass
class ArmRanking:
    """One arm's ranked result in the judgement comparison table.

    Attributes:
        arm_name: Display label from the manifest.
        metrics: P/R/F1 and cost/latency for this arm.
        payoff_per_cost: (F1 gain over baseline) / cost_usd.  None when
            cost_usd is zero (cannot compute a meaningful ratio).  The
            baseline arm itself has payoff_per_cost of 0.0 by definition.
        rank: Position in the sorted ranking (1 = best payoff-per-cost).
    """

    arm_name: str
    metrics: ArmMetrics
    payoff_per_cost: float | None
    rank: int


def compute_payoff_per_cost(arm_f1: float, baseline_f1: float, cost: float) -> float | None:
    """Compute the payoff-per-cost ratio for one arm relative to a baseline.

    Payoff is defined as the F1 gain over the lowest-cost arm divided by
    the arm's cost in USD.  Negative payoffs (arm is worse AND pricier) are
    valid and preserved — they indicate the arm degrades quality at a price.

    Args:
        arm_f1: The arm's F1 score (0.0-1.0).
        baseline_f1: F1 of the baseline arm (lowest-cost arm).
        cost: The arm's cost in USD.

    Returns:
        (arm_f1 - baseline_f1) / cost when cost > 0, or None when cost == 0.
        None signals that cost data is unavailable, not that payoff is zero.

    Examples:
        >>> compute_payoff_per_cost(0.80, 0.50, 0.50)
        0.6
        >>> compute_payoff_per_cost(0.50, 0.50, 0.10)
        0.0
        >>> compute_payoff_per_cost(0.80, 0.50, 0.0)
        # returns None — cost unavailable
    """
    if not cost:
        return None
    return (arm_f1 - baseline_f1) / cost


def rank_arms(scored_arms: list[tuple[str, ArmMetrics]]) -> list[ArmRanking]:
    """Rank N arms by payoff-per-cost, highest first.

    The baseline is the arm with the lowest non-zero cost.  When multiple arms
    share the lowest cost, the first in manifest order (i.e. the first in the
    input list) is used as baseline.

    Arms with cost_usd == 0.0 have payoff_per_cost = None and sort last,
    after all arms with computed payoffs, with their relative order preserved.

    Tiebreak for equal payoff: lexicographic arm_name ascending (stable and
    deterministic; independent of manifest order for reproducibility).

    Args:
        scored_arms: List of (arm_name, ArmMetrics) in manifest order.
            ArmMetrics.cost_usd and ArmMetrics.f1 must be populated.

    Returns:
        List of ArmRanking sorted by payoff_per_cost descending (best first),
        with None-payoff arms appended last.  Ranks are 1-based.

    Raises:
        ValueError: When scored_arms is empty.
    """
    if not scored_arms:
        raise ValueError("scored_arms must not be empty")

    # Determine baseline: arm with the lowest positive cost in manifest order.
    positive_cost_arms = [(name, m) for name, m in scored_arms if m.cost_usd > 0.0]
    if positive_cost_arms:
        _baseline_name, baseline_metrics = min(positive_cost_arms, key=lambda x: x[1].cost_usd)
        baseline_f1 = baseline_metrics.f1
    else:
        baseline_f1 = 0.0

    payoffs: list[ArmRanking] = []
    no_cost: list[ArmRanking] = []

    for arm_name, metrics in scored_arms:
        ppc = compute_payoff_per_cost(metrics.f1, baseline_f1, metrics.cost_usd)
        entry = ArmRanking(arm_name=arm_name, metrics=metrics, payoff_per_cost=ppc, rank=0)
        if ppc is None:
            no_cost.append(entry)
        else:
            payoffs.append(entry)

    # Sort arms with computed payoffs: highest payoff first; tiebreak by name.
    payoffs.sort(key=lambda r: (-r.payoff_per_cost, r.arm_name))  # type: ignore[operator]

    ranked: list[ArmRanking] = []
    for position, entry in enumerate(payoffs + no_cost, start=1):
        ranked.append(
            ArmRanking(
                arm_name=entry.arm_name, metrics=entry.metrics, payoff_per_cost=entry.payoff_per_cost, rank=position
            )
        )
    return ranked
