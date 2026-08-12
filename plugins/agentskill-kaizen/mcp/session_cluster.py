"""Pure-Python clustering for Kaizen tool-call sequences."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from math import sqrt
from typing import TypeAlias, TypedDict

ToolSequences: TypeAlias = Mapping[str, Sequence[str]]
ToolCounter: TypeAlias = Counter[str]
SessionCluster: TypeAlias = tuple[str, ...]


class ClusterResult(TypedDict):
    """Cluster assignments and per-cluster representative tools."""

    clusters: dict[str, list[str]]
    cluster_profiles: dict[str, list[str]]


def cluster_tool_sequences(sequences: ToolSequences, n_clusters: int, top_tools_per_cluster: int) -> ClusterResult:
    """Group sessions by cosine similarity over tool-call counts.

    Returns:
        Cluster assignments and representative tools for each cluster.
    """
    session_ids = tuple(sorted(sequences))
    effective_clusters = min(max(1, n_clusters), len(session_ids))
    vectors = {session_id: Counter(sequences[session_id]) for session_id in session_ids}
    clusters = tuple((session_id,) for session_id in session_ids)

    while len(clusters) > effective_clusters:
        left_index, right_index = _most_similar_pair(clusters, vectors)
        clusters = _merge_cluster_pair(clusters, left_index, right_index)

    return {
        "clusters": {str(index): list(cluster) for index, cluster in enumerate(clusters)},
        "cluster_profiles": _cluster_profiles(clusters, vectors, top_tools_per_cluster),
    }


def _most_similar_pair(clusters: tuple[SessionCluster, ...], vectors: Mapping[str, ToolCounter]) -> tuple[int, int]:
    best_left = 0
    best_right = 1
    best_score = -1.0
    for left_index, left_cluster in enumerate(clusters[:-1]):
        for right_offset, right_cluster in enumerate(clusters[left_index + 1 :], start=left_index + 1):
            score = _cluster_similarity(left_cluster, right_cluster, vectors)
            if score > best_score:
                best_left = left_index
                best_right = right_offset
                best_score = score
    return best_left, best_right


def _cluster_similarity(
    left_cluster: SessionCluster, right_cluster: SessionCluster, vectors: Mapping[str, ToolCounter]
) -> float:
    scores = [
        _cosine_similarity(vectors[left_session], vectors[right_session])
        for left_session in left_cluster
        for right_session in right_cluster
    ]
    return sum(scores) / len(scores)


def _cosine_similarity(left: ToolCounter, right: ToolCounter) -> float:
    if not left or not right:
        return 0.0
    left_norm = sqrt(sum(count * count for count in left.values()))
    right_norm = sqrt(sum(count * count for count in right.values()))
    shared_tools = left.keys() & right.keys()
    dot_product = sum(left[tool] * right[tool] for tool in shared_tools)
    return dot_product / (left_norm * right_norm)


def _merge_cluster_pair(
    clusters: tuple[SessionCluster, ...], left_index: int, right_index: int
) -> tuple[SessionCluster, ...]:
    merged = tuple(sorted((*clusters[left_index], *clusters[right_index])))
    return (*tuple(cluster for index, cluster in enumerate(clusters) if index not in {left_index, right_index}), merged)


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
