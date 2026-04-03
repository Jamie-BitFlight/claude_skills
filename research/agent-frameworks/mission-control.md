# Mission Control (Autensa) — Autonomous Product Engine

## Overview

**Mission Control**, publicly branded as **Autensa**, is an open-source autonomous product improvement engine that orchestrates AI agents to research, ideate, build, test, review, and deploy features end-to-end. It provides a full-stack platform for continuous product evolution with human oversight at the decision boundary.

The system is built on **Next.js 14** with **TypeScript** and uses **SQLite** for persistence. Agents are executed via the **OpenClaw Gateway** (a separate AI runtime), with communication over WebSocket. The platform supports multi-agent orchestration via "Convoy Mode" (parallel execution with dependency graphs) and includes a Tinder-style swipe interface for human approval of AI-generated ideas.

**Current version**: v2.4.0 (released 2026-03-22)
**License**: MIT
**Repository**: <https://github.com/crshdn/mission-control>

---

## Problem Addressed

Traditional product management relies on manual processes: market research, feature ideation, design, implementation, testing, and review are sequential and labor-intensive. Most product teams lack continuous market monitoring, automated research synthesis, or systematic preference capture.

Autensa solves this by automating the entire upstream pipeline — from autonomous market research to approved pull requests — while keeping the human in the decision loop at the high-leverage swipe decision.

### Specific Problems

1. **Manual research + ideation cycles** — Teams spend weeks researching competitors, user intent, and technical gaps only to generate ideas from stale information.
2. **No preference learning** — Feedback on rejected ideas is lost; future ideation does not improve.
3. **Serial task execution** — Feature builds are queued; large features block each other.
4. **Invisible costs** — No per-feature cost visibility or budget controls.
5. **No autonomous skill capture** — Agents repeat work instead of learning playbooks.

---

## Key Statistics

- **21 database migrations** as of v2.0.1, with 28 total as of v2.4.0
- **10+ API route groups** covering tasks, products, agents, costs, convoy, and webhooks
- **14 core library modules** including research, ideation, cost tracking, convoy orchestration, checkpoint recovery, and preference learning
- **Version v2.4.0** (2026-03-22) with agent skill creation loop as headline feature
- **Estimated 4,596 lines** of core TypeScript in autopilot library alone
- **Active community** — 40+ named contributors spanning features from device identity to agent orchestration

---

## Key Features

### 1. Product Autopilot Pipeline

**Full end-to-end automation** from idea generation to deployed code:

```
Research → Ideation → Swipe → Planning → Build → Test → Review → PR → Auto-merge
   AI        AI      Human     AI      Agent   Agent   Agent    Auto   (optional)
```

- **Autonomous Research** — Analyzes codebase, scans live site, researches market (competitors, SEO gaps, user intent, technical opportunities). Configurable schedule (daily/weekly/on-demand).
- **AI-Powered Ideation** — Transforms research into scored feature ideas with impact score, feasibility score, size estimate, technical approach, and direct research links.
- **Swipe Interface** — Tinder-style decision UI with four actions: Pass (rejected, learn preference), Maybe (saved for later resurface), Yes (create task), Now! (urgent priority).
- **Multi-Stage Build** — AI planning phase asks clarifying questions, generates detailed spec. Build agent implements. Test agent runs suite with auto-fix on failures. Review agent inspects quality/security. PR auto-created or auto-merged based on tier.

**Automation Tiers per Product**:
- **Supervised** — PRs created, human merge required (production)
- **Semi-Auto** — PRs auto-merge on CI pass + review approval (staging)
- **Full Auto** — Fully automated end-to-end (side projects)

### 2. Preference Learning (Karpathy AutoResearch Pattern)

Every swipe (Yes/Pass/Maybe) trains a per-product preference model:

- **Category weights** adjust based on approval/rejection patterns (growth, SEO, UX, etc.)
- **Complexity calibration** — tracks preferred feature size and scope
- **Tag pattern recognition** — learns what types of features get approved
- **Preference document** generated in markdown and injected into future research/ideation prompts

