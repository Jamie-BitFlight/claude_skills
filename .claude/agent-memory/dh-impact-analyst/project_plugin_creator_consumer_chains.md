---
name: plugin-creator consumer chains and high-traffic dependencies
description: Key consumer chains, cross-plugin dependencies, and high-traffic reference patterns in the claude_skills repo — critical for impact analysis of plugin-creator changes
type: project
---

Plugin-creator agents are referenced from 3+ plugins simultaneously. When assessing impact of any plugin-creator agent change, always check:

1. **the-rewrite-room plugin** — `plugins/the-rewrite-room/agents/rewrite-room-optimizer.md`, `plugins/the-rewrite-room/skills/the-rewrite-room/SKILL.md`, `plugins/the-rewrite-room/commands/rwr/optimize.md`, `plugins/the-rewrite-room/the-rewrite-room/workflows/optimize.md` — all contain direct routing to plugin-creator agents by name; this is a CROSS-PLUGIN runtime dependency

2. **development-harness task-worker** — `plugins/development-harness/agents/task-worker.md` references specialist agent names from plugin-creator; illustrative but also functional via `profile_load`; `plugins/development-harness/docs/TASK_FILE_FORMAT.md` contains inline comments naming agents

3. **populate-agent-descriptions.mjs** — `plugins/plugin-creator/skills/agent-capability-analyzer/scripts/populate-agent-descriptions.mjs` hard-codes agent registry keys as JavaScript string literals; this is a CODE CHANGE risk (not documentation drift) whenever agents are added or removed

4. **Routing note copy-paste** — the phrase "Routing within `contextual-ai-documentation-optimizer`:" appears verbatim in 15+ files across plugin-creator, the-rewrite-room, and development-harness; any agent rename creates simultaneous stale-instruction risk across all of them

5. **auto_sync_manifests.py** — pre-commit hook auto-bumps plugin.json and marketplace.json on agent CRUD; agent deletion = MAJOR semver bump; `test_auto_sync_manifests.py` may assert on component counts

**Why:** Discovered during impact analysis of #1899 (contextual-ai-documentation-optimizer split). 104 references found via `what_breaks` tool.

**How to apply:** When analyzing any plugin-creator agent change, run `mcp__git-xray__what_breaks` on the agent file, then manually check the-rewrite-room and development-harness plugins as guaranteed consumers.
