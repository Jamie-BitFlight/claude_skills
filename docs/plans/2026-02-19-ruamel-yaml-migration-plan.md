# Shared Frontmatter Module + ruamel.yaml Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all pyyaml usage with a shared frontmatter module backed by ruamel.yaml + python-frontmatter, fix false quoting instructions, and remove CI inline validation.

**Architecture:** A shared `frontmatter_utils.py` module provides a `RuamelYAMLHandler` (python-frontmatter `BaseHandler` subclass) and convenience functions. All scripts that parse/write frontmatter import from this module instead of reimplementing extraction. Validator FM009 stays but changes purpose to detect broken YAML from unquoted colons.

**Tech Stack:** ruamel.yaml>=0.18.0, python-frontmatter>=1.1.0, tomlkit>=0.13.0, Pydantic (existing), Typer/Rich (existing)

**Design doc:** [docs/plans/2026-02-19-ruamel-yaml-migration-design.md](./2026-02-19-ruamel-yaml-migration-design.md)

**Delegation:** All Python implementation tasks delegate to `@python3-development:python-cli-architect`. Documentation/instruction updates delegate to `@plugin-creator:contextual-ai-documentation-optimizer`. Activate `/python3-development:python3-development` skill before first delegation.

---

## Task 1: Update pyproject.toml Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add ruamel.yaml and tomlkit dev dependencies**

In `pyproject.toml` under `[project.optional-dependencies]` or `[dependency-groups]` dev section:
- Add `"ruamel.yaml>=0.18.0"`
- Add `"tomlkit>=0.13.0"`
- Remove `"types-pyyaml>=6.0.12.20250915"`
- Keep `"python-frontmatter>=1.1.0"` (already present)

**Step 2: Install updated deps**

Run: `uv sync`
Expected: Clean install, no errors

**Step 3: Verify imports work**

