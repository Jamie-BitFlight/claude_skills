"""Guards shipped markdown against MCP call shapes that do not exist at runtime (#3162).

Three checks run over every shipped ``.md`` file: server-prefixed tool grants, instructed
tool calls, and artifact enum literals. Each resolves against the servers' live
``list_tools()`` output and the real ``ArtifactType`` / ``ArtifactStatus`` members, so a
tool rename or an enum change fails here instead of failing at dispatch time.

A corpus check alone is not enough. The guard this replaces passed while the defect it
targeted was live, because its regex silently matched nothing. Every guard here is
therefore also driven by ``fixtures/mcp_call_shape_known_defects.json``: each specimen is
injected into a copy of a real shipped file under ``tmp_path`` and the guard must flag it,
and each near-miss specimen is injected the same way and the guard must stay silent.
"""

from __future__ import annotations

import json
import operator
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from backlog_core.models import ArtifactStatus, ArtifactType

from tests.mcp_call_shape_guards import (
    Defect,
    ToolSurface,
    find_artifact_enum_defects,
    find_tool_call_defects,
    find_tool_grant_defects,
    load_tool_surface,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_PLUGIN_ROOT: Final = Path(__file__).resolve().parent.parent
_REPO_ROOT: Final = _PLUGIN_ROOT.parent.parent
_FIXTURE: Final = Path(__file__).resolve().parent / "fixtures" / "mcp_call_shape_known_defects.json"

_ARTIFACT_TYPES: Final = frozenset(member.value for member in ArtifactType)
_ARTIFACT_STATUSES: Final = frozenset(member.value for member in ArtifactStatus)

_KNOWN_DEFECTS: Final = json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _corpus_root() -> Path:
    """Return the directory holding shipped markdown.

    The defect classes span every plugin that instructs a dh MCP call, so the whole
    ``plugins/`` tree is in scope. A standalone plugin bundle has no such tree; there the
    plugin's own root is the entire shipped corpus.
    """
    plugins_dir = _REPO_ROOT / "plugins"
    return plugins_dir if plugins_dir.is_dir() else _PLUGIN_ROOT


def _iter_shipped_markdown(root: Path) -> Iterator[Path]:
    """Yield every shipped markdown file under ``root``.

    ``graphify-out/`` holds generated graph output, not authored instructions.
    """
    for path in sorted(root.rglob("*.md")):
        if "graphify-out" not in path.parts:
            yield path


@pytest.fixture(scope="session")
def tool_surface() -> ToolSurface:
    """The live tool listing from both dh MCP servers."""
    return load_tool_surface()


def _grant_guard(text: str, surface: ToolSurface) -> list[Defect]:
    return find_tool_grant_defects(text, surface)


def _call_guard(text: str, surface: ToolSurface) -> list[Defect]:
    return find_tool_call_defects(text, surface)


def _enum_guard(text: str, _surface: ToolSurface) -> list[Defect]:
    return find_artifact_enum_defects(text, _ARTIFACT_TYPES, _ARTIFACT_STATUSES)


_GUARDS: Final[dict[str, Callable[[str, ToolSurface], list[Defect]]]] = {
    "tool_grant": _grant_guard,
    "tool_call": _call_guard,
    "artifact_enum": _enum_guard,
}


def _scan_corpus(guard: Callable[[str, ToolSurface], list[Defect]], surface: ToolSurface) -> list[str]:
    """Run one guard over every shipped markdown file, returning one line per defect."""
    root = _corpus_root()
    return [
        f"{path.relative_to(root.parent)}: {defect}"
        for path in _iter_shipped_markdown(root)
        for defect in guard(path.read_text(encoding="utf-8"), surface)
    ]


def _mutate(tmp_path: Path, specimen: dict[str, str]) -> tuple[str, str]:
    """Copy the specimen's origin file into ``tmp_path`` and append its markdown.

    Returns:
        The clean text and the mutated text, so a caller can compare defect sets and
        attribute a new flag to the injected markdown rather than to the origin file.
    """
    origin = _REPO_ROOT / specimen["frozen_from"]
    if not origin.is_file():
        pytest.skip(f"origin file not present in this checkout: {specimen['frozen_from']}")
    target = tmp_path / origin.name
    shutil.copyfile(origin, target)
    clean = target.read_text(encoding="utf-8")
    mutated = clean + "\n" + specimen["markdown"]
    target.write_text(mutated, encoding="utf-8")
    return clean, mutated


def _injected_defects(
    guard: Callable[[str, ToolSurface], list[Defect]], clean: str, mutated: str, surface: ToolSurface
) -> list[str]:
    """Return the defect lines the mutation introduced, ignoring any already present."""
    baseline = [str(defect) for defect in guard(clean, surface)]
    after = [str(defect) for defect in guard(mutated, surface)]
    for line in baseline:
        if line in after:
            after.remove(line)
    return after


@pytest.mark.parametrize("specimen", _KNOWN_DEFECTS["must_flag"], ids=operator.itemgetter("id"))
def test_guard_flags_each_known_defect_class(
    specimen: dict[str, str], tmp_path: Path, tool_surface: ToolSurface
) -> None:
    """Injecting a known defect into a real shipped file must produce a flag.

    This is the check the guard being replaced lacked. Without it a regex that matches
    nothing reports a clean corpus and passes forever.
    """
    guard = _GUARDS[specimen["guard"]]
    clean, mutated = _mutate(tmp_path, specimen)

    introduced = _injected_defects(guard, clean, mutated, tool_surface)

    assert any(specimen["expect_contains"] in line for line in introduced), (
        f"Guard {specimen['guard']!r} did not flag the injected defect {specimen['id']!r}. "
        f"Expected a flag containing {specimen['expect_contains']!r}; got {introduced!r}. "
        "A guard that cannot fail on a live defect class is not a guard."
    )


@pytest.mark.parametrize("specimen", _KNOWN_DEFECTS["must_not_flag"], ids=operator.itemgetter("id"))
def test_guards_ignore_each_known_correct_shape(
    specimen: dict[str, str], tmp_path: Path, tool_surface: ToolSurface
) -> None:
    """Injecting a correct shape that resembles a defect must produce no flag.

    Each specimen is a shape a coarser check would flag — a Python attribute call, a
    wildcard grant, ``status=`` on a non-artifact tool, an authoring placeholder. A false
    positive here is what gets a guard switched off.
    """
    clean, mutated = _mutate(tmp_path, specimen)

    introduced = [line for guard in _GUARDS.values() for line in _injected_defects(guard, clean, mutated, tool_surface)]

    assert not introduced, (
        f"Correct shape {specimen['id']!r} was flagged as a defect: {introduced!r}. "
        "A guard that flags valid instructions is a guard authors will disable."
    )


def test_shipped_markdown_grants_only_live_dh_tools(tool_surface: ToolSurface) -> None:
    """Every ``mcp__plugin_dh_*__`` token must name a tool its server actually exposes.

    A grant for a tool that does not exist is dropped silently while the rest of the grant
    survives, so the agent starts without the capability its own frontmatter claims.
    """
    defects = _scan_corpus(_grant_guard, tool_surface)

    assert not defects, (
        "Shipped markdown grants or names dh MCP tools that do not exist on the server "
        "addressed by their prefix. Correct the token, or drop it if the capability was "
        "removed: " + "\n".join(defects)
    )


def test_shipped_markdown_calls_only_live_dh_tools(tool_surface: ToolSurface) -> None:
    """Every instructed ``tool(...)`` call must name a tool one of the servers exposes."""
    defects = _scan_corpus(_call_guard, tool_surface)

    assert not defects, (
        "Shipped markdown instructs calls to dh MCP tools that no server exposes, so an "
        "agent following the instruction cannot dispatch. Replace each with its live "
        "equivalent: " + "\n".join(defects)
    )


def test_shipped_markdown_uses_valid_artifact_enum_literals(tool_surface: ToolSurface) -> None:
    """Every instructed artifact enum literal must be a member of its enum.

    An invalid literal is rejected inside the handler, so the artifact is never stored and
    a later read of it is indistinguishable from a legitimate absence.
    """
    defects = _scan_corpus(_enum_guard, tool_surface)

    assert not defects, (
        "Shipped markdown instructs artifact calls with enum literals that are not members "
        "of ArtifactType/ArtifactStatus, so the registration never happens: " + "\n".join(defects)
    )
