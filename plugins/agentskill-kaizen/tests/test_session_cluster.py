from __future__ import annotations

import random
import time

import pytest
import session_cluster
from session_cluster import cluster_tool_sequences


def test_cluster_tool_sequences_groups_similar_sessions() -> None:
    result = cluster_tool_sequences(
        {"read-a": ["Read", "Grep", "Read"], "read-b": ["Read", "Grep"], "write-a": ["Write", "Edit"]},
        n_clusters=2,
        top_tools_per_cluster=3,
    )

    cluster_sets = [set(members) for members in result.clusters.values()]
    assert {"read-a", "read-b"} in cluster_sets
    assert {"write-a"} in cluster_sets


def test_cluster_tool_sequences_caps_cluster_count_to_session_count() -> None:
    result = cluster_tool_sequences({"only": ["Read", "Write"]}, n_clusters=10, top_tools_per_cluster=3)

    assert result.clusters == {"0": ["only"]}


def test_cluster_tool_sequences_orders_profiles_by_count_then_name() -> None:
    result = cluster_tool_sequences(
        {"alpha": ["Write", "Read"], "beta": ["Read", "Write", "Read"]}, n_clusters=1, top_tools_per_cluster=2
    )

    assert result.cluster_profiles == {"0": ["Read", "Write"]}


def test_cluster_tool_sequences_precomputes_pairwise_similarity_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression guard for the cubic-time merge loop: cosine similarity must be
    computed exactly O(N^2) times (the one-time pairwise precompute), never
    recomputed from raw session vectors on subsequent merge steps."""
    call_count = 0
    original = session_cluster._cosine_similarity

    def _counting_cosine_similarity(left: session_cluster.ToolCounter, right: session_cluster.ToolCounter) -> float:
        nonlocal call_count
        call_count += 1
        return original(left, right)

    monkeypatch.setattr(session_cluster, "_cosine_similarity", _counting_cosine_similarity)

    session_count = 60
    sequences = {f"session-{i}": ["Read", "Grep"] if i % 2 else ["Write", "Edit"] for i in range(session_count)}
    session_cluster.cluster_tool_sequences(sequences, n_clusters=5, top_tools_per_cluster=3)

    assert call_count == session_count * (session_count - 1) // 2


@pytest.mark.slow
def test_cluster_tool_sequences_scales_to_large_session_counts() -> None:
    """1000 sessions must cluster well under the pre-fix ~27.5s measurement.

    200 sessions doesn't reliably trigger the O(n) pair_sim cleanup sweep
    regression this guards against (measured well under a second either
    way) -- 1000 is large enough that the regression is unmistakable.
    Measured without coverage instrumentation: ~6s fixed, ~27.5s with the
    sweep bug reintroduced. Under this suite's default `--cov` instrumentation
    (line-tracing overhead on a hot loop) the fixed case measured ~25s, so
    the bound below is calibrated generously above that -- still well short
    of where a reintroduced O(n) sweep would land, but robust to coverage
    and CI-runner speed variance rather than pinned to an uninstrumented
    measurement.
    """
    rng = random.Random(42)
    tools = ["Read", "Grep", "Write", "Edit", "Bash", "Glob"]
    sequences = {f"session-{i}": [rng.choice(tools) for _ in range(rng.randint(3, 12))] for i in range(1000)}

    start = time.perf_counter()
    result = cluster_tool_sequences(sequences, n_clusters=5, top_tools_per_cluster=5)
    elapsed = time.perf_counter() - start

    assert len(result.clusters) == 5
    assert elapsed < 60.0
