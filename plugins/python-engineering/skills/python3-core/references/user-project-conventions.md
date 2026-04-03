---
title: User Project Conventions
date: 2025-11-17
source: Extracted from user's production projects
projects_analyzed:
- pre-commit-pep723-linter-wrapper (PyPI/GitHub)
- python_picotool (GitLab)
- usb_powertools (GitLab)
- picod (GitLab)
- i2c_analyzer (GitLab)
---

# User Project Conventions

Conventions extracted from actual production projects. The model MUST follow these patterns when creating new Python projects.

## Asset Files Available

The following template files are available in the skill's `assets/` directory for use in new projects:

| File                      | Purpose                                              | Usage                                                 |
| ------------------------- | ---------------------------------------------------- | ----------------------------------------------------- |
| `version.py`              | Dual-mode version management (hatch-vcs + fallback)  | Copy to `packages/{package_name}/version.py`          |
| `hatch_build.py`          | Build hook for binary/asset handling                 | Copy to `scripts/hatch_build.py`                      |
| `.markdownlint.json`      | Markdown linting configuration (most rules disabled) | Copy to project root                                  |
| `.pre-commit-config.yaml` | Standard pre-commit hooks configuration              | Copy to project root, run `uv run pre-commit install` |
| `.editorconfig`           | Editor formatting settings                           | Copy to project root                                  |

The model MUST copy these files when creating new Python projects to ensure consistency with established conventions documented below.

## 1. Version Management

### Pattern: Dual-mode version.py (STANDARD - 5/5 projects)

**Location**: `packages/{package_name}/version.py`

**Pattern**: Hatch-VCS with importlib.metadata fallback

**Implementation**:

```python
"""Compute the version number and store it in the `__version__` variable.

Based on <https://github.com/maresb/hatch-vcs-footgun-example>.
"""

# /// script
# List dependencies for linting only
# dependencies = [
#   "hatchling>=1.14.0",
# ]
# ///
import os


def _get_hatch_version() -> str | None:
    """Compute the most up-to-date version number in a development environment.

    Returns `None` if Hatchling is not installed, e.g. in a production environment.

    For more details, see <https://github.com/maresb/hatch-vcs-footgun-example/>.
    """
    try:
        from hatchling.metadata.core import ProjectMetadata
        from hatchling.plugin.manager import PluginManager
        from hatchling.utils.fs import locate_file
    except ImportError:
        # Hatchling is not installed, so probably we are not in
        # a development environment.
        return None

    pyproject_toml = locate_file(__file__, "pyproject.toml")
    if pyproject_toml is None:
        raise RuntimeError("pyproject.toml not found although hatchling is installed")
    root = os.path.dirname(pyproject_toml)
    metadata = ProjectMetadata(root=root, plugin_manager=PluginManager())
    # Version can be either statically set in pyproject.toml or computed dynamically:
    return str(metadata.core.version or metadata.hatch.version.cached)


def _get_importlib_metadata_version() -> str:
    """Compute the version number using importlib.metadata.

    This is the official Pythonic way to get the version number of an installed
    package. However, it is only updated when a package is installed. Thus, if a
    package is installed in editable mode, and a different version is checked out,
    then the version number will not be updated.
    """
    from importlib.metadata import version

    __version__ = version(__package__ or __name__)
    return __version__


__version__ = _get_hatch_version() or _get_importlib_metadata_version()
```

**pyproject.toml Configuration** (STANDARD - 5/5 projects):

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"
```

\***\*init**.py Export Pattern\*\* (STANDARD - 5/5 projects):

```python
from .version import __version__

__all__ = ["__version__"]  # Plus other exports
```

## 2. Package Structure

### Pattern: src-layout with packages/ directory (STANDARD - 5/5 projects)

**Directory Structure**:

<eg>
project_root/
├── packages/
│   └── {package_name}/
│       ├── __init__.py        # Exports public API + __version__
│       ├── version.py         # Version management
│       ├── {modules}.py
│       └── tests/             # Co-located tests
├── scripts/
│   └── hatch_build.py         # Custom build hook (if needed)
├── pyproject.toml
└── README.md
</eg>

**pyproject.toml Package Mapping** (STANDARD - 5/5 projects):

```toml
[tool.hatch.build.targets.wheel]
packages = ["packages/{package_name}"]

