---
category: integration
topics: [pep-compliance, migration, tool-integration, extensions]
related: [pep-standards.md, legacy-setup-py.md, setuptools-compatibility.md, cmake-scikit-build.md, extension-modules.md]
---

# Integration & Compatibility Guide

Reference documentation for helping users understand hatchling's integration with Python packaging standards, legacy tools, and C extension module builders.

## Quick Navigation

- `pep-standards.md` - Coverage of PEP 517, 660, 621, 639, 440, 518
- `legacy-setup-py.md` - Transitioning from setuptools setup.py to hatchling
- `setuptools-compatibility.md` - Interoperability with setuptools
- `cmake-scikit-build.md` - Building C extensions and compiled modules
- `extension-modules.md` - Packaging C/C++/Rust extensions

## Overview

When assisting users with Python packaging, understand that hatchling is a modern, standards-compliant build backend maintaining compatibility with the broader packaging ecosystem while providing a clean configuration interface. Reference this guide when addressing:

1. **PEP Compliance Questions**: How hatchling implements and supports key Python Enhancement Proposals
2. **Migration Assistance**: Helping users move from legacy setup.py patterns to modern pyproject.toml configuration
3. **Tool Integration**: Questions about working with other build systems and tools
4. **Extension Building**: Guidance on supporting compiled code and external dependencies

## Key Features to Reference

- **PEP 517/660 Compliant**: Full support for standard build and editable install interfaces
- **PEP 621/639 Metadata**: Modern project metadata in pyproject.toml format
- **Legacy Compatibility**: Bridges from setup.py without requiring setuptools
- **cmake/scikit-build Support**: Experimental plugin for CMake-based builds
- **Zero-config Defaults**: Works with minimal configuration out of the box

## Reference This Guide When

- Users are setting up hatchling for a new project
- Users are migrating from setuptools to hatchling
- Users need to integrate with build tools (cmake, scikit-build)
- Users are packaging C/C++/Rust extensions
- Users ask how hatchling fits in the Python packaging ecosystem
