---
description: Guided workflow for adding new features to Python projects. Use when planning a new feature implementation, when adding functionality with proper test coverage, or when following TDD to build features incrementally.
argument-hint: <feature-description>
user-invocable: true
---

# Python Feature Addition Workflow

The model guides feature development through discovery, planning, implementation, and verification phases.

## Arguments

$ARGUMENTS

## Instructions

1. **Understand the feature request** from arguments
2. **Discover project context** (structure, patterns, existing code)
3. **Plan implementation** (files to create/modify, dependencies)
4. **Implement with tests** following TDD
5. **Verify quality** (linting, types, coverage)

---

## Phase 1: Discovery

### Gather Project Context

```text
CHECK:
- [ ] pyproject.toml exists and has project configuration
- [ ] src/ or packages/ directory structure
- [ ] tests/ directory with existing test patterns
- [ ] Linting configuration (ruff, mypy)
- [ ] Existing patterns for similar features
```

### Identify Integration Points

Determine where the feature fits:

- Which module/package owns this functionality?
- What existing classes/functions will interact with it?
- What new files need to be created?

---

## Phase 2: Planning

### Feature Specification

Create a clear specification:

```markdown
## Feature: [Name]

**Purpose**: [One sentence describing what this enables]

**User Story**: As a [user type], I want [capability] so that [benefit].

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Files to Create/Modify**:
- `src/module/new_feature.py` - Main implementation
- `tests/test_new_feature.py` - Test suite
- `src/module/__init__.py` - Export new functionality

**Dependencies**:
- Internal: [existing modules to import]
- External: [new packages if any]
```

### MoSCoW Prioritization

<moscow_framework>

Categorize all requirements using MoSCoW:

| Priority             | Meaning                        | Criteria                            |
| -------------------- | ------------------------------ | ----------------------------------- |
| **P0 (Must Have)**   | Non-negotiable for v1          | Feature is broken without this      |
| **P1 (Should Have)** | Important, committed follow-up | High value, but v1 works without it |
| **P2 (Could Have)**  | Desirable if time permits      | Nice-to-have enhancements           |
| **Won't Have**       | Explicitly deferred            | Out of scope for this release       |

**Discipline Check**: If everything is P0, nothing is P0. Re-evaluate.

**Example**:

```markdown
### Requirements by Priority

**P0 (Must Have)**:
- [ ] Parse CSV input with header detection
- [ ] Output formatted report to stdout
- [ ] Handle malformed rows with error message

**P1 (Should Have)**:
- [ ] Support custom delimiter (--delimiter)
- [ ] Progress indicator for large files

**P2 (Could Have)**:
- [ ] JSON output format option
- [ ] Column filtering

**Won't Have (This Release)**:
- Excel format support (separate feature)
- Database export (requires new dependency)
```

</moscow_framework>

### Acceptance Criteria Formats

<acceptance_criteria_patterns>

Use ONE of these formats for testable acceptance criteria:

**Format 1: Given/When/Then (BDD)**

```gherkin
Given [precondition]
When [user action]
Then [expected outcome]
```

**Example**:

```gherkin
Given a CSV file with 1000 rows
When the user runs `parse report.csv`
Then the output shows all rows within 2 seconds
And no memory warnings are logged
```

**Format 2: Checklist with Specifics**

```markdown
- [ ] Command `parse --help` shows usage with examples
- [ ] Empty file input returns exit code 1 with message "Empty file"
- [ ] Unicode characters in data are preserved in output
- [ ] Ctrl+C during processing exits cleanly (no stack trace)
```

**Anti-Patterns to Avoid**:

| Anti-Pattern               | Problem      | Better                                                       |
| -------------------------- | ------------ | ------------------------------------------------------------ |
| "Should be fast"           | Unmeasurable | "Completes in <2s for 10K rows"                              |
| "Handle errors gracefully" | Vague        | "Invalid input returns exit code 1 with descriptive message" |
| "User-friendly output"     | Subjective   | "Output uses Rich table formatting with headers"             |

</acceptance_criteria_patterns>

### Design Interface First

Define the public API before implementation:

```python
# Define function signatures and docstrings
def new_feature(
    input_data: InputType,
    *,
    option: str = "default",
) -> ResultType:
    """Process input data with new feature capability.

    Args:
        input_data: The data to process
        option: Configuration option

    Returns:
        Processed result

    Raises:
        ValidationError: If input_data is invalid
    """
    ...
```

---

## Phase 3: Test-Driven Implementation

