---
name: Skill Seekers - Documentation to AI Skills Automation
description: Skill Seekers is an open-source Python tool that automatically converts documentation websites, GitHub repositories, and PDF files into production-ready AI skills for Claude, Gemini, OpenAI, and...
license: MIT
metadata:
  topic: skill-seekers
  category: skill-generation-tools
  source_url: https://skillseekersweb.com/
  github: yusufkaraaslan/Skill_Seekers
  version: "v2.7.4"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

Skill Seekers is an open-source Python tool that automatically converts documentation websites, GitHub repositories, and PDF files into production-ready AI skills for Claude, Gemini, OpenAI, and other LLM platforms.

**Core Value Proposition**: Transform hours of manual documentation copying into 20-40 minutes of automated skill generation.

---

## Problem Addressed

| Problem                                                                         | How Skill Seekers Solves It                                                            |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Manually copying documentation into AI chat contexts is tedious and error-prone | Automatically extracts from docs, GitHub repos, and PDFs with multi-source analysis    |
| Large codebases and documentation exceed AI context window limits               | Intelligent chunking, categorization, and Three-Stream Analysis (Code, Docs, Insights) |
| AI responses lack framework-specific knowledge and best practices               | AI-enhanced skills with explanations, examples, and best practices                     |
| Keeping AI knowledge up-to-date with framework changes is time-consuming        | Re-run when docs update to keep AI knowledge fresh and accurate                        |

---

## Key Statistics (as of January 26, 2026)

| Metric                  | Value         |
| ----------------------- | ------------- |
| GitHub Stars            | 7,734         |
| Forks                   | 760           |
| Contributors            | 24            |
| Tests Passing           | 1,200+        |
| Preset Configs          | 24            |
| LLM Platforms Supported | 4             |
| Time per Skill          | 20-40 minutes |

---

## Key Features

### Supported Data Sources

### 1. Documentation Websites

- **llms.txt Support**: Automatically detects and uses LLM-ready documentation files (10x faster)
- **Universal Scraper**: Works with ANY documentation website
- **Smart Categorization**: Automatically organizes content by topic
- **Code Language Detection**: Recognizes Python, JavaScript, C++, GDScript, etc.

### 2. GitHub Repositories (v2.0.0+)

- **Deep Code Analysis**: AST parsing for Python, JavaScript, TypeScript, Java, C++, Go
- **API Extraction**: Functions, classes, methods with parameters and types
- **Repository Metadata**: README, file tree, language breakdown, stars/forks
- **GitHub Issues & PRs**: Fetch open/closed issues with labels and milestones
- **CHANGELOG & Releases**: Automatically extract version history
- **Conflict Detection**: Compare documented APIs vs actual code implementation

### 3. PDF Files (v1.2.0+)

- **Basic PDF Extraction**: Extract text, code, and images from PDF files
- **OCR for Scanned PDFs**: Extract text from scanned documents
- **Password-Protected PDFs**: Handle encrypted PDFs
- **Table Extraction**: Extract complex tables from PDFs
- **Parallel Processing**: 3x faster for large PDFs
- **Intelligent Caching**: 50% faster on re-runs

---

### Supported Output Platforms

| Platform             | Format             | Auto Upload | AI Enhancement | API Key Required  |
| -------------------- | ------------------ | ----------- | -------------- | ----------------- |
| **Claude AI**        | ZIP + YAML         | Yes         | Yes            | ANTHROPIC_API_KEY |
| **Google Gemini**    | tar.gz             | Yes         | Yes            | GOOGLE_API_KEY    |
| **OpenAI ChatGPT**   | ZIP + Vector Store | Yes         | Yes            | OPENAI_API_KEY    |
| **Generic Markdown** | ZIP                | No (Manual) | No             | None              |

---

### Three-Stream GitHub Architecture (v2.6.0+)

The tool splits GitHub repository analysis into three complementary streams:

