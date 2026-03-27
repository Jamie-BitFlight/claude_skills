---
category: Error Handling
topics: [spdx-validation, license-expressions, license-files, pep-639, custom-licenses]
related: [./version-validation.md, ./metadata-compatibility.md, ./build-validation.md]
---

# SPDX License Validation Errors in Hatchling

## Overview

When helping users configure licenses in Hatchling projects, reference this guide to understand and resolve license validation errors. Hatchling validates license metadata against SPDX standards and PEP 639 specifications. This document covers license validation errors, SPDX expressions, and custom license identifiers.

## License Expression Validation

### Error: Invalid SPDX License Expression

**Error Message:**

<eg>
ValueError: Error parsing field `project.license` - unknown license: [license-id]
ValueError: Error parsing field `project.license` - invalid license expression: [expression]
</eg>

### Valid SPDX Expressions

```toml
[project]
# Single licenses
license = "MIT"
license = "Apache-2.0"
license = "GPL-3.0-only"

# Compound expressions
license = "MIT OR Apache-2.0"
license = "MIT AND Apache-2.0"
license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"

# With exceptions
license = "GPL-3.0-only WITH Classpath-Exception-2.0"
```

### Invalid Expressions

<eg>
# INVALID - will cause errors
license = "Use-it-after-midnight"           # Not SPDX
license = "Apache-2.0 OR 2-BSD-Clause"      # Typo in BSD
license = "LicenseRef-License with spaces"  # Spaces in custom ID
license = "LicenseRef-License_with_underscores"  # Underscores not allowed
</eg>

## Custom License Identifiers (PEP 639)

### LicenseRef Format

**Valid Custom Identifiers (v1.26.0+):**

```toml
[project]
# Any LicenseRef- prefix is now valid
license = "LicenseRef-Proprietary"
license = "LicenseRef-MyCompany-License-1.0"
license = "LicenseRef-Special-License"
license = "LicenseRef-Public-Domain"  # Supported since v1.9.0
```

**Rules for Custom Identifiers:**

- Must start with `LicenseRef-`
- Followed by alphanumeric characters, `.`, and/or `-`
- No spaces or underscores allowed
- Case-insensitive validation

### Migration for Proprietary Licenses

**Before v1.26.0:**

```toml
[project]
# Only these two were supported
license = "LicenseRef-Proprietary"
license = "LicenseRef-Public-Domain"
```

**After v1.26.0:**

```toml
[project]
# Any valid LicenseRef- format works
license = "LicenseRef-MyCompany-Commercial-1.0"
license = "LicenseRef-Internal-Use-Only"
```

## License Files Configuration

### Modern Format (v1.26.0+)

```toml
[project]
# Array of glob patterns
license-files = [
    "LICENSE*",
    "COPYING*",
    "NOTICE*",
    "licenses/*.txt"
]
```

### Legacy Format

```toml
[project]
# Backward compatibility maintained
license-files = { paths = ["LICENSE*"], globs = ["licenses/*"] }
```

## Core Metadata Version Compatibility

### Version 2.4 (v1.27.0+)

```toml
# License-Expression field used
[project]
license = "MIT OR Apache-2.0"
license-files = ["LICENSE*"]
```

**Generated Metadata:**

<eg>
License-Expression: MIT OR Apache-2.0
License-File: LICENSE
</eg>

### Version 2.3 and Earlier

```toml
[project]
license = "MIT"
```

**Generated Metadata (back-populated):**

<eg>
License: MIT
License-Expression: MIT  # Added for compatibility
</eg>

### Version 2.1-2.2

- `License-Expression` retroactively supported
- `License-File` retroactively supported
- No `License-Files` field written

## SPDX Version Updates

Hatchling regularly updates SPDX license data:

- **v1.22.0**: SPDX 3.23
- **v1.12.0**: SPDX 3.19
- **v1.7.0**: SPDX 3.18
- **v1.4.0**: SPDX 3.17

## Validation Implementation

### Custom Validation Script

```python
#!/usr/bin/env python3
"""Validate SPDX license expressions."""

from packaging.licenses import NormalizedLicenseExpression
from packaging.licenses import InvalidLicenseExpression

def validate_license(expression: str) -> bool:
    """Validate SPDX license expression."""
    try:
        # Requires packaging >= 24.2
        normalized = NormalizedLicenseExpression(expression)
        print(f"Valid expression: {normalized}")
        return True
    except InvalidLicenseExpression as e:
        print(f"Invalid expression: {e}")
        return False

# Examples
validate_license("MIT")  # Valid
validate_license("MIT OR Apache-2.0")  # Valid
validate_license("LicenseRef-Proprietary")  # Valid
validate_license("Unknown-License")  # Invalid
```

