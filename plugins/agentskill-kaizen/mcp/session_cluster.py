"""Pure-Python clustering for Kaizen tool-call sequences."""

from __future__ import annotations

import heapq
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from math import sqrt
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict

ToolSequences: TypeAlias = Mapping[str, Sequence[str]]
ToolCounter: TypeAlias = Counter[str]
SessionCluster: TypeAlias = tuple[str, ...]
ClusterId: TypeAlias = int
PairKey: TypeAlias = tuple[ClusterId, ClusterId]


class ClusterResult(BaseModel):
    """Cluster assignments and per-cluster representative tools."""

    model_config = ConfigDict(frozen=True)

    clusters: dict[str, list[str]]
    cluster_profiles: dict[str, list[str]]


@dataclass
class _ClusterState:
    """Mutable incremental-merge bookkeeping for average-linkage clustering.

    Purely internal — never constructed as MCP output, so it stays a plain
    dataclass rather than joining the Pydantic conversion applied to
    ClusterResult and the process-model shapes.
    """

    members: dict[ClusterId, SessionCluster]
    sizes: dict[ClusterId, int]
    active_ids: set[ClusterId]
    pair_sim: dict[PairKey, float]
    heap: list[tuple[float, ClusterId, ClusterId]] = field(default_factory=list)
    next_id: int = field(default=0)


def cluster_tool_sequences(sequences: ToolSequences, n_clusters: int, top_tools_per_cluster: int) -> ClusterResult:
    """Group sessions by cosine similarity over tool-call counts.

    Uses average-linkage agglomeration with a Lance-Williams incremental
    similarity update: pairwise session similarities are computed once,
    cluster-to-cluster similarity is updated in O(1) per surviving pair on
    each merge instead of being recomputed from raw session vectors, and
    the next merge candidate is found via a lazily-invalidated max-heap
    instead of rescanning every active pair -- O(n^2 log n) overall
    instead of the O(n^3) a full argmax rescan would still cost even with
    similarity caching.

    Returns:
        Cluster assignments and representative tools for each cluster.
    """
    session_ids = tuple(sorted(sequences))
    effective_clusters = min(max(1, n_clusters), len(session_ids))
    vectors = {session_id: Counter(sequences[session_id]) for session_id in session_ids}

    state = _initial_cluster_state(session_ids, vectors)
    while len(state.active_ids) > effective_clusters:
        _merge_most_similar_pair(state)

    clusters = tuple(state.members[cluster_id] for cluster_id in sorted(state.active_ids))

    return ClusterResult(
        clusters={str(index): list(cluster) for index, cluster in enumerate(clusters)},
        cluster_profiles=_cluster_profiles(clusters, vectors, top_tools_per_cluster),
    )


def _pair_key(left_id: ClusterId, right_id: ClusterId) -> PairKey:
    return (left_id, right_id) if left_id < right_id else (right_id, left_id)


def _initial_cluster_state(session_ids: tuple[str, ...], vectors: Mapping[str, ToolCounter]) -> _ClusterState:
    members: dict[ClusterId, SessionCluster] = {index: (session_id,) for index, session_id in enumerate(session_ids)}
    pair_sim = {
        _pair_key(left_index, right_index): _cosine_similarity(
            vectors[session_ids[left_index]], vectors[session_ids[right_index]]
        )
        for left_index, right_index in combinations(range(len(session_ids)), 2)
    }
    heap = [(-similarity, left_id, right_id) for (left_id, right_id), similarity in pair_sim.items()]
    heapq.heapify(heap)
    return _ClusterState(
        members=members,
        sizes=dict.fromkeys(members, 1),
        active_ids=set(members),
        pair_sim=pair_sim,
        heap=heap,
        next_id=len(session_ids),
    )


def _most_similar_active_pair(state: _ClusterState) -> tuple[ClusterId, ClusterId]:
    """Pop and return the globally most-similar active cluster pair.

    Lazily discards stale heap entries left behind by earlier merges
    (pairs referencing a cluster id that has since been retired) instead
    of rescanning every active pair on each call -- each merge step
    becomes O(log n) amortized heap work instead of an O(active_clusters^2)
    full rescan, which was still cubic overall even after the pairwise
    similarity itself was cached.

    Returns:
        The (left_id, right_id) pair with the highest cached similarity
        among currently active clusters.
    """
    while state.heap:
        _, left_id, right_id = heapq.heappop(state.heap)
        if left_id in state.active_ids and right_id in state.active_ids:
            return left_id, right_id
    msg = "no active cluster pairs remain to merge"
    raise RuntimeError(msg)


def _lance_williams_average_linkage(
    left_similarity: float, right_similarity: float, left_size: int, right_size: int
) -> float:
    """UPGMA (average-linkage) Lance-Williams incremental similarity update.

    sim(AB, C) = (|A| * sim(A, C) + |B| * sim(B, C)) / (|A| + |B|)

    Returns:
        Updated similarity between the merged cluster and the other cluster.
    """
    total_size = left_size + right_size
    return (left_size * left_similarity + right_size * right_similarity) / total_size


def _merge_most_similar_pair(state: _ClusterState) -> None:
    left_id, right_id = _most_similar_active_pair(state)
    merged_id = state.next_id
    state.next_id += 1

    for other_id in state.active_ids - {left_id, right_id}:
        new_similarity = _lance_williams_average_linkage(
            left_similarity=state.pair_sim[_pair_key(left_id, other_id)],
            right_similarity=state.pair_sim[_pair_key(right_id, other_id)],
            left_size=state.sizes[left_id],
            right_size=state.sizes[right_id],
        )
        new_key = _pair_key(merged_id, other_id)
        state.pair_sim[new_key] = new_similarity
        heapq.heappush(state.heap, (-new_similarity, *new_key))

    state.members[merged_id] = tuple(sorted((*state.members[left_id], *state.members[right_id])))
    state.sizes[merged_id] = state.sizes[left_id] + state.sizes[right_id]
    state.active_ids -= {left_id, right_id}
    state.active_ids.add(merged_id)

    retired = {left_id, right_id}
    for key in [key for key in state.pair_sim if key[0] in retired or key[1] in retired]:
        del state.pair_sim[key]


def _cosine_similarity(left: ToolCounter, right: ToolCounter) -> float:
    if not left or not right:
        return 0.0
    left_norm = sqrt(sum(count * count for count in left.values()))
    right_norm = sqrt(sum(count * count for count in right.values()))
    shared_tools = left.keys() & right.keys()
    dot_product = sum(left[tool] * right[tool] for tool in shared_tools)
    return dot_product / (left_norm * right_norm)


def _cluster_profiles(
    clusters: tuple[SessionCluster, ...], vectors: Mapping[str, ToolCounter], top_tools_per_cluster: int
) -> dict[str, list[str]]:
    profiles: dict[str, list[str]] = {}
    for index, cluster in enumerate(clusters):
        tool_counts: Counter[str] = Counter()
        for session_id in cluster:
            tool_counts.update(vectors[session_id])
        profiles[str(index)] = _top_tools(tool_counts, top_tools_per_cluster)
    return profiles


def _top_tools(tool_counts: ToolCounter, limit: int) -> list[str]:
    return [tool for tool, _ in sorted(tool_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


__all__ = ["ClusterResult", "ToolSequences", "cluster_tool_sequences"]
