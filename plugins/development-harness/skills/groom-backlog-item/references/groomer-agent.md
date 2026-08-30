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
  subagent_type: "dh:backlog-item-groomer",
  prompt: "Groom this backlog item. Output groomed content in the standard template format — load dh:dh-meta-docs and read the Backlog Item Groomed Schema document it lists. Output only the groomed body (no ## Groomed header). The groomer agent does NOT perform classification or root-cause analysis — it receives these as inputs and incorporates them into groomed output.

SCOPE BOUNDARY — Problem space and outcomes only. Do NOT include implementation steps, architecture decisions, code design, or proposed solutions. Those belong in the SAM planning phase (add-new-feature / architect spec), which runs AFTER grooming. Groomed output describes: (1) what the problem is and where it lives, (2) what success looks like, (3) how the specialist will know they have reached it. Acceptance criteria must be observable checks — not implementation steps.

DESCRIPTION / AC SEPARATION — The item description is the problem statement: what is wrong, where it lives, and why it matters. Acceptance Criteria are the verifiable success conditions: observable checks that confirm the problem is resolved. Do not restate or paraphrase the description inside Acceptance Criteria. If the description already contains checkboxes or an Acceptance header, treat them as informal notes — write formal, non-overlapping ACs that complement rather than duplicate them.

SCOPE-GATE ACs AND AUTOMATION — When writing a scope-limiting criterion (e.g. 'no other file changes', 'only file X is modified'), scope it to unrequested *content* changes. Do not word it to fail on files that an already-configured project automation modifies as a side effect of any commit — a pre-commit hook bumping version manifests, an agent recording its own operational notes, a formatter or linter auto-fix. Those are deterministic tooling output, not agent-introduced scope creep, and a literal 'zero other files touched' criterion is unsatisfiable wherever such automation runs.

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

Batch in waves of 5 if more than 5 items. Each agent uses `subagent_type: "dh:backlog-item-groomer"`:

```text
Agent(
  description: "Groom backlog item",
  subagent_type: "dh:backlog-item-groomer",
  prompt: "Groom this backlog item. Output groomed content in the standard template format — load dh:dh-meta-docs and read the Backlog Item Groomed Schema document it lists. Output only the groomed body (no ## Groomed header). The groomer agent does NOT perform classification or root-cause analysis — it receives these as inputs and incorporates them into groomed output.

SCOPE BOUNDARY — Problem space and outcomes only. Do NOT include implementation steps, architecture decisions, code design, or proposed solutions. Those belong in the SAM planning phase (add-new-feature / architect spec), which runs AFTER grooming. Groomed output describes: (1) what the problem is and where it lives, (2) what success looks like, (3) how the specialist will know they have reached it. Acceptance criteria must be observable checks — not implementation steps.

DESCRIPTION / AC SEPARATION — The item description is the problem statement: what is wrong, where it lives, and why it matters. Acceptance Criteria are the verifiable success conditions: observable checks that confirm the problem is resolved. Do not restate or paraphrase the description inside Acceptance Criteria. If the description already contains checkboxes or an Acceptance header, treat them as informal notes — write formal, non-overlapping ACs that complement rather than duplicate them.

SCOPE-GATE ACs AND AUTOMATION — When writing a scope-limiting criterion (e.g. 'no other file changes', 'only file X is modified'), scope it to unrequested *content* changes. Do not word it to fail on files that an already-configured project automation modifies as a side effect of any commit — a pre-commit hook bumping version manifests, an agent recording its own operational notes, a formatter or linter auto-fix. Those are deterministic tooling output, not agent-introduced scope creep, and a literal 'zero other files touched' criterion is unsatisfiable wherever such automation runs.

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

---

## Impact Radius Output Format

The impact-analyst teammate writes the Impact Radius section in this format:

```markdown
## Impact Radius

### Code — Producers (write the changed interface)
- `{path}::{function_name}` — {what it produces, what change is needed}

### Code — Consumers (read the changed interface)
- `{path}::{function_name}` — {what it consumes, what migration is needed}

### Code — Other References
- `{path}` — {import/constant/type reference, what change is needed}

### Documentation (will become stale)
- `{path}` — {what section becomes inaccurate}

### Configuration / CI
- `{path}` — {what change is needed}

### Agent Instructions (instruct AI to use current interface)
- `{path}` — {what instruction needs updating}

### Systems Inventory
{full list of TodoItems with roles and connections, for planner completeness verification}

### Ecosystem Completeness Checklist
- [ ] Every code producer updated or verified compatible
- [ ] Every code consumer migrated to new interface
- [ ] Every stale document updated
- [ ] Every agent instruction updated
- [ ] Old interface deprecated or removed (if replacing)
- [ ] CI/config files updated and validated
```

If a category has no affected files, write `None identified.` — do not omit the category.

---

## RT-ICA BLOCKED Batch Format

When MISSING conditions remain after the self-resolution pass in Step 8.5, present them as:

```text
RT-ICA: BLOCKED

The following inputs could not be resolved autonomously.

[Category]:
- Question: {what is unknown}
  Tried: {tools used, what they returned}
  Options found: {a) option with trade-off | b) option with trade-off | c) open-ended}

Answer what you can — skip what you don't know.
Grooming will not proceed to Step 9 with unresolved gaps.
```

---

## Fact-Checker Output Contract

Each claim in fact-checker output must contain these required fields:

```text
verdict: VERIFIED | REFUTED | INCONCLUSIVE
claim: {exact claim from item}
evidence: {tool result citation — WebFetch, WebSearch, Bash, or Read output}
source: {URL or file path with line numbers}
```

Validation rules applied by the orchestrator before writing to `section="Fact-Check"`:

- If `verdict` field absent: reject the claim, log "fact-checker output missing verdict field", do not write
- If `evidence` field absent: mark claim INCONCLUSIVE, write with note "evidence field missing"
- Verdict to RT-ICA mapping: REFUTED maps to MISSING condition, INCONCLUSIVE maps to DERIVABLE
