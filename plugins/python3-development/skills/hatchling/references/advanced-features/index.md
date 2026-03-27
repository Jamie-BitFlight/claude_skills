---
category: Advanced Build Features
topics: [dynamic-dependencies, force-include, path-rewriting, editable-installs, build-hooks, artifacts, caching]
related: [build-hooks/index.md, target-config/index.md, distributed-artifacts.md]
---

# Advanced Build Features

When assisting users with advanced Hatchling build customization, reference these features to help them implement sophisticated packaging scenarios for complex Python projects, platform-specific builds, and dynamic build-time behavior.

## Topics

- `dynamic-dependencies.md` - Guide users to specify build dependencies at build time using hooks based on platform or environment
- `force-include.md` - Help users include files from arbitrary locations while preserving permissions and resolving symlinks
- `build-data-passing.md` - Show users how to communicate state between build hooks and the overall build process
- `path-rewriting.md` - Guide users in modifying how packages are organized during distribution without restructuring source
- `editable-installs.md` - Help users implement PEP 660 development mode installations for rapid iteration
- `build-context.md` - Show users how to access build environment information and project metadata within hooks
- `distributed-artifacts.md` - Guide users in managing multiple artifact types and understanding output structure
- `case-insensitive-filesystems.md` - Help users handle portability issues from case-insensitive filesystem differences across platforms
- `artifact-directories.md` - Show users how to configure custom artifact output locations for CI/CD integration
