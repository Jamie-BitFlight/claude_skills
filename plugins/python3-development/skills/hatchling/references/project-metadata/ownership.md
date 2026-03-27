---
category: project-metadata
topics: [authors, maintainers, contact-information, project-responsibility]
related: [basic-metadata, keywords-classifiers]
---

# Project Ownership: Authors & Maintainers

Project ownership is specified through authors and maintainers fields, indicating the people or organizations responsible for the project. These fields support the same format and are mutually exclusive (if values are identical, use only `authors`).

When Claude helps users add author and maintainer information, explain that both fields use identical structure (name and email objects) and choose the appropriate field based on project context (original authors vs. current maintainers).

## Structure

Both `authors` and `maintainers` accept an array of contact information objects, each containing:

- `name` (required) - Full name of the person or organization
- `email` (optional) - Contact email address

```toml

[project]
authors = [
    {name = "Alice Developer", email = "alice@example.com"},
    {name = "Bob Contributor", email = "bob@example.com"},
]

maintainers = [
    {name = "Carol Maintainer", email = "carol@example.com"},
]

```

## Authors

Represents the original or primary authors of the project. The exact interpretation is flexible and can represent:

- Original creators
- Current lead developers
- Primary maintainers
- Package owners

```toml

[project]
authors = [
    {name = "Author Name", email = "author@example.com"},
]

```

## Maintainers

Identifies current maintainers responsible for ongoing development and support. Use this field to indicate who should be contacted for issues or contributions.

```toml

[project]
maintainers = [
    {name = "Maintainer Name", email = "maintainer@example.com"},
]

```

## Single vs. Multiple Contributors

**Single Author:**

```toml

[project]
authors = [
    {name = "John Doe", email = "john@example.com"},
]

```

**Multiple Authors:**

```toml

[project]
authors = [
    {name = "Alice Smith", email = "alice@example.com"},
    {name = "Bob Johnson", email = "bob@example.com"},
    {name = "Carol White", email = "carol@example.com"},
]

```

## Name-Only Format

When email is not available or preferred, provide name only:

```toml

[project]
authors = [
    {name = "Organization Name"},
]

```

## Combined Authors and Maintainers

Use both fields to distinguish original creators from current maintainers:

```toml

[project]
authors = [
    {name = "Original Author", email = "original@example.com"},
]

maintainers = [
    {name = "Current Maintainer", email = "current@example.com"},
    {name = "Second Maintainer", email = "second@example.com"},
]

```

## Display on Package Indexes

Package indexes like PyPI display this information in project metadata. Authors appear as contact information while maintainers may be highlighted for community contribution inquiries.

## Best Practices

1. **Keep Current**: Update when project ownership or maintenance changes
2. **Email Address**: Include when available for direct contact
3. **Organization Names**: Use when representing a company or organization
4. **Avoid Duplication**: Use only `authors` if the same people maintain the project
5. **Multiple Maintainers**: Include all active maintainers for distributed projects

## Dynamic Ownership

Author and maintainer information can be declared dynamic and injected via metadata hooks:

```toml

[project]
dynamic = ["authors", "maintainers"]

[tool.hatch.metadata.hooks.custom]
path = "hatch_build.py"

```

Then in `hatch_build.py`:

```python

from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        metadata["authors"] = [
            {"name": "John Doe", "email": "john@example.com"}
        ]
        metadata["maintainers"] = [
            {"name": "Jane Smith", "email": "jane@example.com"}
        ]

```

## Related Configuration

- `basic-metadata.md` - Name, version, description
- `custom-hooks.md` - Dynamic metadata injection
- `dynamic-metadata.md` - Marking fields as dynamic
