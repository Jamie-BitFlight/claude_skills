---
name: Mimir MCP - Git-Backed AI Memory System
description: Mimir is a Model Context Protocol (MCP) server that provides persistent, git-versioned memory storage for LLM applications. It combines Git's version control with graph-based memory associations,...
license: MPL-2.0 (Mozilla Public License 2.0)
metadata:
  topic: mimir-mcp
  category: mcp-ecosystem
  source_url: https://github.com/tejzpr/mimir-mcp
  github: tejzpr/mimir-mcp
  version: "Latest"
  verified: "2026-02-04"
  next_review: "2026-05-04"
---

## Overview

Mimir is a Model Context Protocol (MCP) server that provides persistent, git-versioned memory storage for LLM applications. It combines Git's version control with graph-based memory associations, enabling LLMs to maintain long-term memory with full audit trails and relationship tracking.

**Core Value Proposition**: Transform ephemeral AI conversations into persistent, interconnected knowledge bases with complete version history and relationship graphs.

---

## Problem Addressed

| Problem | How Mimir Solves It |
| ------- | ------------------- |
| AI assistants lose context between sessions | Persistent memory storage with git-backed durability |
| No audit trail for AI decisions and learnings | Every memory change is a git commit with full history |
| Difficulty finding related information | Graph-based associations with typed relationships |
| Risk of losing important information | Dual storage (git + SQL index) with remote sync |
| Outdated information pollutes context | Soft delete with archive, supersedes relationships |
| Multi-user memory isolation | Per-user git repositories with configurable access |

---

## Key Statistics (as of 2026-02-04)

| Metric | Value |
| ------ | ----- |
| GitHub Stars | 1 |
| Forks | 0 |
| Open Issues | 0 |
| Primary Language | Go (1.24+) |
| Created | 2026-02-03 |
| Last Push | 2026-02-03 |
| Repository Size | 1,065 KB |
| MCP Tools | 7 |

**Note**: Very new project (1 day old at research time). Statistics expected to change rapidly.

---

## Key Features

### Memory Management

- **7 Human-Aligned MCP Tools**: Tools express intent rather than implementation
  - `mimir_recall` - "What do I know about X?" (semantic search)
  - `mimir_remember` - "Store this for later" (create/update)
  - `mimir_history` - "When did I learn about X?" (temporal queries)
  - `mimir_connect` - "These are related" (link memories)
  - `mimir_forget` - "No longer relevant" (soft delete/archive)
  - `mimir_restore` - "Bring back that archived memory" (undelete)
  - `mimir_sync` - "Sync with remote" (manual git sync)

### Storage Architecture

- **Git-Backed Primary Storage**: Every memory change is a commit
- **SQL Index**: SQLite (development) or PostgreSQL (production)
- **Dual Storage**: Git repository (primary) + SQL database (index)
- **Auto-Sync**: Hourly synchronization to GitHub with PAT authentication
- **Encryption**: 32-character encryption key for sensitive data

### Memory Format

Memories stored as Markdown files with YAML frontmatter:

```markdown
---
id: project-alpha-kickoff-2024-01-15
title: "Project Alpha Kickoff Meeting"
tags: [project, meeting]
created: 2024-01-15T10:30:00Z
updated: 2024-01-15T14:00:00Z
associations:
  - target: contact-john-doe
    type: person
    strength: 1.0
---

# Project Alpha Kickoff Meeting
[Content...]
```

### Graph Associations

- **7 Relationship Types**: `related`, `references`, `follows`, `supersedes`, `part_of`, `person`, `project`
- **Typed Connections**: Link memories with semantic relationships
- **N-Hop Queries**: Traverse memory associations across multiple levels
- **Supersedes Chain**: Automatically marks old memories as outdated when replaced

### Authentication

- **Local Mode**: Development use with system user (whoami)
- **SAML 2.0**: Production authentication with DUO/Okta support
- **Multi-User Mode**: `ACCESSING_USER` environment variable for user isolation
- **Token Management**: Configurable token TTL (default 24 hours)

### Deployment Options

- **Native Binary**: Build from source with `make build`
- **Go Run**: `go run github.com/tejzpr/mimir-mcp/cmd/server@latest`
- **Docker Container**: `docker run tejzpr/mimir-mcp`
- **stdio Mode**: Default for MCP client integration
- **HTTP Mode**: Web interface with authentication UI

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────┐
│                      MCP Client                              │
│              (Cursor, Claude Desktop, etc.)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                    stdio / HTTP transport
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Mimir MCP Server                         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ mimir_recall│  │mimir_remember│  │  mimir_connect     │  │
│  │ mimir_history│ │mimir_forget │  │  mimir_sync        │  │
│  │ mimir_restore│ │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Memory Service Layer                    │    │
│  │   - Search (topic, exact, list_all, path)           │    │
│  │   - CRUD operations with slugs                      │    │
│  │   - Association management                          │    │
│  │   - History and temporal queries                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                                       ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│   SQL Database Index    │           │   Git Repository        │
│                         │           │                         │
│  - SQLite (dev)         │           │  ~/.mimir/store/        │
│  - PostgreSQL (prod)    │           │    mimir-{username}/    │
│  - Full-text search     │           │      2024/01/           │
│  - Relationship graph   │           │      tags/              │
│                         │           │      archive/           │
└─────────────────────────┘           └─────────────────────────┘
                                                  │
                                        Auto-sync (hourly)
                                                  │
                                                  ▼
                                      ┌─────────────────────────┐
                                      │    GitHub Remote        │
                                      │    (with PAT auth)      │
                                      └─────────────────────────┘
