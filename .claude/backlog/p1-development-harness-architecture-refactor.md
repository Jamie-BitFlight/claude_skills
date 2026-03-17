---
name: Development Harness Architecture Refactor
description: 'Type: unbounded-design'
metadata:
  topic: development-harness-architecture-refactor
  source: Session observation — brainstorming discussion about harness architecture
  added: '2026-03-11'
  priority: P1
  type: Refactor
  status: open
  issue: '#581'
  last_synced: '2026-03-14T15:59:47Z'
  groomed: '2026-03-11'
---

## Groomed (2026-03-11)

### Design Context

### Design Intent Preservation

### Superpowers Artifact Mapping

### Issue Classification

Type: unbounded-design
Scenario-target: Architecture refactor spanning two plugins with external tool interop requirements

Rationale: This is not a defect or recurring pattern — it is a design problem requiring decomposition into bounded phases. The scope spans plugin architecture, agent dispatch model, skill naming taxonomy, and external tool adapters. No root-cause analysis needed; design-framing is the appropriate method.

Design framing:
- Phase 1: Establish naming taxonomy + language manifest for python3-development + generic agent dispatch proof-of-concept
- Phase 2: Interop adapters for GSD and Superpowers artifacts
- Phase 3: Lift backlog integration from python3-development into harness
- Phase 4: Deduplicate agents (remove specialist agents from python3-development, replace with domain skills)

### Scope

### Refined Scope (from brainstorming 2026-03-11)

**In scope — Phase 1 (this item):**
- SDLC stage naming taxonomy research and decision
- Language manifest for python3-development (using existing schema)
- Generic agent dispatch model design (agent receives: stage workflow + domain skills + task file + quality gates)
- Nestable skill naming convention: `{domain}-{sdlc-stage}` at each decomposition level
- Proof-of-concept: one generic harness agent executes a Python task by loading stage workflow + python3 domain skill

**In scope — Phase 2 (separate item):**
- Interop adapter skill for GSD `.planning/` artifacts (read/write)
- Interop adapter skill for Superpowers `docs/superpowers/specs/` and `docs/superpowers/plans/` artifacts (read/write)
- Canonical internal format for the adapter layer (Approach 3 from brainstorming)

**In scope — Phase 3 (separate item):**
- Lift backlog integration (create-backlog-item, groom-backlog-item, work-backlog-item) from python3-development into development-harness
- Backlog becomes the upstream intake layer for the harness

**In scope — Phase 4 (separate item):**
- Remove specialist agents from python3-development (16 agents → domain skills only)
- python3-development provides skills + references + conventions + quality gates — no agents
- Deduplicate the 10 shared agents between harness and python3-development

**Out of scope:**
- BMAD-METHOD integration (future)
- Gas Town integration (future)
- TypeScript/Embedded/other language plugins (future — naming convention supports them)
- Custom process flow overrides per language (future — schema already supports it)

### Dependencies

### Internal Dependencies
- development-harness plugin (existing SAM pipeline, workflow skills, language manifest schema)
- python3-development plugin (existing agents, skills, references — source material for refactor)
- backlog system (MCP tools + CLI — currently in python3-development, will be lifted to harness)

### External Dependencies (for interop)
- GSD `.planning/` directory format (observed from /home/ubuntulinuxqa2/repos/get-shit-done)
- Superpowers `docs/superpowers/specs/` and `docs/superpowers/plans/` format (observed from /home/ubuntulinuxqa2/repos/superpowers)

### Blocking Dependencies
- SDLC stage naming taxonomy must be decided before skill naming convention can be finalized
- Generic agent dispatch model must be designed before specialist agents can be replaced

### Non-Blocking
- Interop adapters can be built independently of the agent refactor
- Backlog lift can happen independently of agent refactor

### Research

### Research Needed Before Planning

1. **SDLC stage naming taxonomy** — survey IEEE 12207, ISO 15288, SAFe, and the naming used by BMAD/GSD/Superpowers to propose a universal namespace. This is the BLOCKING research item.

2. **Generic agent dispatch patterns** — how do other multi-agent systems dispatch generic workers with loaded context? Relevant prior art: GSD's executor agents (fresh 200K context per dispatch), Superpowers' subagent-driven-development (fresh subagent per task), Gas Town's Polecat dispatch model.

### Research Completed (2026-03-11 brainstorming session)

External tool composability assessment — all four tools researched:
- **BMAD-METHOD**: Modular YAML agents, micro-file workflow architecture, 18 BMM workflows covering full SDLC, module system (Core + BMM + optional), scale-adaptive intelligence
- **GSD**: Wave-based parallel execution, `.planning/` state directory with phases/plans/verification, thin orchestrator + specialized agents, multi-runtime (Claude Code/OpenCode/Gemini/Codex)
- **Gas Town**: Town/rig-level plugin system, TOML+markdown plugin format, dog dispatch for non-blocking execution, mail/nudge cross-agent communication, federation architecture (planned)
- **Superpowers**: Skill chaining (brainstorming → writing-plans → subagent-driven-development), hard gates (no code without tests), SessionStart hook injection, two-stage code review

### Interop Design Decision (2026-03-11)

Selected **Approach 3 — Interop layer with canonical internal format**:
- Adapter scripts at boundaries read GSD/Superpowers artifacts into harness's canonical format
- Harness stages only read canonical format
- Adapters are small — map field names and directory structures
- Stage skills remain clean — no multi-format awareness needed

### Priority

P1 — confirmed. This is foundational architecture that unblocks:
- Future language plugins (typescript, embedded, etc.)
- External tool interop (GSD, Superpowers, future BMAD/Gas Town)
- Agent count reduction (16 specialist agents → generic agents + domain skills)
- Backlog integration consolidation

Phase 1 (naming + manifest + dispatch model) should be worked first. Phases 2-4 can be created as separate backlog items once Phase 1 design is approved.

### Decision

### Interop Structure Decision (user, 2026-03-11)

**NOT separate skills per external tool.** A single skill: `/development-harness:interop` with reference files that teach agents how to work with external artifacts.

Structure:
```text
skills/interop/
  SKILL.md              — entry point, when to use, how to detect external tools
  references/
    gsd-artifact-mapping.md       — ".planning/ dir maps to our stages like this: <mermaid/>"
    superpowers-artifact-mapping.md — "docs/superpowers/ maps to our stages like this: <mermaid/>"
    session-continuity.md          — ".continuehere.md file contains last pre-clear handoff doc"
```

Key properties:
- Agents learn the mapping by loading the interop skill — no format conversion scripts
- Detection is passive: "check for a `.planning/` dir; if it exists, the plans map to our processes like this"
- Session continuity: `.continuehere.md` is a pre-context-clear handoff document that any tool can write and any tool can read
- Future external tool support (BMAD, Gas Town) adds a new reference file — no skill changes needed

### Bidirectional Handoff Model (user, 2026-03-11)

The interop is not read-only. The harness can toggle state on external systems and vice versa.

**GSD → Harness handoff:**
- User runs GSD's long-form interview, research, and planning phases (`/gsd:new-project`, `/gsd:plan-phase`)
- User pauses GSD work via `/gsd:pause-work` (captures context handoff)
- User invokes `/dh:resume-work` which reads the GSD pause artifact and loads the planning state into harness stages
- Harness picks up from the appropriate stage (e.g., S5 Execution) using GSD's plans as input

**Harness → GSD handoff:**
- Harness completes execution/review stages
- Writes results back in a format GSD can consume (verification artifacts in `.planning/`)
- User can `/gsd:resume-work` to continue with GSD's verification or milestone completion

**Harness → Language Plugin handoff (per-stage):**
- When a stage requires language-specific implementation (e.g., "write the Python code"), the harness dispatches to a generic agent that loads the appropriate domain skills
- Example: harness reaches S5 Execution for a Python task → generic agent loads `/python3-development:python-cli-architect` skill + task file
- The agent operates within the harness's process framework but uses language-specific knowledge

**Harness commands needed:**
- `/dh:resume-work` — detect paused work from GSD/Superpowers/other tools, load their state, map to harness stage
- `/dh:pause-work` — capture harness state in a format external tools can read (`.continuehere.md` or tool-specific pause format)
- `/dh:handoff-to <tool>` — explicitly transition control to another tool's workflow at a specific stage boundary

**Key principle:** The user chooses the best tool for each stage. GSD for research and planning. Superpowers for TDD discipline. The harness for structured execution with language-specific agents. The interop layer makes these transitions seamless — no manual artifact copying.

### Interop Structure Decision (user, 2026-03-11)

**NOT separate skills per external tool.** A single skill: `/development-harness:interop` with reference files that teach agents how to work with external artifacts.

Structure:
```text
skills/interop/
  SKILL.md              — entry point, when to use, how to detect external tools
  references/
    gsd-artifact-mapping.md       — ".planning/ dir maps to our stages like this: <mermaid/>"
    superpowers-artifact-mapping.md — "docs/superpowers/ maps to our stages like this: <mermaid/>"
    session-continuity.md          — ".continuehere.md file contains last pre-clear handoff doc"
```

Key properties:
- Agents learn the mapping by loading the interop skill — no format conversion scripts
- Detection is passive: "check for a `.planning/` dir; if it exists, the plans map to our processes like this"
- Session continuity: `.continuehere.md` is a pre-context-clear handoff document that any tool can write and any tool can read
- Future external tool support (BMAD, Gas Town) adds a new reference file — no skill changes needed

### Design Decisions from Brainstorming

### 1. Mermaid Workflow Per Stage (user, 2026-03-11)

Each base workflow type has a mermaid graph showing the steps and loops for that stage. When a generic agent is dispatched to execute a stage, it receives this mermaid graph as its process definition. The graph defines:
- Sequential steps within the stage
- Loop conditions (e.g., NEEDS_WORK → re-execute)
- Exit conditions (e.g., all acceptance criteria pass)
- Handoff points to the next stage

The agent follows the graph mechanically. Domain knowledge comes from loaded skills, not from the workflow graph itself.

### 2. Nestable Skill Loading Pattern (user, 2026-03-11)

At stages requiring domain expertise (e.g., Software Architecture Planning), the generic agent loads TWO layers of skills:

**Cross-cutting SDLC stage skill** (from the harness):
- `software-architecture-planning` — universal architectural thinking regardless of language

**Per-project-type domain skills** (from the language plugin):
- `python3-project-design`
- `python3-systems-design`
- `python3-cli-design`
- `python3-web-structure`
- `python3-frontend-planning`
- `python3-backend-planning`
- `python3-security-planning`
- `python3-environment-planning`

The naming convention `{domain}-{sdlc-stage}` makes this nestable — the harness knows to look for `{detected-language}-{current-stage}` skills in the language plugin.

### 3. Workload-Splitting Decomposition Hierarchy (user, 2026-03-11)

A dedicated "workload-splitting" step decomposes work through multiple levels, each with its own skill loading:

```text
Architecture Document
  └─ Milestones (load: software-milestone-planning, python3-project-design)
       └─ Prioritized Plans per Milestone
            └─ Feature-Issues (load: feature-decomposition, python3-{relevant-type}-design)
                 └─ Stories / Tasks (load: task-design, python3-{relevant-type}-implementation)
```

At each decomposition level:
- A cross-cutting decomposition skill defines the structure and output format
- A domain skill provides language/framework-specific knowledge for sizing, sequencing, and dependency identification
- The naming convention follows `{domain}-{decomposition-level}` to keep it nestable

This mirrors the current flow (architecture → milestones → plans → features → stories/tasks) but makes each level a formal stage with its own skill loading.

### 4. User Picks Best Tool Per Stage — Design Principle (user, 2026-03-11)

The harness does NOT replace GSD, Superpowers, or other tools. The user chooses the best tool for each SDLC stage:

- **GSD** — long-form interview, research, planning phases
- **Superpowers** — TDD discipline, code review hard gates
- **Development Harness** — structured execution with language-specific agent dispatch
- **BMAD** (future) — agile ceremonies, sprint management, PRD creation
- **Gas Town** (future) — multi-agent scaling, persistent identity, concurrent coordination

The interop layer enables seamless transitions between tools at stage boundaries. No tool owns the full lifecycle — they compose.


## Superpowers Artifact Mapping

### Artifact Locations

Two artifact directories, produced by two different skills:

| Directory | Produced By | Contains |
|-----------|------------|----------|
| `docs/superpowers/specs/` | `/superpowers:brainstorming` | Design specs — requirements, architecture, components, constraints |
| `docs/superpowers/plans/` | `/superpowers:writing-plans` | Implementation plans — bite-sized TDD tasks with checkbox tracking |

### Plan Format

Plans follow a strict structure the interop skill must understand:

```
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development
> or superpowers:executing-plans to implement this plan.

**Goal:** [one sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [key technologies]

---

### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**
  [complete code block]

- [ ] **Step 2: Run test to verify it fails**
  Run: `exact command`
  Expected: FAIL with "specific error"

- [ ] **Step 3: Write minimal implementation**
  [complete code block]

- [ ] **Step 4: Run test to verify it passes**
  Run: `exact command`
  Expected: PASS

- [ ] **Step 5: Commit**
  `git commit -m "feat: specific feature"`
```

### Key Properties for Interop

