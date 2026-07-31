---
category: release-notes
topics: [build-hooks, performance, optimization, file-selection, directory-traversal, metadata-optimization, best-practices]
related: [INDEX.md, RELEASE_NOTES.md, README.md, METADATA_HOOKS_AND_VERSION_SOURCES.md]
---

# Build Hooks and Performance Optimizations

Reference guide for build hooks implementation and performance optimization strategies in Hatchling across releases. Use this when helping users understand build system extensibility, performance improvements, and optimization best practices.

## Build Hooks Evolution

### Initial Introduction

#### v1.4.0 (2022-07-03) - Build Hook Foundation

Introduced the core build hook system:

**Added:**

- Version build hook for dynamic version management
- Generic hook extensibility mechanism
- Hook integration with wheel/sdist targets

**Key Capabilities:**

- PEP 561 type hinting support
- Modification of build-time file selection
- Path rewriting with `sources` option
- Auto-detection of single module layouts

### Build Hook Interface Development

#### v1.7.0 (2022-08-12) - Build Requirements

**Added:**

- `require-runtime-features` option for builders and build hooks
- Declare external requirements for build process
- Improved error messages for dev mode with path rewrites

#### v1.22.0 (2024-03-16) - Hook Dependencies Method

**Major Enhancement:**

- Add `dependencies` method to the build hook interface
- Hooks can dynamically define their own dependencies
- Improved build system flexibility

**Other Improvements:**

- Global build hooks now run before target-specific hooks
- Better integration with metadata hooks

### Build Hook Categories

#### Version Hook (v1.4.0+)

Dynamically provide package version at build time.

**Use Cases:**

- Extract version from source files
- Generate version from VCS information
- Compute version from environment

#### Metadata Hooks (v1.3.0+)

Dynamically provide package metadata.

**Features:**

- Custom metadata computation
- Integration with dynamic metadata fields
- Classifier validation (v1.8.0+)

#### Custom Build Hooks

Arbitrary build customizations.

**Use Cases:**

- Code generation at build time
- Compression or minification
- Generated documentation inclusion
- Asset compilation

### Hook Execution Model

**Order of Execution:**

1. Global build hooks (v1.22.0+)
2. Target-specific build hooks
3. Build process execution
4. Target-specific post-build hooks

**Hook Interface Methods:**

- `dependencies()` - Declare hook dependencies (v1.22.0+)
- `initialize(target_name, build_data)` - Pre-build initialization
- `finalize(target_name, build_data, artifact)` - Post-build finalization

## Performance Optimizations

### Directory Traversal Optimization (v1.4.0+)

#### Initial Optimization (v1.4.0)

**Improvement:** Improve performance by never entering directories that are guaranteed to be undesirable like `__pycache__` rather than excluding individual files within.

**Impact:**

- Faster project scanning
- Reduced file system operations
- More efficient builds for large projects

#### Expanded Exclusions (v1.6.0+)

**Changed (v1.6.0):**

- When no build targets specified, default to `sdist` and `wheel` rather than config-defined targets
- Global build hooks now run before target-specific hooks

**Added (v1.6.0):**

- Optimize directory traversal strategy
- Improved filtering of unnecessary directories

#### Additional Exclusions (v1.10.0+)

**Added (v1.10.0):** Added to never-traverse list:

- `__pypackages__`
- `.hg` (Mercurial)
- `.hatch` (Hatch-specific)
- `.tox` (tox environments)
- `.nox` (nox test environments)

#### Extended Exclusions (v1.18.0+)

**Added (v1.18.0):**

- Updated list of directories that are always excluded
- Removal of Python 3.7 support (lighter maintenance)

#### Further Expansion (v1.24.2+)

**Added (v1.24.2):**

- Add `.venv` to list of directories that cannot be traversed

#### Latest Updates (v1.26.0+)

**Added (v1.26.0):**

- Add `.pixi` (pixi package manager) to exclusion list
- Maintains optimal build performance for modern development tools

### File Selection Improvements

#### v1.9.0 (2022-09-09) - Pattern Matching

**Changed:**

- File pattern matching now more closely resembles Git's behavior
- Improved consistency with user expectations
- Better support for `.gitignore` patterns

**Improvements:**

- Implement minimal `prepare_metadata_for_build_wheel`
- Implement minimal `prepare_metadata_for_build_editable`
- Faster metadata-only operations for non-frontend tools

#### v1.19.0 (2023-12-11) - Selection Validation

**Changed:**

- Error raised if force-included path does not exist
- Error raised if no file selection options defined for wheel target
- Prevents silent failures and confusing build results

**Fixed:**

- Better error message when wheel target cannot determine what to ship
- Proper handling of single-module layout detection

#### v1.20.0 (2023-12-13) - Selection Regression Fix

**Fixed:**

- Fix regression in 1.19.1 that allowed `exclude` to count toward inclusion selection
- Restored proper default inclusion selection heuristics

#### v1.22.0 (2024-03-16) - VCS Integration

**Added:**

- Load VCS ignore patterns first so whitelisted patterns can be excluded by project configuration
- Better integration with Git and other VCS tools

**Fixed:**

- Don't consider VCS ignore files that are outside of the VCS boundary
- Gracefully ignore UNIX socket files in sdist targets
- Begin ignoring certain ubiquitous files (`.DS_Store` on macOS)

