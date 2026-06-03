"""Pure cost-computation module for the judgement system.

No subprocess calls, no I/O, no LLM calls.  All functions are deterministic
and importable directly from tests.

Public API
----------
TokenUsage        — input/output token counts for one run
compute_cost(usage, prices) -> float
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runner.manifest import ModelPrice


@dataclass
class TokenUsage:
    """Token counts captured from a single claude -p run.

    Attributes:
        input_tokens: Number of input (prompt) tokens consumed.
        output_tokens: Number of output (completion) tokens produced.
        model_id: Model identifier used for the run.  Must match a key in
            the manifest prices table for cost computation to succeed.

    Notes:
        For multi-model arms (e.g. ensemble fan-out), claude -p returns
        aggregate totals only — individual worker token counts are not
        separately available.  The aggregate is attributed to the arm's
        primary model when computing cost.  This is a known approximation;
        the STUB comment below marks the extension point for per-worker
        attribution when the claude CLI exposes it.
    """

    input_tokens: int
    output_tokens: int
    model_id: str


def compute_cost(usage: TokenUsage, prices: dict[str, ModelPrice]) -> float:
    """Compute the deterministic USD cost for one arm run.

    Uses the price table from the manifest rather than total_cost_usd
    reported by claude -p, which is non-deterministic (live pricing may
    change).  The reported total_cost_usd is stored in run-meta.json for
    reconciliation but is NOT used as the authoritative cost figure.

    Args:
        usage: Token counts and model id for the arm run.
        prices: Mapping of model id -> ModelPrice, from Manifest.prices.

    Returns:
        Total cost in USD as a float, computed as:
            (input_tokens / 1000) * input_per_1k
          + (output_tokens / 1000) * output_per_1k

    Raises:
        ValueError: When usage.model_id is not found in prices.

    # STUB — per-worker attribution for multi-model arms:
    # When the claude CLI exposes per-worker usage breakdowns, replace
    # this function's signature with:
    #   compute_cost(usages: list[TokenUsage], prices: dict[str, ModelPrice]) -> float
    # and sum across workers using each worker's own model_id.
    # Until then, pass aggregate usage with the primary model's id.
    """
    if usage.model_id not in prices:
        raise ValueError(f"No price entry for model '{usage.model_id}'. Add it to the prices table in arms.yaml.")
    price = prices[usage.model_id]
    return (usage.input_tokens / 1000.0) * price.input_per_1k + (usage.output_tokens / 1000.0) * price.output_per_1k
