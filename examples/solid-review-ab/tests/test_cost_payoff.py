"""Independent correctness tests for cost computation and payoff-per-cost ranking.

Authorship note
---------------
These tests were authored from first-principles definitions, NOT derived from
the scorer's output.  Expected values are hand-computed from the definitions
below and then verified against the implementation.  Any discrepancy between
a hand-computed value and the implementation output is a FINDING to report,
not a reason to adjust the expected value.

Definitions encoded as expected values
---------------------------------------
Cost formula
    cost_usd = (input_tokens / 1000) * input_per_1k
             + (output_tokens / 1000) * output_per_1k

Payoff-per-cost
    payoff_per_cost = (arm_f1 - baseline_f1) / cost_usd
    where baseline is the arm with the lowest non-zero cost_usd.
    When cost_usd == 0.0, payoff_per_cost is None (cannot compute a ratio).
    The baseline arm's own payoff is 0.0 (numerator = 0).

Rank ordering
    Arms are ranked by payoff_per_cost descending (highest first).
    Arms with payoff_per_cost == None are appended last.
    Tiebreak: lexicographic arm_name ascending.

Hand-computed scenario
    arm-cheap:  F1=0.50, input=200, output=100, model=model-a
                price: input_per_1k=0.001, output_per_1k=0.002
                cost = (200/1000)*0.001 + (100/1000)*0.002 = 0.0002 + 0.0002 = 0.0004
                → baseline (lowest cost)
                payoff = 0.0

    arm-mid:    F1=0.80, input=1000, output=500, model=model-a
                cost = (1000/1000)*0.001 + (500/1000)*0.002 = 0.001 + 0.001 = 0.002
                payoff = (0.80 - 0.50) / 0.002 = 0.30 / 0.002 = 150.0

    arm-exp:    F1=0.90, input=10000, output=5000, model=model-b
                price: input_per_1k=0.010, output_per_1k=0.030
                cost = (10000/1000)*0.010 + (5000/1000)*0.030 = 0.100 + 0.150 = 0.250
                payoff = (0.90 - 0.50) / 0.250 = 0.40 / 0.250 = 1.6

    arm-worse:  F1=0.40, cost=0.010 (model-a, arbitrary tokens)
                payoff = (0.40 - 0.50) / 0.010 = -0.10 / 0.010 = -10.0 (negative)

    arm-free:   cost_usd=0.0 → payoff=None (appended last)

    Expected ranking (payoff desc):
        1. arm-mid   (150.0)
        2. arm-exp   (1.6)
        3. arm-cheap (0.0, baseline)
        4. arm-worse (-10.0)
        5. arm-free  (None)
"""

from __future__ import annotations

import pytest
from runner.cost import TokenUsage, compute_cost
from runner.manifest import ModelPrice
from runner.scorer import ArmMetrics, ArmRanking, compute_payoff_per_cost, rank_arms

# ---------------------------------------------------------------------------
# Price fixtures (hand-defined, independent of manifest loader)
# ---------------------------------------------------------------------------

_PRICES: dict[str, ModelPrice] = {
    "model-a": ModelPrice(input_per_1k=0.001, output_per_1k=0.002),
    "model-b": ModelPrice(input_per_1k=0.010, output_per_1k=0.030),
}


# ---------------------------------------------------------------------------
# compute_cost tests
# ---------------------------------------------------------------------------


class TestComputeCost:
    """Tests for runner.cost.compute_cost."""

    def test_cost_model_a_exact(self) -> None:
        """Hand-computed: (200/1000)*0.001 + (100/1000)*0.002 = 0.0004.

        Setup:
            input=200 tokens @ 0.001 per 1k = 0.0002
            output=100 tokens @ 0.002 per 1k = 0.0002
            total = 0.0004
        """
        # Arrange
        usage = TokenUsage(input_tokens=200, output_tokens=100, model_id="model-a")

        # Act
        result = compute_cost(usage, _PRICES)

        # Assert — hand value: 0.0004
        assert result == pytest.approx(0.0004)

    def test_cost_model_b_exact(self) -> None:
        """Hand-computed: (10000/1000)*0.010 + (5000/1000)*0.030 = 0.250.

        Setup:
            input=10000 tokens @ 0.010 per 1k = 0.100
            output=5000 tokens @ 0.030 per 1k = 0.150
            total = 0.250
        """
        # Arrange
        usage = TokenUsage(input_tokens=10000, output_tokens=5000, model_id="model-b")

        # Act
        result = compute_cost(usage, _PRICES)

        # Assert — hand value: 0.250
        assert result == pytest.approx(0.250)

    def test_cost_zero_tokens_is_zero(self) -> None:
        """Zero input and output tokens produce zero cost.

        Setup:
            input=0, output=0 → cost = 0
        """
        # Arrange
        usage = TokenUsage(input_tokens=0, output_tokens=0, model_id="model-a")

        # Act
        result = compute_cost(usage, _PRICES)

        # Assert
        assert result == pytest.approx(0.0)

    def test_cost_unknown_model_raises_value_error(self) -> None:
        """Requesting cost for an unregistered model raises ValueError.

        Ensures the caller learns about missing price data instead of silently
        computing 0.0.
        """
        # Arrange
        usage = TokenUsage(input_tokens=100, output_tokens=50, model_id="nonexistent-model")

        # Act / Assert
        with pytest.raises(ValueError, match="nonexistent-model"):
            compute_cost(usage, _PRICES)

    def test_cost_mid_arm(self) -> None:
        """Hand-computed: (1000/1000)*0.001 + (500/1000)*0.002 = 0.002.

        Setup:
            input=1000 tokens @ 0.001 per 1k = 0.001
            output=500 tokens @ 0.002 per 1k = 0.001
            total = 0.002
        """
        # Arrange
        usage = TokenUsage(input_tokens=1000, output_tokens=500, model_id="model-a")

        # Act
        result = compute_cost(usage, _PRICES)

        # Assert — hand value: 0.002
        assert result == pytest.approx(0.002)


