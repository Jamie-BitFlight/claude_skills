#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "pydantic>=2.9", "pyyaml>=6.0"]
#
# [tool.ty.environment]
# extra-paths = ["."]
# ///
"""Tests for the output-style validator.

Every case here corresponds to a defect found in review. A frontmatter encoding that slips past
the validator is a real failure mode: the skill tells an agent to gate on this script's exit code,
so a false pass ships a broken style.

Run: uv run --with pytest pytest test_validate_output_style.py
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import validate_output_style as v

if TYPE_CHECKING:
    from pathlib import Path

VALID_BODY = "\n\nLead every response with the outcome.\n"


def write_style(directory: Path, name: str, frontmatter: str) -> Path:
    """Write a style file with the given frontmatter.

    Args:
        directory: Directory to write into.
        name: File stem.
        frontmatter: Frontmatter text, without the surrounding delimiters.

    Returns:
        The path written.
    """
    path = directory / f"{name}.md"
    path.write_text(f"---\n{frontmatter}\n---{VALID_BODY}", encoding="utf-8")
    return path


ACCEPTED = {
    "all-fields": "name: A\ndescription: One line\nkeep-coding-instructions: true\nforce-for-plugin: false",
    "description-absent": "name: A\nkeep-coding-instructions: true",
    "description-quoted": 'name: A\ndescription: "One line"',
    "description-holds-delimiter": 'name: A\ndescription: "use --- between sections"',
    "description-anchored": 'name: A\ndescription: &d "one line"',
    "name-absent": "description: One line",
}

REJECTED = {
    # Multiline encodings. Each reached the validator by a different route.
    "folded": "name: A\ndescription: >-\n  folded text",
    "literal": "name: A\ndescription: |\n  literal text",
    "quoted-key": "name: A\n'description': |\n  literal text",
    "tagged": "name: A\ndescription: !!str >\n  tagged folded",
    "implicit-continuation": "name: A\ndescription: this value continues\n  onto a second line",
    "escaped-newline": 'name: A\ndescription: "first\\nsecond"',
    # Field types.
    "name-not-string": "name: 42\ndescription: fine",
    "keep-coding-quoted": 'name: A\nkeep-coding-instructions: "false"',
    "force-for-plugin-quoted": 'name: A\nforce-for-plugin: "true"',
    # Structure.
    "merge-key": "base: &base\n  description: >-\n    folded through a merge\nname: A\n<<: *base",
    "non-string-key": "1: value\nname: A",
}


@pytest.mark.parametrize("frontmatter", ACCEPTED.values(), ids=list(ACCEPTED))
def test_accepts_valid_frontmatter(tmp_path: Path, frontmatter: str) -> None:
    """A well-formed style validates, whatever optional fields it omits."""
    result = v.validate(write_style(tmp_path, "s", frontmatter))
    assert result.valid, result.problems


@pytest.mark.parametrize("frontmatter", REJECTED.values(), ids=list(REJECTED))
def test_rejects_invalid_frontmatter(tmp_path: Path, frontmatter: str) -> None:
    """Each known-bad encoding is reported, not silently accepted."""
    result = v.validate(write_style(tmp_path, "s", frontmatter))
    assert not result.valid
    assert result.problems


def test_rejects_missing_closing_delimiter(tmp_path: Path) -> None:
    """A file that opens frontmatter without closing it is not a style."""
    path = tmp_path / "s.md"
    path.write_text("---\ndescription: okay\n", encoding="utf-8")
    assert not v.validate(path).valid


def test_rejects_file_without_frontmatter(tmp_path: Path) -> None:
    """Prose alone is not a style."""
    path = tmp_path / "s.md"
    path.write_text("just prose\n", encoding="utf-8")
    assert not v.validate(path).valid


def test_accepts_empty_frontmatter_block(tmp_path: Path) -> None:
    """Every field is optional, so an empty block is a valid style."""
    path = tmp_path / "s.md"
    path.write_text("---\n\n---\n\nBody.\n", encoding="utf-8")
    result = v.validate(path)
    assert result.valid, result.problems
    assert result.fields == {}


def test_accepts_adjacent_delimiters(tmp_path: Path) -> None:
    """A frontmatter block with no line between its delimiters is still a block."""
    path = tmp_path / "s.md"
    path.write_text("---\n---\n\nBody.\n", encoding="utf-8")
    assert v.validate(path).valid


def test_rejects_non_mapping_frontmatter(tmp_path: Path) -> None:
    """Frontmatter that parses to a list is not a style."""
    assert not v.validate(write_style(tmp_path, "s", "- one\n- two")).valid


def test_reports_missing_file_without_raising(tmp_path: Path) -> None:
    """A path that does not exist produces a problem, not a traceback."""
    result = v.validate(tmp_path / "absent.md")
    assert not result.valid
    assert result.problems


def test_recursive_alias_does_not_crash(tmp_path: Path) -> None:
    """A cyclic node graph terminates instead of exhausting the stack.

    A recursive alias makes both node walks revisit the same node forever unless they track what
    they have seen.
    """
    result = v.validate(write_style(tmp_path, "s", "name: A\na: &a\n  self: *a"))
    assert isinstance(json.loads(result.model_dump_json()), dict)


def test_result_serialises_with_a_non_string_key(tmp_path: Path) -> None:
    """A non-string YAML key is reported rather than breaking the JSON contract."""
    result = v.validate(write_style(tmp_path, "s", "1: value\nname: A"))
    payload = json.loads(result.model_dump_json())
    assert payload["fields"]["1"] == "str"
    assert any("must be a string" in problem for problem in result.problems)


def test_paths_with_shell_metacharacters(tmp_path: Path) -> None:
    """A path is opened as given; the script never re-interprets it as shell text."""
    awkward = tmp_path / "a dir with spaces" / "O'Brien $USER"
    awkward.mkdir(parents=True)
    path = write_style(awkward, "style-$USER", "name: A\ndescription: fine")
    result = v.validate(path)
    assert result.valid, result.problems
    assert result.path == str(path)


def make_plugin(root: Path, manifest: dict[str, object], style_dirs: dict[str, str]) -> Path:
    """Build a fixture plugin.

    Args:
        root: Directory to build in.
        manifest: The plugin.json contents.
        style_dirs: Mapping of directory name to the style file stem to place inside it.

    Returns:
        The plugin root.
    """
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    for directory, stem in style_dirs.items():
        target = root / directory
        target.mkdir(parents=True, exist_ok=True)
        write_style(target, stem, "name: A\ndescription: fine")
    return root


def test_absent_manifest_key_scans_the_default_directory(tmp_path: Path) -> None:
    """With no outputStyles key, the default directory is still scanned."""
    plugin = make_plugin(tmp_path / "p", {"name": "p"}, {"output-styles": "default"})
    result = v.discover(tmp_path, plugin)
    assert [p.rsplit("/", 1)[-1] for p in result.plugin] == ["default.md"]


def test_declared_paths_replace_the_default_scan(tmp_path: Path) -> None:
    """Declaring outputStyles replaces the default scan rather than adding to it."""
    plugin = make_plugin(
        tmp_path / "p", {"name": "p", "outputStyles": ["./extras/"]}, {"output-styles": "default", "extras": "declared"}
    )
    names = [p.rsplit("/", 1)[-1] for p in v.discover(tmp_path, plugin).plugin]
    assert names == ["declared.md"]


def test_empty_declaration_loads_nothing(tmp_path: Path) -> None:
    """An empty outputStyles array declares no paths, so nothing is loaded.

    This differs from an absent key, which leaves the default scan in place.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": []}, {"output-styles": "default"})
    assert v.discover(tmp_path, plugin).plugin == []


