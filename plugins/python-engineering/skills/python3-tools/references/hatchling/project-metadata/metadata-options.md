---
category: project-metadata
topics: [metadata-options, configuration-flags, direct-references, ambiguous-features]
related: [metadata-hooks, direct-references, dependencies]
---

# Metadata Options & Configuration

Hatchling provides configuration options in the `[tool.hatch.metadata]` table to control metadata handling and validation behavior.

When Claude helps users configure metadata options, explain the `[tool.hatch.metadata]` table as the central point for metadata-related configuration flags. Key options like `allow-direct-references` and `allow-ambiguous-features` control how Hatchling processes metadata. Explain when to enable each option and the implications for build reproducibility and PyPI compatibility.

## Allow Direct References

By default, Hatchling disallows direct references (VCS URLs, local paths) in dependencies to ensure reproducible builds and PyPI compatibility. Enable when needed:

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    "package @ git+https://github.com/user/package.git",
    "local @ file://../local-package",
]

```

**When to Use:**

- Monorepo development with local packages
- Testing forked or patched versions
- Development-only scenarios
- Private package distributions

**Note:** Packages with direct references cannot be published to PyPI.

## Allow Ambiguous Features

By default, Hatchling normalizes optional dependency names per PEP 685 to prevent ambiguity. For backward compatibility with older tools, disable normalization:

```toml

[tool.hatch.metadata]
allow-ambiguous-features = true

[project.optional-dependencies]
My-Feature = ["package"]  # Not normalized to 'my-feature'
my_other_feature = ["package"]  # Not normalized

```

**Status:** This option is deprecated and will be removed after January 1, 2024.

## Complete Configuration

```toml

[tool.hatch.metadata]
allow-direct-references = true
allow-ambiguous-features = false

```

## Related Configuration

- `direct-references.md` - VCS and local dependencies
- `dependencies.md` - Dependency specification
- `dynamic-metadata.md` - Dynamic field handling
