# Plannotator

| Field         | Value                                           |
| ------------- | ----------------------------------------------- |
| Research Date | 2026-01-31                                      |
| Primary URL   | <https://plannotator.ai>                        |
| GitHub        | <https://github.com/backnotprop/plannotator>    |
| Version       | No formal releases (monorepo, continuous dev)   |
| License       | BSL 1.1 (Business Source License)               |
| Created       | 2025-12-28                                      |

---

## Overview

Plannotator is an interactive plan review tool for AI coding agents that intercepts agent plans via hooks, displays them in a visual browser-based UI for annotation, and sends structured feedback back to the agent. It supports Claude Code and OpenCode with built-in integrations for Obsidian and Bear Notes for plan archival. The tool also provides code review functionality for git diffs with inline annotations.

---

## Problem Addressed

| Problem                                                | Solution                                                                    |
| ------------------------------------------------------ | --------------------------------------------------------------------------- |
| AI agent plans are text-only, hard to review           | Visual browser-based UI with markdown rendering and syntax highlighting     |
| No structured way to provide plan feedback             | Annotation system: delete, insert, replace, comment operations              |
| Plans disappear after execution                        | Obsidian and Bear Notes integration for automatic plan archival             |
| Team collaboration on agent plans difficult            | URL sharing via compressed hash for shareable annotations                   |
| Code review feedback to agents is unstructured         | Dedicated code review mode with diff viewer and inline annotations          |
| Remote development complicates plan review             | Environment variables for remote/devcontainer support with port forwarding  |
| Agent proceeds without human approval                  | Hook intercepts ExitPlanMode, requires explicit approve/deny action         |
| Feedback to agent lacks context                        | Image attachment support with pen, arrow, circle annotation tools           |

---

## Key Statistics

| Metric           | Value                    | Date Gathered |
| ---------------- | ------------------------ | ------------- |
| GitHub Stars     | 1,538                    | 2026-01-31    |
| GitHub Forks     | 97                       | 2026-01-31    |
| Open Issues      | 30                       | 2026-01-31    |
| Contributors     | 11                       | 2026-01-31    |
| Primary Language | TypeScript               | 2026-01-31    |
| Repository Size  | 25.6 MB                  | 2026-01-31    |
| Repository Age   | 35 days (since Dec 2025) | 2026-01-31    |

---

## Key Features

### Plan Review System

- **Hook Integration**: Intercepts Claude Code `ExitPlanMode` permission request via configurable hooks
- **Visual Plan Display**: Markdown rendering with syntax-highlighted code blocks
- **Annotation Types**: Deletion, insertion, replacement, comment, global comment
- **Redline Mode**: Quick text selection creates deletion annotations
- **Approve/Deny Flow**: Explicit user action required before agent proceeds

### Code Review System (Jan 2026)

- **Git Diff Viewer**: Reviews unstaged changes with multiple diff view modes
- **Inline Annotations**: Select line numbers to add annotations
- **View Modes**: Switch between unified, split, and raw diff views
- **Feedback Submission**: Structured feedback sent to agent session

### Image Annotations

- **Image Attachment**: Attach images with feedback
- **Drawing Tools**: Pen, arrow, circle tools for visual markup
- **Upload Support**: Server-side image handling for agent context

### Note-Taking Integration

- **Obsidian Integration**: Auto-save approved plans with YAML frontmatter
- **Bear Notes Integration**: Alternative note-taking app support
- **Smart Tagging**: Automatic tag extraction from plan title and code languages
- **Backlinks**: Graph connectivity via `[[Plannotator Plans]]` reference

### URL Sharing

- **Compression Pipeline**: JSON -> deflate-raw -> base64 -> URL-safe encoding
- **Full State Sharing**: Shares plan content and all annotations via URL hash
- **Position Restoration**: Finds text positions in DOM to restore highlights
- **Team Collaboration**: Share annotated plans without server persistence

### Remote Development Support

- **Environment Variables**: `PLANNOTATOR_REMOTE`, `PLANNOTATOR_PORT`, `PLANNOTATOR_BROWSER`
- **Fixed Port Mode**: Enables port forwarding for devcontainers, SSH, WSL
- **Manual URL Mode**: Skips auto-browser-open for remote access

---

## Technical Architecture

### Stack Components

