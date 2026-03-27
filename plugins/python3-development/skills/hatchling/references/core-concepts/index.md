---
category: core-concepts
topics: [reference, index, hatchling, concepts, design-principles]
related: [pep-517-backend.md, minimal-philosophy.md, vcs-file-selection.md, build-hooks.md, version-management.md, wheel-vs-sdist.md, reproducible-builds.md, development-vs-distribution.md]
---

# Hatchling Core Concepts Reference Index

## Overview

When helping users understand Hatchling's design principles and architecture, reference this directory for comprehensive documentation on core concepts, design philosophies, and best practices. Each document is self-contained but cross-referenced to related topics for progressive discovery.

## Core Concept Documents

### 1. `pep-517-backend.md`

**Topics:** Standards compliance, build system abstraction, PEP specifications

**Key Points:**

- What PEP 517/518 mean and why they matter
- How Hatchling implements these standards
- Standards ecosystem and tool integration
- Why standards matter for reproducibility and compatibility

**When to read:** Understanding why Hatchling uses `[build-system]` in pyproject.toml, what "PEP 517 backend" means, compatibility with different package managers.

**Related:** VCS-Aware File Selection, Reproducible Builds

---

### 2. `minimal-philosophy.md`

**Topics:** Design philosophy, sensible defaults, progressive disclosure

**Key Points:**

- Why Hatchling emphasizes minimal configuration
- How sensible defaults work for 70% of projects
- When to add explicit configuration
- Comparison with Poetry, setuptools, and uv

**When to read:** Understanding why Hatchling requires less configuration than other tools, when you should add custom configuration, how defaults work.

**Related:** PEP 517/518 Backend, Build Hooks

---

### 3. `vcs-file-selection.md`

**Topics:** File selection, .gitignore respecting, glob patterns, reproducibility

**Key Points:**

- How VCS awareness makes reproducible builds default
- Git-style glob pattern syntax and examples
- Wheel vs sdist file selection differences
- Why patterns matter for reproducibility

**When to read:** Understanding how Hatchling includes/excludes files, why your .gitignore matters, configuring file selection for non-standard layouts.

**Related:** Reproducible Builds, Minimal Philosophy

---

### 4. `build-hooks.md`

**Topics:** Extensibility, custom build steps, hook interface, common patterns

**Key Points:**

- What build hooks are and when to use them
- BuildHookInterface and hook lifecycle
- Common patterns (generate version, compile C, copy data)
- Third-party hooks (Cython, CMake, Jupyter)
- Best practices and gotchas

**When to read:** Building C extensions, generating files during build, integrating with other tools, understanding hook execution.

**Related:** Development vs Distribution Builds, Minimal Philosophy

---

### 5. `version-management.md`

**Topics:** Single source of truth, version sources, PEP 440, semantic versioning

**Key Points:**

- File-based version (simplest, most common)
- VCS-based version (automatic, for frequent releases)
- Custom hooks for dynamic versioning
- Avoiding version duplication
- Version accessible at runtime

**When to read:** Deciding where to store version, choosing between manual vs automatic versioning, accessing version in code, setting up version for releases.

**Related:** Build Hooks, Development vs Distribution

---

### 6. `wheel-vs-sdist.md`

**Topics:** Distribution formats, installation performance, packaging strategy

**Key Points:**

- Wheel (pre-built, fast) vs sdist (source, flexible)
- When to use each format
- Why upload both to PyPI
- Platform-specific wheels for C extensions
- Installation workflows

**When to read:** Understanding difference between .whl and .tar.gz, deciding what to upload to PyPI, understanding why pip prefers wheels.

**Related:** Reproducible Builds, Development vs Distribution

---

### 7. `reproducible-builds.md`

**Topics:** Security, verification, integrity, deterministic builds

**Key Points:**

- Why reproducible builds matter (security, verification)
- How Hatchling enables reproducible builds
- Verifying reproducibility
- Common issues and solutions
- Best practices

**When to read:** Understanding reproducible builds, setting up verification in CI/CD, ensuring builds are deterministic.

**Related:** VCS-Aware File Selection, Wheel vs Sdist, Development vs Distribution

---

### 8. `development-vs-distribution.md`

**Topics:** Editable installs, PEP 660, workflows, build configurations

**Key Points:**

- Editable installs (pip install -e .) for development
- Distribution builds for end users
- How editable installs work
- Installation workflows (dev, user, release)
- Best practices

