---
name: groom-backlog-item
description: Groom backlog items — trigger /groom-backlog-item <title|section|all> — fact-checks item claims against primary sources, runs RT-ICA per item, then spawns @backlog-item-groomer agents. Writes groomed content into per-item files in .claude/backlog/. Use when preparing backlog items for planning or execution.
argument-hint: <item-title-or-section-or-all>
user-invocable: true
---

<groom_scope>$ARGUMENTS</groom_scope>

# Groom Backlog Item

Orchestrate autonomous backlog refinement: verify claims, clarify scope, estimate effort, map resources and dependencies, and clean stale items — making each item ready for the planning phase.

**Scope boundary**: Grooming answers "what needs to be done, is the problem clear, and what do we have to work with?" It does NOT answer "how should it be built." Architecture, task decomposition, and implementation design happen in the SAM planning phase (`/work-backlog-item` Step 6). Grooming produces a DEEP item (Detailed appropriately, Estimated, Emergent, Prioritized) — not a plan. The human provides direction and priorities; the agent does the research, fact-checking, and resource mapping autonomously.

## Arguments

`<groom_scope/>` accepts:

- **Title substring** — e.g., `Error Recovery` — grooms matching item (case-insensitive)
- **Section** — `P0`, `P1`, `P2`, or `Ideas` — grooms all items in that section
- **`all`** — grooms all items across P0, P1, P2, Ideas (parallel agents)

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

## Workflow

The following diagram is the authoritative procedure for overall groom-backlog-item workflow. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Start(["/groom-backlog-item called with scope argument"]) --> S1["Step 1 — Call backlog_list MCP tool<br>and filter items by scope argument"]
    S1 --> S2["Step 2 — Validity Check<br>Run 4 pre-groom checks per item"]
    S2 --> S2Out{"Item passed all<br>validity checks?"}
    S2Out -->|"Checks 1–3 failed — invalid, done, or stale"| SkipReport(["Report to user and skip this item"])
    S2Out -->|"Checks 1–3 pass AND already groomed today"| PlanCheck{"Item has<br>plan file?"}
    PlanCheck -->|"Yes — plan field set"| S25["Step 2.5 — Plan Drift Check (Mode A)<br>Spawn haiku agent to detect codebase<br>changes since plan was written"]
    PlanCheck -->|"No plan file"| S25B["Step 2.5 — Grooming Drift Check (Mode B)<br>Spawn haiku agent to detect codebase<br>changes since item was groomed"]
    S25 --> DriftDone(["Report drift findings to user — stop"])
    S25B --> DriftDone
    S2Out -->|"Checks 1–3 pass, not groomed today"| S3["Step 3 — Extract item details<br>title, description, research questions, source, suggested_location"]
    S3 --> S35["Step 3.5 — RT-ICA Initial Snapshot<br>Assess AVAILABLE / DERIVABLE / MISSING<br>Write snapshot via backlog_groom"]
    S35 --> S36["Step 3.6 — Scope Sizing<br>Choose MINIMAL / NARROW / STANDARD / FULL<br>based on RT-ICA snapshot and issue type"]
    S36 --> S48["Steps 4–8 — Parallel Grooming Swarm<br>Run agents sized by Step 3.6"]
    S48 --> S85["Step 8.5 — RT-ICA Final Pass<br>Re-assess all conditions with full swarm output<br>Replace snapshot in item"]
    S85 --> FinalDecision{"RT-ICA Final<br>Decision?"}
    FinalDecision -->|"BLOCKED — MISSING conditions remain"| BlockedStop(["STOP — present missing inputs to user<br>Do not proceed to Step 9"])
    FinalDecision -->|"APPROVED — all conditions resolved"| S9["Step 9 — Write groomed content<br>to item files via MCP tools"]
    S9 --> Done(["Item fully groomed and synced"])