[tool.hatch.build.targets.wheel.sources]
"packages/{package_name}" = "{package_name}"
```

### Pattern: **init**.py exports with **all** (STANDARD - 5/5 projects)

The model must export public API + `__version__` in `__init__.py` with explicit `__all__` list.

**Minimal Example** (usb_powertools):

```python
"""Package docstring."""

from .version import __version__

__all__ = ["__version__"]
```

**Full API Example** (pep723_loader):

```python
"""Package docstring."""

from .pep723_checker import Pep723Checker
from .version import __version__

__all__ = ["Pep723Checker", "__version__"]
```

**Evidence**: All 5 projects use this pattern consistently.

## 3. Build Configuration

### Pattern: Custom hatch_build.py Hook (STANDARD - 3/5 projects with binaries)

**Location**: `scripts/hatch_build.py`

**Purpose**: Execute binary build scripts (`build-binaries.sh` or `build-binaries.py`) before packaging.

**Standard Implementation** (usb_powertools, picod, i2c_analyzer identical):

```python
"""Custom hatchling build hook for binary compilation.

This hook runs before the build process to compile platform-specific binaries
if build scripts are present in the project.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class BinaryBuildHook(BuildHookInterface[BuilderConfig]):
    """Build hook that runs binary compilation scripts before packaging.

    This hook checks for the following scripts in order:
    1. scripts/build-binaries.sh
    2. scripts/build-binaries.py

    If either script exists, it is executed before the build process.
    If neither exists, the hook silently continues without error.
    """

    PLUGIN_NAME = "binary-build"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Run binary build scripts if they exist."""
        shell_script = Path(self.root) / "scripts" / "build-binaries.sh"
        if shell_script.exists() and shell_script.is_file():
            self._run_shell_script(shell_script)
            return

        python_script = Path(self.root) / "scripts" / "build-binaries.py"
        if python_script.exists() and python_script.is_file():
            self._run_python_script(python_script)
            return

        self.app.display_info("No binary build scripts found, skipping binary compilation")

    def _run_shell_script(self, script_path: Path) -> None:
        """Execute a shell script for binary building."""
        self.app.display_info(f"Running binary build script: {script_path}")

        if not (bash := shutil.which("bash")):
            raise RuntimeError("bash not found - cannot execute shell script")

        try:
            result = subprocess.run([bash, str(script_path)], cwd=self.root, capture_output=True, text=True, check=True)
            if result.stdout:
                self.app.display_info(result.stdout)
            if result.stderr:
                self.app.display_warning(result.stderr)
        except subprocess.CalledProcessError as e:
            self.app.display_error(f"Binary build script failed with exit code {e.returncode}")
            if e.stdout:
                self.app.display_info(f"stdout: {e.stdout}")
            if e.stderr:
                self.app.display_error(f"stderr: {e.stderr}")
            raise

    def _run_python_script(self, script_path: Path) -> None:
        """Execute a Python script for binary building.

        Executes the script directly using its shebang, which honors PEP 723
        inline metadata for dependency management via uv.
        """
        self.app.display_info(f"Running binary build script: {script_path}")

        try:
            result = subprocess.run([script_path, "--clean"], cwd=self.root, capture_output=True, text=True, check=True)
            if result.stdout:
                self.app.display_info(result.stdout)
            if result.stderr:
                self.app.display_warning(result.stderr)
        except subprocess.CalledProcessError as e:
            self.app.display_error(f"Binary build script failed with exit code {e.returncode}")
            if e.stdout:
                self.app.display_info(f"stdout: {e.stdout}")
            if e.stderr:
                self.app.display_error(f"stderr: {e.stderr}")
            raise
