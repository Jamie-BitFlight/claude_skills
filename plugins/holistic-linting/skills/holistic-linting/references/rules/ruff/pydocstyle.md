# D: pydocstyle Rules

**Source**: Official Ruff Documentation **Purpose**: Docstring Convention Enforcement

This rule family provides comprehensive checks for Python code quality and style conformance.

## Overview

This documentation file contains references for all rules in the D: pydocstyle Rules family. For detailed information about specific rules, refer to the [Official Ruff Documentation](https://docs.astral.sh/ruff/rules/).

## Configuration

### Enable This Rule Family

```toml
[tool.ruff.lint]
extend-select = ["pydocstyle"]
```

### Common Patterns

Most rules in this family can be configured through options in the `[tool.ruff.lint]` section. Check the official documentation for family-specific configuration options.

## Quick Reference

For a complete list of all rules in this family, use the Ruff CLI:

```bash
ruff rule --all | grep "^# pydocstyle"
```

## Integration with Other Rules

This rule family works best when combined with:

- Core rules: E, F, W
- Code quality: B, S
- Import management: I
- Naming conventions: N

## Further Documentation

For detailed rule descriptions, examples, and configuration options, visit the [Official Ruff Documentation](https://docs.astral.sh/ruff/rules/).

---

**Last Updated**: 2025-11-04 **Note**: This is a reference index. Detailed rule documentation is available in the official Ruff documentation.