```

### Step 1: Parse Arguments and Load Backlog

Call `mcp__backlog__backlog_list()` and filter the returned dict's `items` list by argument type above.

### Step 2: Validity Check (Pre-Groom Gate)

The following diagram is the authoritative procedure for the Step 2 validity check. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    ItemIn(["Item selected for grooming"]) --> C1{"Is the job still valid?<br>Does this item still belong<br>in the backlog given current context?"}
    C1 -->|"No — scope, priority, or context changed"| InvalidSkip(["Report invalid — skip grooming for this item"])
    C1 -->|"Yes — item is still relevant"| C2{"Search for evidence work is already done<br>git log --grep keyword + gh pr list merged<br>+ read files at suggested_location<br>Does evidence of completion exist?"}
    C2 -->|"Yes — evidence found"| AlreadyDone["Comment evidence on GitHub issue (if exists)<br>gh issue comment N --body 'Completed via PR'<br>Close GitHub issue: gh issue close N --reason completed<br>Call backlog_resolve with PR/SHA summary"]
    AlreadyDone --> DoneSkip(["Report to user — skip grooming for this item"])
    C2 -->|"No evidence of completion found"| C3{"Does item have a GitHub issue?<br>Check metadata.issue or index link #N"}
    C3 -->|"No GitHub issue"| C4Check{"Check item file's 'groomed' frontmatter field<br>Does groomed == today's date AND<br>item has all required sections?"}
    C3 -->|"Yes — call backlog_view selector='#N'<br>Check 'state' field in returned dict"| IssueState{"state field<br>value?"}
    IssueState -->|"open"| C4Check
    IssueState -->|"closed — local file is stale"| StaleSearch["Search for commits: git log --grep='#N'<br>Search merged PRs: gh pr list --search '#N' --state merged"]
    StaleSearch --> StaleEvidence{"Commits or PRs<br>reference this issue?"}
    StaleEvidence -->|"Yes — evidence found"| StaleClose["Comment evidence on issue<br>Call backlog_resolve with PR/SHA summary"]
    StaleClose --> StaleSkip(["Skip grooming — move to next item"])
    StaleEvidence -->|"No evidence found"| StaleReport(["Report: issue #N closed but no commit/PR found<br>Recommend manual review — skip grooming"])
    C4Check -->|"Yes — already groomed today"| PlanFileCheck{"Does item have<br>a plan file?<br>Check plan field in backlog_list JSON"}
    PlanFileCheck -->|"Yes — plan field is set"| PlanDrift(["Step 2.5 Mode A — Plan Drift Check<br>Spawn haiku agent — report findings — stop"])
    PlanFileCheck -->|"No — no plan field"| GroomDrift(["Step 2.5 Mode B — Grooming Drift Check<br>Spawn haiku agent — report findings — stop"])
    C4Check -->|"No — not groomed today"| PassAll(["All checks pass — proceed to Step 3"])
```

### Step 2.5: Drift Check (groomed item)

**Trigger**: Item is already groomed AND has not been re-groomed today. Two modes based on whether a plan file exists.

---

#### Mode A: Plan Drift (item has a plan file)

**Precondition**: `plan` field is set and points to an existing file.

**Purpose**: Detect what changed in the codebase since the plan was written, so tasks reflect current reality before execution.

Spawn a haiku-model agent (`subagent_type="general-purpose"`, model=haiku) with this task:

1. Read the plan file at the `plan` path
2. Extract all file paths mentioned in the plan (task descriptions, files-to-modify sections, context manifest)
3. Get the plan file's last commit date: `git log -1 --format=%aI -- {plan_path}`
4. For each referenced file, find commits since that date: `git log --oneline --since={date} -- {file_path}`
5. For each commit found, get the diff summary: `git show --stat {sha} -- {file_path}` and `git log -1 --format=%s {sha}` for the commit message
6. Analyze whether each commit changes what the plan expected to find in that file. Categories:
   - **Scope change** — file now does more or less than the plan assumed
   - **Partial fix** — the issue the plan addresses was partially resolved by another commit
   - **New callers** — other files now depend on this file that the plan did not account for
   - **File moved/renamed** — file is at a different path
   - **No impact** — commit is unrelated to the plan's goals for this file
7. Write findings to the backlog item via `mcp__backlog__backlog_groom(selector="{title}", section="Plan Drift", content="...")`

**Plan Drift output format when drift is detected:**