```

**pyproject.toml Configuration**:

```toml
[tool.hatch.build.targets.sdist.hooks.custom]
path = "scripts/hatch_build.py"

[tool.hatch.build]
artifacts = ["builds/*/binary_name"]  # If binaries included
```

## 4. Pre-commit Configuration

### Standard Hook Set (STANDARD - 5/5 projects)

**File**: `.pre-commit-config.yaml`

**Core Hooks** (appear in all projects):

```yaml
repos:
  - repo: https://github.com/mxr/sync-pre-commit-deps
    rev: v0.0.3
    hooks:
      - id: sync-pre-commit-deps

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
        exclude: \.lock$
      - id: end-of-file-fixer
        exclude: \.lock$
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=10000"] # 10MB limit
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-symlinks
      - id: mixed-line-ending
        args: ["--fix=lf"]
      - id: check-executables-have-shebangs
      - id: check-shebang-scripts-are-executable

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.3+
    hooks:
      - id: ruff
        name: Lint Python with ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
        name: Format Python with ruff

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        name: Format YAML, JSON, and Markdown files
        types_or: [yaml, json, markdown]
        exclude: \.lock$

  - repo: https://github.com/pecigonzalo/pre-commit-shfmt
    rev: v2.2.0
    hooks:
      - id: shell-fmt-go
        args: ["--apply-ignore", -w, -i, "4", -ci]

  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.11.0.1
    hooks:
      - id: shellcheck

default_language_version:
  python: python3

exclude: |
  (?x)^(
    \.git/|
    \.venv/|
    __pycache__/|
    \.mypy_cache/|
    \.cache/|
    \.pytest_cache/|
    \.lock$|
    typings/
  )
```

### Pattern: pep723-loader for Type Checking (STANDARD - 3/5 projects)

Projects using `pep723-loader` wrapper for mypy/basedpyright:

```yaml
- repo: local
  hooks:
    - id: mypy
      name: mypy
      entry: uv run -q --no-sync --with pep723-loader --with mypy pep723-loader mypy
      language: system
      types: [python]
      pass_filenames: true

    - id: pyright
      name: basedpyright
      entry: uv run -q --no-sync --with pep723-loader --with basedpyright pep723-loader basedpyright
      language: system
      types: [python]
      pass_filenames: true
      require_serial: true
```

### Pattern: Markdown Linting (STANDARD - 4/5 projects)

```yaml
- repo: https://github.com/DavidAnson/markdownlint-cli2
  rev: v0.18.1
  hooks:
    - id: markdownlint-cli2
      language_version: "latest"
      args: ["--fix"]
```

**Evidence**: pre-commit-pep723-linter-wrapper, usb_powertools, picod all use this pattern.

## 5. Ruff Configuration

### Standard Configuration (STANDARD - 5/5 projects)

**pyproject.toml Section**:

```toml
[tool.ruff]
target-version = "py311"
fix = true
unsafe-fixes = true
src = ["packages", "scripts", "tests", "typings", ".gitlab", ".github"]

[tool.ruff.format]
docstring-code-format = true
quote-style = "double"
line-ending = "lf"
skip-magic-trailing-comma = true
preview = true