### Build Hook for License Validation

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import re

class LicenseValidationHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Validate license configuration."""
        config = self.config

        # Get license from metadata
        license_expr = self.metadata.core.license

        if license_expr:
            # Validate LicenseRef format if custom
            if license_expr.startswith("LicenseRef-"):
                if not self._validate_custom_license(license_expr):
                    raise ValueError(
                        f"Invalid custom license ID: {license_expr}"
                    )

    def _validate_custom_license(self, license_id: str) -> bool:
        """Validate custom LicenseRef identifier."""
        # Pattern: LicenseRef-[idstring]
        # idstring: letters, numbers, . and/or -
        pattern = r"^LicenseRef-[A-Za-z0-9.-]+$"
        return bool(re.match(pattern, license_id))
```

## Common License Configurations

### Open Source Project

```toml
[project]
name = "my-open-source-project"
license = "MIT"
license-files = ["LICENSE"]

[project.urls]
"License" = "https://opensource.org/licenses/MIT"
```

### Dual-Licensed Project

```toml
[project]
name = "dual-licensed-project"
license = "Apache-2.0 OR MIT"
license-files = ["LICENSE-APACHE", "LICENSE-MIT"]

[project.urls]
"License Apache" = "https://www.apache.org/licenses/LICENSE-2.0"
"License MIT" = "https://opensource.org/licenses/MIT"
```

### Proprietary Project

```toml
[project]
name = "proprietary-project"
license = "LicenseRef-Proprietary"
license-files = ["LICENSE.txt", "EULA.txt"]

[project.urls]
"License" = "https://example.com/license"
```

### Complex License Expression

```toml
[project]
name = "complex-project"
license = "(MIT OR Apache-2.0) AND (BSD-3-Clause OR GPL-3.0-only)"
license-files = ["licenses/*.txt"]
```

## Troubleshooting License Errors

### Error: Unknown Trove Classifier

**Problem:**

```toml
[project]
classifiers = [
    "License :: OSI Approved :: MyLicense"  # Not a valid trove
]
```

**Solution:**

```toml
[project]
classifiers = [
    "License :: OSI Approved :: MIT License"  # Valid trove
]
license = "MIT"  # Also set SPDX expression
```

### Error: Disabling Validation

**For Development Only:**

```bash
# Disable trove classifier validation
export HATCH_METADATA_CLASSIFIERS_NO_VERIFY=1
hatch build
```

**Warning:** Never disable validation for production builds!

### Error: License File Not Found

**Problem:**

```toml
[project]
license-files = ["LICENSE"]  # File doesn't exist
```

**Solution:**

1. Create the LICENSE file
2. Or use glob pattern: `license-files = ["LICENSE*"]`
3. Or omit if using license expression only

## Migration Guide

### From setuptools

**setuptools (setup.py):**

```python
setup(
    license='MIT',
    license_files=['LICENSE'],
)
```

**Hatchling (pyproject.toml):**

```toml
[project]
license = "MIT"
license-files = ["LICENSE"]
```

### From Custom License Text

**Old approach:**

```toml
[project]
license = {text = "See LICENSE file for details"}
```

**Modern approach:**

```toml
[project]
license = "LicenseRef-Custom"
license-files = ["LICENSE"]
```

### From Non-SPDX to SPDX

**Non-SPDX:**

```toml
license = "BSD"  # Ambiguous
```

**SPDX:**

```toml
license = "BSD-3-Clause"  # Specific
```

## Best Practices

1. **Use standard SPDX identifiers** when possible
2. **Include license files** in distribution
3. **Use LicenseRef- prefix** for custom licenses
4. **Validate expressions** before publishing
5. **Keep SPDX data updated** with latest Hatchling

## Version History

- **v1.27.0**: Default core metadata 2.4
- **v1.26.0**: Support any LicenseRef- pattern
- **v1.22.0**: Updated SPDX to 3.23
- **v1.12.0**: Added License-Expression support
- **v1.9.0**: Added LicenseRef-Proprietary support

## Related Documentation

- `metadata-validation.md`
- `version-validation.md`
- `metadata-compatibility.md`
