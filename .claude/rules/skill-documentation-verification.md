---
paths:
- '**/SKILL.md'
- '**/references/*.md'
---

# Skill Documentation Verification

Skill documentation (SKILL.md, reference files) is AI-facing, NOT user-facing.

**Primary Audience:**

1. Orchestrator (Claude) — guides orchestration decisions, agent selection, workflow patterns
2. Sub-agents — load and follow guidance when delegated tasks
3. Future sessions — persist across conversations, inform all future AI instances

False/unverified/assumed information in skill documentation causes model self-misleading, sub-agent errors, compounding false feedback loops, and wrong results delivered to humans. Treat skill documentation with same rigor as code: verified, cited, accurate.

## Verification Protocol

Before documenting behavior/capability/characteristic of commands (`~/.claude/commands/`), agents (`~/.claude/agents/`), tools, libraries, or system configuration — execute ALL steps:

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

## Verification Examples

<example type="violation">

**Scenario**: Documenting command behavior without reading source

**Wrong**: "Validates shebang matches script type, checks PEP 723 metadata if external dependencies detected"

**Problem**: Written without reading actual command file to verify what it does

</example>

<example type="correct">

**Scenario**: Verified documentation with source citation

**Right**: "Corrects shebang to match script type, adds PEP 723 metadata if external dependencies detected, removes PEP 723 if stdlib-only, sets execute bit if needed"

Source: Lines 137, 154 of `plugins/python3-development/skills/shebangpython/SKILL.md`

</example>

<example type="correct">

**Scenario**: Explicit uncertainty when unable to verify

**Right**: "The python-portable-script agent purpose is not yet verified. Before documenting its behavior, I will read the agent file to confirm its actual capabilities."

</example>
