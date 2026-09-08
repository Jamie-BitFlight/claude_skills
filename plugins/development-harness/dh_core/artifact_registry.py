"""The artifact-type registry declared in this plugin's ``AGENTS.md``, and the one locator for it.

``AGENTS.md``'s "Artifact types and registering agents" section holds the complete registry of
document-artifact types: every ``artifact_register`` call must match a ``(Type, Registering
agents)`` pair it lists, and its ``Gate-read`` column marks the types whose read decides a workflow
branch. Two readers consume that one table and they must not encode where it is twice:

* :mod:`dh_core.workflow_multigraph.decomposition_gate` resolves an ``ARTIFACT`` referent against
  the ``Type`` column -- ``plugins/development-harness/ARCHITECTURE.md``, "The work graph" §
  "The decomposition-exit gate", Tier 1: an ``ARTIFACT`` referent resolves to "a type in the
  artifact registry, with its id";
* ``tests/test_artifact_type_ownership_drift.py`` holds the shipped markdown's registrations
  against the same table's ownership and gate-read columns.

Both call :func:`registry_rows` here. A locator each reader spells for itself is two encodings of
one fact: the heading anchor and the header-row anchor drifted apart once already, and only the
reader that was not a test noticed.

The locator is loud on purpose. A registry that cannot be found in a file that exists raises
:class:`ArtifactRegistryError` rather than reporting an empty registry, because an empty registry
is indistinguishable from a real one holding no types: it reads as "no artifact type exists", and
every ``ARTIFACT`` referent then fails to resolve with nothing reported about why. That is the
failure this module exists to make impossible, per ``rules/silent-failure-prevention.md``'s
"If no fallback action is possible, raise or warn".

Markdown structure is read through the marko GFM AST, per this repo's rule against regex parsers
for markdown structure.
"""

from __future__ import annotations

from pathlib import Path

from marko import Markdown
from marko.block import Heading
from marko.ext.gfm.elements import Table
from pydantic import BaseModel, ConfigDict, Field

REGISTRY_HEADING = "Artifact types and registering agents"
"""The AGENTS.md heading whose table is the artifact-type registry."""

TYPE_COLUMN = "Type"
"""The registry column naming the artifact type an ``artifact_register`` call passes."""

AGENTS_COLUMN = "Registering agents"
"""The registry column naming the writers permitted to register that type."""

GATE_READ_COLUMN = "Gate-read"
"""The registry column marking the types whose read result decides a workflow branch."""

REQUIRED_COLUMNS = (TYPE_COLUMN, AGENTS_COLUMN, GATE_READ_COLUMN)
"""The columns both readers consume; the table's remaining columns are prose for humans."""

GATE_READ_VALUES = {"yes": True, "no": False}
"""The ``Gate-read`` cell values the registry declares, and what each means."""

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
"""This plugin's root -- the directory holding the ``AGENTS.md`` that declares the registry."""

AGENTS_MD = PLUGIN_ROOT / "AGENTS.md"
"""The registry's own file, for a reader that already runs inside this checkout."""

REPO_RELATIVE_AGENTS_MD = Path("plugins/development-harness/AGENTS.md")
"""The same file, relative to a repository root, for a reader resolving against a given checkout."""


class ArtifactRegistryError(LookupError):
    """Raised when a file exists but its artifact-type registry is not what this module declares.

    Carries the path, so a caller reporting the failure names the file that must be repaired.
    """


class ArtifactTypeRow(BaseModel):
    """One row of the artifact-type registry, as both readers consume it."""

    model_config = ConfigDict(frozen=True)

    artifact_type: str = Field(min_length=1, description="The value an artifact_register call passes as the type.")
    agents: frozenset[str] = Field(
        default_factory=frozenset, description="The writers this row permits, as the `agent` argument's values."
    )
    gate_read: bool = Field(default=False, description="Whether a read of this type decides a workflow branch.")


def inline_text(node: object) -> str:
    """Reconstruct a marko node's plain text from its children, at any nesting depth.

    Walks the node's children recursively, so text inside a code span, emphasis, or a link's label
    is kept and the markers around it are dropped. A node whose ``children`` is already a string is
    a leaf and yields that string.

    Args:
        node: A parsed marko element, or any object exposing marko's ``children`` attribute.

    Returns:
        The node's text with inline formatting stripped; the empty string for a node holding none.
    """
    children = getattr(node, "children", None)
    if isinstance(children, str):
        return children
    if children is None:
        return ""
    return "".join(inline_text(child) for child in children)


