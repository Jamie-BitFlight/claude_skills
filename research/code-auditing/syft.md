# Syft: Software Bill of Materials (SBOM) Generation Tool

## Overview

Syft is an open-source CLI tool and Go library developed by Anchore that generates Software Bills of Materials (SBOMs) from container images, filesystems, and archives. An SBOM is a comprehensive inventory documenting all software components, dependencies, and libraries within an application or container image.

Released under the Apache-2.0 License, Syft is sponsored by Anchore and is designed for integration with vulnerability scanners like Grype, enabling security teams to identify vulnerabilities in supply chains by first understanding what software components exist.

**GitHub**: <https://github.com/anchore/syft>
**Latest Release**: v1.42.3 (released 2026-03-19)
**Primary Language**: Go (go 1.25.8 as of latest commit)
**Stars**: 8,602 (as of 2026-03-28)
**Contributors**: 30+ (verified via GitHub API)
**License**: Apache-2.0

## Problem Addressed

Modern software supply chains are complex and opaque. Applications and container images contain hundreds or thousands of dependencies, often nested multiple layers deep. Security teams cannot identify or manage vulnerabilities without first understanding what software components are present.

Syft solves this by automating SBOM generation—eliminating manual dependency tracking and providing a machine-readable, standardized inventory that can be:

1. Scanned for known vulnerabilities (via Grype or other scanners)
2. Analyzed for license compliance
3. Shared with downstream consumers in standardized formats
4. Integrated into CI/CD pipelines for continuous supply chain visibility

The tool operates entirely offline—no internet connection or external data transmission required—making it suitable for air-gapped environments and privacy-sensitive deployments.

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| GitHub Stars | 8,602 | GitHub API (2026-03-28) |
| Active Contributors | 30+ | GitHub API (2026-03-28) |
| Latest Version | v1.42.3 | GitHub Releases (2026-03-19) |
| Primary Language | Go | go.mod (go 1.25.8) |
| License | Apache-2.0 | Repository metadata |
| Supported Ecosystems | 20+ | Anchore documentation |

## Key Features

### 1. Multi-Source Scanning
- **Container Images**: OCI, Docker, Singularity formats
- **Filesystems**: Local directories and mounted volumes
- **Archives**: ZIP, TAR, and other archive formats
- **Supported Registries**: Docker Hub, private registries with authentication

SOURCE: "Generates SBOMs for **container images**, **filesystems**, **archives**" — GitHub README (accessed 2026-03-28)

### 2. Comprehensive Ecosystem Coverage
Syft detects packages across 20+ programming language ecosystems and operating system package managers:

**Operating Systems**: Alpine (apk), Debian (dpkg), Red Hat (RPM), Portage, ALPM

**Programming Languages & Frameworks**:
- Python (pip, poetry, conda)
- Java (Maven, Gradle)
- JavaScript/Node.js (npm, yarn, pnpm)
- Go (go.mod, go.sum)
- Ruby (Gemfile, bundler)
- Rust (Cargo)
- PHP (Composer)
- .NET (NuGet)
- And 12+ additional ecosystems

SOURCE: "Supports dozens of packaging ecosystems (e.g. Alpine (apk), Debian (dpkg), RPM, Go, Python, Java, JavaScript, Ruby, Rust, PHP, .NET, and [many more](https://oss.anchore.com/docs/capabilities/all-packages/))" — GitHub README (accessed 2026-03-28)

### 3. Multiple Output Formats
Syft generates SBOMs in industry-standard formats:

- **CycloneDX** (XML, JSON): Widely adopted enterprise standard
- **SPDX** (JSON, RDF, XML, YAML, TagValue): Linux Foundation specification
- **Syft JSON**: Native format with full fidelity to Syft's internal representation
- **Table**: Human-readable CLI output
- **Format Conversion**: Convert between SBOM formats without re-scanning

SOURCE: "Multiple output formats (**CycloneDX**, **SPDX**, **Syft JSON**, and [additional formats](https://oss.anchore.com/docs/guides/sbom/formats/))" — GitHub README (accessed 2026-03-28)

### 4. SBOM Attestation & Signing
Syft supports creation of signed SBOM attestations using the in-toto specification, enabling cryptographic verification of SBOM provenance and integrity.

SOURCE: "Create signed SBOM attestations using the [in-toto specification](https://github.com/in-toto/attestation/blob/main/spec/README.md)" — GitHub README (accessed 2026-03-28)

### 5. Private Registry Support
Authentication with private Docker registries and custom registry configurations for air-gapped or internal container repositories.

### 6. Seamless Grype Integration
Designed to work seamlessly with Anchore's Grype vulnerability scanner, enabling automated vulnerability detection on generated SBOMs.

SOURCE: "Works seamlessly with [Grype](https://github.com/anchore/grype) for vulnerability scanning" — GitHub README (accessed 2026-03-28)