</eg>

### Directory Structure

<eg>
~/.mimir/
├── configs/
│   └── config.json              # User configuration
├── db/
│   └── mimir.db                 # SQLite database (index)
└── store/
    └── mimir-{username}/        # User's git repository
        ├── 2024/
        │   └── 01/              # Date-organized memories
        ├── tags/
        │   └── meetings/        # Tag-based organization
        └── archive/             # Soft-deleted memories
</eg>

---

## Installation and Usage

### Build from Source

```bash
make setup    # Run initial setup
make deps     # Install dependencies
make build    # Build the binary
```

### MCP Client Configuration

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mimir": {
      "command": "/path/to/bin/mimir",
      "env": {
        "ENCRYPTION_KEY": "your-32-char-encryption-key-here"
      }
    }
  }
}
```

**Docker Mode**:

```json
{
  "mcpServers": {
    "mimir": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/yourname/.mimir:/home/mimir/.mimir",
        "-e", "ENCRYPTION_KEY=your-32-char-encryption-key-here",
        "tejzpr/mimir-mcp"
      ]
    }
  }
}
```

### Tool Usage Examples

**Recall (Search)**:

```json
{
  "topic": "authentication approach",
  "limit": 10
}
```

**Remember (Store)**:

```json
{
  "title": "Project Alpha Kickoff",
  "content": "# Meeting Notes\n\nDiscussed project timeline...",
  "tags": ["project", "meeting"],
  "replaces": "old-meeting-notes"
}
```

**Connect (Link)**:

```json
{
  "from": "project-alpha",
  "to": "contact-john-doe",
  "relationship": "person"
}
```

**History (Temporal)**:

```json
{
  "slug": "project-alpha",
  "show_changes": true,
  "since": "7d"
}
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Cross-Session Memory**: Enable Claude Code to remember decisions, solutions, and context across conversations
2. **Project Knowledge Base**: Build persistent, searchable knowledge graphs for complex projects
3. **Decision Audit Trail**: Track why decisions were made with full git history
4. **Team Knowledge Sharing**: Multi-user mode enables shared memory across team members

### Patterns Worth Adopting

1. **Human-Aligned Tool Design**: Tools express intent ("What do I know about X?") rather than implementation ("SELECT FROM memories WHERE...")
2. **Supersedes Relationships**: Clean handling of outdated information without deletion
3. **Git-Based Persistence**: Leverage existing version control for AI memory durability
4. **Dual Storage Architecture**: Index for speed, git for durability and audit
5. **Proactive Memory Protocol**: "Recall before answering, store after solving"

### Integration Opportunities

1. **Claude Code Plugin**: Could extend existing context-management approaches in this repository
2. **Skill Memory**: Skills could persist learned patterns and user preferences
3. **Session Continuity**: Hook into session start/end for automatic memory sync
4. **Research Curation**: Use for curating and linking research findings (like this directory)

### Comparison to Existing Solutions

| Feature | Mimir MCP | Claude-Mem | Notes |
| ------- | --------- | ---------- | ----- |
| Storage | Git + SQL | SQLite + Chroma | Mimir has full version control |
| Graph Relations | Yes (7 types) | No | Mimir enables knowledge graphs |
| Supersedes Chain | Yes | No | Clean outdated info handling |
| Multi-User | Yes | No | Team sharing possible |
| Compression | No | Yes (15K stars) | Claude-Mem optimizes token usage |
| Maturity | Very new | Established | Claude-Mem more battle-tested |

---

## Prompt Integration

The repository includes sample prompts for AI assistants:

### Key Behaviors (from SAMPLE_MCP_PROMPT.md)

1. **Check first** - Use `mimir_recall` before answering questions
2. **Store valuable info** - Decisions, solutions, context, action items
3. **Supersede, don't duplicate** - Use `replaces` param when updating
4. **Connect while storing** - Use `connections` param to link memories

### Do Not Store

- Credentials/secrets
- Anything user doesn't want stored

---

## References

1. **GitHub Repository**: <https://github.com/tejzpr/mimir-mcp> (accessed 2026-02-04)
2. **Docker Hub Image**: <https://hub.docker.com/r/tejzpr/mimir-mcp> (accessed 2026-02-04)
3. **README Documentation**: <https://raw.githubusercontent.com/tejzpr/mimir-mcp/main/README.md> (accessed 2026-02-04)
4. **Sample MCP Prompt**: <https://raw.githubusercontent.com/tejzpr/mimir-mcp/main/SAMPLE_MCP_PROMPT.md> (accessed 2026-02-04)
5. **Sample Cursor Rule**: <https://raw.githubusercontent.com/tejzpr/mimir-mcp/main/SAMPLE_CURSOR_RULE.md> (accessed 2026-02-04)
6. **GitHub API Repository Data**: <https://api.github.com/repos/tejzpr/mimir-mcp> (accessed 2026-02-04)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [empirica](../agent-infrastructure/empirica.md) | agent-infrastructure | referenced by empirica (agent-infrastructure) |
| [wigolo](./wigolo.md) | mcp-ecosystem | referenced by wigolo (mcp-ecosystem) |
