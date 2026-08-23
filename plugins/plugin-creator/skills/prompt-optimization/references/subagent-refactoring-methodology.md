# Subagent Refactoring Methodology

Reference for the `subagent-refactorer` agent. Covers analysis criteria, transformation patterns, output format, and validation used when refactoring Claude Code agent prompt files.

SOURCE: Extracted from `subagent-refactorer` agent body during optimization (2026-03-10). Original content authored as part of plugin-creator plugin.

---

## Official Documentation Sources

Fetch these before every refactor. Do not proceed from training-data recall of prompt engineering patterns.

```text
mcp__Ref__ref_search_documentation: "Anthropic Claude prompt engineering XML tags Constitutional AI"
mcp__Ref__ref_read_url: https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags
mcp__Ref__ref_read_url: https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices
```

Focus areas: strategic XML tagging, Constitutional AI, chain-of-thought, prefilling, context engineering, interleaved thinking, parallel tool execution.

**Research validation checklist before refactoring:**

- [ ] Accessed Anthropic official Claude documentation
- [ ] Identified Claude-specific optimization techniques
- [ ] Understood Sonnet vs Opus model economics and use cases
- [ ] Reviewed Constitutional AI self-critique patterns
- [ ] Documented all Anthropic source URLs and access dates

---

## Analysis Criteria

### Structural Issues

**Clarity**

- Are instructions explicit and unambiguous?
- Are there vague qualifiers ("try to", "might", "consider")?
- Is passive voice used instead of imperative commands?

**Organization**

- Is there a clear hierarchical structure (markdown headers)?
- Are concerns properly separated (instructions vs examples vs data)?
- Is there a logical flow: role → responsibilities → process → output?

**Completeness**

- Missing sections: role definition, process steps, output format, boundaries?
- Are examples provided with clear input/output pairs?
- Are edge cases and error conditions addressed?

### Model Optimization Criteria

**Sonnet (default)**

- Cost-optimized for default usage
- Parallel tool execution leveraged
- Effort calibration explicit ("go beyond basics")

**Opus (upgrade only with evidence)**

- Justified by observed complexity (complex coding, multi-step agents, computer use)
- Superior for production code generation and complex agent workflows

**Constitutional AI patterns**

- Self-critique loops implemented?
- Validation checkpoints before output?
- Principles-based rather than rules-based?
- Evidence-based reasoning enforced?

**XML usage**

- Strategic tagging for specific sections (not full document conversion)
- Clear section separation with intuitive tag names
- Nested hierarchically for complex structures
- Mixed with normal text appropriately

### Instruction Quality Criteria

**Command strength — strong vs weak:**

```text
STRONG: MUST, ALWAYS, NEVER, REQUIRED, FORBIDDEN
WEAK:   "try to", "should", "consider", "might"

ACTIVE:  "Generate X"
PASSIVE: "X should be generated"
```

**Specificity — concrete vs vague:**

```text
CONCRETE: "Include exactly 3 examples with code blocks"
VAGUE:    "Include some examples"

QUANTIFIED: "Process timeout: 60 seconds"
UNDEFINED:  "Process for a reasonable time"
```

**Conflict detection**

- Check for contradictory instructions
- Identify implicit vs explicit rule conflicts
- Claude prioritizes system parameter and Constitutional AI principles when conflicting

---

## Transformation Patterns

### Instruction Strengthening

```text
VAGUE → EXPLICIT:
"Try to use examples"           → "MUST include minimum 2 examples with full code blocks"
"Should consider error handling" → "ALWAYS validate inputs; NEVER proceed with invalid data"
"Might need to check"           → "REQUIRED: Verify [specific condition] before [specific action]"

PASSIVE → ACTIVE IMPERATIVE:
"The file should be read"       → "READ the file using the Read tool"
"Code can be generated"         → "GENERATE code following [specific pattern]"
"Analysis may be needed"        → "ANALYZE [specific aspect] using [specific methodology]"

AMBIGUOUS → QUANTIFIED:
"Some details"                  → "Minimum 3 specific details with examples"
"Brief description"             → "1-2 sentence description, maximum 50 words"
"Comprehensive coverage"        → "Address all 5 categories: [list categories]"
```

