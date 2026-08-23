<p align="center">
  <img src="./assets/hero.png" alt="Agent Orchestration" width="800" />
</p>

# Agent Orchestration

This plugin changes how Claude delegates work to sub-agents. Instead of writing vague "fix this" prompts, Claude constructs delegation prompts built on verified observations — telling agents WHERE the problem is, WHAT the success criteria are, and WHY it matters — while leaving HOW to solve it to the agent.

## Why Install This?

When Claude delegates work to sub-agents, the quality of that work depends entirely on the quality of the delegation prompt. Claude sometimes:

- Tells agents what solution to implement (prescribing HOW) rather than what outcome to achieve (defining WHAT)
- Passes assumptions stated as facts, causing agents to act on bad premises
- Repeats information agents can already see in CLAUDE.md, wasting their context
- Fixes one instance of a bug without checking whether the same pattern exists elsewhere
- Claims "done" after an agent returns without verifying the actual deliverable

This plugin makes delegation systematic and evidence-based.

## What You Get

### The WHERE / WHAT / WHY framework

Every delegation prompt is built around three questions:

**WHERE** — the problem location and scope boundaries

```text
Authentication module at src/auth/ — OAuth handlers specifically
```

**WHAT** — identification criteria and acceptance criteria

```text
OAuth redirect must return 200 status with valid session token
```

**WHY** — expected outcome, user requirement, business impact

```text
Users cannot log in with enterprise SSO accounts, blocking customer onboarding
```

Claude defines these three things. The agent decides HOW to achieve them.

### Pre-delegation verification checklist

Before dispatching any agent, Claude verifies:

- All claims in the prompt are labeled as observations, not assumptions
- Success criteria are observable and measurable
- Context includes only what the agent cannot find itself (not contents of CLAUDE.md, not project conventions already in scope)
- The task defines WHAT and WHY — not HOW

### Pattern expansion

When Claude finds a bug in one file, the plugin requires checking whether the same pattern exists elsewhere. A single instance is treated as evidence of a systemic pattern until proven otherwise.

### Parallel dispatch

When a task decomposes into independent subtasks, Claude dispatches agents in parallel using `TeamCreate`. Sequential execution of independent work requires a justification.

### Skills

| Skill | Purpose |
|---|---|
| `agent-orchestration` | Full scientific delegation framework — verification checklist, delegation template, anti-patterns, parallel dispatch patterns |
| `how-to-delegate` | 10-step preparation worksheet — guides through observations, success criteria, world-building context, agent selection, and pre-flight verification before constructing a delegation prompt |
| `delegate` | Decomposes a request into phases, dispatches each phase to its own sub-agent, and adjudicates the results — the WHERE/WHAT/WHY dispatch template with a phase-scoped task table and pre-send checklist |
| `orchestrating-swarms` | Patterns for large-scale parallel agent coordination — swarm spawning, task decomposition, agent pool management |

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install agent-orchestration@jamie-bitflight-skills
```

## Usage

The plugin is active automatically after installation. When Claude is about to delegate work, it applies the framework before constructing the agent prompt.

Invoke manually when you want Claude to use the full 10-step preparation worksheet:

```text
/agent-orchestration:how-to-delegate
```

Or decompose, dispatch, and adjudicate a request before delegating it:

```text
/agent-orchestration:delegate
```

## Example

**Without this plugin:**

```text
Claude → agent: "Fix the authentication bug in login.py.
                 Update the validation logic."
```

The agent receives a HOW, not a WHAT. It implements the prescribed solution without understanding the problem, and may solve the wrong thing.

**With this plugin:**

```text
Claude → agent:
  Your ROLE_TYPE is sub-agent.

  ECOSYSTEM CONTEXT:
  - Project: FastAPI application, Python 3.12, uv workspace
  - Auth module: src/auth/ — handlers for OAuth and session management

  TASK:
  Investigate and fix the authentication bug in src/auth/login.py.

  WHERE: src/auth/login.py — validation logic, reported around line 127

  WHAT:
  - OAuth login returns 200 with a valid session token
  - No 302 redirect to 404 on enterprise SSO accounts
  - All existing auth tests pass

  WHY:
  Users reported: "OAuth login redirects to 404" — enterprise SSO login
  is broken, blocking customer onboarding.

  Also check src/auth/signup.py and src/auth/reset_password.py for the
  same validation pattern — single-instance bugs are often systemic.

  SUCCESS CRITERIA:
  Write findings to .tmp/scratch/reports/auth-fix-YYYYMMDD.md
  Return: STATUS: DONE + path to report
```

The agent receives verified observations, clear success criteria, and autonomy to choose how to fix the problem.

## Requirements

- Claude Code v2.0+

## How It Works

The plugin loads behavioral instructions that Claude follows when orchestrating work:

- Decisions are based on verified observations, not assumptions
- Every delegation prompt defines success criteria the agent can verify independently
- Context passed to agents contains only what they cannot see themselves
- Single-instance bugs trigger a pattern audit across related files
- Parallel dispatch is the default for independent subtasks

---

> **The Ancient Woe**
>
> *The fool of a physician who applies leeches to thy forehead to cure a headache, entirely ignoring the rotting tooth that plagues thy jaw!*

> **The Bard's Decree**
>
> *"Cease thy shallow remedies! Dig beneath the soil, find the poisoned root of this affliction, and cure the disease, not merely the cough!"*
