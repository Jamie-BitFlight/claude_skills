# Agent Lifecycle Audit — Research Document

Deep semantic validation of how agents are configured, what they claim to do, what tools and skills they have access to, and whether their prompts align with the actual capabilities of the components they invoke.

This document describes audit dimensions and detection strategies for future implementation. It is not an executable skill.

---

## What This Audit Does

Given a plugin (or a single agent within a plugin), examine the agent's frontmatter configuration, prompt body, skill references, tool access, and delegation patterns — then evaluate whether the agent can actually accomplish what its description and prompt claim.

This complements the skill-lifecycle-audit: skills define workflows, agents execute them. This audit validates the execution side.

---

## Audit Dimensions

### 1. Capability vs Configuration Alignment

For each agent, compare:

- **What the description claims**: "Reviews Python 3.11+ code for quality, modernization, and best practices"
- **What the prompt instructs**: "Run code smell analysis using `/python-check-codesmells`"
- **What tools are available**: Does the agent's `tools` field (or inherited tools) include what's needed to execute the prompt instructions?
- **What skills are loaded**: Does the agent load the skills it references in its prompt?

**Misalignment examples**:
- Agent description says "runs tests" but agent has no `Bash` tool access
- Agent prompt says "load the uv skill" but `skills` field doesn't include `uv`
- Agent prompt says "use WebFetch to check documentation" but tool list doesn't include `WebFetch`

**Output**: Per-agent capability matrix: `CLAIMED` (in description), `INSTRUCTED` (in prompt), `AVAILABLE` (in tools/skills config), with flags where these don't align.

### 2. Skill Loading Correctness

For each skill reference in an agent prompt:

- Is the skill reference resolvable? (structural — defer to NamespaceReferenceValidator)
  - Intra-plugin references (skill in the same plugin as the agent): bare name works — `write-frontmatter-description`
  - Cross-plugin references (skill in a different plugin): full namespace required — `plugin-creator:audit-skill-completeness`
  - Both forms are valid for intra-plugin; bare name is the cleaner convention
  - Do not flag bare names as errors when the referenced skill lives in the same plugin
  - Verified 2026-02-26, session observation — January 2026 behavior required namespace everywhere, current behavior does not
- Does the loaded skill actually provide the capability the agent expects from it?
- Does the agent pass appropriate inputs to the skill?
- Does the agent consume the skill's output format correctly?

**Example**: An agent loads `/python-engineering:modernpython` and instructs "run modernpython to fix legacy patterns." But `modernpython` is a reference guide, not an automated fixer. The agent's prompt misrepresents what the skill does.

**Output**: Per-agent list of skill loads with semantic correctness evaluation.

### 3. Inter-Agent Contract Alignment

When agents delegate to other agents:

- Does the delegating agent's prompt describe inputs that match what the target agent expects?
- Does the delegating agent expect outputs in a format the target agent produces?
- Are there assumptions about shared state (files, directories, environment variables) that aren't explicitly communicated?

**Example**: `python-cli-architect` delegates to `python-pytest-architect` with "create tests for this implementation." Does `python-pytest-architect` expect to receive file paths? Architecture docs? Both? Does the delegating agent provide what's expected?

**Output**: Contract alignment matrix between agent pairs that delegate to each other.

### 4. Prompt Instruction Contradictions

Compare the instructions within a single agent prompt and across related agents:

- **Internal contradictions**: The same agent says "always use Typer" in one section and "use argparse for CLI" in another, without conditional guards
- **Cross-agent contradictions**: Agent A says "format with ruff before linting" and Agent B says "lint first, then format" — when both operate in the same workflow
- **Skill-agent contradictions**: An agent's prompt gives instructions that conflict with the skill it loads (e.g., agent says "use `unittest.mock`" but loaded skill says "use `pytest-mock` exclusively")

**Output**: Contradiction pairs with file:line references, classification (internal/cross-agent/skill-agent), and whether guarded by conditions.

### 5. Tool Access Sufficiency

For each action the agent prompt describes:

- What tool is required to perform this action?
- Is that tool in the agent's `tools` field (or inherited)?
- If the tool is restricted via `disallowedTools`, is the agent trying to use it anyway?

**Categories**:
- `Bash` needed for: running commands, executing scripts, git operations
- `Read`/`Write`/`Edit` needed for: file operations
- `Grep`/`Glob` needed for: search operations
- `Task` needed for: delegating to other agents
- `WebFetch`/`WebSearch` needed for: documentation lookup
- MCP tools needed for: specific integrations

**Output**: Per-agent tool sufficiency report. Flag instructions that require tools the agent doesn't have.

### 6. Dead Agent Detection

Identify agents that:

