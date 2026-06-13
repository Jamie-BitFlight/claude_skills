<p align="center">
  <img src="./assets/hero.png" alt="dasel — one tool for all structured data" width="800" />
</p>

# dasel

Gives Claude the ability to query, modify, and convert structured data files — JSON, YAML, TOML,
XML, CSV, HCL, INI — using [dasel v3](https://github.com/TomWright/dasel), a single tool with a
unified query syntax across all formats.

## Why Install This?

When you ask Claude to work with config files, data files, or XML documents, Claude may:

- Read entire config files into context just to extract one field
- Write a custom Python or jq script for a simple value lookup or update
- Suggest a different tool for each format (jq for JSON, yq for YAML, xmllint for XML)
- Produce format-specific code that does not generalize across your project's file types
- Fail to query large XML files (2MB+) that cannot be loaded into context

This plugin gives Claude knowledge of dasel v3 — its query syntax, exploration workflows,
transformation patterns, and enterprise XML domain knowledge — so Claude uses a single consistent
tool across all structured data formats.

## What You Get

### Claude Improvements

With this plugin installed, Claude will:

**Use a single tool for all structured data formats** — Whether you have a JSON API response, a
YAML Kubernetes manifest, a TOML config, or a Maven `pom.xml`, Claude applies dasel rather than
reaching for a format-specific tool or loading the whole file.

**Extract targeted values without reading full files** — For large config files or XML documents,
Claude runs a focused dasel query instead of loading the entire file into context.

**Apply safe modification patterns** — When updating config values, Claude follows the temp-file
pattern (transform to a temp file, then rename) to avoid truncating files in place.

**Handle large enterprise XML files** — For InstallAnywhere `.iap_xml`, Spring bean XML, Maven
POMs, Hibernate HBM mappings, and Tomcat `web.xml` files (which can exceed 2MB), Claude uses
structural dasel queries rather than attempting to read the file into context.

**Explore unfamiliar structures systematically** — When you hand Claude an unknown config or data
file, Claude follows a discovery sequence (top-level keys → nested keys → array sampling → type
inspection) before making changes.

**Convert between formats** — Claude transforms data from one format to another (JSON to YAML, TOML
to JSON, CSV to JSON, etc.) in a single dasel pipeline.

### Skills

| Skill | What Claude Gains |
| --- | --- |
| `dasel-reference` | Complete v3 selector syntax, all 19 built-in functions, modification patterns, format-specific caveats |
| `data-exploration` | Step-by-step discovery workflow for unfamiliar structured data files |
| `data-transformation` | Safe patterns for in-place updates, format conversion, array batch operations, object construction |
| `setup` | Knowledge to install, update, and troubleshoot the dasel binary across platforms |
| `enterprise-installanywhere` | Query patterns for InstallAnywhere `.iap_xml` installer definitions (65,000+ line files) |
| `enterprise-spring-xml` | Bean discovery, dependency wiring, JMS mapping, property injection in Spring bean XML |
| `enterprise-maven-pom` | Dependency version extraction, groupId/scope filtering, multi-module hierarchy in `pom.xml` |
| `enterprise-hibernate-hbm` | Entity-table bindings, property-column mapping, relationship tracing in Hibernate `.hbm.xml` |
| `enterprise-tomcat-web` | Servlet enumeration, filter chains, listener listing in Tomcat `web.xml` |

### Agents

**data-explorer** — Read-only exploration agent (Haiku). Discovers the structure of any supported
data file, lists keys, samples arrays, and extracts values. Always shows the exact command it ran.
Never modifies files.

**dasel-guide** — Query construction agent (Haiku). Constructs dasel v3 selectors for any supported
format, explains how the selector works, and gives complete copy-pasteable commands. Covers
enterprise XML domain patterns for Spring, Maven, Hibernate, Tomcat, and InstallAnywhere files.

**data-analyst** — Structural analysis agent (Sonnet). Handles multi-file analysis: schema
comparison, pattern detection across large file sets, cross-file diffing, and migration planning.
Writes intermediate results to `/tmp/` and produces reproducible analysis reports.

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install dasel@jamie-bitflight-skills
```

## Install the dasel Binary

After installing the plugin, Claude needs the dasel binary on your system. Run:

```bash
/dasel:setup
```

This installs the latest dasel v3 release from [GitHub Releases](https://github.com/TomWright/dasel/releases),
verifies the SHA256 digest, and places the binary in user-space:

- **Linux / macOS / WSL2**: `~/.local/bin/dasel`
- **Windows**: `%LOCALAPPDATA%\Programs\dasel\dasel.exe`

Supported platforms: Linux x86\_64, Linux ARM64, macOS amd64/ARM64, Windows x64.

Available options:

```bash
/dasel:setup              # Install or update to latest
/dasel:setup --force      # Reinstall even if already at latest
/dasel:setup --dry-run    # Preview what would happen without making changes
```

## Common dasel Commands

```bash
# Read a value
cat config.yaml | dasel -i yaml 'server.port'

# Read from JSON
cat data.json | dasel -i json 'users.[0].name'

# Update a value (safe: writes to temp file then renames)
cat config.yaml | dasel -i yaml --root 'server.host = "newhost"' > config_tmp.yaml && mv config_tmp.yaml config.yaml

# Convert YAML to JSON
cat config.yaml | dasel -i yaml -o json > config.json

# Convert JSON to TOML
cat data.json | dasel -i json -o toml > data.toml

# List all top-level keys
cat config.yaml | dasel -i yaml 'all()'

# Count array elements
cat data.json | dasel -i json 'len(items)'

# Filter array by condition
cat data.json | dasel -i json 'items.filter(type = "admin").map(name)'
```

## Example

**Without this plugin:**

```
You: What database host is configured in config.yaml?
Claude: [reads the entire config.yaml into context]
Claude: The database host is "db.example.com".
```

```
You: Update the server port to 9090 in config.yaml
Claude: [reads config.yaml into context, writes Python to parse and rewrite YAML]
```

**With this plugin:**

```
You: What database host is configured in config.yaml?
Claude: [runs: cat config.yaml | dasel -i yaml 'database.host']
Claude: The database host is "db.example.com".
```

```
You: Update the server port to 9090 in config.yaml
Claude: [cat config.yaml | dasel -i yaml --root 'server.port = 9090' > config_tmp.yaml && mv config_tmp.yaml config.yaml]
Claude: Done. server.port is now 9090.
```

```
You: How many beans are in chaosrouter_beans.xml?
Claude: [cat chaosrouter_beans.xml | dasel -i xml 'len(beans.bean)']
Claude: chaosrouter_beans.xml contains 47 beans.
```

## Requirements

- Claude Code v2.0+
- dasel v3 binary (installed via `/dasel:setup`)
- Python 3.11+ and `uv` (for the install script)

## References

- [dasel GitHub repository](https://github.com/TomWright/dasel)
- [dasel v3 documentation](https://daseldocs.tomwright.me)
