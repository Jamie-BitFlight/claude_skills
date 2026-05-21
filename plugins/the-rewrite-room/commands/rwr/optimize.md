---
description: Optimize AI-facing prompts, CLAUDE.md, SKILL.md, or agent definitions using Anthropic best practices. Pass the file path as argument.
argument-hint: <file path to optimize>
agent: rewrite-room-optimizer
allowed-tools: Read, Grep, Glob, Bash, Task, Write, Edit
---

Route this optimization task to the rewrite-room-optimizer agent.

Target: $ARGUMENTS

The agent will determine whether this needs the ai-doc-optimizer or subagent-refactorer and delegate accordingly.

Routing by concern (plugin-creator optimization suite):
- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `plugin-creator:ai-doc-optimizer`
- Audit quality (read-only, no writes, score against completeness categories) → `plugin-creator:skill-auditor`
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `plugin-creator:skill-content-updater`
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly
