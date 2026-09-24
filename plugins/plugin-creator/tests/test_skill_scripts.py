"""Smoke tests for the skill scaffolder (init_skill.py), packager (package_skill.py),
and quick-validator (quick_validate.py).

Tests: End-to-end execution of each script's public API against a tmpdir.
How: Import the module-level functions directly (pythonpath includes the scripts
     directory), call them with fresh pytest tmp_path fixtures, and assert outputs.
Why: CI previously ran only linters — a regression in scaffolding path resolution,
     template rendering, ZIP construction, or validation rule firing would be
     invisible until a developer hit it manually.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest
from ruamel.yaml import YAML

_yaml = YAML(typ="safe")


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("CLAUDE.md", "../../rules/frontmatter-requirements.md"),
        ("CLAUDE.md", "../../rules/plugin-json.md"),
        ("examples/agents/example-agent.md", "../../skills/claude-subagent-reference/SKILL.md"),
        ("examples/agents/example-agent.md", "../../skills/agent-creator/SKILL.md"),
        ("examples/agents/example-agent.md", "../../scripts/README.md"),
        ("examples/skills/example-skill/SKILL.md", "../../../skills/claude-skills-overview-2026/SKILL.md"),
        ("examples/skills/example-skill/SKILL.md", "../../../scripts/README.md"),
        ("references/USAGE.md", "./ARCHITECTURE.md"),
    ],
)
def test_repaired_plugin_documentation_link_exists(source: str, target: str) -> None:
    plugin_root = Path(__file__).parents[1]
    assert (plugin_root / source).parent.joinpath(target).resolve().exists()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_valid_skill(base: Path, name: str = "test-skill") -> Path:
    """Write a minimal, validation-passing skill directory under *base*."""
    skill_dir = base / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A test skill for smoke testing\n---\n\n# {name}\n", encoding="utf-8"
    )
    return skill_dir


def _parse_frontmatter(skill_md: Path) -> dict:
    """Return the parsed YAML frontmatter dict from a SKILL.md file."""
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, f"No YAML frontmatter delimiters found in {skill_md}"
    result = _yaml.load(match.group(1))
    assert isinstance(result, dict), "Frontmatter must parse as a YAML mapping"
    return result  # type: ignore[return-value]


# ===========================================================================
# init_skill.py — scaffolder
# ===========================================================================


class TestInitSkillScaffolder:
    """Smoke tests for init_skill.init_skill().

    Tests: File-tree creation, template rendering, and input guards.
    How: Call init_skill() against pytest tmp_path; assert filesystem state.
    Why: A regression in path resolution or template variables would break
         every scaffold operation silently until a developer notices.
    """

    def test_happy_path_creates_expected_file_tree(self, tmp_path: Path) -> None:
        """init_skill creates SKILL.md, scripts/, references/, and assets/.

        Tests: Full file-tree produced by a successful scaffold run.
        How: Call init_skill with a fresh tmp_path; assert directory and file presence.
        Why: Missing output files mean downstream users cannot build on the scaffold.
        """
        from init_skill import init_skill

        result = init_skill("my-test-skill", str(tmp_path))

        assert result is not None
        assert result == tmp_path / "my-test-skill"
        assert result.is_dir()

        # SKILL.md must exist
        skill_md = result / "SKILL.md"
        assert skill_md.exists()

        # Resource subdirectories with example files must be created
        assert (result / "scripts" / "example.py").exists()
        assert (result / "references" / "api_reference.md").exists()
        assert (result / "assets" / "example_asset.txt").exists()

    def test_skill_md_contains_correct_name(self, tmp_path: Path) -> None:
        """Generated SKILL.md embeds the skill name and title correctly.

        Tests: Template variable substitution in SKILL.md.
        How: Inspect the raw text of the generated SKILL.md.
        Why: Wrong name in SKILL.md breaks skilllint name-matches-directory rules.
        """
        from init_skill import init_skill

        result = init_skill("name-check-skill", str(tmp_path))
        assert result is not None

        content = (result / "SKILL.md").read_text(encoding="utf-8")
        assert "name: name-check-skill" in content
        assert "Name Check Skill" in content  # title-cased

    def test_skill_md_frontmatter_is_parseable_yaml(self, tmp_path: Path) -> None:
        """Generated SKILL.md has syntactically valid YAML frontmatter.

        Tests: Template rendering does not produce broken YAML syntax.
        How: Parse the frontmatter block with ruamel.yaml and verify the name key.
        Why: A template quoting bug would silently break every downstream validator.
        """
        from init_skill import init_skill

        result = init_skill("yaml-check-skill", str(tmp_path))
        assert result is not None

        fm = _parse_frontmatter(result / "SKILL.md")
        assert fm.get("name") == "yaml-check-skill"
        assert isinstance(fm.get("description"), str), "description must parse as a string, not a block-scalar artifact"

    def test_invalid_name_uppercase_is_rejected(self) -> None:
        """validate_skill_name rejects names containing uppercase letters.

        Tests: Name validation guard (does not touch the filesystem).
        How: Call validate_skill_name directly with an uppercase name.
        Why: Scaffold directories must match the hyphen-case name convention.
        """
        from init_skill import validate_skill_name

        is_valid, err = validate_skill_name("MyBadName")
        assert not is_valid
        assert err is not None

    @pytest.mark.parametrize("name", ["-bad-start", "bad-end-", "bad--middle"])
    def test_invalid_name_hyphen_placement_is_rejected(self, name: str) -> None:
        """validate_skill_name rejects leading, trailing, or consecutive hyphens.

        Tests: Edge-case in the regex guard.
        How: Call validate_skill_name with malformed hyphen placement.
        Why: Allows the test to catch regressions to the regex pattern.
        """
        from init_skill import validate_skill_name

        is_valid, err = validate_skill_name(name)
        assert not is_valid
        assert err is not None

    def test_lowercase_unicode_name_is_accepted(self) -> None:
        from init_skill import validate_skill_name

        is_valid, err = validate_skill_name("données-分析")

        assert is_valid
        assert err is None

    def test_name_length_is_checked_after_nfkc_normalization(self) -> None:
        from init_skill import validate_skill_name

        is_valid, err = validate_skill_name("ﬀ" * 33)

        assert not is_valid
        assert err is not None

    def test_init_skill_writes_nfkc_normalized_name(self, tmp_path: Path) -> None:
        from init_skill import init_skill

        result = init_skill("cafe\u0301", str(tmp_path))

        assert result == tmp_path / "café"
        assert _parse_frontmatter(result / "SKILL.md")["name"] == "café"

    def test_duplicate_directory_returns_none(self, tmp_path: Path) -> None:
        """init_skill returns None when the target directory already exists.

        Tests: Idempotency guard that prevents accidental overwrites.
        How: Pre-create the skill directory then call init_skill again.
        Why: Silent overwrite would corrupt a developer's work-in-progress skill.
        """
        from init_skill import init_skill

        (tmp_path / "existing-skill").mkdir()
        result = init_skill("existing-skill", str(tmp_path))
        assert result is None

    def test_example_script_is_executable(self, tmp_path: Path) -> None:
        """Generated example.py has executable permission bits set.

        Tests: create_resource_file executable flag is honoured.
        How: Check stat mode of scripts/example.py after init_skill.
        Why: A non-executable template script confuses developers trying to run it.
        """
        from init_skill import init_skill

        result = init_skill("exec-bit-skill", str(tmp_path))
        assert result is not None

        script = result / "scripts" / "example.py"
        assert script.stat().st_mode & 0o111, "example.py should have execute bits set"


# ===========================================================================
# package_skill.py — packager
# ===========================================================================


class TestPackageSkillPackager:
    """Smoke tests for package_skill.package_skill().

    Tests: ZIP archive creation, validation gate, and input guards.
    How: Build skill directories with tmp_path, call package_skill(), inspect archives.
    Why: A regression in zip path calculation or validation wiring would produce
         empty or malformed archives, or silently package broken skills.
    """

    def test_happy_path_creates_skill_zip(self, tmp_path: Path) -> None:
        """package_skill creates a .skill file containing SKILL.md.

        Tests: End-to-end packaging of a valid skill directory.
        How: Build a valid skill dir, package it, verify archive name and content.
        Why: The most basic regression: ZIP not created or SKILL.md not included.
        """
        from package_skill import package_skill

        skill_dir = _make_minimal_valid_skill(tmp_path / "source", "demo-skill")
        out_dir = tmp_path / "dist"

        result = package_skill(skill_dir, out_dir)

        assert result is not None
        assert result.name == "demo-skill.skill"
        assert result.suffix == ".skill"
        assert result.exists()

        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
        assert "demo-skill/SKILL.md" in names, f"Expected 'demo-skill/SKILL.md' in archive entries: {names}"

    def test_zip_contains_all_source_files(self, tmp_path: Path) -> None:
        """All files in the skill directory are included in the .skill archive.

        Tests: ZipFile walk produces complete entries.
        How: Add an extra file to the skill dir; verify it appears in the ZIP.
        Why: A path-filter bug could silently omit resource files.
        """
        from package_skill import package_skill

        skill_dir = _make_minimal_valid_skill(tmp_path / "source", "full-skill")
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")

        result = package_skill(skill_dir, tmp_path / "dist")
        assert result is not None

        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
        assert "full-skill/references/guide.md" in names, (
            f"Expected 'full-skill/references/guide.md' in archive: {names}"
        )

    def test_missing_skill_md_returns_none(self, tmp_path: Path) -> None:
        """package_skill returns None when SKILL.md is absent.

        Tests: Guard that prevents packaging a non-skill directory.
        How: Pass an empty directory (no SKILL.md) to package_skill.
        Why: Packaging a non-skill would silently produce a broken archive.
        """
        from package_skill import package_skill

        bad_dir = tmp_path / "not-a-skill"
        bad_dir.mkdir()

        result = package_skill(bad_dir)
        assert result is None
        # No .skill artifact must be created when SKILL.md is absent
        assert not list(tmp_path.rglob("*.skill")), (
            "package_skill must not create any archive artifact when SKILL.md is missing"
        )

    def test_validation_failure_blocks_packaging(self, tmp_path: Path) -> None:
        """package_skill returns None when quick_validate rejects the skill.

        Tests: Validation gate before ZIP creation.
        How: Create a SKILL.md with an unexpected frontmatter key.
        Why: CI must never package a skill that fails local validation.
        """
        from package_skill import package_skill

        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: bad-skill\ndescription: fine\nunknown-key: should-fail\n---\n\n# Bad\n", encoding="utf-8"
        )

        result = package_skill(skill_dir)
        assert result is None

    def test_invalid_allowed_tools_blocks_packaging(self, tmp_path: Path) -> None:
        from package_skill import package_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "bad-tools-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace("description:", "allowed-tools: Read,Grep\ndescription:"), encoding="utf-8"
        )

        assert package_skill(skill_dir) is None

    def test_nonexistent_path_returns_none(self, tmp_path: Path) -> None:
        """package_skill returns None for a path that does not exist.

        Tests: Input guard for missing skill directories.
        How: Pass a nonexistent path; assert None is returned.
        Why: A missing directory is the most common user error; must be caught early.
        """
        from package_skill import package_skill

        result = package_skill(tmp_path / "does-not-exist")
        assert result is None

    def test_default_output_dir_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When output_dir is omitted, .skill file is placed in cwd.

        Tests: Default output-directory logic in package_skill().
        How: chdir to tmp_path, package a skill without output_dir, assert file in cwd.
        Why: Verifies the cwd fallback path works; a regression would confuse users.
        """
        from package_skill import package_skill

        skill_dir = _make_minimal_valid_skill(tmp_path / "source", "cwd-skill")
        monkeypatch.chdir(tmp_path)

        result = package_skill(skill_dir)  # no output_dir
        assert result is not None
        assert result.parent == tmp_path

    def test_scaffolder_output_can_be_packaged(self, tmp_path: Path) -> None:
        """Skill directory produced by init_skill() can be packaged by package_skill().

        Tests: End-to-end handoff from scaffolder to packager.
        How: Call init_skill() to create a scaffold, then call package_skill() on the
             result, verify the archive is created and contains SKILL.md.
        Why: A regression where init_skill emits frontmatter that quick_validate rejects
             (e.g. wrong template quoting, missing required field) would leave every
             packager test green while packaging all scaffolded skills silently fails.
        """
        from init_skill import init_skill
        from package_skill import package_skill

        scaffold_root = tmp_path / "skills"
        skill_dir = init_skill("scaffold-pack-skill", str(scaffold_root))
        assert skill_dir is not None, "init_skill must succeed before packaging"

        out_dir = tmp_path / "dist"
        result = package_skill(skill_dir, out_dir)

        assert result is not None, "package_skill must succeed on a freshly-scaffolded skill"
        assert result.suffix == ".skill"
        assert result.exists()

        with zipfile.ZipFile(result) as zf:
            names = zf.namelist()
        assert "scaffold-pack-skill/SKILL.md" in names, f"SKILL.md not found at expected path in archive. Got: {names}"


