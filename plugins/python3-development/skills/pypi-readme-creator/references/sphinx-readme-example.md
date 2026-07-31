# Using sphinx-readme for PyPI READMEs

This guide demonstrates how to use the `sphinx-readme` extension to generate PyPI-compatible README.rst files from Sphinx documentation.

## Overview

`sphinx-readme` is a Sphinx extension that converts reStructuredText documentation into README.rst files that render beautifully on PyPI, GitHub, GitLab, and BitBucket. It handles the conversion of Sphinx-specific directives and roles to standard docutils markup that PyPI supports.

**Key benefit**: Maintain a single source of truth in your Sphinx documentation while automatically generating PyPI-compatible READMEs.

## Installation

Add `sphinx-readme` to your project's documentation dependencies:

```bash
# Using uv
uv add --group docs sphinx-readme

# Or in pyproject.toml
[dependency-groups]
docs = [
    "sphinx>=7.0",
    "sphinx-readme>=1.2",
]
```

## Configuration

### Basic Configuration

Add the extension to your Sphinx `conf.py`:

```python
# conf.py
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_readme",  # Add this
]
```

### Advanced Configuration

Configure source and output files:

```python
# conf.py
readme_config = {
    # Source file (relative to docs/ directory)
    "src_file": "index.rst",
    # Output file (relative to project root)
    "out_file": "../README.rst",
    # Optional: sections to include
    "sections": ["introduction", "installation", "usage"],
}
```

## Source Document Structure

Create a Sphinx documentation file that will serve as the README source. Typically `docs/index.rst` or `docs/readme.rst`.

### Example Source: docs/readme.rst

```rst
============
Project Name
============

.. image:: https://img.shields.io/pypi/v/project-name.svg
   :target: https://pypi.org/project/project-name/
   :alt: PyPI version

.. note::

   This is a note that will be preserved in the generated README.

Overview
========

Your project does amazing things.

Installation
============

.. code-block:: bash

   pip install project-name

Usage
=====

Basic example:

.. code-block:: python

   import project_name

   result = project_name.process("data")
   print(result)

See :doc:`advanced` for more examples.

API Reference
=============

.. automodule:: project_name
   :members:
   :undoc-members:

For complete documentation, see :ref:`api-reference`.

.. _api-reference:

Additional Resources
====================

- :doc:`tutorial`
- :doc:`api/index`
- `GitHub Repository <https://github.com/user/project>`_
```

## Conversion Behavior

### Supported Conversions

**Sphinx cross-references** → **Plain text or standard links**

```rst
# Source (Sphinx)
See :doc:`tutorial` for more details.
Use :ref:`api-reference` for API docs.
The :py:func:`process` function handles data.

# Generated (PyPI-compatible)
See tutorial for more details.
Use api-reference for API docs.
The ``process()`` function handles data.
```

**Sphinx directives** → **Standard docutils**

```rst
# Source (Sphinx)
.. automodule:: project_name
   :members:

# Generated (PyPI-compatible)
# (Content is expanded or removed based on context)
```

**Admonitions** → **Preserved**

```rst
# Both source and generated preserve admonitions
.. note::

   This is important information.

.. warning::

   Be careful with this feature.
```

### What Gets Converted

| Sphinx Feature    | Converted To        | Notes                           |
| ----------------- | ------------------- | ------------------------------- |
| `:doc:` role      | Plain text or link  | Link if URL available           |
| `:ref:` role      | Plain text          | Reference targets removed       |
| `:py:func:`       | Inline code         | Formatted as \`\`function()\`\` |
| `:py:class:`      | Inline code         | Formatted as \`\`ClassName\`\`  |
| `:mod:`           | Inline code         | Formatted as \`\`module\`\`     |
| `.. automodule::` | Removed or expanded | Depends on config               |
| `.. toctree::`    | List of links       | Or removed entirely             |
| Admonitions       | Preserved           | Standard docutils syntax        |
| Code blocks       | Preserved           | With syntax highlighting        |

### What Gets Removed

- Sphinx-only directives (`:py:func:`, `:py:class:`, etc.)
- Intersphinx references
- Autodoc directives (unless configured to expand)
- Internal cross-references
- Build-specific metadata

## Building the README

### Manual Build

Build your Sphinx documentation (README generation happens automatically):

```bash
# Standard Sphinx build
uv run sphinx-build -b html docs/ docs/_build/html

# README.rst is generated at project root
```

### Automated Build in CI/CD

Add README generation to your documentation build workflow:

```yaml
# .github/workflows/docs.yml
name: Documentation

