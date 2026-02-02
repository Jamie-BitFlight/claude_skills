# Claude Skills Repository - AI-Facing Project Instructions

This repository contains a Claude Code Marketplace Plugin providing Skills for Claude - modular packages that extend Claude's capabilities with specialized knowledge, workflows, and tools.

**Contributing**: When adding, removing, or updating plugins in this repository, follow the procedures documented in [CONTRIBUTING.md](./CONTRIBUTING.md). The model MUST update `.claude-plugin/marketplace.json` when plugins are added or removed.

---

## Skill Creator Activation Protocol

<skill_activation_triggers>

The model MUST activate the skill-creator skill from the <available_skills> list when ANY of these conditions are met:

**Positive Triggers** (MUST activate):

- User explicitly requests creating, modifying, or reviewing a skill
- Model is about to modify files matching patterns: `*/SKILL.md`, `*/references/*.md` within a skill directory
- User asks questions about skill structure, frontmatter format, or validation requirements
- Model needs to convert documentation into AI-optimized instruction format
- User requests optimization of existing skill documentation for LLM consumption

**Activation Syntax**:

```claude
Skill(command: "plugin-creator:skill-creator")
```

**Negative Conditions** (MUST NOT activate):

- Simply using an existing skill (read-only activation)
- Referencing a skill in conversation without modification intent
- General coding tasks unrelated to skill creation
- Reading skill documentation for context without editing

**Verification**: Before activating skill-creator, the model MUST verify:

1. The task involves skill creation/modification (not just usage)
2. No other specialized skill better matches the task domain
3. The model has read any existing skill files being modified

</skill_activation_triggers>

---

## Task Delegation Rule

**When invoking the Task tool, follow the Delegation Template in the agent-orchestration skill.**

### Path Conventions for Sub-Agent Delegation

<delegation_path_rules>

The model MUST use paths relative to the current working directory when delegating tasks to sub-agents.

**Correct Pattern:**

```text
CONTEXT:
- Location: ./gitlab-skill/scripts/
- File to modify: ./gitlab-skill/scripts/sync-gitlab-docs.py
```

**Incorrect Patterns:**

```text
# Absolute paths - unnecessary, verbose
- Location: /home/user/repos/project/gitlab-skill/scripts/

# Symlink paths - triggers security prompts, outside repo
- Location: ~/.claude/skills/gitlab-skill/scripts/
```

**Why This Matters:**

1. **Security**: Paths outside the current repository trigger manual approval prompts for every file operation
2. **Simplicity**: Relative paths are shorter and clearer
3. **Portability**: Relative paths work regardless of where the repo is cloned
4. **Symlinks**: Skills are symlinked from `~/.claude/skills/` to this repo - always use the repo path, not the symlink

**Rule**: If the file exists within the current working directory tree, use `./relative/path`. The sub-agent inherits the same working directory.

</delegation_path_rules>

### Sub-Agent Selection Rules

<sub_agent_selection>

**CRITICAL: Never use the Explore agent for codebase exploration or contextual questions.**

The Explore agent uses Haiku, which has a ~50% hallucination rate on ambiguous queries. Experimental testing (2026-02-02) demonstrated:

| Agent | Accuracy on Contextual Questions |
| ----- | -------------------------------- |
| Explore | 2/4 correct (grabbed wrong scope, gave up early) |
| context-gathering | 4/4 correct (disambiguated correctly, searched thoroughly) |

**Observed Failure Modes with Explore:**

1. **Semantic ambiguity** - "hooks" matched pre-commit hooks instead of Claude Code hooks
2. **Premature termination** - declared "not found" instead of searching deeper
3. **Fabricated implementations** - suggested bash scripts when repo convention is Python/JavaScript

**Agent Selection Matrix:**

| Task Type | Correct Agent | Wrong Agent |
| --------- | ------------- | ----------- |
| Codebase exploration | context-gathering | Explore |
| Contextual questions | context-gathering | Explore |
| Finding specific files by pattern | Explore (acceptable) | - |
| Exact keyword search | Explore (acceptable) | - |
| Interpretation/analysis | context-gathering, claude-context-optimizer | Explore |
| Recommendations grounded in repo conventions | context-gathering | Explore |