### Correct Agent Structure Pattern

```markdown
# Role and Objective

You are a [specific role title] with [expertise markers]. Your mission is [clear, singular objective].

## Core Responsibilities

1. **[Responsibility Category]**: [Specific actions and deliverables]
2. **[Responsibility Category]**: [Measurable outcomes]

## Boundaries

You MUST NOT:
- [Explicit limitation 1]
- [Explicit limitation 2]

## Process Steps

<process>
  <step_1>Analyze requirements — extract specifications from user request</step_1>
  <step_2>Design solution — plan implementation before acting</step_2>
  <step_3>Generate implementation</step_3>
  <step_4>Validate — verify output meets acceptance criteria</step_4>
</process>

## Output Format

[Format specification with placeholders and required elements]

## Examples

<examples>
  <example id="1">
    <scenario>[Context: what situation triggers this agent]</scenario>
    <input>[EXACT input the agent receives]</input>
    <output>[COMPLETE output in exact format specified]</output>
    <rationale>[Reference to official source supporting this pattern]</rationale>
  </example>
</examples>

## Quality Standards

MUST meet all criteria:
- [Specific metric or criterion 1]
- [Validation method]
```

**KEY PRINCIPLES for structure:**

- Use markdown headers for structure
- Apply XML tags strategically for specific sections (process steps, examples, data)
- Do NOT wrap the entire agent in XML tags
- Mix normal text with XML-tagged sections as needed

### Tool Selection

```text
ANALYZE AGENT'S CORE FUNCTION:
→ File reading/analysis: Read, Grep, Glob
→ File creation: Write, Edit
→ Research/documentation: WebSearch, WebFetch, MCP Ref tools
→ Code operations: Read, Write, Edit, Bash
→ Orchestration: Task, TodoWrite
→ Testing: Bash, Read, Write

APPLY MINIMALISM:
→ Include ONLY tools actually needed for core function
→ Remove tools "just in case" — agents should request tools if needed
→ Prefer specific tools over generic (Grep over Bash for search)

VALIDATE NECESSITY:
→ For each tool: "Would the agent fail without this tool?" If no, remove it.
```

MCP tool name requirements — list each MCP tool in the `tools` field by its exact registered name, case-sensitive: `mcp__Ref__ref_search_documentation` resolves; `mcp__ref__ref_search_documentation` matches nothing and is dropped. Grant a whole server with `mcp__<server>__*` or `mcp__<server>`; both forms grant every tool that server exposes and compose with named tools. A plugin-bundled server registers as `mcp__plugin_<plugin-name>_<server-name>`. Verify exact names against the running MCP server registration before including them.

An entry matching no live tool is dropped and the rest of the grant still resolves; an agent whose every entry resolves to nothing refuses to launch. A server pattern grants nothing while that server is disconnected, so an agent granted only MCP tools cannot be invoked until the server returns — leave it at least one non-MCP tool unless that runtime dependency is intended.

---

## Output Format Specification

Deliver three artifacts:

### 1. Analysis Report

```markdown
# Subagent Refactoring Analysis: [Agent Name]

## Original Agent Assessment

### Structural Issues Identified
- [Issue 1 with specific examples from original]

### Model Optimization Opportunities
- [Opportunity 1 with citation to official source]

### Instruction Quality Issues
- [Issue 1: Quote original instruction, explain problem]

## Research Citations

### Anthropic Official Sources
1. [Source title and URL] — [Key finding applied]

### Cross-Validation
- [Finding validated across N sources]
```

### 2. Refactored Agent File

```markdown
## Refactored Agent: [agent-name].md

### Changes Summary

**Major Structural Changes:**
1. [Change description] — [Rationale with citation]

**Instruction Improvements:**
- [X instances of vague language replaced with explicit commands]
- [Y new examples added]
- [Z tool selections optimized]

**Model Optimizations:**
- [Sonnet: Strategic XML tagging, parallel tool execution]
- [Opus: Justified only if complexity evidence observed]

### Complete Refactored File

<new_agent_file>
[Complete agent file with all improvements]
</new_agent_file>
```

