---
name: mkdocs
description: MkDocs documentation project reference covering CLI commands, mkdocs.yml configuration, Material theme setup, and plugin integration. Bundled references include complete CLI parameters, all mkdocs.yml settings with valid values, Material theme customization options, and plugin configs for mkdocstrings, mermaid2, mkdocs-gen-files, mkdocs-literate-nav, and mkdocs-typer2. Use when initializing a MkDocs site, configuring mkdocs.yml, customizing the Material theme, integrating plugins, building static docs from Markdown, or generating API documentation from Python docstrings.
---

# MkDocs

Build and maintain static documentation sites from Markdown with MkDocs and the Material theme.

## Workflow

```mermaid
flowchart TD
    Start([Task received]) --> Q1{Task type?}
    Q1 -->|Site init, build, serve, deploy| CLI[Load reference — cli_reference.md]
    Q1 -->|mkdocs.yml settings, nav, plugins list| Config[Load reference — configuration_reference.md]
    Q1 -->|Theme, colors, navigation UX, search| Theme[Load reference — material_theme_reference.md]
    Q1 -->|API docs, generated pages, diagrams, CLI docs| Plugins[Load reference — plugins_reference.md]
    Q1 -->|CI/CD deployment, GitHub/GitLab Pages| Examples[Load reference — real_world_examples.md]
```

## Reference Files

### CLI Reference

Every `mkdocs` subcommand (`new`, `build`, `serve`, `gh-deploy`), global flags, environment
variables, and exit codes. Load when scaffolding a new project, running a local preview server,
producing a production build, or deploying to GitHub Pages via the CLI.

`references/cli_reference.md`

### Configuration Reference

Every `mkdocs.yml` setting — project info, `nav`, `docs_dir`/`site_dir`, theme block, Markdown
extensions, plugin registration, hooks, and multi-file config inheritance (`INHERIT`) — with valid
values for each. Load when writing or editing `mkdocs.yml`.

`references/configuration_reference.md`

### Material Theme Reference

Material for MkDocs theme configuration — color palettes and dark/light scheme toggling,
typography, navigation features (tabs, sections, instant loading), search, social cards,
versioning (mike), git repository integration, and icons/logos. Load when customizing the
Material theme's look, navigation behavior, or built-in features.

`references/material_theme_reference.md`

### Plugins Reference

Configuration for the plugin ecosystem: `mkdocstrings` (API docs from Python docstrings),
`mkdocs-gen-files` and `mkdocs-literate-nav` (generated pages and nav), `mkdoxy` (Doxygen/C++),
`mkdocs-typer2` (Typer CLI docs), `mermaid2` (diagrams), `termynal` (animated terminal demos), and
`mkdocs-git-latest-changes-plugin`. Load when integrating any of these plugins or generating docs
from source.

`references/plugins_reference.md`

### Real-World Examples

Production MkDocs deployments — GitHub Pages and GitLab Pages CI/CD workflows, active open-source
repositories using MkDocs, and common multi-plugin configuration patterns. Load when setting up a
deployment pipeline or wanting a working reference configuration to adapt.

`references/real_world_examples.md`

## Quick Start

```bash
uv add --dev mkdocs mkdocs-material
uv run mkdocs new .
uv run mkdocs serve      # local preview at http://127.0.0.1:8000
uv run mkdocs build      # static site in site/
uv run mkdocs gh-deploy  # publish to GitHub Pages
```

```yaml
# mkdocs.yml — minimal starting point
site_name: My Project
theme:
  name: material
nav:
  - Home: index.md
```