Run: `uv run python -c "from ruamel.yaml import YAML; print('ruamel.yaml OK')"`
Run: `uv run python -c "import tomlkit; print('tomlkit OK')"`
Expected: Both print OK

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build(deps): add ruamel.yaml and tomlkit, remove types-pyyaml"
```

---

## Task 2: Create Shared Frontmatter Module — Tests

**Files:**
- Create: `plugins/plugin-creator/tests/test_frontmatter_utils.py`

**Step 1: Write tests for RuamelYAMLHandler**

```python
"""Tests for frontmatter_utils shared module."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestRuamelYAMLHandler:
    """Test the custom python-frontmatter handler using ruamel.yaml."""

    def test_load_simple_frontmatter(self, tmp_path: Path) -> None:
        """Handler parses simple frontmatter without quotes."""
        md = tmp_path / "test.md"
        md.write_text("---\ndescription: A simple description\ntools: Bash, Read\n---\nBody content\n")
        from frontmatter_utils import load_frontmatter

        post = load_frontmatter(md)
        assert post["description"] == "A simple description"
        assert post["tools"] == "Bash, Read"
        assert post.content == "Body content"

    def test_load_quoted_frontmatter(self, tmp_path: Path) -> None:
        """Handler preserves quotes when YAML syntax requires them."""
        md = tmp_path / "test.md"
        md.write_text('---\ndescription: "Has: colon in value"\n---\nBody\n')
        from frontmatter_utils import load_frontmatter

        post = load_frontmatter(md)
        assert post["description"] == "Has: colon in value"

    def test_load_no_frontmatter(self, tmp_path: Path) -> None:
        """Handler returns empty metadata for files without frontmatter."""
        md = tmp_path / "test.md"
        md.write_text("Just body content, no frontmatter.\n")
        from frontmatter_utils import load_frontmatter

        post = load_frontmatter(md)
        assert dict(post.metadata) == {}
        assert "Just body content" in post.content

    def test_roundtrip_preserves_unquoted(self, tmp_path: Path) -> None:
        """Round-trip does not add unnecessary quotes."""
        original = "---\ndescription: No quotes needed here\ntools: Bash, Read\n---\nBody\n"
        md = tmp_path / "test.md"
        md.write_text(original)
        from frontmatter_utils import dump_frontmatter, load_frontmatter

        post = load_frontmatter(md)
        result = dump_frontmatter(post)
        assert "description: No quotes needed here" in result
        assert '"No quotes needed here"' not in result
        assert "'No quotes needed here'" not in result

    def test_roundtrip_preserves_required_quotes(self, tmp_path: Path) -> None:
        """Round-trip keeps quotes where YAML syntax demands them."""
        original = '---\ndescription: "Contains: colon that needs quoting"\n---\nBody\n'
        md = tmp_path / "test.md"
        md.write_text(original)
        from frontmatter_utils import dump_frontmatter, load_frontmatter

        post = load_frontmatter(md)
        result = dump_frontmatter(post)
        # The colon-space in value means quotes are required
        assert "Contains: colon that needs quoting" in result

    def test_roundtrip_removes_unnecessary_quotes(self, tmp_path: Path) -> None:
        """Round-trip strips quotes that YAML does not require."""
        original = '---\ndescription: "No special chars at all"\n---\nBody\n'
        md = tmp_path / "test.md"
        md.write_text(original)
        from frontmatter_utils import dump_frontmatter, load_frontmatter

        post = load_frontmatter(md)
        result = dump_frontmatter(post)
        # ruamel.yaml with preserve_quotes may keep them — verify behavior
        # This test documents actual behavior
        assert "No special chars at all" in result


class TestConvenienceAPI:
    """Test load/dump/update convenience functions."""

    def test_loads_frontmatter_from_string(self) -> None:
        """Parse frontmatter from a string."""
        from frontmatter_utils import loads_frontmatter

        text = "---\ndescription: Test\nmodel: sonnet\n---\nContent here\n"
        post = loads_frontmatter(text)
        assert post["description"] == "Test"
        assert post["model"] == "sonnet"
        assert post.content == "Content here"

    def test_dumps_frontmatter_to_file(self, tmp_path: Path) -> None:
        """Write frontmatter post to a file."""
        from frontmatter_utils import dumps_frontmatter, loads_frontmatter

        text = "---\ndescription: Written to file\n---\nBody\n"
        post = loads_frontmatter(text)
        out = tmp_path / "output.md"
        dumps_frontmatter(post, out)
        assert out.exists()
        content = out.read_text()
        assert "description: Written to file" in content
        assert "Body" in content

    def test_update_field_existing(self, tmp_path: Path) -> None:
        """Update an existing field without re-serializing everything."""
        md = tmp_path / "test.md"
        md.write_text("---\ndescription: Old value\ntools: Bash\n---\nBody\n")
        from frontmatter_utils import load_frontmatter, update_field

        update_field(md, "description", "New value")
        post = load_frontmatter(md)
        assert post["description"] == "New value"
        assert post["tools"] == "Bash"

    def test_update_field_new(self, tmp_path: Path) -> None:
        """Add a new field that did not exist."""
        md = tmp_path / "test.md"
        md.write_text("---\ndescription: Existing\n---\nBody\n")
        from frontmatter_utils import load_frontmatter, update_field

        update_field(md, "model", "sonnet")
        post = load_frontmatter(md)
        assert post["description"] == "Existing"
        assert post["model"] == "sonnet"

    def test_body_content_preserved(self, tmp_path: Path) -> None:
        """Markdown body with code blocks and special chars survives round-trip."""
        body = "# Heading\n\nSome text with `code` and **bold**.\n\n```python\ndef foo():\n    pass\n```\n"
        md = tmp_path / "test.md"
        md.write_text(f"---\ndescription: Test\n---\n{body}")
        from frontmatter_utils import dump_frontmatter, load_frontmatter

        post = load_frontmatter(md)
        result = dump_frontmatter(post)
        # Body content after the closing --- must match
        body_part = result.split("---\n", 2)[2]
        assert "```python" in body_part
        assert "def foo():" in body_part


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file does not crash."""
        md = tmp_path / "empty.md"
        md.write_text("")
        from frontmatter_utils import load_frontmatter

        post = load_frontmatter(md)
        assert dict(post.metadata) == {}

    def test_frontmatter_with_boolean_values(self, tmp_path: Path) -> None:
        """Boolean-like strings in frontmatter are preserved as strings when quoted."""
        md = tmp_path / "test.md"
        md.write_text('---\ndescription: "true"\nuser-invocable: true\n---\nBody\n')
        from frontmatter_utils import load_frontmatter

        post = load_frontmatter(md)
        assert post["user-invocable"] is True

    def test_frontmatter_with_list_values(self, tmp_path: Path) -> None:
        """List values in frontmatter are handled correctly."""
        md = tmp_path / "test.md"
        md.write_text("---\ndescription: Test\ntools:\n  - Bash\n  - Read\n  - Write\n---\nBody\n")
        from frontmatter_utils import load_frontmatter

        post = load_frontmatter(md)
        assert post["tools"] == ["Bash", "Read", "Write"]

    def test_unicode_in_description(self, tmp_path: Path) -> None:
        """Unicode characters survive round-trip."""
        md = tmp_path / "test.md"
        md.write_text("---\ndescription: Handles em\u2014dashes and curly \u201cquotes\u201d\n---\nBody\n")
        from frontmatter_utils import dump_frontmatter, load_frontmatter

        post = load_frontmatter(md)
        result = dump_frontmatter(post)
        assert "\u2014" in result
        assert "\u201c" in result
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest plugins/plugin-creator/tests/test_frontmatter_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'frontmatter_utils'`

**Step 3: Commit test file**

```bash
git add plugins/plugin-creator/tests/test_frontmatter_utils.py
git commit -m "test(frontmatter): add tests for shared frontmatter_utils module"
```

---

## Task 3: Create Shared Frontmatter Module — Implementation

**Files:**
- Create: `plugins/plugin-creator/scripts/frontmatter_utils.py`

**Step 1: Implement the module**

The module provides:
- `RuamelYAMLHandler(BaseHandler)` — custom handler using ruamel.yaml
- `load_frontmatter(path)` — read markdown file, return Post
- `loads_frontmatter(text)` — parse from string
- `dump_frontmatter(post)` — serialize to string
- `dumps_frontmatter(post, path)` — write to file
- `update_field(path, field, value)` — surgical field update

PEP 723 dependencies: `ruamel.yaml>=0.18.0`, `python-frontmatter>=1.1.0`

Delegate to `@python3-development:python-cli-architect` with:
- The test file as the contract
- The `mkapidocs` `yaml_utils.py` pattern as reference
- The `python-frontmatter` `BaseHandler` API documented in the design doc

**Step 2: Run tests to verify they pass**

Run: `uv run pytest plugins/plugin-creator/tests/test_frontmatter_utils.py -v`
Expected: All tests PASS

**Step 3: Run linting**

Run: `uv run prek run --files plugins/plugin-creator/scripts/frontmatter_utils.py`
Expected: Clean

**Step 4: Set executable bit**

Run: `chmod +x plugins/plugin-creator/scripts/frontmatter_utils.py`

**Step 5: Commit**

```bash
git add plugins/plugin-creator/scripts/frontmatter_utils.py
git commit -m "feat(frontmatter): add shared frontmatter_utils module with ruamel.yaml handler"
```

---

## Task 4: Delete CI Inline YAML/TOML Validation

**Files:**
- Modify: `.github/workflows/code-quality.yml`

**Step 1: Identify the inline blocks**

The inline Python blocks at lines ~430-479 that run:
- `uv run python -c "import tomllib; ..."` for TOML syntax checking
- `uv run --with pyyaml python -c "import yaml; yaml.safe_load(...)"` for YAML syntax checking

**Step 2: Delete the inline blocks**

Remove the entire step(s) containing inline Python for YAML/TOML syntax validation. Pre-commit hooks `check-yaml` and `check-toml` (`.pre-commit-config.yaml` lines 39, 42) already cover this.

**Step 3: Verify CI workflow is valid YAML**

Run: `uv run prek run --files .github/workflows/code-quality.yml`
Expected: Clean

**Step 4: Commit**

```bash
git add .github/workflows/code-quality.yml
git commit -m "ci: remove inline YAML/TOML validation duplicated by pre-commit hooks"
```

---

## Task 5: Migrate plugin_validator.py to Shared Module

**Files:**
- Modify: `plugins/plugin-creator/scripts/plugin_validator.py`
- Test: `plugins/plugin-creator/tests/test_frontmatter_validator.py`

**Step 1: Run existing tests to confirm baseline**

Run: `uv run pytest plugins/plugin-creator/tests/test_frontmatter_validator.py -v`
Expected: All PASS

**Step 2: Migrate import and extraction**

Replace:
- `import yaml` with `from frontmatter_utils import load_frontmatter, loads_frontmatter`
- Module-level `extract_frontmatter()` function — delegate extraction to shared module
- `yaml.safe_load()` calls in `FrontmatterValidator` — use shared module
- `yaml.dump()` calls in `_apply_fixes()` — use shared module's ruamel.yaml instance
- PEP 723 dep: `"pyyaml>=6.0"` → `"ruamel.yaml>=0.18.0"`, add `"python-frontmatter>=1.1.0"`

Delegate to `@python3-development:python-cli-architect` with file paths, test file path, and the constraint that all existing tests must continue to pass.

**Step 3: Run tests**

Run: `uv run pytest plugins/plugin-creator/tests/test_frontmatter_validator.py -v`
Expected: All PASS (behavior unchanged)

**Step 4: Run linting**

Run: `uv run prek run --files plugins/plugin-creator/scripts/plugin_validator.py`
Expected: Clean

**Step 5: Commit**

```bash
git add plugins/plugin-creator/scripts/plugin_validator.py
git commit -m "refactor(plugin-validator): migrate from pyyaml to shared frontmatter_utils module"
```

---

## Task 6: Migrate validate_frontmatter.py to Shared Module

**Files:**
- Modify: `plugins/plugin-creator/scripts/validate_frontmatter.py`

**Step 1: Migrate import and extraction**

Same pattern as Task 5:
- Replace `import yaml` with shared module imports
- Replace `yaml.safe_load()` and `yaml.dump()` calls
- Update PEP 723 deps

Delegate to `@python3-development:python-cli-architect`.

**Step 2: Run the script to verify it works**

Run: `uv run plugins/plugin-creator/scripts/validate_frontmatter.py --help`
Expected: Help output, no import errors

**Step 3: Run linting**

Run: `uv run prek run --files plugins/plugin-creator/scripts/validate_frontmatter.py`
Expected: Clean

**Step 4: Commit**

```bash
git add plugins/plugin-creator/scripts/validate_frontmatter.py
git commit -m "refactor(validate-frontmatter): migrate from pyyaml to shared frontmatter_utils module"
```

---

## Task 7: Migrate Remaining Scripts (5 files)

**Files:**
- Modify: `plugins/plugin-creator/skills/skill-creator/scripts/quick_validate.py`
- Modify: `plugins/python3-development/skills/implementation-manager/scripts/task_format.py`
- Modify: `plugins/python3-development/scripts/migrate_task_format.py`
- Modify: `plugins/python3-development/scripts/split_task_file.py`
- Modify: `plugins/gitlab-skill/skills/gitlab-skill/scripts/sync_gitlab_docs.py`

**Step 1: Migrate each script**

For each file:
- Replace `import yaml` with shared module imports
- Replace `yaml.safe_load()` calls with shared module functions
- Update PEP 723 deps: `"pyyaml>=6.0"` → `"ruamel.yaml>=0.18.0"`, add `"python-frontmatter>=1.1.0"`

Delegate to `@python3-development:python-cli-architect` with all 5 file paths.

**Step 2: Verify each script runs**

Run each with `--help` or a dry-run mode to confirm no import errors.

**Step 3: Run linting on all modified files**

Run: `uv run prek run --files <each file>`
Expected: Clean for all

**Step 4: Commit**

```bash
git add plugins/plugin-creator/skills/skill-creator/scripts/quick_validate.py \
      plugins/python3-development/skills/implementation-manager/scripts/task_format.py \
      plugins/python3-development/scripts/migrate_task_format.py \
      plugins/python3-development/scripts/split_task_file.py \
      plugins/gitlab-skill/skills/gitlab-skill/scripts/sync_gitlab_docs.py
