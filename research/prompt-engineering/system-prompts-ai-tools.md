---
title: "System Prompts and Models of AI Tools"
research_date: "2026-02-23"
source_url: "https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools"
github_url: "https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools"
version_at_research: "main branch (last pushed 2026-02-17)"
license: "GPL-3.0"
last_verified: "2026-02-23"
version_at_verification: "main (2026-02-17 push)"
next_review: "2026-05-23"
---

## Overview

This repository is the most comprehensive publicly available collection of leaked and reverse-engineered system prompts, internal tool definitions, and AI model configurations for major commercial AI coding assistants and productivity tools. Maintained by x1xhlol (NotLucknite), it covers 30,000+ lines of system prompt content spanning tools such as Claude Code, Cursor, Windsurf, Devin AI, Copilot, Replit, Lovable, Manus, Perplexity, v0, and many others. The repository serves as a primary reference for understanding how production AI systems structure their instructions, tool schemas, and behavioral constraints.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| System prompts for major AI tools are proprietary and undocumented | Aggregates leaked and reverse-engineered prompts across 30+ AI tools in one repository |
| Prompt engineers and researchers have no reference for how production AI systems are structured | Provides full verbatim system prompts with internal tool definitions and model configuration details |
| Understanding competitor or peer AI tool architectures requires expensive reverse engineering | Community-maintained collection removes individual reverse-engineering burden |
| No canonical source exists for tracking how AI tool prompts evolve over time | Repository is actively updated with new tools and prompt revisions (latest update: 2026-02-17) |
| Developing high-quality AI coding agents requires understanding existing design patterns | Real-world prompt examples from production systems expose best-practice patterns for tool use, safety rails, and task decomposition |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 117,922 | 2026-02-23 |
| Forks | 30,596 | 2026-02-23 |
| Watchers | 1,500 | 2026-02-23 |
| Open Issues | 120 | 2026-02-23 |
| Lines of Content | 30,000+ | 2026-02-23 |
| Tools Covered | 30+ | 2026-02-23 |
| Repository Created | 2025-03-05 | 2026-02-23 |
| Last Updated | 2026-02-17 | 2026-02-23 |

---

## Key Features

### Tool Coverage

Includes system prompts and/or model configurations for: Augment Code, Claude Code, Cluely, CodeBuddy, Comet, Cursor, Devin AI, Junie, Kiro, Leap.new, Lovable, Manus, NotionAI, Orchids.app, Perplexity, Poke, Qoder, Replit, Same.dev, Trae, Traycer AI, VSCode Agent, Warp.dev, Windsurf, Xcode, Z.ai Code, Dia, v0, and other open-sourced tools.

### Content Types

- **System prompts**: Full verbatim base instructions given to each AI model
- **Internal tool definitions**: JSON/function-call schemas for tools available to each AI agent
- **Model configurations**: Model selection, temperature, and context window settings where disclosed
- **Behavioral guidelines**: Safety constraints, refusal patterns, and task decomposition strategies

### Research Accessibility

- Organized in a flat directory structure by tool name
- Plain-text and Markdown format for easy reading and diffing
- Community discussions via GitHub Issues for context and corrections
- DeepWiki integration for AI-powered search across the entire collection

---

## Technical Architecture

### Repository Structure

<eg>
system-prompts-and-models-of-ai-tools/
  {tool-name}/              # One directory per AI tool
    system-prompt.md        # Full system prompt content
    tools.md                # Internal tool definitions (if available)
    model-info.md           # Model configuration details (if available)
  README.md                 # Index with tool list and support information
</eg>

### Content Sourcing

Content is gathered through:

1. **Prompt injection / extraction**: Techniques that cause models to reveal their system instructions
2. **API inspection**: Intercepting network traffic between AI tool frontends and their backends
3. **Community contributions**: Submissions from researchers and developers who discover prompt content
4. **Open-sourced disclosures**: Some tools (e.g., Cursor, GitHub Copilot) have partially disclosed prompt content

---

## Installation & Usage

This repository is a community-maintained archive of system prompts and model configurations. It does not require installation; access the content directly via GitHub or DeepWiki search.

### Option 1: Browse on GitHub

