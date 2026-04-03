---
name: groom-backlog-item
description: Groom backlog items — trigger /groom-backlog-item <title|section|all> — fact-checks item claims against primary sources, runs RT-ICA per item, then spawns @backlog-item-groomer agents. Writes groomed content via backlog MCP tools (backlog_groom, backlog_update). Use when preparing backlog items for planning or execution.
argument-hint: <item-title-or-section-or-all>
user-invocable: true
---

<groom_scope>$ARGUMENTS</groom_scope>

# Groom Backlog Item

Orchestrate autonomous backlog refinement: verify claims, clarify scope, estimate effort, map resources and dependencies, and clean stale items — making each item ready for the planning phase.

**Scope boundary**: Grooming answers "what needs to be done, is the problem clear, and what do we have to work with?" It does NOT answer "how should it be built." Architecture, task decomposition, and implementation design happen in the SAM planning phase (`/work-backlog-item` Step 6). Grooming produces a DEEP item (Detailed appropriately, Estimated, Emergent, Prioritized) — not a plan. The human provides direction and priorities; the agent does the research, fact-checking, and resource mapping autonomously.

See the [Backlog Lifecycle reference](../../docs/backlog-lifecycle.md) for the complete state machine, handoff protocol, and data architecture.

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
    FinalDecision -->|"APPROVED — all conditions resolved"| S87["Step 8.7 — Groomer Output Validation Gate<br>Load references/groomer-output-validation.md"]
    S87 --> S9["Step 9 — Write groomed content<br>to item files via MCP tools"]
    S9 --> Done(["Item fully groomed and synced"])