[tool.ruff.lint]
preview = true
extend-select = [
    "A",     # see: https://docs.astral.sh/ruff/rules/#flake8-builtins-a
    "ANN",   # see: https://docs.astral.sh/ruff/rules/#flake8-annotations-ann
    "ASYNC", # see: https://docs.astral.sh/ruff/rules/#flake8-async-async
    "B",     # see: https://docs.astral.sh/ruff/rules/#flake8-bugbear-b
    "BLE",   # see: https://docs.astral.sh/ruff/rules/#flake8-blind-except-ble
    "C4",    # see: https://docs.astral.sh/ruff/rules/#flake8-comprehensions-c4
    "C90",   # see: https://docs.astral.sh/ruff/rules/#mccabe-c90
    "D",     # see: https://docs.astral.sh/ruff/rules/#pydocstyle-d
    "DOC",   # see: https://docs.astral.sh/ruff/rules/#pydoclint-doc
    "E",     # see: https://docs.astral.sh/ruff/rules/#error-e
    "EXE",   # see: https://docs.astral.sh/ruff/rules/#flake8-executable-exe
    "F",     # see: https://docs.astral.sh/ruff/rules/#pyflakes-f
    "FA",    # see: https://docs.astral.sh/ruff/rules/#flake8-annotations-fa
    "FAST",  # see: https://docs.astral.sh/ruff/rules/#fastapi-fast
    "FLY",   # see: https://docs.astral.sh/ruff/rules/#flynt-fly
    "FURB",  # see: https://docs.astral.sh/ruff/rules/#refurb-furb
    "G201",  # see: https://docs.astral.sh/ruff/rules/logging-exc-info/
    "G202",  # see: https://docs.astral.sh/ruff/rules/logging-redundant-exc-info/
    "I",     # see: https://docs.astral.sh/ruff/rules/#isort-i
    "N",     # see: https://docs.astral.sh/ruff/rules/#flake8-quotes-n
    "PERF",  # see: https://docs.astral.sh/ruff/rules/#perflint-perf
    "PGH",   # see: https://docs.astral.sh/ruff/rules/#pygrep-hooks-pgh
    "PIE",   # see: https://docs.astral.sh/ruff/rules/#flake8-pie-pie
    "PL",    # see: https://docs.astral.sh/ruff/rules/#pyflakes-f
    "PT",    # see: https://docs.astral.sh/ruff/rules/#flake8-pytest-style-pt
    "PTH",   # see: https://docs.astral.sh/ruff/rules/#flake8-use-pathlib-pth
    "PYI",   # see: https://docs.astral.sh/ruff/rules/#flake8-pyi-pyi
    "Q",     # see: https://docs.astral.sh/ruff/rules/#flake8-quotes-q
    "RET",   # see: https://docs.astral.sh/ruff/rules/#flake8-return-ret
    "RSE",   # see: https://docs.astral.sh/ruff/rules/#flake8-raise-rse
    "RUF",   # see: https://docs.astral.sh/ruff/rules/#ruff-ruf
    "S",     # see: https://docs.astral.sh/ruff/rules/#flake8-bandit-s
    "SIM",   # see: https://docs.astral.sh/ruff/rules/#flake8-simplify-sim
    "SLF",   # see: https://docs.astral.sh/ruff/rules/#flake8-self-slf
    "SLOT",  # see: https://docs.astral.sh/ruff/rules/#flake8-slots-slot
    "T10",   # see: https://docs.astral.sh/ruff/rules/#flake8-debugger-t10
    "T20",   # see: https://docs.astral.sh/ruff/rules/#flake8-typing-t20
    "TC",    # see: https://docs.astral.sh/ruff/rules/#flake8-type-checking-tc
    "TRY",   # see: https://docs.astral.sh/ruff/rules/#tryceratops-try
    "UP",    # see: https://docs.astral.sh/ruff/rules/#pyupgrade-up
    "W",     # see: https://docs.astral.sh/ruff/rules/#warning-w
    "YTT",   # see: https://docs.astral.sh/ruff/rules/#flake8-2020-ytt
]
ignore = [
    "DOC501", # Raised exception {id} missing from docstring
    "DOC502", # Raised exception is not explicitly raised
    "E501",   # Line too long ({width} > {limit})
    "EXE003", # Shebang should contain python, pytest, or uv run (doesn't handle global arguments)
    "S404",   # subprocess possibly insecure - still need to use subprocess though
    "S603",   # subprocess without shell=True
    "TRY003", # Long error messages are fine
]
unfixable = ["F401"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S", "D", "E501"]
"typings/**" = ["N", "ANN", "A"]
".gitlab/scripts/**" = [
    "T201", # print() statements are intentional for CI output visibility
]

[tool.ruff.lint.pycodestyle]
max-line-length = 120

[tool.ruff.lint.isort]
combine-as-imports = true
split-on-trailing-comma = false
force-single-line = false
force-wrap-aliases = false

[tool.ruff.lint.flake8-quotes]
docstring-quotes = "double"

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.mccabe]
max-complexity = 12
```

**Evidence**: Standard configuration used across all projects.

## 6. Mypy Configuration

### Standard Configuration (STANDARD - 5/5 projects)

```toml
[tool.mypy]
python_version = "3.11"
strict = true
extra_checks = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
ignore_missing_imports = true
show_error_codes = true
pretty = true
disable_error_code = ["call-arg", "misc"]
mypy_path = ["packages", "scripts", "."]

