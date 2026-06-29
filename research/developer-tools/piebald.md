---
title: "Piebald - Cross-Platform Agentic AI Desktop Client"
research_date: "2026-02-23"
source_url: "https://piebald.ai"
github_url: "<https://github.com/Piebald-AI/piebald> (issue tracker; application is closed-source)"
documentation_url: "https://docs.piebald.ai"
version_at_research: "v0.1.19"
license: "Proprietary (Free + Pro tiers)"
last_verified: "2026-02-23"
version_at_verification: "v0.1.19"
next_review: "2026-05-23"
---

## Overview

Piebald is a closed-source, cross-platform desktop application for agentic AI coding that lets developers orchestrate parallel agents, exercise fine-grained control over context and inference parameters, and use multiple AI provider subscriptions including Claude Pro/Max, ChatGPT Pro/Plus, and Google AI directly without a separate API key. Unlike CLI-based tools, Piebald is fully cross-platform — including native Windows support without WSL or Git Bash — and persists all sessions (including pending tool-call approvals) across machine reboots.

**Core Value Proposition**: Full developer control over every layer of the agentic loop — providers, inference parameters, MCP tools, system prompts, and agent skills — in a single cross-platform GUI with built-in session persistence and HTTP-level traffic inspection.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding agents lose progress when the machine reboots or the app crashes | Persistent sessions with preserved tool-call approval state across reboots |
| Prompt drafts are lost when switching between chats | Auto-saved draft prompts; return to any in-progress prompt from any chat |
| Using AI subscriptions (Claude Max, ChatGPT Plus) requires reverse-engineering or unofficial wrappers | Official OAuth sign-in for Claude, ChatGPT, Google, and GitHub Copilot subscriptions |
| Agentic tools lock you into a single model or provider | Multi-provider: OpenAI (completions + responses API), Anthropic, Google, Amazon Bedrock, GitHub Copilot |
| No visibility into what HTTP requests the agent loop actually sends | Pro: real-time HTTP traffic inspector with request/response bodies, headers, SSE chunks, and durations |
| System prompt, temperature, and other inference params cannot be changed without code | Per-chat and per-profile customization of system prompt, temperature, stop sequences, max tokens, and custom JSON fields |
| Switching between different tool sets requires reconfiguration every session | Profiles: reusable collections of config and MCP tool selections, switchable per-chat |
| Windows users must install WSL or Git Bash to use AI coding CLIs | Native Windows support (EXE + portable ZIP) without any Unix compatibility layer |
| Context window fills up during long sessions, requiring manual intervention | Manual compaction with custom instructions and configurable auto-compaction threshold |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Latest Release | v0.1.19 | 2026-02-23 |
| Release Date | 2026-02-19 | 2026-02-23 |
| Supported Platforms | macOS (Universal), Windows 64-bit, Linux 64-bit | 2026-02-23 |
| AI Providers | OpenAI, Anthropic, Google, Amazon Bedrock, GitHub Copilot | 2026-02-23 |
| OAuth Subscriptions | Claude Pro/Max, ChatGPT Pro/Plus, Google AI Free/Pro/Ultra | 2026-02-23 |
| Company | Piebald LLC | 2026-02-23 |
| License | Proprietary (Free + Pro tiers) | 2026-02-23 |
| GitHub Repository | Issue tracker only (application closed-source) | 2026-02-23 |

---

## Key Features

### Session Management

- **Persistent sessions**: All sessions visible in sidebar with preserved status; pending tool-call approvals survive machine reboots
- **Auto-saved prompts**: All prompts saved as you type; return to any in-progress draft after switching chats
- **Active chats view**: Dedicated view for currently running or attention-needed sessions
- **Chat branching**: Branch any conversation at any message point to explore alternative paths
- **Chat tagging**: Automatic and manual tagging with model-assisted tag selection (Pro)
- **Chat continuation**: Resume a completed chat while preserving the full prior context (Pro)

### Provider and Model Support

- **Multi-provider**: OpenAI (completions and responses APIs), Anthropic, Google Gemini, Amazon Bedrock, GitHub Copilot
- **OAuth subscriptions**: Sign in directly to Claude Pro/Max, ChatGPT Pro/Plus, and Google AI Free/Pro/Ultra — no API key needed
- **New models instantly**: Claude and ChatGPT subscription models available as soon as they are released
- **Custom compatible APIs**: Any OpenAI-compatible API endpoint supported

### Fine-Grained Configuration

- **Inference controls**: Per-chat and per-profile customization of system prompt, temperature, stop sequences, max tokens, and custom provider-specific JSON override fields
- **Profiles**: Reusable configuration sets (system prompt + tool selection); switch per-chat (e.g., a "Chatting" profile with only `web_fetch`)
- **MCP server and tool control**: Enable/disable specific MCP servers and individual tools per chat and per profile
- **AGENTS.md support**: Project-wide agent instructions loaded automatically

### Agentic Capabilities

