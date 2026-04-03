---
category: project-metadata
topics: [direct-references, VCS-dependencies, git-dependencies, local-dependencies, development-dependencies]
related: [dependencies, metadata-options]
---

# Direct References: VCS & Local Dependencies

Direct references allow dependencies to be specified using URLs pointing to version control systems or local filesystem paths, instead of relying on version specifiers. This is useful for development, testing unreleased versions, or depending on forked packages.

When Claude helps users configure direct references, first verify that `allow-direct-references = true` is set in `[tool.hatch.metadata]`. Explain that direct references cannot be published to PyPI and are intended for development and monorepo scenarios. Show Git, Mercurial, and local path examples with proper syntax.

## Enabling Direct References

By default, direct references are not allowed in project dependencies. To enable them, set `allow-direct-references` to `true` in the Hatchling metadata configuration:

```toml

[tool.hatch.metadata]
allow-direct-references = true

```

## VCS References

Dependencies from version control systems (Git, Mercurial, Subversion, Bazaar) can be specified with URL references.

### Git References

#### Current Branch

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    "package @ git+https://github.com/user/package.git",
]

```

#### Specific Tag

```toml

dependencies = [
    "package @ git+https://github.com/user/package.git@v1.0.0",
]

```

#### Specific Commit

```toml

dependencies = [
    "package @ git+https://github.com/user/package.git@abc123def456",
]

```

#### Specific Branch

```toml

dependencies = [
    "package @ git+https://github.com/user/package.git@develop",
]

```

### Mercurial (Hg) References

```toml

dependencies = [
    "package @ hg+https://hg.example.com/package@main",
]

```

### Subversion (Svn) References

```toml

dependencies = [
    "package @ svn+https://svn.example.com/package/trunk",
]

```

### Bazaar (Bzr) References

```toml

dependencies = [
    "package @ bzr+https://bzr.example.com/package/main",
]

```

## Local Path References

Dependencies can reference packages in local directories on the filesystem.

### Relative Paths

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    "local-package @ file:///../sibling-package",
    "dev-package @ file:///./packages/dev",
]

```

### Absolute Paths

```toml

dependencies = [
    "package @ file:///home/user/workspace/package",
]

```

### Editable Installs

Local references are typically installed in editable mode (using `pip install -e`), allowing development without reinstalling after changes:

```bash

# The package will be installed in editable mode automatically
pip install -e .

```

## URL References

Direct HTTP/HTTPS URLs to package archives:

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    "package @ https://example.com/packages/package-1.0.0.tar.gz",
    "another @ https://github.com/user/repo/releases/download/v1.0/package-1.0.whl",
]

```

## Combined VCS & Version Specifiers

VCS references can optionally include version specifiers:

```toml

[project]
dependencies = [
    "package @ git+https://github.com/user/package.git@main ; python_version>='3.8'",
]

```

## Practical Examples

### Development Setup

For a monorepo with multiple interdependent packages:

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
name = "main-package"
dependencies = [
    "core-lib @ file://../core-lib",
    "utils @ file://../utils",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "testing-lib @ file://../testing-lib",
]

```

### Fork or Patched Version

When using a forked or patched version of a package:

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    # Use patched fork from GitHub
    "requests @ git+https://github.com/my-org/requests.git@my-fix",
    # With tag for specific version
    "click @ git+https://github.com/pallets/click.git@8.0",
]

```

### Unreleased Development Versions

Testing against unreleased development versions:

```toml

[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    # Test against development branch
    "numpy @ git+https://github.com/numpy/numpy.git@main",
]

```

## Important Considerations

### Build Time vs. Runtime

- Direct references are resolved at build time
- The referenced repository/URL must be accessible during package build
- CI/CD pipelines must have access to the repositories

### Security

- Only use trusted repositories
- Avoid dynamic URL resolution in CI/CD environments
- Use specific commits/tags rather than branches when possible

### Distribution

- Packages with direct references cannot be published to PyPI
- They are useful for private distributions or development-only scenarios
- Source distributions will contain the references as configured

### Reproducibility

- Use specific commits or tags for reproducible builds
- Avoid mutable references like branch names
- Document why direct references are necessary

## Comparison: When to Use

| Scenario                       | Use                               |
| ------------------------------ | --------------------------------- |
| Published packages on PyPI     | Version specifiers                |
| Monorepo development           | Local paths                       |
| Testing patched/forked package | Git with tag or commit            |
| Development/unreleased version | Git with branch or tag            |
| Internal package server        | Version specifiers                |
| Quick local development        | Local paths with editable install |

## Related Configuration

- `dependencies.md` - Dependency specification overview
- `version-specifiers.md` - Standard version constraints
- `metadata-options.md` - Direct references configuration