<eg>
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Stream 1: Code │ │  Stream 2: Docs │ │Stream 3: Insights│
│                 │ │                 │ │                  │
│ - C3.x analysis │ │ - README        │ │ - GitHub issues  │
│ - Design patterns│ │ - CONTRIBUTING │ │ - Labels         │
│ - Test examples │ │ - docs/*.md    │ │ - Stars/forks    │
│ - Configs       │ │ - API docs     │ │ - Common problems│
│ - Architecture  │ │                 │ │                  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
</eg>

**Analysis Depth Options**:

- `basic`: 1-2 minutes - Quick overview
- `c3x`: 20-60 minutes - Deep analysis with patterns, examples, guides, configs, architecture

---

### C3.x Codebase Analysis System

### C3.1: Design Pattern Extraction

Identifies common software design patterns in the codebase.

### C3.2: Test Examples

Extracts test cases as usage examples.

### C3.3: AI-Enhanced How-To Guides

- Transforms basic guides into professional tutorials
- 5 automatic improvements: step descriptions, troubleshooting, prerequisites, next steps, use cases
- Dual-mode support: API mode (Claude API) or LOCAL mode (Claude Code CLI)
- No API costs with LOCAL mode using Claude Code Max plan

### C3.4: Configuration Pattern Extraction

- **9 Config Formats**: JSON, YAML, TOML, ENV, INI, Python, JavaScript, Dockerfile, Docker Compose
- **7 Pattern Types**: Database, API, logging, cache, email, auth, server configurations
- **Security Analysis**: Finds hardcoded secrets, exposed credentials
- **Auto-Documentation**: Generates JSON + Markdown documentation of all configs

---

## Installation & Usage

### Installation Options

```bash
# PyPI (Recommended)
pip install skill-seekers

# uv (Modern, Fast)
uv tool install skill-seekers

# With Gemini support
pip install skill-seekers[gemini]

# With OpenAI support
pip install skill-seekers[openai]

# With all LLM platforms
pip install skill-seekers[all-llms]

# From Source (Development)
git clone https://github.com/yusufkaraaslan/Skill_Seekers.git
cd Skill_Seekers
pip install -e .
```

---

### Basic Usage Workflow

```bash
# Step 1: Install
pip install skill-seekers

# Step 2: Scrape documentation
skill-seekers scrape --config react
# Or from URL directly
skill-seekers scrape --url https://react.dev --name react

# Step 3: Package and upload
skill-seekers package output/react/
skill-seekers upload react.zip

# Done! Your skill is ready to use
```

---

### Multi-Source Unified Scraping (v2.0.0+)

Combine documentation + GitHub + PDF in one skill with conflict detection:

```bash
# Combine multiple sources
skill-seekers scrape \
  --url https://react.dev \
  --github facebook/react \
  --pdf react-patterns.pdf \
  --name react-complete
```

**Features**:

- Automatically finds discrepancies between docs and code
- Rule-based or AI-powered conflict resolution
- Side-by-side comparison with warnings
- Documentation gap analysis (identifies outdated docs and undocumented features)

---

### Configuration System (v2.7.0+)

### Multi-Token Management

```bash
# One-time configuration (5 minutes)
skill-seekers config --github

# Add multiple GitHub profiles (personal, work, OSS)
skill-seekers config

# Use specific profile for private repos
skill-seekers github --repo mycompany/private-repo --profile work

# CI/CD mode (fail fast, no prompts)
skill-seekers github --repo owner/repo --non-interactive

# View current configuration
skill-seekers config --show

# Test connections
skill-seekers config --test
```

### Rate Limit Strategies

| Strategy           | Behavior                                 | Use Case             |
| ------------------ | ---------------------------------------- | -------------------- |
| `prompt` (default) | Ask what to do when rate limited         | Interactive use      |
| `wait`             | Automatically wait with countdown timer  | Unattended runs      |
| `switch`           | Automatically try next available profile | Multi-account setups |
| `fail`             | Fail immediately with clear error        | CI/CD pipelines      |

### Resume Capability

```bash
# List resumable jobs
skill-seekers resume --list

# Resume interrupted job
skill-seekers resume github_react_20260117_143022
```

---

### Bootstrap Skill - Self-Hosting (v2.7.0+)

Generate skill-seekers as a Claude Code skill to use within Claude:

```bash
# Generate the skill
./scripts/bootstrap_skill.sh

# Install to Claude Code
cp -r output/skill-seekers ~/.claude/skills/

# Verify
ls ~/.claude/skills/skill-seekers/SKILL.md
```

**Output includes**:

- Complete skill documentation
- CLI command reference
- Quick start examples
- Auto-generated API docs
- YAML frontmatter validation

---

### Private Config Repositories (v2.2.0+)

For team collaboration:

- Git-based config sources from private/team git repositories
- Multi-source management for GitHub, GitLab, Bitbucket repos
- Team collaboration for 3-5 person teams
- Enterprise support scaling to 500+ developers
- Secure authentication via environment variable tokens
- Intelligent caching with automatic pull updates
- Offline mode with cached configs

---

### Preset Configurations Available

24 preset configs for popular frameworks:

- **Frontend**: React, Vue, Angular, Svelte
- **Backend**: Django, FastAPI, Flask, Express
- **Game Engines**: Godot (handles 40K+ pages), Unity
- **Languages**: Python, JavaScript, TypeScript, Go
- **And more...**

Browse all at: <https://skillseekersweb.com/configs>

---

## MCP Integration

Built-in Model Context Protocol support with 27+ tools:

```bash
# Setup MCP integration
./setup_mcp.sh
```

Natural language commands:

- "Scrape GitHub repo facebook/react"
- "Extract config patterns from this codebase"

---

## Relevance to Claude Code Development

### Direct Applications

1. **Skill Generation**: Automate creation of Claude Code skills from any documentation
2. **Documentation-to-Skill Pipeline**: Convert framework docs into AI-consumable formats
3. **Multi-Source Truth**: Combine docs + code + PDFs into unified skill
4. **Conflict Detection**: Identify drift between documentation and implementation

### Patterns Worth Adopting

1. **Three-Stream Analysis**: Separating Code/Docs/Insights for comprehensive coverage
2. **C3.x Depth Levels**: Configurable analysis depth (basic vs deep)
3. **AI Enhancement Modes**: API vs LOCAL modes for cost optimization
4. **Rate Limit Strategies**: Configurable handling for API limits
5. **Resume Capability**: State persistence for interrupted operations

### Integration Opportunities

1. Could integrate with existing skill-creation workflows in this repository
2. Bootstrap capability could generate skills for any Claude Code plugin
3. Configuration patterns could inform plugin settings design
4. Multi-platform export could extend plugin distribution options

---

## Technical Architecture

<eg>
User Input (URL/GitHub/PDF)
         │
         ▼
┌─────────────────────────────┐
│    Source Detection         │
│  (Docs / GitHub / PDF)      │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Content Extraction       │
│  - Web scraping             │
│  - GitHub API + AST parsing │
│  - PDF text/OCR extraction  │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Analysis & Categorization│
│  - Smart chunking           │
│  - Topic detection          │
│  - Code language detection  │
│  - Conflict detection       │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    AI Enhancement           │
│  (Optional)                 │
│  - Add explanations         │
│  - Best practices           │
│  - Troubleshooting          │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Platform-Specific        │
│    Packaging                │
│  - Claude ZIP + YAML        │
│  - Gemini tar.gz            │
│  - OpenAI Vector Store      │
│  - Generic Markdown         │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Upload to Platform       │
│  (Auto or Manual)           │
└─────────────────────────────┘
</eg>

---

## References

1. **Official Website**: <https://skillseekersweb.com/> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/yusufkaraaslan/Skill_Seekers> (accessed 2026-01-26)
3. **PyPI Package**: <https://pypi.org/project/skill-seekers/> (accessed 2026-01-26)
4. **Three-Stream Implementation Summary**: <https://github.com/yusufkaraaslan/Skill_Seekers/blob/main/docs/IMPLEMENTATION_SUMMARY_THREE_STREAM.md>
5. **Claude AI Skills Announcement**: <https://www.anthropic.com/news/skills>
