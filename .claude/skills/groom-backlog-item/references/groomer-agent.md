# Groomer Agent Prompt Templates

Full prompt templates for spawning `backlog-item-groomer` agents in Step 8.

---

## RT-ICA Categorization Rule

The rtica-assessor and any agent performing RT-ICA assessment MUST apply this rule before listing any condition:

RT-ICA assesses INFORMATION completeness — "do we know enough to plan?" Only conditions that
represent information gaps or verifiable facts about the environment belong in RT-ICA.
Implementation deliverables (things to build) belong in acceptance criteria, not RT-ICA conditions.

- AVAILABLE — information exists and is verified from the item or codebase
- DERIVABLE — information can be obtained with tools (grep, read, web search, command output)
- MISSING — information we lack that cannot be derived and requires a human decision

A condition like "sam create command exists" is a deliverable — it belongs in acceptance criteria.
The RT-ICA question is "do we know what sam create needs to do?" — if yes, AVAILABLE.

Before marking any condition MISSING, attempt to resolve it with tools. Every resolution must
cite the tool result. Answering project-specific conditions from training data is banned.

---

## Single Item

```text
Agent(
  description: "Groom backlog item",
  subagent_type: "backlog-item-groomer",
  prompt: "Groom this backlog item. Output groomed content in the standard template format (see .claude/docs/backlog-item-groomed-schema.md). Output only the groomed body (no ## Groomed header). The groomer agent does NOT perform classification or root-cause analysis — it receives these as inputs and incorporates them into groomed output.

SCOPE BOUNDARY — Problem space and outcomes only. Do NOT include implementation steps, architecture decisions, code design, or proposed solutions. Those belong in the SAM planning phase (add-new-feature / architect spec), which runs AFTER grooming. Groomed output describes: (1) what the problem is and where it lives, (2) what success looks like, (3) how the specialist will know they have reached it. Acceptance criteria must be observable checks — not implementation steps.

Item title: {item title}
Item description: {item description}
Item source: {item source}
Item priority: {item priority}
Item file path: {item file path}

RT-ICA Assessment:
{rt-ica summary}

Fact-Check Verdicts:
{fact-check summary}

Issue Classification:
{classification section from Step 6}

Root-Cause Analysis:
{evidence chain from Step 7, or 'N/A - not applicable for this issue type'}

Impact Radius:
{impact radius section from Step 3.5 — documents, upstream producers, downstream consumers, config/CI files, and Ecosystem Completeness Checklist}

Additional context from conversation:
{any relevant user messages or discussion context}",
  model: "sonnet"
)
```

## Multiple Items (parallel, max 5 concurrent)

Batch in waves of 5 if more than 5 items. Each agent uses `subagent_type: "backlog-item-groomer"`:

```text
Agent(
  description: "Groom backlog item",
  subagent_type: "backlog-item-groomer",
  prompt: "Groom this backlog item. Output groomed content in the standard template format (see .claude/docs/backlog-item-groomed-schema.md). Output only the groomed body (no ## Groomed header). The groomer agent does NOT perform classification or root-cause analysis — it receives these as inputs and incorporates them into groomed output.

SCOPE BOUNDARY — Problem space and outcomes only. Do NOT include implementation steps, architecture decisions, code design, or proposed solutions. Those belong in the SAM planning phase (add-new-feature / architect spec), which runs AFTER grooming. Groomed output describes: (1) what the problem is and where it lives, (2) what success looks like, (3) how the specialist will know they have reached it. Acceptance criteria must be observable checks — not implementation steps.

Item title: {item title}
Item description: {item description}
Item file path: {item file path}

RT-ICA Assessment:
{rt-ica summary}

Fact-Check Verdicts:
{fact-check summary}

Issue Classification:
{classification section from Step 6}

Root-Cause Analysis:
{evidence chain from Step 7, or 'N/A - not applicable for this issue type'}

Impact Radius:
{impact radius section from Step 3.5 — documents, upstream producers, downstream consumers, config/CI files, and Ecosystem Completeness Checklist}",
  model: "sonnet"
)
```

The `backlog-item-groomer` agent discovers related skills, agents, prior work, and dependency graphs. Pass file paths (not file contents) so it can verify independently.