on: [push, pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Install dependencies
        run: uv sync --group docs

      - name: Build documentation
        run: uv run sphinx-build -b html docs/ docs/_build/html

      - name: Verify README generated
        run: test -f README.rst

      - name: Validate README for PyPI
        run: |
          uv build
          uv run --with twine twine check dist/*
```

## Integration with pyproject.toml

Configure your project to use the generated README:

```toml
[project]
name = "project-name"
version = "1.0.0"
description = "One-line description"
readme = "README.rst"  # Generated by sphinx-readme
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatchling.build.targets.wheel]
packages = ["src/project_name"]
```

## Complete Workflow Example

### Project Structure

```
my-project/
├── pyproject.toml
├── README.rst          # Generated by sphinx-readme
├── docs/
│   ├── conf.py         # Sphinx config with sphinx_readme
│   ├── index.rst       # Main documentation
│   ├── readme.rst      # README source (optional)
│   ├── installation.rst
│   ├── usage.rst
│   └── api/
│       └── index.rst
└── src/
    └── my_project/
        └── __init__.py
```

### docs/conf.py

```python
# Sphinx configuration
project = "My Project"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.intersphinx", "sphinx_readme"]

# sphinx-readme configuration
readme_config = {
    "src_file": "readme.rst",  # Dedicated README source
    "out_file": "../README.rst",
}

# Intersphinx (for internal references)
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
```

### docs/readme.rst (Dedicated README Source)

```rst
==========
My Project
==========

.. image:: https://img.shields.io/pypi/v/my-project.svg
   :target: https://pypi.org/project/my-project/

A powerful tool for processing data efficiently.

Installation
============

.. code-block:: bash

   pip install my-project

Quick Start
===========

.. code-block:: python

   from my_project import Processor

   processor = Processor()
   result = processor.run("input")
   print(result)

For detailed usage, see :doc:`usage`.

Features
========

- Fast processing
- Easy to use API
- Comprehensive documentation

See :doc:`installation` for system requirements.

Documentation
=============

Full documentation: https://my-project.readthedocs.io

License
=======

MIT License - see LICENSE file.
```

### Build and Publish

```bash
# 1. Build documentation (generates README.rst)
uv run sphinx-build -b html docs/ docs/_build/html

# 2. Verify README was generated
cat README.rst

# 3. Build package
uv build

# 4. Validate README rendering
uv run --with twine twine check dist/*

# 5. Publish to PyPI
uv run --with twine twine upload dist/*
```

## Troubleshooting

### Issue: README not generated

**Check:**

- Extension added to `conf.py`: `'sphinx_readme'` in `extensions`
- Source file exists: `docs/readme.rst` or configured path
- Sphinx build runs without errors

### Issue: Sphinx roles appear as errors

**Cause**: Sphinx-specific roles in source document

**Solution**: sphinx-readme should convert these automatically. If errors persist, check:

```bash
# Test generated README
uv run --with docutils rst2html.py README.rst /dev/null
```

### Issue: Content missing from generated README

**Cause**: Content might be in sections excluded by config

**Solution**: Check `readme_config` sections setting:

```python
readme_config = {
    "src_file": "readme.rst",
    "out_file": "../README.rst",
    # 'sections': ['intro', 'install'],  # Remove to include all
}
```

### Issue: Links broken in generated README

**Cause**: Internal Sphinx cross-references

**Solution**: Use absolute URLs for external links:

```rst
# Instead of :doc:`tutorial`
See the `tutorial <https://my-project.readthedocs.io/tutorial.html>`_

# Or use simple references
See tutorial_ for details.

.. _tutorial: https://my-project.readthedocs.io/tutorial.html
```

## Best Practices

1. **Separate README source**: Create dedicated `docs/readme.rst` instead of using `index.rst`
2. **Minimal Sphinx features**: Use standard RST directives in README source
3. **Test rendering**: Always validate with `twine check` before publishing
4. **Absolute URLs**: Use full URLs for links to documentation
5. **Simple admonitions**: Stick to standard admonitions (note, warning, tip)
6. **Version control**: Commit generated `README.rst` to track changes
7. **CI validation**: Add README validation to CI pipeline

## Alternative Approach: Manual Maintenance

If `sphinx-readme` doesn't meet your needs, maintain separate README.rst:

**Pros:**

- Full control over content
- No dependency on Sphinx build
- Simpler workflow

**Cons:**

- Duplicate maintenance
- Risk of drift between docs and README
- Manual updates required

**When to use manual approach:**

- README content significantly different from docs
- Sphinx documentation is complex and doesn't translate well
- Project has minimal documentation

## Resources

- [sphinx-readme Documentation](https://sphinx-readme.readthedocs.io/)
- [sphinx-readme on PyPI](https://pypi.org/project/sphinx-readme/)
- [sphinx-readme GitHub](https://github.com/tdkorn/sphinx-readme)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [PyPI README Guide](https://packaging.python.org/guides/making-a-pypi-friendly-readme/)