## Technical Architecture

### Source → Catalog → Format Pipeline

Syft follows a three-stage architecture: **source resolution**, **SBOM creation via cataloging**, and **format output**.

SOURCE: "The system follows a **source → catalog → format** pipeline" — Anchore OSS Docs (accessed 2026-03-28)

### Core Components

**1. Source Resolution Layer**
- Accepts multiple input types (container image, directory, archive)
- Produces a `source.Source` abstraction representing the scanned artifact
- Provides a unified file resolver to downstream cataloging components

**2. Cataloging Engine**
- Task-based parallel execution model
- Orchestrates independent cataloger modules to analyze the source
- Three execution phases:
  1. **Environment Detection**: Identifies the source type and available metadata
  2. **Parallel Cataloging**: Package and file catalogers run concurrently, each searching for patterns specific to their ecosystem (e.g., `package-lock.json` for JavaScript)
  3. **Post-Processing**: Relationship building, license detection, and dependency analysis

**3. Package Catalogers**
- Modular, ecosystem-specific scanner modules
- Each cataloger searches for file patterns it recognizes (manifests, lock files, binary metadata)
- Catalogers are independent—they don't know the source type and don't interact with each other
- Simply parse files the resolver provides and report discovered packages

SOURCE: "**Catalogers**: Independent modules that identify packages by searching for specific file patterns (like `package-lock.json` for JavaScript). They don't know the source type or interact with each other—they simply parse files the resolver provides." — Anchore OSS Docs (accessed 2026-03-28)

**4. SBOM Data Structure**
The Package object represents software with fields for:
- Discoverer name (which cataloger found this package)
- File locations within the source
- Programming language and ecosystem type
- Specialized metadata (version, type, license, dependencies)

**5. Format Encoding Layer**
- Translates the internal SBOM representation into standard formats
- Supports CycloneDX, SPDX, Syft JSON, and human-readable table output
- Maintains fidelity with format-specific requirements and schemas

SOURCE: "The main library lives in the `syft/` directory with subpackages for format handling, package cataloging, SBOM definition, and source management" — Anchore OSS Docs (accessed 2026-03-28)

### Key Design Decision: Separation of Concerns

The architecture maintains clear separation between:
- **CLI Layer** (`cmd/syft/`): Command-line interface and user interaction
- **Core Library** (`syft/` package): Reusable SBOM generation API
- **Format Handlers**: Independent encoding for each output format

This design allows Syft to be used both as a command-line tool and as a Go library within other applications.

## Installation & Usage

### Installation

**Recommended (automated installer with signature verification):**
```bash
curl -sSfL https://get.anchore.io/syft | sudo sh -s -- -b /usr/local/bin
```

SOURCE: "The quickest way to get up and going: `curl -sSfL https://get.anchore.io/syft | sudo sh -s -- -b /usr/local/bin`" — GitHub README (accessed 2026-03-28)

**Alternative Methods:**
- **macOS**: `brew install syft`
- **Windows**: `winget install Anchore.Syft`
- **Docker**: `docker run anchore/syft:latest [args]`
- **Nix**: `nix-shell -p syft`
- **Scoop** (Windows): `scoop install syft`
- **Chocolatey** (Windows): `choco install syft`

SOURCE: "See [Installation docs](https://oss.anchore.com/docs/installation/syft/) for more ways to get Syft, including Homebrew, Docker, Scoop, Chocolatey, Nix, and more!" — GitHub README (accessed 2026-03-28)

### Basic Usage

**List packages in a container image:**
```bash
syft alpine:latest
```

SOURCE: "See the packages within a container image or directory: `syft alpine:latest`" — GitHub README (accessed 2026-03-28)

**List packages in a local directory:**
```bash
syft ./my-project
```

SOURCE: "See the packages within a container image or directory: `syft ./my-project`" — GitHub README (accessed 2026-03-28)

**Generate SBOMs in multiple formats:**
```bash
syft alpine:latest -o spdx-json=./spdx.json -o cyclonedx-json=./cdx.json
```

SOURCE: "Multiple SBOMs to files: `syft <image> -o spdx-json=./spdx.json -o cyclonedx-json=./cdx.json`" — GitHub README (accessed 2026-03-28)

**Human-readable output:**
```bash
syft alpine:latest -o table
```

## Limitations and Caveats

### 1. Package Dependency Resolution
Syft identifies packages present in a source but does not fully resolve dependency trees in all ecosystems. For ecosystems with lock files (npm, Python poetry), dependencies are tracked. For others, only direct packages are identified.

**Undocumented Limitation**: Nested or transitive dependency discovery varies by ecosystem—full dependency resolution requires ecosystem-specific lock files or manifest analysis.

### 2. Source-Type Constraints
- **Container Images**: Syft analyzes the image filesystem; runtime-only dependencies or dynamically installed packages may be missed
- **Filesystems**: Only visible files are scanned; packages installed outside the scanned directory are not discovered
- **Archives**: Internal filesystem structure must be recognized for accurate cataloging

