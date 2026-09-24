---
name: subagent-refactoring-methodology
description: Analysis criteria, transformation patterns, output format, and validation checklist for refactoring Claude Code agent prompt files. Load this skill when preparing to run the subagent-refactorer agent or when reviewing agent prompt files for structural, model optimization, or instruction quality improvements.
user-invocable: false
---

# Subagent Refactoring Methodology

## Analysis Criteria

### Structural Issues

- Are instructions explicit and unambiguous, or do they use vague qualifiers ("try to", "might", "consider")?
- Is there a clear hierarchical structure (markdown headers) with logical flow: role → responsibilities → process → output?
- Are concerns properly separated (instructions vs examples vs data)?
- Missing sections: role definition, process steps, output format, boundaries?

### Model Optimization

- **Sonnet (default)**: cost-optimized, parallel tool execution, effort calibration explicit
- **Opus (upgrade only with observed complexity evidence)**: complex coding, multi-step agents, computer use

Constitutional AI patterns: self-critique loops, validation checkpoints before output, principles-based over rules-based, evidence-based reasoning enforced.

XML usage: strategic tagging for specific sections only — NOT full document conversion.

### Instruction Quality

```text
STRONG imperatives: MUST, ALWAYS, NEVER, REQUIRED, FORBIDDEN
WEAK qualifiers to eliminate: "try to", "should", "consider", "might"

ACTIVE:  "Generate X"
PASSIVE: "X should be generated"  ← eliminate

CONCRETE: "Include exactly 3 examples with code blocks"
VAGUE:    "Include some examples"  ← eliminate
```

Check for contradictory instructions. Claude prioritizes system parameter and Constitutional AI principles when conflicting.

## Transformation Patterns

```text
VAGUE → EXPLICIT:
"Try to use examples"           → "MUST include minimum 2 examples with full code blocks"
"Should consider error handling" → "ALWAYS validate inputs; NEVER proceed with invalid data"

PASSIVE → ACTIVE:
"The file should be read"       → "READ the file using the Read tool"
"Analysis may be needed"        → "ANALYZE [specific aspect] using [specific methodology]"

AMBIGUOUS → QUANTIFIED:
"Some details"                  → "Minimum 3 specific details with examples"
"Brief description"             → "1-2 sentence description, maximum 50 words"
```

## Correct Agent Structure Pattern

```markdown
# Role and Objective

You are a [specific role]. Your mission is [clear, singular objective].

## Constraints

You MUST NOT:
- [Explicit limitation]

## Process Steps

<process>
  <step_1>Analyze requirements</step_1>
  <step_2>Design solution</step_2>
  <step_3>Generate implementation</step_3>
  <step_4>Validate output</step_4>
</process>

## Output Format

[Format specification with placeholders]

## Examples

<examples>
  <example id="1">
    <input>[Exact input]</input>
    <output>[Complete output in exact format]</output>
    <rationale>[Official source supporting this pattern]</rationale>
  </example>
</examples>
```

KEY: markdown headers for structure, XML tags strategically for specific sections (process steps, examples), NOT wrapping the entire agent.

## Tool Selection

For each tool in an agent's list, ask: "Would the agent fail without this tool?" If no, remove it.

```text
File reading/analysis:      Read, Grep, Glob
File creation:              Write, Edit
Research/documentation:     WebSearch, WebFetch, MCP Ref tools
Code operations:            Read, Write, Edit, Bash
Orchestration:              current task tracking or plain STATUS updates
```

Prefer specific tools over generic (Grep over Bash for search).

## Output Format Specification

Deliver three artifacts:

**1. Analysis report**

```markdown
# Subagent Refactoring Analysis: [Agent Name]

## Structural Issues Identified
- [Issue with specific example from original]

## Model Optimization Opportunities
- [Opportunity with citation to official source]

## Instruction Quality Issues
- [Issue: quote original instruction, explain problem]

## Research Citations
1. [Source URL] — [Key finding applied]
```

**2. Refactored agent file**

```markdown
## Changes Summary

Major Structural Changes:
1. [Change] — [Rationale with citation]

Instruction Improvements:
- [X vague phrases replaced with imperatives]
- [Y examples added]
- [Z tools removed]

<new_agent_file>
[Complete agent file]
</new_agent_file>
```

**3. Validation checklist** — confirm all items before delivery:

- [ ] Role defined in one sentence
- [ ] Output specified with verifiable form
- [ ] All instructions use MUST/NEVER/ALWAYS
- [ ] No vague qualifiers remain
- [ ] Active voice throughout
- [ ] Strategic XML applied (not full-document conversion)
- [ ] Tool set minimal — each tool has named use case
- [ ] Minimum 2 examples included
- [ ] All changes cite official Anthropic sources

## Self-Validation Before Delivery

1. Did I consult official Anthropic documentation? → Cite specific URL and finding
2. Are ALL recommendations backed by Claude-specific authoritative sources? → List source per major change
3. Did I remove, not add, unnecessary complexity? → Justify each addition
4. Can someone implement this exactly as written? → Test by reading instructions literally

**Anti-patterns to avoid:**
- Adding features not requested
- Citing blog posts instead of official documentation
- Applying techniques from outdated model versions
- Converting entire agent to XML format (contradicts Anthropic guidance)
- Adding tools "just in case"