- **Granularity**: Each step is 2-5 minutes, one action
- **Self-contained**: Complete code in plan, exact file paths, exact commands with expected output
- **TDD enforced**: Red-green-refactor cycle is structural, not optional
- **Checkbox tracking**: `- [ ]` / `- [x]` for progress state
- **Chunked review**: Plans use `## Chunk N: <name>` headings, each ≤1000 lines
- **Execution handoff**: Plans are designed for fresh subagent per task + two-stage review (spec compliance, then code quality)

### Harness Mapping

Each Superpowers "Task N" maps to a harness execution unit:
- Task's **Files** section → harness file impact summary
- Task's **Steps** → harness execution sequence within a single agent dispatch
- Task's checkbox state → harness task status (NOT STARTED / IN PROGRESS / COMPLETE)
- The plan's **Goal** + **Architecture** → harness discovery/plan artifact equivalent

The interop skill's `superpowers-artifact-mapping.md` reference must teach generic agents to:
1. Find plans in `docs/superpowers/plans/` and specs in `docs/superpowers/specs/`
2. Parse the Task N / Step N / checkbox structure
3. Map each Task to a harness dispatch unit
4. Track progress via checkbox state
5. Report results back by updating checkboxes and appending verification output


## Design Intent Preservation

### Critical: This Is Consolidation, Not Replacement

The development-harness was intentionally designed based on the SAM methodology (stateless-agent-methodology repo). It is NOT a stale copy of python3-development — it embodies specific SAM design principles that must be preserved during consolidation:

- **Stateless agents** — fresh context per agent, task file IS the complete prompt
- **Externalized memory** — all state in artifact files, not conversation
- **Single responsibility** — each agent does exactly one thing
- **Message passing** — agents communicate via artifacts, not shared context
- **Verification at boundaries** — every stage validates previous stage output
- **Deterministic backpressure** — always run tests/linters/static analysis, treat failures as ground truth
- **Independent verification** — producer and reviewer are structurally separate (Principle 3 from autonomous-loop-principles.md)

### python3-development Has Battle-Tested Backlog Integration

The python3-development plugin received incremental updates to integrate with the backlog system:

```
Backlog Skills (user-facing):
  /create-backlog-item  — intake: guided, quick, or autonomous modes
  /groom-backlog-item   — autonomous refinement: validity, fact-check, RT-ICA, root-cause
  /work-backlog-item    — bridges backlog → SAM planning → /add-new-feature

Backlog Pipeline:
  Intake → Triage → Grooming → Feasibility/Research → Ready to Implement
    │                                                        │
    └── adds related bugs/sub-tasks found during work ◄──────┘
                                                        (loop-back)
```

The grooming skill performs RT-ICA assessment, issue classification, and root-cause analysis before items reach the implementation pipeline. This front-loading aligns with SAM Principle 2 ("Front-Loading Reduces Runtime Human Gates").

### Autonomous Loop Principles to Preserve

From the SAM autonomous-loop-principles.md — 7 principles extracted from cross-framework analysis of BMAD, Gastown, GSD, Octocode, Ralph, and SAM:

1. **Structure Over Instruction** — gates must be structural (pipeline forces the check), not instructional
2. **Front-Loading Reduces Runtime Human Gates** — more context captured upfront = fewer interventions during execution
3. **AI Cannot Reliably Self-Evaluate** — producer and evaluator must be structurally separate
4. **Compression Is Architectural** — fixed output formats compress better than "please summarize"
5. **Autonomous Loop Control Requires Iteration-Aware State** — convergence tracking, oscillation detection, drift detection need cross-iteration state
6. **Parallelism Enables Independent Verification** — multiple agents checking different dimensions simultaneously
7. **Escalation Failure Paths Need More Compression** — failures need better human-readable summaries than successes

### Consolidation Rules

- Do NOT discard harness design decisions in favor of python3-development's working patterns without first checking whether the harness decision was intentional SAM alignment
- When the two systems diverge, document the divergence and its SAM design rationale before choosing which to keep
- The backlog integration from python3-development should be lifted into the harness as the upstream intake layer
- The harness's ARL human touchpoint model should be preserved — it provides the structured escalation that python3-development's backlog grooming feeds into


## Design Context

### Source of Truth

The python3-development + backlog integration is the battle-tested, working system. The development-harness was created as a SAM abstraction from python3-development but has received almost no updates since creation. All incremental fixes, backlog integration, and workflow refinements went into python3-development.

The harness should be rebuilt to match the working python3-development + backlog pipeline, then made language-agnostic — NOT the other way around.