```

### Step 1: Parse Arguments and Load Backlog

Call `mcp__plugin_dh_backlog__backlog_list()` and filter the returned dict's `items` list by argument type above.

### Step 2: Validity Check (Pre-Groom Gate)

The following diagram is the authoritative procedure for the Step 2 validity check. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    ItemIn(["Item selected for grooming"]) --> O1{"Observable check A: Prior implementation<br>git log --oneline --all -50 --grep='{title keywords}'<br>AND backlog_list_merged_prs(search='{title keywords}')<br>Commits or merged PRs found?"}
    O1 -->|"Commit or merged PR references this item"| AlreadyDone["Comment evidence on GitHub issue (if exists)<br>mcp: backlog_comment_issue(issue_number=N, body='Completed via PR')<br>Close GitHub issue: mcp: backlog_close(selector='#N')<br>Call backlog_resolve with PR/SHA summary"]
    AlreadyDone --> DoneSkip(["Report to user — skip grooming for this item"])
    O1 -->|"No commits or PRs found"| O2{"Observable check B: Location validity<br>Glob(suggested_location) returns results?<br>OR suggested_location absent from item?"}
    O2 -->|"Path exists OR no suggested_location in item"| O3
    O2 -->|"Path not found AND description requires it"| LocationGone{"Grep codebase for module name or class<br>from suggested_location path — substitute found?"}
    LocationGone -->|"Substitute path found"| UpdateSuggested["Update suggested_location via backlog_update — proceed as valid"]
    LocationGone -->|"No substitute"| InvalidSkip(["C1 INVALID: suggested_location gone with no substitute<br>Report and skip — recommend close or re-groom"])
    UpdateSuggested --> O3
    O3{"Observable check C: Age and activity<br>metadata.added older than 90 days?<br>AND metadata.groomed absent?<br>AND no GitHub issue comments? AND no plan?"}
    O3 -->|"Age 90 days or less OR has recent activity"| C3
    O3 -->|"Age over 90 days AND no activity"| AgeStale{"backlog_list — scan all titles for keyword overlap<br>with this item's title keywords<br>Any item added in last 30 days with overlap?"}
    AgeStale -->|"No overlap found"| C3
    AgeStale -->|"Overlap found"| Superseded(["WARN: possibly superseded by '{newer title}'<br>Interactive: AskUserQuestion<br>AUTO_MODE: log WARN and proceed"])
    Superseded --> C3
    C3{"Does item have a GitHub issue?<br>Check metadata.issue or index link #N"}
    C3 -->|"No GitHub issue"| C4Check{"Check item file's 'groomed' frontmatter field<br>Does groomed == today's date AND<br>item has all required sections?"}
    C3 -->|"Yes — call backlog_view selector='#N'<br>Check 'state' field in returned dict"| IssueState{"state field<br>value?"}
    IssueState -->|"open"| C4Check
    IssueState -->|"closed — local file is stale"| StaleSearch["Search for commits: git log --grep='#N'<br>Search merged PRs: mcp: backlog_list_merged_prs(search='#N')"]
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

- **Mode A (Plan Drift)** — item has a plan file: extract file paths from plan, compare git log since plan date, write to "Plan Drift" section, then stop
- **Mode B (Grooming Drift)** — item has no plan file: extract file paths from Impact Radius / Files / Output Evidence sections, compare git log since groomed date, write to "Grooming Drift" section, then stop

Full procedures, agent spawn instructions, and output format templates: [drift-check.md](./references/drift-check.md)

---

After either drift check completes, report findings to the user and stop. Do not proceed to Step 3.

---

### Step 3: Extract Item Details

For each target item, extract: title, description, research-first questions (if present), source, suggested location.

### Step 3.1: Discovery Gate

Before running RT-ICA or spawning the swarm, check whether a structured discovery artifact
exists for this item. This surfaces prior requirements gathering that should inform grooming.

```mermaid
flowchart TD
    Extract([Step 3 complete — item details extracted]) --> HasIssue{"Item has GitHub<br>Issue number?"}
    HasIssue -->|"No — no issue linked"| SkipGate["Skip discovery gate<br>Proceed to Step 3.5"]
    HasIssue -->|"Yes — issue #{N}"| TypeCheck{"Item labels include<br>'type:fix' or 'type:bug'?"}
    TypeCheck -->|"Yes — fix/bug type"| SkipGate
    TypeCheck -->|"No — feature/refactor/other"| CheckArtifact["artifact_list(<br>issue_number={N},<br>artifact_type='feature-context')"]
    CheckArtifact --> HasDiscovery{"count > 0?"}
    HasDiscovery -->|"Yes"| LoadDiscovery["Read via artifact_read(issue_number={N},<br>artifact_type='feature-context')<br>Pass content to swarm agents as prior context"]
    HasDiscovery -->|"No"| InvokeDiscovery["Invoke: Skill(skill='dh:discovery')<br>Wait for completion"]
    InvokeDiscovery --> LoadDiscovery
    LoadDiscovery --> Continue([Proceed to Step 3.5 with discovery context])
    SkipGate --> Continue
