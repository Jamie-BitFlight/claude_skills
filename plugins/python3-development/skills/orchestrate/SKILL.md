---
name: orchestrate
description: Use when orchestrating a Python development task via specialized agents. Activates on "build a Python CLI", "add a feature", "write tests", "refactor Python code", "debug Python", "code review", or any multi-agent Python workflow. Invoke as /orchestrate with a task description or alone to use conversation context.
argument-hint: '[task description]'
---

# Task

orchestrate in plugins/python3-development/skills/orchestrate/

If `orchestrate` is empty, derive the task from the conversation so far. If no task can be derived, ask the user to describe what they want built or changed before proceeding.

## Step 1 — Read the orchestration guide (MANDATORY)

Read `../python3-development/references/python-development-orchestration.md`.

Do not proceed to Step 2 until this file has been read. It contains agent selection criteria, workflow patterns, quality gates, and multi-agent chaining patterns you will need to fill in Step 2.

## Step 2 — Route to track

```mermaid
flowchart TD
    Q{"Does the task meet ANY of:<br>- user said 'add a feature', 'plan', or 'track'<br>- requires ≥ 2 agents in sequence<br>- spans multiple files/modules<br>- needs durable progress tracking across turns"}
    Q -->|"Yes"| SAM["SAM Track → Step 3A"]
    Q -->|"No — single focused task:<br>fix a bug, write tests for one file,<br>review code, one-shot refactor"| Direct["Direct Track → Step 3B"]
```

Then state aloud before the first Agent tool call:

```text
Task: <one sentence>
Track: SAM | Direct
Workflow pattern: <TDD | Feature Addition | Refactoring | Debugging | Code Review>
Agent chain: <AGENT1> → <AGENT2> → ...
```

If you cannot fill in workflow pattern and agent chain from the guide read in Step 1, go back and read it.

## Step 3A — SAM Track

```mermaid
flowchart TD
    P1["Phase 1 — Plan<br>Skill: /dh:add-new-feature<br>Args: task description<br>Produces: ~/.dh/projects/{slug}/plan/P{NNN}-{slug}.yaml"]
    P1 --> P1Q{"add-new-feature result?"}
    P1Q -->|"BLOCKED — plan-validator gate failed"| P1Blocked["Surface blocker to user<br>Await clarification<br>STOP"]
    P1Q -->|"PASS — task file produced"| P2
    P2["Phase 2 — Execute<br>Skill: /dh:implement-feature<br>Args: path to task file<br>Loop: sam ready → start-task → SubagentStop hook marks COMPLETE<br>Repeat until no tasks remain"]
    P2 --> P3["Phase 3 — Quality gates<br>Auto-invoked by implement-feature<br>Skill: /dh:complete-implementation<br>Runs: code review → feature verification → integration check<br>→ doc drift → doc update → context refinement → commit"]
    P3 --> Done(["DONE — changes committed"])
```

## Step 3B — Direct Track

Agent routing — delegate rather than implement:

- Python code → subagent_type="python3-development:python-cli-architect"
- Tests → subagent_type="python3-development:python-pytest-architect"
- Code review → subagent_type="python3-development:code-reviewer"
- Architecture design → subagent_type="python3-development:python-cli-design-spec"
- Task breakdown → subagent_type="dh:swarm-task-planner"
- Requirements → subagent_type="spec-analyst"
- Stdlib-only script → Skill(skill: "python3-development:stdlib-scripting")

Each delegation must include:

- Outcomes: what must be true when the agent is done
- Constraints: user requirements, compatibility, scope boundaries
- Known issues: error messages already in context (pass-through, not pre-gathered)
- File paths: where to start looking — not what you found there

Do NOT read source files before delegating. Agents search and read files for themselves — pass file paths, not file contents. Pre-gathering wastes orchestrator context and duplicates work the agent will do anyway.

Track is DONE when all agents in the stated chain have returned their outputs.