# ===========================================================================
# quick_validate.py — validator broken-fixture corpus
# ===========================================================================


class TestQuickValidateBrokenFixtures:
    """validate_skill() rejects intentionally-broken SKILL.md fixtures.

    Tests: Each validation rule fires for its target defect class.
    How: Write a minimal SKILL.md with one specific defect per test; assert False + message.
    Why: A silent pass on a broken fixture means a validation rule regression goes
         undetected until downstream users notice missing error codes.
    """

    def test_valid_skill_passes(self, tmp_path: Path) -> None:
        """A well-formed skill directory passes validation.

        Tests: Baseline — validate_skill returns True for a correct skill.
        """
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "valid-skill")

        valid, message = validate_skill(skill_dir)
        assert valid, f"Expected valid skill to pass: {message}"

    def test_missing_skill_md_fails(self, tmp_path: Path) -> None:
        """Directory without SKILL.md is rejected.

        Tests: Guard for skill directories that never had SKILL.md created.
        """
        from quick_validate import validate_skill

        skill_dir = tmp_path / "no-skill-md"
        skill_dir.mkdir()

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "SKILL.md" in message

    def test_no_frontmatter_block_fails(self, tmp_path: Path) -> None:
        """SKILL.md without a YAML frontmatter block is rejected.

        Tests: Frontmatter-presence guard.
        """
        from quick_validate import validate_skill

        skill_dir = tmp_path / "no-frontmatter"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Just a heading\n\nNo frontmatter here.\n", encoding="utf-8")

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "frontmatter" in message.lower()

    def test_unexpected_frontmatter_key_fails(self, tmp_path: Path) -> None:
        """Frontmatter with an unrecognised key is rejected.

        Tests: Allowed-keys allowlist check.
        """
        from quick_validate import validate_skill

        skill_dir = tmp_path / "bad-key"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: bad-key\ndescription: fine\nrogue-key: not-allowed\n---\n\n# Bad\n", encoding="utf-8"
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "rogue-key" in message

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("argument-hint", "'[topic]'"),
            ("arguments", "topic"),
            ("disable-model-invocation", "true"),
            ("user-invocable", "true"),
            ("disallowed-tools", "Write"),
            ("model", "sonnet"),
            ("effort", "high"),
            ("context", "fork"),
            ("agent", "Explore"),
            ("background", "false"),
            ("hooks", "{}"),
            ("paths", "[]"),
            ("shell", "bash"),
            ("when_to_use", "tests"),
        ],
    )
    def test_claude_only_key_fails_portable_validation(self, tmp_path: Path, key: str, value: str) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "portable-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace("description:", f"{key}: {value}\ndescription:"), encoding="utf-8"
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert key in message

    @pytest.mark.parametrize("missing", ["name", "description"])
    def test_required_portable_field_fails(self, tmp_path: Path, missing: str) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "required-fields")
        skill_md = skill_dir / "SKILL.md"
        lines = [line for line in skill_md.read_text().splitlines() if not line.startswith(f"{missing}:")]
        skill_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert missing in message.lower()

    def test_name_must_match_parent_directory(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "directory-name")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("name: directory-name", "name: other-name"))

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "must match parent directory" in message

    def test_uppercase_name_fails(self, tmp_path: Path) -> None:
        """Name containing uppercase letters is rejected.

        Tests: Hyphen-case name validation rule.
        """
        from quick_validate import validate_skill

        skill_dir = tmp_path / "uppercase-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: MyUpperCaseSkill\ndescription: description here\n---\n\n# Skill\n", encoding="utf-8"
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert any(kw in message for kw in ("hyphen-case", "MyUpperCaseSkill"))

    def test_lowercase_unicode_name_passes(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "données-分析")

        valid, message = validate_skill(skill_dir)
        assert valid, message

    def test_unicode_uppercase_name_fails(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "НАВЫК")

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "lowercase" in message

    def test_non_alphanumeric_unicode_name_fails(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "技能_分析")

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "Unicode alphanumeric characters and hyphens" in message

    def test_nfkc_normalized_name_matches_directory(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "café")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("name: café", "name: cafe\u0301"), encoding="utf-8")

        valid, message = validate_skill(skill_dir)
        assert valid, message

    def test_name_length_is_checked_after_nfkc_normalization(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        expanded_name = "ﬀ" * 33
        skill_dir = _make_minimal_valid_skill(tmp_path, expanded_name)

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "66 characters" in message

    @pytest.mark.parametrize("compatibility", ["", "   "])
    def test_empty_compatibility_fails(self, tmp_path: Path, compatibility: str) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "compatibility-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace("description:", f"compatibility: '{compatibility}'\ndescription:"),
            encoding="utf-8",
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "compatibility" in message.lower()

    @pytest.mark.parametrize("key", ["license", "compatibility", "metadata", "allowed-tools"])
    def test_explicit_null_optional_field_fails(self, tmp_path: Path, key: str) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "null-field-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("description:", f"{key}: null\ndescription:"))

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert key in message

    @pytest.mark.parametrize("description", ["", "   "])
    def test_whitespace_only_description_fails(self, tmp_path: Path, description: str) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "empty-description-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace(
                "description: A test skill for smoke testing", f"description: '{description}'"
            ),
            encoding="utf-8",
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "description is required" in message.lower()

    def test_description_length_is_checked_before_trimming(self, tmp_path: Path) -> None:
        from quick_validate import MAX_DESCRIPTION_LENGTH, validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "long-description-skill")
        skill_md = skill_dir / "SKILL.md"
        description = f" {'a' * MAX_DESCRIPTION_LENGTH} "
        skill_md.write_text(
            skill_md.read_text().replace(
                "description: A test skill for smoke testing", f"description: '{description}'"
            ),
            encoding="utf-8",
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert f"{len(description)} characters" in message

    def test_space_delimited_allowed_tools_passes(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "tool-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace("description:", "allowed-tools: Bash(git:*) Read\ndescription:"),
            encoding="utf-8",
        )

        valid, message = validate_skill(skill_dir)
        assert valid, message

    def test_yaml_list_allowed_tools_fails_portable_validation(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "tool-list-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace("description:", "allowed-tools: [Read, Grep]\ndescription:"), encoding="utf-8"
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "allowed-tools must be a string" in message

    @pytest.mark.parametrize(
        "allowed_tools", ["", "Read,Grep", "Read, Grep", "Read\tGrep", "Read  Grep", " Read Grep", "Read Grep "]
    )
    def test_non_space_delimited_allowed_tools_fails(self, tmp_path: Path, allowed_tools: str) -> None:
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, "tool-format-skill")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            skill_md.read_text().replace("description:", f"allowed-tools: '{allowed_tools}'\ndescription:"),
            encoding="utf-8",
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "space-separated tool tokens" in message

    def test_description_with_angle_brackets_passes(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = tmp_path / "angle-bracket-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: angle-bracket-skill\ndescription: Uses <html> tags\n---\n\n# Skill\n", encoding="utf-8"
        )

        valid, message = validate_skill(skill_dir)
        assert valid, message

    def test_yaml_block_scalar_description_passes(self, tmp_path: Path) -> None:
        from quick_validate import validate_skill

        skill_dir = tmp_path / "multiline-indicator"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: multiline-indicator\ndescription: >-\n  A portable multiline description\n---\n\n# Skill\n",
            encoding="utf-8",
        )

        valid, message = validate_skill(skill_dir)
        assert valid, message

    def test_name_too_long_fails(self, tmp_path: Path) -> None:
        """Name exceeding the maximum length is rejected.

        Tests: Length cap in _validate_name().
        """
        from quick_validate import MAX_NAME_LENGTH, validate_skill

        long_name = "a" * (MAX_NAME_LENGTH + 1)
        skill_dir = tmp_path / "long-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {long_name}\ndescription: fine\n---\n\n# Skill\n", encoding="utf-8"
        )

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "long" in message.lower() or str(MAX_NAME_LENGTH) in message or "maximum" in message.lower()

    @pytest.mark.parametrize("name", ["-bad-start", "bad-end-", "bad--middle"])
    def test_name_with_invalid_hyphen_placement_fails(self, tmp_path: Path, name: str) -> None:
        """Names with leading, trailing, or consecutive hyphens are rejected.

        Tests: Hyphen-placement guards in _validate_name().
        """
        from quick_validate import validate_skill

        skill_dir = _make_minimal_valid_skill(tmp_path, name)

        valid, message = validate_skill(skill_dir)
        assert not valid
        assert "hyphen" in message.lower()