```

The discovery context (if loaded) is passed to the swarm agents in Steps 4-8 as additional
input alongside the item description. Agents should treat it as verified requirements that
do not need re-derivation.

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

Write this snapshot to the item via `mcp__plugin_dh_backlog__backlog_groom(selector="{title}", section="RT-ICA", content="{snapshot}")`.

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

Exclude archived and generated content: plan artifacts, `docs/plans/`, `.claude/archive/`, `.claude/grooming-sessions/`, test fixtures. Backlog items (accessible via `backlog_view`) are informational — they describe the problem, not the system.

**Phase 2: Impact Checklist (per system)**

For each TodoItem, answer these five questions:

1. **Will this file break when the item ships?** — Does it depend on an interface, format, or behavior that the item changes? If yes: what specifically breaks.
2. **Will this file become stale?** — Does it describe, document, or reference the current behavior? If yes: what section or claim becomes inaccurate.
3. **Does this file need a code change?** — Import update, API migration, format change, dependency update. If yes: what change.
4. **Does this file need a content update?** — Documentation rewrite, instruction update, example refresh. If yes: what section.
5. **Is there a test that covers this file's interaction with the changed interface?** — If no: flag as needing a new test.

Mark each TodoItem complete after answering. Any system with at least one "yes" answer goes into the Impact Radius output.

**Impact Radius output format**: Six named categories (Code Producers, Code Consumers, Code Other References, Documentation, Configuration/CI, Agent Instructions) plus a Systems Inventory and Ecosystem Completeness Checklist. Full format template: [groomer-agent.md — Impact Radius Output Format](./references/groomer-agent.md#impact-radius-output-format). If a category has no affected files, write `None identified.` — do not omit the category.

#### Fact-Check — evidence rules

The fact-checker teammate (or agent) verifies item claims against primary sources. Training data recall is NOT evidence. Valid evidence: WebFetch output, WebSearch results, command output, repository source code, MCP tool output.

Output: `Fact-Check Summary` with claims checked, VERIFIED/REFUTED/INCONCLUSIVE counts, and citations.

REFUTED claims become MISSING conditions in RT-ICA. INCONCLUSIVE claims become DERIVABLE.

#### Fact-Checker Output Contract

Required fields (`verdict`, `claim`, `evidence`, `source`) and validation rules (reject on missing verdict, INCONCLUSIVE on missing evidence, REFUTED→MISSING / INCONCLUSIVE→DERIVABLE RT-ICA mapping): [groomer-agent.md — Fact-Checker Output Contract](./references/groomer-agent.md#fact-checker-output-contract).

#### RT-ICA — information completeness

The rtica-assessor produces:

```text
RT-ICA: {item title}
Goal: {one sentence}
Conditions:
1. {condition} | Status: {AVAILABLE|DERIVABLE|MISSING} | Info needed: {what}
Decision: {APPROVED|BLOCKED}
```

**ARL human-probing integration:** When RT-ICA returns BLOCKED or MISSING conditions, optionally include `invisible_knowledge_prompts` — questions to ask the human before planning. See [arl-human-probing-design.md](../../docs/sdlc-layers/arl-human-probing-design.md).

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
    BlockedBatch --> BlockedStop(["PAUSE — present batch to user<br>When user answers arrive: mark each resolved condition AVAILABLE<br>with user citation, re-run FinalDecision check<br>If APPROVED: proceed immediately to Step 8.7"])
    FinalDecision -->|"APPROVED — all conditions AVAILABLE or DERIVABLE resolved"| Proceed(["Proceed to Step 8.7"])
```

RT-ICA Final report format:

```text
RT-ICA Final: {item title}
Date: {YYYY-MM-DD}
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

**BLOCKED batch format**: Full template for presenting unresolved MISSING conditions to the user: [groomer-agent.md — RT-ICA BLOCKED Batch Format](./references/groomer-agent.md#rt-ica-blocked-batch-format).

**After BLOCKED**: When user provides answers, mark each resolved condition AVAILABLE with user citation, re-run Final Decision check. If APPROVED, continue to Step 8.7 immediately — do not stop or re-invoke.

### Step 8.7: Groomer Output Validation Gate (Pre-Write Gate)

Runs when RT-ICA Final Decision is APPROVED, before `backlog_groom(mark_groomed=True)` in Step 9.

Full procedure (7-section presence check, scope boundary check, retry/escalation flowchart): [groomer-output-validation.md](./references/groomer-output-validation.md). Scope violations are logged as notes but do not block the write; failures after 3 attempts mark status `blocked` and stop.

---

### Step 9: Write Groomed Content via MCP

For each item, write groomed content via the backlog MCP tools. The MCP server handles persistence and GitHub sync.

**MCP tool parameters are schema-enforced.** Unlike CLI subcommands, MCP tools reject invalid parameters
with a structured error. There is no need to verify signatures before calling. If unsure which tool to
use, check the tool name and parameters:

- `mcp__plugin_dh_backlog__backlog_update` — updates an existing item (selector required)
- `mcp__plugin_dh_backlog__backlog_groom` — writes groomed content (selector required)
- `mcp__plugin_dh_backlog__backlog_sync` — creates GitHub issues for items missing them and pushes groomed content (no selector — operates on entire backlog)

**`mark_groomed` parameter** (`bool`, default `False`): Pass `mark_groomed=True` on the final `backlog_groom` call to automatically advance the item's status from `needs-grooming` to `groomed`. When `True`, after all content writes complete: (a) the item's `metadata.status` field is set to `groomed` in the local per-item file; (b) the `status:needs-grooming` GitHub label is removed (no-op if already absent); (c) the `status:groomed` GitHub label is added to the issue (created automatically if it does not exist on the repository). When used with the `sections` batch parameter, all sections are written first and the status transition fires exactly once after the batch completes. Calling `backlog_groom` with `mark_groomed=True` multiple times is safe — if `status:groomed` is already present the label update is skipped. If the GitHub label transition fails, the local frontmatter update still applies and a warning is recorded in the result.

Prefer incremental updates so sections (Fact-Check, RT-ICA, groomed subsections) are written as they become available. GitHub is canonical: when the item has an issue, the MCP tool syncs groomed content to the GitHub issue body.

**Preferred: incremental section updates**

After each step, call `mcp__plugin_dh_backlog__backlog_groom` with `section` and `content`:

```text
# After Step 4 (fact-check)
mcp__plugin_dh_backlog__backlog_groom(selector="{item title}", section="Fact-Check", content="{fact-check summary}")