def registry_rows(agents_md: Path) -> tuple[ArtifactTypeRow, ...]:
    """Parse the artifact-type registry table out of an ``AGENTS.md``.

    Locates the table by the :data:`REGISTRY_HEADING` section it lives under, then reads its
    columns by the names in :data:`REQUIRED_COLUMNS` rather than by position, so a column added or
    reordered does not silently shift what each reader reads.

    Args:
        agents_md: Path to the ``AGENTS.md`` declaring the registry.

    Returns:
        One :class:`ArtifactTypeRow` per body row of the registry table, in document order.

    Raises:
        ArtifactRegistryError: If the file does not exist, the section is absent, the section holds
            no table, the table omits a required column, or a row carries an empty type or a
            ``Gate-read`` value the registry does not declare. Each of those is the registry being
            somewhere other than where this module says it is, which no caller can detect from an
            empty result.
    """
    if not agents_md.is_file():
        raise ArtifactRegistryError(f"{agents_md}: no such file, so it declares no artifact-type registry")
    document = Markdown(extensions=["gfm"]).parse(agents_md.read_text(encoding="utf-8"))
    table = find_registry_table(document, agents_md)
    header, *body = table.children
    columns = column_indices(header, agents_md)
    return tuple(parse_row(row, columns, agents_md) for row in body)


def find_registry_table(document: object, agents_md: Path) -> Table:
    """Return the GFM table under the registry's heading.

    Args:
        document: The parsed marko document.
        agents_md: The file it was parsed from, named in the raised error.

    Returns:
        The first table appearing under the :data:`REGISTRY_HEADING` section.

    Raises:
        ArtifactRegistryError: If no heading matches, or the section ends before a table appears.
    """
    in_section = False
    for child in getattr(document, "children", []):
        if isinstance(child, Heading):
            if in_section:
                break
            in_section = inline_text(child).strip() == REGISTRY_HEADING
            continue
        if in_section and isinstance(child, Table):
            return child
    found = "the section holds no table" if in_section else "no heading matches"
    raise ArtifactRegistryError(f"{agents_md}: no artifact-type registry under heading {REGISTRY_HEADING!r} -- {found}")


def column_indices(header: object, agents_md: Path) -> dict[str, int]:
    """Map each required column name to its position in the registry table's header row.

    Args:
        header: The table's header row.
        agents_md: The file it was parsed from, named in the raised error.

    Returns:
        One entry per name in :data:`REQUIRED_COLUMNS`.

    Raises:
        ArtifactRegistryError: If the header row omits a required column.
    """
    names = [inline_text(cell).strip() for cell in getattr(header, "children", [])]
    missing = [column for column in REQUIRED_COLUMNS if column not in names]
    if missing:
        raise ArtifactRegistryError(
            f"{agents_md}: the artifact-type registry table omits column(s) {missing!r}; its header row names {names!r}"
        )
    return {column: names.index(column) for column in REQUIRED_COLUMNS}


def parse_row(row: object, columns: dict[str, int], agents_md: Path) -> ArtifactTypeRow:
    """Read one body row of the registry table into an :class:`ArtifactTypeRow`.

    Args:
        row: The table body row.
        columns: Column-name to position map, from :func:`column_indices`.
        agents_md: The file it was parsed from, named in the raised error.

    Returns:
        The row's declared type, its registering agents, and its gate-read flag.

    Raises:
        ArtifactRegistryError: If the row is short of the required columns, names an empty type, or
            carries a ``Gate-read`` value outside :data:`GATE_READ_VALUES`.
    """
    cells = [inline_text(cell).strip() for cell in getattr(row, "children", [])]
    if len(cells) <= max(columns.values()):
        raise ArtifactRegistryError(f"{agents_md}: artifact-type registry row {cells!r} is short of its columns")
    artifact_type = cells[columns[TYPE_COLUMN]]
    if not artifact_type:
        raise ArtifactRegistryError(f"{agents_md}: artifact-type registry row {cells!r} names no type")
    gate_read = cells[columns[GATE_READ_COLUMN]].lower()
    if gate_read not in GATE_READ_VALUES:
        raise ArtifactRegistryError(
            f"{agents_md}: artifact type {artifact_type!r} declares {GATE_READ_COLUMN} {gate_read!r}, "
            f"which is not one of {sorted(GATE_READ_VALUES)}"
        )
    agents = frozenset(agent.strip() for agent in cells[columns[AGENTS_COLUMN]].split(",") if agent.strip())
    return ArtifactTypeRow(artifact_type=artifact_type, agents=agents, gate_read=GATE_READ_VALUES[gate_read])


def artifact_types(agents_md: Path) -> frozenset[str]:
    """Return the artifact types the registry names.

    Args:
        agents_md: Path to the ``AGENTS.md`` declaring the registry.

    Returns:
        Every value in the registry's :data:`TYPE_COLUMN`; the empty set when ``agents_md`` itself
        does not exist, which is the case of a checkout that ships no such registry rather than one
        whose registry moved.

    Raises:
        ArtifactRegistryError: If the file exists but its registry is not where this module says it
            is -- see :func:`registry_rows`.
    """
    if not agents_md.is_file():
        return frozenset()
    return frozenset(row.artifact_type for row in registry_rows(agents_md))