```markdown
## Plan Drift

**Plan**: {plan_path}
**Plan last modified**: {date}
**Files checked**: {count}
**Files with drift**: {count}

### {file_path}

**Commits since plan** ({count}):
- `{sha_short}` ({date}): {commit_message}

**Impact on plan**:
When first planned, this file {description of expected state}.
In commit {sha} on {date}, {description of what changed}.
{New callers / scope changes / partial fixes discovered}.
Review {specific task IDs} against this change during execution.

### {next file}
...
```

**Plan Drift output format when no drift is detected:**

```markdown
## Plan Drift

**Plan**: {plan_path}
**Plan last modified**: {date}
**Files checked**: {count}
**No drift detected** — all referenced files unchanged since plan creation.
```

---

#### Mode B: Grooming Drift (item groomed but no plan file)

**Precondition**: Item is groomed (has groomed sections) but `plan` field is absent or empty.

**Purpose**: Detect what changed in the codebase since the item was groomed, so the groomed content reflects current reality before planning begins.

Spawn a haiku-model agent (`subagent_type="general-purpose"`, model=haiku) with this task:

1. Call `mcp__backlog__backlog_view(selector="{title}")` to retrieve the full item
2. Extract file paths from the groomed sections:
   - **Impact Radius** section — file paths listed under Code, Documentation, Configuration/CI, Agent Instructions
   - **Files** section — explicit file paths listed by the groomer
   - **Output / Evidence** section — file paths cited as evidence
3. Get the item's groomed date from the frontmatter `groomed` field (format: `YYYY-MM-DD`)
4. For each extracted file path, find commits since that date: `git log --oneline --since={groomed_date} -- {file_path}`
5. For each commit found, get the diff summary: `git show --stat {sha} -- {file_path}` and `git log -1 --format=%s {sha}` for the commit message
6. Analyze whether each commit changes what the groomed content describes. Same categories as Mode A:
   - **Scope change** — file now does more or less than the groomed content assumed
   - **Partial fix** — the issue the item describes was partially resolved by another commit
   - **New callers** — other files now depend on this file that the groomed content did not account for
   - **File moved/renamed** — file is at a different path
   - **No impact** — commit is unrelated to the item's scope for this file
7. Write findings to the backlog item via `mcp__backlog__backlog_groom(selector="{title}", section="Grooming Drift", content="...")`

**Grooming Drift output format when drift is detected:**

```markdown
## Grooming Drift

**Groomed date**: {groomed_date}
**Files checked**: {count}
**Files with drift**: {count}

### {file_path}

**Commits since grooming** ({count}):
- `{sha_short}` ({date}): {commit_message}

**Impact on groomed content**:
When groomed on {groomed_date}, this file {description of expected state}.
In commit {sha} on {date}, {description of what changed}.
{New callers / scope changes / partial fixes discovered}.
Re-groom or update the affected sections before planning.

### {next file}
...
```

**Grooming Drift output format when no drift is detected:**

```markdown
## Grooming Drift

**Groomed date**: {groomed_date}
**Files checked**: {count}
**No drift detected** — all referenced files unchanged since grooming.
```

---

After either drift check completes, report findings to the user and stop. Do not proceed to Step 3.

---

### Step 3: Extract Item Details

For each target item, extract: title, description, research-first questions (if present), source, suggested location.

### Step 3.5: RT-ICA Initial Snapshot

Before spawning any agents, the orchestrator runs a quick RT-ICA pass using only the information available from Steps 2-3 (item fields, description, suggested_location). This is a baseline — not the final assessment.

**Categorization rule (apply before listing any condition):**

RT-ICA assesses INFORMATION completeness — "do we know enough to plan?" Only list conditions that represent information gaps or verifiable facts about the environment. Implementation deliverables (things to build) belong in acceptance criteria, not in RT-ICA conditions.

- AVAILABLE — information exists and is verified from the item or codebase
- DERIVABLE — information can be obtained with tools during the swarm phase
- MISSING — information we lack that cannot be derived and requires a human decision

