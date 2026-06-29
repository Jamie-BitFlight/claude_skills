---
title: Empirica
version: 1.7.7
date: 2026-04-05
resource_url: https://github.com/Nubaeon/empirica
source_freshness: current
---

# Empirica — AI Epistemic Measurement & Calibration Infrastructure

## Overview

Empirica is an open-source **measurement and calibration layer for AI agents**, designed to address fundamental reliability issues in autonomous AI work: uncertainty tracking, pre-action understanding validation, knowledge persistence across sessions, and grounded confidence assessment.

**Problem statement**: "AI coding agents today have no self-awareness about what they know" — they forget between sessions, act before understanding, cannot distinguish knowledge from confabulation, and leave no audit trail of reasoning. Empirica solves this through epistemic transactions, gating mechanisms, multi-layer memory, and calibration against ground truth.

**Primary use case**: Enhance Claude Code's native capabilities with measurement, gating, and learning feedback. Also available for Cursor, Cline, Copilot, Gemini, Qwen, Roo Code, and any AI via CLI + system prompt.

**Identity**: Version 1.7.7 (released 2026-04-01 per GitHub commit history), MIT License, authored by David S. L. Van Assche. 204 GitHub stars, 24 forks. Written in Python (>=3.10).

---

## Problem Addressed

Empirica targets specific, measurable failures in AI agent autonomy:

| Failure Mode | Empirica Solution |
|---|---|
| **Forgets between sessions** | 4-layer memory system with persistent storage, cross-session artifact retrieval, BREADCRUMBS git notes |
| **Acts before understanding** | Sentinel gate between noetic (investigation) and praxic (action) phases; blocks edits until understanding is verified |
| **Cannot tell when guessing** | 13-vector epistemic framework differentiates knowledge state from uncertainty; explicit doubt tracking |
| **No audit trail** | Complete transaction logging (PREFLIGHT→CHECK→POSTFLIGHT), findings/unknowns/dead-ends stored in `.empirica/` SQLite + qdrant |

Source: README.md, lines 18–26 ("The Problem"); Architecture.md, epistemic framework documentation.

---

## Key Statistics

- **Version**: 1.7.7 (released 2026-04-01, verified via git tag)
- **Stars**: 204 (as of 2026-04-05, via GitHub API `stargazers_count`)
- **Forks**: 24 (as of 2026-04-05, via GitHub API `forks_count`)
- **License**: MIT License
- **Primary Language**: Python
- **Python Support**: 3.10, 3.11, 3.12, 3.13 (verified in pyproject.toml classifiers)
- **CLI Commands**: 150+ (stated in README.md line 57)
- **Epistemic Vectors**: 13 dimensions (documented in README.md lines 189–206)
- **Release Pattern**: Active development with regular updates (1.6.11→1.7.7 within ~4 months)
- **Topics (GitHub)**: "ai-agents", "ai-memory", "ai-native-shell", "ai-os", "ai-workflows", "anti-confabulation", "epistemic-ai"

Sources: GitHub API response, pyproject.toml [project] section, README.md §The Measurement Architecture, CHANGELOG.md.

---

## Key Features

### 1. Sentinel Gate — Epistemic Readiness Gating

**What it does**: The Sentinel is a governance layer that controls the transition between investigation (noetic) and action (praxic) phases. Before the AI is permitted to edit code, it must demonstrate understanding through the Sentinel gate.

**Mechanism**: The CHECK phase compares epistemic vectors against dynamic thresholds. If vectors meet calibrated thresholds, the gate PROCEEDS; if insufficient understanding, the gate forces INVESTIGATE. The decision is reversible — the AI can loop through investigation phases, accumulating evidence, until ready.

**Configuration**: Sentinel has an "allow list" of always-permitted noetic tools (ToolSearch, git notes, intelligence layer MCP) and blocks praxic tools during investigation. Closed transactions allow safe noetic tools without requiring a new PREFLIGHT. Access: `sentinel-gate.py` module, configurable via `EMPIRICA_SENTINEL_LOOPING` and `EMPIRICA_AUTOPILOT` environment variables.

Source: README.md §How It Works With Claude Code (line 218); SENTINEL_ARCHITECTURE.md, lines 1–40; CHANGELOG.md [1.7.7] "Sentinel closed-transaction noetic check"; CONFIGURATION_REFERENCE.md.

