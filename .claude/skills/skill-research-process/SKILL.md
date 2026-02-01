---
description: Systematic process for building comprehensive Claude Code skills using parallel research agents. Triggers on "research for skill", "build skill from docs", "create comprehensive skill", or when needing to gather extensive documentation from official sources before skill creation.
argument-hint: <tool-or-library-name>
model: sonnet
context: fork
agent: general-purpose
user-invocable: true
---

# Skill Research Process

Systematic, scalable approach for building comprehensive Claude Code skills using parallel research agents. Use this when a skill requires extensive documentation gathering from official sources.

## Process Overview

```text
Stage 1: Initialize → Categorization agent creates TODO checklist
    ↓
Gate 1: Verify categories are distinct and complete
    ↓
Stage 2: Research → Parallel agents populate references/{category}/
    ↓
Gate 2: Anti-hallucination checkpoint (verify all claims cited)
    ↓
Stage 3: Integrate → Update SKILL.md, validate structure
    ↓
Gate 3: Final validation (links work, quality standards met)
```

## Pre-Requisites

1. Activate skill-creator for structure guidance:

   ```text
   Skill(command: "plugin-creator:skill-creator")
   ```

2. Read CLAUDE.md for verification requirements

## Stage 1: Initialize Skill Structure

**Objective**: Create base skill directory and identify documentation categories.

### Steps

1. **Initialize skill directory**:

   ```bash
   plugins/plugin-creator/skills/skill-creator/scripts/init_skill.py <skill-name> --path <output-directory>
   ```

2. **Launch categorization agent** - see [Agent Prompts](./references/agent-prompts.md#categorization-agent)

3. **Output**: `{skill-name}.TODO.md` with categorized checklist

### Quality Gate 1: Category Verification

Before proceeding, verify:

- [ ] Categories are distinct (no overlap)
- [ ] Each category is specific enough to guide focused research
- [ ] 5-10 categories total (fewer for simple tools, more for complex)
- [ ] Categories cover the tool's full scope

**If categories overlap**: Merge or redefine boundaries before Stage 2.

## Stage 2: Parallel Category Research

**Objective**: Launch concurrent research agents to build reference documentation.

### Steps

1. Read TODO categories from `{skill-name}.TODO.md`
2. Launch concurrent Task agents (one per category) with `run_in_background: true`
3. Each agent outputs to `./references/{category}/`

See [Research Agent Prompt](./references/agent-prompts.md#research-agent) for template.

### Parallel Execution

Launch all agents in a **single message** with multiple Task calls:

```text
Task(subagent_type: "general-purpose", description: "Research Category A", run_in_background: true, ...)
Task(subagent_type: "general-purpose", description: "Research Category B", run_in_background: true, ...)
```

### Quality Gate 2: Anti-Hallucination Checkpoint

**MANDATORY before Stage 3.** For each category, verify:

- [ ] Every factual claim has a cited source (URL + access date)
- [ ] No claims based on training data knowledge
- [ ] Sources are authoritative (official docs > blogs > forums)
- [ ] Code examples are from official sources or tested
- [ ] Uncertain information marked explicitly as "unverified"

**Citation Format Required**:

```markdown
According to the official documentation (https://example.com/docs, accessed 2026-02-01), ...
```

**If citation missing**: Research agent must add source or mark as "NOT_VERIFIED: [claim]".

## Stage 3: Integration

**Objective**: Update SKILL.md with category links and finalize.

### Steps

1. Update `./SKILL.md` with links to each category's `index.md`
2. Verify SKILL.md body ≤5k words
3. Validate structure

### Quality Gate 3: Final Validation

Run validation:

```bash
plugins/plugin-creator/skills/skill-creator/scripts/package_skill.py <skill-path>
```

Verify:

- [ ] All markdown links resolve (use Read tool to verify)
- [ ] All index.md files contain working links
- [ ] All TODO items from Stage 1 have corresponding reference files
- [ ] Skill follows skill-creator guidelines

## Error Recovery

### MCP Tools Unavailable

Fallback strategy when MCP tools not available:

1. **WebFetch + WebSearch**: For discovery and overview
2. **GitHub CLI (`gh`)**: For repository metadata, issues, releases
3. **Clone + Read**: Clone repo locally, use Read tool for code analysis

### Research Agent Fails

If an agent fails or times out:

1. Check output file with Read tool (background agents write to file)
2. Resume with remaining work if partial results exist
3. Re-launch with narrower scope if timeout

### Incomplete Source Documentation

If official docs are incomplete:

1. Document what IS available with citations
2. Mark gaps explicitly: "Official documentation does not cover [topic]"
3. Use GitHub issues/discussions as secondary sources (with citation)
4. Never fill gaps with training data assumptions

## MCP Tool Selection

| Tool         | Fidelity | Use When                                       |
| ------------ | -------- | ---------------------------------------------- |
| WebFetch     | Low      | Scoping only. NEVER for implementation details |
| mcp**exa**\* | Medium   | Code snippets, documentation extraction        |
| mcp**Ref**\* | High     | Authoritative, verbatim documentation          |

See [MCP Tool Usage Guide](./references/mcp-tools.md) for details.

## Key Principles

| Principle              | Rule                                         |
| ---------------------- | -------------------------------------------- |
| Progressive Disclosure | SKILL.md ≤5k words; details in `references/` |
| Parallel Execution     | Launch all category agents in single message |
| Citation Required      | Every claim needs source + access date       |
| No Training Data       | Only document what sources confirm           |
| Relative Paths         | All links use `./` prefix                    |

## Success Checklist

Before finalizing:

- [ ] All quality gates passed (1, 2, 3)
- [ ] Every factual claim has citation with access date
- [ ] No speculation or training-data-based claims
- [ ] All links use `./` relative paths
- [ ] Categories are distinct (no overlap)
- [ ] SKILL.md ≤5k words
- [ ] Each category has `index.md` with working links
- [ ] Validation script passes

## References

- [Agent Prompt Templates](./references/agent-prompts.md)
- [MCP Tool Usage Guide](./references/mcp-tools.md)
- [Gaps Analysis](./references/gaps-analysis.md) - Known limitations and improvement opportunities