**The model MUST use context-gathering instead of Explore when:**

- The task requires understanding repo conventions
- The query has semantic ambiguity
- The answer requires interpretation, not just retrieval
- Recommendations must be grounded in existing patterns

**SOURCE**: Experimental validation in conversation (2026-02-02). Tested 4 questions with both agents. Context-gathering correctly disambiguated and found evidence in all cases; Explore failed on 2/4 due to semantic confusion and incomplete search.

</sub_agent_selection>

### Language Conventions for Skill Components

<skill_component_languages>

**Established through experimental validation (2026-02-02):**

| Component Type | Required Language | Evidence |
| -------------- | ----------------- | -------- |
| Claude Code hooks | JavaScript (Node.js) | 9 existing hooks in `.claude/hooks/` and `sessions/hooks/` |
| Companion scripts | Python 3.11+ with PEP 723 | 27+ scripts in `plugins/**/scripts/` |
| Pre-commit hooks | Python 3.11+ | `auto-sync-manifests.py`, `validate_frontmatter.py` |

**JavaScript Hook Pattern** (from `.claude/hooks/session-start-backlog.js`):

```javascript
#!/usr/bin/env node
const fs = require('node:fs');
// ... implementation
console.log(JSON.stringify({ hookSpecificOutput: { ... } }));
```

**Python Script Pattern** (from `plugins/plugin-creator/scripts/create_plugin.py`):

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0"]
# ///
```

**The model MUST NOT suggest bash scripts** for hooks or companion scripts in this repository. Bash is only acceptable for:

- Simple CI/CD wrappers
- POSIX compatibility layers
- Existing legacy scripts (do not create new ones)

</skill_component_languages>

---

## Path Fidelity Rule

When user provides file or directory paths, use them exactly as given:

- Do NOT add filenames to directory paths
- Do NOT narrow scope by appending specific files
- A skill/plugin is a DIRECTORY containing SKILL.md, references/, assets/ - examine the ecosystem, not one file

---

## Pre-Deletion Verification

Before deleting any file:

1. Verify the replacement contains equivalent content
2. If agent comparison says "NEEDS MERGE" but user says proceed, ASK for clarification
3. Never delete based on flawed/incomplete comparison

---

## Post-Mistake Behavior

After irreversible mistakes:

- State concretely what was lost and what can/cannot be recovered
- Do NOT speculate optimistically ("probably small loss")
- Ask user what they want to do next

---

## Plugin Testing During Development

To test plugins during local development, use one of these methods:

**Option 1: Session-based loading**

```bash
claude --plugin-dir ./plugins/plugin-name
```

**Option 2: Local marketplace with enable/disable**

```bash
# Add local marketplace (one-time)
/plugin marketplace add ./.claude-plugin/marketplace.json

# Install plugin (--scope local keeps it gitignored)
/plugin install plugin-name@jamie-bitflight-skills --scope local

