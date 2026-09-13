---
name: jscpd - Copy/Paste Detector for Source Code
description: jscpd is a copy/paste detector for programming source code supporting 150+ programming languages and document formats. It implements the Rabin-Karp algorithm for efficient duplication detection and...
license: MIT
metadata:
  topic: jscpd
  category: developer-tools
  source_url: https://jscpd.dev/
  github: kucherenko/jscpd
  version: "v3.5.10"
  verified: "2026-01-31"
  next_review: "2026-04-30"
---

## Overview

jscpd is a copy/paste detector for programming source code supporting 150+ programming languages and document formats. It implements the Rabin-Karp algorithm for efficient duplication detection and provides multiple output formats for CI/CD integration. The tool identifies code duplication as technical debt and helps maintain code quality through configurable thresholds and reporting.

**Core Value Proposition**: Detect and quantify copy/paste code duplication across 150+ languages with CI-friendly thresholds, git blame integration, and multiple report formats (HTML, JSON, XML, SARIF).

---

## Problem Addressed

| Problem                                                        | How jscpd Solves It                                                |
| -------------------------------------------------------------- | ------------------------------------------------------------------ |
| Copy/paste code creates technical debt                         | Detects duplicated blocks across 150+ languages                    |
| Manual duplication audits are time-consuming                   | Automated scanning with configurable thresholds                    |
| Duplication sources are hard to identify                       | Git blame integration shows authors and dates of duplicated blocks |
| Need CI/CD integration for quality gates                       | Threshold-based exit codes, SARIF output for GitHub Actions        |
| Different projects need different sensitivity                  | Three detection modes (strict, mild, weak) with token/line limits  |
| Need to exclude legitimate duplications (imports, boilerplate) | Ignore blocks with `jscpd:ignore-start/end` comments               |
| Large repositories cause memory issues                         | LevelDB store option for big repositories                          |

---

## Key Statistics (as of January 31, 2026)

| Metric               | Value                                                    |
| -------------------- | -------------------------------------------------------- |
| GitHub Stars         | 5,268                                                    |
| Forks                | 223                                                      |
| Open Issues          | 72                                                       |
| Primary Language     | TypeScript                                               |
| Created              | May 2013                                                 |
| Last Updated         | January 28, 2026                                         |
| Latest Version       | v3.5.10                                                  |
| NPM Weekly Downloads | ~75,000                                                  |
| Supported Formats    | 150+                                                     |
| Notable Users        | GitHub Super Linter, Mega-Linter, Codacy, Code-Inspector |

---

## Key Features

### 1. Multi-Language Support (150+ Formats)

- **Programming Languages**: JavaScript, TypeScript, Python, Java, C/C++, Go, Rust, Ruby, PHP, C#, Kotlin, Swift, Scala, Elixir, and 100+ more
- **Markup & Config**: HTML, CSS, SCSS, JSON, YAML, XML, Markdown, Docker, Nginx, etc.
- **Embedded Code Detection**: Detects duplications in `<script>` and `<style>` blocks within HTML
- **Custom Extensions**: Map custom file extensions to existing formats via `--formats-exts`

### 2. Detection Algorithm (Rabin-Karp)

- **Token-Based Matching**: Compares code at token level, not just text
- **Configurable Sensitivity**:
  - `--min-tokens` (default 50): Minimum tokens for a block to be considered
  - `--min-lines` (default 5): Minimum lines for a block
  - `--max-lines` (default 1000): Skip files larger than threshold
- **Detection Modes**:
  - `strict`: All symbols as tokens
  - `mild`: Skip newlines and empty symbols
  - `weak`: Skip newlines, empty symbols, and comments

### 3. Reporting System

- **Console Reporters**:
  - `console`: Summary of clones
  - `consoleFull`: Includes code blocks
  - `verbose`: Debug information
- **File Reporters**:
  - `json`: Machine-readable JSON output
  - `xml`: PMD-CPD compatible XML format
  - `csv`: Spreadsheet-compatible
  - `markdown`: Documentation-friendly
  - `html`: Interactive HTML report with code highlighting
  - `sarif`: SARIF format for GitHub Security tab integration
- **Badge Reporter**: Generate SVG badges for README files