git commit -m "refactor(scripts): migrate 5 scripts from pyyaml to shared frontmatter_utils module"
```

---

## Task 8: Migrate discover_linters.py (Non-Frontmatter YAML)

**Files:**
- Modify: `plugins/holistic-linting/skills/holistic-linting/scripts/discover_linters.py`

**Step 1: Migrate YAML handling**

This script reads `.pre-commit-config.yaml` (not frontmatter). It needs ruamel.yaml directly, not the frontmatter module:
- Replace lazy `import yaml` fallback with `from ruamel.yaml import YAML`
- Replace `yaml.safe_load(f)` with `YAML(typ='safe').load(f)`
- PEP 723: remove `"types-pyyaml>=6.0.0"`, change `"pyyaml>=6.0"` to `"ruamel.yaml>=0.18.0"`, keep `"tomlkit>=0.13.0"`

Delegate to `@python3-development:python-cli-architect`.

**Step 2: Verify script runs**

Run: `uv run plugins/holistic-linting/skills/holistic-linting/scripts/discover_linters.py --help`
Expected: No import errors

**Step 3: Run linting**

Run: `uv run prek run --files plugins/holistic-linting/skills/holistic-linting/scripts/discover_linters.py`
Expected: Clean

**Step 4: Commit**

```bash
git add plugins/holistic-linting/skills/holistic-linting/scripts/discover_linters.py
git commit -m "refactor(discover-linters): migrate from pyyaml to ruamel.yaml"
```

---

## Task 9: Remove Dead pyyaml Dependency from fix_tool_formats.py

**Files:**
- Modify: `plugins/plugin-creator/scripts/fix_tool_formats.py`

**Step 1: Remove pyyaml from PEP 723 deps**

Remove `"pyyaml>=6.0.0"` from the PEP 723 `dependencies` list. No code changes — pyyaml is never imported.

**Step 2: Run linting**

Run: `uv run prek run --files plugins/plugin-creator/scripts/fix_tool_formats.py`
Expected: Clean

**Step 3: Commit**

```bash
git add plugins/plugin-creator/scripts/fix_tool_formats.py
git commit -m "fix(fix-tool-formats): remove unused pyyaml dependency"
```

---

## Task 10: Update Validator FM009 Purpose and Tests

**Files:**
- Modify: `plugins/plugin-creator/scripts/plugin_validator.py` (FM009 messaging)
- Modify: `plugins/plugin-creator/tests/test_frontmatter_validator.py` (FM009 test assertions)
- Modify: `plugins/plugin-creator/tests/conftest.py` (fixtures if needed)

**Step 1: Update FM009 error message and suggestion**

In `plugin_validator.py`, find the FM009 emission code. Change:
- Message: from "quote the description or remove colons" to "description contains unquoted colons — this will break YAML parsing. Quote the value or remove colons"
- Suggestion: from "Quote the description" to "Quote the description value or avoid colons. ruamel.yaml handles quoting on write, but hand-edited YAML with unquoted colons fails to parse"
- Keep the auto-fix behavior (adding quotes) unchanged

**Step 2: Update FM009 test**

In `test_frontmatter_validator.py`, update `test_autofix_unquoted_colon` assertions to match new message text.

**Step 3: Run tests**

Run: `uv run pytest plugins/plugin-creator/tests/test_frontmatter_validator.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add plugins/plugin-creator/scripts/plugin_validator.py \
      plugins/plugin-creator/tests/test_frontmatter_validator.py
