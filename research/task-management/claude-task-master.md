---
name: Claude Task Master - AI-Powered Task Management for Development
description: Claude Task Master (Taskmaster) is an AI-powered task management system designed for AI-driven development workflows. It integrates with Cursor, Windsurf, VS Code, and other AI-enabled IDEs via MCP...
license: MIT with Commons Clause
metadata:
  topic: claude-task-master
  category: task-management
  source_url: https://task-master.dev
  github: eyaltoledano/claude-task-master
  version: "0.42.0"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

Claude Task Master (Taskmaster) is an AI-powered task management system designed for AI-driven development workflows. It integrates with Cursor, Windsurf, VS Code, and other AI-enabled IDEs via MCP (Model Context Protocol), providing structured task decomposition, tracking, and execution guidance. The system parses Product Requirements Documents (PRDs) into actionable development tasks and guides AI assistants through implementation.

**Core Value Proposition**: Bridge the gap between high-level product requirements and AI-assisted implementation by providing structured task management that AI assistants can understand and execute.

---

## Problem Addressed

| Problem                                                          | How Task Master Solves It                                                       |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| AI assistants lack context about project progress and next steps | Persistent task state with dependencies, status tracking, and priority ordering |
| PRDs are too abstract for AI to implement directly               | Automated PRD parsing generates structured, implementable tasks                 |
| Switching between AI models requires reconfiguration             | Model-agnostic with support for 10+ providers (Anthropic, OpenAI, Google, etc.) |
| AI context windows fill up with task management overhead         | Selective tool loading reduces context usage from 21K to 5K tokens              |
| Research tasks produce outdated information from training data   | Dedicated research model with live web access (Perplexity, xAI)                 |

---

## Key Statistics (as of January 26, 2026)

| Metric                 | Value                             |
| ---------------------- | --------------------------------- |
| GitHub Stars           | 25,062                            |
| Forks                  | 2,406                             |
| Open Issues            | 157                               |
| Contributors           | 30+                               |
| npm Downloads          | High volume (weekly/monthly)      |
| Commits                | 1,188                             |
| MCP Tools Available    | 36 (all), 15 (standard), 7 (core) |
| Supported AI Providers | 10+                               |
| Created                | March 4, 2025                     |

---

## Supported AI Providers

| Provider     | Model Types               | API Key Required     |
| ------------ | ------------------------- | -------------------- |
| Anthropic    | Claude 3.5/4 Sonnet, Opus | ANTHROPIC_API_KEY    |
| OpenAI       | GPT-4o, GPT-4 Turbo       | OPENAI_API_KEY       |
| Google       | Gemini Pro, Flash         | GOOGLE_API_KEY       |
| Perplexity   | Research models           | PERPLEXITY_API_KEY   |
| xAI          | Grok models               | XAI_API_KEY          |
| OpenRouter   | Any model                 | OPENROUTER_API_KEY   |
| Mistral      | Mistral models            | MISTRAL_API_KEY      |
| Groq         | Fast inference            | GROQ_API_KEY         |
| Azure OpenAI | Enterprise GPT            | AZURE_OPENAI_API_KEY |
| Ollama       | Local models              | OLLAMA_API_KEY       |
| Claude Code  | CLI-based (no key)        | None                 |
| Codex CLI    | OAuth-based               | None                 |

**Model Configuration**:

- **Main Model**: Primary task processing
- **Research Model**: Live web search and current information
- **Fallback Model**: Backup when primary fails

---

## IDE/Editor Integration

| Editor          | Configuration Path                                 | MCP Key      |
| --------------- | -------------------------------------------------- | ------------ |
| Cursor          | `~/.cursor/mcp.json` or project `.cursor/mcp.json` | `mcpServers` |
| Windsurf        | `~/.codeium/windsurf/mcp_config.json`              | `mcpServers` |
| VS Code         | `<project>/.vscode/mcp.json`                       | `servers`    |
| Q Developer CLI | `~/.aws/amazonq/mcp.json`                          | `mcpServers` |

---

