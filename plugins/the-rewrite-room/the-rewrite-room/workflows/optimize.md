# Optimize Workflow

Loaded by: `/rwr:optimize` command
Orchestrator: Claude (reads this workflow and executes steps)

## Step 1 — Read Prompt Optimization Principles

Before ANY optimization task, load the knowledge reference:

Read `plugins/plugin-creator/skills/prompt-optimization/SKILL.md`

Key principle to carry forward: positive framing over prohibitions (models attend to key nouns — "NEVER use X" still activates "use X"). The optimizer will fix prohibition patterns.

## Step 2 — Classify Target

```mermaid
flowchart TD
    Start([$ARGUMENTS]) --> Q{Target file pattern?}
    Q -->|"CLAUDE.md, .claude/CLAUDE.md"| CLAUDEmd[Type: CLAUDE.md optimization\nAgent: plugin-creator:ai-doc-optimizer]
    Q -->|"SKILL.md, skills/**/*"| SKILLmd[Type: SKILL.md optimization\nAgent: plugin-creator:ai-doc-optimizer]
    Q -->|"agents/*.md, */agents/*.md"| AgentFile[Type: Agent definition optimization\nSee agent selection below]
    Q -->|"Any AI-facing .md prompt file"| Prompt[Type: Prompt optimization\nAgent: plugin-creator:ai-doc-optimizer]
    AgentFile --> AgentQ{Optimization type?}
    AgentQ -->|"Content/structure improvement"| ContentOpt[Agent: plugin-creator:ai-doc-optimizer]
    AgentQ -->|"Applying Anthropic official best practices"| BestPractices[Agent: plugin-creator:subagent-refactorer]
    AgentQ -->|Unclear| DefaultOpt[Default: plugin-creator:ai-doc-optimizer\nHandles both]
```

Routing by concern:
- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `plugin-creator:ai-doc-optimizer`
- Audit quality (read-only, no writes, score against completeness categories) → `plugin-creator:skill-auditor`
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `plugin-creator:skill-content-updater`
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly

## Step 3 — Read Agent Protocol

Before spawning, read the agent's file:

- ai-doc-optimizer: Read `plugins/plugin-creator/agents/ai-doc-optimizer.md`
  - Note: It runs its own RT-ICA blocking gate. Do not pre-empt it.
  - Note: Pass file PATH — never pre-summarize file content for it.

- subagent-refactorer: Read `plugins/plugin-creator/agents/subagent-refactorer.md`
  - Note: It has a MANDATORY research phase reading official Anthropic docs first.

## Step 4 — Spawn Agent

For ai-doc-optimizer:

```text
Agent(
  subagent_type="plugin-creator:ai-doc-optimizer",
  prompt="Optimize the following file for Claude comprehension:

File: <path>

Target audience: AI-facing
Constraints: [any specific constraints from user]"
)
```

For subagent-refactorer:

```text
Agent(
  subagent_type="plugin-creator:subagent-refactorer",
  prompt="Refactor this agent using Anthropic official best practices:

Agent file: <path>

Target model: [sonnet/opus if specified, default sonnet]
Specific issues: [if any identified]"
)
```

## Step 5 — Handle Return

```mermaid
flowchart TD
    Return([Agent returns]) --> Q{STATUS?}
    Q -->|DONE| TokenReport[Present token impact report to user]
    TokenReport --> Diff{Before/after diff available?}
    Diff -->|Yes| ShowDiff[Show diff]
    Diff -->|No| Skip[Skip]
    ShowDiff --> Validate[Run frontmatter validation on modified file]
    Skip --> Validate
    Validate --> ValQ{Validation result?}
    ValQ -->|Pass| Done([Done])
    ValQ -->|Fail| Report[Report issues to user and offer to fix]
    Q -->|BLOCKED| ShowNeeded[Show NEEDED list to user]
    ShowNeeded --> Gather[Gather missing information]
    Gather --> Retry[Return to Step 4 with complete context]
    Q -->|Issues found but not fixed| Revision{Revision cycle count?}
    Revision -->|Less than 2| Revise[Pass previous output as context\nReturn to Step 4]
    Revision -->|2 or more| Escalate[Report unresolved issues to user]
```

Frontmatter validation command:

```bash
uv run plugins/plugin-creator/scripts/normalize_frontmatter.py <modified-file>
```

Revision context prompt template:

```text
"Previous attempt found: [issues]. Please address these specifically."
```

## Output Contract

Base format — see [../references/status-block-contract.md](../references/status-block-contract.md).

Optimize workflow VALIDATION subfields:

```text
VALIDATION:
  - frontmatter-check: PASS|FAIL  (normalize_frontmatter.py exit code)
  - skilllint-check: PASS|FAIL    (uvx skilllint@latest exit code)
```