[[tool.mypy.overrides]]
module = ["test.*", "tests.*"]
disable_error_code = ["attr-defined", "call-arg", "var-annotated"]
```

## 7. Basedpyright Configuration

### Standard Configuration (STANDARD - 5/5 projects)

```toml
[tool.basedpyright]
pythonVersion = "3.11"
typeCheckingMode = "basic"
reportMissingImports = false
reportMissingTypeStubs = false
reportUnnecessaryTypeIgnoreComment = "error"
reportPrivateImportUsage = false
include = ["packages", "scripts"]
extraPaths = ["packages", "scripts", "tests"]
ignore = ["**/typings", "**/tests"]
venvPath = "."
venv = ".venv"
```

**Evidence**: All 5 projects use this configuration.

## 8. Pytest Configuration

### Standard Configuration (STANDARD - 5/5 projects)

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=packages/{package_name}",
    "--cov-report=term-missing",
    "-v",
]
testpaths = ["packages/{package_name}/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
pythonpath = [".", "packages/"]
markers = [
    "hardware: tests that require USB hardware",
    "slow: tests that take significant time to run",
    "integration: integration tests",
]

[tool.coverage.run]
omit = ["*/tests/*"]

[tool.coverage.report]
show_missing = true
fail_under = 70
```

**Evidence**: All projects follow this pattern with minor marker variations.

## 9. Formatting Configuration Files

### .markdownlint.json (STANDARD - 5/5 projects)

**All projects use identical configuration**:

```json
{
  "MD003": false,
  "MD007": { "indent": 2 },
  "MD001": false,
  "MD022": false,
  "MD024": false,
  "MD013": false,
  "MD036": false,
  "MD025": false,
  "MD031": false,
  "MD041": false,
  "MD029": false,
  "MD033": false,
  "MD046": false,
  "blanks-around-fences": false,
  "blanks-around-headings": false,
  "blanks-around-lists": false,
  "code-fence-style": false,
  "emphasis-style": false,
  "heading-start-left": false,
  "heading-style": false,
  "hr-style": false,
  "line-length": false,
  "list-indent": false,
  "list-marker-space": false,
  "no-blanks-blockquote": false,
  "no-hard-tabs": false,
  "no-missing-space-atx": false,
  "no-missing-space-closed-atx": false,
  "no-multiple-blanks": false,
  "no-multiple-space-atx": false,
  "no-multiple-space-blockquote": false,
  "no-multiple-space-closed-atx": false,
  "no-trailing-spaces": false,
  "ol-prefix": false,
  "strong-style": false,
  "ul-indent": false
}
```

**Evidence**: Identical across all 5 projects.

### .editorconfig (COMMON - 2/5 projects have it)

**Standard Pattern** (python_picotool, picod):

```ini
# EditorConfig: https://editorconfig.org/

root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
max_line_length = 120

[*.md]
indent_style = space
indent_size = 4
trim_trailing_whitespace = false

[*.py]
indent_style = space
indent_size = 4

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[*.sh]
indent_style = space
indent_size = 4

[*.toml]
indent_style = space
indent_size = 2

[*.json]
indent_style = space
indent_size = 2

[COMMIT_EDITMSG]
max_line_length = 72
```

