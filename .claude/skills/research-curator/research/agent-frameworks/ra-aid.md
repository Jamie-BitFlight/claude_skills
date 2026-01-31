# RA.Aid

| Field         | Value                                               |
| ------------- | --------------------------------------------------- |
| Research Date | 2026-01-31                                          |
| Primary URL   | <https://ra-aid.ai/>                                |
| Documentation | <https://docs.ra-aid.ai>                            |
| GitHub        | <https://github.com/ai-christianson/RA.Aid>         |
| PyPI          | <https://pypi.org/project/ra-aid/>                  |
| Version       | v0.30.2 (released 2025-05-07)                       |
| License       | Apache-2.0                                          |
| Discord       | <https://discord.gg/f6wYbzHYxV>                     |

---

## Overview

RA.Aid (pronounced "raid") is a standalone autonomous software development assistant built on LangGraph's agent-based task execution framework. It implements a three-stage architecture (Research, Planning, Implementation) to handle complex multi-step development tasks. The tool can optionally integrate with aider for specialized code editing and supports multiple LLM providers including Anthropic, OpenAI, OpenRouter, Makehub, Gemini, and DeepSeek.

---

## Problem Addressed

| Problem                                                | Solution                                                                    |
| ------------------------------------------------------ | --------------------------------------------------------------------------- |
| Complex tasks require manual breakdown                 | Three-stage architecture automatically researches, plans, and implements    |
| Single-shot code edits insufficient for complex work   | Multi-step task planning executes discrete steps sequentially               |
| Need for human oversight in autonomous execution       | Human-in-the-loop mode allows agent questions during execution              |
| Context gathering is manual and time-consuming         | Automated web research via Tavily API gathers real-world context            |
| Expert reasoning needed for complex debugging          | Dedicated expert provider supports o1/o3 reasoning models when needed       |
| Code editing requires specialized tools                | Optional aider integration leverages specialized code editing capabilities  |
| Autonomous execution can be dangerous                  | Shell command approval prompts by default, cowboy mode optional             |
| Model lock-in limits flexibility                       | Multi-provider support: Anthropic, OpenAI, OpenRouter, Makehub, Gemini, DeepSeek |

---

## Key Statistics

| Metric           | Value                    | Date Gathered |
| ---------------- | ------------------------ | ------------- |
| GitHub Stars     | 2,204                    | 2026-01-31    |
| GitHub Forks     | 218                      | 2026-01-31    |
| Open Issues      | 60                       | 2026-01-31    |
| Primary Language | Python                   | 2026-01-31    |
| PyPI Monthly DL  | 933                      | 2026-01-31    |
| PyPI Weekly DL   | 106                      | 2026-01-31    |
| Repository Age   | Since December 2024      | 2026-01-31    |
| Python Required  | >=3.10                   | 2026-01-31    |

---

## Key Features

### Three-Stage Architecture

- **Research Stage**: Gathers information, analyzes codebases, identifies components and dependencies
- **Planning Stage**: Develops detailed implementation plans, breaks down tasks into steps, identifies challenges
- **Implementation Stage**: Executes planned tasks sequentially, generates code, performs system operations

### Multi-Provider LLM Support

- **Anthropic**: Default provider with Claude 3.7 Sonnet (`claude-3-7-sonnet-20250219`)
- **OpenAI**: GPT-4o and o1/o3 reasoning models for expert queries
- **OpenRouter**: Access to Mistral, Llama, and other models
- **Makehub**: Price-performance optimization with configurable ratio
- **Gemini**: Google's Gemini models including thinking variants
- **DeepSeek**: DeepSeek Reasoner for complex reasoning tasks
- **OpenAI-compatible**: Custom endpoints via `OPENAI_API_BASE`

### Expert Reasoning System

- Dedicated expert provider configuration separate from main agent
- Supports reasoning models (o1, o3, DeepSeek Reasoner, Gemini Thinking)
- Used for complex debugging and architectural decisions
- Independent API key configuration per provider

### Web Research Integration

- Autonomous web research powered by Tavily API
- Automatic context gathering when agent determines it valuable
- Searches for best practices, documentation, security recommendations
- No explicit configuration required - happens automatically

### Execution Modes

