"""Unit tests for hook script discovery features in HookValidator.

Tests:
- _is_file_path_reference: file path vs shell command discrimination
- _find_plugin_root: .claude-plugin directory traversal
- _validate_command_script_references: HK004/HK005 for missing/non-executable scripts
- _validate_hook_script_references_in_hooks_dict: full hooks dict traversal
- FrontmatterValidator integration: hooks field in SKILL.md frontmatter
"""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest
from git import Repo

# Add parent directory to path to import plugin_validator
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from plugin_validator import FrontmatterValidator, HookValidator, YamlValue


class TestIsFilePathReference:
    """Test HookValidator._is_file_path_reference static method."""

    @pytest.mark.parametrize(
        "command", ["./script.sh", "../scripts/hook.py", "/usr/bin/hook", "${CLAUDE_PLUGIN_ROOT}/scripts/hook.sh"]
    )
    def test_file_paths_return_true(self, command: str) -> None:
        """Test that paths starting with ./, ../, /, or ${CLAUDE_PLUGIN_ROOT}/ return True.

        Tests: File path detection positive cases
        How: Call _is_file_path_reference with each path pattern
        Why: Verify all file path prefixes are recognized
        """
        assert HookValidator._is_file_path_reference(command) is True

    @pytest.mark.parametrize("command", ["echo hello", "python3 -m pytest", "npm run test", "git status"])
    def test_shell_commands_return_false(self, command: str) -> None:
        """Test that bare shell commands return False.

        Tests: Shell command detection negative cases
        How: Call _is_file_path_reference with each shell command
        Why: Verify bare commands are not treated as file paths
        """
        assert HookValidator._is_file_path_reference(command) is False

    def test_empty_string_returns_false(self) -> None:
        """Test that empty string returns False.

        Tests: Edge case for empty command
        How: Call _is_file_path_reference with empty string
        Why: Verify empty command is handled gracefully
        """
        assert HookValidator._is_file_path_reference("") is False


class TestFindPluginRoot:
    """Test HookValidator._find_plugin_root static method."""

    def test_directory_with_claude_plugin_parent(self, tmp_path: Path) -> None:
        """Test finding plugin root when .claude-plugin/ exists above.

        Tests: Plugin root discovery via .claude-plugin/ directory
        How: Create nested structure with .claude-plugin/ at top, search from deeper dir
        Why: Verify upward traversal finds plugin root correctly
        """
        plugin_root = tmp_path / "my-plugin"
        plugin_root.mkdir()
        (plugin_root / ".claude-plugin").mkdir()

        nested_dir = plugin_root / "hooks"
        nested_dir.mkdir()

        result = HookValidator._find_plugin_root(nested_dir)
        assert result == plugin_root.resolve()

    def test_directory_without_claude_plugin(self, tmp_path: Path) -> None:
        """Test fallback when no .claude-plugin/ directory exists.

        Tests: Fallback to base_dir when no plugin root found
        How: Create directory without .claude-plugin/ parent, search
        Why: Verify fallback returns original base_dir
        """
        plain_dir = tmp_path / "no-plugin"
        plain_dir.mkdir()

        result = HookValidator._find_plugin_root(plain_dir)
        assert result == plain_dir