## Key Features

### 1. PRD Parsing and Task Generation

Convert high-level requirements into structured development tasks:

<eg>
User: "Can you parse my PRD at scripts/prd.txt?"
Task Master: [Generates hierarchical task structure with dependencies]
</eg>

**Output Structure**:

- Tasks with IDs, titles, descriptions
- Subtasks for granular work
- Dependencies between tasks
- Status tracking (pending, in-progress, done)
- Tags for categorization

### 2. Intelligent Task Sequencing

<eg>
User: "What's the next task I should work on?"
Task Master: [Analyzes dependencies, returns highest-priority unblocked task]
</eg>

### 3. Task Expansion

Break down complex tasks into implementation steps:

<eg>
User: "Can you help me expand task 4?"
Task Master: [Generates subtasks with implementation details]
</eg>

### 4. Live Research

Query current information with project context:

<eg>
User: "Research the latest best practices for JWT authentication with Node.js"
Task Master: [Uses research model for live web search]
</eg>

### 5. Cross-Tag Task Movement

Kanban-style task management:

```bash
task-master move --from=5 --from-tag=backlog --to-tag=in-progress
task-master move --from=5,6,7 --from-tag=backlog --to-tag=done --with-dependencies
```

---

## Tool Loading Configuration

Optimize context window usage with selective tool loading:

| Mode               | Tools    | Context Usage  | Use Case             |
| ------------------ | -------- | -------------- | -------------------- |
| `all` (default)    | 36       | ~21,000 tokens | Complete feature set |
| `standard`         | 15       | ~10,000 tokens | Common operations    |
| `core` (or `lean`) | 7        | ~5,000 tokens  | Essential workflow   |
| `custom`           | Variable | Variable       | Specific tools only  |

**Core Tools (7)**:

- `get_tasks`, `next_task`, `get_task`
- `set_task_status`, `update_subtask`
- `parse_prd`, `expand_task`

**Standard Tools (15)**: Core plus:

- `initialize_project`, `analyze_project_complexity`
- `expand_all`, `add_subtask`, `remove_task`
- `generate`, `add_task`, `complexity_report`

**Configuration**:

```json
{
  "mcpServers": {
    "task-master-ai": {
      "command": "npx",
      "args": ["-y", "task-master-ai"],
      "env": {
        "TASK_MASTER_TOOLS": "standard",
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Installation & Usage

### MCP Integration (Recommended)

```bash
# Claude Code
claude mcp add taskmaster-ai -- npx -y task-master-ai

# Core mode (~70% token reduction)
claude mcp add task-master-ai --scope user \
  --env TASK_MASTER_TOOLS="core" \
  -- npx -y task-master-ai@latest
```

### Command Line

```bash
# Install globally
npm install -g task-master-ai

# Initialize project
task-master init

# Parse PRD
task-master parse-prd your-prd.txt