def test_custom_skill_paths_do_not_mask_default_skills(tmp_path: Path) -> None:
    from check_agent_auto_discovery import _check_one_plugin

    plugin_dir = tmp_path / "plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / "skills" / "default-skill").mkdir(parents=True)
    (plugin_dir / "skills" / "default-skill" / "SKILL.md").write_text("# Default\n")
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    plugin_json.write_text('{"skills": ["./custom-skills"]}\n')

    assert _check_one_plugin(plugin_json) == []


def test_single_agent_path_string_is_accepted(tmp_path: Path) -> None:
    from check_agent_auto_discovery import _check_one_plugin

    plugin_dir = tmp_path / "plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    plugin_json.write_text('{"agents": "./custom/reviewer.md"}\n')

    assert _check_one_plugin(plugin_json) == []


def test_explicit_agent_paths_cannot_mask_nested_default_agents(tmp_path: Path) -> None:
    from check_agent_auto_discovery import _check_one_plugin

    plugin_dir = tmp_path / "plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / "agents" / "review").mkdir(parents=True)
    (plugin_dir / "agents" / "reviewer.md").write_text("# Reviewer\n")
    (plugin_dir / "agents" / "review" / "security.md").write_text("# Security\n")
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    plugin_json.write_text('{"agents": ["./agents/reviewer.md"]}\n')

    violations = _check_one_plugin(plugin_json)

    assert len(violations) == 1
    assert "./agents/review/security.md" in violations[0]


@pytest.mark.parametrize("entry", [1, None, {"path": "./agents/reviewer.md"}])
def test_agent_path_array_rejects_non_string_entries(tmp_path: Path, entry: object) -> None:
    import json

    from check_agent_auto_discovery import _check_one_plugin

    plugin_dir = tmp_path / "plugin"
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    plugin_json.write_text(json.dumps({"agents": ["./agents/reviewer.md", entry]}))

    violations = _check_one_plugin(plugin_json)

    assert len(violations) == 1
    assert "entries must be strings" in violations[0]
