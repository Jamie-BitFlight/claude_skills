---
title: "Snyk CLI for Open-Source C++ Scans"
research_date: "2026-02-23"
source_url: "https://docs.snyk.io/supported-languages/supported-languages-list/c-c++/snyk-cli-for-open-source-c++-scans"
github_url: "<https://github.com/snyk/snyk> (CLI source)"
documentation_url: "https://docs.snyk.io/supported-languages/supported-languages-list/c-c++"
version_at_research: "Current (last updated ~June 2025 per docs)"
license: "Proprietary — Commercial (subscription required; free tier available for open-source projects)"
last_verified: "2026-02-23"
version_at_verification: "Current (docs last updated ~June 2025)"
next_review: "2026-05-23"
---

## Overview

Snyk CLI provides open-source vulnerability scanning for C/C++ projects that do not use a traditional package manager. Using the `--unmanaged` flag, Snyk converts all source files in a directory to cryptographic hashes, sends them to the Snyk scan server, and matches them against a database of known open-source library releases. This approach allows dependency identification and CVE reporting directly from vendored or in-tree source code, without needing a lockfile or manifest.

**Core Value Proposition**: Identify known vulnerabilities in vendored C/C++ dependencies from their source code alone, with confidence scoring that reflects how closely the scanned files match the Snyk database, enabling security teams to audit codebases that have no package manager metadata.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| C/C++ projects lack standard package managers, so traditional SCA tools cannot find dependencies | `snyk test --unmanaged` hashes source files and matches them against known library releases without needing a manifest |
| Vendored or in-tree dependencies are invisible to registry-based scanners | Source-code hashing identifies libraries even when embedded directly in the repo |
| No persistent tracking of C/C++ dependency vulnerabilities | `snyk monitor --unmanaged` uploads a snapshot to the Snyk Web UI for ongoing notifications |
| Dependency versions in C/C++ are hard to determine without metadata | Confidence scoring (0–1) shows how closely source files match a specific library version in the database |
| Archive-bundled dependencies cannot be scanned by most tools | `--max-depth` flag enables recursive extraction and scanning of zip, tar, and tar.gz archives |

---

## Key Features

### Unmanaged Dependency Scanning

- **Hash-based identification**: All files in the scanned directory are converted to irreversible hashes and sent to the Snyk server for matching
- **PURL output**: Identified dependencies are reported as Package URLs (`pkg:generic/curl@7.29.0?download_url=...`)
- **Confidence scoring**: Each identified dependency carries a confidence value from `0` (poor match) to `1` (all files matched exactly)
- **Only official releases/tags tracked**: Arbitrary commits are not indexed — only tagged releases from GitHub or published tarballs

### Vulnerability Reporting

- **CVE mapping**: Matched dependencies are linked to known CVEs in the Snyk Vulnerability Database
- **Severity filtering**: `--severity-threshold=<low|medium|high|critical>` limits output to actionable findings
- **JSON output**: `--json` and `--json-file-output` produce machine-readable results for CI integration
- **Continuous monitoring**: `snyk monitor --unmanaged` creates a project in the Snyk Web UI with email alerts for newly disclosed vulnerabilities

### Archive Extraction

- **Supported formats**: zip-like archives, tar, tar with gzip compression
- **Recursive extraction**: `--max-depth=<N>` controls how many levels deep archives are extracted before scanning

### Dependency Inspection

- `--print-deps`: Lists all identified dependencies with version and download URL
- `--print-dep-paths`: Shows which source files contributed to each dependency match alongside confidence
- Both flags work with `snyk test --unmanaged` for local analysis without uploading results

### Data Collection (Privacy Considerations)

- **File hashes**: All scanned files are converted to irreversible hashes before transmission — source code is never sent
- **Relative paths**: Paths relative to the scanned directory are sent alongside hashes for identification purposes (e.g., `./project/vendor/bzip2-1.0.6/blocksort.c`)

---

## Technical Architecture

<eg>
Local Filesystem (C/C++ source tree)
        |
        v
[Snyk CLI: snyk test --unmanaged]
        |
        | 1. Convert all files → irreversible hashes
        | 2. Collect relative file paths
        v