| Component          | Technology                              |
| ------------------ | --------------------------------------- |
| Runtime            | Bun                                     |
| Language           | TypeScript                              |
| UI Framework       | React                                   |
| Syntax Highlighting| highlight.js (bundled)                  |
| Text Highlighting  | web-highlighter library                 |
| Build Tool         | Vite (single-file HTML output)          |
| Compression        | CompressionStream API (deflate-raw)     |

### Monorepo Structure

```text
plannotator/
├── apps/
│   ├── hook/                 # Claude Code plugin
│   │   ├── .claude-plugin/   # Plugin manifest
│   │   ├── commands/         # Slash commands (plannotator-review.md)
│   │   ├── hooks/            # PermissionRequest hook config
│   │   └── server/           # Entry point (plan + review subcommands)
│   ├── opencode-plugin/      # OpenCode integration
│   ├── review/               # Standalone review server
│   ├── portal/               # Shared plan viewer (share.plannotator.ai)
│   └── marketing/            # Marketing site (plannotator.ai)
├── packages/
│   ├── server/               # Shared server implementation
│   ├── ui/                   # Shared React components
│   ├── editor/               # Plan review App.tsx
│   └── review-editor/        # Code review UI
└── .claude-plugin/           # Marketplace registration
```

### Hook Flow

```text
Claude calls ExitPlanMode
        |
PermissionRequest hook fires
        |
Bun server reads plan from stdin JSON (tool_input.plan)
        |
Server starts on random port, opens browser
        |
User reviews plan, adds annotations
        |
Approve -> stdout: {"hookSpecificOutput":{"decision":{"behavior":"allow"}}}
Deny    -> stdout: {"hookSpecificOutput":{"decision":{"behavior":"deny","message":"..."}}}
```

### Server API Endpoints

**Plan Server**:

| Endpoint               | Method | Purpose                                        |
| ---------------------- | ------ | ---------------------------------------------- |
| `/api/plan`            | GET    | Returns plan content and origin                |
| `/api/approve`         | POST   | Approve plan with save options                 |
| `/api/deny`            | POST   | Deny plan with structured feedback             |
| `/api/image`           | GET    | Serve uploaded images                          |
| `/api/upload`          | POST   | Upload image for annotation                    |
| `/api/obsidian/vaults` | GET    | Detect available Obsidian vaults               |

**Review Server**:

| Endpoint       | Method | Purpose                              |
| -------------- | ------ | ------------------------------------ |
| `/api/diff`    | GET    | Returns raw patch and git ref        |
| `/api/feedback`| POST   | Submit review with annotations       |

### Data Types

```typescript
enum AnnotationType {
  DELETION = "DELETION",
  INSERTION = "INSERTION",
  REPLACEMENT = "REPLACEMENT",
  COMMENT = "COMMENT",
  GLOBAL_COMMENT = "GLOBAL_COMMENT",
}

interface Annotation {
  id: string;
  blockId: string;
  startOffset: number;
  endOffset: number;
  type: AnnotationType;
  text?: string;
  originalText: string;
  createdAt: number;
  author?: string;
}

interface Block {
  id: string;
  type: "paragraph" | "heading" | "blockquote" | "list-item" | "code" | "hr";
  content: string;
  level?: number;
  language?: string;
  order: number;
  startLine: number;
}
```

---

## Installation and Usage

### Prerequisites

Install the `plannotator` command:

```bash
# macOS / Linux / WSL
curl -fsSL https://plannotator.ai/install.sh | bash

# Windows PowerShell
irm https://plannotator.ai/install.ps1 | iex
```

### Claude Code Plugin Installation

```text
/plugin marketplace add backnotprop/plannotator
/plugin install plannotator@plannotator
```

Restart Claude Code after plugin install.