class TestValidateCommandScriptReferences:
    """Test HookValidator._validate_command_script_references method."""

    def test_existing_executable_script(self, tmp_path: Path) -> None:
        """Test that an existing executable script produces no errors.

        Tests: Valid script reference produces no HK004/HK005
        How: Create executable file, reference it in hook entry, validate
        Why: Verify happy path with no issues
        """
        script = tmp_path / "hook.sh"
        script.write_text("#!/bin/bash\necho ok\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

        validator = HookValidator()
        errors: list = []
        entries: list[dict[str, YamlValue]] = [{"type": "command", "command": "./hook.sh"}]
        validator._validate_command_script_references(entries, tmp_path, errors)

        hk_codes = [e.code for e in errors]
        assert "HK004" not in hk_codes
        assert "HK005" not in hk_codes

    def test_missing_script_hk004(self, tmp_path: Path) -> None:
        """Test that a missing script file produces HK004 error.

        Tests: Non-existent script reference detection
        How: Reference a script that does not exist, validate
        Why: Verify HK004 is reported for missing files
        """
        validator = HookValidator()
        errors: list = []
        entries: list[dict[str, YamlValue]] = [{"type": "command", "command": "./nonexistent.sh"}]
        validator._validate_command_script_references(entries, tmp_path, errors)

        hk_codes = [e.code for e in errors]
        assert "HK004" in hk_codes

    def test_non_executable_script_hk005(self, tmp_path: Path) -> None:
        """Test that a script without execute bit in Git produces HK005 warning.

        Tests: Git-tracked execute bit detection (cross-platform)
        How: Create file in Git repo without execute bit (100644), validate
        Why: Ensures Windows and Linux get same validation; plugins that pass
             on Windows will pass on Linux
        """
        script = tmp_path / "hook.sh"
        script.write_text("#!/bin/bash\necho ok\n")
        repo = Repo.init(tmp_path)
        repo.index.add(["hook.sh"])
        repo.index.write()

        validator = HookValidator()
        errors: list = []
        entries: list[dict[str, YamlValue]] = [{"type": "command", "command": "./hook.sh"}]
        validator._validate_command_script_references(entries, tmp_path, errors)

        hk_codes = [e.code for e in errors]
        assert "HK005" in hk_codes

    def test_shell_command_ignored(self, tmp_path: Path) -> None:
        """Test that bare shell commands are not validated as file paths.

        Tests: Shell command bypass
        How: Pass a bare command like 'echo hello', validate
        Why: Verify non-file-path commands produce no HK004/HK005
        """
        validator = HookValidator()
        errors: list = []
        entries: list[dict[str, YamlValue]] = [{"type": "command", "command": "echo hello"}]
        validator._validate_command_script_references(entries, tmp_path, errors)

        assert len(errors) == 0

    def test_plugin_root_variable(self, tmp_path: Path) -> None:
        """Test ${CLAUDE_PLUGIN_ROOT} variable resolution.

        Tests: Variable substitution in script path
        How: Create plugin structure, reference script via variable, validate
        Why: Verify ${CLAUDE_PLUGIN_ROOT} resolves to detected plugin root
        """
        # Build plugin structure
        plugin_root = tmp_path / "my-plugin"
        plugin_root.mkdir()
        (plugin_root / ".claude-plugin").mkdir()
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir()

        script = scripts_dir / "hook.sh"
        script.write_text("#!/bin/bash\necho ok\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

        hooks_dir = plugin_root / "hooks"
        hooks_dir.mkdir()

        validator = HookValidator()
        errors: list = []
        entries: list[dict[str, YamlValue]] = [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/scripts/hook.sh"}]
        validator._validate_command_script_references(entries, hooks_dir, errors)

        hk_codes = [e.code for e in errors]
        assert "HK004" not in hk_codes
        assert "HK005" not in hk_codes


class TestHookScriptReferencesInHooksDict:
    """Test HookValidator._validate_hook_script_references_in_hooks_dict method."""

    def test_valid_hooks_dict_with_scripts(self, tmp_path: Path) -> None:
        """Test full hooks dict with valid script references.

        Tests: Complete hooks dict traversal with valid scripts
        How: Build hooks dict structure referencing existing executable scripts
        Why: Verify no issues when all scripts exist and are executable
        """
        script = tmp_path / "hook.sh"
        script.write_text("#!/bin/bash\necho ok\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

        hooks_dict: dict[str, YamlValue] = {"PreToolUse": [{"hooks": [{"type": "command", "command": "./hook.sh"}]}]}

        validator = HookValidator()
        errors: list = []
        validator.validate_hook_script_references_in_hooks_dict(hooks_dict, tmp_path, errors)

        hk_codes = [e.code for e in errors]
        assert "HK004" not in hk_codes
        assert "HK005" not in hk_codes

    def test_hooks_dict_with_missing_scripts(self, tmp_path: Path) -> None:
        """Test hooks dict with broken file references produces HK004.

        Tests: Missing script detection through hooks dict traversal
        How: Build hooks dict referencing non-existent script, validate
        Why: Verify HK004 is reported for missing scripts in full dict structure
        """
        hooks_dict: dict[str, YamlValue] = {
            "PostToolUse": [{"hooks": [{"type": "command", "command": "./missing-script.sh"}]}]
        }

        validator = HookValidator()
        errors: list = []
        validator.validate_hook_script_references_in_hooks_dict(hooks_dict, tmp_path, errors)

        hk_codes = [e.code for e in errors]
        assert "HK004" in hk_codes

    def test_non_command_type_ignored(self, tmp_path: Path) -> None:
        """Test that prompt-type hooks are not checked for file paths.

        Tests: Type filtering for script validation
        How: Build hooks dict with prompt type entry, validate
        Why: Verify only command-type hooks are checked for file paths
        """
        hooks_dict: dict[str, YamlValue] = {
            "PreToolUse": [{"hooks": [{"type": "prompt", "prompt": "Check tool usage"}]}]
        }

        validator = HookValidator()
        errors: list = []
        validator.validate_hook_script_references_in_hooks_dict(hooks_dict, tmp_path, errors)

        assert len(errors) == 0


class TestFrontmatterHooksIntegration:
    """Test hook script validation triggered from FrontmatterValidator.

    When SKILL.md frontmatter contains a ``hooks:`` field, the
    FrontmatterValidator delegates to HookValidator for script reference
    validation (HK004/HK005).
    """

    def test_frontmatter_hooks_with_valid_script(self, tmp_path: Path) -> None:
        """Test SKILL.md with hooks referencing an existing executable script.

        Tests: Integration between FrontmatterValidator and HookValidator
        How: Create SKILL.md with hooks frontmatter pointing to existing script
        Why: Verify no HK004/HK005 when hooks reference valid scripts
        """
        # Create the script that hooks will reference
        script = tmp_path / "check-tool.sh"
        script.write_text("#!/bin/bash\necho ok\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "description: Skill with hooks\n"
            "hooks:\n"
            "  PreToolUse:\n"
            "    - hooks:\n"
            "        - type: command\n"
            "          command: ./check-tool.sh\n"
            "---\n"
            "\n"
            "# Test Skill\n"
        )

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        hk_codes = [e.code for e in result.errors]
        assert "HK004" not in hk_codes
        assert "HK005" not in hk_codes

    def test_frontmatter_hooks_with_missing_script(self, tmp_path: Path) -> None:
        """Test SKILL.md with hooks referencing a non-existent script.

        Tests: HK004 surfaced through FrontmatterValidator
        How: Create SKILL.md with hooks pointing to non-existent script
        Why: Verify HK004 error is propagated from HookValidator to FrontmatterValidator result
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "description: Skill with broken hooks\n"
            "hooks:\n"
            "  PreToolUse:\n"
            "    - hooks:\n"
            "        - type: command\n"
            "          command: ./nonexistent-hook.sh\n"
            "---\n"
            "\n"
            "# Test Skill\n"
        )

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        hk_codes = [e.code for e in result.errors]
        assert "HK004" in hk_codes