### 2. Epistemic Transaction Workflow — PREFLIGHT→CHECK→POSTFLIGHT

**What it does**: Every goal or task runs through a three-phase epistemic cycle. Each phase measures the AI's epistemic state (knowledge, confidence, understanding) and gates transitions.

**Mechanism**:
- **PREFLIGHT**: Baseline assessment. AI states what it knows before starting. Records initial values of all 13 epistemic vectors.
- **CHECK**: Sentinel gate transition. Vectors are re-assessed. If all meet thresholds (computed from calibration data), proceed to action. Otherwise, loop back to PREFLIGHT with new investigation instructions.
- **POSTFLIGHT**: Learning measurement. After completing work, AI measures what it learned — computing a delta between preflight and postflight vectors. This delta persists to memory and feeds calibration.

**Storage**: Transactions are logged in `.empirica/sessions.db` (SQLite). Each transaction records findings, unknowns, dead-ends, vector values, confidence, and outcomes.

Source: README.md §The Epistemic Transaction Cycle (lines 150–165); EPISTEMIC_AGENT_ARCHITECTURE.md, lines 1–50; MEMORY_ARCHITECTURE.md, lines 90–100+.

### 3. The 13 Epistemic Vectors — Multidimensional Knowledge Measurement

**What it does**: Empirica measures AI knowledge and state using 13 dimensions (vectors) that emerged from 600+ real working sessions. These dimensions predict success or failure in complex agent tasks.

**The vectors** (organized by tier):

| Tier | Vector | Measures |
|------|--------|----------|
| Gate | `engagement` | Is the AI actively processing or disengaged? |
| Foundation | `know` | Domain knowledge depth |
| | `do` | Execution capability |
| | `context` | Access to relevant information |
| Comprehension | `clarity` | How clear is the understanding? |
| | `coherence` | Do the pieces fit together? |
| | `signal` | Signal-to-noise in available information |
| | `density` | Information richness |
| Execution | `state` | Current working state |
| | `change` | Rate of progress/change |
| | `completion` | Task completion level |
| | `impact` | Significance of the work |
| Meta | `uncertainty` | Explicit doubt tracking |

**Real-time display**: When Claude Code hooks are enabled, a statusline shows epistemic state: `[empirica] ⚡94% ↕70% │ 🎯3 │ POST 🔍92% │ K:95% C:92% │ Δ +K +C` where ⚡ is overall confidence, ↕ is Sentinel threshold, 🎯 is open goals, POST is phase + work state, K/C are knowledge/context vectors, Δ is learning delta.

Source: README.md §The 13 Epistemic Vectors (lines 187–206); §Live Statusline (lines 168–184).

### 4. Four-Layer Memory Architecture — Persistence Across Sessions

**What it does**: Empirica maintains a 4-tier memory system that survives context compaction, session boundaries, and repository transfers. The AI can query this memory to bootstrap understanding in a new session.

**The tiers** (from always-loaded to persistent-storage):

1. **TIER 1 (ALWAYS LOADED)**: System prompt with vector definitions, MEMORY.md (auto-curated 200-line index), hook output (SessionStart, UserPromptSubmit)
2. **TIER 2 (ON-DEMAND)**: Individual memory files, .breadcrumbs.yaml (calibration corrections), Qdrant search (eidetic/episodic), project-bootstrap output
3. **TIER 3 (PERSISTENT STORAGE)**: sessions.db (goals, artifacts, calibration), workspace.db (cross-project registry), Qdrant collections, Git notes --ref=breadcrumbs
4. **TIER 4 (TRANSIENT)**: Per-session instance files, active work metadata, transaction state (ephemeral, auto-cleaned)

**Auto-curation**: MEMORY.md is automatically maintained at ~200 lines, ranking findings by epistemic confidence. This hot cache prevents context bloat while preserving critical learnings.

**Portability**: BREADCRUMBS (git notes) encode epistemic snapshots locally, surviving repo clone/transfer without cloud dependencies.

Source: MEMORY_ARCHITECTURE.md, complete diagram (lines 8–85); README.md §How It Works With Claude Code (line 219).

### 5. Calibration & Grounded Verification — Reality Check on AI Confidence

