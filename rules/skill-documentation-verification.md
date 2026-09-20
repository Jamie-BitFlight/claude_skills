# Skill Documentation Verification

Skill documentation (SKILL.md, reference files) is AI-facing, NOT user-facing. For an external or URL source, use `citation-requirements.md`'s citation methods instead of this file's line-number format.

**Primary Audience:**

1. Orchestrator (Claude) — guides orchestration decisions, agent selection, workflow patterns
2. Sub-agents — load and follow guidance when delegated tasks
3. Future sessions — persist across conversations, inform all future AI instances

## Verification Protocol

Before documenting behavior/capability/characteristic of commands (this repo's `.claude/commands/` or a plugin's `commands/`), agents (`.claude/agents/` or a plugin's `agents/`), tools, libraries, or system configuration — execute ALL steps:

1. **Read Actual Source**
   - Commands: Read entire file, note line numbers
   - Agents: Read YAML frontmatter and complete prompt
   - Official docs: Use WebSearch, WebFetch, mcp__Ref tools
   - Library code: Read source directly

2. **Verify Behavior**
   - Execute commands/scripts to observe actual behavior
   - Cite evidence from source files with line number references
   - Test against documented claims before writing

3. **Cite Observations**
   - Format: "According to lines X-Y of [file path]..."
   - Format: "Testing command X produces output: [exact output]"
   - Format: "Per official documentation at [URL]..."

4. **State uncertainty explicitly**
   - If unknown: state "unverified" explicitly
   - If unable to verify: "Unable to verify [claim] due to [reason]"
   - Mark assumptions: "Assuming [X] based on [pattern/inference]"

**Minimum Requirements:**

- Include line numbers when referencing code files
- Execute test if behavior observable directly
- Note publication dates for documentation sources
