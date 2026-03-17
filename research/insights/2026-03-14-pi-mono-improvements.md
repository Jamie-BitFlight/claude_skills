# Improvement Proposals: Pi Monorepo

**Research entry**: ./research/agent-frameworks/pi-mono.md
**Generated**: 2026-03-14
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 5

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Agent Runtime Architecture — context transformation pipeline (`transformContext()` / `convertToLlm()`) separating message preparation from LLM submission | Low | Pi's TypeScript runtime architecture (programmatic message pipeline with event streaming) is fundamentally different from this repo's prompt-based delegation model. The local SAM workflow delegates via text prompts to sub-agents, not via a programmatic message transformation pipeline. To raise confidence, one would need to identify a concrete failure mode in the local system caused by the absence of explicit context transformation — e.g., sub-agents receiving irrelevant context that causes errors or wasted tokens. No such failure mode was observed in the local files. |
| Extension System — Pi Packages bundling templates, skills, extensions, themes into shareable npm packages | Low | The local system already has a plugin marketplace format (`plugin.json` + `marketplace.json`) that bundles skills, agents, hooks, and MCP servers into installable packages. Pi's "Pi Package" concept bundles prompt templates, skills, extensions, themes, and configuration into a single npm package — functionally equivalent to the local plugin directory structure. To raise confidence, one would need evidence that the local packaging model is missing a concrete capability that Pi Packages provide (e.g., cross-plugin dependency resolution, versioned template sharing). No such gap was confirmed. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Coding Agent Pattern (`read`, `write`, `edit`, `bash` tool set) | Already covered — Claude Code uses the identical core tool set. No gap exists. |
| TUI Framework (differential rendering, flicker-free synchronized output) | Not applicable — this repo's skills and agents are text/markdown-based prompts, not terminal UI applications. The TUI pattern addresses a different domain (interactive terminal rendering) that has no local system equivalent to improve. |
| Multi-Provider LLM Abstraction (unified API across providers) | Already in backlog as #108 "SAM: Multi-Model Strategy" |
| Session Persistence and Branching (session branching, message compaction) | Already tracked in backlog: #113 "Multi-session build state lost during context compaction", #115 "Background agent result deduplication after compaction", #317 "Structured session work logs with pre-compact and session-start hooks" |
| Multi-agent collision prevention (AGENTS.md collaborative rules) | Already tracked in backlog: #453 "Systematic git worktree isolation for concurrent task agents", #452 "Concurrency cap for parallel task dispatch in implement-feature" |
