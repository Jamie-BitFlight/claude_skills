---
name: foreman
title: Foreman
subtitle: Python asyncio runtime for semantic supervision of coding agents with TypeSafe AI's Jev
research_date: 2026-10-02
source_url: https://github.com/thruwire/foreman
github_repository: https://github.com/thruwire/foreman
version_at_research: 0.4.1 (commit e5d1aa45, 2026-09-28)
license: MIT License
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 0.4.1 (commit e5d1aa45, 2026-09-28)
  next_review: 2027-01-02
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: medium, Technical Architecture: medium, Installation & Usage: high, Limitations: high, Relevance: medium"
---

# Foreman

## Overview

Foreman is a native Python `asyncio` runtime that combines a coding agent loop with an independent supervisory loop. It watches software factory work by placing TypeSafe AI's Jev decision model above slower coding agents (Codex, OpenCode, or Hermes) to assess work quality, route decisions, and intervene in real-time. Foreman separates software engineering work from continuous semantic supervision without replacing the agent's reasoning or tool selection—only monitoring outputs and proposing directives based on probabilistic assessments of job completion, test sufficiency, worker health, and requirement satisfaction.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Coding agents are slow and stateful generative systems; monitoring their progress requires human polling or agent-native supervision that blocks forward progress | Foreman runs independent semantic supervision in a debounced observation loop while the worker subprocess remains active, allowing frequent lightweight assessments without stalling work |
| Hard to know when a stuck or off-track agent needs intervention or when work is genuinely complete | Pluggable responsibilities with Jev checks (implementation_complete, worker_stuck, work_off_track, requirements_satisfied, needs_verification, needs_human) that evaluate to probabilistic scores on bounded evidence |
| Integration of supervision with multiple coding agents requires rewriting the supervisor for each agent's protocol | Agent-agnostic supervision layer with pluggable worker backends (Codex App Server, OpenCode, Hermes) and a small Worker protocol that any agent can implement |
| Verification passes and human-facing decisions lack semantic grounding; factory decisions are opaque | Explicit routing of observations to Jev, configurable evidence providers, and deterministic policy that makes each directive traceable to threshold crossings and check scores |

---

## Key Features

### Semantic Supervision with Jev

- Sends bounded, structured observations to TypeSafe AI's Jev decision model via the official Python SDK (`typesafe-sdk`, `AsyncTypeSafeClient`, authenticated with `TYPESAFE_API_KEY`)
- Evaluates 10-11 built-in Jev checks (yes/no probabilities) in a single parallel request: `implementation_complete`, `requirements_satisfied`, `ready_to_finish`, `tests_sufficient`, `needs_verification`, `worker_stuck`, `work_off_track`, `meaningful_progress`, `agents_md_drift`, `needs_human`, and conditional `documentation_sufficient`
- All checks are sent to Jev in one parallel request within a configurable timeout (default: 10 seconds)
- Uses TypeSafe's `Noul` primitive (yes/no questions) evaluated independently and in parallel

### Pluggable Responsibility System

- Responsibilities own one or more Jev checks plus deterministic Python logic that proposes directives
- Each built-in responsibility (Completion, Verification, Worker Health, Repository Instructions, Human Escalation) can activate independently
- Directives ordered by safety-first policy: human escalation, iteration bounds, AGENTS.md drift detection, stuck/off-track workers, retry handling, completion, verification, continued work
- Thresholds declared per check in TOML definition files alongside instructions; defaults range from 0.65 to 0.80 depending on responsibility
- Custom responsibilities can be added via the `ResponsibilityRegistry` without changing the Jev adapter or runtime

### Worker Backend Abstraction

- Supports multiple coding-agent backends via pluggable adapter: `codex` (default, with Codex App Server for live steering), `opencode` (non-interactive), `hermes` (headless chat mode)
- Selected via `FOREMAN_WORKER_BACKEND` environment variable
- Codex App Server backend enables live steering—sending Jev-informed guidance into an in-flight Codex turn over its JSONL protocol (`turn/steer` message)
- Other backends degrade to stop/retry on interventions
- Worker protocol is small and agent-agnostic; new backends can implement it without modifying Foreman's observation or policy layers

### Evidence Collection Framework

- Built-in evidence providers deliver bounded, typed observations: worker activity, git status/diff, repository instructions, test summaries, verification results, lifecycle events, and prior decisions
- Optional command evidence: trusted CLI tools (pytest, linters, custom scripts) defined in central configuration (`~/.foreman/config.toml`), not repository code
- Evidence is collected by providers and selected by individual checks: omitting `evidence` in a check's TOML gives it all built-in providers; explicit `evidence` array selects only those named
- Commands run sequentially with repository root as working directory, bounded by timeout and output limits, results added to check context
- Checks with the same evidence selection are batched into one Jev call for efficiency

