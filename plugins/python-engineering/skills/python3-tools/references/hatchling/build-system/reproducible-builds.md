---
category: build-system
topics:
- reproducible-builds
- source-date-epoch
- deterministic-builds
- build-timestamps
- ci-cd-builds
related:
- build-options
- environment-variables
- build-hooks
---

# Reproducible Builds Guide for Claude

This reference helps Claude implement reproducible builds in Hatchling projects. Reproducible builds ensure identical binary artifacts from the same source code, enabling verification and consistent deployments.

## Core Concept

Reproducible builds mean:

- Same source code → Same binary output
- Consistent file timestamps
- Deterministic file ordering
- Predictable archive generation

## SOURCE_DATE_EPOCH Configuration

### What is SOURCE_DATE_EPOCH

A Unix timestamp (seconds since 1970-01-01 00:00:00 UTC) that sets the maximum timestamp for files in the build. This is a standard from [reproducible-builds.org](https://reproducible-builds.org/specs/source-date-epoch/).

### Default Configuration

```toml
[tool.hatch.build]
# Enabled by default
reproducible = true
```

When `reproducible = true`:

1. Uses SOURCE_DATE_EPOCH if set
2. Otherwise uses consistent default value
3. All archive files get this timestamp

### Setting SOURCE_DATE_EPOCH

Help users set the timestamp:

```bash
# Use last Git commit time
export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
hatch build

# Use specific date
export SOURCE_DATE_EPOCH=$(date -d "2024-01-01" +%s)
hatch build

# Use Unix timestamp directly
export SOURCE_DATE_EPOCH=1704067200  # 2024-01-01 00:00:00 UTC
hatch build
```

## CI/CD Integration

### GitHub Actions

Suggest this workflow:

```yaml
name: Build
on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0 # Full history for timestamps

      - name: Set SOURCE_DATE_EPOCH
        run: |
          echo "SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)" >> $GITHUB_ENV

      - name: Build package
        run: |
          pip install hatchling
          hatch build
```

### GitLab CI

```yaml
build:
  script:
    - export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
    - pip install hatchling
    - hatch build
  artifacts:
    paths:
      - dist/
```

### Generic CI Pattern

```bash
#!/bin/bash
# get-timestamp.sh

if git rev-parse --git-dir > /dev/null 2>&1; then
    # Use last commit timestamp
    export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
else
    # Fallback to current time
    export SOURCE_DATE_EPOCH=$(date +%s)
fi

hatch build
```

## Verification Methods

### Verify Build Reproducibility

Help users verify builds are reproducible:

```bash
# Build twice and compare
export SOURCE_DATE_EPOCH=1704067200

# First build
hatch build
mv dist/mypackage-1.0.0-py3-none-any.whl dist/build1.whl

# Second build (clean first)
rm -rf dist/
hatch build
mv dist/mypackage-1.0.0-py3-none-any.whl dist/build2.whl

# Compare checksums - should be identical
sha256sum dist/build1.whl dist/build2.whl
```

### Inspect Archive Timestamps

Check file timestamps in archives:

```bash
# For wheel files
python -m zipfile -l dist/mypackage-1.0.0-py3-none-any.whl

# Check timestamps (should all be the same)
unzip -l dist/mypackage-1.0.0-py3-none-any.whl | head -20

# For tar.gz files
tar -tvf dist/mypackage-1.0.0.tar.gz | head -20
```

## Writing Reproducible Build Hooks

### Hook Best Practices

Help users write reproducible hooks:

```python
# build_hook.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Use SOURCE_DATE_EPOCH if available
        timestamp = int(os.environ.get('SOURCE_DATE_EPOCH', '0'))

        # Generate files with consistent content
        with open('generated.py', 'w') as f:
            f.write(f'# Generated at timestamp {timestamp}\n')
            f.write(f'BUILD_TIME = {timestamp}\n')

        # Avoid random data
        # BAD: BUILD_ID = str(uuid.uuid4())
        # GOOD: BUILD_ID = "stable-build-id"
```

## Common Issues and Solutions

### Non-Reproducible Elements

Help users identify and fix:

1. **Random Data in Files**

```python
# Avoid
import uuid
BUILD_ID = str(uuid.uuid4())

# Use instead
BUILD_ID = "stable-build-id"
# Or derive from source
import hashlib
BUILD_ID = hashlib.sha256(source_code.encode()).hexdigest()[:8]
```

2. **Current Time in Generated Files**

```python
# Avoid
from datetime import datetime
BUILD_TIME = datetime.now()

# Use instead
import os
from datetime import datetime
timestamp = int(os.environ.get('SOURCE_DATE_EPOCH', '0'))
BUILD_TIME = datetime.fromtimestamp(timestamp)
```

3. **Unstable File Ordering**

```python
# Avoid
files = set(Path('.').glob('*.py'))

# Use instead
files = sorted(Path('.').glob('*.py'))
```

## Testing Reproducibility

### Automated Test

Provide this test template:

```python
# test_reproducible.py
import subprocess
import hashlib
import tempfile
import os
from pathlib import Path

def test_reproducible_build():
    """Test that builds are reproducible."""
    os.environ['SOURCE_DATE_EPOCH'] = '1704067200'

    # Build twice
    subprocess.run(['hatch', 'build'], check=True)

    wheels = list(Path('dist').glob('*.whl'))
    assert len(wheels) == 1

    # Calculate checksum
    with open(wheels[0], 'rb') as f:
        hash1 = hashlib.sha256(f.read()).hexdigest()

    # Clean and rebuild
    subprocess.run(['rm', '-rf', 'dist'], check=True)
    subprocess.run(['hatch', 'build'], check=True)

    wheels = list(Path('dist').glob('*.whl'))
    with open(wheels[0], 'rb') as f:
        hash2 = hashlib.sha256(f.read()).hexdigest()

    assert hash1 == hash2, "Builds are not reproducible!"
```

## Version-Based Timestamps

### Map Versions to Timestamps

For consistent version timestamps:

```python
# In a build script or hook
from datetime import datetime
import os

VERSION_DATES = {
    "1.0.0": "2024-01-01",
    "1.1.0": "2024-02-15",
    "1.2.0": "2024-03-30",
}

version = "1.2.0"  # Get from project
if version in VERSION_DATES:
    dt = datetime.fromisoformat(VERSION_DATES[version])
    os.environ["SOURCE_DATE_EPOCH"] = str(int(dt.timestamp()))
```

## Benefits to Emphasize

When users ask why reproducible builds matter:

1. **Security**: Verify no tampering occurred
2. **Caching**: Same input → same output → better caching
3. **Debugging**: Consistent artifacts across environments
4. **Compliance**: Audit trail for regulatory requirements
5. **Trust**: Users can verify official builds

## Best Practices to Recommend

### Development Workflow

1. Always enable `reproducible = true` for releases
2. Set SOURCE_DATE_EPOCH from version control
3. Document the reproducible build process
4. Test reproducibility in CI/CD

### Build Hygiene

1. Avoid dynamic content in build artifacts
2. Sort all collections before iteration
3. Use deterministic algorithms
4. Pin all build dependencies

### Validation Strategy

1. Compare checksums between builds
2. Verify timestamps in archives
3. Test on different machines
4. Include in release checklist

## Disable When Necessary

For development/debugging:

```toml
[tool.hatch.build]
# Use current timestamps
reproducible = false
```

When disabled:

- Files get actual modification times
- Builds vary between runs
- Useful for development debugging

## Navigation

- `build-options.md` - General build configuration
- `environment-variables.md` - Build environment setup
- `../build-hooks/index.md` - Custom build processing