- Are registered in `plugin.json` but never referenced by any skill, command, or other agent
- Are referenced in documentation but never activated as `/plugin:skill` or dispatched as `plugin:agent`
- Have descriptions with trigger phrases that no workflow ever activates

**Output**: List of potentially dead agents with evidence (no inbound references found).

### 7. Scriptable Agent Patterns

Identify agents whose entire workflow could be replaced by a script:

- Agent prompt is a fixed sequence of tool calls with no conditional logic
- Agent doesn't need AI reasoning — just runs commands in order
- Agent's "decisions" are deterministic based on file existence or command output

These are candidates for conversion to Python scripts or commands, which execute faster, cost nothing, and are deterministic.

**Output**: List of scriptable agent patterns with the deterministic steps identified.

### 8. Self-Referential Pattern Learning

Same approach as skill-lifecycle-audit dimension 7:

1. Classify each discovered issue by detection pattern
2. Record the pattern with description, heuristic, and example
3. Re-scan all already-audited agents using the newly discovered pattern
4. Repeat until convergence

**Output**: Append to the shared `patterns.md` file (same file as skill-lifecycle-audit).

---

## Recursive Depth Strategy

### Tier 1: Configuration Scan (fast, automated)

- Parse frontmatter: extract tools, skills, model, disallowedTools
- Extract all Skill/Task/@ references from prompt body
- Build agent dependency graph
- Check tool sufficiency against instruction keywords

### Tier 2: Semantic Analysis (AI reasoning required)

- Read agent description and full prompt to understand claimed purpose
- Compare claimed purpose against actual instructions
- Evaluate whether skill loads make semantic sense
- Detect instruction contradictions with context awareness

### Tier 3: Specialist Delegation (for specific issue types)

```mermaid
flowchart TD
    Q{Issue type?}
    Q -->|Tool access ambiguity| Docs["Dispatch context-gathering agent for Claude Code tool inheritance research<br>Context: agent file path, specific ambiguous tool reference<br>Output: .planning/audit/tool-access-finding.md —<br>confirmed behavior with documentation citations"]
    Q -->|Cross-agent contract mismatch| Contract["Dispatch context-gathering agent for input/output contract evaluation<br>Context: delegating agent path, target agent path,<br>specific contract claim in prompt<br>Output: .planning/audit/contract-mismatch.md —<br>compatibility verdict with file:line evidence"]
    Q -->|Prompt quality issues| Prompt["Dispatch plugin-creator:subagent-refactorer for prompt optimization<br>Context: agent file path, finding description,<br>audit dimension that detected the issue<br>Output: .planning/audit/improvements/{agent-name}-patch.md —<br>revised prompt with rationale"]
```

---

## Relationship to Skill Lifecycle Audit

These two audits are complementary:

| Aspect | skill-lifecycle-audit | agent-lifecycle-audit |
|---|---|---|
| Primary target | SKILL.md files | Agent .md files |
| Focus | Workflow coherence | Execution capability |
| Call graph direction | Skill → Skill, Skill → Agent | Agent → Agent, Agent → Skill |
| Contradiction scope | Cross-skill instructions | Cross-agent and agent-vs-skill |
| Duplication scope | Shared content between skills | N/A (agents rarely duplicate) |
| Scriptability | Multi-command sequences in skills | Deterministic agent workflows |

**Recommended execution order**: Run skill-lifecycle-audit first (it maps the workflow graph), then agent-lifecycle-audit (it validates agents can execute those workflows). Findings from each inform the other — the `patterns.md` file is shared.

---

## Output Artifacts

The audit produces:

1. **`agent-audit-report-{plugin-slug}.md`** — Full findings organized by dimension
2. **`agent-dependency-graph-{plugin-slug}.md`** — Agent-to-agent and agent-to-skill delegation graph
3. **`patterns.md`** — Shared pattern catalog (appended to, shared with skill-lifecycle-audit)
4. **`agent-recommendations.md`** — Prioritized list of actionable fixes

Each finding includes:
- Agent file path and line number
- The specific text that triggered the finding
- The audit dimension that detected it
- Severity: `error` (agent cannot accomplish its purpose), `warning` (partial capability gap), `info` (optimization opportunity)
- Whether the finding was confirmed by a specialist delegation

---

## What This Audit Does NOT Do

- Does NOT fix issues (audit only)
- Does NOT validate namespace references resolve to files (that's `NamespaceReferenceValidator`)
- Does NOT validate frontmatter schema (that's `skilllint`)
- Does NOT optimize agent prompts (that's `@plugin-creator:subagent-refactorer`)
- Does NOT assess plugin structure (that's `/plugin-creator:assessor`)

This audit answers: "Given that all the agents exist and their references resolve, can these agents actually do what they claim to do, and do they work together correctly?"