# Common operations
task-master list           # List all tasks
task-master next           # Show next task
task-master show 1,3,5     # Show specific tasks
```

### Workflow Example

<eg>
1. Create PRD at .taskmaster/docs/prd.txt
2. "Initialize taskmaster-ai in my project"
3. "Can you parse my PRD?"
4. "What's the next task I should work on?"
5. "Can you help me implement task 3?"
6. [Repeat until project complete]
</eg>

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────────┐
│                     Task Master System                           │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   MCP Server    │  │   Task Engine    │  │   AI Provider    │
│                 │  │                  │  │   Gateway        │
│ - Tool registry │  │ - Task state     │  │                  │
│ - 36 tools      │  │ - Dependencies   │  │ - Main model     │
│ - Selective     │  │ - Status         │  │ - Research model │
│   loading       │  │ - Tags           │  │ - Fallback model │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PRD Parser    │  │  Research       │  │   Project Files  │
│                 │  │  Subsystem      │  │                  │
│ - Requirement   │  │                 │  │ - .taskmaster/   │
│   extraction    │  │ - Live web      │  │ - tasks.json     │
│ - Task          │  │ - Context-aware │  │ - prd.txt        │
│   decomposition │  │ - Multi-model   │  │ - rules/         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
</eg>

---

## Project Structure

<eg>
project/
├── .taskmaster/
│   ├── config.json          # Project configuration
│   ├── tasks/
│   │   └── tasks.json       # Task data
│   ├── docs/
│   │   └── prd.txt          # Product requirements
│   └── templates/
│       └── example_prd.txt  # PRD template
├── .cursor/mcp.json         # Cursor MCP config
└── .vscode/mcp.json         # VS Code MCP config
</eg>

---

## Claude Code Plugin

Task Master provides a Claude Code plugin for native integration:

**Plugin Files**:

- `.claude-plugin/` directory
- `CLAUDE.md` with project instructions
- `CLAUDE_CODE_PLUGIN.md` documentation

**Features**:

- Native tool exposure via MCP
- Context-aware task suggestions
- Automatic status updates
- Integration with Claude Code CLI

---

## Licensing Details

**MIT License with Commons Clause**:

**Allowed**:

- Use for any purpose (personal, commercial, academic)
- Modify the code
- Distribute copies
- Create and sell products built using Task Master

**Not Allowed**:

- Sell Task Master itself
- Offer Task Master as a hosted service
- Create competing products based on Task Master

---

## Relevance to Claude Code Development

### Direct Applications

1. **Task Tracking Pattern**: Task Master demonstrates effective AI-to-AI task communication via structured data
2. **MCP Tool Design**: 36 tools with selective loading shows context-optimization patterns
3. **Multi-Model Architecture**: Main/research/fallback model pattern enables specialized capabilities
4. **PRD-to-Implementation**: Automated requirement decomposition could inform Claude Code planning features

### Patterns Worth Adopting

1. **Selective Tool Loading**: Reduce context usage by loading only needed tools
2. **Model Role Separation**: Main, research, and fallback models for different purposes
3. **Persistent Task State**: File-based state that survives session boundaries
4. **Tag-Based Organization**: Kanban-style workflow with cross-tag movement
5. **Project Complexity Analysis**: Pre-implementation analysis to guide task breakdown

### Integration Opportunities

1. **Complement Claude Code Task Tool**: Task Master provides richer task features than built-in TaskCreate/TaskUpdate
2. **Research Augmentation**: Dedicated research model could enhance Claude Code's information gathering
3. **Plugin Model**: Task Master's Claude Code plugin demonstrates effective plugin patterns
4. **Context Management**: Selective tool loading pattern applicable to Claude Code plugins

### Comparison with Claude Code Built-in Tasks

| Feature            | Task Master       | Claude Code Tasks |
| ------------------ | ----------------- | ----------------- |
| PRD Parsing        | Yes               | No                |
| Dependencies       | Yes               | Yes (blockedBy)   |
| Research Model     | Yes (dedicated)   | No                |
| Persistence        | File-based        | Session-based     |
| MCP Tools          | 36                | 4 (Task\*)        |
| Multi-Editor       | Yes               | Claude Code only  |
| Token Optimization | Selective loading | N/A               |

---

## References

1. **Official Website**: <https://task-master.dev> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/eyaltoledano/claude-task-master> (accessed 2026-01-26)
3. **Documentation**: <https://docs.task-master.dev> (accessed 2026-01-26)
4. **npm Package**: <https://www.npmjs.com/package/task-master-ai> (accessed 2026-01-26)
5. **Configuration Guide**: <https://github.com/eyaltoledano/claude-task-master/blob/main/docs/configuration.md> (accessed 2026-01-26)
6. **Claude Code Integration**: <https://github.com/eyaltoledano/claude-task-master/blob/main/docs/examples/claude-code-usage.md> (accessed 2026-01-26)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [unblocked](../context-management/unblocked.md) | context-management | referenced by unblocked (context-management) |
| [sidecar](../developer-tools/sidecar.md) | developer-tools | referenced by sidecar (developer-tools) |
| [xyops](./xyops.md) | task-management | referenced by xyops (task-management) |
