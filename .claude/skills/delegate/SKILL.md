---
name: delegate
description: Quick delegation template for sub-agent prompts. Use when assigning work to a sub-agent, before invoking the Agent tool, or when preparing prompts for specialized agents. Provides the WHERE-WHAT-WHY framework. For comprehensive delegation guidance, activate the agent-orchestration how-to-delegate skill.
user-invocable: true
---
# Delegation Template

**Workflow Reference**: See [Multi-Agent Orchestration](./../../knowledge/workflow-diagrams/multi-agent-orchestration.md) for complete delegation flow with DONE/BLOCKED signaling.

**Step 1:** Analyze the task. Do you have the "WHERE, WHAT, WHY"?

**Step 2:** Construct the prompt using the template below.

---

## Template

```text
Your ROLE_TYPE is sub-agent.

[Task Identification - one sentence]

OBSERVATIONS:
- [Factual observations already in your context]
- [Verbatim error messages if applicable]
- [Environment or system state if relevant]

DEFINITION OF SUCCESS:
- [Specific measurable outcome]
- [Acceptance criteria]
- [Verification method]

CONTEXT:
- Location: [Where to look]
- Scope: [Boundaries]
- Constraints: [Hard requirements vs Preferences]

ECOSYSTEM CONTEXT:
- [Session-specific facts the agent cannot find in CLAUDE.md or tool descriptions]
- [Authenticated CLIs, non-obvious doc locations, task-specific access]

YOUR TASK:
1. Run /verify (as completion criteria guide)
2. Perform comprehensive context gathering
3. Form hypothesis → Experiment → Verify
4. Implement solution
5. Only report completion after /verify criteria are met
```

**Authoring guidance** (for the orchestrator filling in this template — do not include these annotations in the delivered prompt):

- **OBSERVATIONS**: Pass-through only — data already in your context (user messages, prior agent reports, command outputs you already received). Include file:line references if already known. Include verbatim error messages, not paraphrased. Do NOT pre-gather data for the agent (e.g., don't run `ruff check .` before delegating to a linting agent). Do NOT read, grep, or glob files to find context for the agent — the agent has full tool access and an empty context window; it does its own discovery. No interpretations ("I think"), no assumptions ("probably"). SOURCE: [agent-orchestration SKILL.md](./../../../plugins/agent-orchestration/skills/agent-orchestration/SKILL.md) — Pre-Delegation Verification Checklist section.
- **DEFINITION OF SUCCESS**: The "WHAT". Measurable outcomes the agent can verify. When the agent will produce more than ~1 line of output, instruct it to write results to a file and return only the path — this keeps orchestrator context lean. Example: `Write findings to .claude/reports/NAME-YYYYMMDD.md. Return: STATUS: DONE + file path.`
- **CONTEXT**: The "WHERE" and "WHY". Location narrows scope; constraints bound the solution space.

---

## Delegation Rules

Check before sending:

| Rule               | Check                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------- |
| **Formula**        | Delegation = Observations + Success Criteria + Resources - Assumptions - Micromanagement |
| **No HOW**         | Do NOT tell agent _how_ to implement (e.g., "Change line 42 to X")                       |
| **Constraints OK** | DO tell agent _constraints_ (e.g., "Must use the 'requests' library")                    |
| **No Assumptions** | Do NOT say "The issue is probably..."                                                    |
| **Full Scope**     | If code smell found, instruct agent to audit _entire pattern_, not single instance       |

---

## Quick Checklist

- [ ] Starts with `Your ROLE_TYPE is sub-agent.`
- [ ] Contains only factual observations
- [ ] No assumptions stated as facts
- [ ] Defines WHAT and WHY, not HOW
- [ ] Lists resources without prescribing tools
