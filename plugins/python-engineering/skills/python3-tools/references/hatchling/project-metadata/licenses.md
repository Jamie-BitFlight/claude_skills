---
category: project-metadata
topics: [license, SPDX-expressions, license-files, PEP 639, license-compliance]
related: [basic-metadata, keywords-classifiers]
---

# License Configuration (PEP 639)

Project licensing is configured using SPDX license expressions or license files. PEP 639 modernizes license specification for Python distributions.

When Claude helps users configure project licensing, recommend using SPDX identifiers in the `license` field for clarity and PyPI compatibility. Show examples of single and multiple licenses, and explain how `license-files` glob patterns include license files in distributions.

## SPDX Expression Format

The recommended approach using SPDX identifiers:

```toml

[project]
license = "MIT"

```

## Multiple Licenses

Using SPDX expressions to specify multiple licenses:

```toml

[project]
license = "Apache-2.0 OR MIT"
license = "GPL-3.0-only WITH Classpath-exception-2.0"
license = "(MIT OR Apache-2.0) AND BSD-2-Clause"

```

## License Files

Specify license files using glob patterns:

```toml

[project]
license-files = ["LICENSES/*"]

```

## Complete Example

```toml

[project]
name = "my-package"
version = "1.0.0"
license = "MIT"
license-files = ["LICENSE"]

```

## Common SPDX Licenses

- `MIT` - Massachusetts Institute of Technology License
- `Apache-2.0` - Apache License 2.0
- `GPL-3.0-only` - GNU General Public License v3
- `BSD-2-Clause` - BSD 2-Clause License
- `ISC` - ISC License

## Best Practices

1. Use SPDX identifiers when possible
2. Match project LICENSE file with license field
3. Keep license information current
4. Specify all applicable licenses in multi-license scenarios