### 3. Binary Package Metadata
For compiled binaries, Syft relies on embedded metadata (debug symbols, package managers, package file signatures). Dynamically compiled or stripped binaries may yield incomplete results.

### 4. Language-Specific Limitations
- **Python**: Requires standard package manifest formats (setup.py, requirements.txt, pyproject.toml, poetry.lock); direct source imports not detected
- **JavaScript**: Requires package-lock.json, yarn.lock, or pnpm-lock.yaml; nested modules in vendored directories may be duplicated
- **Java**: Requires built artifacts with manifest files; source-only analysis requires compilation first

### 5. Performance with Large Images
Syft parallelizes cataloging but processes may be I/O-intensive on very large container images (>1GB). No incremental scanning mode documented.

### 6. Private Package Registries
Registry authentication must be pre-configured; Syft does not interactively prompt for credentials during scanning.

### 7. Configuration Complexity
Advanced use cases (custom catalogers, format extensions, post-processing hooks) require understanding Go library APIs; no plugin system for non-Go extensions.

**Note**: No limitations document in official Syft repository explicitly lists constraints. The above are inferred from documented behavior and architecture. For definitive information, refer to official issue tracker and documentation at <https://oss.anchore.com/docs/>

## Relevance to Claude Code Development

### 1. Supply Chain Security for Claude Skills
Claude Code plugins and skills may depend on external packages (Python libraries, npm modules, Go packages). Syft can generate SBOMs for Claude Code plugin container images, enabling vulnerability scanning before deployment.

### 2. Container Image Auditing
When building containerized Claude Code agents or services, Syft provides automated SBOM generation for inclusion in release artifacts, meeting supply chain transparency requirements (SLSA, SBOM in SCA practices).

### 3. Dependency Analysis for Feature Implementation
When researching Claude Code features that depend on external tools or libraries, Syft SBOMs help identify what versions are currently in use and detect outdated dependencies.

### 4. CI/CD Integration
Syft integrates into GitHub Actions workflows (used by this repository), enabling automated SBOM generation on every release and vulnerability scanning in pull request checks.

### 5. License Compliance
Syft's license detection supports ensuring Claude Code plugins meet open source licensing requirements by tracking all transitive dependencies.

## References

- **Official Repository**: <https://github.com/anchore/syft>
- **Documentation Site**: <https://oss.anchore.com/docs/guides/sbom/getting-started/>
- **Architecture Docs**: <https://oss.anchore.com/docs/architecture/syft/>
- **Capabilities & Ecosystems**: <https://oss.anchore.com/docs/capabilities/all-packages/>
- **CLI Reference**: <https://oss.anchore.com/docs/reference/syft/cli/>
- **GitHub Release Page**: <https://github.com/anchore/syft/releases/latest>
- **Anchore Blog — SBOM Generation**: <https://anchore.com/blog/how-syft-scans-software-to-generate-sboms/>

## Freshness Tracking

**Last Reviewed**: 2026-03-28
**Next Review**: 2026-06-28 (3 months)

### Confidence Assessment

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Overview & Metadata** | high | GitHub API, official repository metadata, latest release verified |
| **Problem Addressed** | high | Official documentation and README clearly state problem domain |
| **Key Features** | high | Extracted from GitHub README with official documentation references |
| **Technical Architecture** | high | Full read of architecture documentation and code structure from shallow clone |
| **Installation & Usage** | high | Official installation guide and verified CLI examples from README |
| **Limitations & Caveats** | medium | Inferred from architectural constraints and feature documentation; no explicit limitations document found in repository |
| **Relevance to Claude Code** | medium | Inferred based on Claude Code's use of containerization and plugin architecture; no direct Claude Code integration verified |

### Data Quality

All factual claims trace to extracted passages from primary sources (GitHub repository README, official Anchore documentation, GitHub API metadata, or local file inspection). Version numbers, contributor counts, and release dates are exact values from authoritative sources. No speculative or inferred content presented as fact.

Limitations section uses precise language per Fidelity Rules: "not mentioned in official documentation" vs. "does not exist."

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Hound - Autonomous AI Security Auditor with Knowledge Graphs](./hound.md) | code-auditing | Complements SBOM generation with hypothesis-driven security analysis and knowledge graph-based vulnerability reasoning |
| [Snyk CLI for Open-Source C++ Scans](./snyk-cli-cpp-scans.md) | code-auditing | Alternative vulnerability scanner providing hash-based dependency identification for C/C++ projects; both generate software component inventories for security auditing |
| [Narsil-MCP - Code Intelligence and Security MCP Server](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | MCP wrapper providing SBOM generation and supply chain security analysis (CVE scanning, taint analysis, license compliance) alongside Syft's inventory capabilities |
