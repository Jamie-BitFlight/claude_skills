"""Tests for backlog_core.operations.analyze_impact_radius_conflicts().

Covers:
- No-conflict cases (empty list, single item, disjoint paths)
- Simple pairwise conflict producing one group
- Transitive merging (A-B, B-C → one group via union-find)
- Multiple independent conflict groups
- Items with missing / empty / whitespace-only impact_radius are excluded
- Bullet-marker and header stripping in path parsing
- Reason string contains sorted shared file paths
- Stable group_id numbering (1-based, ordered by component root)
"""

from __future__ import annotations

from typing import cast

import pytest
from backlog_core.operations import ImpactRadiusItem, analyze_impact_radius_conflicts
from dispatch_schema.core.models import ConflictGroup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _item(title: str, issue: int, impact_radius: str | None = None) -> ImpactRadiusItem:
    d: ImpactRadiusItem = {"title": title, "issue": issue}
    if impact_radius is not None:
        d["impact_radius"] = impact_radius
    return d


# ---------------------------------------------------------------------------
# No-conflict cases
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_empty_list_returns_empty() -> None:
    # Arrange
    items: list[ImpactRadiusItem] = []

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []


def test_analyze_impact_radius_conflicts_single_item_returns_empty() -> None:
    # Arrange
    items = [_item("A", 1, "plugins/foo.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []


def test_analyze_impact_radius_conflicts_disjoint_paths_returns_empty() -> None:
    # Arrange
    items = [_item("A", 1, "plugins/foo.py"), _item("B", 2, "plugins/bar.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []


def test_analyze_impact_radius_conflicts_no_impact_radius_key_excluded() -> None:
    # Arrange — neither item has an impact_radius key
    items: list[ImpactRadiusItem] = [{"title": "A", "issue": 1}, {"title": "B", "issue": 2}]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []


def test_analyze_impact_radius_conflicts_empty_impact_radius_excluded() -> None:
    # Arrange
    items = [_item("A", 1, ""), _item("B", 2, "   ")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Simple pairwise conflict
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_two_items_one_shared_path_returns_one_group() -> None:
    # Arrange
    shared = "plugins/development-harness/backlog_core/operations.py"
    items = [_item("Feature A", 10, shared), _item("Feature B", 20, shared)]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    group = result[0]
    assert isinstance(group, ConflictGroup)
    assert group.group_id == 1
    assert set(group.items) == {"Feature A", "Feature B"}
    assert shared in group.reason


def test_analyze_impact_radius_conflicts_reason_contains_sorted_shared_files() -> None:
    # Arrange
    items = [_item("A", 1, "z-file.py\na-file.py"), _item("B", 2, "a-file.py\nz-file.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    # Reason must list shared files in sorted order
    assert result[0].reason == "Shared systems: a-file.py, z-file.py"


# ---------------------------------------------------------------------------
# Transitive merging (union-find correctness)
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_transitive_overlap_merged_into_one_group() -> None:
    # Arrange: A-B share file1, B-C share file2, A-C share nothing
    items = [_item("A", 1, "file1.py"), _item("B", 2, "file1.py\nfile2.py"), _item("C", 3, "file2.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    group = result[0]
    assert set(group.items) == {"A", "B", "C"}


def test_analyze_impact_radius_conflicts_four_items_two_chains_two_groups() -> None:
    # Arrange: chain 1 (A-B) and chain 2 (C-D), no cross-chain overlap
    items = [_item("A", 1, "alpha.py"), _item("B", 2, "alpha.py"), _item("C", 3, "beta.py"), _item("D", 4, "beta.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 2
    group_items = {frozenset(g.items) for g in result}
    assert frozenset({"A", "B"}) in group_items
    assert frozenset({"C", "D"}) in group_items
    # group_ids are 1 and 2
    assert {g.group_id for g in result} == {1, 2}


# ---------------------------------------------------------------------------
# Bullet markers and header stripping
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_bullet_markers_stripped() -> None:
    # Arrange: paths prefixed with '- ' and '* '
    items = [_item("A", 1, "- plugins/foo.py\n* plugins/bar.py"), _item("B", 2, "- plugins/foo.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    assert "plugins/foo.py" in result[0].reason


@pytest.mark.parametrize("root_file", ["Dockerfile", "Makefile"])
def test_analyze_impact_radius_conflicts_preserves_backticked_extensionless_root_files(root_file: str) -> None:
    first = f"- `{root_file}` — build input"
    second = f"- `{root_file}` — build consumer"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].reason == f"Shared systems: {root_file}"


def test_analyze_impact_radius_conflicts_markdown_headers_excluded_from_paths() -> None:
    # Arrange: body includes a section header line that must not become a path
    body = "## Impact Radius\n- plugins/baz.py"
    items = [_item("A", 1, body), _item("B", 2, "plugins/baz.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    # Header must not appear in the reason
    assert "##" not in result[0].reason
    assert "plugins/baz.py" in result[0].reason


def test_analyze_impact_radius_conflicts_uses_system_from_inventory_row() -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"
    first = f"""### Systems Inventory
- `{shared}` | Role: producer | Action: CODE_CHANGE | Risk: HIGH
### Unknown Frontier
- `plugins/unknown-a.py` | Owner: team-a
"""
    second = f"""### Systems Inventory
- `{shared}` | Role: consumer | Action: VERIFY_COMPATIBLE | Risk: MEDIUM
### Unknown Frontier
- `plugins/unknown-b.py` | Owner: team-b
"""

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].reason == f"Shared systems: {shared}"


def test_analyze_impact_radius_conflicts_reads_legacy_inventory_row_suffix() -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"
    first = f"### Systems Inventory\n- `{shared}` — producer connected to dispatch"
    second = f"### Systems Inventory\n- `{shared}` | Role: consumer"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].reason == f"Shared systems: {shared}"


@pytest.mark.parametrize("level", range(1, 7))
@pytest.mark.parametrize("closing", ["", " ##"])
def test_analyze_impact_radius_conflicts_ignores_inventory_headings_inside_fences(level: int, closing: str) -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"

    def radius(example: str) -> str:
        return f"""### Fact-Check
```markdown
### Systems Inventory
- `{example}` | Role: example
```
{"#" * level} Systems Inventory{closing}
- `{shared}` | Role: runtime system
### Excluded Candidates and Unknown Frontier
- None identified.
"""

    result = analyze_impact_radius_conflicts([
        _item("A", 1, radius("plugins/fenced-example.py")),
        _item("B", 2, radius("plugins/fenced-example.py")),
    ])

    assert len(result) == 1
    assert result[0].reason == f"Shared systems: {shared}"


def test_analyze_impact_radius_conflicts_ignores_unknown_frontier_paths() -> None:
    first = """### Systems Inventory
- `plugins/a.py` | Role: producer
### Excluded Candidates and Unknown Frontier
- Unknown: `plugins/shared-unknown.py` - owner must inspect
"""
    second = """### Systems Inventory
- `plugins/b.py` | Role: consumer
### Excluded Candidates and Unknown Frontier
- Unknown: `plugins/shared-unknown.py` - owner must inspect
"""

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert result == []


def test_analyze_impact_radius_conflicts_normalizes_symbols_to_owning_system() -> None:
    first = "### Systems Inventory\n- `plugins/shared.py::first` | Role: producer"
    second = "### Systems Inventory\n- `plugins/shared.py::second` | Role: consumer"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert result[0].reason == "Shared systems: plugins/shared.py"


@pytest.mark.parametrize("directory", ["plugins", "plugins/example", "plugins/example/"])
def test_analyze_impact_radius_conflicts_detects_directory_and_nested_file_overlap(directory: str) -> None:
    first = f"### Systems Inventory\n- `{directory}` | Role: directory scope"
    second = "### Systems Inventory\n- `plugins/example/nested.py` | Role: file scope"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].reason == f"Shared systems: {directory}"


@pytest.mark.parametrize(
    ("directory", "nested_file"),
    [
        ("./plugins/example/", "plugins/example/nested.py"),
        ("plugins/other/../example/", "plugins/example/nested.py"),
        ("./", "plugins/example/nested.py"),
    ],
)
def test_analyze_impact_radius_conflicts_normalizes_repository_relative_paths(directory: str, nested_file: str) -> None:
    first = f"### Systems Inventory\n- `{directory}` | Role: directory scope"
    second = f"### Systems Inventory\n- `{nested_file}` | Role: file scope"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].items == ["A", "B"]


@pytest.mark.parametrize(("first_system", "second_system"), [("./", "Dockerfile"), ("./Dockerfile", "Dockerfile")])
def test_analyze_impact_radius_conflicts_normalizes_extensionless_root_files(
    first_system: str, second_system: str
) -> None:
    first = f"### Systems Inventory\n- `{first_system}` | Role: repository scope"
    second = f"### Systems Inventory\n- `{second_system}` | Role: root file"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].items == ["A", "B"]


def test_analyze_impact_radius_conflicts_does_not_treat_multiword_system_as_root_file() -> None:
    first = "### Systems Inventory\n- `./` | Role: repository scope"
    second = "### Systems Inventory\n- `release approval control` | Role: process control"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert result == []


def test_analyze_impact_radius_conflicts_detects_shared_non_file_system() -> None:
    system = "release approval control"
    first = f"### Systems Inventory\n- `{system}` | Role: process control"
    second = f"### Systems Inventory\n- `{system}` | Role: human handoff"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert len(result) == 1
    assert result[0].reason == f"Shared systems: {system}"


def test_analyze_impact_radius_conflicts_legacy_ignores_shared_status_lines() -> None:
    first = "SCOPE_EXPANSION: None.\n- plugins/a.py - changed producer"
    second = "SCOPE_EXPANSION: None.\n- plugins/b.py - changed consumer"

    result = analyze_impact_radius_conflicts([_item("A", 1, first), _item("B", 2, second)])

    assert result == []


# ---------------------------------------------------------------------------
# Mixed: some items with and without impact_radius
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_items_without_radius_do_not_form_groups() -> None:
    # Arrange: only items with a valid radius can conflict
    items = [
        _item("A", 1, "common.py"),
        _item("B", 2, "common.py"),
        _item("C", 3),  # no impact_radius key
        _item("D", 4, ""),  # empty
    ]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert — only A and B conflict
    assert len(result) == 1
    assert set(result[0].items) == {"A", "B"}


# ---------------------------------------------------------------------------
# ConflictGroup model compliance
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_group_id_starts_at_one() -> None:
    # Arrange
    items = [_item("X", 1, "shared.py"), _item("Y", 2, "shared.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result[0].group_id == 1


def test_analyze_impact_radius_conflicts_items_sorted_alphabetically_in_group() -> None:
    # Arrange: titles in reverse alphabetical order
    items = [_item("Zebra Feature", 1, "shared.py"), _item("Alpha Feature", 2, "shared.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result[0].items == ["Alpha Feature", "Zebra Feature"]


# ---------------------------------------------------------------------------
# Edge cases: None / whitespace-only impact_radius values
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_none_impact_radius_value_excluded() -> None:
    """Verify items with impact_radius=None are excluded from conflict analysis.

    Tests: analyze_impact_radius_conflicts filtering of None values.
    How: Build items where one has impact_radius=None explicitly set (key present,
    value None). The item must not form a conflict group.
    Why: The key being present but None is distinct from the key being absent;
    both must be excluded.
    """
    # Arrange — item A has impact_radius=None, item B has a valid path
    # cast is used to deliberately pass None for a key declared as str — this tests
    # the runtime branch that excludes items where impact_radius is present but None.
    item_a = cast("ImpactRadiusItem", {"title": "A", "issue": 1, "impact_radius": None})
    item_b = _item("B", 2, "plugins/shared.py")

    # Act
    result = analyze_impact_radius_conflicts([item_a, item_b])

    # Assert — no conflict: A is excluded, B has nothing to conflict with
    assert result == []


def test_analyze_impact_radius_conflicts_newline_only_impact_radius_excluded() -> None:
    """Verify items whose impact_radius is only newlines are excluded.

    Tests: analyze_impact_radius_conflicts filtering of whitespace-only values.
    How: impact_radius contains only newline characters — no paths after stripping.
    Why: Path parsing strips each line; if all lines are empty after stripping,
    no paths exist and the item must be excluded.
    """
    # Arrange
    items = [_item("A", 1, "\n\n\n"), _item("B", 2, "real_path.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# Edge cases: three independent conflict groups
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_three_independent_groups() -> None:
    """Verify three independent pairwise conflicts produce three distinct groups.

    Tests: analyze_impact_radius_conflicts with three disjoint connected components.
    How: Three pairs of items; each pair shares a unique file; no cross-pair overlap.
    Why: Validates that the union-find correctly identifies three separate components
    and assigns group_ids 1, 2, 3.
    """
    # Arrange
    items = [
        _item("A1", 1, "alpha.py"),
        _item("A2", 2, "alpha.py"),
        _item("B1", 3, "beta.py"),
        _item("B2", 4, "beta.py"),
        _item("C1", 5, "gamma.py"),
        _item("C2", 6, "gamma.py"),
    ]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 3
    assert {g.group_id for g in result} == {1, 2, 3}
    group_member_sets = {frozenset(g.items) for g in result}
    assert frozenset({"A1", "A2"}) in group_member_sets
    assert frozenset({"B1", "B2"}) in group_member_sets
    assert frozenset({"C1", "C2"}) in group_member_sets


# ---------------------------------------------------------------------------
# Edge cases: reason string format with multiple shared files
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_reason_format_multiple_shared_files() -> None:
    """Verify reason string lists multiple shared files comma-separated and sorted.

    Tests: analyze_impact_radius_conflicts reason string format.
    How: Two items share three files; verify reason string format and sort order.
    Why: Downstream consumers parse the reason string; it must be stable and sorted.
    """
    # Arrange — items share three files in different orders
    items = [
        _item("Feature X", 1, "zoo.py\naardvark.py\nmiddle.py"),
        _item("Feature Y", 2, "middle.py\nzoo.py\naardvark.py"),
    ]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    assert result[0].reason == "Shared systems: aardvark.py, middle.py, zoo.py"


# ---------------------------------------------------------------------------
# Edge cases: standalone # header lines excluded from path parsing
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_hash_header_lines_stripped() -> None:
    """Verify lines starting with # are not treated as file paths.

    Tests: analyze_impact_radius_conflicts markdown header line filtering.
    How: impact_radius body includes a '# Section Title' line alongside real paths.
    Why: Markdown section titles in backlog item bodies must not pollute path sets.
    """
    # Arrange
    body = "# Files Changed\nplugins/auth.py\n## Subsection\nplugins/auth.py"
    items = [_item("A", 1, body), _item("B", 2, "plugins/auth.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    assert "plugins/auth.py" in result[0].reason
    assert "#" not in result[0].reason


# ---------------------------------------------------------------------------
# ConflictGroup model compliance: return type
# ---------------------------------------------------------------------------


def test_analyze_impact_radius_conflicts_returns_list_of_conflict_group_instances() -> None:
    """Verify the return value is a list of ConflictGroup model instances.

    Tests: analyze_impact_radius_conflicts return type contract.
    How: Trigger a single conflict; verify the type of each element.
    Why: Callers pass the result directly to DispatchPlan.conflict_groups which
    expects ConflictGroup instances. Wrong types cause Pydantic validation failures.
    """
    # Arrange
    items = [_item("A", 1, "shared.py"), _item("B", 2, "shared.py")]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], ConflictGroup)
    assert isinstance(result[0].group_id, int)
    assert isinstance(result[0].reason, str)
    assert isinstance(result[0].items, list)


@pytest.mark.parametrize("count", [1, 2, 5])
def test_analyze_impact_radius_conflicts_single_item_always_returns_empty(count: int) -> None:
    """Verify that fewer than two items with valid paths never produce a conflict.

    Tests: analyze_impact_radius_conflicts minimum-group-size guard.
    How: Parametrize item counts below the threshold (single item with various paths).
    Why: A conflict requires at least two parties. This parametrized test catches
    off-by-one regressions in the minimum group size constant.
    """
    # Arrange — only one item with `count` paths; nothing to conflict with
    paths = "\n".join(f"path_{i}.py" for i in range(count))
    items = [_item("Lone Item", 99, paths)]

    # Act
    result = analyze_impact_radius_conflicts(items)

    # Assert
    assert result == []