- **Standard Mode**: Interactive approval prompts for shell commands
- **Cowboy Mode**: Automated execution without confirmation (for CI/CD, batch processing)
- **Human-in-the-Loop (HIL)**: Agent can ask questions during execution
- **Chat Mode**: Interactive assistant for collaborative problem-solving
- **Research-Only Mode**: Analysis without implementation

### Aider Integration

- Optional integration via `--use-aider` flag
- Leverages aider's specialized code editing capabilities
- Automatic model selection based on available API keys
- Configurable via `AIDER_FLAGS` environment variable

### Cost and Token Management

- `--show-cost`: Display cost information during execution
- `--track-cost`: Track token usage and costs
- `--max-cost`: Set maximum cost threshold in USD
- `--max-tokens`: Set maximum token threshold
- `--exit-at-limit`: Auto-exit when limits reached

### Server and Web Interface (Alpha)

- Modern dark-themed chat interface
- Real-time streaming of agent trajectory
- Responsive design for all devices
- Configurable host and port

---

## Technical Architecture

### Stack Components

| Component        | Technology                                    |
| ---------------- | --------------------------------------------- |
| Core Framework   | Python (>=3.10)                               |
| Agent Framework  | LangGraph (graph-based workflow management)   |
| LLM Integration  | LangChain (langchain-anthropic)               |
| Web Research     | Tavily API (tavily-python)                    |
| Git Operations   | GitPython 3.1.41                              |
| Terminal Output  | Rich >=13.0.0                                 |
| String Matching  | FuzzyWuzzy, python-Levenshtein                |

### Core Modules

```text
ra_aid/
├── console/     # Console output formatting, user interaction
├── proc/        # Interactive processing, workflow control
├── text/        # Text processing utilities
└── tools/       # File operations, search, shell execution
```

### Workflow

```text
User Input → Research Stage → Planning Stage → Implementation Stage → Output
                  ↓                  ↓                  ↓
            Analyze codebase   Break into steps   Execute with tools
            Gather context     Identify risks     Generate code
            Web research       Create plan        System operations
```

### Tool Categories

- **Shell Execution**: Run commands with optional approval
- **Expert Querying**: Access reasoning models for complex problems
- **File Operations**: Read, write, modify files
- **Memory Management**: Persistent context across execution
- **Research Tools**: Web search, codebase analysis
- **Code Analysis**: AST parsing, dependency identification

---

## Installation and Usage

### Installation

```bash
# Using pip
pip install ra-aid

# Using Homebrew (macOS)
brew tap ai-christianson/homebrew-ra-aid
brew install ra-aid
```

### Environment Setup

```bash
# Required for default Anthropic provider
export ANTHROPIC_API_KEY=your_key

# Optional providers
export OPENAI_API_KEY=your_key
export OPENROUTER_API_KEY=your_key
export GEMINI_API_KEY=your_key
export DEEPSEEK_API_KEY=your_key
export MAKEHUB_API_KEY=your_key

# Web research
export TAVILY_API_KEY=your_key
```

### Basic Usage

```bash
# Basic task
ra-aid -m "Your task or query here"

# Research only (no implementation)
ra-aid -m "Explain the authentication flow" --research-only

# Automated execution
ra-aid -m "Update deprecated API calls" --cowboy-mode

# Human-in-the-loop
ra-aid -m "Implement new feature" --hil

# Chat mode
ra-aid --chat

# With aider integration
ra-aid -m "Refactor database code" --use-aider
```

### Provider Configuration

```bash
# OpenAI
ra-aid -m "Task" --provider openai --model gpt-4o

# OpenRouter
ra-aid -m "Task" --provider openrouter --model mistralai/mistral-large-2411

# Expert provider (for complex reasoning)
ra-aid -m "Task" --expert-provider openai --expert-model o1

# Makehub with price-performance optimization
ra-aid -m "Task" --provider makehub --model anthropic/claude-4-sonnet --price-performance-ratio 0.7
```

### Server Mode