A condition like "sam create command exists" is a deliverable — it belongs in acceptance criteria. The RT-ICA question is "do we know what sam create needs to do?" — if yes, AVAILABLE; if it must be researched, DERIVABLE.

```text
RT-ICA Snapshot: {item title}
Goal: {one sentence}
Conditions:
1. {condition} | Status: {AVAILABLE|DERIVABLE|MISSING}
...
AVAILABLE count: {N}
DERIVABLE count: {N}
MISSING count: {N}
```

Write this snapshot to the item via `mcp__backlog__backlog_groom(selector="{title}", section="RT-ICA", content="{snapshot}")`.

This snapshot serves two purposes:

- It feeds the scope-sizing decision in Step 3.6
- It gives the swarm agents a starting picture of what's known and what needs research

### Step 3.6: Scope Sizing

The orchestrator determines how many agents to spawn based on the RT-ICA snapshot and the item's nature. This is a decision the orchestrator makes — not a delegation.

```mermaid
flowchart TD
    Start([RT-ICA snapshot + item description]) --> Q1{Issue type?}
    Q1 -->|defect / bug fix| Q2{How many conditions are AVAILABLE?}
    Q2 -->|All AVAILABLE| Minimal["MINIMAL scope<br>2 agents: fact-checker + groomer<br>Impact radius = file + direct callers only"]
    Q2 -->|Some DERIVABLE| Narrow["NARROW scope<br>3 agents: impact-analyst + fact-checker + groomer<br>Impact radius from known files"]
    Q2 -->|Any MISSING| Standard["STANDARD scope<br>4 agents: impact-analyst + fact-checker + rtica-assessor + groomer"]
    Q1 -->|missing-guardrail / procedural| Q3{How many conditions are DERIVABLE or MISSING?}
    Q3 -->|Mostly AVAILABLE| Narrow
    Q3 -->|Mixed| Standard
    Q3 -->|Mostly DERIVABLE/MISSING| Full["FULL scope<br>5 agents: all teammates<br>Full impact radius expansion"]
    Q1 -->|unbounded-design / new plugin| Full
    Q1 -->|recurring-pattern| Standard
```

| Scope | Agents | When | Impact Radius depth |
|-------|--------|------|-------------------|
| MINIMAL | 2 (fact-checker, groomer) | Bug fix, all conditions known, existing system | File + direct callers |
| NARROW | 3 (impact-analyst, fact-checker, groomer) | Known system, some unknowns to derive | Known files + one level of expansion |
| STANDARD | 4 (impact-analyst, fact-checker, rtica-assessor, groomer) | Mixed knowns/unknowns, existing system being modified | Full expansion from known starting points |
| FULL | 5 (all teammates including classifier) | New system, many unknowns, unbounded design | Deep expansion, classify issue type, full RCA |

**Escalation rule:** If any agent discovers scope beyond what the current sizing anticipated (e.g., impact-analyst in NARROW scope finds 15+ affected systems), the orchestrator escalates to the next scope level by spawning additional agents. In team mode, new teammates join the existing team. In no-team mode, the orchestrator spawns new agents in the next wave.

### Steps 4-8: Parallel Grooming Swarm

Steps 4-8 run as a parallel swarm sized by Step 3.6. Each concern gets its own agent. All agents write to the same backlog item via MCP `backlog_groom` (each writes to a different section — no clobbering). Agents broadcast findings to the team so others can react.

#### Team mode (preferred — when TeamCreate is available)

```text
TeamCreate(team_name: "groom-{item-slug}")
```

Create tasks and spawn teammates for each concern:

**Teammates to spawn** (all run in parallel, all write via MCP):