# Disable/enable as needed
/plugin disable plugin-name@jamie-bitflight-skills
/plugin enable plugin-name@jamie-bitflight-skills
```

---

## Marketplace Maintenance

**The model MUST follow these rules when modifying the plugin structure:**

### Adding a New Plugin

1. Create plugin directory structure under `plugins/`
2. Validate plugin: `claude plugin validate plugins/plugin-name/`
3. **MANDATORY**: Add entry to `.claude-plugin/marketplace.json` in the `plugins` array
4. **MANDATORY**: Bump `metadata.version` (minor version for new plugins)
5. Validate marketplace JSON: `python3 -m json.tool .claude-plugin/marketplace.json`

### Removing a Plugin

1. Remove plugin directory: `plugins/plugin-name/`
2. **MANDATORY**: Remove entry from `.claude-plugin/marketplace.json`
3. **MANDATORY**: Bump `metadata.version` (major if breaking, minor if experimental)
4. Validate marketplace JSON

### Version Bumping Rules

- **Major** (X.0.0): Breaking changes, removed widely-used plugins
- **Minor** (1.X.0): New plugins added, significant additions
- **Patch** (1.0.X): Bug fixes, documentation only

**Complete procedures**: See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed step-by-step instructions.

---

## Content Optimization for Skills

<content_optimization_purpose> When tasked with rewriting text for LLM consumption: Transform input into concise, technical instructions, reference material, and rules suitable for AI consumption. The audience is an AI model with expert-level comprehension of all technical concepts. Assume complete familiarity with domain internals. </content_optimization_purpose>

### Core Principles

The model MUST follow these principles when transforming text into RULES, CONDITIONS, and CONSTRAINTS:

- Write focused, imperative, actionable, scoped rules
- Keep rules concise (target: under 500 lines per file)
- Split significant concepts into multiple composable rules or contextually tagged data sets
- Preemptively provide URLs to further reading and links to referenced files
- Avoid vague guidance - write rules as clear internal documentation
- Use declarative phrasing ("The model MUST") for all instructions
- Produce deterministic, flat ASCII text - avoid stylistic markdown (bold, italic) - use only structural markdown (headings, lists, links, code fences with language specifiers)
- Include explicit sections for: identity, intent, task rules, issue handling, triggers, external references
- Preserve or expand structured examples found in source text

### Strategic XML Tag Usage

<xml_usage_guidelines>

**When to Use XML Tags** (Source: Anthropic docs.claude.com/prompt-engineering/use-xml-tags):

XML tags improve clarity, accuracy, flexibility, and parseability when prompts involve multiple components such as context, instructions, and examples.

**Application**:

- Use tags like `<instructions>`, `<example>`, `<formatting>` to separate prompt parts
- Prevents Claude from mixing up instructions with examples or context
- Be consistent with tag names throughout prompts
- Nest tags `<outer><inner></inner></outer>` for hierarchical content
- Combine with multishot prompting (`<examples>`) or chain of thought (`<thinking>`, `<answer>`)

**Key Insight**: There are no canonical "best" XML tags - use semantic names that make sense with the information they surround.

</xml_usage_guidelines>

### Text Transformation Rules

<transformation_rules>

When rewriting text for AI consumption, the model MUST:

1. Open with a directive on how to read and apply the rules
2. Maximize information density using technical jargon, dense terminology, equations, industry-specific terms
3. Rephrase for accuracy and specificity
4. Address an expert, scientific, or academic audience
5. Use only visible ASCII characters
6. Write as lookup references for AI consumption - optimize as decision triggers and pattern-matching rules for an AI that already knows technical details, NOT educational content
7. Omit greetings and unnecessary prose
8. Preserve original text's output structure specifications if observed
9. Use precise, deterministic ACTION→TRIGGER→OUTCOME format in frontmatter descriptions
10. Set clear priority levels between rules to resolve conflicts efficiently
11. Provide concise positive and negative examples of rule application
12. Optimize for AI context window efficiency - remove non-essential information
13. Use standard glob patterns without quotes (e.g., _.js, src/\*\*/_.{ts,js})
14. Keep frontmatter descriptions rich with TRIGGERS for when rules should be used
15. Limit examples to essential patterns only

</transformation_rules>

---

## File Reference Patterns in Skills

### Code Fence Language Specifiers

The model MUST add a language specifier to ALL opening code fences:

Markdown file containing nested code blocks

````markdown
# Section Title

```text
Plain text content or structured ASCII
```

```python
def example():
    return True