def test_declared_hidden_directory_is_found(tmp_path: Path) -> None:
    """A dot-prefixed declared directory resolves correctly.

    ``lstrip("./")`` would strip the leading dot of ``.styles`` and search ``styles`` instead.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": ["./.styles/"]}, {".styles": "hidden"})
    names = [p.rsplit("/", 1)[-1] for p in v.discover(tmp_path, plugin).plugin]
    assert names == ["hidden.md"]


def test_string_declaration_is_accepted(tmp_path: Path) -> None:
    """outputStyles accepts a bare string as well as an array."""
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": "./extras/"}, {"extras": "one"})
    assert [p.rsplit("/", 1)[-1] for p in v.discover(tmp_path, plugin).plugin] == ["one.md"]


def test_unreadable_manifest_is_reported_and_scans_nothing(tmp_path: Path) -> None:
    """Malformed JSON is a manifest defect, not an absent key.

    Falling back to the default scan would report the plugin as shipping styles on the strength of
    a manifest nothing can read.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p"}, {"output-styles": "default"})
    (plugin / ".claude-plugin" / "plugin.json").write_text("{not json", encoding="utf-8")
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert len(result.plugin_manifest_problems) == 1
    assert "not valid JSON" in result.plugin_manifest_problems[0]


def test_non_object_manifest_root_is_reported_and_scans_nothing(tmp_path: Path) -> None:
    """A manifest whose JSON root is a list is a defect, not a traceback and not an absent key.

    ``json.loads`` succeeds on ``[]``, so reading the key off the result would raise AttributeError.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p"}, {"output-styles": "default"})
    (plugin / ".claude-plugin" / "plugin.json").write_text("[]", encoding="utf-8")
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_manifest_problems == [
        f"{plugin / '.claude-plugin' / 'plugin.json'}: manifest root is array, expected an object"
    ]


def test_missing_manifest_is_not_a_defect(tmp_path: Path) -> None:
    """A directory with no manifest declares nothing, and the default scan still applies."""
    root = tmp_path / "p"
    (root / "output-styles").mkdir(parents=True)
    write_style(root / "output-styles", "default", "name: A\ndescription: fine")
    result = v.discover(tmp_path, root)
    assert [p.rsplit("/", 1)[-1] for p in result.plugin] == ["default.md"]
    assert result.plugin_manifest_problems == []


def test_invalid_output_styles_type_is_reported_and_scans_nothing(tmp_path: Path) -> None:
    """outputStyles: 42 is a declaration this cannot read, so it is not treated as absent.

    Scanning the default directory here would attribute styles to a plugin whose manifest names
    none, misreporting a malformed plugin as one that ships usable styles.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": 42}, {"output-styles": "default"})
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_declared_paths == []
    assert result.plugin_manifest_problems == [
        f"{plugin / '.claude-plugin' / 'plugin.json'}: outputStyles is number, expected a string or an array of strings"
    ]