# ---------------------------------------------------------------------------
# compute_payoff_per_cost tests
# ---------------------------------------------------------------------------


class TestComputePayoffPerCost:
    """Tests for runner.scorer.compute_payoff_per_cost."""

    def test_payoff_positive_gain(self) -> None:
        """Hand-computed: (0.80 - 0.50) / 0.002 = 150.0."""
        # Act
        result = compute_payoff_per_cost(arm_f1=0.80, baseline_f1=0.50, cost=0.002)

        # Assert — hand value: 150.0
        assert result == pytest.approx(150.0)

    def test_payoff_baseline_arm_is_zero(self) -> None:
        """Baseline arm vs itself: (0.50 - 0.50) / 0.0004 = 0.0."""
        # Act
        result = compute_payoff_per_cost(arm_f1=0.50, baseline_f1=0.50, cost=0.0004)

        # Assert — hand value: 0.0
        assert result == pytest.approx(0.0)

    def test_payoff_zero_cost_returns_none(self) -> None:
        """When cost is 0.0, return None — do not divide by zero."""
        # Act
        result = compute_payoff_per_cost(arm_f1=0.90, baseline_f1=0.50, cost=0.0)

        # Assert
        assert result is None

    def test_payoff_negative_gain(self) -> None:
        """Arm worse than baseline: (0.40 - 0.50) / 0.010 = -10.0.

        Negative payoffs are valid — arm degrades quality at a price.
        """
        # Act
        result = compute_payoff_per_cost(arm_f1=0.40, baseline_f1=0.50, cost=0.010)

        # Assert — hand value: -10.0
        assert result == pytest.approx(-10.0)

    def test_payoff_expensive_arm_lower_ratio(self) -> None:
        """Hand-computed: (0.90 - 0.50) / 0.250 = 1.6."""
        # Act
        result = compute_payoff_per_cost(arm_f1=0.90, baseline_f1=0.50, cost=0.250)

        # Assert — hand value: 1.6
        assert result == pytest.approx(1.6)


# ---------------------------------------------------------------------------
# rank_arms tests
# ---------------------------------------------------------------------------


def _make_metrics(f1: float, cost_usd: float) -> ArmMetrics:
    """Build a minimal ArmMetrics with only f1 and cost_usd set.

    Args:
        f1: F1 score to assign.
        cost_usd: Cost in USD to assign.

    Returns:
        ArmMetrics with only f1 and cost_usd populated; all other fields default.
    """
    return ArmMetrics(f1=f1, cost_usd=cost_usd)