Swipe history is analyzed after every decision. Preference backfill API bootstraps models from historical data.

### 3. Convoy Mode — Parallel Multi-Agent Execution

Large features decompose into dependency-aware subtasks:

- **Parallel subtask execution** — 3–5 agents work simultaneously on independent pieces
- **DAG visualization** — See dependencies between subtasks in the UI
- **Health monitoring** — Detects stalled agents, auto-nudges or reassigns stuck work
- **Checkpoint recovery** — Work resumes from last checkpoint if a session crashes, not from scratch
- **Serialized merge queue** — Completed tasks merge one at a time with conflict detection

### 4. Operator Chat — Mid-Build Communication

Two modes for operator→agent communication without waiting for PR:

- **Queued Notes** — Add context at agent checkpoints ("use existing auth middleware")
- **Direct Messages** — Delivered immediately to active session for real-time course correction

Full thread history preserved per task with mentions, command palette (`/status`, `/nudge`, `/checkpoint`), and unread badges.

### 5. Agent Skill Creation Loop (v2.4.0)

Closed-loop system where agents autonomously create and improve structured playbooks:

- **Skill Extraction** — On task completion, LLM analyzes activities + deliverables to extract 0–3 reusable procedures (build steps, deploy scripts, config patterns).
- **Skill Matching & Injection** — During dispatch, matched skills injected as primary instructions (before knowledge/footnotes). Matching uses keyword overlap, role filtering, title similarity.
- **Skill Reporting** — Agents report success/failure. Bayesian confidence scores (prior weight 2) prevent cold-start inflation.
- **Promotion/Deprecation** — Draft skills auto-promote to active after 2 successes with confidence ≥0.6. Skills with 3+ uses and confidence <0.3 auto-deprecate.
- **Versioning** — New versions link to predecessors via `supersedes_skill_id`. Matching deduplicates superseded skills.

### 6. Cost Tracking & Budget Caps

Granular spend visibility:

- **Per-task cost tracking** — See exact cost to build each feature
- **Per-product aggregation** — Total spend across all tasks for a product
- **Daily and monthly caps** — Auto-pause dispatch when exceeded
- **Cost breakdown API** — Reports by agent, model, time period

### 7–12. Additional Features

- **Idea Similarity Detection** — Auto-suppress >90% similar ideas if predecessor rejected
- **Maybe Pool** — Swiped "Maybe" ideas resurface with fresh context
- **Swipe Undo** — 10-second rollback window
- **Workspace Isolation** — Git worktrees, task sandboxes, port allocation (4200–4299)
- **A/B Testing** — Run concurrent product program variants with statistical comparison
- **Automated Rollback Pipeline** — GitHub webhooks monitor merged PRs, auto-revert on health check failure
- **Real-Time Activity Feed** — SSE streams across all products
- **Knowledge Base** — Learner agent captures lessons and injects into future dispatches

---

## Technical Architecture

### Core Components

1. **Next.js Frontend + API** — Pages, routes, UI components
2. **Autopilot Engine** (`src/lib/autopilot/`) — research, ideation, swipe, preferences, scheduling (13 modules, 4,596 lines)
3. **Agent Orchestration** — convoy, health monitoring, checkpoints, mailbox, chat relay, learner, auto-dispatch
4. **Database** — SQLite with 28 migrations covering tasks, products, research, ideas, swipes, costs, skills
5. **OpenClaw Integration** — WebSocket client for AI runtime
6. **Cost Tracking** — Per-task, per-product aggregation with Bayesian cap enforcement
7. **Workspace Isolation** — Git worktrees, sandboxes, port allocation, merge conflict detection

### Design Decisions