- **Subagents**: Orchestrate parallel subagents within a single Piebald session (added v0.1.18)
- **Agent Skills**: Load [agentskills.io](https://agentskills.io/home) compatible skills to augment agent capabilities
- **Plan mode**: `ProposePlanToUser` built-in tool for plan/approval loops before execution
- **Compaction**: Manual compaction with custom instructions; auto-compaction on configurable context usage threshold
- **AskUserQuestion**: Built-in tool for agents to interactively request clarification mid-task
- **Live interactive terminal**: Terminal commands run live and interactively, not buffered until completion (added v0.1.17)
- **Streamed tool calls**: Tool call output streams in real-time (added v0.1.17)

### Developer Ergonomics

- **@-mentioning**: Reference files by `@` prefix with autocomplete
- **Rich-text editor**: Full-featured prompt editor with markdown and code support
- **Web search and fetch**: Built-in `web_search` and `web_fetch` tools for agents without extra MCP servers
- **Message quoting**: Quote any assistant message selection to include in the next prompt
- **Message reactions**: React to model messages with emojis; model can react back
- **Font customization**: App-wide font configuration (added v0.1.18)
- **Desktop notifications**: Notify when attention-needed chats require input (added v0.1.11)

### Pro Features

- **HTTP traffic inspector**: Real-time view of all agentic HTTP requests, responses, headers, status codes, durations, and streamed SSE chunks; retention and history
- **Pausing the agentic loop**: Pause execution mid-loop and resume or modify before continuing
- **Diff editor**: Use diffs instead of Monaco editor for file edits
- **Clickable file references**: File paths in agent output are clickable and show contents on hover
- **Chat relocation and duplication**: Move or duplicate chats between projects (added v0.1.7)
- **Filtering chats by tags**: Search and filter session sidebar by auto-assigned or manual tags (added v0.1.9)
- **GitHub-flavored callout blocks**: Alert/callout rendering in chat output (added v0.1.9)
- **"Continue" link**: Auto-offered when agent response ends mid-thought without a tool call (added v0.1.19)

### Cross-Platform

- **Native Windows**: EXE installer and portable ZIP; no WSL or Git Bash required
- **macOS Universal**: Single binary for Apple Silicon and Intel
- **Linux**: AppImage, DEB, and RPM packages

---

## Technical Architecture

<eg>
┌──────────────────────────────────────────────────────────────────────────┐
│                        Piebald Desktop Application                        │
│                   (cross-platform; Electron or Tauri/framework TBD)       │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      GUI / Session Manager                           │  │
│  │                                                                      │  │
│  │  - Multi-chat sidebar with status badges (working/done/needs input)  │  │
│  │  - Draft prompt auto-save per chat                                   │  │
│  │  - Rich-text prompt editor with @-mention autocomplete               │  │
│  │  - Chat branching and continuation                                   │  │
│  │  - Tag-based organization (auto + manual, model-assigned)            │  │
│  │  - Profile switcher (config + MCP tool sets)                         │  │
│  │  - Per-chat MCP enable/disable controls                              │  │
│  └──────────────────────────┬───────────────────────────────────────────┘  │
│                              │                                              │
│  ┌───────────────────────────v─────────────────────────────────────────┐  │
│  │                      Agentic Loop Engine                              │  │
│  │                                                                      │  │
│  │  - Provider abstraction (OpenAI completions/responses, Anthropic,    │  │
│  │    Google, Bedrock, GitHub Copilot, custom compatible)               │  │
│  │  - OAuth credential manager (Claude Max, ChatGPT Plus, Google AI)   │  │
│  │  - Built-in tools: web_search, web_fetch, AskUserQuestion           │  │
│  │  - Tool approval gate with reboot-persistent pending state           │  │
│  │  - Subagent spawning and result aggregation (v0.1.18+)              │  │
│  │  - Plan mode via ProposePlanToUser built-in                          │  │
│  │  - Manual and auto-compaction with custom instructions               │  │
│  └──────────────────────────┬───────────────────────────────────────────┘  │
│                              │                                              │
│  ┌───────────────────────────v─────────────────────────────────────────┐  │
│  │                   Pro: HTTP Traffic Inspector                          │  │
│  │                                                                      │  │
│  │  - All LLM provider HTTP requests, responses, headers, status codes  │  │
│  │  - Streamed SSE chunks with per-chunk intervals                      │  │
│  │  - Configurable retention of traffic history                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
</eg>

### Key Architectural Decisions

1. **OAuth subscription bridging**: Piebald authenticates directly with Claude, ChatGPT, and Google AI subscription portals (not the provider API), enabling use of consumer-tier subscriptions (Claude Max, ChatGPT Plus) without an API key. This expands access for developers who have subscriptions but no API billing.

2. **Session persistence to disk**: All session state — including tool calls awaiting approval — is written to disk so it survives app crashes and machine reboots. This is architecturally distinct from in-memory-only CLI tools.

3. **Profile-based MCP control**: MCP server/tool selection is a first-class profile concept, not a global toggle. This enables creating purpose-built profiles (e.g., a "Coding" profile with full tools, a "Chat" profile with none) without reconfiguring per session.

4. **HTTP-layer transparency (Pro)**: Rather than providing high-level "token usage" summaries, the Pro tier exposes the actual HTTP wire traffic. This enables debugging of token usage, inference parameters, and provider-specific behavior at the protocol level.

---

## Installation & Usage

### Download

Available at <https://piebald.ai/downloads>:

- **macOS Universal**: DMG or `.app.tar.gz`
- **Windows 64-bit**: EXE installer or portable ZIP (no WSL required)
- **Linux 64-bit**: AppImage, DEB, or RPM

### Getting Started

1. Download and install for your platform
2. Launch Piebald and go to **Settings → Providers**
3. Add a provider via API key or OAuth subscription sign-in
4. Open or create a project directory
5. Start a new chat and begin working

### Agent Skills

Piebald supports [agentskills.io](https://agentskills.io/home) compatible skills:

<eg>
Settings → Skills → Add Skill Directory
</eg>

Load skill directories from the filesystem; skills augment the agent's capabilities for the duration of the session.

### Profiles Example

Create a "Chatting" profile to avoid the model searching the codebase for simple questions:

<eg>
Settings → Profiles → New Profile → "Chatting"
  Tools: web_fetch, web_search only
  System prompt: "Answer technical questions concisely."
</eg>

Switch profile per chat via the chat configuration panel.

---

## Relevance to Claude Code Development

### Applications

1. **AgentSkills.io compatibility**: Piebald explicitly supports loading [agentskills.io](https://agentskills.io/home) skills — the same skill format this repository targets. Skills developed here are directly testable in Piebald, making it a native validation environment for skill development work.

2. **HTTP traffic debugging for skill development**: The Pro HTTP traffic inspector exposes raw LLM request/response cycles, useful for diagnosing when a skill's prompt is being misinterpreted, when context window limits are being hit, or when provider-specific parameters are not behaving as expected.

3. **Windows-native testing target**: Piebald's native Windows support (no WSL) means it represents a substantial segment of developers who may not have access to Claude Code CLI on Windows. Skills that work in Piebald should be validated for Windows path separator and shell differences.

4. **Subagent orchestration reference**: The subagent support added in v0.1.18 provides a reference implementation of parallel agent orchestration in a GUI context, complementing the CLI-based swarm patterns documented in the orchestrator skill.

### Patterns Worth Adopting

1. **Profile-based tool isolation**: The pattern of creating named profiles with specific tool subsets addresses the "model uses search tools for simple questions" problem that skills often need to guard against. This is a configuration-level solution worth documenting as a usage pattern in skill guides targeting Piebald.

2. **Reboot-persistent pending state**: Persisting tool approval gates across reboots is a robustness pattern for long-running agentic tasks. Skills designed for long tasks should be tolerant of session interruptions, consistent with this persistence model.

3. **Draft prompt auto-save**: The auto-save-as-you-type prompt pattern addresses context loss from accidental navigation. Skill UX guidance should note that complex multi-line prompts are safer to compose in tools with this feature.

### Integration Opportunities

1. **Skill testing workflow**: Add Piebald as a recommended local testing environment for skills developed in this repository, alongside Claude Code CLI, given its first-class agentskills.io support.

2. **AgentSkills.io format validation**: Piebald's skill loader is a live validation target for the `SKILL.md` frontmatter format. Skills that load and trigger correctly in Piebald confirm agentskills.io spec compliance.

3. **Competitive context for GUI comparisons**: Piebald, Yume, and Claude Code GUI provide three distinct points in the GUI-for-agentic-coding design space. Cross-referencing features (profiles vs. config files, HTTP inspector vs. none, OAuth subscriptions vs. API keys) helps with capability and design documentation.

### Considerations

1. **Closed-source**: The application is not open source; implementation patterns are not directly inspectable. The GitHub repository is an issue tracker only. Feature descriptions are based on official website and changelog documentation.

2. **Evolving rapidly**: Piebald has released 19 versions with weekly cadence since inception, adding major features (subagents, branching, multi-provider OAuth) in successive releases. Feature availability may differ from this documentation within weeks.

3. **Pro feature gating**: Several capabilities relevant to skill development (HTTP inspector, traffic retention, agentic loop pausing) require the Pro tier, whose pricing was not publicly available on the pricing page at time of research.

4. **Session persistence mechanism**: The specific technology used for cross-reboot persistence is not documented. The reliability of this mechanism under edge cases (corrupt disk, mid-write crash) is unknown.

---

## References

- [Piebald Official Website](https://piebald.ai) (accessed 2026-02-23)
- [Piebald Downloads Page](https://piebald.ai/downloads) (accessed 2026-02-23)
- [Piebald Roadmap](https://docs.piebald.ai/roadmap) (accessed 2026-02-23)
- [Piebald GitHub Issue Tracker](https://github.com/Piebald-AI/piebald) (accessed 2026-02-23)
- [AgentSkills.io](https://agentskills.io/home) (accessed 2026-02-23)

---