### Hook-Based Integration with Interactive Sessions

- `foreman hook` accepts one lifecycle event as JSON on stdin and outputs assistant-specific hook JSON, letting Foreman supervise interactive human-started sessions
- Client adapter selects protocol (currently `codex` adapter for Codex integration)
- Normalized event flow: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SessionEnd`
- Hook sessions stored globally under `~/.foreman/sessions/` with SHA256 hash of client + session ID to prevent path injection
- Codex plugin `foreman@thruwire` published in ThruWire marketplace for installation into Codex

### Persistent State and Inspection

- Each repository run stores state in `.foreman/runs/<run-id>/`: `state.json` (atomically replaced, typed recovery state) and `events.jsonl` (append-only timeline)
- CLI commands to list and inspect runs: `foreman runs --repo ./my-project`, `foreman inspect <run-id> --repo ./my-project`
- `.foreman/` directory is locally ignored (contains run state, not factory config)
- Event history retained and queryable for debugging; no production-grade durability guarantees

### Policy Directives

- Eight possible directives ordered by safety-first policy: `CONTINUE`, `START_WORKER`, `START_VERIFIER`, `STEER_WORKER`, `STOP_WORKER`, `RETRY_WORKER`, `FINISH`, `ESCALATE`
- A worker crossing off-track/stuck/drift thresholds is steered once (sending Jev-informed guidance); repeated high scores trigger stop/retry
- Transient Jev failures tolerated up to `FOREMAN_MAX_CONSECUTIVE_ASSESSMENT_FAILURES` (default: 3) without escalating the run
- Human escalation threshold: 0.80; off-track, stuck, drift, and requirements-not-satisfied thresholds: 0.75–0.80

### Deterministic Demo Mode

- `foreman demo --repo .` runs the complete runtime with deterministic mock worker and model implementations
- Requires no API key, network, external CLI, or external repository
- Exercises the same state persistence, event stream, responsibility routing, and terminal UI as a real run

---

## Technical Architecture

Foreman's architecture separates two concurrent loops running in native Python `asyncio`:

**CODING AGENT LOOP**: Worker (reason → tool → observe → edit → test) with subprocess lifecycle.

**FOREMAN LOOP**: Observation (watch → assess → decide → intervene) with independent debounced timing.

Both loops run simultaneously. Worker output and lifecycle events flow into the observation loop via bounded event queues, while the worker subprocess remains active. The observation loop is debounced with a minimum assessment interval (default: 5 seconds) and periodic assessment during quiet work (default: 30 seconds).

### Core Components

**Factory** (`FactoryConfig`, runtime orchestrator): Manages worker lifecycle, event queues, observation bounds (diff size, output tails, event history), iteration/retry/timeout limits. Hosts the worker backends, responsibility registry, and policy arbiter.

**Worker** (protocol interface): Encapsulates interaction with a coding agent. Current implementations: `CodexAppServerWorker` (Codex via JSONL), `OpenCodeWorker` (non-interactive), `HermesWorker` (headless chat). Each streams output, reports status, accepts stop/steer commands.

**Observation** (bounded evidence collection): Collects worker state, git diff, test results, command evidence, lifecycle history. Size-bounded (20,000 char diff, 12,000 per output tail, 30 events default, 10 worker history by default). Repository instructions (`AGENTS.md` or `AGENTS.override.md`) read per observation, included in transient Jev request, never persisted.

**Jev Integration** (`AsyncTypeSafeClient`): Calls TypeSafe API with structured state (job, observation, policy context) and question set (10–11 `Noul` checks). Returns probabilistic scores per check. Retries on 429/5xx within assessment timeout.

**Responsibility** (pluggable checks + logic): Base class with typed Jev check IDs, decision methods, TOML routing/configuration. Built-in: `CompletionResponsibility`, `VerificationResponsibility`, `WorkerHealthResponsibility`, `RepositoryInstructionsResponsibility`, `HumanEscalationResponsibility`. New responsibilities add checks to one Jev request without modifying adapter or loop.

**Policy Arbiter** (deterministic decision selection): Evaluates all active responsibility proposals in safety-first order. Returns one selected directive (e.g., `STOP_WORKER`, `STEER_WORKER`, `FINISH`). Policy logic is Python code, not Jev output; Jev only scores probabilities.

**Persistence** (`state.json`, `events.jsonl`): State atomic swap; events append-only. Recovery parses state file and resumes from last known position. Event stream immutable, searchable for debugging.

### Evidence Provider Architecture

Built-in providers return structured observations; command providers invoke trusted external CLI tools:

- Providers return `ProviderResult` with evidence ID, content, metadata (timing, exit codes)
- `check.evidence` array selects which providers feed that check
- Checks with identical evidence selections batch into one Jev call
- Different selections require separate Jev calls
- Commands run sequentially in repository root, bounded by timeout and output limits

### Data Flow

1. Worker emits event (output chunk, exit, status change)
2. Factory queues event, signals observation loop
3. Observation loop debounced (min 5s, max 30s during quiet)
4. Collects bounded evidence from all providers, reads AGENTS.md
5. Calls Jev once with all active responsibility checks
6. Jev returns check scores (0–1 probabilities)
7. Each responsibility evaluates scores against thresholds, proposes directive(s)
8. Policy arbiter selects one directive in safety-first order
9. Factory executes directive (CONTINUE, STEER, STOP, RETRY, START_VERIFIER, FINISH, ESCALATE)
10. Event appended to timeline, state atomically replaced
11. Loop continues

---

## Installation & Usage

### Installation

Install from published package:

```bash
python -m pip install foreman-core
```

The distribution name is `foreman-core`; it installs the `foreman` command and the `foreman` Python package.

For development from checkout:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[dev]'
cp .env.example .env
```