1. **impact-analyst** — Build the affected systems inventory (Phase 1), then run the 5-question impact checklist on each system (Phase 2). Write results to `section="Impact Radius"`. Broadcast scope-expanding findings to the team.
2. **fact-checker** — Verify item claims against primary sources. Write results to `section="Fact-Check"`. Broadcast REFUTED claims (these become MISSING conditions for rtica-assessor).
3. **rtica-assessor** — Assess information completeness. Write results to `section="RT-ICA"`. When fact-checker broadcasts a REFUTED claim, mark that condition MISSING. When impact-analyst broadcasts new scope, add new conditions. Broadcast DERIVABLE conditions (fact-checker or impact-analyst may be able to resolve them).
4. **classifier** — Classify issue type and run root-cause analysis if `defect` or `recurring-pattern`. Write to `section="Issue Classification"` and `section="Root-Cause Analysis"`.
5. **groomer** — Produce groomed subsections (Reproducibility, Priority, Impact, Benefits, Expected Behavior, Acceptance Criteria, Files, Resources, Dependencies, Effort). Waits for impact-analyst, fact-checker, and rtica-assessor to complete first (task dependency). Write each subsection via `section="{name}"`.

**Task dependencies:**

```text
TaskCreate(subject: "Impact Radius")           # no deps
TaskCreate(subject: "Fact-Check")              # no deps
TaskCreate(subject: "RT-ICA")                  # blocked by Impact Radius + Fact-Check
TaskCreate(subject: "Issue Classification")    # no deps
TaskCreate(subject: "Groomer")                 # blocked by RT-ICA + Issue Classification
```

**Teammate interaction flow:**

```mermaid
sequenceDiagram
    participant L as Orchestrator
    participant IA as impact-analyst
    participant FC as fact-checker
    participant RT as rtica-assessor
    participant CL as classifier
    participant GR as groomer

    L->>IA: spawn (item details, Files, Evidence, suggested_location)
    L->>FC: spawn (item claims to verify)
    L->>RT: spawn (item details — waits for IA + FC)
    L->>CL: spawn (item description)

    IA->>IA: build systems inventory from groomed content
    IA->>IA: expand via imports, docs, agents, config, CI
    IA-->>FC: broadcast "SCOPE: found 12 systems, 2 CI workflows"
    FC->>FC: adds CI claims to verification list

    FC->>FC: verify claims against primary sources
    FC-->>RT: broadcast "REFUTED: task_format.py multi-doc support"
    RT->>RT: marks condition MISSING

    IA->>IA: run 5-question checklist per system
    IA->>IA: write Impact Radius section via MCP

    FC->>FC: write Fact-Check section via MCP

    RT->>RT: assess completeness using IA + FC results
    RT-->>FC: broadcast "DERIVABLE: check ruamel.yaml multi-doc"
    FC->>FC: researches, broadcasts result
    RT->>RT: updates assessment
    RT->>RT: write RT-ICA section via MCP

    CL->>CL: classify + RCA if needed
    CL->>CL: write Issue Classification section via MCP

    Note over GR: unblocked after RT-ICA + Classification complete
    GR->>GR: read all sections written by other teammates
    GR->>GR: produce Reproducibility, Priority, Impact, etc.
    GR->>GR: write each subsection via MCP

    L->>L: all tasks complete — shutdown team
```

**Scope expansion handling:** When impact-analyst discovers systems not in the original groomed content, it broadcasts the finding. Other teammates adjust:
- fact-checker adds new claims to verify
- rtica-assessor adds new conditions
- groomer incorporates new systems into its sections

After all teammates complete, the orchestrator shuts down the team and proceeds to Step 9.

#### No-team fallback (when TeamCreate is not available)

Spawn agents sequentially, re-spawning when new information arrives:

**Wave 1** (parallel — no dependencies between them):
- Agent: impact-analyst — writes `section="Impact Radius"`
- Agent: fact-checker — writes `section="Fact-Check"`
- Agent: classifier — writes `section="Issue Classification"` and `section="Root-Cause Analysis"`

**After Wave 1 completes**, read the Impact Radius and Fact-Check sections from the item. If impact-analyst found systems that change the scope of the fact-check, spawn a second fact-checker agent with the expanded scope.

**Wave 2** (depends on Wave 1 results):
- Agent: rtica-assessor — receives Impact Radius + Fact-Check results, writes `section="RT-ICA"`

If RT-ICA returns BLOCKED, stop and present missing inputs to user. Do not proceed to Wave 3.

**Wave 3** (depends on Wave 2):
- Agent: groomer — receives all prior sections, writes groomed subsections