```
````

<rationale>4 backticks on outer fence, language specifiers on all inner fences, proper nesting</rationale>

### Markdown Links with Relative Paths

<correct_pattern>

When creating references between files within a skill, the model MUST use markdown links with relative paths starting with `./`:

**Syntax**: `[descriptive text](./path/to/file.md)`

**Examples from Anthropic's mcp-builder skill**:

```markdown
[📋 View Best Practices](./reference/mcp_best_practices.md) [🐍 Python Implementation Guide](./reference/python_mcp_server.md) [✅ Evaluation Guide](./reference/evaluation.md)
```

**Directory Context Rules**:

- From `SKILL.md` → reference files: `[text](./references/filename.md)`
- From `references/modern-modules.md` → same dir: `[text](./filename.md)`
- From `references/modern-modules.md` → subdir: `[text](./modern-modules/filename.md)`

**Why This Matters**:

1. Navigability: Markdown links allow Claude Code to click through to referenced files
2. Portability: Relative paths work regardless of installation location
3. Progressive Disclosure: Claude can load referenced files on demand, preserving context efficiency
4. User Experience: Users and Claude can follow references naturally

</correct_pattern>

<anti_patterns>

The model MUST NOT use these patterns:

**❌ Backticks Around Filenames** (not navigable):

```markdown
See `modern-modules/httpx.md` for details
```

**❌ Absolute Paths** (not portable):

```markdown
See [httpx](/home/user/repos/claude_skills/python3-development/references/modern-modules/httpx.md)
```

**❌ Skill Activation as File Path** (incorrect syntax):

```markdown
See `/uv/SKILL.md` for uv documentation
```

Correct: `Activate the uv skill with @uv or Skill(command: "uv")`

**❌ Relative Paths Without `./` Prefix** (ambiguous):

```markdown
[text](references/file.md)
```

Correct: `[text](./references/file.md)`

</anti_patterns>

### Skill Activation References

<skill_reference_pattern>

When referencing other skills, the model MUST use activation syntax in descriptive text:

**✅ Correct**:

```markdown
For comprehensive Astral uv documentation, activate the uv skill:

Skill(command: "uv")
```

**❌ Incorrect**:

```markdown
See `/uv/SKILL.md` for uv documentation
```

</skill_reference_pattern>

---

## Skill Documentation Verification Requirements

<critical_understanding>

**Skill documentation (SKILL.md, reference files) is AI-facing documentation, NOT user-facing documentation.**

**Primary Audience**:

1. The orchestrator (Claude) - reads skills to guide orchestration decisions, agent selection, workflow patterns
2. Sub-agents - load and follow the same skill guidance when delegated tasks
3. Future sessions - skills persist across conversations and inform all future AI instances

**NOT the Primary Audience**:

- Human users do not directly read SKILL.md line-by-line
- Skills are NOT user-facing product documentation
- Skills are AI→AI instruction sets

</critical_understanding>

### Why Verification Matters for Skill Documentation

<verification_importance>

When the model writes false, unverified, or assumed information in skill documentation:

1. **The model misleads itself** - will reference and believe fabricated content later
2. **Sub-agents are misled** - follow incorrect guidance in their implementations
3. **Future sessions are misled** - false information persists and compounds
4. **The human receives wrong results** - because all AI instances follow bad guidance
5. **Creates false feedback loops** - wrong information becomes "truth" in context

**Critical Principle**: The model must treat skill documentation with the same rigor as code - it must be verified, cited, and accurate.

</verification_importance>

### Mandatory Verification Protocol

<verification_protocol>

Before documenting ANY behavior, capability, or characteristic of:

- Commands (slash commands in `~/.claude/commands/`)
- Agents (in `~/.claude/agents/`)
- Tools (CLI tools, system commands)
- Libraries or packages
- System behavior or configuration

**The model MUST execute ALL of these steps**:

<verification_steps>

1. **Read the Actual Source**

   - Command files: Read entire file, note line numbers
   - Agent files: Read YAML frontmatter and complete prompt
   - Official documentation: Use WebSearch, WebFetch, or mcp\_\_Ref tools
   - Library code: Read source files directly

2. **Verify the Behavior**

   - Execute commands/scripts if possible to observe actual behavior
   - Cite evidence from source files with line number references
   - Test against documented claims before writing them

3. **Cite Observations**

   - Format: "According to lines X-Y of [file path]..."
   - Format: "Testing command X produces output: [exact output]"
   - Format: "Per official documentation at [URL]..."

4. **Never Fabricate**

   - If unknown, state "unverified" explicitly
   - Research using available tools (Read, Grep, WebSearch, mcp\_\_Ref)
   - If unable to verify, state "Unable to verify [claim] due to [reason]"

5. **Distinguish Assumption from Fact**
   - Mark assumptions explicitly: "Assuming [X] based on [pattern/inference]"
   - Separate verified facts from reasonable inferences
   - Never present assumptions as facts

</verification_steps>

**Minimum Requirements**:

- Cite minimum 3 independent authoritative sources for major claims
- Include line numbers when referencing code files
- Execute test if behavior can be observed directly
- Note publication dates for documentation sources

</verification_protocol>

### Verification Examples

<examples>

<example type="violation">
  <scenario>Documenting command behavior without reading source</scenario>
  <incorrect_output>
→ Validates shebang matches script type
→ Checks PEP 723 metadata if external dependencies detected
  </incorrect_output>
  <problem>Written without reading actual command file to verify what it does</problem>
  <consequence>If command doesn't actually validate shebangs, this creates false information in AI knowledge base</consequence>
</example>

<example type="violation">
  <scenario>Assuming tool capabilities without verification</scenario>
  <incorrect_output>
python-portable-script agent creates stdlib-only scripts
  </incorrect_output>
  <problem>Written without reading agent implementation or verifying PEP 723 requirement</problem>
  <consequence>Sub-agents will follow incorrect guidance when using this agent</consequence>
</example>

<example type="violation">
  <scenario>Inventing requirements from training data patterns</scenario>
  <incorrect_output>
Stdlib-only scripts need PEP 723 for self-contained execution
  </incorrect_output>
  <problem>Based on pattern-matching from training, not verification of PEP 723 specification</problem>
  <consequence>Creates false technical requirement that propagates across sessions</consequence>
</example>

<example type="correct">
  <scenario>Verified documentation with source citation</scenario>
  <correct_output>
→ Corrects shebang to match script type
→ Adds PEP 723 metadata if external dependencies detected
→ Removes PEP 723 if stdlib-only
→ Sets execute bit if needed

Source: Lines 137, 154 of plugins/python3-development/skills/shebangpython/SKILL.md </correct_output> <rationale>Includes specific line number citations from actual source file</rationale> </example>

<example type="correct">
  <scenario>Explicit uncertainty when unable to verify</scenario>
  <correct_output>
The python-portable-script agent purpose is not yet verified. Before documenting its behavior, I will read the agent file to confirm its actual capabilities.
  </correct_output>
  <rationale>States uncertainty explicitly and commits to verification before documenting</rationale>
</example>

</examples>

---

## Reference Documentation Citation Requirements

<citation_requirements>

**Principle**: Reference documentation is only as reliable as its sources. Without citations, guidance cannot be verified, updated, or trusted.

**The model MUST provide source attribution for ALL reference documentation using one of these methods:**

### Citation Method 1: Inline Citations

Cite sources directly within the contextual section where the information is used:

```markdown
### Tool Naming Standards

RULE: Use snake*case for tool names with pattern `{service}*{action}\_{resource}`