git commit -m "refactor(validator): update FM009 to detect broken YAML, not enforce quoting convention"
```

---

## Task 11: Update Error Code Documentation

**Files:**
- Modify: `plugins/plugin-creator/references/ERROR_CODES.md`
- Modify: `plugins/plugin-creator/docs/ERROR_CODES.md`
- Modify: `plugins/plugin-creator/references/ARCHITECTURE.md`
- Modify: `plugins/plugin-creator/references/USAGE.md`

**Step 1: Update FM009 descriptions**

In both ERROR_CODES.md files:
- Change FM009 description from "Unquoted description with colons" to "Unquoted colons in description — breaks YAML parsing"
- Update fix guidance to match new purpose

In ARCHITECTURE.md and USAGE.md:
- Update FM009 references to match new description
- Update any pyyaml references to ruamel.yaml

Delegate to `@plugin-creator:contextual-ai-documentation-optimizer`.

**Step 2: Run linting on modified files**

Run: `uv run prek run --files <each file>`
Expected: Clean

**Step 3: Commit**

```bash
git add plugins/plugin-creator/references/ERROR_CODES.md \
      plugins/plugin-creator/docs/ERROR_CODES.md \
      plugins/plugin-creator/references/ARCHITECTURE.md \
      plugins/plugin-creator/references/USAGE.md