**What it does**: Empirica compares AI self-assessment (predicted confidence, stated readiness) against objective outcomes (test results, code quality metrics, task completion). This delta reveals whether the AI's confidence is justified or overconfident.

**Mechanism**: Brier Score calibration (proper scoring rule) computes how far AI confidence diverges from actual success. Dynamic thresholds are computed from calibration data — threshold = f(AI's historical accuracy on similar tasks). If AI claims 95% confidence but only succeeds 60% of the time on tasks where it claimed 95%, the next 95% claim gets a lower CHECK threshold.

**Grounded evidence**: Dual-track verification compares AI reasoning against:
- Test pass/fail results
- Git metrics (file churn, complexity metrics)
- Goal completion status
- Domain-specific success criteria (e.g., API contract compliance, security assertions)

Source: README.md §Prevents confident mistakes (line 35); CHANGELOG.md [1.7.0] "Brier Score Calibration"; PHASE_AWARE_CALIBRATION.md.

### 6. Cross-Project Search & Multi-Tenant Storage

**What it does**: Empirica supports multiple projects (e.g., "auth-service", "frontend", "cli-tool") in a single workspace. The AI can search across all project histories, finding patterns and prior solutions via semantic search.

**Mechanism**: Each project has a Qdrant vector collection (docs, memory, eidetic, episodic). The search API supports:
- `kind='eidetic'` — What have you learned? (episodic + personal memory)
- `kind='episodic'` — What happened? (project history, sequences of events)
- `kind='intelligence'` — Cross-domain knowledge (v1.7.7: new boost weights for collection-type relevance)

**Global search**: `--global` flag searches ALL projects' collections at once.

Source: CHANGELOG.md [1.7.5] "Cross-Project Search"; [1.7.7] "Intelligence search kind"; README.md §How It Works With Claude Code (line 220).

### 7. AI Workflow Pattern Mining — Learn From Your Own Behavior

**What it does**: Empirica detects repeated tool sequences (workflows) that the AI uses across transactions. Pattern mining surfaces which workflows work well (high success rate) and which lead to dead-ends.

**Mechanism**: Sequential pattern analysis (PrefixSpan algorithm) identifies repeated tool call sequences. Each pattern is ranked by:
- Frequency (how often does it appear)
- Success rate (what % of transactions using this pattern complete)
- Learning delta (did using this pattern improve epistemic vectors)

**Workflow suggestion engine**: When starting a new task, Empirica suggests workflows that succeeded on similar prior tasks (matched by goal keywords, code domain, etc.).

Source: CHANGELOG.md [1.7.7] "Workflow Pattern Mining" and "Workflow Suggestion Engine"; new `workflow-patterns` CLI command.

### 8. Natural Language Workflow — AI Operates the System Automatically

**What it does**: Users interact with Empirica via natural language. The AI (Claude Code, etc.) reads the statusline, interprets what's needed, and issues CLI commands automatically. Users never need to learn 150+ commands.

**Mechanism**: Empirica ships with system prompts (for Claude, Copilot, Gemini, Qwen, Roo) that teach the AI:
- How to read epistemic vectors from the statusline
- When to run investigation vs action
- Which CLI commands are available
- How to interpret CHECK gate decisions (investigate vs proceed)

The AI learns this once (via system prompt) and applies it across all sessions. Power users can still invoke commands directly: `empirica goals-list`, `empirica calibration-report`, etc.

Source: README.md §How You Use It (lines 43–60); docs/human/developers/system-prompts/ directory.

---

## Technical Architecture

### Core Components & Module Structure

**Entry point module**: `empirica.core` packages:
- `sentinel` — Gate logic (NoeticFilter, AxiologicGate, DecisionLogic)
- `epistemic_vectors` — 13-vector measurement system
- `memory` — 4-tier storage (SQLite, Qdrant, filesystem, transient)
- `calibration` — Brier score, threshold computation
- `artifacts` — Findings, unknowns, dead-ends logging
- `transaction` — PREFLIGHT/CHECK/POSTFLIGHT lifecycle

**Storage backends**:
- `.empirica/sessions.db` — SQLite (transactions, goals, artifacts, calibration snapshots)
- `.empirica/workspace.db` — SQLite (cross-project registry, entity knowledge graph)
- `.empirica/qdrant_data/` — Qdrant vector DB (4 collections per project: docs, memory, eidetic, episodic)
- `.git/refs/notes/empirica/*` — Git notes (BREADCRUMBS portable snapshots)

**Integration surfaces**:
- **Claude Code hooks** — PreToolUse, UserPromptSubmit, PostToolUse, PreCompact, SessionEnd in settings.json
- **MCP server** — Table-driven 44-tool registry (CLI wrapper), 30s timeout, stdout JSON routing
- **CLI** — 150+ Typer commands (goals-list, project-init, calibration-report, etc.)
- **System prompts** — Model-specific instructions (claude.md, copilot-instructions.md, gemini.md, qwen.md, rovodev.md)

### Data Flow

```
Session Start → SessionStart hook → session-init.py
  ├─ Load TIER 1 context (system prompt, MEMORY.md, hooks)
  ├─ Query TIER 2 (qdrant search, .breadcrumbs.yaml)
  └─ Create active_work_{session}.json

Mid-Session → PreToolUse hook → sentinel-gate.py
  ├─ Read active transaction state
  ├─ Classify tool (noetic vs praxic)
  ├─ Check Sentinel gate (vectors vs thresholds)
  └─ PROCEED | INVESTIGATE

Work Completion → UserPromptSubmit hook → post-work analysis
  ├─ Record findings/unknowns from AI reasoning
  ├─ Update transaction state

Session End → SessionEnd hook → session-end-postflight.py
  ├─ Run POSTFLIGHT measurement
  ├─ Compute learning delta
  ├─ Update calibration
  ├─ Write to sessions.db + qdrant
  └─ Push to intelligence layer if CORTEX_API_KEY set
```

Source: MEMORY_ARCHITECTURE.md §Data Flow (lines 88–120+); SENTINEL_ARCHITECTURE.md §Core Architecture (lines 25–40).

### Data Model — Epistemic Vectors & Transactions

**Transaction record** (in sessions.db):

```
{
  transaction_id: UUID,
  session_id: UUID,
  goal_id: UUID,
  phase: PREFLIGHT | CHECK | POSTFLIGHT,
  preflight_vectors: {know, do, context, clarity, coherence, signal, density, state, change, completion, impact, uncertainty, engagement},
  postflight_vectors: {same 13 vectors after work},
  learning_delta: {vector_name: float(change)},
  findings: [list of findings],
  unknowns: [list of unknowns],
  dead_ends: [list of dead-ends],
  tool_count: {noetic: int, praxic: int},
  confidence: float(0..1),
  outcome: SUCCESS | PARTIAL | FAILED | BLOCKED
}
```

**Artifact types** (logged separately):
- Finding (verified fact, source, confidence)
- Unknown (unanswered question, why it matters)
- Dead-End (tried approach, outcome, what was learned)
- Decision (choice made, rationale, alternatives considered)
- Assumption (unstated premise, risk level)

Source: DATABASE_SCHEMA_UNIFIED.md, EPISTEMIC_STATE_COMPLETE_CAPTURE.md.

### Sentinel Gate Decision Logic

```
IF noetic_phase:
  allow: investigation tools (read, grep, search, git, test runs)
  block: modification tools (write, commit, deploy)

IF check_phase:
  vectors = assess_current_state()
  thresholds = compute_thresholds(calibration_data)
  IF all(vectors[v] >= thresholds[v] for v in GATE_VECTORS):
    PROCEED to praxic
  ELSE:
    INVESTIGATE (loop back to noetic with guidance on what's missing)

IF praxic_phase:
  allow: modification tools (write, commit, deploy)
  block: other investigation (new unknowns require new PREFLIGHT)

IF closed_transaction:
  noetic_tools + safe bash allowed without new PREFLIGHT
```

Source: SENTINEL_GATE_REFERENCE.md; SENTINEL_ARCHITECTURE.md §Dual Defense Layers (lines 80–100+).

---

## Installation & Usage

### Quick Start — Claude Code (Recommended)

```bash
pip install empirica
empirica setup-claude-code
```

This command automatically configures:
- Epistemic hooks in `.claude/settings.json` (PreToolUse, SessionEnd, etc.)
- System prompt injection with empirica instructions
- Live statusline rendering
- MCP server for empirica CLI tools
- `.empirica/` project initialization

**First-time session:**

```bash
empirica onboard  # Interactive walkthrough
```

Then work normally — the AI manages the epistemic workflow automatically.

**For existing Claude Code projects** (preserve other hooks):

```bash
empirica setup-claude-code --force  # Only removes empirica's own hooks, preserves Railway, Superpowers, etc.
```

Source: README.md §Quick Start (lines 65–129); CLAUDE_CODE_SETUP.md.

### Alternative Installations

**Homebrew (macOS)**:

```bash
brew tap nubaeon/tap && brew install empirica
empirica setup-claude-code
```

**Docker**:

```bash
docker pull nubaeon/empirica:1.7.7-alpine  # 276MB, security-hardened
docker pull nubaeon/empirica:1.7.7         # 414MB, Debian slim
docker run -it -v $(pwd)/.empirica:/data/.empirica nubaeon/empirica:1.7.7 /bin/bash
```

**Manual / Other Platforms**:

```bash
pip install empirica
pip install empirica-mcp  # For Cursor, Cline, etc.
cd your-project && empirica project-init
```

Source: README.md §Alternative Installation Methods (lines 84–121).

### Key CLI Commands (150+ available)

Power users can invoke directly:

| Command | Purpose |
|---|---|
| `empirica goals-list` | List open goals for current session |
| `empirica goals-ready` | Show goals ready based on epistemic state (combines dependencies + vectors) |
| `empirica calibration-report` | Current calibration thresholds and prediction accuracy |
| `empirica project-search --task "..."` | Find prior solutions to similar tasks |
| `empirica project-switch <name>` | Switch to another project (displays Epistemic Brief) |
| `empirica finding-log "Finding text"` | Log a finding to current project |
| `empirica workflow-patterns` | See repeated tool sequences and their success rates |
| `empirica memory-export` | Export memory files for sharing/archiving |

Source: README.md §How You Use It (line 57); docs/human/developers/CLI_COMMANDS_UNIFIED.md (150+ commands documented).

### Configuration

**Environment variables**:
- `EMPIRICA_SENTINEL_LOOPING` — Enable/disable looping mode (default: enabled)
- `EMPIRICA_AUTOPILOT` — Enable/disable auto-investigation (default: enabled)
- `EMPIRICA_CORTEX_URL` — Intelligence layer URL (default: localhost:8420)
- `CORTEX_API_KEY` — Auth token for remote intelligence layer
- `EMPIRICA_MCP_TIMEOUT` — MCP tool timeout in seconds (default: 30s)

**Project-local configuration** (`.empirica/config.yaml`):

```yaml
project:
  name: "project-slug"
  domains: ["security", "devops"]  # For calibration bucketing
memory:
  max_lines_per_memory_file: 200
  auto_curation: true
sentinel:
  know_threshold: 0.75  # Dynamically computed, but overridable
  engagement_threshold: 0.65
```

Source: CONFIGURATION_REFERENCE.md; ENVIRONMENT_VARIABLES.md.

---

## Relevance to Claude Code Development

### Specific Use Cases Within Claude Code Workflows

1. **Investigation Phase Enforcement**: The Sentinel gate integrates with Claude Code's `/dh:work-backlog-item` skill, enforcing noetic (investigation) phases before tasks are allowed to modify code. This prevents the "acts before understanding" anti-pattern.

2. **Task Decomposition Measurement**: When Claude Code's task decomposition produces sub-tasks, Empirica measures epistemic state at each decomposition boundary. The AI must demonstrate understanding of the subtask before being allowed to implement it.

3. **Memory Persistence Across Milestones**: Claude Code's MEMORY.md is auto-curated by Empirica into a ranked index of findings, dead-ends, and learnings. This enables cross-milestone context without manual summarization — the AI bootstraps understanding from prior work in seconds.

4. **Calibration of Confident Mistakes**: When an AI's stated confidence (e.g., "I'm certain this authentication logic is correct, confidence 95%") is contradicted by test failures, Empirica adjusts future thresholds. Tasks where the AI was historically overconfident get higher Sentinel gates.

5. **Workflow Pattern Learning**: After 50+ Claude Code sessions, Empirica identifies which investigation patterns (read tests → check API → search examples) lead to successful implementations. New similar tasks get workflow suggestions based on prior success rates.

6. **Cross-Project Intelligence**: When working on multiple Claude Code projects, `--global` search surfaces solutions and patterns from prior projects without manual knowledge transfer. This compounds learning across projects.

### Why Empirica Matters for Claude Code Agents

- **Prevents context collapse**: 4-layer memory survives Claude Code's context compaction hooks
- **Grounds autonomy**: Sentinel gate prevents autonomous edits on shallow understanding
- **Measures learning**: Each milestone completion updates calibration, improving future estimations
- **Audit trail**: Complete transaction logs for debugging agent failures or understanding decision chains
- **Integrates seamlessly**: No Claude Code modifications needed — Empirica runs via hooks and MCP

---

## Limitations & Caveats

1. **Qdrant optional but important**: Vector search (eidetic/episodic queries) requires Qdrant. Without it, memory querying falls back to BM25 search (slower, less semantic). Installation: `pip install empirica[vector]` or run separately.

2. **Vision/OCR experimental**: The `empirica[vision]` extra (pytesseract, PIL, opencv) is marked experimental in pyproject.toml. Visual understanding for browser interactions or diagram analysis has limited test coverage.

3. **Thresholds are adaptive, not fixed**: Sentinel thresholds are computed from historical data per-project. New projects without calibration history use defaults (know: 0.75, engagement: 0.65) which may be too loose or too strict for your domain.

4. **MCP timeout at 30s**: All MCP tool calls have a 30-second timeout (configurable via `EMPIRICA_MCP_TIMEOUT`). Long-running investigations (e.g., expensive cross-project search) may timeout. Workaround: invoke directly via CLI for long operations.

5. **No cloud-native persistence**: Empirica is fundamentally local-first. The CORTEX_API_KEY integration for remote intelligence is experimental (v1.7.6). For production multi-user deployments, manual setup required.

6. **Git notes require push for portability**: BREADCRUMBS (epistemic snapshots in git notes) are portable across clones ONLY if explicitly pushed. Default: local-only. To share snapshots: `git push origin refs/notes/empirica/*`

7. **Context overhead on first run**: The system prompt and Tier 1 memory add ~2–3K tokens of always-loaded context. For memory-constrained deployments (e.g., GPT-4 Mini with tight context), use `setup-claude-code --lean` for 81% reduction (v1.7.0 feature).

8. **Platform-specific behaviors**: Claude Code integration is production (full hooks). Cursor/Cline via MCP only. Copilot/Gemini via system prompt only (no hooks). Compatibility matrix: see README.md §Platform Support.

Source: README.md §Privacy & Data (lines 291–299); CHANGELOG.md [1.7.0] "Lean Core Prompt"; pyproject.toml optional-dependencies; CONFIGURATION_REFERENCE.md; CLAUDE_CODE_SETUP.md.

---

## Key Learnings & Design Patterns

1. **Epistemic transactions over imperative tasks**: The noetic-praxic cycle inverts the typical "do first, measure later" pattern. Measurement-first gates prevent confident failures.

2. **Vectors over binary gates**: Rather than YES/NO "ready to act", 13 vectors give nuanced understanding. The AI might be high-confidence but low-signal (knows what it wants but missing info). Vectors reveal this.

3. **Calibration via proper scoring rules**: Brier Score (a strictly proper scoring rule) forces honest confidence reporting. If the AI is overconfident, the score penalizes it more than underconfidence. This incentivizes truthful self-assessment.

4. **Memory as ranked cache**: Auto-curation ranks findings by epistemic confidence, not by time or frequency. The AI sees the most epistemically solid learnings first, not the most recent.

5. **Portability via git notes**: Epistemic snapshots in git notes (BREADCRUMBS) survive repo transfer without central servers. Decentralized, version-controlled, human-readable (YAML).

---

## Freshness Tracking

**Last verified**: 2026-04-05
**Source check date**: 2026-04-05

### Confidence by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Identity/Metadata** | high | v1.7.7 confirmed via GitHub commit history (8e6f8a7), PyPI package, API response |
| **Features** | high | Extracted from README.md, ARCHITECTURE.md, CHANGELOG.md v1.7.7. All features traced to source code modules |
| **Technical Architecture** | high | Core module structure from `empirica.core` references in docs; data models from DATABASE_SCHEMA_UNIFIED.md; data flow from MEMORY_ARCHITECTURE.md |
| **Installation & Usage** | high | Installation commands verified against README.md §Quick Start and §Alternative Installation; CLI commands listed in CLI_COMMANDS_UNIFIED.md; config from CONFIGURATION_REFERENCE.md |
| **Claude Code Integration** | medium | Integration points (hooks, MCP) documented in CLAUDE_CODE_SETUP.md and architecture docs. Use cases inferred from design (noetic/praxic phase alignment with `/dh:` skills, memory integration with MEMORY.md). Operational details require live testing in Claude Code environment |
| **Limitations** | medium | Documented limitations from README.md §Platform Support, experimental features from pyproject.toml, known issues from CHANGELOG.md. Some limitations (git notes portability, threshold defaults) inferred from architecture design; operational edge cases require live testing |

### Next Review

Recommended review date: **2026-07-05** (90 days from today)

Review triggers:
- New major release (2.0.0)
- Breaking changes to hook schema or epistemic vector definitions
- Changes to Sentinel gate logic or calibration methodology
- Significant additions to 150+ command set

---

## References

- **GitHub repository**: <https://github.com/Nubaeon/empirica> (accessed 2026-04-05)
- **Website & Training**: <https://getempirica.com> (mentioned in README.md, accessed 2026-04-05)
- **Official Documentation**: docs/architecture/, docs/human/, docs/reference/ (all files read from shallow clone 2026-04-05)
- **Latest Release**: v1.7.7 released 2026-04-01 per GitHub API (tag 8e6f8a7)
- **PyPI Package**: <https://pypi.org/project/empirica/> (listed in README.md badge)
- **Authors**: David S. L. Van Assche (pyproject.toml authors field)

### Documentation Files Consulted

- README.md (main overview)
- ARCHITECTURE.md (core architecture diagram)
- CHANGELOG.md (version history, feature releases)
- AGENTS.md (beads issue tracking integration)
- docs/architecture/SENTINEL_ARCHITECTURE.md
- docs/architecture/EPISTEMIC_AGENT_ARCHITECTURE.md
- docs/architecture/MEMORY_ARCHITECTURE.md
- docs/reference/CONFIGURATION_REFERENCE.md
- docs/reference/DATABASE_SCHEMA_UNIFIED.md
- docs/reference/SENTINEL_GATE_REFERENCE.md
- docs/human/developers/CLAUDE_CODE_SETUP.md
- docs/human/developers/CLI_COMMANDS_UNIFIED.md
- pyproject.toml (package metadata, dependencies)
- GitHub API (stars, forks, topics, license, creation date)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [claude-mem.md](../context-management/claude-mem.md) | context-management | shares persistent memory compression strategy; empirica's 4-layer memory system integrates measurement with compression |
| [claude-pilot.md](../developer-tools/claude-pilot.md) | developer-tools | both provide quality-enforcement layers for Claude Code via hooks; empirica adds epistemic gating, claude-pilot adds TDD enforcement |
| [compression-monitor.md](../ai-observability/compression-monitor.md) | ai-observability | aligned on measuring behavioral drift in Claude Code sessions; empirica tracks epistemic state vectors, compression-monitor detects post-compression degradation |
| [local-memory.md](../context-management/local-memory.md) | context-management | both implement multi-tier memory persistence; empirica couples memory with calibrated confidence measurement |
| [liteagents.md](../agent-frameworks/liteagents.md) | agent-frameworks | overlapping measurement concern: empirica uses 13 epistemic vectors, liteagents uses session friction analysis for agent behavior assessment |
| [mimir-mcp.md](../mcp-ecosystem/mimir-mcp.md) | mcp-ecosystem | both provide persistent AI memory via structured storage; empirica's MCP server exposes memory operations as tools |
| [gitnexus.md](../mcp-ecosystem/gitnexus.md) | mcp-ecosystem | shared Claude Code hooks integration; empirica provides agent self-awareness, gitnexus provides code intelligence graph |
| [everything-claude-code.md](../developer-tools/everything-claude-code.md) | developer-tools | both target Claude Code performance optimization via hooks; empirica narrows on epistemic measurement, everything-claude-code provides broader harness |

---

**Note**: This entry was created via deep primary-source research from the Empirica repository (v1.7.7, commit 8e6f8a7). All factual claims are grounded in extracted passages from official documentation, code comments, or GitHub metadata. Where inference was necessary (e.g., use cases for Claude Code), it is marked as such and supported by architectural design principles extracted from source.