### 4. CI/CD Integration

- **Threshold-Based Exit**: `--threshold 10` fails if duplication exceeds 10%
- **Custom Exit Codes**: `--exitCode 1` for CI failure on detection
- **Silent Mode**: `--silent` for minimal output in pipelines
- **Absolute Paths**: `--absolute` for CI-friendly file references

### 5. Git Integration

- **Blame Information**: `--blame` shows authors and dates of duplicated code
- **Gitignore Support**: Respects `.gitignore` patterns
- **Symlink Handling**: `--noSymlinks` option

### 6. Ignore Mechanisms

- **Comment Markers**: `/* jscpd:ignore-start */` ... `/* jscpd:ignore-end */`
- **Glob Patterns**: `--ignore "**/*.min.js,**/*.map"`
- **Regex Patterns**: `--ignore-pattern "import.*from\s*'.*'"`

### 7. Architecture (Monorepo Packages)

| Package                 | Purpose                                   |
| ----------------------- | ----------------------------------------- |
| `jscpd`                 | Main CLI and API                          |
| `jscpd-server`          | HTTP API server for duplication detection |
| `@jscpd/core`           | Core algorithm (minimal dependencies)     |
| `@jscpd/finder`         | File-based duplication finder             |
| `@jscpd/tokenizer`      | Source code tokenization                  |
| `@jscpd/leveldb-store`  | LevelDB store for large repositories      |
| `@jscpd/html-reporter`  | HTML report generation                    |
| `@jscpd/badge-reporter` | SVG badge generation                      |

---

## Technical Architecture

<eg>
Source Files
      |
      v
+------------------------------------------+
|              jscpd CLI / API              |
|  +------------------------------------+  |
|  |         File Discovery             |  |
|  |  - Glob patterns                   |  |
|  |  - Gitignore integration           |  |
|  |  - Format detection                |  |
|  +------------------------------------+  |
|                  |                       |
|                  v                       |
|  +------------------------------------+  |
|  |         Tokenizer                  |  |
|  |  - Language-aware parsing          |  |
|  |  - Comment/whitespace handling     |  |
|  |  - Mode-based filtering            |  |
|  +------------------------------------+  |
|                  |                       |
|                  v                       |
|  +------------------------------------+  |
|  |     Rabin-Karp Detection           |  |
|  |  - Hash-based matching             |  |
|  |  - Min tokens/lines filtering      |  |
|  |  - Clone grouping                  |  |
|  +------------------------------------+  |
|                  |                       |
|                  v                       |
|  +------------------------------------+  |
|  |         Store                      |  |
|  |  - Memory (default)                |  |
|  |  - LevelDB (large repos)           |  |
|  +------------------------------------+  |
|                  |                       |
|                  v                       |
|  +------------------------------------+  |
|  |         Reporters                  |  |
|  |  - Console / JSON / XML / HTML     |  |
|  |  - SARIF / CSV / Markdown          |  |
|  |  - Badge generation                |  |
|  +------------------------------------+  |
+------------------------------------------+
      |
      v
Reports + Exit Code (threshold-based)
</eg>

---

## Installation & Usage

### Installation Options

```bash
# NPM (global)
npm install -g jscpd

# NPX (no install)
npx jscpd /path/to/source

# Yarn
yarn global add jscpd

# pnpm
pnpm add -g jscpd
```

### Basic Usage

```bash
# Scan directory
jscpd /path/to/source

# Scan with pattern
jscpd --pattern "src/**/*.js"

# With threshold for CI
jscpd --threshold 10 --exitCode 1 /path/to/source

# Generate HTML report
jscpd -r html -o ./report /path/to/source

# Silent mode with specific formats
jscpd --silent --format "javascript,typescript" /path/to/source

# With git blame
jscpd --blame /path/to/source
```

### Configuration File (.jscpd.json)

```json
{
  "threshold": 10,
  "reporters": ["html", "console", "badge"],
  "ignore": [
    "**/__snapshots__/**",
    "**/*.min.js",
    "**/node_modules/**",
    "**/dist/**"
  ],
  "format": ["javascript", "typescript", "css"],
  "absolute": true,
  "gitignore": true,
  "minTokens": 50,
  "minLines": 5,
  "mode": "mild"
}
```