**When to read:** Understanding why `pip install -e .` is different from `pip install .`, how to set up for development, testing distributions before release.

**Related:** Build Hooks, Version Management, Wheel vs Sdist

---

## Topic Map

### By Use Case

**I'm starting a new project:**

1. `minimal-philosophy.md` - understand defaults
2. `pep-517-backend.md` - understand standards
3. `version-management.md` - choose version strategy

**I'm setting up development:**

1. `development-vs-distribution.md` - editable installs
2. `version-management.md` - version in code
3. `build-hooks.md` - if you need custom build steps

**I'm preparing a release:**

1. `wheel-vs-sdist.md` - what to build
2. `reproducible-builds.md` - ensure reproducibility
3. `version-management.md` - version strategy

**I have a non-standard layout:**

1. `minimal-philosophy.md` - understand when config needed
2. `vcs-file-selection.md` - file patterns
3. `build-hooks.md` - if hooks needed

**I'm building C extensions:**

1. `build-hooks.md` - understand hook patterns
2. `wheel-vs-sdist.md` - platform-specific wheels
3. `reproducible-builds.md` - reproducibility with compiled code

### By Concept

**Standards and Compliance:**

- `pep-517-backend.md`
- `wheel-vs-sdist.md`
- `reproducible-builds.md`

**Configuration:**

- `minimal-philosophy.md`
- `vcs-file-selection.md`
- `build-hooks.md`

**Versioning:**

- `version-management.md`

**Installation and Distribution:**

- `development-vs-distribution.md`
- `wheel-vs-sdist.md`

**Quality and Reproducibility:**

- `reproducible-builds.md`
- `vcs-file-selection.md`

## Key Cross-References

### Minimal Configuration Philosophy appears in context of

- All documents reference defaults and sensible choices

### VCS-Aware File Selection relates to

- Reproducible Builds (consistency)
- Wheel vs Sdist (different file selection per target)

### Build Hooks integrates with

- Version Management (generating version files)
- Development vs Distribution (different hooks for different contexts)

### Version Management influences

- Build Hooks (version generation)
- Development vs Distribution (accessing version at runtime)

### Reproducible Builds depends on

- VCS-Aware File Selection (consistent files)
- Minimal Configuration (no non-deterministic options)

### Development vs Distribution relates to

- Build Hooks (hooks run for both contexts)
- Wheel vs Sdist (different installation workflows)

## Reading Paths

### Beginner Path (Understanding Basics)

1. `minimal-philosophy.md` - why Hatchling is simple
2. `pep-517-backend.md` - standards compliance
3. `development-vs-distribution.md` - workflows
4. `version-management.md` - version handling

### Intermediate Path (Working with Hatchling)

1. `vcs-file-selection.md` - configuring file inclusion
2. `build-hooks.md` - customizing build process
3. `wheel-vs-sdist.md` - distribution formats
4. `reproducible-builds.md` - ensuring quality

### Advanced Path (Mastering Hatchling)

1. `build-hooks.md` - advanced customization
2. `reproducible-builds.md` - security and verification
3. `version-management.md` - complex scenarios
4. `pep-517-backend.md` - standards deep-dive

### Problem-Solving Path (By Challenge)

- "How do I include/exclude files?" → `vcs-file-selection.md`
- "How do I manage version?" → `version-management.md`
- "How do I build C extensions?" → `build-hooks.md`
- "What's the difference between .whl and .tar.gz?" → `wheel-vs-sdist.md`
- "How do I ensure reproducible builds?" → `reproducible-builds.md`
- "When should I configure Hatchling?" → `minimal-philosophy.md`
- "Why use `pip install -e .`?" → `development-vs-distribution.md`

## Quick Reference

### Common Configurations

**Standard project (no configuration needed):**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
```

**Version from source file:**

```toml
[tool.hatch.version]
path = "src/myproject/__init__.py"
```

**Custom file selection:**

```toml
[tool.hatch.build.targets.sdist]
include = ["/src", "/tests"]
exclude = ["*.pyc"]
```

**Custom build hook:**

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

**VCS-based versioning:**

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"
```

## Additional Resources

- [Official Hatch Documentation](https://hatch.pypa.io/)
- [Python Packaging Guide](https://packaging.python.org/)
- `pep-517-backend.md#references`