**Re-spawn rule:** After each wave, read what was written to the item via MCP. If new scope was discovered (impact-analyst found systems not in the original description), check whether the existing sections need updating. If yes, spawn targeted agents to update specific sections before proceeding to the next wave.

#### Impact Radius — what to find and why

The impact-analyst teammate (or agent in no-team mode) performs two phases:

**Phase 1: Build the Affected Systems Inventory**

Starting from the files and functions in the groomed content (Files, Evidence, Description, suggested_location sections), identify all systems that interact with the thing this item changes. A "system" is any file that produces, consumes, documents, configures, tests, or instructs the use of the affected interface.

Create a TodoItem for each system. Each TodoItem includes: file path, role (producer / consumer / documentation / configuration / CI / agent-instruction), and connection (why this file is affected).

Start with the known systems from the groomed content:
- Files listed in the **Files** section
- Functions cited in the **Output / Evidence** section
- Path from **suggested_location**

Then expand by searching for:
- Files that import from or call into the known systems
- Documentation that describes the current behavior of these systems
- Agent or skill files that instruct the AI to use these systems
- Configuration files that reference these modules
- CI workflows that test these modules
- Test files that exercise these systems

Exclude archived and generated content: `plan/` artifacts, `docs/plans/`, `.claude/archive/`, `.claude/grooming-sessions/`, test fixtures. Backlog item files (`.claude/backlog/*.md`) are informational — they describe the problem, not the system.

**Phase 2: Impact Checklist (per system)**

For each TodoItem, answer these five questions:

1. **Will this file break when the item ships?** — Does it depend on an interface, format, or behavior that the item changes? If yes: what specifically breaks.
2. **Will this file become stale?** — Does it describe, document, or reference the current behavior? If yes: what section or claim becomes inaccurate.
3. **Does this file need a code change?** — Import update, API migration, format change, dependency update. If yes: what change.
4. **Does this file need a content update?** — Documentation rewrite, instruction update, example refresh. If yes: what section.
5. **Is there a test that covers this file's interaction with the changed interface?** — If no: flag as needing a new test.

Mark each TodoItem complete after answering. Any system with at least one "yes" answer goes into the Impact Radius output.

**Impact Radius output format:**

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

#### Fact-Check — evidence rules

The fact-checker teammate (or agent) verifies item claims against primary sources. Training data recall is NOT evidence. Valid evidence: WebFetch output, WebSearch results, command output, repository source code, MCP tool output.

Output: `Fact-Check Summary` with claims checked, VERIFIED/REFUTED/INCONCLUSIVE counts, and citations.

REFUTED claims become MISSING conditions in RT-ICA. INCONCLUSIVE claims become DERIVABLE.

#### RT-ICA — information completeness

The rtica-assessor produces:

```text
RT-ICA: {item title}
Goal: {one sentence}
Conditions:
1. {condition} | Status: {AVAILABLE|DERIVABLE|MISSING} | Info needed: {what}
Decision: {APPROVED|BLOCKED}
```

**ARL human-probing integration:** When RT-ICA returns BLOCKED or MISSING conditions, optionally include `invisible_knowledge_prompts` — questions to ask the human before planning. See [.claude/docs/sdlc-layers/arl-human-probing-design.md](../../docs/sdlc-layers/arl-human-probing-design.md).

#### Issue Classification

Classify the issue type. See flowchart and write template in [issue-classification.md](./references/issue-classification.md).

| Type | Analysis Method |
|------|----------------|
| `procedural` | none |
| `recurring-pattern` | 6-sigma |
| `defect` | 5-whys |
| `missing-guardrail` | none |
| `unbounded-design` | design-framing |

Root-cause analysis runs only for `defect` or `recurring-pattern`. Full procedures: [issue-classification.md](./references/issue-classification.md).

#### Groomer — subsection production

The groomer teammate (or agent) produces: Reproducibility, Priority, Impact, Benefits, Expected Behavior, Acceptance Criteria, Files, Resources, Dependencies, Effort. Prompt templates: [groomer-agent.md](./references/groomer-agent.md).