### package.json Configuration

```json
{
  "jscpd": {
    "threshold": 10,
    "reporters": ["html", "console"],
    "ignore": ["**/__snapshots__/**"],
    "absolute": true
  }
}
```

### Programming API

```typescript
import { detectClones } from "jscpd";

const clones = await detectClones({
  path: ["./src"],
  minTokens: 50,
  minLines: 5,
  mode: "mild",
  silent: true,
});

console.log(`Found ${clones.length} duplications`);
```

### Server Mode (jscpd-server)

```bash
# Install and start server
npm install -g jscpd-server
jscpd-server

# Check code via API
curl -X POST http://localhost:3000/api/check \
  -H "Content-Type: application/json" \
  -d '{
    "code": "function hello() { console.log(\"hello\"); }",
    "format": "javascript"
  }'
```

---

## Ignore Block Examples

### JavaScript/TypeScript

```javascript
/* jscpd:ignore-start */
import lodash from 'lodash';
import React from 'react';
import { User } from './models';
/* jscpd:ignore-end */
```

### HTML

```html
<!--
// jscpd:ignore-start
-->
<meta name="theme-color" content="#cb3837"/>
<link rel="stylesheet" href="vendor.css"/>
<!--
// jscpd:ignore-end
-->
```

### Python

```python
# jscpd:ignore-start
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
# jscpd:ignore-end
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Code Quality Skills**: Create skills that run jscpd to detect duplications before commits or PRs
2. **Refactoring Suggestions**: Use duplication reports to identify refactoring candidates
3. **Technical Debt Tracking**: Monitor duplication percentage over time in projects
4. **Pre-Commit Hooks**: Integrate via pre-commit/prek to prevent new duplications

### Patterns Worth Adopting

1. **Threshold-Based Quality Gates**: Apply similar threshold patterns to other code quality metrics
2. **Multi-Format Detection**: The 150+ language support demonstrates comprehensive file type handling
3. **Ignore Block Pattern**: The `jscpd:ignore-start/end` pattern can be adopted for other tools
4. **Token-Based Analysis**: Token-level comparison is more accurate than line-level for code analysis
5. **Modular Package Architecture**: The monorepo structure with core/finder/tokenizer packages shows good separation

### Key Insight

jscpd demonstrates that code quality tools benefit from language-aware tokenization rather than simple text matching. This principle applies to Claude Code skills: understanding code structure (AST, tokens) enables more accurate analysis than regex-based approaches.

---

## References

1. **GitHub Repository**: <https://github.com/kucherenko/jscpd> (accessed 2026-01-31)
2. **Official Website**: <https://jscpd.dev/> (accessed 2026-01-31)
3. **NPM Package**: <https://www.npmjs.com/package/jscpd> (accessed 2026-01-31)
4. **CLI Documentation**: <https://github.com/kucherenko/jscpd/blob/master/apps/jscpd/README.md> (accessed 2026-01-31)
5. **Supported Formats**: <https://github.com/kucherenko/jscpd/blob/master/supported_formats.md> (accessed 2026-01-31)
6. **Rabin-Karp Algorithm**: <https://en.wikipedia.org/wiki/Rabin%E2%80%93Karp_algorithm>
7. **HTML Report Demo**: <http://kucherenko.github.io/jscpd-report.html>
8. **SARIF Specification**: <https://github.com/oasis-tcs/sarif-spec>

---


---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [TheAlgorithms-Python](../learning-resources/TheAlgorithms-Python.md) | learning-resources | referenced by TheAlgorithms-Python (learning-resources) |

## Related Tools

| Tool                                                                 | Relationship                                        |
| -------------------------------------------------------------------- | --------------------------------------------------- |
| [PMD CPD](https://pmd.github.io/latest/pmd_userdocs_cpd.html)        | Java-based CPD with XML output (jscpd compatible)   |
| [Simian](https://www.harukizaemon.com/simian/)                       | Commercial similarity analyzer                      |
| [SonarQube](https://www.sonarqube.org/)                              | Full code quality platform with duplication metrics |
| [dupfinder](https://www.jetbrains.com/help/resharper/dupFinder.html) | JetBrains C#/VB.NET duplication finder              |
