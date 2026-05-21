---
name: audit-skill-lifecycle
description: Audit skill lifecycle by tracing call chains, detecting circular dependencies, finding instruction contradictions, identifying duplicated datasets, analyzing bidirectional coherence, discovering scriptable sequences, and learning patterns. Use when checking skill coherence, validating skill workflow, finding semantic gaps in plugin structure, or auditing plugin before marketplace submission. Generates audit reports to .claude/audits/ with findings by dimension.
argument-hint: <plugin-path>
model: sonnet
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.


# Audit Skill Lifecycle

Deep semantic validation of how skills interconnect, what they load, what they produce, and whether the resulting call graph forms a coherent, non-contradictory workflow.

## Purpose

This audit traces every outbound reference from skills, agents, commands, and data files within a plugin to evaluate whether the resulting graph is coherent, complete, and non-redundant. It performs semantic validation beyond structural checks, answering whether the wiring makes sense given what each component claims to do.

This is NOT structural validation (that's what `NamespaceReferenceValidator` and `/plugin-creator:assessor` do). This is semantic validation of the skill lifecycle itself.

## When to Use

Invoke this skill when:

- Preparing plugin for marketplace submission (semantic quality gate)
- Debugging why skill workflows fail to achieve stated goals
- Identifying instruction contradictions across related skills
- Finding duplicated content that should be extracted to shared references
- Detecting circular skill loading that could cause infinite recursion
- Analyzing whether skills in a domain form a complete lifecycle
- Discovering manual command sequences that should be scripted

## Workflow

### Step 1: Discovery

Scan plugin structure to identify all skills, agents, commands, and reference files. Build initial inventory:

- Skill directories containing SKILL.md files
- Agent .md files in agents/ directory
- Command .md files in commands/ directory
- Reference files loaded by skills
- Data files (JSON, YAML, markdown tables) consumed by skills

Extract all `Skill(skill:)`, `Skill(skill=)`, `Agent(command:)`, and `@agent` references to build outbound dependency graph.

### Step 2: Analysis — Run Audit Dimensions

Execute 7 audit dimensions as defined in `references/skill-lifecycle-audit.md`. Each dimension analyzes a different aspect of semantic coherence:

| Dimension | Checks | Output Type |
|-----------|--------|-------------|
| Call Chain Completeness | For each skill: does it load components that actually provide the capabilities it needs? | Call graph with annotations: SUPPORTED / PARTIAL / UNSUPPORTED / MISSING |
| Bidirectional Lifecycle Coherence | For skills in same domain: are references bidirectional where expected? Do producers know about consumers? | Bidirectional reference matrix per domain with one-directional reference flags |
| Circular Loading Detection | Trace all Skill() references to find direct/indirect cycles and self-references | List of cycles with full chain (A→B→C→A) |
| Duplicated Datasets | Scan for identical/near-identical content blocks appearing in multiple skills (>10 lines, >80% similarity) | List of duplicated blocks with source locations and extraction recommendations |
| Instruction Contradictions | Compare instructions across skills in same domain, detect opposing guidance, distinguish guarded vs unguarded contradictions | Contradiction pairs with file:line references and guard status |
| Scriptable Command Sequences | Identify multi-step shell command patterns that parse output and make decisions | List of scriptable sequences with complexity reduction estimates |
| Self-Referential Pattern Learning | Classify discovered issues by detection pattern, re-scan using new patterns until no new patterns emerge | patterns.md catalog with pattern definitions and all instances |

### Step 3: Report Generation

Write audit artifacts to `.claude/audits/` directory:

- `audit-report-{slug}.md` — Full findings organized by dimension with severity (error/warning/info)
- `call-graph-{slug}.md` — Visual call graph (mermaid format) with annotations
- `patterns.md` — Self-referential pattern catalog updated with newly discovered patterns from this audit
- `recommendations.md` — Prioritized actionable fixes

Each finding includes:
- File path and line number
- The specific text that triggered the finding
- The audit dimension that detected it
- Severity: error (broken workflow), warning (incomplete workflow), info (optimization opportunity)
- Whether the finding was confirmed by a specialist delegation

## Audit Dimensions

### 1. Call Chain Completeness

For each skill, verify:

- What does this skill claim to do? (from description and body)
- What other skills/agents/commands does it invoke?
- For each invoked component: does that component's description and capability actually support what the caller needs from it?
- Are there steps in the workflow that require capabilities not provided by any loaded component?

Returns call graph per skill with capability match annotations.

### 2. Bidirectional Lifecycle Coherence

For each skill in a domain (e.g., "Python code quality"):

- Which other skills in same domain reference it?
- Which other skills SHOULD reference it but don't?
- Is there a producer-consumer relationship where the producer doesn't know about the consumer?

Example: If `stinkysnake` identifies code smells and delegates remediation, does the remediation agent know to invoke `stinkysnake` when doing code quality review? If not, lifecycle has a gap.

Returns bidirectional reference matrix per domain with one-directional reference flags.

### 3. Circular Loading Detection

Trace all `Skill(skill:)` and `Skill(skill=)` references to build directed graph. Identify:

- Direct cycles: A loads B, B loads A
- Indirect cycles: A loads B, B loads C, C loads A
- Self-references that could cause infinite recursion during activation

Returns list of cycles with full chain notation.

### 4. Duplicated Datasets

Scan all skill bodies and reference files for:

- Identical or near-identical content blocks appearing in multiple skills
- Content that could be extracted into shared reference file loaded by multiple skills
- Copy-paste indicators: identical code fences, identical tables, identical instruction blocks

Threshold: Content blocks greater than 10 lines appearing in 2 or more skills with greater than 80% similarity.

Returns list of duplicated blocks with source locations and recommendation for extraction.

### 5. Instruction Contradictions

Compare instructions across skills operating in same domain:

- Identify pairs of instructions giving opposing guidance
- Check whether contradictions are guarded by conditions (e.g., "for Python 3.9" vs "for Python 3.11+")
- Flag unguarded contradictions as errors

Guarded contradictions (acceptable):
- Skill A: "Use `List[str]` type hints" (within Python 3.9 compatibility section)
- Skill B: "Use `list[str]` type hints" (within Python 3.11+ section)

Unguarded contradictions (errors):
- Skill A: "Always use `Dict[str, Any]` for type hints"
- Skill B: "Use `dict[str, Any]` for type hints"
- Neither specifies Python version condition

Returns contradiction pairs with file:line references and guard status.

### 6. Scriptable Command Sequences

Identify patterns where skill instructs AI to:

1. Run shell command
2. Parse the output
3. Make decision based on output
4. Run another command with arguments derived from step 3

These multi-step command sequences are candidates for wrapping in Python script that handles argument validation, environment checks (tool availability, correct versions), proper error handling, and structured output.

Returns list of scriptable sequences with steps involved, file:line location, and estimated complexity reduction.

### 7. Self-Referential Pattern Learning

As audit discovers issues:

1. Classify each issue by detection pattern that found it (e.g., "one-directional domain reference", "unguarded Python version contradiction")
2. Record pattern with description and example
3. Re-scan all already-audited skills using newly discovered pattern
4. Repeat until no new patterns emerge

Returns `patterns.md` file listing all discovered patterns with: pattern name, description, detection heuristic, and all instances found.

## Tier Strategy

Not all issues require same depth of analysis. The audit uses 3-tier approach:

### Tier 1: Structural Scan (fast, automated)

- Build call graph from regex extraction of Skill/Task/@ references
- Detect cycles, missing targets, one-directional references
- Identify duplicated content blocks via text similarity

### Tier 2: Semantic Analysis (AI reasoning required)

- Read skill descriptions and bodies to understand intent
- Evaluate whether invoked components actually provide needed capabilities
- Detect instruction contradictions with context awareness

### Tier 3: Specialist Delegation (for specific issue types)

When Tier 2 identifies potential problem requiring domain expertise:

- Contradictions in Python typing advice → delegate to agent that reads relevant PEPs and Python version docs
- Circular dependency that might be intentional → delegate to agent that evaluates whether cycle serves valid recursive workflow pattern
- Duplicated content that might be intentionally different → delegate to agent that does fine-grained diff analysis

Each specialist delegation returns verdict: `CONFIRMED_ISSUE`, `FALSE_POSITIVE`, or `NEEDS_HUMAN_REVIEW`.

## Output Format

The audit produces artifacts in `.claude/audits/`:

### audit-report-{slug}.md

```markdown
# Skill Lifecycle Audit Report
Plugin: {plugin-name}
Date: {timestamp}
Auditor: audit-skill-lifecycle

## Summary
- Total skills audited: {N}
- Total findings: {N} ({errors} errors, {warnings} warnings, {info} info)
- Cycles detected: {N}
- Contradictions found: {N} unguarded, {N} guarded
- Duplicated blocks: {N}
- Scriptable sequences: {N}
- Patterns discovered: {N}

## Findings by Dimension

### 1. Call Chain Completeness
[Findings with file:line, severity, description]

### 2. Bidirectional Lifecycle Coherence
[Findings with file:line, severity, description]

[... remaining dimensions ...]

## Patterns Discovered
[Reference to patterns.md with newly discovered patterns]

## Recommendations
[Prioritized list - see recommendations.md for details]
```

### call-graph-{slug}.md

Visual call graph using mermaid syntax showing skills, agents, commands, and their dependencies with annotations for capability match status.

### patterns.md

Self-referential pattern catalog updated with patterns discovered during this audit run. Includes pattern name, description, detection heuristic, and all instances across all audited plugins.

### recommendations.md

Prioritized actionable fixes:

1. CRITICAL (errors): Broken workflows, unguarded contradictions, circular dependencies causing failures
2. HIGH (warnings): Incomplete workflows, one-directional references in domains requiring bidirection
3. MEDIUM (info): Duplicated content extraction opportunities, scriptable sequence candidates
4. LOW: Optimization opportunities

## Additional Resources

- `references/skill-lifecycle-audit.md` — detailed audit dimension definitions, detection strategies, tier implementation guidance, and examples of each finding type

## What This Audit Does NOT Do

- Does NOT fix issues (that's separate workflow)
- Does NOT validate namespace references resolve to files (that's `NamespaceReferenceValidator` in pre-commit hook)
- Does NOT validate frontmatter schema (that's `skilllint`)
- Does NOT replace `/plugin-creator:assessor` (which does structural assessment for refactoring planning)

This audit answers: "Given that all files exist and all references resolve, does the resulting system actually work as a coherent whole?"