```bash
# Start web interface
ra-aid --server

# Custom host/port
ra-aid --server --server-host 127.0.0.1 --server-port 3000
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Three-Stage Architecture Reference**: The Research-Planning-Implementation pattern provides a clear model for structuring complex autonomous tasks with distinct phases.

2. **Multi-Provider Abstraction**: RA.Aid's provider configuration pattern (separate expert provider, research provider, planner provider) demonstrates how to route different task types to appropriate models.

3. **Human-in-the-Loop Patterns**: The HIL mode implementation shows how to pause autonomous execution for human input and resume with new context.

4. **Cost Control Mechanisms**: Token and cost tracking with configurable limits demonstrates patterns for responsible autonomous execution.

5. **Aider Integration Model**: The optional aider integration shows how to compose specialized tools within an agent framework.

### Patterns Worth Adopting

1. **Staged Execution**: Explicit separation of research, planning, and implementation phases improves task quality and debuggability.

2. **Expert Escalation**: Routing complex problems to reasoning models (o1, DeepSeek Reasoner) only when needed optimizes cost while maintaining capability.

3. **Cowboy Mode Toggle**: Having a dedicated flag for unattended execution vs interactive approval is a clean safety pattern.

4. **Command Interruption**: Ctrl-C pauses for feedback rather than immediate exit, allowing course correction.

5. **Per-Stage Provider Configuration**: Allowing different models for research vs planning vs implementation enables cost/quality optimization.

6. **Test Integration**: `--test-cmd` and `--auto-test` flags for automatic test execution after code changes.

### Integration Opportunities

1. **LangGraph Compatibility**: Both use graph-based agent execution, potential for shared tooling or patterns.

2. **Aider Bridge**: RA.Aid's aider integration patterns could inform Claude Code's approach to external tool composition.

3. **Tavily Integration**: Web research patterns applicable to Claude Code context gathering.

4. **Expert Tool Pattern**: Delegating complex reasoning to specialized models is directly applicable to sub-agent design.

### Comparison with Claude Code

| Aspect              | RA.Aid                                  | Claude Code                           |
| ------------------- | --------------------------------------- | ------------------------------------- |
| Primary Use         | Autonomous software development         | Developer workflow automation         |
| Architecture        | Three-stage (Research/Plan/Implement)   | Agent delegation, Task tool           |
| Execution Model     | Sequential stage execution              | Tool-based, iterative                 |
| Human Interaction   | HIL mode, chat mode, interruption       | Interactive by default                |
| Code Editing        | Native + optional aider                 | Native Edit tool                      |
| Model Support       | Multi-provider (6+ providers)           | Claude models (Anthropic)             |
| Cost Controls       | Token/cost limits, exit-at-limit        | Session-based                         |
| Web Research        | Tavily integration                      | MCP tools, WebSearch                  |
| Deployment          | CLI + web server (alpha)                | CLI + IDE integration                 |

---

## References

| Source                       | URL                                                       | Accessed   |
| ---------------------------- | --------------------------------------------------------- | ---------- |
| Official Website             | <https://ra-aid.ai/>                                      | 2026-01-31 |
| Official Documentation       | <https://docs.ra-aid.ai>                                  | 2026-01-31 |
| GitHub Repository            | <https://github.com/ai-christianson/RA.Aid>               | 2026-01-31 |
| GitHub README                | <https://github.com/ai-christianson/RA.Aid/blob/master/README.md> | 2026-01-31 |
| PyPI Package                 | <https://pypi.org/project/ra-aid/>                        | 2026-01-31 |
| PyPI Stats                   | <https://pypistats.org/packages/ra-aid>                   | 2026-01-31 |
| Installation Guide           | <https://docs.ra-aid.ai/quickstart/installation>          | 2026-01-31 |
| Open Models Setup            | <https://docs.ra-aid.ai/quickstart/open-models>           | 2026-01-31 |
| Contributing Guide           | <https://docs.ra-aid.ai/contributing>                     | 2026-01-31 |

**Research Method**: Information gathered from official GitHub repository README (via GitHub API), PyPI package metadata, PyPI download statistics API, and official website metadata. Statistics verified via direct API calls on research date.

---

## Freshness Tracking

| Field              | Value                              |
| ------------------ | ---------------------------------- |
| Version Documented | v0.30.2                            |
| Release Date       | 2025-05-07                         |
| GitHub Stars       | 2,204 (as of 2026-01-31)           |
| Monthly Downloads  | 933 (as of 2026-01-31)             |
| Next Review Date   | 2026-05-01                         |

**Review Triggers**:

- Major version release (v1.x)
- Significant star growth (5K, 10K milestones)
- New stage architecture (additional stages beyond R-P-I)
- Production-ready server/web interface release
- New provider integrations of note
- Breaking changes to CLI or configuration
- Aider integration changes or removal
- New execution modes
