---
name: github-research-agent-patterns
research_date: "2025-12-09"
source_url: "https://github.com/github-patterns"
version_at_research: "community-maintained"
license: "Mixed (individual repos vary)"
freshness_tracking:
  last_verified: "2026-08-11"
  version_at_verification: "as of 2026-08-11"
  next_review: "2026-11-11"
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: high (code-read) | Installation & Usage: high | Relevance: high | References: high"
---

# GitHub Research Agent Patterns

## Overview

Comprehensive collection of 5 major research agent architecture patterns discovered from open-source GitHub repositories, including production-ready Claude Code agent implementations, academic research workflows, and multi-agent orchestration systems. Covers 40+ awesome lists and specialized research repositories with 100+ production-ready agent definitions, 12-agent academic pipelines, Pydantic AI frameworks, and chief-of-staff orchestration models. Research completed December 2025; patterns extracted from yuz207/claude-agents-research-team, adrianstier/research-agent, aldiakhou/codex-main, and curated awesome lists (hesreallyhim/awesome-claude-code, VoltAgent/awesome-claude-code-subagents, punkpeye/awesome-mcp-servers).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Multi-agent research workflows lack clear orchestration patterns and role definitions | Chief of Staff model (yuz207/claude-agents-research-team) defines explicit team structure, role separation, and request-based coordination |
| Research findings get lost or fragmented across multiple agent invocations | Context preservation protocol: mandatory agent context files with complete workflow state, findings, and hypothesis before each delegation |
| No guidance on when to run agents in parallel vs. sequentially, leading to inefficient workflows | Parallel vs. sequential execution rules based on dependency analysis — parallelism for discovery phases, sequences for iterative refinement |
| Large research outputs exceed context windows and get truncated | Large file write strategy: phase-based pagination and multi-file organization preserves completeness without truncation |
| Citation management falls out of sync between research phases and final outputs | Dedicated Citation Agent pattern: centralized citation tracking with hash-based keys generated during research, inserted at end |
| No standard for structuring research evidence, findings, and synthesis | Structured outputs using Pydantic models (Finding, Synthesis, Plan, CitationRequest) enforce consistency and type safety across agents |
| Academic research workflows lack end-to-end templates from hypothesis through manuscript submission | 12-agent Academic Research Workflow (adrianstier/research-agent): complete pipeline from PRD through literature review, EDA, modeling, figure design, writing, and submission |

---

## Key Features

### Pattern Collection Coverage