### Wheel Optimization

#### v1.12.2 (2023-01-05) - macOS Compatibility

**Added:**

- `macos-max-compat` option for wheel target (enabled by default)
- Support for latest version of `packaging` library
- Improved macOS compatibility

#### v1.25.0 (2024-06-22) - Default Change

**Changed:**

- The `macos-max-compat` option is now disabled by default
- Will be removed in a future release
- Reduced performance overhead for non-macOS users

**Added:**

- Artifacts now have permission bits normalized
- Zip64 support properly enabled for large wheels

#### v1.25.0 - Platform-Specific Tagging

**Fixed:**

- Ignore `manylinux`/`musllinux` tags for wheel artifact name
- Respect `MACOSX_DEPLOYMENT_TARGET` environment variable

### Metadata Optimization

#### v1.22.0 (2024-03-16) - PKG-INFO Reuse

**Major Optimization:**

- Wheel metadata now defaults to `PKG-INFO` metadata within source distributions
- Reduces redundant metadata computation
- Faster editable installs from source distributions

**Impact:**

- Building wheels from source distributions is faster
- Reduced CPU usage during builds
- Better support for reproducible builds

#### v1.22.1-1.22.5 (2024-03-16 to 2024-04-04)

Series of refinements to metadata handling:

- v1.22.1: Update default core metadata to 2.3
- v1.22.2: Fix regression when loading from source distributions
- v1.22.3: Fix custom hook with dynamic dependencies
- v1.22.4: Only read explicitly defined dynamic fields
- v1.22.5: Fix reading metadata from source distributions

### Build Data Optimizations

#### v1.24.0 (2024-04-16) - Shared Artifacts

**Added:**

- `shared_data` and `shared_scripts` build data for wheel target
- Enables efficient packaging of shared files
- Reduces wheel size for multi-wheel distributions

#### v1.24.1 (2024-04-18)

**Fixed:**

- Maintain file permissions for shared-scripts

#### v1.25.0 (2024-06-22)

**Added:**

- Permission bits normalization for all artifacts

### Encoding & String Handling

#### v1.19.0 (2023-12-11)

**Fixed:**

- Properly escape spaces for URI context formatting
- Improved handling of special characters in paths

#### v1.11.0 (2022-10-08)

**Fixed:**

- Use proper CSV formatting for `RECORD` metadata file
- Prevents warnings from `pip` during installation
- Handles file names with special characters (commas, etc.)

## Build Performance Metrics

### Key Performance Improvements

| Area                | Version | Improvement             |
| ------------------- | ------- | ----------------------- |
| Directory traversal | v1.4.0  | Skip undesirable dirs   |
| VCS integration     | v1.22.0 | Load patterns first     |
| Metadata reuse      | v1.22.0 | Use PKG-INFO from sdist |
| Shared artifacts    | v1.24.0 | Efficient multi-wheel   |
| Exclusion list      | v1.26.0 | Pixi support            |

### Build Time Reduction Strategies

1. **Skip unnecessary directories** (v1.4.0+)

   - Automatically excludes `__pycache__`, venv, etc.
   - ~10-30% faster scanning on large projects

2. **Metadata reuse** (v1.22.0+)

   - Wheel metadata from source dist PKG-INFO
   - Significant speedup for wheel builds from sdist

3. **Lazy evaluation**

   - Only process explicitly dynamic fields
   - Skip metadata computation for static fields

4. **Intelligent file matching** (v1.9.0+)
   - Git-like pattern matching
   - Early termination on matched patterns

## Build Hook Best Practices

### Performance Considerations

1. **Minimize Hook Complexity**

   - Avoid expensive operations in hooks
   - Cache computed results when possible
   - Use simple hooks for simple operations

2. **Declare Dependencies Properly** (v1.22.0+)

   ```python
   def dependencies(self):
       # Only include truly necessary dependencies
       return ["required-package>=1.0"]
   ```

3. **Use Appropriate Hook Type**
   - Version hook for version management
   - Metadata hook for metadata computation
   - Custom hook for complex build operations

### Hook Debugging

- Enable verbose output: `hatchling build -v`
- Check hook execution order
- Verify dependencies are available

## Related Documentation

- [Hatchling Build Hooks](https://hatch.pypa.io/latest/plugins/build-hook/)
- [Build System Reference](https://hatch.pypa.io/latest/config/build/)
- [Wheel Target Configuration](https://hatch.pypa.io/latest/plugins/builder/wheel/)
- [Source Distribution Configuration](https://hatch.pypa.io/latest/plugins/builder/sdist/)

## Known Issues and Workarounds

### Slow Builds with Custom Hooks

**Issue:** Build process is slow with custom hooks

**Solutions:**

1. Profile hook execution to identify bottlenecks
2. Use simpler version/metadata sources if possible
3. Cache results across builds
4. Consider using pre-computed values

### Directory Exclusion Issues

**Issue:** Important directory is being excluded

**Solution:**

- Use `include` option to force-include specific paths
- Check `.gitignore` files for conflicting patterns
- Verify VCS boundary configuration

### Metadata Loading from Editable Installs

**Issue:** Metadata not loading correctly in editable mode

**Solution (v1.22.0+):**

- Ensure `PKG-INFO` exists in source distribution
- Check dynamic field declarations
- Verify metadata hook configuration