**Evidence**:

## 10. Semantic Release Configuration

### Standard Configuration (STANDARD - 5/5 projects)

```toml
[tool.semantic_release]
version_toml = []
major_on_zero = true
allow_zero_version = true
tag_format = "v{version}"
build_command = "uv build"

[tool.semantic_release.branches.main]
match = "(main|master)"
prerelease = false

[tool.semantic_release.commit_parser_options]
allowed_tags = [
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "style",
    "refactor",
    "test",
]
minor_tags = ["feat"]
patch_tags = ["fix", "perf", "refactor"]
```

**Evidence**: All 5 projects use this configuration identically.

## 11. Dependency Groups

### Standard dev Dependencies (STANDARD - 5/5 projects)

```toml
[dependency-groups]
dev = [
    "basedpyright>=1.21.1",
    "hatch-vcs>=0.5.0",
    "hatchling>=1.14.0",
    "mypy>=1.18.2",
    "pre-commit>=4.3.0",
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.9.4",
    "python-semantic-release>=10.4.1",
    "generate-changelog>=0.16.0",
]
```

**Common Pattern**: All projects include mypy, basedpyright, ruff, pytest, pre-commit, hatchling tools.

**Evidence**: All 5 projects have dev dependency groups with these core tools.

## 12. GitLab Project-Specific Patterns

### Pattern: Custom PyPI Index (STANDARD - 4/4 GitLab projects)

```toml
[tool.uv]
publish-url = "{{gitlab_instance_url}}/api/v4/projects/{{project_id}}/packages/pypi"

[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple"
default = true

[[tool.uv.index]]
name = "gitlab"
url = "{{gitlab_instance_url}}/api/v4/groups/{{group_id}}/-/packages/pypi/simple"
explicit = true
default = false
```

## 13. Project Metadata Standards

### Pattern: Author and Maintainer (STANDARD - 5/5 projects)

```toml
[project]
authors = [{ name = "{{author_name_from_git_config_user_name}}", email = "{{author_email_from_git_config_user_email}}" }]
maintainers = [{ name = "{{author_name_from_git_config_user_name}}", email = "{{author_email_from_git_config_user_email}}" }]
```

**Observation**: Email addresses differ between GitHub projects (personal email) and GitLab projects (corporate email).

### Pattern: Classifiers (STANDARD - 5/5 projects)

**Common classifiers across all projects**:

```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Operating System :: POSIX :: Linux" or "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
```

### Pattern: Keywords (STANDARD - 5/5 projects)

All projects include domain-specific keywords related to their purpose.

### Pattern: requires-python (STANDARD - 5/5 projects)

**Two variants**:

- GitHub: `>=3.10`
- GitLab: `>=3.11,<3.13`

## 14. CLI Entry Points

### Pattern: Typer-based CLI (STANDARD - 5/5 projects)

```toml
[project.scripts]
{package_name} = "{package_name}.cli:main" or "{package_name}.cli:app"

[project]
dependencies = [
    "typer>=0.21.2",
]
```

**Evidence**: All 5 projects use Typer for CLI implementation.

## Summary of Standard Patterns

**STANDARD** (5/5 projects):

- Dual-mode version.py with hatch-vcs
- packages/ directory structure
- **all** exports in **init**.py
- Ruff formatting with 120 char line length
- Mypy strict mode
- Basedpyright type checking
- Pre-commit hooks (sync-deps, ruff, prettier, shellcheck, shfmt)
- .markdownlint.json (identical config)
- Semantic release configuration
- Typer-based CLI
- pytest with coverage

**COMMON** (3-4/5 projects):

- pep723-loader for type checking in pre-commit
- Custom hatch_build.py hook
- .editorconfig
- GitLab custom PyPI index

The model must follow STANDARD patterns for all new Python projects. COMMON patterns should be used when applicable (e.g., hatch_build.py only if binaries needed).