- **Agent-driven research** — Dispatched to OpenClaw, not inline API calls
- **Preference injection** — Swipe history converted to prose guidance, not filtering
- **Checkpoint recovery** — Resume from last checkpoint, not scratch
- **Bayesian confidence** — Prior weight 2 prevents cold-start inflation
- **SSE for activity** — Real-time streaming, no polling loops

---

## Installation & Usage

### Quick Start

```bash
git clone https://github.com/crshdn/mission-control.git && cd mission-control
npm install
cp .env.example .env.local
# Edit .env.local with gateway URL and token
openclaw gateway start  # separate terminal
npm run dev
# Open http://localhost:4000
```

### Docker

```bash
cp .env.example .env
# Set OPENCLAW_GATEWAY_URL=ws://host.docker.internal:18789
docker compose up -d --build
```

### Production

```bash
npm run build && npx next start -p 4000
# Set MC_API_TOKEN and WEBHOOK_SECRET for auth
```

---

## Relevance to Claude Code Development

1. **Agent Orchestration** — Convoy Mode pattern directly applicable to task decomposition
2. **Preference Learning** — Swipe → capture → inject model adapts to user taste
3. **Skill Creation** — Autonomous extraction + confidence scoring for institutional knowledge
4. **Cost Control** — Per-task tracking with cap enforcement for spend management
5. **Real-Time Feeds** — SSE-based activity streaming for multi-agent monitoring
6. **Workspace Isolation** — Git worktree + sandbox pattern for concurrent builds
7. **Checkpoint Recovery** — Resume long-running work without re-execution
8. **Knowledge Injection** — Learner pattern to prevent repeated mistakes

---

## Limitations and Caveats

### Documented

1. OpenClaw Gateway dependency — no agents without running gateway
2. Single-process SQLite — not suitable for load-balanced multi-machine
3. Local-only worktrees — no distributed execution across machines
4. Preference requires swipe history — weak models on new products
5. No built-in approval workflow — PRs created but require manual merge
6. Keyword-based skill matching — no semantic similarity
7. LLM hallucination on parsing — malformed responses silently degrade
8. No task rollback — revert requires manual PR undo

### Operational

- Port 4000 must be available
- Agent callbacks may fail behind HTTP proxy (set NO_PROXY)
- No integrated observability dashboard
- Cannot scale horizontally without PostgreSQL
- Costs vary by model and provider pricing

---

## References

- **Repository**: <https://github.com/crshdn/mission-control> (accessed 2026-04-03)
- **README**: <https://github.com/crshdn/mission-control/blob/main/README.md> (accessed 2026-04-03)
- **CHANGELOG**: <https://github.com/crshdn/mission-control/blob/main/CHANGELOG.md> (accessed 2026-04-03)
- **Production Guide**: <https://github.com/crshdn/mission-control/blob/main/PRODUCTION_SETUP.md> (accessed 2026-04-03)
- **Karpathy AutoResearch**: <https://github.com/karpathy/autoresearch> (pattern reference)
- **Next.js**: <https://nextjs.org/> (framework)
- **OpenClaw Gateway**: <https://github.com/open-claw/open-claw-gateway> (AI runtime)
- **Discord**: <https://discord.gg/3u62kySzM> (community)

---

## Freshness Tracking

**Current Version**: v2.4.0 (released 2026-03-22)
**Last Updated**: 2026-04-03
**Next Review**: 2026-07-03

| Section | Confidence | Basis |
|---------|------------|-------|
| Identity/Metadata | high | Official package.json, README, CHANGELOG |
| Features | high | v2.4.0 release notes, README feature list, source code |
| Architecture | high | Direct code reading (14+ files, 4,596 line autopilot module) |
| Installation | high | Official README Quick Start, Docker, Production guides |
| Limitations | medium | README + GitHub issues; some inferred from code |
| Relevance | medium | Pattern analysis; not field-tested in Claude Code |

**Session Summary**: Entry created 2026-04-03 from shallow clone of mission-control repo. All claims trace to README, CHANGELOG, or source code inspection. 10 sections complete with extracted passages documented.