Add your TypeSafe API key to `.env`:

```dotenv
TYPESAFE_API_KEY=your-key-here
```

### Running a Job

```bash
foreman run \
  --repo ./my-project \
  --job "Add rate limiting to the API and make sure it is properly tested."
```

Terminal output shows worker lifecycle messages and grouped assessments, making clear when the agent is active versus when Foreman is independently watching.

### Configuring Evidence Commands

Define trusted commands in central config (`~/.foreman/config.toml`):

```toml
[[evidence.commands]]
id = "pytest"
command = ["python", "-m", "pytest", "-q"]
timeout_seconds = 120
```

Reference in a responsibility definition's check:

```toml
[checks.tests_sufficient]
instructions = """
Does the selected evidence show sufficient relevant coverage and passing verification?
"""
min_threshold = 0.75
evidence = ["worker", "git.diff", "command.pytest"]
```

### Demo Mode (No API Key Required)

```bash
foreman demo --repo .
```

Runs with deterministic mock implementations; no TypeSafe credentials, network, or external CLI needed.

### Inspection

```bash
foreman runs --repo ./my-project                    # List all runs
foreman inspect <run-id> --repo ./my-project       # View run state and timeline
```

### Hook Integration with Codex

Install Codex plugin:

```bash
codex plugin marketplace add thruwire/marketplace
codex plugin add foreman@thruwire
```

Plugin forwards lifecycle events to `foreman hook --client codex`, allowing Foreman to supervise interactive Codex sessions in addition to autonomous `foreman run` jobs.

---

## Key Requirements

- **Python 3.11+** (tested with 3.12)
- **TypeSafe API key** for real runs (demo and tests do not require it)
- **Coding agent CLI**: one of Codex (default), OpenCode, or Hermes on `PATH` with authentication configured
- For Codex with live steering: Codex CLI version supporting `codex app-server` subcommand

---

## Limitations