The groomer reads all sections written by prior teammates (Impact Radius, Fact-Check, RT-ICA, Issue Classification) from the item via MCP before producing its sections. This ensures the groomed content reflects the full findings.

### Step 8.5: RT-ICA Final Pass

The following diagram is the authoritative procedure for the Step 8.5 RT-ICA final pass. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    SwarmDone(["All swarm agents complete"]) --> ReadAll["Read all sections now written to the item<br>Impact Radius, Fact-Check, Issue Classification,<br>groomed subsections — via MCP"]
    ReadAll --> ReAssess["Re-assess every condition from the Step 3.5 snapshot<br>Compare snapshot status to final status per condition<br>Apply categorization rule: deliverables are not conditions"]
    ReAssess --> ResolutionPass["Self-resolution pass<br>For each MISSING or DERIVABLE condition:<br>attempt tool-based resolution (Grep, Read, WebSearch, Bash)<br>Every resolution must cite the tool result<br>Training data answers banned"]
    ResolutionPass --> ResolvedAny{"Any conditions<br>resolved by tools?"}
    ResolvedAny -->|"Yes — mark AVAILABLE with citation"| UpdateConditions["Update conditions to AVAILABLE<br>with tool result citation"]
    ResolvedAny -->|"No"| BuildFinal
    UpdateConditions --> BuildFinal["Build RT-ICA Final report<br>Format: condition | Snapshot status to Final status<br>List all changes from snapshot<br>Include new conditions discovered by swarm<br>Include tool citations for resolved conditions"]
    BuildFinal --> WriteRTICA["Write final RT-ICA to item via backlog_groom<br>selector=title, section='RT-ICA', content=final<br>This replaces the Step 3.5 snapshot"]
    WriteRTICA --> FinalDecision{"RT-ICA Final Decision?"}
    FinalDecision -->|"BLOCKED — MISSING conditions remain<br>after self-resolution pass"| BlockedBatch["Batch all remaining MISSING conditions<br>For each: what was tried, options found,<br>trade-offs from tool results<br>Present as single batch to user"]
    BlockedBatch --> BlockedStop(["STOP — do not proceed to Step 9<br>Wait for user answers<br>Re-check after receiving responses"])
    FinalDecision -->|"APPROVED — all conditions AVAILABLE or DERIVABLE resolved"| Proceed(["Item fully groomed with verified information<br>Proceed to Step 9"])
```

RT-ICA Final report format:

```text
RT-ICA Final: {item title}
Goal: {same as snapshot}
Conditions:
1. {condition} | Snapshot: {AVAILABLE|DERIVABLE|MISSING} → Final: {AVAILABLE|DERIVABLE|MISSING} | Citation: {tool result}
...
Changes from snapshot:
- {condition X}: DERIVABLE → AVAILABLE (resolved by fact-checker — cite: {tool result})
- {condition Y}: AVAILABLE → MISSING (refuted by fact-checker)
- {condition Z}: (new) MISSING (discovered by impact-analyst)
Decision: {APPROVED|BLOCKED}
```

**BLOCKED batch format (when MISSING conditions remain after self-resolution pass):**

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

### Step 9: Write Groomed Content to Item Files

For each item, write groomed content into the per-item file via the backlog MCP tools.

**MCP tool parameters are schema-enforced.** Unlike CLI subcommands, MCP tools reject invalid parameters
with a structured error. There is no need to verify signatures before calling. If unsure which tool to
use, check the tool name and parameters:

- `mcp__backlog__backlog_update` — updates an existing item (selector required)
- `mcp__backlog__backlog_groom` — writes groomed content (selector required)
- `mcp__backlog__backlog_sync` — creates GitHub issues for items missing them and pushes groomed content (no selector — operates on entire backlog)

Prefer incremental updates so sections (Fact-Check, RT-ICA, groomed subsections) are written as they become available. GitHub is canonical: when the item has an issue, the MCP tool syncs groomed content to the GitHub issue body.

**Preferred: incremental section updates**

After each step, call `mcp__backlog__backlog_groom` with `section` and `content`:

```text
# After Step 4 (fact-check)
mcp__backlog__backlog_groom(selector="{item title}", section="Fact-Check", content="{fact-check summary}")