[Snyk Scan Server]
        |
        | 3. Compute dependency candidates from hash list
        | 4. Query Snyk Vulnerability Database
        v
[Results Returned to CLI]
        |
        | 5. Link dependencies → CVEs
        | 6. Apply severity thresholds
        v
[Output: JSON / console / Web UI snapshot]
</eg>

**Confidence Scoring**: Calculated as the ratio of matched files to expected files for the candidate library release. A confidence of `1.000` means every expected source file was found in the scanned directory. Modifications to vendored source code reduce confidence and may result in misidentification.

**Release Tracking**: Only dependencies with an official release or tag (on GitHub or as a published tarball) are indexed. For C/C++ unmanaged scans, this requires a GitHub tag or official release on the dependency's repository.

---

## Installation & Usage

```bash
# Install Snyk CLI via npm
npm install -g snyk

# Or via Homebrew
brew install snyk-cli

# Authenticate
snyk auth
```

```bash
# Scan a C/C++ project directory (unmanaged dependencies)
cd /path/to/c-project
snyk test --unmanaged

# Show identified dependencies with PURL and confidence
snyk test --unmanaged --print-deps

# Show which files matched each dependency
snyk test --unmanaged --print-dep-paths

# Output machine-readable JSON for CI pipelines
snyk test --unmanaged --json

# Scan archives recursively (up to 3 levels deep)
snyk test --unmanaged --max-depth=3

# Filter by severity
snyk test --unmanaged --severity-threshold=high

# Upload snapshot for continuous monitoring
snyk monitor --unmanaged --project-name=my-c-project

# Full set of supported flags for snyk test --unmanaged
# --org=<ORG_ID>
# --json
# --json-file-output=<OUTPUT_FILE_PATH>
# --remote-repo-url=<URL>
# --severity-threshold=<low|medium|high|critical>
# --max-depth
# --print-dep-paths
```

---

## Relevance to Claude Code Development

### Applications

- **C/C++ security scanning in CI**: Integrate `snyk test --unmanaged --json` into GitHub Actions workflows to surface CVEs in vendored C++ dependencies during PRs
- **Plugin security auditing**: Use in a Claude Code skill to audit C/C++ plugin dependencies before release
- **Compliance reporting**: `snyk monitor --unmanaged` provides a persistent inventory of C/C++ open-source components for license and compliance audits

### Patterns Worth Adopting

- **Hash-based dependency fingerprinting**: The technique of identifying libraries purely from file content hashes (without manifest metadata) could inform agent skills that analyze codebases with missing or incomplete dependency declarations
- **Confidence-scored identification**: Reporting confidence levels alongside findings is a useful pattern for any tool that performs approximate matching — agents could surface a confidence score when providing uncertain analysis results
- **Unmanaged scanning concept**: The `--unmanaged` pattern is applicable beyond C/C++ — any language where dependencies are vendored without a lockfile could benefit from this approach

### Integration Opportunities

- **Claude Code skill**: Create a `snyk-cpp-audit` skill that wraps `snyk test --unmanaged --json` and parses output to provide actionable CVE summaries with fix guidance
- **CI/CD pipeline step**: Add as a quality gate in the repository's `.github/workflows/` alongside existing code quality checks
- **Competitive Analysis**: Complements static analysis tools (e.g., Hound, CodeQL) by adding known-vulnerability database matching; does not perform SAST or logic-error detection

---

## References

- [Snyk CLI for open-source C++ scans (official docs)](https://docs.snyk.io/supported-languages/supported-languages-list/c-c++/snyk-cli-for-open-source-c++-scans) (accessed 2026-02-23)
- [C/C++ language support overview](https://docs.snyk.io/supported-languages/supported-languages-list/c-c++) (accessed 2026-02-23)
- [snyk test --unmanaged CLI reference](https://docs.snyk.io/developer-tools/snyk-cli/commands/test#unmanaged) (accessed 2026-02-23)
- [snyk monitor --unmanaged CLI reference](https://docs.snyk.io/developer-tools/snyk-cli/commands/monitor#unmanaged) (accessed 2026-02-23)
- [Snyk Vulnerability Database](https://security.snyk.io) (accessed 2026-02-23)
- [Snyk CLI GitHub repository](https://github.com/snyk/snyk) (accessed 2026-02-23)

---
