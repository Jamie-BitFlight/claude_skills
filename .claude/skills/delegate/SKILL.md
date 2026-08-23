---
name: delegate
description: Delegation prompt template enforcing WHERE-WHAT-WHY structure for sub-agent prompts. Use when assigning work to a sub-agent, before invoking the Agent tool, preparing prompts for specialized agents, or needing the OBSERVATIONS-SUCCESS-CONTEXT format with authoring rules and pre-send checklist. For comprehensive delegation guidance, activate the agent-orchestration how-to-delegate skill.
user-invocable: true
---

# Delegation Template

**Workflow Reference**: See [Multi-Agent Orchestration](./../../knowledge/workflow-diagrams/multi-agent-orchestration.md) for complete delegation flow with DONE/BLOCKED signaling.

**Step 1:** Load `mattpocock-skills:writing-for-agents`. The prompt you are about to write is a
document an agent consumes, and its levers — duplication, no-ops, negation, completion criteria —
govern it.

**Step 2:** Analyze the task. Do you have the "WHERE, WHAT, WHY"?

**Step 3:** Construct the prompt using the template below. Keep it DRY against the repository: the
agent loads `AGENTS.md` and `CLAUDE.md` itself, so a prompt restating what they already say is a
second copy of one meaning that goes stale silently while the file moves on.

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

DELIVERY:
- [The channel that reaches the dispatcher, and where any longer artifact is written]

CONTEXT:
- Location: [Where to look]
- Scope: [Boundaries]
- Constraints: [Hard requirements vs Preferences]

ECOSYSTEM CONTEXT:
- [Session-specific facts the agent cannot find in CLAUDE.md or tool descriptions]
- [Authenticated CLIs, non-obvious doc locations, task-specific access]

YOUR TASK:
1. Run /dh:verify-done (as completion criteria guide)
2. Perform comprehensive context gathering
3. Form hypothesis → Experiment → Verify
4. Implement solution
5. Only report completion after /dh:verify-done criteria are met
```

**Authoring guidance** (for the orchestrator filling in this template — do not include these annotations in the delivered prompt):

- **OBSERVATIONS**: Pass-through only — data already in your context (user messages, prior agent reports, command outputs you already received). Include file:line references if already known. Include verbatim error messages, not paraphrased. Do NOT pre-gather data for the agent (e.g., don't run `ruff check .` before delegating to a linting agent). Do NOT read, grep, or glob files to find context for the agent — the agent has full tool access and an empty context window; it does its own discovery. No interpretations ("I think"), no assumptions ("probably"). SOURCE: [agent-orchestration SKILL.md](./../../../plugins/agent-orchestration/skills/agent-orchestration/SKILL.md) — Pre-Delegation Verification Checklist section.
- **DEFINITION OF SUCCESS**: The "WHAT". Measurable outcomes the agent can verify. When the agent will produce more than ~1 line of output, instruct it to write results to a file and return only the path — this keeps orchestrator context lean. Example: `Write findings to .claude/reports/NAME-YYYYMMDD.md. Return: STATUS: DONE + file path.`
- **DELIVERY**: State the delivery channel explicitly. The channel that carries an agent's final response back to its dispatcher differs between harnesses. Name the channel this dispatch expects, and name the artifact fallback: the full result written to a file whose path the agent returns. A result that exists only in the agent's final response text may never be read. Do not assume the dispatcher receives anything the prompt did not ask the agent to send.
- **CONTEXT**: The "WHERE" and "WHY". Location narrows scope; constraints bound the solution space.
- **ECOSYSTEM CONTEXT**: Only what exists because of this session and cannot be found by reading the repo — which branch a PR merged into, that another agent is live on the same files, a change made an hour ago that is not in `main` yet. Repo conventions belong to `AGENTS.md`; restating them here is duplication, and restating them as prohibitions is worse, since a banned behaviour named in a prompt is more available to the model, not less.

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
| **Stated Delivery** | Every prompt names how the result reaches the dispatcher                                |

---

## Quick Checklist

- [ ] Starts with `Your ROLE_TYPE is sub-agent.`
- [ ] Contains only factual observations
- [ ] No assumptions stated as facts
- [ ] Defines WHAT and WHY, not HOW
- [ ] Lists resources without prescribing tools
- [ ] Says nothing `AGENTS.md` or `CLAUDE.md` already says
- [ ] Names the delivery channel and where any longer artifact is written
