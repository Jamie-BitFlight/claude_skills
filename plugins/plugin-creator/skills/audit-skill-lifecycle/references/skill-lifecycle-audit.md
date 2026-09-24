# Skill Lifecycle Audit — Research Document

Deep semantic validation of how skills interconnect, what they load, what they produce, and whether the resulting call graph forms a coherent, non-contradictory workflow.

This document describes audit dimensions and detection strategies for future implementation. It is not an executable skill.

---

## What This Audit Does

Given a plugin (or a single skill within a plugin), trace every outbound reference — skills loaded, agents delegated to, commands invoked, data consumed, data produced — and evaluate whether the resulting graph is **coherent, complete, and non-redundant**.

This is NOT structural validation (that's what `NamespaceReferenceValidator` and `/plugin-creator:assessor` do). This is **semantic validation** — does the wiring make sense given what each component claims to do?

---

## Audit Dimensions

### 1. Call Chain Completeness

For each skill, answer:

- What does this skill claim to do? (from its description and body)
- What other skills/agents/commands does it invoke to accomplish that?
- For each invoked component: does that component's description and capability actually support what the caller needs from it?
- Are there steps in the skill's workflow that require capabilities not provided by any loaded component?

**Output**: A call graph per skill with annotations: `SUPPORTED` (target provides what caller needs), `PARTIAL` (target provides some but not all), `UNSUPPORTED` (target doesn't do what caller expects), `MISSING` (no target loaded for this step).

### 2. Bidirectional Lifecycle Coherence

For each skill that participates in a domain (e.g., "Python code quality"):

- Which other skills in the same domain reference it?
- Which other skills SHOULD reference it but don't?
- Is there a skill that produces output that this skill consumes, but the producer doesn't know about this consumer?

**Example**: `stinkysnake` identifies code smells and delegates remediation. Does the remediation agent (`python-code-reviewer`) know to invoke `stinkysnake` or `snakepolish` when doing code quality review? If not, the lifecycle has a gap — the reviewer can't trigger the smell detection workflow.

**Output**: Bidirectional reference matrix per domain. Flag one-directional references where bidirectional is expected.

### 3. Circular Loading Detection

Trace all portable `/plugin:skill` references to build a directed graph. Identify:

- Direct cycles: A loads B, B loads A
- Indirect cycles: A loads B, B loads C, C loads A
- Self-references that could cause infinite recursion during skill activation

**Output**: List of cycles found, with the full chain.

### 4. Duplicated Datasets

Scan all skill bodies and reference files for:

- Identical or near-identical content blocks appearing in multiple skills (e.g., the same configuration template, the same list of rules, the same decision tree)
- Content that could be extracted into a shared reference file loaded by multiple skills
- Copy-paste indicators: identical code fences, identical tables, identical instruction blocks

**Threshold**: Content blocks >10 lines that appear in 2+ skills with >80% similarity.

**Output**: List of duplicated blocks with source locations and a recommendation for extraction into a shared reference.

### 5. Instruction Contradictions

Compare instructions across skills that operate in the same domain:

- Identify pairs of instructions that give opposing guidance
- Check whether contradictions are guarded by conditions (e.g., "for Python 3.9" vs "for Python 3.11+")
- Flag unguarded contradictions as errors

**Examples of guarded contradictions (acceptable)**:
- Skill A: "Use `List[str]` type hints" (within a Python 3.9 compatibility section)
- Skill B: "Use `list[str]` type hints" (within a Python 3.11+ section)

**Examples of unguarded contradictions (errors)**:
- Skill A: "Always use `Dict[str, Any]` for type hints"
- Skill B: "Use `dict[str, Any]` for type hints"
- Neither skill specifies a Python version condition

**Output**: List of contradiction pairs with file:line references and whether they are guarded or unguarded.

### 6. Scriptable Command Sequences

Identify patterns where a skill instructs the AI to:

1. Run a shell command
2. Parse the output
3. Make a decision based on the output
4. Run another command with arguments derived from step 3

These multi-step command sequences are candidates for wrapping in a Python script that:
- Handles argument validation
- Performs environment checks (tool availability, correct versions)
- Chains the steps with proper error handling
- Produces structured output the AI can consume directly

**Output**: List of scriptable sequences with the steps involved, the skill file:line where they appear, and the estimated complexity reduction from scripting.

### 7. Self-Referential Pattern Learning

As the audit discovers issues:

1. Classify each issue by the **detection pattern** that found it (e.g., "one-directional domain reference", "unguarded Python version contradiction", "duplicated pyproject.toml template")
2. Record the pattern with a description and example
3. Re-scan all already-audited skills using the newly discovered pattern
4. Repeat until no new patterns emerge

**Output**: A `patterns.md` file listing all discovered patterns, each with: pattern name, description, detection heuristic, and all instances found.

---

## Recursive Depth Strategy

Not all issues require the same depth of analysis. The audit uses a tiered approach:

### Tier 1: Structural Scan (fast, automated)

- Build call graph from regex extraction of Skill/Task/@ references
- Detect cycles, missing targets, one-directional references
- Identify duplicated content blocks via text similarity

### Tier 2: Semantic Analysis (AI reasoning required)

- Read skill descriptions and bodies to understand intent
- Evaluate whether invoked components actually provide needed capabilities
- Detect instruction contradictions with context awareness

### Tier 3: Specialist Delegation (for specific issue types)

When Tier 2 identifies a potential problem that requires domain expertise:

- **Contradictions in Python typing advice** → delegate to an agent that reads the relevant PEPs and Python version docs
- **Circular dependency that might be intentional** → delegate to an agent that evaluates whether the cycle serves a valid recursive workflow pattern
- **Duplicated content that might be intentionally different** → delegate to an agent that does fine-grained diff analysis

Each specialist delegation returns a verdict: `CONFIRMED_ISSUE`, `FALSE_POSITIVE`, or `NEEDS_HUMAN_REVIEW`.

---

## Output Artifacts

The audit produces:

1. **`audit-report-{plugin-slug}.md`** — Full findings organized by dimension
2. **`call-graph-{plugin-slug}.md`** — Visual call graph (mermaid or ASCII)
3. **`patterns.md`** — Self-referential pattern catalog with detection heuristics
4. **`recommendations.md`** — Prioritized list of actionable fixes

Each finding includes:
- File path and line number
- The specific text that triggered the finding
- The audit dimension that detected it
- Severity: `error` (broken workflow), `warning` (incomplete workflow), `info` (optimization opportunity)
- Whether the finding was confirmed by a specialist delegation

---

## What This Audit Does NOT Do

- Does NOT fix issues (that's a separate workflow)
- Does NOT validate namespace references resolve to files (that's `NamespaceReferenceValidator` in the pre-commit hook)
- Does NOT validate frontmatter schema (that's `skilllint`)
- Does NOT replace `/plugin-creator:assessor` (which does structural assessment for refactoring planning)

This audit answers: "Given that all the files exist and all the references resolve, does the resulting system actually work as a coherent whole?"
