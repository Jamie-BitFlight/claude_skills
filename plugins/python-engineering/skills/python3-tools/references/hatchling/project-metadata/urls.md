---
category: project-metadata
topics: [project-urls, documentation-url, repository-url, issue-tracker, homepage]
related: [basic-metadata, keywords-classifiers]
---

# Project URLs

Project URLs provide links to important project resources such as documentation, repository, issue tracker, and custom web pages.

When Claude helps users add project URLs, explain that the `[project.urls]` table uses descriptive keys (Documentation, Repository, etc.) that appear on PyPI and direct users to important project resources. While standard keys are common, projects can use custom labels for additional links.

## URL Configuration

URLs are specified as a table where keys are descriptive labels and values are the actual URLs:

```toml

[project.urls]
Documentation = "https://example.com/docs"
Repository = "https://github.com/user/project"
"Bug Tracker" = "https://github.com/user/project/issues"
Changelog = "https://github.com/user/project/releases"

```

## Common URL Labels

**Documentation**

```toml
[project.urls]
Documentation = "https://project.readthedocs.io"
```

**Repository**

```toml
[project.urls]
Repository = "https://github.com/user/project"
"Source Code" = "https://github.com/user/project"
```

**Issue Tracking**

```toml
[project.urls]
"Bug Tracker" = "https://github.com/user/project/issues"
"Issue Tracker" = "https://github.com/user/project/issues"
```

**Changelog**

```toml
[project.urls]
Changelog = "https://github.com/user/project/releases"
"Release Notes" = "https://github.com/user/project/releases"
```

**Discussion/Support**

```toml
[project.urls]
Discussions = "https://github.com/user/project/discussions"
"Support Forum" = "https://community.example.com"
```

**Additional Resources**

```toml
[project.urls]
"API Reference" = "https://example.com/api"
"Contributing Guide" = "https://github.com/user/project/blob/main/CONTRIBUTING.md"
```

## Complete Example

```toml

[project]
name = "my-package"
version = "1.0.0"

[project.urls]
Homepage = "https://example.com"
Documentation = "https://docs.example.com"
Repository = "https://github.com/user/my-package"
"Bug Tracker" = "https://github.com/user/my-package/issues"
Changelog = "https://github.com/user/my-package/blob/main/CHANGELOG.md"
"Contributing Guide" = "https://github.com/user/my-package/blob/main/CONTRIBUTING.md"

```

## Best Practices

1. **Use Standard Labels**: Follow commonly recognized naming conventions
2. **Valid URLs**: Ensure all URLs are correct and accessible
3. **Relevant Links**: Include only useful resources for users
4. **Update Regularly**: Keep URLs current as project infrastructure changes
5. **Use HTTPS**: Prefer secure HTTPS URLs when available

## Dynamic URLs

URLs can be declared dynamic and injected via metadata hooks:

```toml

[project]
dynamic = ["urls"]

[tool.hatch.metadata.hooks.custom]

```

## Display on Package Indexes

Package indexes like PyPI display these URLs prominently on project pages, enabling users to easily navigate to documentation, report issues, and contribute.

## Related Configuration

- `basic-metadata.md`
- `ownership.md`