def test_null_output_styles_is_reported_rather_than_absent(tmp_path: Path) -> None:
    """An explicit null is a present declaration, and its message names the JSON type."""
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": None}, {"output-styles": "default"})
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert "outputStyles is null" in result.plugin_manifest_problems[0]


def test_non_string_entries_are_reported_and_valid_ones_kept(tmp_path: Path) -> None:
    """A mixed array keeps its string entries and reports each entry it dropped, by index.

    Silently dropping them would report the plugin's styles as complete when the manifest is not.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": ["./extras/", 42, None]}, {"extras": "declared"})
    result = v.discover(tmp_path, plugin)
    assert [p.rsplit("/", 1)[-1] for p in result.plugin] == ["declared.md"]
    assert result.plugin_declared_paths == ["./extras/"]
    manifest = plugin / ".claude-plugin" / "plugin.json"
    assert result.plugin_manifest_problems == [
        f"{manifest}: outputStyles entry 1 is number, expected a string",
        f"{manifest}: outputStyles entry 2 is null, expected a string",
    ]


def test_valid_manifest_reports_no_problems(tmp_path: Path) -> None:
    """A well-formed declaration leaves plugin_manifest_problems empty."""
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": ["./extras/"]}, {"extras": "declared"})
    assert v.discover(tmp_path, plugin).plugin_manifest_problems == []


def test_boolean_output_styles_is_not_read_as_a_number(tmp_path: Path) -> None:
    """JSON true is a boolean, even though Python bool subclasses int."""
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": True}, {"output-styles": "default"})
    assert "outputStyles is boolean" in v.discover(tmp_path, plugin).plugin_manifest_problems[0]


def test_declared_path_escaping_the_plugin_root_is_rejected(tmp_path: Path) -> None:
    """A declared ../outside/ entry is not searched, and is reported as rejected.

    Phase 1 tells the agent to read every reported style, so an escaping entry in an untrusted
    manifest would feed it unrelated file content.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    write_style(outside, "not-mine", "name: A\ndescription: fine")
    plugin = make_plugin(tmp_path / "plug", {"name": "p", "outputStyles": "./../outside/"}, {})
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_rejected_paths == ["./../outside/"]


def test_absolute_declared_path_is_rejected(tmp_path: Path) -> None:
    """An absolute declared path is outside the plugin root by definition."""
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    write_style(outside, "not-mine", "name: A\ndescription: fine")
    plugin = make_plugin(tmp_path / "plug", {"name": "p", "outputStyles": str(outside)}, {})
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_rejected_paths == [str(outside)]


def test_symlink_escaping_the_plugin_root_is_rejected(tmp_path: Path) -> None:
    """A symlink inside the plugin that points outside it is rejected.

    ``Path.resolve`` follows symlinks, so the confinement check sees the real target rather than
    the link's location inside the root.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    write_style(outside, "not-mine", "name: A\ndescription: fine")
    plugin = make_plugin(tmp_path / "plug", {"name": "p", "outputStyles": "./linked/"}, {})
    try:
        (plugin / "linked").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow creating a symlink here")
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_rejected_paths == ["./linked/"]


def test_symlinked_style_file_escaping_the_plugin_is_rejected(tmp_path: Path) -> None:
    """A markdown symlink inside an accepted directory is judged by its target.

    Confining the declared directory is not enough: glob and is_file both follow symlinks, so a
    link sitting legitimately inside output-styles/ can still point anywhere on disk.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    target = write_style(outside, "evil", "name: A\ndescription: fine")
    plugin = make_plugin(tmp_path / "plug", {"name": "p"}, {})
    (plugin / "output-styles").mkdir()
    try:
        (plugin / "output-styles" / "looks-fine.md").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow creating a symlink here")
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_rejected_paths == [str(plugin / "output-styles" / "looks-fine.md")]


