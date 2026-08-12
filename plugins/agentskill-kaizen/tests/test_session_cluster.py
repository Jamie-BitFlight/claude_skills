from __future__ import annotations

from session_cluster import cluster_tool_sequences


def test_cluster_tool_sequences_groups_similar_sessions() -> None:
    result = cluster_tool_sequences(
        {"read-a": ["Read", "Grep", "Read"], "read-b": ["Read", "Grep"], "write-a": ["Write", "Edit"]},
        n_clusters=2,
        top_tools_per_cluster=3,
    )

    cluster_sets = [set(members) for members in result["clusters"].values()]
    assert {"read-a", "read-b"} in cluster_sets
    assert {"write-a"} in cluster_sets


def test_cluster_tool_sequences_caps_cluster_count_to_session_count() -> None:
    result = cluster_tool_sequences({"only": ["Read", "Write"]}, n_clusters=10, top_tools_per_cluster=3)

    assert result["clusters"] == {"0": ["only"]}


def test_cluster_tool_sequences_orders_profiles_by_count_then_name() -> None:
    result = cluster_tool_sequences(
        {"alpha": ["Write", "Read"], "beta": ["Read", "Write", "Read"]}, n_clusters=1, top_tools_per_cluster=2
    )

    assert result["cluster_profiles"] == {"0": ["Read", "Write"]}