### Write Tests First

```python
import pytest
from pytest_mock import MockerFixture

class TestNewFeature:
    """Tests for new_feature functionality."""

    def test_basic_operation(self) -> None:
        """Test basic feature operation with valid input."""
        # Arrange
        input_data = create_valid_input()

        # Act
        result = new_feature(input_data)

        # Assert
        assert result.status == "success"

    def test_handles_invalid_input(self) -> None:
        """Test feature raises error for invalid input."""
        with pytest.raises(ValidationError, match="Invalid input"):
            new_feature(invalid_input)

    def test_option_affects_behavior(self) -> None:
        """Test that option parameter changes processing."""
        result_default = new_feature(data, option="default")
        result_custom = new_feature(data, option="custom")

        assert result_default != result_custom
```

### Implement to Pass Tests

1. Run tests - they should fail (red)
2. Implement minimal code to pass (green)
3. Refactor for quality (refactor)
4. Repeat for each test case

### Implementation Checklist

```text
- [ ] All functions have complete type hints
- [ ] Docstrings follow Google style
- [ ] Error handling uses specific exceptions
- [ ] No hardcoded values (use constants or config)
- [ ] Follows existing project patterns
```

---

## Phase 4: Integration

### Update Module Exports

```python
# src/module/__init__.py
from .new_feature import new_feature, ResultType

__all__ = [
    "new_feature",
    "ResultType",
    # ... existing exports
]
```

### Add to CLI (if applicable)

```python
@app.command()
def feature_command(
    input_file: Annotated[Path, typer.Argument(help="Input file")],
) -> None:
    """Run new feature on input file."""
    result = new_feature(load_data(input_file))
    console.print(f"Result: {result}")
```

---

## Phase 5: Verification

### Run Quality Checks

```bash
# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type checking
uv run mypy src/ tests/

# Tests with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Coverage Requirements

- New feature code: 100% coverage
- Integration points: Covered by integration tests
- Overall project: Maintain or improve existing coverage

### Success Metrics

<success_metrics_framework>

Define measurable success criteria before implementation:

**Leading Indicators** (Observable in days-weeks):

| Metric          | Target        | How to Measure             |
| --------------- | ------------- | -------------------------- |
| Test pass rate  | 100%          | `pytest --tb=short`        |
| Type coverage   | 100%          | `mypy --strict`            |
| Code coverage   | ≥80% new code | `pytest --cov`             |
| Command startup | <500ms        | `time uv run <cmd> --help` |

**Lagging Indicators** (Observable in weeks-months):

| Metric          | Target                  | How to Measure         |
| --------------- | ----------------------- | ---------------------- |
| User adoption   | N users/week            | Usage logs or feedback |
| Error rate      | <1% of invocations      | Error logs             |
| Support tickets | Reduction from baseline | Issue tracker          |

**For CLI Features**:

```bash
# Performance baseline
hyperfine 'uv run <command> <args>' --warmup 3

# Memory usage
/usr/bin/time -v uv run <command> <args> 2>&1 | grep "Maximum resident"
```

**Evaluation Window**: Specify when metrics will be reviewed (e.g., "1 week post-merge", "after 100 invocations").

</success_metrics_framework>

### Documentation

Update relevant documentation:

- README.md if user-facing feature
- API docs if public interface
- CHANGELOG.md with feature description

---

## Example Workflow

**Request**: "Add CSV export functionality to the report module"

### Discovery

```text
Project structure:
- src/reports/generator.py - existing report generation
- src/reports/formats/ - existing format handlers
- tests/reports/ - existing report tests

Pattern: Format handlers inherit from BaseFormatter
```

### Planning

```markdown
## Feature: CSV Export

**Purpose**: Export reports in CSV format

**Files**:
- `src/reports/formats/csv_formatter.py` - CSV implementation
- `tests/reports/formats/test_csv_formatter.py` - Tests

**Interface**:
class CsvFormatter(BaseFormatter):
    def format(self, report: Report) -> str: ...
```

### Implementation

1. Write tests for CsvFormatter
2. Implement CsvFormatter class
3. Register in format factory
4. Add CLI option `--format csv`
5. Run verification checks

---

## Quality Standards

The model MUST ensure:

1. **Type Safety**: All code passes mypy --strict
2. **Linting**: Zero ruff errors or warnings
3. **Tests**: New code has 100% coverage
4. **Patterns**: Follows existing project conventions
5. **Documentation**: Docstrings on all public interfaces

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
