---
name: autoresearchclaw
research_date: 2026-04-03
source_url: https://github.com/aiming-lab/AutoResearchClaw
github_repository: https://github.com/aiming-lab/AutoResearchClaw
version_at_research: v0.4.0
license: MIT
freshness_tracking:
  last_verified: 2026-04-03
  version_at_verification: v0.4.0
  next_review: 2026-07-03
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: medium (code-read), Installation & Usage: high, Relevance: medium, References: high"
---

# AutoResearchClaw

## Overview

AutoResearchClaw is a fully autonomous research pipeline that transforms a single research topic into a conference-ready academic paper through a 23-stage orchestration process. The system orchestrates multi-agent teams across 8 phases—from literature discovery through experiment execution to publication-grade output—with optional human intervention at critical decision points (accessed 2026-04-03).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Labor-intensive manual literature review and paper writing | Autonomous research pipeline retrieves genuine papers from OpenAlex, Semantic Scholar, and arXiv with 4-layer citation verification to eliminate fabricated references |
| Variable hardware availability for experiments | Auto-detects computing resources (GPU/CPU/MPS) and tailors experiment code accordingly; routes complex projects to OpenCode "Beast Mode" |
| Experiment failures block research progress | Isolated sandboxes with self-healing capabilities allow the system to diagnose failures and attempt repairs before proceeding |
| Lack of human control in fully autonomous systems | Six intervention modes (gate-only, checkpoint, co-pilot, step-by-step, express, custom) plus `--auto-approve` baseline allow researchers to guide decisions at critical junctures while automation handles routine stages |

---

## Key Features

### Research & Literature

- **Genuine Literature Retrieval**: Integrates with OpenAlex, Semantic Scholar, and arXiv through a 4-layer citation verification process that detects and removes fabricated references.
- **Multi-Agent Peer Review**: Quality assurance via automated peer review agents that validate results and prevent low-quality outputs from proceeding downstream.

### Experiment Execution

- **Hardware-Aware Sandbox Execution**: Auto-detects available computing resources and runs experiments in isolated environments with built-in self-healing—diagnoses failures and attempts repairs before proceeding.
- **Evidence Consistency Checking**: Automated quality gates verify experimental results match claims before integration into the paper.

### Human-AI Collaboration (v0.4.0+)

- **Seven Execution Modes**: Fully autonomous via `--auto-approve` baseline, plus six intervention modes (gate-only, checkpoint, co-pilot, step-by-step, express, custom) allow researchers to direct decisions at varying granularities.
- **Continuous Learning**: MetaClaw integration (v0.3.0+) enables cross-run learning with reported +18.3% robustness improvement in controlled experiments.

### Output

- **Publication-Grade LaTeX**: Generates conference-ready papers targeting NeurIPS, ICML, ICLR standards with complete citations and reproducibility information.

---

## Technical Architecture

### 23-Stage Pipeline (8 Phases)

The system orchestrates eight distinct phases across 23 sequential stages (README L282-304):

1. **Phase A — Research Scoping** (Stages 1-2): Problem definition, scope boundaries
2. **Phase B — Literature Discovery** (Stages 3-6): Paper search, source validation, knowledge compilation
3. **Phase C — Knowledge Synthesis** (Stages 7-8): Hypothesis generation, research gap analysis
4. **Phase D — Experiment Design** (Stages 9-11): Methodology selection, baseline establishment, experiment configuration
5. **Phase E — Experiment Execution** (Stages 12-13): Sandbox setup, code generation, hardware auto-detection, experiment runs
6. **Phase F — Analysis & Decision** (Stages 14-15): Result aggregation, statistical validation
7. **Phase G — Paper Writing** (Stages 16-19): Draft composition, peer review (Stage 18), revision (Stage 19), result integration, reference assembly
8. **Phase H — Finalization** (Stages 20-23): Quality gate (Stage 20 QUALITY_GATE), citation verification (Stage 23 CITATION_VERIFY), publication preparation

### Multi-Agent Subsystems (v0.2.0+)

**CodeAgent**: Generates hardware-aware experiment code with auto-detection and adaptation logic.

**BenchmarkAgent**: Finds and acquires benchmarks, validates dataset availability, and selects evaluation metrics.

**FigureAgent**: Synthesizes visualization artifacts and statistical summaries from raw results.

### Sandbox Security

- **Docker Hardening** (v0.2.0+): Network-policy-aware sandbox execution prevents unauthorized data exfiltration.
- **Citation Verification** (README L336): 4-layer citation integrity process — (1) arXiv ID check, (2) CrossRef/DataCite DOI validation, (3) Semantic Scholar title match, (4) LLM relevance scoring — eliminates hallucinated references before integration into paper.

---

## Installation & Usage

### Quick Start

```bash
git clone https://github.com/aiming-lab/AutoResearchClaw.git
cd AutoResearchClaw
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
researchclaw setup
researchclaw init
export OPENAI_API_KEY="sk-..."
researchclaw run --topic "Your research idea" --auto-approve
```

### Setup Verification

The `researchclaw setup` command:
- Installs all dependencies
- Verifies Docker and LaTeX availability
- Validates hardware (GPU/CPU detection)

