---
category: release-notes
topics: [metadata-hooks, version-sources, dynamic-metadata, version-management, build-hooks, dynamic-versioning, configuration]
related: [INDEX.md, RELEASE_NOTES.md, README.md, BUILD_HOOKS_AND_PERFORMANCE.md, PEP_639_LICENSE_METADATA.md]
---

# Metadata Hooks and Version Sources Evolution

Reference guide for the evolution and implementation of metadata hooks and version sources in Hatchling. Use this when helping users understand dynamic metadata generation and version management across releases.

## Metadata Hooks History

### Introduction of Metadata Hooks

#### v1.3.0 (2022-06-15) - Initial Mechanism

First introduction of the metadata hook mechanism:

- Enable dynamic computation of package metadata
- Provide interface for custom metadata providers
- Support multiple metadata sources

#### v1.4.0 (2022-07-03) - Version Hook

- Dedicated `version` build hook for dynamic version management
- Simplified version retrieval from various sources
- Standard interface for custom version logic

#### v1.8.0 (2022-08-16) - Classifier Methods

Added `get_known_classifiers` method to metadata hooks:

- Retrieve valid Trove classifiers
- Validate classifiers at build time
- Prevent invalid classifier values

#### v1.22.0 (2024-03-16) - Hook Dependencies

Major enhancement to the metadata hook interface:

**Changed:**

- Metadata for the `wheel` target now defaults to `PKG-INFO` metadata within source distributions
- Improved integration with build process

**Added:**

- `dependencies` method to the build hook interface
- Hooks can now dynamically define their own dependencies
- Enables complex build scenarios with external dependencies

### Metadata Hook Interface Evolution

| Feature      | Version | Change                          |
| ------------ | ------- | ------------------------------- |
| Basic hooks  | v1.3.0  | Initial mechanism               |
| Version hook | v1.4.0  | Dedicated hook type             |
| Classifiers  | v1.8.0  | get_known_classifiers method    |
| PKG-INFO     | v1.22.0 | Default to source dist metadata |
| Dependencies | v1.22.0 | Hooks can define dependencies   |

## Version Sources Implementation

### Supported Version Sources

Hatchling provides multiple built-in mechanisms to dynamically determine package version:

#### 1. Regex Version Source (v1.2.0+)

Extract version from file patterns using regular expressions.

**Features:**

- Match version strings in source files
- Flexible pattern matching
- Support for various file formats

**Example:**

```toml
[tool.hatch.version]
path = "src/mypackage/__init__.py"
pattern = '__version__ = ["\'](?P<version>[^"\']*)["\']'
```

#### 2. Code Version Source (v1.6.0+)

Execute Python code or import modules to retrieve version.

**Features (v1.6.0):**

- Load version from Python source code
- Support extension modules (v1.6.0)
- Search multiple paths (v1.6.0)

**Features (v1.2.0+):**

- Execute arbitrary Python code
- Import package modules
- Dynamic version computation

**Example:**

```toml
[tool.hatch.version]
source = "code"
path = "src/mypackage/__init__.py"
search-paths = ["src"]
```

#### 3. Environment Variable Version Source (v1.11.0+)

Retrieve version from environment variables at build time.

**Added in v1.11.0:**

- Simple environment variable lookup
- Useful for CI/CD pipelines
- Optional default fallback values

**Example:**

```toml
[tool.hatch.version]
source = "env"
variable = "PROJECT_VERSION"
```

### Version Source Timeline

| Version | Release    | Feature                                   |
| ------- | ---------- | ----------------------------------------- |
| 1.2.0   | 2022-05-20 | Regex version source                      |
| 1.6.0   | 2022-07-23 | Code source with extensions; search-paths |
| 1.11.0  | 2022-10-08 | Environment variable source               |

### Version Scheme Support

#### Standard Version Scheme (v1.0.0+)

Default semantic versioning scheme with bump validation.

**Features:**

- Semantic versioning support
- Epoch handling (fixed v1.19.0)
- Version bumping utilities

**v1.11.0 Enhancement:**

- Added `validate-bump` option for strict version progression

### Third-Party Version Plugins

Popular community plugins compatible with Hatchling:

- **hatch-vcs** - Version from VCS tags (git, hg)
- **versioningit** - Advanced VCS versioning
- **setuptools-scm** - setuptools-compatible VCS versions
- **uv-dynamic-versioning** - Dynamic versioning for uv/hatch

## Version Source Configuration Examples

### Regex Pattern Example

```toml
[tool.hatch.version]
path = "src/mypackage/__init__.py"
pattern = '__version__\s*=\s*["\'](?P<version>[^"\']*)["\']'
```

### Code Source Example

```toml
[tool.hatch.version]
source = "code"
path = "src/mypackage/__init__.py"
search-paths = ["src", "lib"]
```

### Environment Variable Example

```toml
[tool.hatch.version]
source = "env"
variable = "BUILD_VERSION"
```

### VCS Plugin Example

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"
```

## Dynamic Metadata Integration

### How Metadata Hooks Work

1. **Hooks run during build process**

   - Before wheel/sdist creation
   - Can access project configuration
   - May query external sources

2. **Multiple hooks can cooperate**

   - Each hook provides specific metadata
   - Hooks can depend on each other
   - Executed in dependency order

3. **Metadata can override static config**
   - Useful for version, dependencies, classifiers
   - Dynamic computation at build time
   - Enables complex build scenarios

### Dynamic Metadata Fields Supported

- `version` - Package version
- `dependencies` - Runtime dependencies
- `optional-dependencies` - Optional feature dependencies
- `classifiers` - Trove classifiers
- Custom metadata fields

### Build Hook Dependencies (v1.22.0+)

```python
class CustomMetadataHook:
    PLUGIN_NAME = "custom"

    def __init__(self, root, config):
        self.root = root
        self.config = config

    def dependencies(self):
        # Return list of packages needed for this hook
        return ["requests>=2.0.0", "ruamel.yaml>=0.18"]

    def update(self, metadata):
        # Metadata is now updated with hook dependencies
        pass
```

## Recent Improvements (v1.22+)

### Metadata Loading from Source Distributions

- Wheel metadata now defaults to `PKG-INFO` from source distributions
- Reduces build time and complexity
- Better support for editable installs from sdists

### Selective Metadata Reading (v1.22.3+)

- Only read source distribution metadata for explicitly dynamic fields
- Avoid unnecessary metadata processing
- Proper handling of non-core-metadata dynamic fields like entry points

### Build Hook Robustness

- v1.22.2: Fixed metadata hooks when building from source distributions
- v1.22.3: Fixed custom build hooks with dynamic dependencies
- v1.22.4: Only read explicitly defined dynamic fields
- v1.22.5: Fix reading metadata from source distributions

## Version Management Best Practices

### Choosing a Version Source

1. **Regex Pattern** - Simple cases with consistent version format
2. **Code Source** - Python package with `__version__` variable
3. **Environment Variable** - CI/CD systems with version from environment
4. **VCS Plugin** - Automatic versioning from git/hg tags

### Single Source of Truth

**Best Practice:**

- Define version in one location
- Use appropriate source to extract it
- Avoid duplicating version information

### Validation Strategy (v1.11.0+)

```toml
[tool.hatch.version]
path = "src/mypackage/__init__.py"
pattern = '__version__\s*=\s*"(?P<version>[^"]*)"'

[tool.hatch.version.scheme]
validate-bump = true  # Ensure valid version progression
```

## Related Documentation

- [Hatchling Version Configuration](https://hatch.pypa.io/latest/plugins/version-source/)
- [Hatchling Metadata Hooks](https://hatch.pypa.io/latest/plugins/metadata-hook/)
- [Dynamic Metadata Guide](https://hatch.pypa.io/latest/how-to/config/dynamic-metadata/)
- [Build System Reference](https://hatch.pypa.io/latest/config/build/)

## Known Issues and Workarounds

### Version Source Edge Cases

**Issue:** Extension modules in version source fail to load

**Solution (v1.6.0+):**

- Use `search-paths` option to specify module directories
- Ensure compiled extensions are available

### Dynamic Dependencies with Hooks

**Issue:** Build hooks with dependencies may be slow

**Solution (v1.22.0+):**

- Use `dependencies()` method properly
- Minimize external dependencies in hooks
- Consider using regex source for simple cases