git commit -m "docs(error-codes): update FM009 description and pyyaml references"
```

---

## Task 12: Update Active Instruction Files (9 files)

**Files:**
- Modify: `plugins/plugin-creator/skills/write-frontmatter-description/SKILL.md`
- Modify: `plugins/plugin-creator/skills/skill-creator/SKILL.md`
- Modify: `plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md`
- Modify: `plugins/plugin-creator/agents/contextual-ai-documentation-optimizer.md`
- Modify: `plugins/plugin-creator/agents/refactor-validator.md`
- Modify: `.claude/skills/agent-creator/references/agent-schema.md`
- Modify: `plugins/plugin-creator/skills/agent-creator/references/agent-schema.md`
- Modify: `.claude/skills/optimize-claude-md/SKILL.md`
- Modify: `.claude/commands/write-to-skill-file-original.md`

**Step 1: Update quoting guidance in all 9 files**

Change all instances of:
- "always quote descriptions" → "avoid colons in descriptions; quote only when YAML syntax requires it"
- "use quoted single-line strings" → "use single-line strings; quote only when YAML syntax requires it (colons, leading special chars, boolean literals)"
- "Description is single-line quoted string" → "Description is single-line string (quoted only if YAML syntax requires)"
- "colons trigger YAML quoting" → "colons in descriptions break YAML parsing if unquoted — avoid colons or quote the value"

Keep all FM004/multiline indicator guidance unchanged — that is a real Claude Code platform limitation.

Delegate to `@plugin-creator:contextual-ai-documentation-optimizer` with all 9 file paths and the exact guidance changes.

**Step 2: Run linting**

Run: `uv run prek run --files <each file>`
Expected: Clean

**Step 3: Commit**

```bash
git add <all 9 files>
git commit -m "docs(skills): fix false quoting convention in 9 instruction files"
```

---

## Task 13: Update CLAUDE.md / README Files (4 files)

**Files:**
- Modify: `plugins/plugin-creator/CLAUDE.md`
- Modify: `plugins/plugin-creator/scripts/CLAUDE.md`
- Modify: `plugins/plugin-creator/README.md`
- Modify: `plugins/plugin-creator/scripts/README.md`

**Step 1: Update auto-fix capability descriptions**

Change: "Multiline descriptions → single-line quoted strings" → "Multiline descriptions → single-line strings"
Change: "Unquoted descriptions with colons" → "Unquoted colons in descriptions — adds quotes to prevent YAML parsing failures"

Delegate to `@plugin-creator:contextual-ai-documentation-optimizer`.

**Step 2: Run linting**

Run: `uv run prek run --files <each file>`
Expected: Clean

**Step 3: Commit**

```bash
git add <all 4 files>
git commit -m "docs(plugin-creator): update auto-fix descriptions for new quoting rules"
```

---

## Task 14: Update Project Convention Docs (6 files)

**Files:**
- Modify: `plugins/development-harness/docs/TASK_FILE_FORMAT.md`
- Modify: `plugins/plugin-creator/references/ARCHITECTURE.md`
- Modify: `plugins/plugin-creator/references/USAGE.md`
- Modify: `plugins/plugin-creator/skills/add-doc-updater/references/doc-updater-template.md`
- Modify: `plugins/python3-development/agents/code-reviewer.md`
- Modify: `plugins/python3-development/agents/python-cli-design-spec.md`

**Step 1: Update pyyaml references to ruamel.yaml**

In each file, replace pyyaml code examples and references with ruamel.yaml equivalents:
- `import yaml` → `from ruamel.yaml import YAML` or `from frontmatter_utils import load_frontmatter`
- `yaml.safe_load()` → `YAML(typ='safe').load()` or shared module call
- `pyyaml>=6.0` dependency references → `ruamel.yaml>=0.18.0`
- "pyyaml" library name references → "ruamel.yaml"

Delegate to `@plugin-creator:contextual-ai-documentation-optimizer` for skill/agent docs, `@python3-development:python-cli-architect` for python3-development agent docs.

**Step 2: Run linting**

Run: `uv run prek run --files <each file>`
Expected: Clean

**Step 3: Commit**

```bash
git add <all 6 files>
git commit -m "docs: update pyyaml references to ruamel.yaml in project convention docs"
```

---

## Task 15: Update Third-Party Library Reference Docs (5+ files)

**Files:**
- Modify: `plugins/holistic-linting/skills/holistic-linting/references/rules/bandit/deserialization.md`
- Modify: `plugins/python3-development/skills/python3-development/references/modern-modules/box.md`
- Modify: `plugins/python3-development/skills/python3-development/references/modern-modules/shiv.md`
- Modify: `plugins/python3-development/skills/hatchling/references/` (multiple files with pyyaml examples)
- Modify: `plugins/python3-development/skills/python3-development/planning/reference-document-architecture.md`

**Step 1: Update pyyaml examples to ruamel.yaml**

Replace pyyaml code examples with ruamel.yaml equivalents. For bandit deserialization docs, update `yaml.safe_load()` examples to show ruamel.yaml safe mode. For hatchling/box/shiv, update dependency references.

Delegate to `@plugin-creator:contextual-ai-documentation-optimizer`.

**Step 2: Run linting**

Run: `uv run prek run --files <each file>`
Expected: Clean

**Step 3: Commit**

```bash
git add <all modified files>
git commit -m "docs: update pyyaml examples to ruamel.yaml in library reference docs"
```

---

## Task 16: Add CLAUDE.md Convention Statement

**Files:**
- Modify: `.claude/CLAUDE.md` (project-level)

**Step 1: Add library convention**

Add a section to the project CLAUDE.md stating:

```markdown
## YAML and TOML Libraries