- Jev assessment accuracy for this use case is unproven; scores need real-world calibration
- False positives can stop useful workers; false negatives allow bad work to continue
- Repository observations are incomplete and bounded (no full file inspection)
- Coding agent remains responsible for tool selection and software-engineering reasoning
- Codex App Server is experimental; its protocol may change between CLI versions
- Runs one coding worker at a time (concurrent workers listed as future work)
- Local execution is not isolated (workers run with user's permissions)
- Persistence useful for inspection, not production-grade durable execution
- No formal proof of correctness; verifier reports evidence through same observation channel as work

---

## Relevance to Claude Code Development

### Applications

- **Autonomous agent supervision with policy-driven decision making** -> `AGENTS.md`
  - Term: `orchestration`
  - Today: "dependency between its parts; load `agent-orchestration:parallel-work` for fan-out shapes and"
  - Change: none — AGENTS.md already routes fan-out and worker close-out through `agent-orchestration`; Foreman's responsibility-registry and policy-arbiter pattern supervises one live worker, which that guidance does not address, and no edit is warranted without a concrete supervision requirement

- **Worker lifecycle management and recovery from stuck states** -> `rules/fix-delegation-discipline.md`
  - Term: `stuck`
  - Today: "Stuck after 3 cycles | Same failure persists after 3 research-fix iterations"
  - Change: none — rules/fix-delegation-discipline.md already covers it with a fixed 3-cycle escalation to `/scientific-method:scientific-thinking`; Foreman's live stop/retry detection of a stuck worker is a different mechanism (runtime monitoring vs post-hoc cycle count)

- **Semantic assessment of work progress and code quality** -> `rules/review-and-correction-discipline.md`
  - Term: `assessment`
  - Today: "assessment. Checks substance: does the prose instruct the agent to do the right thing across its"
  - Change: none — out of scope (the repo's "assessment" is a review gate over agent prose, not live scoring of a running worker; no shared code path with Foreman's verifier)

### Integration Opportunities

- **TypeSafe Jev integration for probabilistic policy decisions** -> `plugins/development-harness/skills/root-cause-tracing-process/SKILL.md`
  - Term: `probabilistic`
  - Today: "Do not require a probabilistic cause to fail on every run. Choose the hypothesis form before"
  - Change: none — out of scope (this line uses "probabilistic" for a debugging hypothesis form, unrelated to Jev scoring; Jev is an external service, so integration would require the TypeSafe SDK and an authenticated client plus a hook into the development-harness agent loop)

---

## References

- [Foreman README](https://github.com/thruwire/foreman/blob/main/README.md) (revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman — Runtime and event flow](https://github.com/thruwire/foreman/blob/main/docs/runtime.md) (H1 "Runtime and event flow"; sections "Components" and "One assessment cycle"; revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman — Coding-assistant hooks and attached workers](https://github.com/thruwire/foreman/blob/main/docs/hooks.md) (revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman — Live steering](https://github.com/thruwire/foreman/blob/main/docs/steering.md) (revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman — Responsibility configuration and routing](https://github.com/thruwire/foreman/blob/main/docs/routing.md) (revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman — Evidence providers](https://github.com/thruwire/foreman/blob/main/docs/evidence.md) (revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman src/foreman/config.py](https://github.com/thruwire/foreman/blob/main/src/foreman/config.py) (lines 54-55, 75-76, 80-81: periodic assessment 30.0 s, Jev timeout 10.0 s, `diff_limit` 20_000, `output_limit` 12_000, `event_history_limit` 30, `worker_history_limit` 10; read from clone, revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman src/foreman/workers/codex_app_server.py](https://github.com/thruwire/foreman/blob/main/src/foreman/workers/codex_app_server.py) (lines 327 and 403: `turn/start`, `turn/steer`; read from clone, revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman src/foreman/hooks.py](https://github.com/thruwire/foreman/blob/main/src/foreman/hooks.py) (line 158: `hashlib.sha256(identity.encode("utf-8")).hexdigest()`; read from clone, revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman src/foreman/responsibilities/definitions/*.toml](https://github.com/thruwire/foreman/tree/main/src/foreman/responsibilities/definitions) (`min_threshold` values 0.65 to 0.80 and `routing_threshold` 0.70; read from clone, revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [Foreman LICENSE (MIT)](https://github.com/thruwire/foreman/blob/main/LICENSE) (revision 0.4.1 (commit e5d1aa45, 2026-09-28); accessed 2026-10-03)
- [TypeSafe AI Jev Documentation](https://docs.typesafe.ai/primitives) (referenced in Foreman docs, link noted 2026-10-02; page itself not fetched — accessed 2026-10-02 only as a reference)
- [TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python) (referenced in Foreman docs, link noted 2026-10-02; page itself not fetched — accessed 2026-10-02 only as a reference)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [AutoResearchClaw](./AutoResearchClaw.md) | agent-frameworks | shares asyncio-based worker coordination and evidence collection patterns |
| [gitagent](./gitagent.md) | agent-frameworks | implements agent supervision with orchestration and backend abstraction |
| [Trellis](./Trellis.md) | agent-frameworks | orchestrates multiple agent backends (Codex/OpenCode/Hermes) like foreman's worker pool |
| [flue](./flue.md) | agent-frameworks | shares worker backend abstraction and asyncio-based event processing |
| [omnigent](./omnigent.md) | agent-frameworks | provides multi-agent orchestration with verification patterns similar to foreman |
| [everything-claude-code](./everything-claude-code.md) | agent-frameworks | coordinates Claude Code sessions with evidence and backend abstraction |
| [claude-code-harness](./claude-code-harness.md) | agent-frameworks | supervises agent execution with evidence collection and policy directives |
| [ruflo](./ruflo.md) | agent-frameworks | uses async worker pattern with backend abstraction and orchestration |