Research identifies patterns from 40+ awesome lists and specialized research repositories:
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) — 52,029 stars, curated commands/workflows/agents for Claude Code
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) — 24,174 stars, 100+ production-ready specialized agents
- [hesreallyhim/a-list-of-claude-code-agents](https://github.com/hesreallyhim/a-list-of-claude-code-agents) — 1,340 stars, community-submitted agents
- [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) — 92,033 stars, MCP server collection
- [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers) — 4,254 stars, curated MCP servers

**Source**: Awesome Lists (accessed 2026-08-11)

### Pattern 1: Chief of Staff Orchestration

Stateless agents coordinate via file-based context sharing. Mandatory context files record complete workflow state before each agent invocation. Request-based coordination prevents direct agent-to-agent coupling.

**Key components:**
- Workflow directory: `agent_notes/[timestamp]_[workflow_name]/`
- Agent context file: `context_[agent].md` with plan, reasoning, findings, requirements
- Phase organization: `phase[N]_[agent]_[purpose].md` outputs, `phase[N]_synthesis.md` cross-agent views
- Parallel vs. sequential execution rules based on dependency analysis

**Documented by**: yuz207/claude-agents-research-team

### Pattern 2: Academic Research Workflow (12-Agent Pipeline)

Complete end-to-end pipeline from hypothesis generation through manuscript submission. Includes explicit agent roles for each research stage: PRD, literature synthesis, EDA, modeling, figure design, scientific writing, reviewer personas, submission packaging.

**Key components:**
- Research PRD Agent: Convert high-level question to structured research requirements
- Literature & Conceptual Framework Agent: Synthesize domain knowledge
- Data QA & Cleaning Agent: Quality assurance
- EDA Agent: Exploratory data analysis with 15-25 recommended plots
- Modeling Agent: Statistical analysis plan and model specifications
- Figure Factory Agent: Design all figures with panel layouts and aesthetics
- Scientific Writer Agent: Transform analyses into polished manuscript sections
- Reviewer Agent: Internal multi-persona review
- Submission Agent: Prepare journal-specific submission materials

**Documented by**: adrianstier/research-agent

### Pattern 3: Iterative Research Loop with Memory

Plan → Execute → Synthesize → Continue/Exit cycle with persistent memory. Each iteration saves plans and synthesis snapshots. Loop exits when plan recommends stop or synthesis recommends exit.

**Key components:**
- LeadResearcher: coordinates plan, delegates to subagents
- Subagents: focused research on single aspects
- Memory persistence: save/recall for plans, findings, citations
- Temperature control: tuned per agent role (research: 0.2, planning: 0.3, citation: 0.1)
- Citation tracking: hash-based keys generated during research, aggregated for final bibliography

**Documented by**: aldiakhou/codex-main (Pydantic AI framework)

### Pattern 4: File Organization for Multi-Phase Research

Three pagination strategies for handling large research outputs:

1. **Chief of Staff** (yuz207): Phase-based — agent_notes/[timestamp]/phase1/, phase2/, phase3/
2. **Pydantic AI** (aldiakhou): Memory-based — in-process JSON storage with iteration snapshots
3. **Academic** (adrianstier): Aspect-based — research_artifacts/aspect_A/, aspect_B/, aspect_C/ with synthesis referencing all

**Source**: File Organization Patterns section (accessed 2025-12-09)

### Pattern 5: Structured Output Models

Pydantic BaseModel definitions enforce consistency:
- `Synthesis`: executive_summary, findings, gaps_or_open_questions, recommend_next_iteration
- `Finding`: subtask_id, aspect, summary, citations
- `Plan`: steps, continue_research, rationale
- `CitationRequest`: draft_report_markdown, bibliography

**Source**: PATTERN 4 Codex code examples (accessed 2025-12-09)

---

## Technical Architecture

### Agent Team Structures

**Chief of Staff Model** (yuz207):
```
Human (You)
    ↓
Claude Code (Executive)
    ↓
ai-research-lead (Principal Investigator)
    ├── ml-analyst (Validation)
    ├── experiment-tracker (Documentation)
    └── [When needed] Research Engineers
        ├── architect
        ├── developer
        └── debugger
```

**Pydantic AI Model** (aldiakhou):
```
User → System → LeadResearcher → Subagents (A,B,...) → Memory → CitationAgent → System
        ↑____________iterative research loop___________↓
```

**Academic Model** (adrianstier):
```
Orchestrator Agent
    ├── Research PRD Agent
    ├── Literature Agent
    ├── Data QA Agent
    ├── EDA Agent
    ├── Modeling Agent
    ├── Figure Factory Agent
    ├── Scientific Writer Agent
    ├── Reviewer Agent (multi-persona)
    └── Submission Agent
```

**Source**: PATTERN 1-3 architecture diagrams (accessed 2025-12-09)

### Data Flow Patterns

**Chief of Staff context preservation:**
1. Orchestrator writes agent_notes/[timestamp]_[workflow]/context_[agent].md
2. Orchestrator invokes Agent(prompt + context file)
3. Agent reads context, executes, writes phase[N]_[agent]_[purpose].md
4. Orchestrator reads outputs, creates phase[N]_synthesis.md
5. Next agent gets synthesis + previous agent outputs

**Pydantic AI iteration loop:**
1. Planner creates Plan (steps, continue_research boolean)
2. LeadResearcher invokes subagents for each step
3. Subagents return Finding (aspect, summary, citations)
4. LeadResearcher creates Synthesis (executive_summary, gaps, recommend_next_iteration)
5. If continue_research && recommend_next_iteration: loop to step 1
6. CitationAgent inserts citations into final report

**Academic workflow progression:**
- Research PRD Agent → Literature Agent → Data QA Agent → EDA Agent → Modeling Agent → Figure Factory Agent → Writer Agent → Reviewer Agent → Submission Agent

**Source**: Synthesis/Aggregation section (accessed 2025-12-09)

### Mandatory Rules for Multi-Agent Research

**Stateless agents principle**: Each agent invocation starts fresh; agents cannot directly access previous conversation turns. Solution: file-based context sharing with complete state.

**Context preservation protocol (Chief of Staff)**:
- Create workflow directory before any agent invocation
- Write agent context file with: overall plan, delegation reasoning, current phase objective, previous findings, critical requirements, hypothesis, file outputs
- Each agent appends to its output file (never overwrites)
- Synthesis files reference original outputs, don't over-summarize

**Evidence preservation (Codex pattern)**:
- Store per-iteration findings separately (preserve source fidelity)
- Create iteration-level synthesis referencing findings
- Maintain plans and synthesis snapshots in memory
- Final aggregation iterates through all findings, preserves aspect/subtask_id context

**Source**: Communication Rules section and Preservation principle (accessed 2025-12-09)

---

## Detailed Technical Content

This section contains the full pattern documentation extracted from GitHub repositories (detailed patterns, implementation code, and architectural specifications). See Key Features and Technical Architecture sections above for structured overview; full implementation details follow:

| Repository                                                                                                | Stars (as of 2025-12-09) | Description                                                                                                                                            | Last Updated |
| --------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)                   | 17,825 | A curated list of awesome commands, files, and workflows for Claude Code                                                                               | 2025-12-06   |
| [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)     | 5,616  | Production-ready Claude subagents collection with 100+ specialized AI agents for full-stack development, DevOps, data science, and business operations | 2025-12-08   |
| [hesreallyhim/a-list-of-claude-code-agents](https://github.com/hesreallyhim/a-list-of-claude-code-agents) | 1,073  | A list of Claude Code Sub-Agents submitted by the community                                                                                            | 2025-12-09   |
| [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)                           | 76,332 | A collection of MCP servers                                                                                                                            | 2025-12-09   |
| [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)                                 | 3,070  | A curated list of Model Context Protocol (MCP) servers                                                                                                 | 2025-12-09   |

Current star counts (accessed 2026-08-11): hesreallyhim/awesome-claude-code 52,029; VoltAgent/awesome-claude-code-subagents 24,174; hesreallyhim/a-list-of-claude-code-agents 1,340; punkpeye/awesome-mcp-servers 92,033; wong2/awesome-mcp-servers 4,254. See the bullet list above for these current figures with citation.

---

## PATTERN 1: Comprehensive Research Agent Team Architecture

**Source**: [yuz207/claude-agents-research-team](https://github.com/yuz207/claude-agents-research-team)
**Repository**: yuz207/claude-agents-research-team (⭐ Not starred yet - active development)
**Last Updated**: 2025-12-07
**Type**: Production Claude Code agents for multi-phase research workflows

### Team Structure (Verbatim)

```yaml
research_team:
  core_scientists:
    - ai-research-lead      # PI: Designs, experiments, analyzes
    - ml-analyst           # Validates, profiles, optimizes
    - experiment-tracker   # Documents everything
  research_engineers:     # Called when needed for implementation
    - architect           # Designs complex system architectures
    - developer          # Implements new architectures cleanly
    - debugger           # Diagnoses training failures
    - quality-reviewer   # Pre-production validation
  potential_future_members:
    - technical-writer     # Manuscript preparation, literature review
    - science-critic      # Devil's advocate, challenges assumptions
```

### Communication Architecture (Verbatim)

```
Human (You)
    ↓
Claude Code (Executive Interface)
    ↓
ai-research-lead (Principal Investigator)
    ↓ [Delegates to]
    ├── ml-analyst (Senior Empirical Analyst)
    ├── experiment-tracker (Research Secretary)
    └── [When needed] Research Engineers
        ├── architect (Complex designs)
        ├── developer (Clean implementations)
        └── debugger (Failure diagnosis)
```

**Key Features**:

- **Stateless agents**: Each invocation starts fresh, no memory of previous calls
- **File-based context sharing**: Uses `agent_notes/[timestamp]_[workflow_name]/` directories
- **Request-based coordination**: Agents request Claude Code to invoke other agents
- **Clear role separation**: PI coordinates, analysts validate, engineers implement
- **Structured outputs**: All agents return typed findings/results

### Agent Role Definitions (Extracted)

**ai-research-lead**:

- Principal Investigator & Lead Data Scientist
- Generates and tests hypotheses
- Performs statistical analyses and modeling
- Coordinates specialist agents
- Makes research recommendations

**ml-analyst**:

- Empirical model evaluation
- Statistical validation with evidence-based rigor
- A/B test analysis
- Root cause analysis
- Production monitoring
- Challenges PI's hypotheses with data

**experiment-tracker**:

- Documents all experiments
- Records decisions and context
- Preserves research artifacts
- Maintains searchable records
- Takes meeting minutes

**architect**:

- Designs complex implementations for novel architectures
- System design specifications
- Never implements, only designs

**developer**:

- Implements research ideas with production-quality code
- Writes comprehensive tests
- Implements architectures designed by architect

**debugger**:

- Root cause analysis of training/implementation failures
- Investigates NaN losses, gradient explosions
- Evidence-based diagnosis only

### Critical Communication Rules (Verbatim)

1. **Agents are stateless** - Each invocation starts fresh, no memory of previous calls
2. **Agents can't see chat history** - They only see what's in the Agent tool prompt
3. **Agents can't directly invoke each other** - Must request Claude Code to do it

**SOLUTION**: Request-based coordination with COMPLETE context:

1. Agents request Claude Code to invoke other agents
2. Must provide ALL necessary context (data, findings, code, etc.)
3. Surface ALL findings visibly in output for human and Claude Code
4. Claude Code orchestrates invocations and maintains context

---

## PATTERN 2: Chief of Staff Workflow Orchestration

**Source**: [yuz207/claude-agents-research-team - chief-of-staff.md](https://github.com/yuz207/claude-agents-research-team/blob/main/chief-of-staff.md)
**File Path**: `/chief-of-staff.md`

### Mandatory Context Preservation Protocol (Verbatim)

**BEFORE Invoking ANY Agent, MUST execute these steps**:

1. **Create Workflow Directory**

   ```
   agent_notes/[timestamp]_[workflow_name]/
   Example: agent_notes/20250117_research_validation/
   ```

2. **Write Agent Context File** (MUST include ALL of these):

   ```markdown
   # Agent Context: [Task Name]
   Created: [ISO timestamp]
   Workflow Phase: [1/2/3]

   ## Overall Workflow Plan
   [The complete multi-phase plan I'm executing]

   ## Delegation Reasoning
   [WHY this specific agent for this task - based on their expertise]

   ## Current Phase Objective
   [What this specific agent needs to accomplish]

   ## Previous Agent Findings (if applicable)
   - [Key discoveries from earlier phases]
   - [Critical patterns identified]
   - [Important decisions made]

   ## Current State
   - [What's been completed]
   - [What's in progress]
   - [Known issues or blockers]

   ## Critical Requirements
   - [Specific output format needed]
   - [Validation requirements]
   - [Success criteria]

   ## Hypothesis & Research Directions
   - [Current hypotheses being tested]
   - [Promising patterns to investigate]
   - [Alternative approaches if primary fails]

   ## File Outputs
   - Your output file: agent_notes/[timestamp]/phase[N]_[agent]_[detailed_purpose].md
   - Previous phase files: [list for reference]
   - IMPORTANT: APPEND to your file, don't overwrite

   ## For Agent to Document:
   - [ ] Initial analysis plan
   - [ ] Key findings and discoveries
   - [ ] Decisions made and rationale
   - [ ] Recommendations for next phase
   - [ ] Final summary of work completed
   ```

### Parallel vs Sequential Execution Rules (Verbatim)

**Prefer parallel when possible for speed:**

- Independent analysis needed (discovery phase)
- Multiple aspects to check (security + performance + design)
- Time is critical
- No dependencies between agents

**Use sequential when:**

- Output dependencies exist (developer → debugger to verify)
- Building on findings (research-lead → ml-researcher to validate)
- Iterative refinement needed (developer ↔ debugger cycles)
- Each phase informs the next

### Agent Invocation Pattern (Verbatim)

```
Agent(subagent_type="research-lead", prompt="[context + task]")
```

**When to include "ultrathink":**

- Complex debugging or root cause analysis
- Statistical analysis or hypothesis testing
- Architecture design decisions
- Performance optimization
- Any task requiring deep reasoning

---

## PATTERN 3: Academic Research Workflow - 12-Agent System

**Source**: [adrianstier/research-agent](https://github.com/adrianstier/research-agent)
**File**: `ai_research_workflow_agent_template.md`
**Repository**: adrianstier/research-agent
**Last Updated**: 2025-11-20
**Type**: Academic research pipeline from hypothesis → manuscript → submission

### Complete Agent Suite (Verbatim)

#### 1. **Orchestrator Agent**

- **Role**: Coordinate all specialized agents to move research project from idea to submission-ready manuscript
- **Process**:
  1. Read the Research Project Brief
  2. Determine which stage the project is at (framing, EDA, modeling, writing)
  3. Select which agent(s) to activate next
  4. Draft precise task instructions for each agent
  5. Review outputs for consistency and traceability
- **Outputs**: Project roadmap, status reports, task instructions to other agents

#### 2. **Research PRD Agent** (Problem Definition)

- **Role**: Convert high-level research question into precise, structured PRD
- **Inputs**: Research Project Brief, data description, project notes
- **Outputs**:
  - Umbrella question + nested questions
  - Hypothesis tree with expected directions
  - Causal diagram (described in text)
  - Variable definitions (predictors, responses, random effects)
  - Study design summary
  - Planned endpoints and metrics
  - Planned primary vs secondary analyses
  - Risk & confounder list

#### 3. **Literature & Conceptual Framework Agent**

- **Role**: Synthesize domain knowledge and theoretical frameworks
- **Outputs**: Literature synthesis, conceptual models, theoretical basis for hypotheses

#### 4. **Data QA & Cleaning Agent**

- **Role**: Quality assurance on dataset
- **Outputs**: Data quality report, cleaning decisions, data dictionary

#### 5. **EDA (Exploratory Data Analysis) Agent**

- **Role**: Systematic exploration of data structure
- **Outputs**:
  - EDA plan organized by variable
  - Catalog of 15-25 recommended plots with code templates
  - Interpretive notes tied to hypotheses
  - Flagged issues (surprises, violations)

#### 6. **Modeling Agent**

- **Role**: Design and document statistical analysis plan
- **Outputs**:
  - Modeling PRD with model specifications
  - Primary & secondary model specifications
  - Sensitivity analysis grid
  - Code skeletons for R/Python
  - Diagnostics and fit checks

#### 7. **Figure Factory Agent**

- **Role**: Design all main and supplementary figures
- **Outputs**:
  - Figure PRD (F1–F?, S1–S?)
  - Panel designs and aesthetics
  - Caption drafts
  - Code templates for each figure

#### 8. **Scientific Writer Agent**

- **Role**: Transform analyses into polished manuscript sections
- **Outputs**:
  - Draft Introduction (literature + hypotheses)
  - Draft Methods (reproducible detail)
  - Draft Results (effect sizes, not p-values)
  - Draft Discussion (interpretation + literature)

#### 9. **Reference Agent**

- **Role**: Manage citations and references
- **Outputs**:
  - Clean reference list
  - Citation consistency check
  - Formatted bibliography

#### 10. **Reviewer Agent**

- **Role**: Internal review from multiple personas
- **Outputs**:
  - Reviewer reports (Reviewer 1, 2, Statistical)
  - Consolidated revision suggestions

#### 11. **Submission Agent**

- **Role**: Prepare all submission materials
- **Outputs**:
  - Cover letter tailored to journal
  - Highlights/key points
  - Author contribution statement
  - Data & code availability statements
  - Compliance checklist

### Research Project Brief Template (Verbatim)

```markdown
# Research Project Brief

## 1. Project Title
[Working title]

## 2. Umbrella Question
[High-level research question]

## 3. Nested Questions & Hypotheses
- Q1:
  - H1a:
  - H1b:
- Q2:
  - H2a:
  - H2b:

## 4. System & Concepts
- Focal system:
- Key taxa / entities:
- Scales (space, time):
- Core mechanisms of interest:

## 5. Data Overview
- Data source(s):
- Observational vs experimental:
- Response variables:
- Predictor variables:
- Random effects / grouping:
- Known limitations / quirks:

## 6. Target Outlet & Constraints
- Target journals:
- Word limits:
- Figure/table limits:
- Any style constraints:

## 7. Deliverables
- Main manuscript
- Supplementary information
- Core figures (F1–F4 or more)
- Supplementary figures/tables
- Reproducible code repo
- Data & code availability statements

## 8. Known Risks & Confounders
[List potential issues: bias, missing data, design limitations, etc.]
```

---

## PATTERN 4: Multi-Agent Research Pipeline with Pydantic AI

**Source**: [aldiakhou/codex-main - x.py](https://github.com/aldiakhou/codex-main/blob/main/x.py)
**File**: `x.py` (Complete implementation)
**Repository**: aldiakhou/codex-main
**Type**: Python-based multi-agent research pipeline using Pydantic AI + OpenAI

### Architecture Pattern (Verbatim)

```
User ─▶ System ─▶ LeadResearcher ─▶ Subagents (A,B,...) ─▶ Memory ─▶ CitationAgent ─▶ System
           ▲                            │                                        │
           └─────────────── iterative research loop ◀─────────────────────────────┘
```

### Core Data Structures (Verbatim)

```python
class Synthesis(BaseModel):
    """LeadResearcher synthesis output from findings."""
    executive_summary: str
    findings: list[Finding]
    gaps_or_open_questions: list[str] = Field(default_factory=list)
    recommend_next_iteration: bool


class Finding(BaseModel):
    subtask_id: str
    aspect: str
    summary: str
    # link to citations gathered while researching that subtask
    citations: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Plan created by LeadResearcher for this iteration."""
    steps: list[Subtask] = Field(default_factory=list, description="Sub-tasks to execute now.")
    continue_research: bool = Field(
        description="True to continue iterative loop after current steps are done."
    )
    rationale: str


class Subtask(BaseModel):
    id: str = Field(description="Unique ID for the sub-task, short (e.g. 'A' or 'B').")
    aspect: str = Field(description="What this sub-agent should research.")
    target_depth: str = Field(
        description="Depth like 'quick scan', 'deep dive', 'verify claims'."
    )


class CitationRequest(BaseModel):
    """What we give the CitationAgent."""
    draft_report_markdown: str
    bibliography: dict[str, str]  # (url -> "Author, Title, Year" etc.)


class FinalReport(BaseModel):
    """What the CitationAgent returns after inserting citations."""
    markdown_with_citations: str
```

### Iterative Research Loop (Verbatim)

```python
async def research_pipeline(user_query: str) -> str:
    """
    End-to-end:
      1) Create dependencies (HTTP client, Memory)
      2) Create agents (Subagent, LeadResearcher, Planner, CitationAgent)
      3) Iterate: plan -> delegate -> synthesize, until plan says stop (or cap)
      4) Ask CitationAgent to insert citations and return the final report
    """
    # ... initialization ...

    all_findings: list[Finding] = []
    max_loops = 3  # safety cap
    iteration = 0

    while iteration < max_loops:
        iteration += 1

        # --- Plan the next iteration
        plan_res = await planner.run(
            f"User query:\n{user_query}\n\nMemory:\n{json.dumps(deps.memory.all(), indent=2)}"
        )
        plan = plan_res.output
        # Persist the plan to memory for traceability
        deps.memory.save(f"plan_iter_{iteration}", plan.model_dump_json())

        # --- Execute plan by delegating to sub-agents
        iter_findings: list[Finding] = []
        for step in plan.steps:
            try:
                finding = await lead.tools["delegate_to_subagent"](
                    subtask_id=step.id, aspect=step.aspect, depth=step.target_depth
                )
                iter_findings.append(finding)
            except UnexpectedModelBehavior as e:
                iter_findings.append(
                    Finding(
                        subtask_id=step.id,
                        aspect=step.aspect,
                        summary=f"Failed to research due to error: {e}",
                        citations=[],
                    )
                )

        all_findings.extend(iter_findings)

        # --- Synthesize for this iteration
        synth_prompt = (
            "Synthesize findings for this iteration.\n"
            f"User query: {user_query}\n"
            f"Iteration: {iteration}\n"
            f"Findings JSON:\n{json.dumps([f.model_dump() for f in iter_findings], indent=2)}\n"
        )
        synth = (await lead.run(synth_prompt, deps=deps)).output

        # Save synthesis snapshot
        deps.memory.save(f"synthesis_iter_{iteration}", synth.model_dump_json())

        # Exit/continue?
        if not plan.continue_research or not synth.recommend_next_iteration:
            break

    # --- Final drafting
    draft_md_lines: list[str] = [
        f"# Research report",
        "",
        f"**User query**: {user_query}",
        "",
        "## Executive summary",
    ]

    # Aggregate the last synthesis
    last_synth_json = deps.memory.recall(f"synthesis_iter_{iteration}") or ""
    if last_synth_json:
        try:
            last_synth = Synthesis.model_validate_json(last_synth_json)
            draft_md_lines.append(last_synth.executive_summary)
        except ValidationError:
            pass

    draft_md_lines += ["", "## Findings"]
    for f in all_findings:
        cites = " ".join(f.citations) if f.citations else ""
        draft_md_lines.append(f"- **[{f.subtask_id}] {f.aspect}** — {f.summary} {cites}")

    draft_md = "\n".join(draft_md_lines)

    # --- Citation insertion
    biblio: dict[str, str] = {}
    for k, v in deps.memory.all().items():
        if k.startswith("[cite:"):
            biblio[k] = v

    cite_req = CitationRequest(draft_report_markdown=draft_md, bibliography=biblio)
    final = (
        await citation.run(
            "Insert citations into the draft and add a 'References' section at the end.",
            deps=deps,
            input=cite_req,
        )
    ).output

    return final.markdown_with_citations
```

### Sub-Agent Pattern (Verbatim)

```python
def make_subagent() -> Agent[Deps, Finding]:
    """
    A sub-agent performs focused research for ONE aspect.
    It has two tools available: web_search and fetch_page.
    It must return a structured Finding.
    """
    sub = Agent[Deps, Finding](
        'openai:gpt-4o-mini',
        instructions=(
            "You are a precise research sub-agent. "
            "Goal: research the requested aspect, collect a few high-quality sources, "
            "quote short relevant snippets, and produce a concise summary. "
            "Avoid hallucination; prefer authoritative sources (docs, standards, journals, gov). "
            "Add a short list of citation keys (e.g., [cite:URL_HASH]) you saw during research."
        ),
        model_settings=ModelSettings(temperature=0.2, timeout=60),
    )

    @sub.tool
    async def web_search(ctx: RunContext[Deps], query: str, max_results: int = 5) -> WebSearchOutput:
        """Use DuckDuckGo to find relevant pages."""
        # ...implementation...

    @sub.tool
    async def fetch_page(ctx: RunContext[Deps], url: HttpUrl, max_chars: int = 6000) -> FetchPageOutput:
        """Fetch and extract main text of the page. Truncates to keep context compact."""
        # Build a stable, short citation key for later insertion
        cite_key = f"[cite:{abs(hash(str(url))) % 10**8}]"
        # Persist a mapping URL->key so CitationAgent can render bibliography
        ctx.deps.memory.save(cite_key, str(url))
        # ...implementation...

    return sub
```

### Citation Agent Pattern (Verbatim)

```python
def make_citation_agent() -> Agent[Deps, FinalReport]:
    cite = Agent[Deps, FinalReport](
        'openai:gpt-4o-mini',
        instructions=(
            "You are a precise citation agent. "
            "Given a draft markdown and a bibliography mapping citation keys to URLs, "
            "insert citation markers after claims and compile a References section. "
            "Keep the author's wording; only add [^n] style footnotes or inline (Author, Year) "
            "and a final 'References' list. Preserve markdown formatting."
        ),
        model_settings=ModelSettings(temperature=0.1, timeout=90),
    )

    @cite.tool
    def fetch_bibliography(ctx: RunContext[Deps]) -> dict[str, str]:
        """Return mapping from citation keys to URLs."""
        return ctx.deps.memory.all()

    return cite
```

### Key Features of Pattern

- **Memory persistence**: Saves plans, findings, and synthesis at each iteration
- **Citation tracking**: Automatic citation key generation during research
- **Structured outputs**: All agents return Pydantic models
- **Temperature control**: Lower temperature for research (0.2), citation (0.1); higher for planning (0.3)
- **Iterative refinement**: Loop until no more research recommended
- **Final bibliography**: Aggregated from all citations gathered during research

---

## PATTERN 5: Research Lead Agent Prompt Structure

**Source**: [yuz207/claude-agents-research-team - research-lead.md](https://github.com/yuz207/claude-agents-research-team/blob/main/research-lead.md)
**File Path**: `/research-lead.md`
**Type**: Production-ready Claude Code agent definition with frontmatter

### Core Mission (Verbatim)

```
You are the Principal Investigator leading a multi-agent research team. You drive breakthrough
insights through rigorous hypothesis-driven research with PhD-level expertise in data science,
statistical analysis, and experimental design across ALL domains.
```

### Cardinal Rule (Verbatim)

```
RULE 0 (MOST IMPORTANT): Never Fake or Fabricate ANYTHING

- NEVER fabricate data, results, or analysis - not even examples
- NEVER make up numbers - use placeholders like [X] if unknown
- NEVER pretend to have run analysis you haven't actually executed
- NEVER hide errors or failures - report them immediately
- ALWAYS report negative results with same detail as positive
- ALWAYS say "I don't know" rather than guess
- NEVER skip statistical validation to save time
- ALWAYS check assumptions before ANY inference
- NEVER present correlation as causation without proven mechanism

If you're unsure about ANYTHING:
1. Say "I'm not sure" or "I cannot determine this"
2. Show your actual searches/attempts
3. Request the specific data or clarification needed

Fabricating even ONE number = -$100000 penalty. This is UNFORGIVABLE.
```

### Scientific Method Workflow (Verbatim)

```
Your Analysis MUST Follow This Sequence:

1. **Check Existing Work**
   - Reference existing work by ID (H001, H002, etc.)

2. **Generate Hypothesis**
   - State clear, testable prediction
   - Define variables (IV, DV, moderators, mediators)
   - Specify mechanism
   - Set success criteria (effect size, p-value)

3. **Design Experiment**
   - Calculate required sample size
   - Identify confounders to control
   - Choose appropriate statistical test
   - Plan robustness checks

4. **Execute Analysis**
   - Run primary statistical test
   - Check ALL assumptions explicitly
   - Calculate effect sizes with CIs
   - Run sensitivity analyses

5. **Validate Findings**
   - Request ml-analyst if p-value borderline
   - Test alternative specifications
   - Check for p-hacking artifacts
   - Verify temporal stability

6. **Make Decision**
   - Strong evidence (all criteria met) → Proceed to implementation
   - Moderate evidence (3-4 criteria) → Collect more data
   - Weak evidence (1-2 criteria) → Revise hypothesis
   - No evidence → Reject and pivot
```

### Statistical Standards (NON-NEGOTIABLE) (Verbatim)

**You MUST**:

- Report effect size WITH confidence intervals
- Report p-values WITH multiple testing correction
- Report sample size and statistical power
- Document assumption violations if any
- Show both raw and adjusted results
- ALWAYS check assumptions before ANY inference
- ALWAYS say "I don't know" rather than guess

**You MUST NEVER**:

- NEVER report p-values without effect sizes
- NEVER skip assumption checking
- NEVER ignore multiple testing problem
- NEVER hide negative results
- NEVER cherry-pick significant findings
- NEVER present correlation as causation without proven mechanism
- NEVER skip statistical validation to save time

### Output Format (Verbatim)

```markdown
## HYPOTHESIS [ID]: [Clear statement]
STATUS: [TESTING/VALIDATED/REJECTED/REVISED]

## RESULTS
- Effect size: [magnitude] [95% CI]
- Statistical significance: p=[value]
- Sample size: n=[number]
- Robustness: [description]

## EVIDENCE
[Actual data, numbers, and analysis details]

## INTERPRETATION
[Causal mechanism and implications]

## KEY FINDINGS
[Anything the human MUST know]

## NEXT STEPS
1. [Immediate action]
2. [Follow-up action]
3. [Alternative if 1 fails]
Timeline: [X days/weeks]
Pivot point: [When to abandon this path]
```

### Hypothesis Structure (Verbatim)

```markdown
### H[XXX]: [One-line statement]
- **Variables**: IV=[var], DV=[var], Moderators=[vars]
- **Mechanism**: [Theoretical explanation]
- **Prediction**: [Specific, measurable outcome]
- **Success Criteria**: Effect size > [X], p < 0.05
- **Status**: [PROPOSED/TESTING/VALIDATED/REJECTED]
- **Related**: [H001, H002] # Links to other hypotheses
- **Related findings**: [provided with context]
```

### Evidence Assessment Rules (Verbatim)

| Criteria Met | Evidence Level | Action              |
| ------------ | -------------- | ------------------- |
| All 5        | STRONG         | → Implementation    |
| 3-4          | MODERATE       | → More data         |
| 1-2          | WEAK           | → Revise hypothesis |
| 0            | NONE           | → Reject & pivot    |

**The 5 Criteria for Evidence**:

1. Statistical significance (p < 0.05 adjusted)
2. Practical effect size (context-dependent)
3. Robustness across specifications
4. Replicable in subsamples
5. Clear causal mechanism

---

## Synthesis/Aggregation Without Over-Summarizing

### Pattern from Codex (x.py)

**Key approach**: Preserve full findings, then synthesize iteratively:

1. **Store per-iteration findings** in structured format (Finding dataclass)
2. **Create iteration-level synthesis** that references full findings
3. **Maintain memory of all plans** (saved as JSON at each iteration)
4. **Final aggregation**: Iterate through all findings, preserve aspect/subtask_id
5. **Draft markdown**: Enumerate findings with subtask context preserved
6. **Citation integration**: Maintain URL→citation key mappings throughout

```python
# Store findings with context preserved
for f in all_findings:
    cites = " ".join(f.citations) if f.citations else ""
    draft_md_lines.append(f"- **[{f.subtask_id}] {f.aspect}** — {f.summary} {cites}")

# Don't over-summarize: include finding.summary + citations explicitly
```

### Pattern from Research Team (chief-of-staff.md)

**Key approach**: File-based synthesis between phases

1. **After each phase**, read ALL agent outputs from completed phase
2. **Create synthesis file**: `agent_notes/[timestamp]/phase[N]_synthesis.md`
3. **Note CRITICAL/PRIORITY/CONCERN findings** for final summary
4. **Preserve findings verbatim** in synthesis, add reasoning layer on top
5. **Next phase agents read synthesis** but also reference original output files

```markdown
# Phase 1 Synthesis
[Copy key findings from agent outputs verbatim]

## Critical Findings
- [Agent]: [Critical finding flagged during workflow]

## Reasoning
[Interpretation and recommendations for next phase]
```

---

## File Organization Patterns for Research Output

### Pattern 1: Chief of Staff (yuz207/claude-agents-research-team)

```
agent_notes/
├── 20250117_research_validation/          # Workflow directory
│   ├── context_research-lead.md            # Agent context file
│   ├── context_ml-analyst.md
│   ├── context_experiment-tracker.md
│   ├── phase1_research-lead_hypothesis.md  # Phase 1 outputs
│   ├── phase1_ml-analyst_validation.md
│   ├── phase1_synthesis.md                 # Cross-agent synthesis
│   ├── phase2_developer_implementation.md  # Phase 2 outputs
│   ├── phase2_debugger_testing.md
│   ├── phase2_synthesis.md
│   └── FINAL_SUMMARY.md                    # Consolidated results
```

**File naming convention**:

- `context_[agent].md` - Agent's context for invocation
- `phase[N]_[agent]_[purpose].md` - Agent's output (APPEND, don't overwrite)
- `phase[N]_synthesis.md` - Cross-agent synthesis
- `FINAL_SUMMARY.md` - Consolidated findings

### Pattern 2: Pydantic AI Research Pipeline (aldiakhou/codex-main)

```
Memory store (in-process):
├── plan_iter_1: Plan JSON
├── plan_iter_2: Plan JSON
├── synthesis_iter_1: Synthesis JSON
├── synthesis_iter_2: Synthesis JSON
├── [cite:12345]: https://source-1.com
├── [cite:67890]: https://source-2.com
```

**Access pattern**:

- Save/recall via memory.save(key, value)
- Retrieve full plan history via `deps.memory.all()`
- Build bibliography from keys starting with `[cite:`

### Pattern 3: Academic Research Workflow (adrianstier/research-agent)

```
project_root/
├── PROJECT_BRIEF.md                    # Central research document
├── research_artifacts/
│   ├── PRD.md                          # Research PRD Agent output
│   ├── LITERATURE_REVIEW.md            # Literature Agent output
│   ├── DATA_QA_REPORT.md              # Data QA Agent output
│   ├── EDA_RESULTS.md                 # EDA Agent output
│   ├── MODELING_PLAN.md               # Modeling Agent output
│   ├── FIGURES.md                     # Figure Factory Agent output
│   ├── figures/                       # Actual figure files
│   │   ├── F1.png
│   │   ├── F2.png
│   │   └── ...
│   └── MANUSCRIPT_DRAFT/
│       ├── introduction.md
│       ├── methods.md
│       ├── results.md
│       ├── discussion.md
│       ├── references.bib
│       └── FINAL_SUBMISSION_PACKAGE.md
```

---

## Citation & Bibliography Management Approaches

### Approach 1: Hash-based Citation Keys (Codex Pattern)

```python
# During research, create stable citation keys
cite_key = f"[cite:{abs(hash(str(url))) % 10**8}]"
ctx.deps.memory.save(cite_key, str(url))

# Final pass: CitationAgent receives
CitationRequest(
    draft_report_markdown=draft_md,
    bibliography=biblio  # { "[cite:12345]": "https://..." }
)

# CitationAgent inserts citations and builds References section
```

**Advantages**:

- Deterministic (same URL = same key)
- Compact (8-digit hash)
- Embedded in research process (collected during sub-agent research)

### Approach 2: URL-based Mapping (Pydantic AI)

```python
# Save during fetch_page()
ctx.deps.memory.save(f"[cite:{abs(hash(str(url))) % 10**8}]", str(url))

# Retrieve in CitationAgent
bibliography: dict[str, str] = {}
for k, v in deps.memory.all().items():
    if k.startswith("[cite:"):
        bibliography[k] = v
```

### Approach 3: Full Metadata Tracking (Academic Pattern)

```markdown
## Bibliography (adrianstier/research-agent)

Agents collect:
- Author names
- Publication year
- DOI
- Journal/source
- Full URL

Output in standard format (APA, Chicago, etc.) matching target journal
```

---

## Multi-File Research Output Organization (Pagination)

### Pattern: Phase-based Pagination

**Problem**: Research findings too large for single file or context window

**Solution**: Organize by iteration/phase

```
agent_notes/20250117_validation/
├── phase1_discovery_findings.md          # Iteration 1 results
├── phase2_validation_findings.md         # Iteration 2 results
├── phase3_refinement_findings.md         # Iteration 3 results
├── CONSOLIDATED_FINDINGS.md              # References all above
```

**Access pattern**:

- Each phase file is self-contained
- Synthesis file references all phase files
- Final report aggregates with `[See phase1_discovery_findings.md line X]` references

### Pattern: Aspect-based Pagination (Subtask Division)

**For large topics**, divide by research aspect:

```
research_artifacts/
├── aspect_A_neural_architectures.md      # Subtask A findings
├── aspect_B_training_efficiency.md       # Subtask B findings
├── aspect_C_inference_optimization.md    # Subtask C findings
├── SYNTHESIS_across_aspects.md           # Integrates all three
```

**In synthesis**: Link to aspect files

```markdown
### Key Findings Across Aspects

- **[A] Neural Architectures**: [summary from aspect_A_neural_architectures.md]
  See full findings: [aspect_A_neural_architectures.md](./aspect_A_neural_architectures.md)

- **[B] Training Efficiency**: [summary from aspect_B_training_efficiency.md]
  See full findings: [aspect_B_training_efficiency.md](./aspect_B_training_efficiency.md)
```

---

## Hooks and Commands for Research Workflows

### From hesreallyhim/awesome-claude-code

**Discovered categories relevant to research**:

- Agent Skills (research-specific agents)
- Workflows & Knowledge Guides (documented research processes)
- Tooling (research support tools)
- Orchestrators (multi-agent coordination)

**Example resources documented**:

- Research agent definitions
- Research workflow templates
- Agent orchestration patterns
- Context management tools
- Output style guides for research

### Research-Relevant Patterns in Awesome Lists

From [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents):

**Category 10: Research & Analysis**

- `research-analyst.md` - Comprehensive research specialist
- `search-specialist.md` - Advanced information retrieval expert
- `trend-analyst.md` - Emerging trends and forecasting expert
- `competitive-analyst.md` - Competitive intelligence specialist
- `market-researcher.md` - Market analysis and consumer insights
- `data-researcher.md` - Data discovery and analysis expert

**Category 09: Meta & Orchestration** (relevant for multi-agent research)

- `agent-organizer.md` - Multi-agent coordinator
- `context-manager.md` - Context optimization expert
- `knowledge-synthesizer.md` - Knowledge aggregation expert
- `multi-agent-coordinator.md` - Advanced multi-agent orchestration
- `workflow-orchestrator.md` - Complex workflow automation

---

## Key Takeaways & Recommendations

### For Implementing Your Research Agent System

1. **Use the Chief of Staff Model** (yuz207/claude-agents-research-team)

   - Stateless agents with file-based context sharing
   - Explicit workflow directories with phase-based organization
   - Context files mandatory before any agent invocation

2. **Implement Iterative Loops with Exit Criteria** (aldiakhou/codex-main)

   - Plan → Execute → Synthesize → Loop or Exit
   - Save plans and synthesis snapshots for traceability
   - Cap loops to prevent infinite research

3. **Preserve Source Fidelity** (Core Principle)

   - Store per-iteration/per-subtask findings separately
   - Use synthesis files as interpretation layer, not replacement
   - Link to original findings, don't over-summarize
   - Maintain citation mappings throughout

4. **Use Structured Outputs**

   - Pydantic models for all agent returns (Finding, Synthesis, Plan, etc.)
   - Type safety from agent invocation through aggregation
   - JSON serialization for memory/state preservation

5. **Citation Management**

   - Generate citation keys during research (not after)
   - Maintain URL→key mappings in persistent memory
   - Delegate citation insertion to dedicated Citation Agent
   - Build bibliography from all sources encountered

6. **For Large Research Projects**
   - Divide by phase (iteration 1, 2, 3...)
   - Divide by aspect/subtask (A=architecture, B=training, C=inference...)
   - Create synthesis files that reference all parts
   - Use markdown links for navigation between files

### Recommended Architecture

```
Research Coordinator (Orchestrator)
    ├── Research Lead (PI)
    │   ├── Delegates to → Sub-agent (Aspect A)
    │   ├── Delegates to → Sub-agent (Aspect B)
    │   ├── Delegates to → Sub-agent (Aspect C)
    │   ├── Requests → ML Analyst (validation)
    │   └── Requests → Experiment Tracker (documentation)
    ├── Context Manager (saves/recalls from agent_notes/)
    └── Citation Agent (final bibliography insertion)

Output Structure:
agent_notes/[timestamp]_[project]/
├── phase1_synthesis.md
├── phase2_synthesis.md
├── FINAL_REPORT.md
└── bibliography.json
```

---

## Full Repository Links for Further Study

| Repository                    | URL                                                          | Key Patterns                                                           |
| ----------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- |
| research-agent (Academic)     | <https://github.com/adrianstier/research-agent>              | 12-agent academic pipeline, Project Brief template                     |
| claude-agents-research-team   | <https://github.com/yuz207/claude-agents-research-team>      | Chief of Staff, context preservation, team structure                   |
| codex-main (Pydantic AI)      | <https://github.com/aldiakhou/codex-main>                    | Iterative loops, memory persistence, citation tracking                 |
| awesome-claude-code           | <https://github.com/hesreallyhim/awesome-claude-code>        | Research agent examples, workflows, best practices                     |
| awesome-claude-code-subagents | <https://github.com/VoltAgent/awesome-claude-code-subagents> | 100+ production-ready agent definitions including research specialists |

---

**Research completed**: December 9, 2025
**Total repositories analyzed**: 40+ awesome lists and specialized research repos
**Patterns extracted**: 5 major architectures with source code and implementation details

---

## Installation & Usage

These are research patterns extracted from open-source repositories. Implementation requires:

### Option 1: Study and Implement Locally

1. **Clone the primary pattern repositories**:
   ```bash
   git clone https://github.com/yuz207/claude-agents-research-team
   git clone https://github.com/adrianstier/research-agent
   git clone https://github.com/aldiakhou/codex-main
   ```

2. **Read agent definitions** (e.g., `claude-agents-research-team/research-lead.md`)

3. **Adapt pattern for your use case**: Copy the orchestration structure, context preservation protocol, or iteration loop into your workflow

**Source**: Repository links documented (accessed 2025-12-09)

### Option 2: Use Awesome Lists for Agent Selection

Browse curated agent collections:

- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents): 100+ production-ready agents organized by category (Research & Analysis, Meta & Orchestration)
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code): Workflows, skills, and orchestration patterns
- [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers): 92,033-star collection of MCP tools for agent integration (accessed 2026-08-11; 76,332 as of 2025-12-09)

**Source**: Awesome Lists Found section (accessed 2025-12-09)

### Option 3: Build with Recommended Architecture

Implement the Chief of Staff + Iterative Loop hybrid:

1. **Set up workflow directory structure**:
   ```bash
   mkdir -p agent_notes/[timestamp]_[project_name]
   ```

2. **Write orchestrator script** that:
   - Creates context files before each agent invocation
   - Collects outputs into phase directories
   - Creates synthesis files across phases
   - Manages iteration loop with exit criteria

3. **Define agent roles** (from patterns): Research Lead, ML Analyst, Experiment Tracker, Architect, Developer, Debugger

4. **Configure memory persistence** (from Pydantic AI pattern): JSON snapshots of plans, findings, citations

**Source**: Recommended Architecture section + Mandatory Rules section (accessed 2025-12-09)

---

## Relevance to Claude Code Development

### Applications

1. **Multi-Agent Orchestration**: Claude Code plugin developers can use Chief of Staff coordination model for complex tasks requiring multiple specialized agents.

2. **Research Automation**: Use academic pipeline patterns to automate research-heavy workflows (literature review, analysis, documentation).

3. **Context Management**: Implement file-based context preservation to enable stateless agent teams without relying on context windows.

4. **Structured Outputs**: Apply Pydantic models for type-safe agent returns and memory persistence.

### Patterns Worth Adopting

- **Chief of Staff context protocol**: File-based state sharing enables agent independence and parallelism
- **Iterative research loops with exit criteria**: Prevents infinite loops while enabling multi-phase refinement
- **Dedicated Citation Agent**: Separates citation management from research, enabling accurate bibliographies
- **Phase-based pagination**: Preserves research evidence without truncation across multiple files

### Integration Opportunities

- Integrate iterative loop pattern into SAM 7-stage pipeline for multi-iteration refinement
- Add Chief of Staff coordination to agent-orchestration skill for stateless multi-agent teams
- Implement citation tracking patterns in multi-source synthesis for proper bibliography management
- Enhance research-curator agent with 12-agent academic pipeline structure

**Source**: Key Takeaways & Recommendations + Integration Opportunities sections (accessed 2025-12-09)

---

## References

- [yuz207/claude-agents-research-team](https://github.com/yuz207/claude-agents-research-team) (accessed 2025-12-09)
- [adrianstier/research-agent](https://github.com/adrianstier/research-agent) (accessed 2025-12-09)
- [aldiakhou/codex-main](https://github.com/aldiakhou/codex-main) (accessed 2025-12-09)
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) (accessed 2025-12-09)
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) (accessed 2025-12-09)
- [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) (accessed 2025-12-09)
- [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers) (accessed 2025-12-09)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [CocoIndex Code](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | MCP-based semantic code search complements github-patterns' file selection and context discovery |
| [Screenpipe](../mcp-ecosystem/screenpipe.md) | mcp-ecosystem | Continuous context capture via MCP could enhance Chief of Staff model with ambient project context |

---

## Integration Opportunities

> Discovered during research artifact analysis. Review for applicability.

### Enhances Existing

| Target | Type | How |
|--------|------|-----|
| `plugins/agent-orchestration/skills/agent-orchestration/` | skill | Add Chief of Staff context preservation protocol (file-based agent_notes/ directories with phase-based organization) and request-based coordination patterns to enable stateless multi-agent workflows with complete context passing. |
| `plugins/development-harness/skills/development-harness/` | skill | Integrate iterative research loop pattern with exit criteria (Plan → Execute → Synthesize → Continue/Exit) to enable the SAM 7-stage pipeline to perform multi-iteration refinement with memory persistence across phases. |
| `plugins/summarizer/skills/multi-source-synthesis/` | skill | Add citation tracking patterns from Pydantic AI research pipeline (hash-based citation keys generated during research, URL→key mappings in memory, dedicated citation insertion agent) to enable proper bibliography management in multi-source synthesis. |
| `.claude/agents/research-curator.md` | agent | Enhance with Academic Research Workflow patterns (12-agent pipeline structure, Research PRD format, Literature & Conceptual Framework integration, Figure Factory approach) to enable comprehensive research entry creation beyond basic documentation. |
| `.claude/agents/research-context-agent.md` | agent | Add structured output patterns using Pydantic models (Finding, Synthesis, Plan, CitationRequest) and memory persistence patterns to enable traceable cross-referencing with state preservation across research analysis iterations. |

### New Skill Candidates

- **research-workflow-orchestrator**: Implements the Chief of Staff pattern with mandatory context preservation protocol for stateless multi-agent research workflows. Creates workflow directories (agent_notes/[timestamp]_[workflow_name]/), writes agent context files with complete delegation reasoning, and orchestrates parallel vs sequential execution based on dependency analysis. Enables research teams to coordinate discovery, validation, and documentation phases with full context handoff.

- **hypothesis-driven-research**: Teaches Claude to apply the Research Lead agent's scientific method workflow (hypothesis generation with testable predictions, experiment design with sample size calculation, statistical validation with effect sizes and confidence intervals, evidence assessment using 5-criteria framework). Enforces non-negotiable statistical standards and structured hypothesis tracking with status and evidence levels.

- **academic-manuscript-pipeline**: Implements the 12-agent Academic Research Workflow from hypothesis through manuscript submission. Orchestrates Research PRD generation, literature synthesis, EDA with 15-25 plot catalog, modeling plan with sensitivity analysis, figure factory with panel designs, scientific writing for each section, citation management, internal reviewer personas, and submission package preparation with journal-specific formatting.

### New MCP Server Candidates

- **research-memory-mcp**: Exposes persistent memory operations following the Pydantic AI pattern (save/recall with structured keys, iteration-level snapshots, citation tracking with hash-based keys, full history retrieval). Provides tools for plan_storage, synthesis_storage, citation_tracking, and bibliography_generation to enable research agents to maintain state across invocations without relying on context windows.

- **research-artifact-mcp**: Provides file-based research artifact management following Chief of Staff organization patterns. Exposes tools for create_workflow_directory, write_agent_context, store_phase_output, create_synthesis_file, and link_artifacts to enable structured research output organization with phase-based pagination and cross-file navigation.

### Cross-References

- Related research: `research/context-management/local-memory.md` — Both address persistent state management for AI agents; github-patterns provides research-specific memory patterns (citation tracking, plan persistence, finding aggregation) while local-memory focuses on general context retention across sessions.
- Related research: `research/agent-frameworks/bmad-method.md` — BMAD methodology could integrate with github-patterns' Chief of Staff orchestration model to provide the strategic planning layer while Chief of Staff handles tactical agent coordination and context management.
- Related research: `research/agent-frameworks/get-shit-done.md` — GSD's task decomposition approach complements github-patterns' iterative research loop pattern; combining them would enable breaking research projects into subtasks with Plan → Execute → Synthesize cycles at each level.