SOURCE: [MCP Best Practices - Tool Naming](https://modelcontextprotocol.io/docs/best-practices#tool-naming) (accessed 2025-01-15)

EXAMPLES:

- `slack_send_message` (not just `send_message`)
```

### Citation Method 2: References Footer

Add a "## References" section at the end of the document:

```markdown
## References

1. **MCP Protocol Specification** - https://modelcontextprotocol.io/llms-full.txt (accessed 2025-01-15)
2. **FastMCP Documentation** - https://github.com/jlowin/fastmcp (accessed 2025-01-15)
3. **Tool Design Patterns** - Community consensus from FastMCP examples repository
```

Reference in text using: `[1]`, `[2]`, etc.

### Citation Method 3: Separate references.md File

For skills with extensive citations, create `./references/references.md`:

```markdown
# References for fastmcp-creator Skill

## Official Documentation

- MCP Protocol: https://modelcontextprotocol.io/llms-full.txt
- FastMCP: https://github.com/jlowin/fastmcp

## Community Resources

- FastMCP Examples: https://github.com/jlowin/fastmcp/tree/main/examples
```

Reference in SKILL.md: `See [References](./references/references.md) for complete source list`

### Required Citation Details by Source Type

**Derived from Another Skill:**

```markdown
SOURCE: Based on [mcp-builder skill](https://github.com/anthropics/claude-code-examples/tree/main/mcp-builder) ADAPTATIONS: Modified tool naming conventions for Python-specific patterns
```

**Collated from Websites/Forums:**

The model MUST cite EVERY source when aggregating information:

```markdown
SOURCES:

- [MCP Best Practices](https://modelcontextprotocol.io/docs/best-practices) (accessed 2025-01-15)
- [FastMCP GitHub Issues #42](https://github.com/jlowin/fastmcp/issues/42) (accessed 2025-01-15)
- [Reddit: r/ClaudeAI - MCP Tool Design Discussion](https://reddit.com/r/ClaudeAI/comments/xyz) (accessed 2025-01-15)

RATIONALE: Allows verification and updates as new information becomes available
```

**Based on User Preferences/Discussions:**

The model MUST document the origin with date:

```markdown
SOURCE: User preference established in conversation (2025-01-15) CONTEXT: User prefers 5-part tool description structure based on improved AI tool selection in testing VALIDATION: Tested on 20 tools, improved selection accuracy from 65% to 89%
```

**Based on Experiments/Testing:**

The model MUST document the experimental basis:

```markdown
SOURCE: Experimental validation (2025-01-15) METHOD: Tested 15 tools with varying description formats across 50 prompts RESULTS: 5-part structure yielded 89% correct tool selection vs 65% for unstructured descriptions DATASET: Available at ./references/experiments/tool-description-testing.md
```

### Verification Requirements

When creating or updating reference documentation, the model MUST verify:

- [ ] Every factual claim has a cited source
- [ ] URLs include access dates (format: YYYY-MM-DD)
- [ ] Skill derivations link to source skill repository
- [ ] User preferences note the conversation date
- [ ] Experimental claims reference datasets or methodology
- [ ] Citations distinguish between official docs, community practices, and opinions

### Prohibited Patterns

**❌ Uncited Best Practices:**

```markdown
RULE: Tool descriptions must be concise and actionable
```

**✅ Properly Cited:**

```markdown
RULE: Tool descriptions must be concise and actionable SOURCE: [MCP Best Practices](https://modelcontextprotocol.io/docs/best-practices#descriptions) (accessed 2025-01-15)
```

**❌ Vague Attribution:**

```markdown
Based on community best practices
```

**✅ Specific Attribution:**

```markdown
SOURCE: Pattern observed across FastMCP example projects:

- https://github.com/jlowin/fastmcp/tree/main/examples/weather (accessed 2025-01-15)
- https://github.com/jlowin/fastmcp/tree/main/examples/github (accessed 2025-01-15)
```

### Rationale

**Why Citations Matter:**

1. **Verifiability** - Claims can be checked against original sources
2. **Updateability** - When upstream documentation changes, we know what to update
3. **Authority** - Distinguishes official specs from opinions
4. **Trust** - Future AI sessions can validate guidance before following it
5. **Debugging** - When guidance fails, citations reveal whether source changed or was misinterpreted

**Without Citations:**

- Cannot distinguish fact from assumption
- Cannot update when sources change
- Cannot verify correctness
- Creates false feedback loops in AI knowledge

</citation_requirements>

---

## File Reference Verification Checklist

<verification_checklist>

When creating or updating reference files, the model MUST verify:

- [ ] All file references use markdown link syntax: `[text](./path)`
- [ ] Relative paths start with `./`
- [ ] Paths are relative to the file containing the reference
- [ ] Referenced files actually exist at those paths (verify with Read tool)
- [ ] No backticks used for file references (unless showing code/commands)
- [ ] Language specifiers present on all code fences
- [ ] Nested code blocks use proper backtick counts (4 for outer, 3 for inner)

</verification_checklist>

---

## Skill Validation vs Packaging

<skill_validation>

**Validation: YES** - The model MUST validate skills to ensure quality standards:

- YAML frontmatter is properly formatted
- Required fields are present (name, description, tools, model)
- File references are correct and target files exist
- Directory structure is valid

**Packaging: NO** - The model MUST NOT package skills into .zip files for distribution:

- Skills in this repository are for local use
- Already in their final location
- Packaging creates unnecessary files
- Serves no purpose for local development

</skill_validation>

---

## Markdown Formatting Standards

<markdown_standards>

The model MUST follow these markdown formatting rules:

**MD031/blanks-around-fences**: Fenced code blocks MUST be surrounded by blank lines

**Example**:

````markdown
This is a paragraph.

```python
def example():
    return True
```
````

This is another paragraph.

````

</markdown_standards>

---

## Local Formatting and Linting Tools

<available_tools>

The model MUST use these tools for formatting and linting in this repository:

```bash
uv run prek run --files <file>
```

**Note**: This repository uses `prek` (Rust-based pre-commit replacement), not `pre-commit`. Both use the same `.pre-commit-config.yaml` with identical syntax.

**When to use**:

- Before committing skill documentation
- After modifying SKILL.md or reference files
- To validate markdown formatting compliance

</available_tools>

---

## Linting Exception Conditions

<linting_exceptions>

The model MUST NOT ignore or bypass linting errors UNLESS the code falls into one of these categories:

**Acceptable Exceptions** (OK to ignore linting):

1. **Vendored code** - Third-party code copied into the repository without modification. The model did not author this code and should not modify it.

2. **Examples of what-not-to-do** - Intentionally incorrect code used for educational purposes or negative test cases. The linting errors are the point.

3. **Code specifically and intentionally pinned to historic Python version** - Code that must remain compatible with Python versions older than 3.11 where modern syntax is unavailable. Right now, no code in this repository is in this category, but call it out if you see it and ask about it.

4. **Code for Python derivatives** - CircuitPython, MicroPython, or other Python implementations with different syntax requirements or missing standard library modules.
Do not modify the files with inline comments that prevent linting like `# noqa`. Instead update the linting configuration files, such as the pyproject.toml or .vscode/settings.json to exclude the files that fall into these categories. If the user asks about why you are adding a file to the exclusions, you must double check the rules above and ensure that the file does actually fit. If it does fit, then you can say the file fits the linting_exception list item {item}.

**Unacceptable Exceptions** (MUST fix or escalate):

If NONE of the above conditions apply, the model MUST:

1. Fix the linting smell by using the hollistic-linting:hollistic-linting Skill, which describes the exact methodology required when addressing linting issues.
2. If unable to fix, document the specific blocker
3. Never add `# type: ignore`, `# noqa`, or similar suppressions without explicit user approval

**Rule Codes That MUST Always Be Fixed** (never suppress):

These rule codes indicate real code quality issues that must be resolved at root cause:

- **BLE001** (blind-except): Replace generic `except Exception` with specific exception types
- **D103** (missing-docstring-in-public-function): Add docstrings to public functions
- **TRY300** (try-consider-else): Restructure try/except/else blocks properly

**Per-File Exceptions in pyproject.toml** (acceptable):

The following rules may be configured as per-file ignores in `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`:

- `**/scripts/**`: T201 (print), S (security), DOC, ANN401, PLR0911, PLR0917, PLC0415
- `**/tests/**`: S, D, E501, ANN, DOC, PLC, SLF, PLR, EXE, N, T
- `**/assets/**`: PLC0415, DOC
- `typings/**`: N, ANN, A

These configurations allow relaxed checking in appropriate contexts without inline suppressions.

**Touched Files Must Be Clean**:

When files are modified, moved, or renamed, all linting issues in those files MUST be resolved before committing. Touching a file means taking responsibility for its quality.

**SOURCE**: User policy established in conversation (2025-01-15)

</linting_exceptions>

---

When referencing a skill we do not use the '@' symbol, we use '/'. When referencing an agent we use '@' and not '/'.
You are NEVER allowed to suppose anything. No Speculation as diagnosis. You say what occured, and what you observed when it occured. You do not project causality into the situation when you can't show that relationship
````