def test_real_style_file_beside_an_escaping_symlink_is_kept(tmp_path: Path) -> None:
    """Rejecting one escaping link does not discard the plugin's genuine styles."""
    outside = tmp_path / "outside"
    outside.mkdir()
    target = write_style(outside, "evil", "name: A\ndescription: fine")
    plugin = make_plugin(tmp_path / "plug", {"name": "p"}, {"output-styles": "genuine"})
    try:
        (plugin / "output-styles" / "looks-fine.md").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow creating a symlink here")
    result = v.discover(tmp_path, plugin)
    assert [p.rsplit("/", 1)[-1] for p in result.plugin] == ["genuine.md"]
    assert len(result.plugin_rejected_paths) == 1


def test_declared_path_inside_the_root_is_not_rejected(tmp_path: Path) -> None:
    """The confinement check does not reject a legitimate nested directory."""
    plugin = make_plugin(tmp_path / "plug", {"name": "p", "outputStyles": "./deep/nested/"}, {"deep/nested": "ok"})
    result = v.discover(tmp_path, plugin)
    assert [p.rsplit("/", 1)[-1] for p in result.plugin] == ["ok.md"]
    assert result.plugin_rejected_paths == []


def test_project_scan_walks_ancestors_to_the_repository_root(tmp_path: Path) -> None:
    """Every .claude/output-styles between the start and the repo root is in scope."""
    (tmp_path / ".git").mkdir()
    leaf = tmp_path / "pkg" / "sub"
    leaf.mkdir(parents=True)
    for directory, stem in ((tmp_path, "root"), (leaf, "leaf")):
        styles = directory / ".claude" / "output-styles"
        styles.mkdir(parents=True)
        write_style(styles, stem, "name: A\ndescription: fine")

    found = {p.rsplit("/", 1)[-1] for p in v.discover(leaf, None).project}
    assert found == {"root.md", "leaf.md"}


def test_project_symlink_escaping_the_checkout_is_rejected(tmp_path: Path) -> None:
    """A project style linking outside the repository is not the checkout's content.

    A cloned repository can belong to someone else, so a link out of the tree is treated the same
    way as a plugin's escaping path.
    """
    (tmp_path / "repo" / ".claude" / "output-styles").mkdir(parents=True)
    (tmp_path / "repo" / ".git").mkdir()
    outside = tmp_path / "secrets"
    outside.mkdir()
    target = write_style(outside, "private", "name: A\ndescription: fine")
    link = tmp_path / "repo" / ".claude" / "output-styles" / "leak.md"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow creating a symlink here")
    result = v.discover(tmp_path / "repo", None)
    assert result.project == []
    assert result.project_rejected_paths == [str(link)]


def test_manifest_path_without_the_required_prefix_is_rejected(tmp_path: Path) -> None:
    """rules/plugin-json.md requires every component path to start with './'.

    Claude's own plugin validator rejects a manifest without it, so reporting styles under such a
    path would claim the plugin ships something Claude does not load.
    """
    plugin = make_plugin(tmp_path / "p", {"name": "p", "outputStyles": "extras/"}, {"extras": "s"})
    result = v.discover(tmp_path, plugin)
    assert result.plugin == []
    assert result.plugin_rejected_paths == ["extras/"]


def test_project_scan_stops_at_the_repository_root(tmp_path: Path) -> None:
    """A style above the repository root is out of scope."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    outside = tmp_path / ".claude" / "output-styles"
    outside.mkdir(parents=True)
    write_style(outside, "outside", "name: A\ndescription: fine")
    assert v.discover(repo, None).project == []


def test_managed_directory_differs_per_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """The managed settings directory is resolved per platform, and never the legacy path."""
    expected = {
        "darwin": "/Library/Application Support/ClaudeCode",
        "win32": "C:/Program Files/ClaudeCode",
        "linux": "/etc/claude-code",
    }
    for platform, path in expected.items():
        monkeypatch.setattr(v.sys, "platform", platform)
        assert v.managed_settings_directory().as_posix() == path


def test_discovery_result_reports_every_scope(tmp_path: Path) -> None:
    """discover always returns the full key set, so a caller can rely on the shape."""
    payload = json.loads(v.discover(tmp_path, None).model_dump_json())
    assert set(payload) == {
        "user",
        "managed",
        "project",
        "project_rejected_paths",
        "plugin",
        "plugin_declared_paths",
        "plugin_rejected_paths",
        "plugin_manifest_problems",
    }