class TestRankArms:
    """Tests for runner.scorer.rank_arms."""

    def test_full_scenario_hand_computed(self) -> None:
        """Five-arm scenario: verify rank order and payoff values against hand computation.

        Setup (from module docstring):
            arm-cheap:  F1=0.50, cost=0.0004 → baseline (rank 3, payoff=0.0)
            arm-mid:    F1=0.80, cost=0.002  → payoff=150.0   (rank 1)
            arm-exp:    F1=0.90, cost=0.250  → payoff=1.6     (rank 2)
            arm-worse:  F1=0.40, cost=0.010  → payoff=-10.0   (rank 4)
            arm-free:   F1=0.70, cost=0.0    → payoff=None    (rank 5)
        """
        # Arrange — manifest order
        scored = [
            ("arm-cheap", _make_metrics(f1=0.50, cost_usd=0.0004)),
            ("arm-mid", _make_metrics(f1=0.80, cost_usd=0.002)),
            ("arm-exp", _make_metrics(f1=0.90, cost_usd=0.250)),
            ("arm-worse", _make_metrics(f1=0.40, cost_usd=0.010)),
            ("arm-free", _make_metrics(f1=0.70, cost_usd=0.0)),
        ]

        # Act
        rankings = rank_arms(scored)

        # Assert — ordering
        names_by_rank = [r.arm_name for r in rankings]
        assert names_by_rank == ["arm-mid", "arm-exp", "arm-cheap", "arm-worse", "arm-free"]

        # Assert — payoff values (hand-computed)
        by_name = {r.arm_name: r for r in rankings}
        assert by_name["arm-mid"].payoff_per_cost == pytest.approx(150.0)
        assert by_name["arm-exp"].payoff_per_cost == pytest.approx(1.6)
        assert by_name["arm-cheap"].payoff_per_cost == pytest.approx(0.0)
        assert by_name["arm-worse"].payoff_per_cost == pytest.approx(-10.0)
        assert by_name["arm-free"].payoff_per_cost is None

        # Assert — 1-based ranks
        assert by_name["arm-mid"].rank == 1
        assert by_name["arm-exp"].rank == 2
        assert by_name["arm-cheap"].rank == 3
        assert by_name["arm-worse"].rank == 4
        assert by_name["arm-free"].rank == 5

    def test_single_arm_is_baseline_with_zero_payoff(self) -> None:
        """A single arm is its own baseline; payoff = 0.0.

        Setup:
            one-arm: F1=0.75, cost=0.005 → baseline → payoff=0.0
        """
        # Arrange
        scored = [("one-arm", _make_metrics(f1=0.75, cost_usd=0.005))]

        # Act
        rankings = rank_arms(scored)

        # Assert
        assert len(rankings) == 1
        assert rankings[0].arm_name == "one-arm"
        assert rankings[0].payoff_per_cost == pytest.approx(0.0)
        assert rankings[0].rank == 1

    def test_all_zero_cost_all_none_payoff(self) -> None:
        """When no arm has a cost, all payoffs are None and arms appear in name order.

        Tiebreak for None-payoff arms: preserved in input (manifest) order —
        rank_arms appends them last in the order encountered.
        """
        # Arrange
        scored = [("arm-z", _make_metrics(f1=0.9, cost_usd=0.0)), ("arm-a", _make_metrics(f1=0.5, cost_usd=0.0))]

        # Act
        rankings = rank_arms(scored)

        # Assert — no crashes, all None
        assert all(r.payoff_per_cost is None for r in rankings)
        assert [r.arm_name for r in rankings] == ["arm-z", "arm-a"]

    def test_empty_raises_value_error(self) -> None:
        """rank_arms([]) must raise ValueError — not return an empty list silently."""
        # Act / Assert
        with pytest.raises(ValueError, match="empty"):
            rank_arms([])

    def test_tiebreak_equal_payoff_lexicographic(self) -> None:
        """When two arms have equal payoff, names sort ascending (a before z).

        Setup:
            arm-z: F1=0.80, cost=0.002 → payoff = (0.80 - 0.50) / 0.002 = 150.0
            arm-a: F1=0.80, cost=0.002 → payoff = 150.0
            baseline: arm-cheap F1=0.50, cost=0.0004

        Tiebreak: arm-a < arm-z lexicographically → arm-a ranks 1, arm-z ranks 2.
        """
        # Arrange
        scored = [
            ("arm-cheap", _make_metrics(f1=0.50, cost_usd=0.0004)),
            ("arm-z", _make_metrics(f1=0.80, cost_usd=0.002)),
            ("arm-a", _make_metrics(f1=0.80, cost_usd=0.002)),
        ]

        # Act
        rankings = rank_arms(scored)

        # Assert — arm-a before arm-z (equal payoffs)
        by_name = {r.arm_name: r for r in rankings}
        assert by_name["arm-a"].rank < by_name["arm-z"].rank

    def test_negative_payoff_ranks_last_before_none(self) -> None:
        """A negative-payoff arm ranks after positive-payoff arms but before None-cost arms.

        Setup:
            arm-good:  payoff = positive
            arm-bad:   payoff = negative
            arm-free:  payoff = None
        """
        # Arrange
        scored = [
            ("arm-baseline", _make_metrics(f1=0.60, cost_usd=0.001)),
            ("arm-good", _make_metrics(f1=0.80, cost_usd=0.010)),
            ("arm-bad", _make_metrics(f1=0.40, cost_usd=0.010)),
            ("arm-free", _make_metrics(f1=0.90, cost_usd=0.0)),
        ]

        # Act
        rankings = rank_arms(scored)
        by_name = {r.arm_name: r for r in rankings}

        # Assert ordering: good > baseline > bad > free
        assert by_name["arm-good"].rank < by_name["arm-baseline"].rank
        assert by_name["arm-baseline"].rank < by_name["arm-bad"].rank
        assert by_name["arm-bad"].rank < by_name["arm-free"].rank
        assert by_name["arm-free"].payoff_per_cost is None

    def test_return_type_is_list_of_arm_ranking(self) -> None:
        """rank_arms returns a list of ArmRanking instances."""
        # Arrange
        scored = [("arm-x", _make_metrics(f1=0.5, cost_usd=0.001))]

        # Act
        rankings = rank_arms(scored)

        # Assert
        assert isinstance(rankings, list)
        assert all(isinstance(r, ArmRanking) for r in rankings)
