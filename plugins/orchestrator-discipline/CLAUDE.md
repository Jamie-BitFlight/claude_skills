# Orchestrator Context Window Discipline

These rules enforce delegation discipline for the orchestrator role. The orchestrator's context window is a shared, finite resource across the entire session. Agents get fresh context per task — the orchestrator does not.

---

## Context Window Read Constraints

**ORCHESTRATOR reads — PERMITTED**:

- Task status (TaskList, TaskGet) for routing decisions
- Agent output artifacts to verify after delegation
- Backlog items (.claude/backlog/ per-item files), plan files, skill/agent config files, CLAUDE.md
- Files you will Edit or Write in this same turn

**ORCHESTRATOR reads — NEVER** (hard constraint, no exceptions):

- Source code files (`.py`, `.js`, `.ts`, `.go`, `.rs`, `.rb`, `.java`) you will not edit this turn
- Config files (`.toml`, `.yaml`, `.yml`, `.json`) you will not edit this turn
- Test files
- Output from diagnostic commands (`ty check`, `ruff check`, `mypy`, `pytest`, `eslint`, `cargo check`)
- Agent `.output` files or JSONL transcripts — use the completion notification summary instead
- `TaskOutput` with `block=false` on a running agent — the completion notification arrives automatically

**Falsifiable test before every Read/Grep/Bash on a source or config file**:

> "Will I Edit or Write this file in this turn?" If NO — pass the path to an agent instead.

---

## Delegation Constraints

Prompt construction: `agent-orchestration:delegate`. This file governs what the orchestrator itself may read and run.

---

## Investigation Escalation Anti-Pattern

A validated failure mode where the orchestrator progressively reads more files, each justified by the previous read's findings, ending in self-implementation instead of delegation.

**Pattern sequence**:

1. "Let me check the current state" — seemingly legitimate baseline
2. "That changed things, let me verify" — scope creep from result
3. "Now I need to understand the pattern" — active investigation
4. "This is simple enough to do myself" — delegation bypass

```mermaid
flowchart TD
    Start([Orchestrator encounters task]) --> Q1{Need to understand current state?}
    Q1 -->|Yes| Delegate1["Delegate to Explore agent:<br>'Run [command] and report summary'"]
    Q1 -->|No| Delegate2[Delegate implementation to specialist agent]
    Delegate1 --> Receive[Receive agent summary]
    Receive --> Q2{Scope changed from original?}
    Q2 -->|Yes| AskUser[Present updated scope to user]
    Q2 -->|No| Delegate2
    AskUser --> Delegate2
    Delegate2 --> Verify[Spot-check agent output after completion]

    Q1 -.->|ANTI-PATTERN| SelfRead["Read files yourself<br>Run diagnostics yourself<br>Investigate patterns yourself"]
    SelfRead -.->|Leads to| SelfImpl["Plan to self-implement<br>'No delegation needed'"]
```

**Trigger signal**: 3+ Read/Grep/Bash calls on source files without an intervening Edit/Write or Agent delegation.

**Response when triggered**: STOP. Write the file paths and observations gathered so far into a delegation prompt. Do not read one more file. Delegate.

---

## Agent Output Polling Anti-Pattern

A variant of investigation escalation where the orchestrator reads a running agent's output file mid-execution, rationalizing it as "checking progress." Same root cause — orchestrator reads instead of waiting or delegating.

**Observed in**: Session 77509a5e (2026-02-19, dasel plugin creation).

**Why polling is never valid**: The agent completion notification arrives automatically. There is no signal gap that polling fills. Raw agent transcripts are JSONL with full message payloads — enormous context cost for zero information value.

**Prohibited operations**:

- `TaskOutput` with `block=false` on a **running** agent
- `Read` on any `.output` file or agent JSONL transcript

**Rationalization phrase** (trigger signal, not justification):

> "I'm just checking progress" / "Let me see how the agent is doing" / "Let me peek at the current state"

**Correct workflow**:

```mermaid
flowchart TD
    Start([Background agent launched]) --> Wait[Continue other work]
    Wait --> Notify[Receive automatic completion notification]
    Notify --> Q1{Notification summary sufficient?}
    Q1 -->|Yes| Done[Proceed — no reads needed]
    Q1 -->|No| Delegate["Delegate focused reader agent:<br>'Summarize [output path] focusing on [aspect]. 5 sentences max.'"]
    Delegate --> Done

    Start -.->|ANTI-PATTERN| Poll["Call TaskOutput with block=false<br>Read .output file directly<br>Rationalization: 'I'm just checking progress'"]
    Poll -.->|Result| Waste["Thousands of tokens of JSONL transcript<br>consumed for zero information value"]
```

**Connection**: Investigation escalation reads source files instead of delegating. Agent output polling reads agent transcripts instead of waiting. Both patterns share the identical fix: stop reading, use the delegation channel.

---

## Diagnostic Commands

The orchestrator MUST NOT run diagnostic commands that produce large output directly into its context window. These commands should be delegated to an Explore agent or specialist.

**Commands that must be delegated** (not run directly by the orchestrator):

- `ty check`, `ruff check`, `mypy`, `pyright`, `basedpyright`, `pylint`
- `pytest`, `pre-commit run`, `prek run`
- `eslint`, `tsc --noEmit`, `cargo check`, `cargo clippy`, `go vet`

**Exception**: Post-edit verification of a single file you just modified. Scope the check to that file only — never the entire codebase.

**Correct delegation pattern**:

```text
Delegate to Explore agent:
"Run [diagnostic command] and report:
 - Total count by diagnostic category
 - Affected file paths
 - Representative example of each category
 3 sentences maximum."
```

---

## Epistemic Identity Scope

When operating as orchestrator, "use tools to verify" applies to task-routing information only:

- Skill documentation, backlog items (.claude/backlog/ per-item files), agent configurations, CLAUDE.md — verify directly
- Source code, test files, diagnostic output — delegate to agents with fresh context

The verification imperative does not override the delegation constraint. Investigation is not the orchestrator's job.
