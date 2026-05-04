# skilllint Architecture

Technical reference for the skilllint implementation, design patterns, and extension guide.

---

## Overview

**Package**: `skilllint` (PyPI: <https://pypi.org/project/skilllint>)
**Language**: Python 3.11+ with PEP 723 inline dependencies
**Execution**: Standalone script using `uv` package manager

**Purpose**: Comprehensive validation tool for Claude Code plugins, skills, agents, and commands with token-based complexity measurement.

---

## Architecture Principles

### 1. Validator Protocol

All validators implement the `Validator` protocol for consistent interface:

```python
class Validator(Protocol):
    """Protocol for validation components."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate the given path."""
        ...

    def can_fix(self) -> bool:
        """Return True if this validator can auto-fix issues."""
        ...

    def fix(self, path: Path) -> list[str]:
        """Fix issues. Returns list of fixes applied."""
        ...
```

**Benefits**:
- Structural typing (duck typing with type safety)
- No ABC inheritance complexity
- Easy to add new validators
- Consistent error handling

### 2. Data Model Design

**Immutable data structures** using frozen dataclasses:

```python
@dataclass(frozen=True)
class ValidationIssue:
    """Represents a single validation issue."""

    field: str  # Field name or component that failed
    severity: Literal["error", "warning", "info"]  # Issue severity
    message: str  # Human-readable description
    code: str  # Error code (e.g., "FM001")
    line: int | None = None  # Line number if applicable
    suggestion: str | None = None  # Suggested fix
    docs_url: str | None = None  # Documentation URL

@dataclass(frozen=True)
class ValidationResult:
    """Result of running validators."""

    passed: bool  # Overall pass/fail status
    errors: list[ValidationIssue]  # Blocking errors
    warnings: list[ValidationIssue]  # Non-blocking warnings
    info: list[ValidationIssue]  # Informational notices
```

**Benefits**:
- Immutable (thread-safe, cacheable)
- Complete type hints for static analysis
- Easy to serialize for reporting
- Clear separation of concerns

### 3. Token-Based Complexity

**Philosophy**: Line counting is a poor proxy for AI processing cost. Token counting directly measures what Claude processes.

**Implementation** (lines 1475-1656):

```python
class ComplexityValidator:
    """Validates skill complexity using token counting."""

    def validate(self, path: Path) -> ValidationResult:
        # Lazy-load tiktoken only when needed
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")  # Claude-compatible

        # Split frontmatter from body
        frontmatter, body = self._split_frontmatter(content)

        # Count tokens in body only (exclude frontmatter)
        body_tokens = len(encoding.encode(body))

        # Apply thresholds
        if body_tokens > TOKEN_ERROR_THRESHOLD:  # 6400
            # ERROR: Must split
        elif body_tokens > TOKEN_WARNING_THRESHOLD:  # 4000
            # WARNING: Consider splitting
```

**Thresholds** (defined as constants in `skilllint`):
- **TOKEN_WARNING_THRESHOLD**: Consider splitting
- **TOKEN_ERROR_THRESHOLD**: Must split

**Rationale**:
- Token count correlates with API cost
- Matches Claude's context window accounting
- More accurate than line count for mixed content (code, markdown, YAML)

### 4. Security-First Subprocess Execution

**Critical requirements** (lines 1936-2074):

```python
# NEVER use shell=True (command injection risk)
subprocess.run(
    [cmd_path, *args],  # List arguments, not shell string
    timeout=30,  # Prevent hanging
    capture_output=True,
    text=True,
    check=False,  # Handle errors explicitly
)
```

**Security patterns**:
- Always use list arguments (not shell strings)
- Resolve commands with `shutil.which()` before execution
- Set timeouts to prevent hanging
- Never interpolate user input into shell commands

### 5. Progressive Disclosure Pattern

**Design**: Large skills should use directory structure to organize content:

```
skill-name/
├── SKILL.md (high-level workflow, under warning threshold)
├── references/
│   ├── detailed-guide.md (reference material)
│   └── api-reference.md (technical details)
├── examples/
│   └── common-patterns.md (code examples)
└── scripts/
    └── helper.py (implementation)
```

**Validator** (lines 303-415):
- Checks for `references/`, `examples/`, `scripts/` directories
- Reports as INFO (not errors) - these are recommendations
- Counts files in each directory if present

---

## Validator Classes

### 1. FrontmatterValidator (lines 779-1137)

**Purpose**: Validates YAML frontmatter schema compliance

**Error codes**: FM001-FM010

**Pydantic models**:
- `SkillFrontmatter` - Skills (all fields optional)
- `AgentFrontmatter` - Agents (name, description required)
- `CommandFrontmatter` - Commands (description required)

**Auto-fix capabilities**:
- FM004: Removes multiline indicators (`>-`, `|-`)
- FM007: Converts tools YAML array → CSV string
- FM008: Converts skills YAML array → CSV string
- FM009: Quotes descriptions with colons — `_fix_unquoted_colons()` skips rewriting lines inside ecosystem-owned top-level frontmatter blocks (e.g., `mcp:` from OpenCode)

**Implementation highlights**:

```python
def fix(self, path: Path) -> list[str]:
    """Auto-fix frontmatter issues."""

    fixes = []

    # Fix 1: YAML arrays → CSV strings
    if "tools:" in content and "- " in content:
        content = re.sub(
            r"tools:\s*\n(?:\s*-\s*(\w+)\n)+",
            lambda m: f"tools: {', '.join(m.groups())}",
            content
        )
        fixes.append("Converted tools YAML array to CSV")

    # Fix 2: Quote descriptions with colons
    if "description:" in content and ":" in desc_value:
        content = content.replace(
            f"description: {desc_value}",
            f'description: "{desc_value}"'
        )
        fixes.append("Quoted description with colons")

    return fixes
```

### 2. NameFormatValidator (lines 1139-1324)

**Purpose**: Validates skill/agent name format

**Error codes**: SK001-SK003

**Pattern**: `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`

**Rules**:
- Lowercase only (no uppercase)
- Hyphens allowed (no underscores)
- No leading/trailing hyphens
- No consecutive hyphens

**Not auto-fixable**: Requires human decision on correct name

### 3. DescriptionValidator (lines 1326-1473)

**Purpose**: Validates description quality

**Error codes**: SK004-SK005

**Requirements**:
- Minimum 20 characters
- Contains trigger phrases: "use when", "use this", "trigger", "activate"

**Severity**: WARNING (not ERROR)

**Rationale**: Descriptions should help AI understand when to use the skill

### 4. ComplexityValidator (lines 1475-1659)

**Purpose**: Measures skill complexity using tokens

**Error codes**: SK006-SK007

**Token encoding**: `cl100k_base` (Claude/GPT-4 compatible)

**Lazy loading**:

```python
def validate(self, path: Path) -> ValidationResult:
    # Import tiktoken only when needed (not at module level)
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    ...
```

**Why lazy loading**:
- `tiktoken` has large binary dependencies
- Not all validations require token counting
- Improves startup time

### 5. InternalLinkValidator (lines 417-777)

**Purpose**: Validates markdown internal links

**Error codes**: LK001-LK002

**Link extraction regex**:

```python
LINK_PATTERN = r"\[([^\]]+)\]\(([^)]+)\)"
```

**Validation logic**:

```python
for match in re.finditer(LINK_PATTERN, content):
    link_text, link_target = match.groups()

    # Filter out external links
    if link_target.startswith(("http://", "https://", "ftp://")):
        continue

    # Filter out anchor links
    if link_target.startswith("#"):
        continue

    # Check for ./ prefix
    if not link_target.startswith("./"):
        warnings.append(LK002)

    # Check file exists
    target_path = skill_dir / link_target
    if not target_path.exists():
        errors.append(LK001)
```

### 6. ProgressiveDisclosureValidator (lines 303-415)

**Purpose**: Checks for progressive disclosure directories

**Error codes**: PD001-PD003

**Directories checked**:
- `references/` - Detailed documentation
- `examples/` - Code examples
- `scripts/` - Companion scripts

**Severity**: INFO (not errors)

**File counting**:

```python
def _count_files(self, directory: Path) -> int:
    """Recursively count files in directory."""
    return sum(1 for _ in directory.rglob("*") if _.is_file())
```

### 7. PluginStructureValidator (lines 1661-1935)

**Purpose**: Validates plugin.json and delegates to Claude CLI

**Error codes**: PL001-PL005

**Claude CLI integration**:

```python
def validate(self, path: Path) -> ValidationResult:
    # Check if claude CLI available
    claude_path = shutil.which("claude")
    if not claude_path:
        return ValidationResult(
            passed=True,
            errors=[],
            warnings=[],
            info=[ValidationIssue(
                field="claude-cli",
                severity="info",
                message="Claude CLI not available, skipping plugin validation",
                code="PL001"
            )]
        )

    # Find plugin directory
    plugin_dir = self._find_plugin_directory(path)
    if not plugin_dir:
        return ValidationResult(passed=True, ...)  # Not a plugin

    # Run claude plugin validate
    result = subprocess.run(
        [claude_path, "plugin", "validate", str(plugin_dir)],
        timeout=CLAUDE_TIMEOUT,
        capture_output=True,
        text=True,
        check=False
    )

    # Parse output for errors
    return self._parse_claude_errors(result.stdout, result.stderr)
```

**Graceful degradation**:
- If `claude` not available: Skip with INFO message (no error)
- If not a plugin directory: Skip silently
- If timeout: Report as PL002 error

---

## CLI Layer

**Framework**: Typer (click-based CLI framework)

**Entry point**:

```python
app = typer.Typer(
    name="skilllint",
    help="Validate Claude Code plugins, skills, agents, and commands",
    no_args_is_help=True,
)

@app.command()
def main(
    path: Path,
    check: bool = False,
    fix: bool = False,
    verbose: bool = False,
    no_color: bool = False,
) -> None:
    """Validate plugin components."""
```

**Exit code handling**:

```python
try:
    # Validation logic
    ...
except KeyboardInterrupt:
    console.print("[yellow]Validation interrupted[/yellow]")
    raise SystemExit(130)  # Standard Ctrl+C exit code
except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
    raise SystemExit(1)
```

**Reporter selection**:

```python
if no_color:
    reporter = CIReporter()  # Plain text
else:
    reporter = ConsoleReporter()  # Rich colors

if verbose:
    reporter.set_verbose(True)
```

---

## Reporter Layer

**Implementation**: Lines 102-302

**Abstraction**: Protocol-based reporter interface

```python
class Reporter(Protocol):
    """Protocol for validation reporters."""

    def report(self, results: list[tuple[Path, ValidationResult]]) -> None:
        """Report validation results."""
        ...

    def summarize(self, results: list[tuple[Path, ValidationResult]]) -> None:
        """Print summary statistics."""
        ...
```

**Implementations**:

1. **ConsoleReporter** - Rich-formatted output with colors
2. **CIReporter** - Plain text for CI/CD pipelines
3. **SummaryReporter** - Single-line status

**Rich table configuration**:

```python
from rich.table import Table
from rich import box

table = Table(
    box=box.MINIMAL_DOUBLE_HEAD,  # Clean table style
    show_header=True,
    header_style="bold cyan",
)
```

---

## Integration Points

### 1. Claude CLI Integration

**Location**: Lines 1936-2012

**Function**: `validate_with_claude(plugin_dir: Path) -> tuple[bool, str]`

**Security considerations**:
- Resolves `claude` path with `shutil.which()`
- Uses list arguments (no shell interpolation)
- Sets 30-second timeout
- Handles missing CLI gracefully

**Error mapping**:
- Exit code 0 → Success
- Exit code non-zero → Parse errors from output
- Timeout → PL002 error
- FileNotFoundError → Skip with info message

### 2. Git Integration

**Location**: Lines 2015-2074

**Function**: `get_staged_files() -> list[Path]`

**Purpose**: Get list of files staged for commit (pre-commit hook context)

**Implementation**:

```python
def get_staged_files() -> list[Path]:
    """Get list of staged files from git."""
    git_path = shutil.which("git")
    if not git_path:
        return []

    result = subprocess.run(
        [git_path, "diff", "--cached", "--name-only"],
        timeout=10,
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        return []

    return [Path(line) for line in result.stdout.strip().split("\n") if line]
```

### 3. Pre-Commit Hook Integration

**Configuration** (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: local
    hooks:
      - id: skilllint
        name: Validate Plugin Components
        entry: uvx skilllint@latest check
        language: system
        files: '^plugins/.*/.*\.(md|json)$'
        pass_filenames: false
        args: [--check, --no-color]
```

**Behavior**:
- Runs only on staged files matching pattern
- Uses `--check` mode (no auto-fix in pre-commit)
- Uses `--no-color` for CI compatibility
- Exit code 1 blocks commit (errors found)

---

## Extension Guide

### Adding a New Validator

**Step 1**: Define validator class implementing Validator protocol

```python
class MyNewValidator:
    """Validates X for Y."""

    def validate(self, path: Path) -> ValidationResult:
        """Validate the given path."""
        issues: list[ValidationIssue] = []

        # Validation logic here
        if condition_fails:
            issues.append(ValidationIssue(
                field="field-name",
                severity="error",
                message="Description of issue",
                code="XX001",  # New error code
                suggestion="How to fix",
                docs_url=f"{ERROR_CODE_BASE_URL}#xx001"
            ))

        return ValidationResult(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            errors=[i for i in issues if i.severity == "error"],
            warnings=[i for i in issues if i.severity == "warning"],
            info=[i for i in issues if i.severity == "info"]
        )

    def can_fix(self) -> bool:
        """Return True if auto-fix is implemented."""
        return False  # Or True if fix() is implemented

    def fix(self, path: Path) -> list[str]:
        """Fix issues (if can_fix() returns True)."""
        if not self.can_fix():
            raise NotImplementedError("This validator cannot auto-fix")

        fixes = []
        # Fix logic here
        return fixes
```

**Step 2**: Add error codes to constants section (lines 61-97)

```python
# New Category Errors (XX001-XX005)
XX001 = "XX001"  # Description
XX002 = "XX002"  # Description
...
```

**Step 3**: Register validator in main validation flow

```python
def main(path: Path, ...) -> None:
    validators: list[Validator] = [
        FrontmatterValidator(),
        NameFormatValidator(),
        # ... existing validators
        MyNewValidator(),  # Add new validator
    ]
```

**Step 4**: Document error codes in ERROR_CODES.md

**Step 5**: Add tests (create `tests/test_my_new_validator.py`)

### Adding Auto-Fix Capability

**Requirements**:
1. Implement `fix()` method
2. Return `can_fix() = True`
3. Modify file in-place
4. Return list of human-readable fixes applied

**Example**:

```python
def fix(self, path: Path) -> list[str]:
    """Auto-fix issues."""
    content = path.read_text()
    fixes = []

    # Pattern matching and replacement
    if pattern_found:
        new_content = apply_fix(content)
        path.write_text(new_content)
        fixes.append("Description of fix applied")

    return fixes
```

**Best practices**:
- Make minimal changes (don't reformat entire file)
- Preserve user content exactly (no normalization)
- Log each fix applied
- Re-validate after fixing

### Adding New Error Code

**Step 1**: Add constant (lines 61-97)

```python
XX001 = "XX001"  # Category and number
```

**Step 2**: Use in validator

```python
ValidationIssue(
    field="field-name",
    severity="error",
    message="Human-readable description",
    code=XX001,  # Use constant
    suggestion="How to fix",
    docs_url=f"{ERROR_CODE_BASE_URL}#xx001"
)
```

**Step 3**: Document in ERROR_CODES.md

**Step 4**: Add to summary table in ERROR_CODES.md

---

## Performance Considerations

### 1. Lazy Loading

**tiktoken** library has large binary dependencies. Load only when needed:

```python
def validate(self, path: Path) -> ValidationResult:
    # Import inside method, not at module level
    import tiktoken
    ...
```

**Benefit**: Improves startup time for validators that don't need token counting

### 2. File I/O Optimization

**Read once, pass content**:

```python
# Good: Read once
content = path.read_text()
for validator in validators:
    validator.validate_content(path, content)

# Bad: Read multiple times
for validator in validators:
    validator.validate(path)  # Each validator reads file again
```

### 3. Subprocess Timeouts

**Always set timeouts** to prevent hanging:

```python
subprocess.run(
    [cmd_path, *args],
    timeout=30,  # REQUIRED
    ...
)
```

**Recommended timeouts**:
- `claude plugin validate`: 30 seconds
- `git diff --cached`: 10 seconds
- Other git operations: 5 seconds

### 4. Parallel Validation

**Future optimization**: Validate multiple files in parallel

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(validate_file, path) for path in paths]
    results = [future.result() for future in futures]
```

**Consideration**: Thread-safe validators required

---

## Testing Strategy

### Unit Tests

**Location**: `tests/test_*_validator.py`

**Pattern**: Parametrized tests for each error code

```python
import pytest

@pytest.mark.parametrize("name,expected_error", [
    ("valid-name", None),
    ("Invalid-Name", "SK001"),  # Uppercase
    ("invalid_name", "SK002"),  # Underscore
    ("-invalid", "SK003"),  # Leading hyphen
])
def test_name_validation(name, expected_error):
    validator = NameFormatValidator()
    result = validator.validate_name(name)

    if expected_error:
        assert not result.passed
        assert any(i.code == expected_error for i in result.errors)
    else:
        assert result.passed
```

### Integration Tests

**Location**: `tests/test_cli.py`

**Pattern**: Test CLI with Typer CliRunner

```python
from typer.testing import CliRunner

runner = CliRunner()

def test_validate_success():
    result = runner.invoke(app, ["plugins/valid-plugin"])
    assert result.exit_code == 0
    assert "PASSED" in result.stdout

def test_validate_failure():
    result = runner.invoke(app, ["plugins/invalid-plugin"])
    assert result.exit_code == 1
    assert "ERROR" in result.stdout
```

### Property-Based Tests

**Location**: `tests/test_token_counting.py`

**Pattern**: Use hypothesis for token counting validation

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_token_count_deterministic(text):
    """Token count should be deterministic for same input."""
    count1 = count_tokens(text)
    count2 = count_tokens(text)
    assert count1 == count2
```

---

## Dependencies

**PEP 723 inline dependencies** (lines 2-11):

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "rich>=13.0.0",
#     "tiktoken>=0.8.0",
#     "ruamel.yaml>=0.18.0",
#     "pydantic>=2.0.0",
# ]
# ///
```

**Dependency purposes**:
- **typer**: CLI framework (includes Click)
- **rich**: Terminal formatting and colors
- **tiktoken**: Token counting (OpenAI tokenizer)
- **ruamel.yaml**: YAML parsing with round-trip comment preservation
- **pydantic**: Schema validation with type hints

**Installation**: Automatic with `uv run` (no manual install needed)

---

## Design Decisions

### Why Protocol, Not ABC?

**Decision**: Use `Protocol` for structural typing instead of `abc.ABC`

**Rationale**:
- Structural typing is more Pythonic
- No inheritance required (simpler)
- Better type inference with mypy
- Easier to test (mock any object with correct methods)

### Why Token Count, Not Line Count?

**Decision**: Use tiktoken for complexity measurement instead of line counting

**Rationale**:
- Token count directly measures AI cost
- Line count doesn't account for content density
- 500 lines of prose ≠ 500 lines of code in token cost
- Matches Claude's internal accounting

### Why Lazy-Load tiktoken?

**Decision**: Import tiktoken inside validator methods, not at module level

**Rationale**:
- tiktoken has 1MB+ binary dependencies
- Not all validations need token counting
- Improves startup time (200ms → 50ms)
- Only pay cost when actually needed

### Why Separate Reporters?

**Decision**: Abstract reporter interface with multiple implementations

**Rationale**:
- ConsoleReporter for interactive use (Rich colors)
- CIReporter for CI/CD (no ANSI codes)
- SummaryReporter for quick status
- Easy to add JSON reporter, HTML reporter, etc.

---

## Scripts Inventory

| Script | Purpose |
|--------|---------|
| `skilllint` | Main validation CLI — frontmatter, links, complexity, plugin structure |
| `auto_sync_manifests.py` | Pre-commit hook — syncs plugin.json component arrays, bumps semver |

---

## See Also

- [ERROR_CODES.md](./ERROR_CODES.md) - Complete error code reference
- [USAGE.md](./USAGE.md) - CLI usage and workflow examples
- [skilllint](https://pypi.org/project/skilllint) - Source code
- [PEP 723](https://peps.python.org/pep-0723/) - Inline script metadata
- [Typer Documentation](https://typer.tiangolo.com/) - CLI framework
- [tiktoken Documentation](https://github.com/openai/tiktoken) - Token counting