# After Step 5 (RT-ICA)
mcp__backlog__backlog_groom(selector="{item title}", section="RT-ICA", content="{rt-ica summary}")

# After Step 8 (groomer output) — subsection or full groomed body
mcp__backlog__backlog_groom(selector="{item title}", section="Reproducibility", content="{reproducibility section}")
# ... or for full groomed body:
mcp__backlog__backlog_groom(selector="{item title}", groomed_content="{full groomed body}")
```

**Alternative: full content**

```text
mcp__backlog__backlog_groom(selector="{item title}", groomed_content="{full groomed body}")
```

Note — `--groomed-file {path}` and stdin pipe (`< {file}`) patterns have no MCP equivalent.
Provide groomed content inline via the `groomed_content` parameter.

**Valid section names** — top-level: `Fact-Check`, `RT-ICA`, `Impact Radius`. Groomed subsections: `Reproducibility`, `Priority`, `Impact`, `Scope`, `Output / Evidence`, `Dependencies`, `Research`, `Skills`, `Agents`, `Prior Work`, `Files`, `Decision`, `Issue Classification`, `Root-Cause Analysis`.

The backlog script updates `.claude/backlog/{priority}-{slug}.md` with merged sections, sets `groomed` in frontmatter, and syncs to the GitHub issue when the item has one.

**Bulk grooming (multiple items)** — when grooming 2+ items, optionally persist a session summary to `.claude/grooming-sessions/{YYYY-MM-DD}.md`:

```markdown
# Grooming Session {YYYY-MM-DD}

**Items groomed**: {count}
**Arguments**: {original arguments}

## Summary

| Item | Fact-Check | RT-ICA | Written |
|------|------------|--------|---------|
| {title} | {V}/{R}/{I} | {APPROVED/BLOCKED} | ✓ |

## Cross-Item Findings

### Shared Dependencies
- {items multiple backlog items depend on}

### Suggested Groupings
- {items that could be worked together}

### Research Gaps
- {topics needing research}
```

Per-item groomed content lives in each item file; this session file holds only metadata and cross-item findings.

## Example Invocations

```text
/groom-backlog-item Error Recovery
/groom-backlog-item P1
/groom-backlog-item all
```

## Completion Criteria

- Validity check (job still valid, problem reproducible, local file not stale) before grooming
- Drift Check run (Step 2.5) when item is already groomed today:
  - Mode A (Plan Drift) — item has a plan file: extract file paths from plan, compare git log since plan date, write to "Plan Drift" section, then stop
  - Mode B (Grooming Drift) — item has no plan file: extract file paths from Impact Radius / Files / Output Evidence sections, compare git log since groomed date, write to "Grooming Drift" section, then stop
- RT-ICA initial snapshot run before swarm (Step 3.5) — baselines what is AVAILABLE / DERIVABLE / MISSING
- Scope sized from RT-ICA snapshot + issue type (Step 3.6) — MINIMAL / NARROW / STANDARD / FULL
- Agent count matches scope sizing — not all 5 agents for every item
- All grooming concerns run as parallel swarm (team mode) or iterative waves (no-team fallback)
- Impact Radius: systems inventory built from groomed content, 5-question checklist run per system, section written via MCP
- Fact-Check: claims verified against primary sources (training data not used as evidence), section written via MCP
- Issue Classification: assigned with RCA for `defect`/`recurring-pattern` types, section written via MCP
- Groomer: subsections produced after all prior sections are available, each written via MCP
- Scope expansion handled: when new systems or refuted claims change scope, orchestrator escalates to next scope level
- RT-ICA final pass run after swarm completes (Step 8.5) — re-assesses all conditions with full information, replaces snapshot
- RT-ICA final shows changes from snapshot (which conditions moved, which are new)
- If RT-ICA final is BLOCKED, stop and present missing inputs — do not proceed to Step 9
- When item has GitHub issue, all sections synced to issue body
- Team shut down after all teammates complete (team mode) or all waves finish (fallback mode)
- Bulk session summary optionally saved to `.claude/grooming-sessions/{date}.md` when grooming multiple items