### Manual Hook Installation

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "plannotator",
            "timeout": 1800
          }
        ]
      }
    ]
  }
}
```

### OpenCode Installation

Add to `opencode.json`:

```json
{
  "plugin": ["@plannotator/opencode@latest"]
}
```

### Environment Variables

| Variable             | Description                                        |
| -------------------- | -------------------------------------------------- |
| `PLANNOTATOR_REMOTE` | Set to `1` for remote mode (fixed port, no auto-open) |
| `PLANNOTATOR_PORT`   | Fixed port (default: random locally, 19432 remote) |
| `PLANNOTATOR_BROWSER`| Custom browser path                                |

### Code Review Usage

```text
/plannotator-review
```

Opens diff viewer for unstaged git changes with annotation support.

---

## Relevance to Claude Code Development

### Direct Applications

1. **Hook System Reference**: Demonstrates production use of Claude Code's `PermissionRequest` hook system for `ExitPlanMode` interception.

2. **Plugin Marketplace Pattern**: Shows complete plugin structure with marketplace.json registration, commands, and hooks configuration.

3. **Plan Feedback Loop**: Establishes a pattern for structured human-in-the-loop plan review before implementation.

4. **Visual Plan Review UX**: Proves value of visual annotation over text-only plan feedback.

5. **Single-File HTML Deployment**: Vite build produces self-contained HTML files for easy hook integration.

### Patterns Worth Adopting

1. **Annotation Type System**: The DELETE/INSERT/REPLACE/COMMENT taxonomy provides structured feedback categories beyond free-text comments.

2. **URL Hash State Sharing**: Compressed state in URL hash enables stateless sharing without server persistence.

3. **Dual-Mode Review**: Separate plan review and code review workflows for different feedback contexts.

4. **Note Integration**: Automatic archival to knowledge management tools (Obsidian) creates searchable execution history.

5. **Remote Session Detection**: Environment variable flags for remote/devcontainer mode is a clean pattern for deployment flexibility.

6. **Block-Based Parsing**: Markdown-to-blocks parsing enables precise annotation positioning.

7. **Cookie Settings**: Using cookies instead of localStorage allows settings persistence across random ports.

### Integration Opportunities

1. **Native Plan Review**: Plannotator's annotation system could inform Claude Code's native plan review UX.

2. **Hook Library**: The hook configuration patterns are reusable for other PermissionRequest interceptions.

3. **Structured Feedback Format**: The annotation export format (`exportDiff`) could become a standard for plan feedback.

4. **Knowledge Integration**: Obsidian/Bear integration pattern applicable to any execution logging.

### Comparison with Native Claude Code

| Aspect           | Plannotator                      | Native Claude Code            |
| ---------------- | -------------------------------- | ----------------------------- |
| Plan Review      | Visual browser UI with annotations | Text-based inline editing    |
| Feedback Format  | Structured annotations           | Free-text                     |
| Archival         | Obsidian/Bear auto-save          | Manual copy                   |
| Collaboration    | URL sharing                      | Session-based                 |
| Code Review      | Dedicated diff viewer            | Inline in conversation        |
| Remote Support   | Environment variable flags       | Native terminal               |
| Setup Required   | Plugin install + restart         | None                          |

---

## References

| Source                 | URL                                                    | Accessed   |
| ---------------------- | ------------------------------------------------------ | ---------- |
| Official Website       | <https://plannotator.ai>                               | 2026-01-31 |
| GitHub Repository      | <https://github.com/backnotprop/plannotator>           | 2026-01-31 |
| GitHub README          | <https://github.com/backnotprop/plannotator/blob/main/README.md> | 2026-01-31 |
| GitHub CLAUDE.md       | <https://github.com/backnotprop/plannotator/blob/main/CLAUDE.md> | 2026-01-31 |
| Hook Installation Docs | <https://github.com/backnotprop/plannotator/blob/main/apps/hook/README.md> | 2026-01-31 |
| GitHub API             | <https://api.github.com/repos/backnotprop/plannotator> | 2026-01-31 |
| LICENSE File           | <https://github.com/backnotprop/plannotator/blob/main/LICENSE> | 2026-01-31 |
| Claude Code Demo       | <https://www.youtube.com/watch?v=a_AT7cEN_9I>          | 2026-01-31 |
| OpenCode Demo          | <https://youtu.be/_N7uo0EFI-U>                         | 2026-01-31 |

**Research Method**: Information gathered from official GitHub repository via GitHub API, README and CLAUDE.md files fetched directly, LICENSE file reviewed for licensing terms. Statistics verified via direct API calls on research date.

---

## Freshness Tracking

| Field              | Value                              |
| ------------------ | ---------------------------------- |
| Version Documented | No formal releases (monorepo)      |
| Last Push          | 2026-01-29                         |
| GitHub Stars       | 1,538 (as of 2026-01-31)           |
| GitHub Forks       | 97 (as of 2026-01-31)              |
| Next Review Date   | 2026-05-01                         |

**Review Triggers**:

- First formal version release
- Significant star growth (5K, 10K milestones)
- New agent platform integrations beyond Claude Code and OpenCode
- Major annotation system changes
- New collaboration features (real-time sync, commenting)
- Changes to hook system or plugin structure
- BSL license change date (2030-01-01 conversion to open source)
- Breaking changes to API endpoints
- Native Claude Code plan review feature release (competitive context)
