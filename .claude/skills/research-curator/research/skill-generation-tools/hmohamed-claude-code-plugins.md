# hmohamed01/claude-code-plugins

| Field         | Value                                                        |
| ------------- | ------------------------------------------------------------ |
| Research Date | 2026-01-31                                                   |
| Primary URL   | <https://github.com/hmohamed01/claude-code-plugins>          |
| GitHub        | <https://github.com/hmohamed01/claude-code-plugins>          |
| Installation  | `claude plugin marketplace add hmohamed01/claude-code-plugins` |
| Version       | swift-developer@0.3.0, rust-developer@0.2.0                  |
| License       | MIT                                                          |
| Author        | [@hmohamed01](https://github.com/hmohamed01)                 |

---

## Overview

A collection of Claude Code plugins providing autonomous development agents for Swift and Rust programming languages. The repository implements a monorepo structure with independent plugins for iOS/macOS Swift development (SwiftUI, Swift 6 concurrency, Xcode) and comprehensive Rust development (cargo, clippy, async patterns, WebAssembly). Each plugin includes specialized agents, skills with reference documentation, pre-tool hooks for unsafe pattern detection, and utility scripts.

---

## Problem Addressed

| Problem                                                | Solution                                                                       |
| ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Swift development requires language-specific expertise | swift-developer plugin with SwiftUI, Swift 6 concurrency, and Xcode knowledge  |
| Rust's ownership model creates common pitfalls         | rust-developer plugin with ownership, borrowing, and lifetime reference docs   |
| Unsafe code patterns slip into production              | PreToolUse hooks automatically detect and warn about unsafe patterns           |
| Apple docs not programmatically accessible             | GitHub-based documentation sources (Swift Book, Swift Evolution, Swift Testing)|
| Manual setup for new Swift/Rust projects               | Utility scripts: `new_package.sh`, `new_project.sh` with config files          |
| Testing requires simulator/toolchain knowledge         | Built-in xcodebuild, simctl, cargo commands and reference documentation        |
| AI agents lack framework-specific patterns             | Skills include Axum, Actix, Rocket (Rust) and SwiftUI, @Observable (Swift)     |

---

## Key Statistics

| Metric           | Value                            | Date Gathered |
| ---------------- | -------------------------------- | ------------- |
| GitHub Stars     | 4                                | 2026-01-31    |
| GitHub Forks     | 1                                | 2026-01-31    |
| Open Issues      | 0                                | 2026-01-31    |
| Primary Language | Shell                            | 2026-01-31    |
| Repository Age   | Since 2026-01-06                 | 2026-01-31    |
| Last Updated     | 2026-01-28                       | 2026-01-31    |
| Last Pushed      | 2026-01-13                       | 2026-01-31    |
| Plugin Count     | 2                                | 2026-01-31    |
| Contributors     | 1                                | 2026-01-31    |

---

## Key Features

### Plugin: swift-developer (v0.3.0)

| Component     | Purpose                                                          |
| ------------- | ---------------------------------------------------------------- |
| Agent         | Autonomous Swift development for iOS/macOS apps                  |
| Skill         | `swift-knowledge` - SwiftUI, Swift 6 concurrency, XCTest         |
| Hooks         | PreToolUse detection of force unwraps, hardcoded secrets, unsafe patterns |
| Command       | `/swift-developer:swift-developer <task>`                        |

#### Swift Unsafe Pattern Detection

| Pattern                    | Issue                     | Recommended Fix                              |
| -------------------------- | ------------------------- | -------------------------------------------- |
| Force unwraps (`!`)        | Runtime crashes           | `guard let`, `if let`, or `??`               |
| Hardcoded secrets          | Security vulnerability    | Keychain or environment variables            |
| `DispatchQueue.main.sync`  | Main thread blocking      | `.async` or async/await                      |
| `@unchecked Sendable`      | Thread safety bypass      | Proper synchronization (NSLock, actors)      |
| Missing `@MainActor`       | UI thread safety          | Add `@MainActor` to ObservableObject classes |

#### Swift Documentation Sources

| Source             | Content                                 |
| ------------------ | --------------------------------------- |
| Swift Book         | Language guide and reference manual     |
| Swift Testing      | Modern testing (`@Test`, `#expect`)     |
| Swift Evolution    | Latest language proposals               |
| Swift Async Algos  | Async sequence operations               |

### Plugin: rust-developer (v0.2.0)

| Component     | Purpose                                                              |
| ------------- | -------------------------------------------------------------------- |
| Agent         | Comprehensive Rust development with cargo ecosystem                  |
| Skill         | `rust-knowledge` - ownership, async Rust, error handling, frameworks |
| Hooks         | PreToolUse detection of panics, unwraps, unsafe blocks, blocking ops |
| Command       | `/rust-developer:rust-developer <task>`                              |

#### Rust Reference Documentation

| Topic           | Coverage                                      |
| --------------- | --------------------------------------------- |
| Ownership       | Ownership, borrowing, and lifetimes           |
| Error Handling  | Result, Option, thiserror, anyhow             |
| Async Rust      | Tokio, async/await, channels                  |
| Testing         | Unit tests, integration tests, mocking        |
| Cargo           | Cargo.toml, workspaces, features              |
| Clippy          | Linting rules and configuration               |
| WebAssembly     | wasm-pack, wasm-bindgen                       |
| Frameworks      | Axum, Actix, Rocket patterns                  |
| Troubleshooting | Common errors and solutions                   |

#### Rust Unsafe Pattern Warnings

| Pattern                              | Issue                           |
| ------------------------------------ | ------------------------------- |
| Hardcoded secrets/API keys           | Security vulnerability          |
| `panic!` in library code             | Production instability          |
| Multiple `.unwrap()` without context | Missing error context           |
| `unsafe` without `// SAFETY:`        | Undocumented unsafe reasoning   |
| Blocking operations in async         | Thread pool exhaustion          |

### Utility Scripts

| Plugin          | Script              | Purpose                                    |
| --------------- | ------------------- | ------------------------------------------ |
| swift-developer | `new_package.sh`    | Create Swift package with SwiftFormat/Lint |
| swift-developer | `run_tests.sh`      | Run tests with common options              |
| swift-developer | `format_and_lint.sh`| Format and lint Swift code                 |
| swift-developer | `simulator.sh`      | Quick iOS simulator management             |
| rust-developer  | `new_project.sh`    | Create Rust project with config files      |
| rust-developer  | `run_tests.sh`      | Run tests with common options              |
| rust-developer  | `format_lint.sh`    | Format and lint Rust code                  |

---

## Technical Architecture

### Repository Structure

```text
claude-code-plugins/
├── .claude-plugin/
│   └── marketplace.json     # Marketplace manifest (2 plugins)
├── CLAUDE.md                # Repo-wide AI guidance
├── swift-developer/
│   ├── .claude-plugin/
│   │   └── plugin.json      # Plugin manifest
│   ├── CLAUDE.md            # Swift-specific AI guidance
│   ├── commands/
│   │   └── swift-developer.md
│   ├── agents/
│   │   └── swift-developer.md
│   ├── skills/
│   │   └── swift-knowledge/
│   │       ├── SKILL.md
│   │       ├── references/
│   │       ├── scripts/
│   │       └── assets/
│   └── hooks/
│       ├── hooks.json
│       └── scripts/
└── rust-developer/
    └── [same structure as swift-developer]
```

### Plugin Architecture Pattern

Each plugin follows a consistent structure:

1. **Command** - Entry point via slash command (`/plugin-name:plugin-name`)
2. **Agent** - Autonomous task execution with tool access
3. **Skill** - Knowledge base with SKILL.md and reference files
4. **Hooks** - PreToolUse hooks for pattern detection and enforcement

### Marketplace Configuration

```json
{
  "name": "hmohamed-plugins",
  "owner": { "name": "hmohamed01" },
  "metadata": {
    "description": "A collection of Claude Code plugins for Swift and Rust development"
  },
  "plugins": [
    { "name": "swift-developer", "version": "0.3.0" },
    { "name": "rust-developer", "version": "0.2.0" }
  ]
}
```

### Monorepo Design

- Each plugin is an independent, self-contained project
- Plugin-specific CLAUDE.md provides isolated AI instructions
- No cross-plugin dependencies
- kebab-case folder naming convention

---

## Installation and Usage

### Installation

```bash
# Add the marketplace
claude plugin marketplace add hmohamed01/claude-code-plugins

# Browse and install plugins via /plugins command
```

### Swift Developer Usage

```text
/swift-developer:swift-developer create a SwiftUI settings screen with @Observable
/swift-developer:swift-developer review my code for concurrency issues
/swift-developer:swift-developer run tests on iPhone 15 simulator
```

### Rust Developer Usage

```text
/rust-developer:rust-developer create a new async HTTP client library
/rust-developer:rust-developer review my code for ownership issues
/rust-developer:rust-developer run clippy and fix the warnings
```

### Requirements

| Plugin          | Requirements                                      |
| --------------- | ------------------------------------------------- |
| swift-developer | macOS, Xcode 15+ (Xcode 16+ for Swift 6), CLI tools |
| rust-developer  | Rust toolchain via rustup, clippy, rustfmt        |

---

## Relevance to Claude Code Development

### Direct Applications

1. **Plugin Architecture Reference**: Demonstrates well-structured Claude Code plugin organization with command, agent, skill, and hook components working together.

2. **Language-Specific Skills**: Provides templates for creating deep, domain-specific skills with comprehensive reference documentation.

3. **PreToolUse Hook Patterns**: Shows how to implement safety guardrails that detect and warn about unsafe patterns before code is written.

4. **Documentation Verification Pattern**: Swift plugin's approach to using GitHub-based sources when primary documentation (Apple developer docs) is JavaScript-rendered.

5. **Utility Script Integration**: Demonstrates how to package helper scripts within skills for common development operations.

### Patterns Worth Adopting

1. **Monorepo Plugin Organization**: Independent plugins in a single repository with per-plugin CLAUDE.md enables focused AI guidance while maintaining unified distribution.

2. **Hook-Based Safety Rails**: PreToolUse hooks catch dangerous patterns (force unwraps, unsafe blocks, hardcoded secrets) before they enter the codebase.

3. **Structured Reference Documentation**: Skills include categorized reference files (ownership.md, error-handling.md, async-rust.md) for progressive disclosure.

4. **Slash Command Entry Points**: `/plugin-name:plugin-name <task>` pattern provides clear invocation path for users.

5. **Version Management**: Marketplace.json tracks plugin versions independently, allowing granular updates.

6. **Dual CLAUDE.md Strategy**: Repository-level CLAUDE.md for global conventions, plugin-level CLAUDE.md for domain-specific guidance.

### Integration Opportunities

1. **Skill Format Compatibility**: Skills could be adapted or imported using the same structure as this repository's skill format.

2. **Hook Pattern Extraction**: Unsafe pattern detection hooks could inform safety guardrails in other development plugins.

3. **Reference Documentation Model**: The categorized reference file approach could be applied to other language-specific skills.

4. **Swift/Rust Skills**: The plugins themselves could be installed for users needing Swift or Rust development assistance.

### Comparison with This Repository

| Aspect              | hmohamed01/claude-code-plugins      | This Repository (claude_skills)       |
| ------------------- | ----------------------------------- | ------------------------------------- |
| Plugin Count        | 2 (Swift, Rust)                     | Multiple plugins + skills             |
| Focus               | Language-specific development       | General-purpose skill marketplace     |
| Hook Usage          | PreToolUse safety checks            | Configurable hooks                    |
| Skill Structure     | SKILL.md + references/ + scripts/   | SKILL.md + references/                |
| Marketplace Support | Yes (marketplace.json)              | Yes                                   |
| Primary Author      | @hmohamed01                         | Community                             |
| Installation        | Plugin marketplace add              | Plugin marketplace + direct install   |

---

## References

| Source                        | URL                                                                          | Accessed   |
| ----------------------------- | ---------------------------------------------------------------------------- | ---------- |
| GitHub Repository             | <https://github.com/hmohamed01/claude-code-plugins>                          | 2026-01-31 |
| GitHub README                 | <https://github.com/hmohamed01/claude-code-plugins/blob/main/README.md>      | 2026-01-31 |
| GitHub API (Metadata)         | <https://api.github.com/repos/hmohamed01/claude-code-plugins>                | 2026-01-31 |
| Swift Developer README        | <https://github.com/hmohamed01/claude-code-plugins/tree/main/swift-developer>| 2026-01-31 |
| Rust Developer README         | <https://github.com/hmohamed01/claude-code-plugins/tree/main/rust-developer> | 2026-01-31 |
| Marketplace Configuration     | <https://github.com/hmohamed01/claude-code-plugins/blob/main/.claude-plugin/marketplace.json> | 2026-01-31 |
| CLAUDE.md                     | <https://github.com/hmohamed01/claude-code-plugins/blob/main/CLAUDE.md>      | 2026-01-31 |

**Research Method**: Information gathered from GitHub repository README files, GitHub API for repository metadata (stars, forks, dates, contributors), and raw file fetches for marketplace.json and CLAUDE.md. Statistics verified via direct API calls on 2026-01-31.

---

## Freshness Tracking

| Field              | Value                                        |
| ------------------ | -------------------------------------------- |
| Version Documented | swift-developer@0.3.0, rust-developer@0.2.0  |
| Last Pushed        | 2026-01-13                                   |
| GitHub Stars       | 4 (as of 2026-01-31)                         |
| Plugin Count       | 2 (as of 2026-01-31)                         |
| Next Review Date   | 2026-05-01                                   |

**Review Triggers**:

- New plugins added to marketplace
- Major version bumps (swift-developer@1.0, rust-developer@1.0)
- GitHub stars milestone (25, 50, 100)
- Significant new language features documented (Swift 7, Rust 2024 edition)
- Additional language plugins added (Go, Python, TypeScript)
- Changes to Claude Code plugin architecture