### 3. Validation Checklist

After delivering the refactored file, confirm all items:

**Structure**

- [ ] Clear role and objective defined
- [ ] Responsibilities explicitly listed with action verbs
- [ ] Step-by-step process included
- [ ] Output format specified with examples
- [ ] Boundaries and constraints defined

**Instruction Quality**

- [ ] All instructions use strong imperatives (MUST/NEVER/ALWAYS)
- [ ] No vague qualifiers (try to, should, might)
- [ ] Active voice throughout
- [ ] Quantified metrics where applicable
- [ ] No conflicting instructions detected

**Model Optimization**

- [ ] Strategic XML tagging applied (not full XML conversion)
- [ ] Model-specific features leveraged appropriately
- [ ] Examples follow official patterns
- [ ] Chain-of-thought prompt included for complex reasoning

**Completeness**

- [ ] Minimum 2 comprehensive examples included
- [ ] All edge cases addressed
- [ ] Tool selection justified and minimal
- [ ] Citations to official sources provided

---

## Self-Validation Before Delivery

Before delivering a refactored agent, verify:

1. Did I consult official Anthropic documentation? → Cite specific URL and finding
2. Did I apply Constitutional AI self-critique patterns? → Cite specific implementation
3. Are ALL recommendations backed by Claude-specific authoritative sources? → List source for each major change
4. Would this agent work better on the target model? → Explain expected improvement with reasoning
5. Are instructions unambiguous and testable? → Provide verification method
6. Did I remove, not add, unnecessary complexity? → Justify each addition
7. Can someone implement this exactly as written? → Test by reading instructions literally

**Anti-patterns to avoid:**

- Adding features not requested or needed
- Over-engineering with excessive structure
- Citing blog posts instead of official documentation
- Applying techniques from outdated model versions
- Making subjective changes without authoritative backing
- Increasing token count unnecessarily
- Adding tools "just in case"
- Converting entire agent to XML format (contradicts Anthropic guidance)

---

## Example Transformation

### Before (Hypothetical — weak agent)

```markdown
name: code-helper
description: Helps with code
tools: *

You are a coding assistant. Help users write code. Try to follow best practices
and write good code. Provide examples when possible.
```

### After (Refactored — following Anthropic guidance)

```markdown
name: code-helper
description: Use when implementing new functions, classes, or modules with comprehensive
  documentation and tests. Expert code generation specialist following language-specific
  best practices.
tools: Read, Write, Edit, Grep, Bash
model: sonnet

# Expert Code Generation Specialist

You are a senior software engineer. Your mission is to generate production-ready,
well-tested code following industry best practices.

## Core Responsibilities

1. **Code Generation**: Create syntactically correct, idiomatic code in the requested language
2. **Documentation**: Include comprehensive docstrings, type annotations, and inline comments
3. **Testing**: Generate unit tests covering happy path, edge cases, and error conditions

## Process Steps

<process>
  <step_1>Analyze Requirements — extract exact specifications from user request</step_1>
  <step_2>Design Solution — plan implementation (data structures, patterns, error handling)</step_2>
  <step_3>Generate Implementation — write production-quality code with type annotations</step_3>
  <step_4>Create Tests — generate test suite with minimum 5 test cases</step_4>
  <step_5>Validate — confirm code runs, tests pass, documentation is complete</step_5>
</process>

## Constraints

- MUST include type annotations
- MUST include comprehensive docstrings
- MUST handle errors gracefully
- NEVER use placeholder comments like "# TODO"

## Quality Standards

MUST meet all criteria:
- Code executes without syntax errors
- Tests achieve >80% coverage
- No security vulnerabilities
```

**Key changes made:**

- Added specific role (senior software engineer)
- Converted "try to follow" into explicit MUST/NEVER commands
- Added structured 5-step process with strategic XML tagging
- Defined exact output format
- Reduced tools from `*` to minimal necessary set
- Cited official sources for patterns applied
- Used markdown structure with strategic XML tags, NOT full XML conversion
