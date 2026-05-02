---
title: Claude Brain
description: Give Claude Code photographic memory in ONE portable file. Session-aware memory engine built on memvid.
resource_url: https://github.com/memvid/claude-brain
repository: https://github.com/memvid/claude-brain
topics:
  - context-management
  - memory-persistence
  - claude-code-plugin
  - ai-memory
  - portable-memory
author: Memvid <hello@memvid.com>
license: MIT
published_date: 2025-12-18
---

## Overview

Claude Brain is a Claude Code plugin that adds persistent, searchable memory to Claude Code sessions. It stores all session context, decisions, bugs, and solutions in a single portable `.mv2` file at `.claude/mind.mv2`, enabling Claude to retain context across sessions without relying on cloud storage, databases, or API keys.

The plugin integrates via three lifecycle hooks: SessionStart (injects past context), PostToolUse (captures observations from tool usage), and Stop (saves session summary). All memory is local-only and survives project transfers, git commits, and handoffs to teammates.

---

## Problem Addressed

Claude Code provides a 200K context window but zero memory between sessions. Developers must re-explain previous work, repeat debugging steps, and restate architectural decisions in every new session. Claude Brain solves this by capturing observations automatically and re-injecting relevant context at session start.

SOURCE: "200K context window. Zero memory between sessions. You're paying for a goldfish with a PhD." (README.md, accessed 2026-05-02)

---

## Key Statistics

- **Version**: v1.0.11 (latest)
- **Latest Release**: v1.0.7 published 2026-01-05
- **GitHub Stars**: 482 (as of 2026-05-02)
- **License**: MIT (Copyright 2025 Memvid)
- **Repository**: <https://github.com/memvid/claude-brain>
- **File Size**: Empty file ~70KB; grows ~1KB per memory; full year of use stays under 5MB

SOURCE: package.json v1.0.11, GitHub API repos/memvid/claude-brain (accessed 2026-05-02), README.md FAQ section (accessed 2026-05-02)

---

## Key Features

### Single-File Memory Storage

Memory is stored in one file (`.claude/mind.mv2`) at the project root under `.claude/`. No database, cloud service, or API keys required. The file is:
- **Versionable**: Commit to git, preserving memory in project history
- **Portable**: Transfer via `scp`, email, or git clone for instant teammate onboarding
- **Compact**: ~70KB empty, grows ~1KB per captured memory; one year of typical use stays under 5MB

SOURCE: README.md lines 69-75, FAQ section (accessed 2026-05-02)

### Four Built-In Commands

Four slash commands are available in Claude Code after installation:

1. `/mind stats` — View memory statistics (total observations, sessions, memory composition)
2. `/mind search "<query>"` — Full-text search of past context (returns top matches with relevance scores)
3. `/mind ask "<question>"` — Ask your memory a question in natural language
4. `/mind recent` — Display timeline of recent memories

Commands can also be invoked naturally in chat: "mind stats", "search my memory for auth bugs", etc.

SOURCE: README.md lines 94-100 (accessed 2026-05-02)

### Automatic Observation Capture

The PostToolUse hook captures observations from tool outputs without explicit user action. Observations are classified into 10 types:

- `discovery` — New information discovered
- `decision` — Decision made
- `problem` — Problem identified
- `solution` — Solution implemented
- `pattern` — Pattern recognized
- `warning` — Warning or concern
- `success` — Successful outcome
- `refactor` — Code refactored
- `bugfix` — Bug fixed
- `feature` — Feature added

Captured tools include: Read, Edit, Write, Update, Bash, Grep, Glob, WebFetch, WebSearch, Task, NotebookEdit. Observations are compressed using "ENDLESS MODE" to store 20x more context in the same space.

SOURCE: src/types.ts lines 18-29, src/hooks/post-tool-use.ts lines 6, 24-36 (accessed 2026-05-02)

### Context Injection at Session Start

At session start, the SessionStart hook injects relevant past context without requiring SDK load (< 1 second overhead). The hook displays:
- Project name
- Memory file size and location
- Available commands
- Status indicator (active or ready to create)

No user action required; context is automatically injected as additional system context.