The subsequent `researchclaw init` command prompts for LLM provider configuration and creates `config.arc.yaml`.

### Execution Modes (v0.4.0+, README L356-364)

The system supports fully autonomous execution via `--auto-approve` plus six intervention modes:

```bash
# Fully autonomous (no human intervention required)
researchclaw run --topic "Your research idea" --auto-approve

# Gate-only mode (pause at 3 critical pipeline gates)
researchclaw run --topic "Your research idea" --mode gate-only

# Checkpoint mode (pause at each phase boundary)
researchclaw run --topic "Your research idea" --mode checkpoint

# Co-pilot mode (deep collaboration at critical stages, auto elsewhere)
researchclaw run --topic "Your research idea" --mode co-pilot

# Step-by-step mode (pause after every stage—learn the pipeline)
researchclaw run --topic "Your research idea" --mode step-by-step

# Express mode (quick review focusing on 3 most critical gates)
researchclaw run --topic "Your research idea" --mode express

# Custom mode (define per-stage policies via stage_policies config)
researchclaw run --topic "Your research idea" --mode custom
```

---

## Relevance to Claude Code Development

### Applications

1. **Autonomous Research Workflows**: AutoResearchClaw's multi-agent orchestration pattern—coordinating specialized agents (CodeAgent, BenchmarkAgent, FigureAgent) across pipeline stages—demonstrates scalable patterns for Claude Code multi-agent systems handling long-running, complex tasks.

2. **Human-in-the-Loop Agent Control**: The seven execution modes (`--auto-approve` baseline plus gate-only, checkpoint, co-pilot, step-by-step, express, custom) provide concrete patterns for Claude Code to implement graded levels of human oversight from fully autonomous to step-by-step collaborative control.

3. **Self-Healing Sandbox Execution**: The hardware-detection and failure-recovery mechanisms in experiment execution are directly applicable to Claude Code's sandbox design for autonomous code execution.

### Patterns Worth Adopting

- **Stage-Based Gating**: Quality gates after critical stages (baseline selection, result aggregation) prevent low-quality outputs from propagating downstream.
- **Evidence Validation**: Automated consistency checking between experimental claims and measured results provides a pattern for automated validation gates.
- **Cross-Run Learning Integration**: MetaClaw's +18.3% robustness improvement demonstrates the value of persistent memory across agent runs—applicable to Claude Code's session persistence.

---

## References

- [GitHub Repository](https://github.com/aiming-lab/AutoResearchClaw) (accessed 2026-04-03)
- [GitHub README](https://github.com/aiming-lab/AutoResearchClaw/blob/main/README.md) (accessed 2026-04-03)
- [Releases](https://github.com/aiming-lab/AutoResearchClaw/releases) — v0.2.0 through v0.4.0 feature history (accessed 2026-04-03)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [AI Agents Frameworks](./ai-agents-frameworks.md) | agent-frameworks | comparative benchmark study covering 10 frameworks; complements AutoResearchClaw's multi-agent orchestration patterns with framework selection methodology |
| [Agno](./agno.md) | agent-frameworks | multi-agent orchestration with learning systems and knowledge transfer; shares async-first design and stateful agent architecture for cross-session context persistence |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | 16-agent orchestration with hooks and token optimization; parallel pattern execution model overlaps with AutoResearchClaw's multi-phase pipeline design |
| [AI Data Science Team](../research-agent-patterns/ai-data-science-team.md) | research-agent-patterns | LangGraph supervisor-agent pattern with 9 specialist agents for data pipelines; mirrors AutoResearchClaw's stage-based agent routing and sandboxed code execution |
| [Gastown](../research-agent-patterns/gastown.md) | research-agent-patterns | multi-agent workspace with tmux coordination, Dolt ledger, and DAG scheduling; shares supervisor-worker orchestration pattern and state-driven workflow progression |
| [Compound Engineering Plugin](../research-agent-patterns/compound-engineering-plugin.md) | research-agent-patterns | 27-agent Plan/Work/Review/Compound workflow; overlapping multi-phase architecture with approval gates similar to AutoResearchClaw's Stage 5/9/20 quality gates |
| [Google ADK Context Engineering](../research-agent-patterns/google-adk-context-engineering.md) | research-agent-patterns | tiered storage model and scoped multi-agent handoffs; provides context engineering patterns applicable to AutoResearchClaw's knowledge extraction and synthesis phases |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | persistent memory compression across sessions with progressive disclosure; applicable to AutoResearchClaw's cross-run learning and MetaClaw integration for retaining lessons |
| [OpenHands](../coding-agents/openhands.md) | coding-agents | model-agnostic coding agent platform with sandboxed execution and self-healing; shares sandbox isolation and autonomous repair patterns with AutoResearchClaw's experiment execution |
| [OpenSpec MCP](../mcp-ecosystem/openspec-mcp.md) | mcp-ecosystem | spec-driven workflow with approval state machine and quality gates; parallels AutoResearchClaw's multi-stage pipeline with structured gating and verification logic |

---

*Research entry created 2026-03-19. All factual claims trace to primary sources: README.md, integration-guide.md, pyproject.toml, LICENSE, researchclaw/pipeline/stages.py.*
