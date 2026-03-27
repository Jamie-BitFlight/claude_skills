---
category: project-metadata
topics: [keywords, classifiers, discovery, trove-classifiers, pypi-categorization]
related: [basic-metadata, ownership]
---

# Keywords & Classifiers

Keywords and classifiers serve as metadata aids for project discovery and categorization on package indexes like PyPI. They help users find projects relevant to their needs.

When Claude helps users improve project discoverability, explain the distinction: keywords are free-form search aids while classifiers are standardized Trove categories that organize projects on PyPI. Recommend 5-10 relevant keywords and 3-5 meaningful classifiers for optimal discoverability.

## Keywords

Keywords are arbitrary strings that assist in project discovery through search functionality.

```toml

[project]
keywords = [
    "web",
    "framework",
    "asgi",
    "api",
    "python",
]

```

### Guidelines

1. **Clarity**: Use clear, commonly understood terms
2. **Relevance**: Include primary concepts and use cases
3. **Count**: 5-10 keywords typically sufficient (no hard limit)
4. **Format**: Lowercase, hyphen-separated for multi-word keywords
5. **Avoid Duplicates**: Don't list variations of the same term

### Common Keywords

```toml

[project]
keywords = [
    "http",
    "client",
    "request",
    "networking",
    "python-library",
]

```

### Multi-Word Keywords

```toml

[project]
keywords = [
    "machine-learning",
    "natural-language-processing",
    "deep-learning",
    "transformers",
]

```

## Classifiers

Classifiers are standardized strings from the official [PyPI Classifiers](https://pypi.org/classifiers/) list. They categorize projects across multiple dimensions.

```toml

[project]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

```

### Classifier Categories

**Development Status:**

- Draft
- Development Status :: 1 - Planning
- Development Status :: 2 - Pre-Alpha
- Development Status :: 3 - Alpha
- Development Status :: 4 - Beta
- Development Status :: 5 - Production/Stable
- Development Status :: 6 - Mature
- Development Status :: 7 - Inactive

**Environment:**

- Environment :: Console
- Environment :: Web Environment
- Environment :: Console :: Curses

**Intended Audience:**

- Intended Audience :: Developers
- Intended Audience :: System Administrators
- Intended Audience :: End Users/Desktop
- Intended Audience :: Financial and Insurance Industry

**License:**

- License :: OSI Approved :: MIT License
- License :: OSI Approved :: Apache Software License
- License :: OSI Approved :: GNU General Public License v3 (GPLv3)
- License :: OSI Approved :: BSD License

**Programming Language:**

```toml

classifiers = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

```

**Operating System:**

- Operating System :: OS Independent
- Operating System :: POSIX :: Linux
- Operating System :: Microsoft :: Windows
- Operating System :: MacOS

**Topic:**

- Topic :: Software Development
- Topic :: Software Development :: Libraries
- Topic :: Internet :: WWW/HTTP
- Topic :: Utilities

**Framework:**

- Framework :: Django
- Framework :: Flask
- Framework :: FastAPI
- Framework :: Sphinx
- Framework :: Pytest

### Complete Example

```toml

[project]
name = "my-awesome-package"
version = "1.0.0"
description = "An awesome web framework for Python"
keywords = [
    "web",
    "framework",
    "http",
    "asgi",
]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

```

## Best Practices

1. **Accuracy**: Only use classifiers that truly apply to your project
2. **Completeness**: Include classifiers for all supported Python versions
3. **Status**: Keep development status current with actual project state
4. **Keywords**: Use natural language keywords distinct from classifiers
5. **Validation**: Verify classifiers exist on [PyPI Classifiers](https://pypi.org/classifiers/) before using

## Dynamic Classifiers

Classifiers can be declared dynamic and injected via metadata hooks:

```toml

[project]
dynamic = ["classifiers"]

[tool.hatch.metadata.hooks.custom]

```

## Impact on Discoverability

- Package indexes use classifiers for filtering and browsing
- Keywords appear in search results
- Both are indexed by search engines
- Proper classification improves project visibility

## Related Configuration

- `basic-metadata.md` - Name and description
- `urls.md` - Repository and documentation links
- `dynamic-metadata.md` - Declaring dynamic fields
