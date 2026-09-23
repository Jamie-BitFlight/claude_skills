---
title: 'shiv: Python Zipapp Builder for Self-Contained Applications'
library_name: shiv
pypi_package: shiv
category: packaging-distribution
python_compatibility: 3.8+
last_updated: '2025-11-02'
official_docs: https://shiv.readthedocs.io
official_repository: https://github.com/linkedin/shiv
maintenance_status: active
---

# shiv

## Overview

shiv is a command-line utility for building fully self-contained Python zipapps as outlined in PEP 441, but with all their dependencies included. It is developed and maintained by LinkedIn and provides a fast, easy way to distribute Python applications.

**Official Repository**: @<https://github.com/linkedin/shiv> **Official Documentation**: @<https://shiv.readthedocs.io/en/latest/> **PyPI Package**: @<https://pypi.org/project/shiv/>

## Core Purpose

### Problem Statement

shiv solves the challenge of distributing Python applications with all their dependencies bundled into a single executable file without requiring complex build processes or compilation.

**What problems does shiv solve?**

1. **Dependency bundling**: Packages your application and all its dependencies into a single `.pyz` file
2. **Simple distribution**: Creates executable files that can be shared and run on systems with compatible Python installations
3. **No compilation required**: Unlike PyInstaller or cx_Freeze, shiv does not compile Python code to binaries
4. **Fast deployment**: Built on Python's standard library zipapp module (PEP 441) for minimal overhead
5. **Reproducible builds**: Creates deterministic outputs for version control and deployment

**When you would be "reinventing the wheel" without shiv:**

- Building custom scripts to bundle dependencies with applications
- Manually creating zipapp structures with dependencies
- Writing deployment automation for Python CLI tools
- Managing virtual environments on deployment targets

## When to Use shiv vs Alternatives

### Use shiv When

- Deploying Python applications to controlled environments where Python is already installed
- Building CLI tools for internal distribution within organizations
- Creating portable Python applications for Linux/macOS/WSL environments
- You need fast build times and simple deployment workflows
- Your application is pure Python or has platform-specific compiled dependencies that can be installed per-platform
- You want to leverage the PEP 441 zipapp standard

### Use PyInstaller/cx_Freeze When

- Distributing to end-users who do not have Python installed
- Creating true standalone executables with embedded Python interpreter
- Targeting Windows environments without Python installations
- Building GUI applications for general consumer distribution
- You need absolute portability without Python runtime dependencies

### Use wheel/sdist When

- Publishing libraries to PyPI
- Developing packages meant to be installed via pip
- Creating reusable components rather than standalone applications
- Working in environments where pip/package managers are the standard

## Decision Matrix

<eg>
┌─────────────────────────┬──────────┬─────────────┬───────────┐
│ Requirement             │ shiv     │ PyInstaller │ wheel     │
├─────────────────────────┼──────────┼─────────────┼───────────┤
│ Python required         │ Yes      │ No          │ Yes       │
│ Build speed             │ Fast     │ Slow        │ Fast      │
│ Bundle size             │ Small    │ Large       │ Smallest  │
│ Cross-platform binary   │ No       │ Yes         │ No        │
│ PEP 441 compliant       │ Yes      │ No          │ N/A       │
│ Installation required   │ No       │ No          │ Yes (pip) │
│ C extension support     │ Limited* │ Full        │ Full      │
└─────────────────────────┴──────────┴─────────────┴───────────┘

- C extensions work but are platform-specific (not cross-compatible)
</eg>

## Python Version Compatibility