# After Step 5 (RT-ICA)
mcp__plugin_dh_backlog__backlog_groom(selector="{item title}", section="RT-ICA", content="{rt-ica summary}")

# After Step 8 (groomer output) — subsection or full groomed body
mcp__plugin_dh_backlog__backlog_groom(selector="{item title}", section="Reproducibility", content="{reproducibility section}")
# ... or for full groomed body (batch mode):
mcp__plugin_dh_backlog__backlog_groom(selector="{item title}", sections={"Reproducibility": "{section content}", "Impact Radius": "{section content}"})
```

**Alternative: full content (batch mode)**

```text
mcp__plugin_dh_backlog__backlog_groom(selector="{item title}", sections={"Overview": "...", "Impact Radius": "...", "Open Questions": "..."})
```

Note — `--groomed-file {path}` and stdin pipe (`< {file}`) patterns have no MCP equivalent.
Provide groomed content inline via the `sections` dict parameter (batch mode) or incremental `section`+`content` parameters.

**Batch pattern: sections dict (preferred when writing 3+ sections at once)**

When the groomer produces all subsections at the end of Step 8, write them in a single call
using the `sections` parameter instead of one call per section. This produces a single GitHub
sync rather than one sync per section:

```text
mcp__plugin_dh_backlog__backlog_groom(
    selector="{item title}",
    sections={
        "Reproducibility": "{reproducibility section text}",
        "Priority": "{priority section text}",
        "Files": "{files section text}",
        "Implementation notes": "{notes section text}"
    },
    mark_groomed=True
)
```

Pass `mark_groomed=True` on the final `backlog_groom` call to automatically advance the item's
status from `needs-grooming` to `groomed`. Using `sections` combined with `mark_groomed=True`
is the recommended pattern — it writes all content and advances status atomically in a single
GitHub sync.

Use the batch pattern when all subsections are ready simultaneously (end of swarm). Use the
incremental pattern (`section` + `content`) when writing sections as they become available
mid-workflow (e.g., Fact-Check after Step 4, RT-ICA after Step 5) — omit `mark_groomed=True`
on intermediate calls and include it only on the final call.

**Valid section names** — top-level: `Fact-Check`, `RT-ICA`, `Impact Radius`. Groomed subsections: `Reproducibility`, `Priority`, `Impact`, `Scope`, `Output / Evidence`, `Dependencies`, `Research`, `Skills`, `Agents`, `Prior Work`, `Files`, `Decision`, `Issue Classification`, `Root-Cause Analysis`.

The MCP server merges sections, updates the item status, and syncs to the GitHub issue when the item has one.

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

### Handoff B: Grooming to Milestone Grouping

When Step 9 completes with `mark_groomed=True` applied and `metadata.status=groomed`:

```text
NEXT: skill="group-items-to-milestone" args="" condition="mark_groomed=True applied AND metadata.status=groomed"
```

---

## Example Invocations

```text
/groom-backlog-item Error Recovery
/groom-backlog-item P1
/groom-backlog-item all
```

## Completion Criteria

- Validity check (job still valid, problem reproducible, GitHub issue state current) before grooming
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