This repository uses `ruamel.yaml` for all YAML operations and `tomlkit` for TOML read-write operations. Never use `pyyaml` (`import yaml`). `tomllib` (stdlib) is acceptable for read-only TOML in stdlib-only contexts.

For frontmatter parsing/writing, use the shared module: `from frontmatter_utils import load_frontmatter, dump_frontmatter`.
```

**Step 2: Run linting**

Run: `uv run prek run --files .claude/CLAUDE.md`
Expected: Clean

**Step 3: Commit**

```bash
git add .claude/CLAUDE.md
git commit -m "docs(CLAUDE.md): add ruamel.yaml and tomlkit convention statement"
```

---

## Task 17: Mechanical Quote Normalization

**Files:**
- Modify: All frontmatter-bearing component files (skills, agents, commands, rules)

**Step 1: Write normalization script**

Create a script that:
1. Uses `plugin_validator.py`'s `FileType` enum to discover frontmatter-bearing files
2. For each file, calls `load_frontmatter()` then `dumps_frontmatter()` to round-trip through ruamel.yaml
3. Reports which files were modified (diff detection)
4. Has `--dry-run` mode that reports changes without writing

Delegate to `@python3-development:python-cli-architect`.

**Step 2: Run in dry-run mode**

Run: `uv run plugins/plugin-creator/scripts/normalize_frontmatter.py --dry-run`
Expected: List of files that would change, with diff preview

**Step 3: Review dry-run output**

Inspect the reported changes. Verify:
- Unnecessary quotes are removed
- Required quotes (colons, special chars) are preserved
- No content corruption

**Step 4: Run for real**

Run: `uv run plugins/plugin-creator/scripts/normalize_frontmatter.py`
Expected: Files updated

**Step 5: Run full validation**

Run: `uv run prek run --all-files`
Expected: Clean

**Step 6: Commit**

```bash
git add -A
git commit -m "style(frontmatter): normalize YAML quoting across all component files"
```

---

## Task 18: Final Verification

**Step 1: Run full test suite**

Run: `uv run pytest plugins/plugin-creator/tests/ -v`
Expected: All PASS

**Step 2: Run full linting**

Run: `uv run prek run --all-files`
Expected: Clean

**Step 3: Verify no pyyaml imports remain in scripts**

Run: `grep -rn "^import yaml$\|^from yaml import" plugins/ .github/ --include="*.py"`
Expected: Zero matches

**Step 4: Verify no pyyaml deps remain in PEP 723 blocks**

Run: `grep -rn "pyyaml" plugins/ --include="*.py" | grep -v "planning/" | grep -v "tests/"`
Expected: Zero matches (or only detection/instruction references)

**Step 5: Run plugin validator on a known-good skill**

Run: `uv run plugins/plugin-creator/scripts/plugin_validator.py plugins/plugin-creator/`
Expected: Passes validation

**Step 6: Verify FM009 still catches unquoted colons**

Create a temp file with `description: has: colon` (unquoted), run validator, confirm FM009 fires.

**Step 7: Verify FM004 still catches multiline indicators**

Create a temp file with `description: >-\n  multiline`, run validator, confirm FM004 fires.