### Current Working Pipeline (python3-development + backlog)

```
Backlog (upstream intake)
  ├── Inbound: ideas, bugs, feature requests
  ├── Triage and grooming
  ├── Feasibility and research — collects data on desired outcome
  │   and what needs to be known to achieve it
  └── "Ready to implement" handoff
        │
        ▼
python3-development (implementation lifecycle)
  ├── Architecture — works from backlog research data
  ├── Planning — task decomposition
  ├── Test design
  ├── Code implementation
  ├── Validation
  ├── Review
  └── Loop-back: related bugs/issues found during implementation
        are added back to backlog as related/sub-task items,
        then addressed after first pass completes
```

### Target Architecture

```
development-harness (process engine — language-agnostic)
  ├── Owns: workflow definitions, job dispatch, CI monitoring,
  │         agent spawning, concurrency, state management
  ├── Generic role-based agents (not per-language specialists)
  │   Each agent loads: stage workflow + domain skill(s) at dispatch time
  ├── Backlog integration (intake, triage, research, handoff)
  └── Interop skill for GSD .planning/ and Superpowers specs/

language plugins (knowledge providers — no process logic)
  ├── python3-development: skills, references, conventions, quality gates
  ├── future: typescript-development, embedded-development, etc.
  └── Each provides a language manifest mapping roles to skills
```

### Generic Agent Model

No specialist agents in language plugins. A small set of role-based generic agents in the harness receive:
1. A workflow stage definition (mermaid graph with steps + loops)
2. A cross-cutting SDLC stage skill (e.g., software-architecture-planning)
3. Domain skill(s) from the language plugin (e.g., python3-cli-design)
4. A task/artifact file (input from previous stage)
5. Quality gate commands (from language manifest)

### Interop Requirements

Single `/development-harness:interop` skill with references for:
- GSD `.planning/` directory — artifact mapping to harness stages
- Superpowers `docs/superpowers/specs/` — spec mapping to harness stages
- Handoff protocol — `.continuehere.md`, state recovery, cross-tool session continuity

Agents learn the mapping via loaded skill references — no format conversion step.

### External Tool Assessment

| Tool | Composability | Integration Priority |
|------|--------------|---------------------|
| GSD | Wave-based execution, `.planning/` state dir | High — currently used |
| Superpowers | Skill chaining, `docs/superpowers/specs/` | High — currently used |
| BMAD-METHOD | Modular YAML agents, phase-based workflows | Future |
| Gas Town | Multi-agent scaling, plugin dispatch, federation | Future |

### Naming Convention

Nestable `{domain}-{sdlc-stage}` pattern for skills across all language plugins. Research needed on conventional SDLC stage names (IEEE/ISO, SAFe) for the universal namespace.

## RT-ICA

RT-ICA: Development Harness Architecture Refactor
Goal: Establish development-harness as the universal process engine with pluggable language knowledge providers and external tool interop

Conditions:
1. SAM 7-stage pipeline design exists in development-harness | Status: AVAILABLE | Already defined in skills/workflows/
2. Language manifest schema exists | Status: AVAILABLE | At skills/development-harness/references/language-manifest-schema.md
3. python3-development agent/skill inventory | Status: AVAILABLE | 16 agents, 25+ skills documented
4. Conventional SDLC stage naming taxonomy | Status: MISSING | Need IEEE/ISO/SAFe research for universal namespace
5. GSD .planning/ artifact format specification | Status: DERIVABLE | Observable from /home/ubuntulinuxqa2/repos/get-shit-done/docs/USER-GUIDE.md and actual .planning/ directories
6. Superpowers spec/plan format specification | Status: AVAILABLE | Documented in groomed content (Superpowers Artifact Mapping section)
7. Generic agent dispatch mechanism | Status: MISSING | Design needed — how does a generic agent receive stage workflow + domain skills + task file at dispatch time
8. Backlog integration lift plan | Status: DERIVABLE | Current backlog skills in python3-development are documented; lift path to harness is design work
9. Cross-tool session continuity protocol | Status: MISSING | No existing design for handoff between GSD/Superpowers/harness mid-session
10. BMAD/Gas Town artifact formats | Status: AVAILABLE | Researched in brainstorming session (2026-03-11) but integration is future scope

Decision: APPROVED-WITH-GAPS
Missing:
- SDLC stage naming taxonomy (condition 4) — blocks skill naming convention
- Generic agent dispatch mechanism (condition 7) — core architectural decision
- Cross-tool session continuity protocol (condition 9) — needed for interop but can be deferred to phase 2