SOURCE: src/hooks/session-start.ts (accessed 2026-05-02)

### Optional CLI for Power Users

An optional CLI tool (`memvid-cli`) provides direct access to memory files outside Claude Code:

```bash
npm install -g memvid-cli
memvid stats .claude/mind.mv2           # View memory statistics
memvid find .claude/mind.mv2 "auth"     # Search memories
memvid ask .claude/mind.mv2 "why JWT?"  # Ask questions
memvid timeline .claude/mind.mv2        # View timeline
```

[Full CLI reference →](https://docs.memvid.com/cli/cheat-sheet)

SOURCE: README.md lines 105-120 (accessed 2026-05-02)

### Privacy and Performance

- **100% local**: Nothing leaves your machine; all memory is stored on-device
- **Sub-millisecond search**: Native Rust core; searches 10K+ memories in <1ms
- **No external dependencies**: Works offline; no API keys or cloud services required

SOURCE: README.md FAQ section (accessed 2026-05-02)

---

## Technical Architecture

### Core Components

Claude Brain is built on top of **memvid** — a single-file memory engine written in Rust. The plugin wraps the memvid SDK (`@memvid/sdk ^2.0.149`) with Claude Code integrations.

**Key classes and types**:

1. **Mind** — Main engine class (src/core/mind.ts)
   - `Mind.open()` — Open or create memory file
   - `remember(observation)` — Store an observation
   - `getContext(query)` — Retrieve context for a query
   - `search(term)` — Full-text search memories
   - `stats()` — Get memory statistics

2. **Observation** — Data structure for captured memories
   - `id`: Unique identifier
   - `timestamp`: When captured
   - `type`: ObservationType (one of 10 types)
   - `tool`: Which tool produced this observation (Read, Edit, Bash, etc.)
   - `summary`: Short description
   - `content`: Full content
   - `metadata`: File list, functions, confidence score, tags, session ID

3. **SessionSummary** — Session closure record
   - `id`: Session ID
   - `startTime`, `endTime`: Session duration
   - `observationCount`: Total observations in session
   - `keyDecisions`: Array of major decisions made
   - `filesModified`: List of edited files
   - `summary`: Natural language summary of work

4. **InjectedContext** — Context returned at session start
   - `recentObservations`: Last N observations (configurable, default 20)
   - `relevantMemories`: Observations matched by search (updated dynamically)
   - `sessionSummaries`: Previous session records
   - `tokenCount`: Estimated tokens in injected context

SOURCE: src/types.ts, src/core/mind.ts (accessed 2026-05-02)

### Three Lifecycle Hooks

Claude Brain integrates via hooks.json (src/hooks/hooks.json) with three event handlers:

1. **SessionStart Hook** (`session-start.ts`)
   - Runs at Claude session startup
   - Timeout: 5 seconds
   - Fast path: Checks memory file existence without loading SDK
   - Injects context as `additionalContext` into the SessionStart hook output
   - Displays memory status and available commands

2. **PostToolUse Hook** (`post-tool-use.ts`)
   - Runs after every tool execution
   - Timeout: 10 seconds
   - Captures observation from tool output (if output is non-trivial)
   - Compresses output using ENDLESS MODE compression
   - Deduplicates observations (1-minute window to avoid re-capturing same tool call)
   - Writes to memory file via memvid SDK

3. **Stop Hook** (`stop.ts`)
   - Runs when Claude session ends
   - Timeout: 30 seconds
   - Generates session summary from accumulated observations
   - Saves summary to memory file
   - Prunes old backup files (keeps 3 most recent)

Smart-install hook runs on SessionStart to auto-install dependencies if needed.

SOURCE: src/hooks/hooks.json, CONTRIBUTING.md lines 37-42 (accessed 2026-05-02)

### Configuration

Default memory configuration (src/types.ts):

```typescript
{
  memoryPath: ".claude/mind.mv2",
  maxContextObservations: 20,        // Inject up to 20 past observations
  maxContextTokens: 2000,            // Cap injected context at 2000 tokens
  autoCompress: true,                // Compress observations automatically
  minConfidence: 0.6,                // Store observations with ≥60% confidence
  debug: false                       // Enable debug logging
}
```

All configuration is customizable per project via environment variables or the MindConfig interface.

SOURCE: src/types.ts lines 78-84 (accessed 2026-05-02)

### Data Flow

```
Tool Execution → PostToolUse Hook → Classify Output → Compress → Deduplicate → Store in Memory File
                                                                                         ↓
Session Start → SessionStart Hook → Read Memory File → Inject Context → Prepend to System Prompt
                                                                                         ↑
Session End → Stop Hook → Summarize Session → Append Summary to Memory File ← Prune Backups
```

Compression uses ENDLESS MODE (memvid feature) to fit 20x more context into the same file space. Deduplication uses a 1-minute in-memory cache to avoid storing duplicate observations of the same tool call.

SOURCE: src/hooks/post-tool-use.ts lines 1-80, src/hooks/session-start.ts, src/core/mind.ts (accessed 2026-05-02)

---

## Installation & Usage

### Plugin Installation (30 seconds)

1. Ensure git is configured (one-time setup):
   ```bash
   git config --global url."https://github.com/".insteadOf "git@github.com:"
   ```

2. In Claude Code, run:
   ```bash
   /plugin add marketplace memvid/claude-brain
   ```

3. Go to `/plugins` → Installed → **mind** → Enable Plugin → Restart Claude Code.

Memory file (`.claude/mind.mv2`) is created automatically in `.claude/` on first observation.

SOURCE: README.md lines 50-62 (accessed 2026-05-02)

### Basic Commands

```bash
# In Claude Code chat
/mind stats                       # Show memory statistics
/mind search "authentication"     # Find past context
/mind ask "why did we choose X?"  # Ask your memory
/mind recent                      # View timeline
```

Or use natural language: "mind stats", "search my memory for auth bugs".

SOURCE: README.md lines 94-100 (accessed 2026-05-02)

### Reset Memory

To clear all memories and start fresh:
```bash
rm .claude/mind.mv2
```

The file will be recreated on the next observation.

SOURCE: README.md FAQ section (accessed 2026-05-02)

### CLI Installation (Optional)

For power users who want direct access outside Claude Code:

```bash
npm install -g memvid-cli
memvid stats .claude/mind.mv2
memvid find .claude/mind.mv2 "bug"
memvid ask .claude/mind.mv2 "what architecture did we choose?"
memvid timeline .claude/mind.mv2
```

SOURCE: README.md lines 105-120 (accessed 2026-05-02)

---

## Relevance to Claude Code Development

Claude Brain directly addresses a core pain point in Claude Code-assisted development: the loss of session context between conversations. It is particularly relevant for:

1. **Long-form Projects**: Multi-session feature development, architecture decisions, and bug fixes are automatically recorded and available without manual documentation.

2. **Debugging Workflows**: When revisiting a bug or issue, `/mind search` retrieves previous debugging steps, error traces, and attempted fixes without requiring manual context re-entry.

3. **Decision Tracking**: Architectural choices, technology selections, and trade-off decisions are captured as observations and can be re-stated with exact rationale from previous sessions.

4. **Team Onboarding**: Memory files can be committed to git or shared directly, allowing new team members to understand project history and decisions without running the entire development session again.

5. **Plugin Development**: For developers building Claude Code plugins, Claude Brain serves as a reference implementation of the lifecycle hook system (SessionStart, PostToolUse, Stop).

6. **Context Management Research**: Claude Brain demonstrates practical approaches to selective context injection (20 observations, 2000 tokens) and ENDLESS MODE compression for maximizing context within token limits.

Claude Brain is production-ready and published on the Claude Code plugin marketplace, making it immediately usable in any Claude Code project.

---

## Limitations and Caveats

1. **Single-Project Scope**: Memory is tied to a single project directory. Running Claude Code in a different directory creates a separate memory file. Cross-project context is not supported.

2. **No Automatic Synchronization**: Memory files are not synced across devices. If you clone a project to another machine, you must manually transfer the `.claude/mind.mv2` file or re-create memory from scratch.

3. **Observation Classification Relies on Heuristics**: The `classifyObservationType` function uses rule-based logic to infer observation type (decision, bug, solution, etc.) from tool output. Some observations may be misclassified or marked with low confidence.

4. **Search Relevance**: Full-text search is lexical (substring matching); semantic search is not available in the current version. Highly relevant memories may not surface if keywords are not matched verbatim.

5. **Hook Timeout Constraints**: PostToolUse and Stop hooks have 10- and 30-second timeouts respectively. On extremely large tool outputs or slow storage (network mounts), compression or storage operations may timeout and be skipped.

6. **No Encryption**: Memory files are stored in plaintext binary format (memvid .mv2). Sensitive information in memories is not encrypted at rest; encrypt the `.claude` directory if needed.

7. **One-File Scalability**: While the plugin claims full-year use stays under 5MB, extremely long projects (multiple developers, hundreds of sessions) may exceed this estimate. No horizontal scaling is provided.

SOURCE: README.md FAQ section, src/hooks/post-tool-use.ts timeout configurations, src/types.ts compression defaults (accessed 2026-05-02); "Not mentioned in documentation" for encryption and semantic search (confidence: medium)

---

## References

- [Claude Brain GitHub Repository](https://github.com/memvid/claude-brain) — primary source (accessed 2026-05-02)
- [memvid — Single-File Memory Engine](https://github.com/memvid/memvid) — underlying technology
- [Claude Code Plugin Marketplace](https://claude.ai/plugins) — installation location
- [memvid CLI Cheat Sheet](https://docs.memvid.com/cli/cheat-sheet) — optional CLI reference
- [npm Package: claude-brain v1.0.11](https://www.npmjs.com/package/claude-brain) — published package

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude-Mem](./claude-mem.md) | context-management | Competing persistent memory plugin for Claude Code with progressive disclosure and SQLite+Chroma hybrid search |
| [SimpleMem-Cross](./simplemem-cross.md) | context-management | Alternative memory system with 64% higher LoCoMo benchmark score and 3-tier redaction for sensitive data |
| [Local Memory](./local-memory.md) | context-management | Unified persistent memory infrastructure with MCP/REST/CLI supporting multi-agent knowledge sharing across Claude Desktop/Code/Codex |
| [MemPalace](./mempalace.md) | context-management | Memory system using verbatim palace structure with 96.6% LongMemEval recall; zero API calls with local ChromaDB |
| [Unblocked](./unblocked.md) | context-management | Context engine for coding agents with 27+ integrations (GitHub, Slack, Confluence, Jira, Linear); 48% token reduction |
| [Jina AI](./jina-ai.md) | context-management | Search foundation platform providing Reader API and embedding/reranking infrastructure used by memory systems |
| [SlimContext](./slimcontext.md) | context-management | Zero-dependency TypeScript library for chat history compression; complements memory systems with token optimization |
| [SourceSync.ai](./sourcesyncai.md) | context-management | Managed RAG platform with auto-syncing connectors and hybrid search; alternative to single-file memory stores |

---

## Freshness Tracking

**Last Reviewed**: 2026-05-02
**Next Review**: 2026-08-02 (3 months)

**Confidence Summary**

- **Identity/Metadata**: high — version, license, repository confirmed via package.json and GitHub API
- **Key Features**: high — all feature descriptions extracted from README and source code
- **Technical Architecture**: high — hook system, types, and data structures read from source TypeScript files
- **Installation & Usage**: high — commands verified in README and command files
- **Limitations**: medium — documented limitations are explicit in README; undocumented limitations inferred from architecture (no encryption, single-project scope, lexical search only)

**Data Sources**

All claims in this entry trace to one or more of:
- package.json (v1.0.11, dependencies, scripts)
- README.md (features, FAQ, commands, use cases)
- src/types.ts (Observation, MindConfig, InjectedContext types)
- src/core/mind.ts (Mind class interface)
- src/hooks/*.ts (SessionStart, PostToolUse, Stop implementations)
- CONTRIBUTING.md (hook lifecycle, project structure)
- LICENSE (MIT, copyright)
- GitHub API responses (stars, releases, repository metadata)

No claims are inferred or paraphrased from secondary sources. All factual assertions require a cited extract from the above primary sources.
