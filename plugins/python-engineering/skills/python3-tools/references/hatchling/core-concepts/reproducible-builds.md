---
category: core-concepts
topics: [reproducibility, security, verification, integrity, determinism]
related: [vcs-file-selection.md, wheel-vs-sdist.md, pep-517-backend.md]
---

# Reproducible Builds Configuration

## Overview

When helping users ensure build integrity and security, reference this document to understand how reproducible builds ensure that the same source code always produces identical distribution packages, bit-for-bit—critical for security, verification, and integrity.

**Source:** [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/) [Reproducible Builds Project](https://reproducible-builds.org/)

## Why Reproducible Builds Matter

### Security Implications

Reproducible builds enable users to verify package integrity:

<eg>
1. I build the package from source
2. I compare my build to the published wheel
3. If they're identical, the wheel is legitimate
4. If they differ, something is wrong
</eg>

Without reproducibility, users must trust the publisher unconditionally.

### Distribution Verification

Developers can verify upstream builds:

```bash
# I audit the source code and build locally
hatch build

# Compare with PyPI version
sha256sum dist/myproject-1.0.0-py3-none-any.whl
# sha256: a1b2c3d4e5f6...

# PyPI claims:
# sha256: a1b2c3d4e5f6...

# Match = trustworthy
# Mismatch = investigate
```

### Supply Chain Security

Reproducibility helps detect:

- Unauthorized modifications
- Compromised build systems
- Malicious injection attempts

## How Hatchling Enables Reproducible Builds

### 1. VCS-Aware File Selection

Hatchling respects `.gitignore` by default:

```toml
[tool.hatch.build.targets.sdist]
# No configuration needed
# Uses .gitignore automatically
```

**Effect:**

- Same files included in every build
- No accidental inclusion of local files
- Consistent across environments

### 2. Deterministic File Ordering

Hatchling orders files consistently in archives:

<eg>
TAR/ZIP archives always contain files in same order
├── a.py (always listed first)
├── b.py (always listed second)
└── c.py (always listed third)
</eg>

**Why this matters:** Different orderings would create different checksums.

### 3. Consistent Metadata

Package metadata is normalized:

<eg>
Before: Author     = "John Doe"
        Email      = "john@example.com"

After:  Author-Email = "John Doe <john@example.com>"
        (normalized to PEP 621 format)
</eg>

Same input always produces same output.

### 4. Timestamp Control

In source distributions, timestamps are normalized:

<eg>
All files in sdist have timestamp: 1980-01-01 00:00:00 UTC
(Not current build time)
</eg>

**Effect:** Building at different times produces identical archives.

### 5. Wheel Determinism

Wheels are built deterministically:

<eg>
RECORD file contents always same
dist-info/WHEEL metadata always same
Byte order always same
</eg>

## Configuration for Reproducibility

### Standard Configuration (Reproducible by Default)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.sdist]
# Respects .gitignore automatically
# Deterministic ordering
# Normalized timestamps

[tool.hatch.build.targets.wheel]
# Deterministic metadata
# Normalized timestamps
```

No special configuration needed - reproducibility is default.

### VCS Configuration

Ensure `.gitignore` is current:

```gitignore
# Exclude temporary files
*.pyc
__pycache__/
.pytest_cache/

# Exclude build artifacts
build/
dist/
*.egg-info/

# Exclude IDE/OS files
.vscode/
.idea/
.DS_Store

# Exclude local configuration
local_config.ini
.env
```

**Why:** If `.gitignore` is incomplete, files leak into distributions inconsistently.

### Explicit File Selection

If you need explicit file selection:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]

[tool.hatch.build.targets.sdist]
# Explicit selection (reproducible)
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
]

# Exclude specific files
exclude = [
    "*.pyc",
    "__pycache__",
    ".pytest_cache",
    "**/.DS_Store",
]
```

**Important:** Patterns should be deterministic (no wildcards that might match different files).

## Verifying Reproducibility

### Basic Verification

Build twice and compare:

```bash
# Build 1
hatch build

# Clean and build again
rm -rf dist/
hatch build

# Compare checksums
sha256sum dist/myproject-1.0.0-py3-none-any.whl > build1.txt
mv dist/ dist.backup/

# Build 3rd time
hatch build
sha256sum dist/myproject-1.0.0-py3-none-any.whl > build2.txt

# Should be identical
diff build1.txt build2.txt
# (no output = identical = reproducible)
```

### Full Verification

Use diffoscope to compare builds in detail:

```bash
# Build 1
hatch build
cp dist/*.whl wheel1.whl

# Clean
rm -rf dist/

# Build 2
hatch build
cp dist/*.whl wheel2.whl

# Compare in detail
diffoscope wheel1.whl wheel2.whl
# (no output = fully identical)
```

### CI/CD Integration

Add reproducibility check to pipeline:

```yaml
# GitHub Actions
jobs:
  reproducible-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build
        run: hatch build

      - name: Save checksums
        run: sha256sum dist/* > checksums.txt

      - name: Clean
        run: rm -rf dist/

      - name: Rebuild
        run: hatch build

      - name: Verify
        run: sha256sum -c checksums.txt
```

## Common Reproducibility Issues and Solutions

### Issue 1: Timestamps in Archives

**Problem:** Building at different times creates different archives.

**Solution:** Hatchling normalizes timestamps automatically.

```bash
# Both commands create identical archives
# (even at different times)
hatch build
# later...
hatch build
# Checksums match
```

### Issue 2: File Ordering

**Problem:** Files in archive in different order creates different checksum.

**Solution:** Hatchling orders files deterministically.

### Issue 3: Incomplete .gitignore

**Problem:** .gitignore missing patterns → inconsistent file inclusion.

**Solution:** Keep .gitignore complete and current:

```bash
# Check what would be included
tar tzf dist/myproject-1.0.0.tar.gz | head -20

# Look for unexpected files
tar tzf dist/myproject-1.0.0.tar.gz | grep __pycache__
# (should output nothing)
```

### Issue 4: Platform Differences

**Problem:** Different platforms might produce different outputs.

**Solution:** Build in consistent environment:

```bash
# Use container for builds
docker run --rm -v $(pwd):/project python:3.11 \
  bash -c "cd /project && pip install hatch && hatch build"
```

### Issue 5: Locale/Encoding Differences

**Problem:** Different locale settings affect string handling.

**Solution:** Set consistent locale:

```bash
# Ensure UTF-8 locale
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

hatch build
```

## How to Break Reproducibility (Anti-patterns)

Do NOT do these things:

### 1. Include Build Timestamps

```python
# Bad: Timestamp in generated file
build_time = datetime.now().isoformat()
```

Better:

```python
# Use version or commit date, not build time
# or compute from git tags
```

### 2. Include Random Data

```python
# Bad: Random data in generated file
random_token = secrets.token_hex()
```

Better:

```python
# Use deterministic data based on source
import hashlib
token = hashlib.sha256(source_file).hexdigest()
```

### 3. Incomplete .gitignore

```gitignore
# Bad: Too permissive
# build/

# Good: Specific patterns
build/
dist/
*.egg-info/
__pycache__/
.pytest_cache/
```

### 4. Platform-Specific Includes

```toml
# Bad: Different files on different platforms
# [tool.hatch.build.targets.sdist]
# include = ["/unix_only.sh"]  # Only on Unix

# Good: Include everything consistently
[tool.hatch.build.targets.sdist]
include = ["/src", "/tests", "/*.md"]
```

## Reproducibility and Version Management

### File-Based Version

Reproducible:

```python
# src/package/__init__.py
__version__ = "1.0.0"
```

Always produces same build for same version.

### VCS-Based Version

Reproducible with conditions:

```toml
[tool.hatch.version]
source = "vcs"
```

**Reproducible only if building from tag:**

```bash
git tag v1.0.0
git checkout v1.0.0  # Reproducible
hatch build          # Always version 1.0.0

git checkout main    # Commits after tag
hatch build          # Version changes (1.0.1.dev0)
```

**For reproducibility:** Always build from tags, not from commits.

## Reproducibility in the Ecosystem

### Why Projects Care

- **Debian/Ubuntu:** Require reproducible builds for package inclusion
- **Security audits:** Can verify packages match source
- **Community trust:** Enables distributed verification

### Public Verification

Some projects publish build results:

<eg>
Package: myproject-1.0.0-py3-none-any.whl
Build by: CI/CD on GitHub
SHA256: a1b2c3d4e5f6...
Reproducible: Yes
Verified by: 3 independent builds
</eg>

### Getting Recognized

For official Reproducible Builds recognition:

1. Make builds reproducible
2. Document reproducibility
3. Share checksums with community
4. Submit to Reproducible Builds database

## Best Practices

### 1. Keep .gitignore Current

```bash
# Regularly review
git check-ignore -v **/*

# Update when adding new directories
.tox/
.mypy_cache/
coverage/
```

### 2. Document Reproducibility

In README or CONTRIBUTING:

```markdown
## Reproducible Builds

This project builds reproducibly. To verify:

1. Clone and checkout this version
2. Run: hatch build
3. Compare: sha256sum dist/myproject-\*.whl
4. Should match published checksums
```

### 3. Publish Checksums

Make checksums available:

```bash
# In release notes or RELEASES.md
- myproject-1.0.0-py3-none-any.whl
  SHA256: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### 4. Test Reproducibility in CI/CD

```yaml
# GitHub Actions: Verify reproducibility
- name: Verify reproducible build
  run: |
    hatch build
    sha256sum dist/* > checksums.txt
    rm -rf dist/
    hatch build
    sha256sum -c checksums.txt
```

### 5. Use Standard Layouts

Standard layouts are more likely to be reproducible:

<eg>
src/myproject/      # Recommended
                    # Standard ordering, well-tested
</eg>

## Key Takeaways

1. **Reproducible builds** are enabled by default
2. **VCS awareness** respects .gitignore
3. **Deterministic ordering** and timestamps ensure consistency
4. **Keep .gitignore current** for reproducibility
5. **Test reproducibility** by building twice and comparing
6. **Publish checksums** for community verification
7. **Standards compliance** makes reproducibility easier

## References

- [Reproducible Builds Project](https://reproducible-builds.org/)
- [Reproducible Builds Debian](https://wiki.debian.org/ReproducibleBuilds)
- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
- [PEP 427 - Reproducibility Considerations](https://peps.python.org/pep-0427/#reproducible-builds)