Visit the [system-prompts-and-models-of-ai-tools GitHub Repository](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) and navigate by tool name. Each directory contains markdown and text files with full system prompts and tool definitions.

**File structure for each tool:**
```
claude-code/
  └── system-prompt.md        # Full Claude Code system prompt
  └── tools.md               # MCP tool definitions
  └── model-info.md          # Model configuration details
```

**Source**: Repository structure documented at GitHub README (accessed 2026-02-23)

### Option 2: AI-Powered Search with DeepWiki

Use [DeepWiki's semantic search](https://deepwiki.com/x1xhlol/system-prompts-and-models-of-ai-tools) to find system prompt content across all 30+ tools. Search for patterns: "file editing tool", "context window size", "safety constraints", "refusal behavior", etc.

**Example search**:
```
Query: "How does Cursor handle file creation?"
Result: Returns relevant sections from Cursor's system-prompt.md with context
```

**Source**: DeepWiki integration mentioned in repository README (accessed 2026-02-23)

### Option 3: Clone the Repository Locally

```bash
# Clone the full repository
git clone https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools.git

# Navigate to a tool
cd system-prompts-and-models-of-ai-tools/claude-code

# View system prompt
cat system-prompt.md

# View tool definitions
cat tools.md
```

All content is in plain text and markdown for easy diffing, version control, and local analysis.

**Source**: Repository structure supports local cloning (accessed 2026-02-23)

### Contributing New Prompts

The repository accepts community submissions via:

1. **GitHub Issues**: Submit prompt content or correction suggestions as issues
2. **Pull Requests**: Contribute newly discovered or updated system prompts directly
3. **Community discussion**: Engage with other researchers in existing issues

Each contribution should include:
- Full verbatim system prompt text
- Source documentation (how the prompt was obtained)
- Tool version and disclosure date
- Any relevant context about changes from previous versions

**Source**: Community contribution model indicated by issue-based discussions on GitHub (accessed 2026-02-23)

---

## Relevance to Claude Code Development

### Applications

- **Claude Code system prompt analysis**: The repository includes Claude Code's system prompt, providing direct insight into how Anthropic structures Claude's coding agent instructions — valuable for understanding what behaviors are built-in vs. what can be customized
- **Skill and agent design benchmarking**: Compare Claude Code skill/agent designs against how Cursor, Windsurf, and Devin AI structure their agent instructions to identify gaps and patterns worth adopting
- **Tool schema reference**: The internal tool definitions (JSON function schemas) from production agents like Devin AI and Manus provide real-world examples of tool design for complex coding workflows
- **Safety and refusal pattern research**: Examining safety constraints across multiple AI systems helps design more robust behavioral guardrails for custom Claude Code agents

### Patterns Worth Adopting

- **Explicit tool use protocols**: Most production system prompts include explicit instructions for when and how to use each tool, including ordering preferences and fallback behaviors — a pattern that could strengthen Claude Code skill SKILL.md files
- **Structured task decomposition**: Systems like Devin AI and Manus use layered decomposition instructions (high-level goal → sub-tasks → individual tool calls) that could inform multi-agent orchestration patterns
- **Verbosity and format controls**: Production prompts carefully specify output format, verbosity levels, and when to ask for clarification vs. proceeding autonomously — directly applicable to Claude Code agent design

### Integration Opportunities

- **Prompt pattern library**: Extract and catalog recurring patterns from across the collection (e.g., "how 10 coding agents handle file editing") to inform Claude Code skill content
- **Competitive gap analysis**: Systematically compare Claude Code's available capabilities against those documented for Cursor, Windsurf, and Devin AI to identify missing skill/agent coverage
- **Safety pattern adoption**: Use documented safety and boundary patterns from multiple production systems to improve Claude Code agent behavioral constraints

---

## References

- [system-prompts-and-models-of-ai-tools GitHub Repository](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) (accessed 2026-02-23)
- [Trendshift — Repository Ranking](https://trendshift.io/repositories/14084) (accessed 2026-02-23)
- [DeepWiki — AI-powered search of the collection](https://deepwiki.com/x1xhlol/system-prompts-and-models-of-ai-tools) (accessed 2026-02-23)
- [ZeroLeaks — Related AI security audit service referenced in README](https://zeroleaks.ai/) (accessed 2026-02-23)

---