- **Minimum Python version**: 3.8 (per setup.cfg @<https://github.com/linkedin/shiv/blob/main/setup.cfg>)
- **Tested versions**: 3.8, 3.9, 3.10, 3.11
- **Python 3.11+ compatibility**: Fully compatible
- **Python 3.12-3.14 status**: Expected to work (relies on standard library zipapp module)
- **PEP 441 dependency**: Requires Python 3.5+ (PEP 441 introduced in Python 3.5)

### Installation

```bash
# From PyPI
pip install shiv

# From source
git clone https://github.com/linkedin/shiv.git
cd shiv
python3 -m pip install -e .
```

## Core Concepts

### PEP 441 zipapp Integration

shiv builds on Python's standard library `zipapp` module (PEP 441) which allows creating executable ZIP files. The key enhancement is automatic dependency installation and bundling.

**How it works:**

1. Creates a temporary directory structure
2. Installs specified packages and dependencies using pip
3. Packages everything into a ZIP file
4. Adds a shebang line to make it executable
5. Extracts dependencies to `~/.shiv/` cache on first run

### Deployment Patterns

**Single-file distribution:**

```bash
# Build once
shiv -c myapp -o myapp.pyz myapp

# Distribute myapp.pyz
# Users run: ./myapp.pyz
```

**Library bundling:**

```bash
# Bundle multiple packages
shiv -o toolkit.pyz requests click ruamel.yaml
```

**From requirements.txt:**

```bash
shiv -r requirements.txt -o app.pyz -c app
```

## Usage Examples

### Basic Command-Line Tool

Create a standalone executable of flake8:

```bash
shiv -c flake8 -o ~/bin/flake8 flake8
```

**Explanation:**

- `-c flake8`: Specifies the console script entry point
- `-o ~/bin/flake8`: Output file location
- `flake8`: Package to install from PyPI

**Running:**

```bash
~/bin/flake8 --version
# Output: 3.7.8 (mccabe: 0.6.1, pycodestyle: 2.5.0, pyflakes: 2.1.1)
```

### Interactive Python Environment

Create an interactive executable with libraries:

```bash
shiv -o boto.pyz boto
```

**Running:**

```bash
./boto.pyz
# Opens Python REPL with boto available
>>> import boto
>>> boto.__version__
'2.49.0'
```

### Real-World Example: CLI Application Distribution

From @<https://github.com/scs/smartmeter-datacollector/blob/master/README.md>:

```bash
# Build a self-contained zipapp using shiv
poetry run poe build_shiv
```

This creates a `.pyz` file containing the smartmeter-datacollector application and all dependencies, distributable as a single file.

### Custom Python Interpreter Path

```bash
shiv -c myapp -o myapp.pyz -p "/usr/bin/env python3" myapp
```

The `-p` flag specifies the shebang line for the executable.

### Building from Local Package

```bash
# From current directory with setup.py or pyproject.toml
shiv -c myapp -o myapp.pyz .
```

### Advanced: Building shiv with shiv

From @<https://github.com/linkedin/shiv/blob/main/README.md>:

```bash
python3 -m venv .
source bin/activate
pip install shiv
shiv -c shiv -o shiv shiv
```

This creates a self-contained shiv executable using shiv itself, demonstrating bootstrapping capability.

## Integration Patterns

### CI/CD Pipeline Integration

```yaml
# Example GitHub Actions workflow
- name: Build application zipapp
  run: |
    pip install shiv
    shiv -c myapp -o dist/myapp.pyz myapp

- name: Upload artifact
  uses: actions/upload-artifact@v3
  with:
    name: myapp-zipapp
    path: dist/myapp.pyz
```

### Makefile Integration

From @<https://github.com/JanssenProject/jans/blob/main/jans-cli-tui/Makefile>:

```makefile
zipapp:
	@echo "Building zipapp with shiv"
	shiv -c jans_cli_tui -o jans_cli_tui.pyz .
```

### Poetry Integration

In `pyproject.toml`:

```toml
[tool.poe.tasks]
build_shiv = "shiv -c myapp -o dist/myapp.pyz ."
```

Run with: `poetry run poe build_shiv`

## Platform-Specific Considerations

### Linux/macOS

- **Shebang support**: Full support for `#!/usr/bin/env python3`
- **Permissions**: Requires `chmod +x` for executable files
- **Cache location**: `~/.shiv/` for dependency extraction

### Windows

- **Shebang limitations**: Windows does not natively support shebangs
- **Execution**: Must run as `python myapp.pyz`
- **Alternative**: Use Python launcher: `py myapp.pyz`
- **Cache location**: `%USERPROFILE%\.shiv\`

### Cross-Platform Gotchas

**From @<https://github.com/linkedin/shiv/blob/main/README.md>:**

> Zipapps created with shiv are not guaranteed to be cross-compatible with other architectures. For example, a pyz file built on a Mac may only work on other Macs, likewise for RHEL, etc. This usually only applies to zipapps that have C extensions in their dependencies. If all your dependencies are pure Python, then chances are the pyz will work on other platforms.

**Recommendation**: Build platform-specific executables for production deployments when using packages with C extensions.

## Cache Management

shiv extracts dependencies to `~/.shiv/` (or `SHIV_ROOT`) on first run. This directory can grow over time.

**Cleanup:**

```bash
# Remove all cached extractions
rm -rf ~/.shiv/

# Set custom cache location
export SHIV_ROOT=/tmp/shiv_cache
./myapp.pyz
```

## When NOT to Use shiv

### Scenarios Where Alternatives Are Better

1. **Windows-only distribution without Python**: Use PyInstaller or cx_Freeze for embedded interpreter
2. **End-user applications**: Users expect double-click executables, not Python scripts
3. **Cross-platform binaries from single build**: shiv requires platform-specific builds for C extensions
4. **Library distribution**: Use wheel/sdist and publish to PyPI
5. **Complex GUI applications**: PyInstaller has better support for frameworks like PyQt/Tkinter
6. **Environments without Python**: shiv requires a compatible Python installation on the target system

## Common Use Cases

### Internal Tool Distribution

**Example**: DevOps teams distributing CLI tools

```bash
# Build deployment tool
shiv -c deploy -o deploy.pyz deploy-tool

# Distribute to team members
# Everyone runs: ./deploy.pyz --environment prod
```

### Lambda/Cloud Function Packaging

While AWS Lambda has native Python support, shiv can simplify dependency management:

```bash
shiv -o lambda_function.pyz --no-binary :all: boto3 requests
```

### Portable Development Environments

Create portable toolchains:

```bash
# Bundle linting tools
shiv -o lint.pyz black pylint mypy flake8

# Bundle testing tools
shiv -o test.pyz pytest pytest-cov hypothesis
```

## Real-World Projects Using shiv

Based on GitHub search results (@<https://github.com/search?q=shiv+zipapp>):

1. **JanssenProject/jans** - IAM authentication server

   - Uses shiv to build CLI and TUI applications
   - Makefile integration for zipapp builds
   - @<https://github.com/JanssenProject/jans>

2. **scs/smartmeter-datacollector** - Smart meter data collection

   - Poetry integration with custom build command
   - Self-contained distribution for Raspberry Pi
   - @<https://github.com/scs/smartmeter-datacollector>

3. **praetorian-inc/noseyparker-explorer** - Security scanning results explorer

   - TUI application distributed via shiv
   - @<https://github.com/praetorian-inc/noseyparker-explorer>

4. **ClericPy/zipapps** - Alternative zipapp builder
   - Built as comparison/alternative to shiv
   - @<https://github.com/ClericPy/zipapps>

## Additional Resources

### Official Documentation

- PEP 441 - Improving Python ZIP Application Support: @<https://www.python.org/dev/peps/pep-0441/>
- Python zipapp module: @<https://docs.python.org/3/library/zipapp.html>
- shiv documentation: @<https://shiv.readthedocs.io/en/latest/>
- Lincoln Loop blog: "Dissecting a Python Zipapp Built with Shiv": @<https://lincolnloop.com/insights/dissecting-python-zipapp-built-shiv/>

### Community Resources

- Real Python tutorial: "Python's zipapp: Build Executable Zip Applications": @<https://realpython.com/python-zipapp/>
- jhermann blog: "Bundling Python Dependencies in a ZIP Archive": @<https://jhermann.github.io/blog/python/deployment/2020/03/08/ship_libs_with_shiv.html>

### Comparison Articles

- PyOxidizer comparisons (includes shiv): @<https://pyoxidizer.readthedocs.io/en/stable/pyoxidizer_comparisons.html>
- Hacker News discussion: @<https://news.ycombinator.com/item?id=26832809>

## Technical Implementation Details

### Dependencies

From @<https://github.com/linkedin/shiv/blob/main/setup.cfg>:

```ini
[options]
install_requires =
  click>=6.7,!=7.0
  pip>=9.0.3
  setuptools
python_requires = >=3.8
```

shiv has minimal dependencies, relying primarily on standard library components plus click for CLI and pip for dependency resolution.

### Entry Points

shiv provides two console scripts:

1. `shiv`: Main build tool
2. `shiv-info`: Inspect zipapp metadata

### Build Backend

Uses setuptools with pyproject.toml (PEP 517/518 compliant):

```toml
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

## Maintenance and Support

- **License**: BSD 2-Clause License
- **Maintainer**: LinkedIn (@<https://github.com/linkedin>)
- **GitHub Stars**: 1,884+ (as of October 2025)
- **Active Development**: Yes (last updated October 2025)
- **Open Issues**: 66 (as of October 2025)
- **Community**: Active issue tracker and pull request reviews

## Security Considerations

1. **Code signing**: shiv does not sign executables; implement external signing if required
2. **Dependency verification**: shiv uses pip, which respects pip's security model
3. **Cache security**: `~/.shiv/` directory contains extracted dependencies; ensure proper permissions
4. **Supply chain**: Verify package sources before building zipapps

## Performance Characteristics

- **Build time**: Fast (seconds for typical applications)
- **Startup overhead**: First run extracts to cache (one-time cost), subsequent runs are instant
- **Runtime performance**: Native Python performance (no interpretation overhead)
- **File size**: Smaller than PyInstaller bundles (no embedded interpreter)

## Troubleshooting

### Common Issues

**Issue**: "shiv requires Python >= 3.8" **Solution**: Upgrade Python or use an older shiv version

**Issue**: "ImportError on different platform" **Solution**: Rebuild zipapp on target platform for C extension dependencies

**Issue**: "Permission denied" **Solution**: `chmod +x myapp.pyz`

**Issue**: "SHIV_ROOT fills up disk" **Solution**: Clean cache: `rm -rf ~/.shiv/` or set `SHIV_ROOT` to tmpfs

## Conclusion

shiv is an excellent choice for distributing Python applications in controlled environments where Python is available. It provides a simple, fast, and standards-based approach to application packaging without the complexity of binary compilation. For internal tools, CLI utilities, and cloud function packaging, shiv offers an ideal balance of simplicity and functionality.

**Quick decision guide:**

- Need standalone binary with no Python? Use PyInstaller/cx_Freeze
- Distributing library? Use wheel + PyPI
- Internal tool with Python available? Use shiv
- Cross-platform GUI app? Use PyInstaller
- Cloud function deployment? Consider shiv or native platform tools
