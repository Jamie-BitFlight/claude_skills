# AutoResearchClaw

## Overview

AutoResearchClaw is a fully autonomous 23-stage research pipeline that converts a single research idea into a conference-ready academic paper without human intervention. The system orchestrates multi-agent workflows across literature discovery, hypothesis generation, experiment design and execution, result analysis, and paper writing with integrated quality gates and self-healing capabilities.

**Core proposition**: "Chat an Idea. Get a Paper. Fully Autonomous & Self-Evolving." Users provide a research topic; the system outputs a complete paper with real literature, reproducible experiments, statistical analysis, and publication-ready LaTeX targeting venues like NeurIPS, ICLR, and ICML.

## Problem Addressed

Research publication is a multi-month, human-intensive process involving literature review, hypothesis formulation, experiment design, coding, result analysis, and manuscript writing. Even for domain experts, this workflow is repetitive and error-prone. AutoResearchClaw addresses the need for end-to-end research automation that can:

1. Discover relevant literature from multiple sources (OpenAlex, Semantic Scholar, arXiv) with quality filtering
2. Synthesize findings into coherent hypotheses via multi-agent debate
3. Design and execute reproducible experiments in sandboxed, hardware-aware environments
4. Detect and repair runtime failures (NaN/Inf, code bugs) autonomously
5. Analyze results and make autonomous PIVOT/REFINE/PROCEED decisions
6. Generate conference-grade manuscripts with verified citations
7. Self-improve across runs through learned lessons and skills

## Key Statistics

- **Version**: v0.3.1 (released 2026-03-18)
- **Pipeline stages**: 23 stages organized in 8 phases
- **Test coverage**: 1,634 tests passing
- **License**: MIT
- **Language**: Python 3.11+
- **Development status**: Active (latest release 2026-03-18)

## Key Features

### 23-Stage Research Pipeline

The pipeline is divided into 8 phases with explicit gating and decision logic:

- **Phase A (Scoping)**: TOPIC_INIT → PROBLEM_DECOMPOSE — decomposes the topic into structured research questions
- **Phase B (Literature)**: SEARCH_STRATEGY → LITERATURE_COLLECT → LITERATURE_SCREEN [gate] → KNOWLEDGE_EXTRACT — multi-source literature discovery with quality filtering
- **Phase C (Synthesis)**: SYNTHESIS → HYPOTHESIS_GEN [multi-agent debate] — clusters findings, identifies gaps, generates testable hypotheses
- **Phase D (Design)**: EXPERIMENT_DESIGN [gate] → CODE_GENERATION → RESOURCE_PLANNING — hardware-aware experiment design
- **Phase E (Execution)**: EXPERIMENT_RUN → ITERATIVE_REFINE [self-healing] — runs experiments in sandbox with NaN/Inf detection and targeted LLM repair
- **Phase F (Analysis)**: RESULT_ANALYSIS [multi-agent] → RESEARCH_DECISION [autonomous PIVOT/REFINE/PROCEED] — analyzes results and makes autonomous direction decisions
- **Phase G (Writing)**: PAPER_OUTLINE → PAPER_DRAFT → PEER_REVIEW [methodology-evidence consistency] → PAPER_REVISION — generates 5,000-6,500 word manuscripts
- **Phase H (Finalization)**: QUALITY_GATE [gate] → KNOWLEDGE_ARCHIVE → EXPORT_PUBLISH [LaTeX] → CITATION_VERIFY [4-layer relevance check]

### Multi-Agent Architecture

- **Hypothesis Generation**: Multi-perspective debate between competing hypotheses
- **Result Analysis**: Structured multi-agent analysis of experimental outcomes
- **Peer Review**: Evidence-consistency checks between methodology and reported results
- **Code Generation**: Hardware-aware code generation with GPU detection (NVIDIA CUDA, Apple MPS, CPU-only)

### Citation Integrity & Literature Management

- **Multi-Source Literature**: Real papers from OpenAlex, Semantic Scholar, and arXiv with query expansion and deduplication
- **4-Layer Citation Verification**: (1) arXiv ID validation → (2) CrossRef/DataCite DOI lookup → (3) Semantic Scholar title matching → (4) LLM relevance scoring; hallucinated references are auto-removed
- **Real BibTeX References**: Auto-pruned references.bib file that matches inline citations in the generated paper

### Hardware-Aware Execution

- Auto-detects GPU availability (NVIDIA CUDA, Apple MPS) or falls back to CPU-only mode
- Adapts experiment code generation, import selection, and experiment scale based on available hardware
- Warns if local hardware is limited for the requested experiment size

### Self-Healing Experiments

- AST-validated code with immutable harness
- NaN/Inf fast-fail detection
- Targeted LLM repair of runtime failures
- Iterative refinement up to 10 rounds with partial result capture
- Autonomous decision to REFINE (tweak parameters) or PIVOT (new direction) at Stage 15

### OpenCode Beast Mode

Complex experiments are automatically routed to [OpenCode](https://github.com/anomalyco/opencode) for multi-file project generation with custom architectures, training loops, and ablation studies. Installed via `researchclaw setup`.

### Conference-Grade Output Artifacts

- `paper_draft.md` — Full academic paper (Introduction, Related Work, Method, Experiments, Results, Conclusion)
- `paper.tex` — Conference-ready LaTeX with templates for NeurIPS 2025, ICLR 2026, ICML 2026
- `references.bib` — Real BibTeX references from OpenAlex, Semantic Scholar, arXiv
- `verification_report.json` — 4-layer citation integrity and relevance verification
- `experiment_runs/` — Generated code, sandbox results, structured JSON metrics
- `charts/` — Auto-generated condition comparison charts with error bars and confidence intervals
- `reviews.md` — Multi-agent peer review with methodology-evidence consistency checks
- `evolution/` — Self-learning lessons extracted from each run (with 30-day time-decay for future runs)
- `deliverables/` — All final outputs compile-ready for Overleaf

### MetaClaw Integration (Cross-Run Learning)

When paired with [MetaClaw](https://github.com/aiming-lab/MetaClaw), the pipeline captures lessons from failures and warnings, converts them into reusable skills, and injects those skills into all 23 stages on subsequent runs. Reported improvements in controlled experiments:

- Stage retry rate: -24.8% (10.5% → 7.9%)
- Refine cycle count: -40.0% (2.0 → 1.2)
- Pipeline stage completion: +5.3% (18/19 → 19/19)
- Overall robustness score: +18.3% (0.714 → 0.845)

Disabled by default; opt-in via `metaclaw_bridge.enabled: true` in config — fully backward-compatible.

### OpenClaw Integration

AutoResearchClaw is [OpenClaw](https://github.com/openclaw/openclaw)-compatible. Users can:

1. Share the GitHub repo URL with OpenClaw
2. OpenClaw reads `RESEARCHCLAW_AGENTS.md` and `README.md`
3. Say "Research [your topic]"
4. OpenClaw clones, installs, configures, runs, and returns results

OpenClaw Bridge supports 6 optional capabilities:

- Scheduled research runs (cron)
- Progress notifications (Discord/Slack/Telegram)
- Cross-session knowledge persistence
- Parallel sub-session spawning
- Live web search during literature review
- Browser-based paper collection

### Agent Client Protocol (ACP) Support

AutoResearchClaw can use any ACP-compatible coding agent (Claude Code, Codex CLI, Gemini CLI, OpenCode, Kimi CLI) as its LLM backend without API keys — maintains a single persistent session across all 23 stages via [acpx](https://github.com/openclaw/acpx).

### Quality Gates & Human-in-the-Loop

- Stage 5 (Literature Screen): Approve/reject collected literature
- Stage 9 (Experiment Design): Approve/reject experiment plan
- Stage 20 (Quality Gate): Approve/reject final paper before publication

Skip gates with `--auto-approve` flag. On rejection, the pipeline rolls back automatically.

## Technical Architecture

### Core Components (extracted from `researchclaw/pipeline/stages.py`)

The pipeline is implemented as a 23-stage state machine with the following components:

- **Stage Enum**: 23-stage sequence (Stage 1-23) with natural progression
- **StageStatus Enum**: PENDING, RUNNING, BLOCKED_APPROVAL, APPROVED, REJECTED, PAUSED, RETRYING, FAILED, DONE
- **TransitionEvent**: START, SUCCEED, APPROVE, REJECT, TIMEOUT, FAIL, RETRY, RESUME, PAUSE
- **Stage Navigation**: STAGE_SEQUENCE tuple, NEXT_STAGE and PREVIOUS_STAGE dicts for forward/rollback flow
- **Gate Logic**: Stages 5, 9, 20 block on BLOCKED_APPROVAL until APPROVE or REJECT event
- **Decision Logic**: Stage 15 (RESEARCH_DECISION) emits transitions to ITERATE (→ Stage 13), PIVOT (→ Stage 8), or PROCEED (→ Stage 16)

### Key Modules

- `researchclaw/cli.py` — Command-line interface (setup, init, run, validate)
- `researchclaw/llm/client.py` — LLM client for OpenAI-compatible endpoints
- `researchclaw/llm/acp_client.py` — Agent Client Protocol integration
- `researchclaw/literature/openalex_client.py` — OpenAlex API wrapper for literature search
- `researchclaw/literature/arxiv_client.py` — arXiv API wrapper
- `researchclaw/pipeline/executor.py` — Pipeline orchestrator
- `researchclaw/agents/` — Multi-agent implementations (code, benchmark, figure agents)

### Sandbox Environment

Experiments run in a configurable sandbox with:

- Mode options: simulated, sandbox (default), docker, ssh_remote
- Python path configuration for controlled environment
- Allowed imports whitelist (math, random, json, numpy, torch, sklearn, etc.)
- Memory limit (default 4096 MB)
- GPU enabling (true/false)
- Network policy (none, setup_only, pip_only, full) — default setup_only

## Installation & Usage

### Quick Start

```bash
# 1. Clone & install
git clone https://github.com/aiming-lab/AutoResearchClaw.git
cd AutoResearchClaw
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Setup (interactive — installs OpenCode beast mode, checks Docker/LaTeX)
researchclaw setup

# 3. Configure
researchclaw init          # Interactive: choose LLM provider, creates config.arc.yaml
# Or manually: cp config.researchclaw.example.yaml config.arc.yaml

# 4. Run
export OPENAI_API_KEY="sk-..."
researchclaw run --config config.arc.yaml --topic "Your research idea" --auto-approve
```

### Minimum Required Configuration

```yaml
project:
  name: "my-research"

research:
  topic: "Your research topic here"

llm:
  base_url: "https://api.openai.com/v1"
  api_key_env: "OPENAI_API_KEY"
  primary_model: "gpt-4o"
  fallback_models: ["gpt-4o-mini"]

experiment:
  mode: "sandbox"
  sandbox:
    python_path: ".venv/bin/python"
```

### Using with OpenClaw

If OpenClaw is available, simply provide the repo URL and natural language request — no manual setup needed.

### Using with ACP-Compatible Agents

```yaml
llm:
  provider: "acp"
  acp:
    agent: "claude"   # or codex, gemini, opencode, kimi
    cwd: "."
```

## Limitations and Caveats

### Known Limitations (from reviewed sources)

1. **LLM Dependency**: Output quality depends entirely on the configured LLM (primary and fallback models). Hallucinated content is possible if the LLM generates false citations or experimental claims.
2. **Literature Source Limitations**: Multi-source search (OpenAlex, Semantic Scholar, arXiv) may have coverage gaps in niche subdisciplines or very recent preprints.
3. **Experiment Sandboxing**: The sandbox environment is not foolproof — complex or resource-intensive experiments may exceed memory or time budgets without warning.
4. **Conference Template Coverage**: Only three conference templates are pre-built (NeurIPS 2025, ICLR 2026, ICML 2026); other venues require custom LaTeX templates.
5. **Self-Healing Limits**: Iterative repair has a maximum of 10 rounds; if bugs persist after 10 attempts, the stage fails.
6. **Hardware Auto-Detection**: GPU detection is limited to NVIDIA CUDA and Apple MPS; other accelerators (AMD, Intel) may not be properly identified.
7. **Gate Approval Timeout**: Stage 5, 9, 20 have configurable timeout (default 12 hours); after timeout, the pipeline pauses indefinitely unless resumed manually.
8. **MetaClaw Dependency**: Cross-run learning (MetaClaw integration) is opt-in; without it, the pipeline does not retain lessons across sessions.
9. **Documentation Coverage**: Not documented in reviewed sources: memory limits for large literature databases, network policy enforcement details, and exact citation scoring algorithm.

## Relevance to Claude Code Development

AutoResearchClaw demonstrates architectural patterns and techniques highly relevant to multi-agent AI systems:

1. **Multi-Agent Orchestration**: The 23-stage pipeline coordinates specialized agents (hypothesis generator, code generator, peer reviewer, result analyzer) with structured inputs/outputs and decision logic — a pattern applicable to complex Claude Code workflows.

2. **Sandbox Execution & Self-Healing**: Autonomous experiment execution with NaN/Inf detection and targeted LLM repair mirrors self-healing patterns needed for autonomous coding agents that must detect and fix their own runtime failures.

3. **Hardware Awareness**: Auto-detection of GPU/MPS/CPU and adaptation of code generation and experiment scale is essential for coding agents deployed across heterogeneous infrastructure.

4. **Quality Gates & Human-in-the-Loop**: Structured approval gates at Stages 5, 9, 20 with automatic rollback on rejection — a pattern for integrating human oversight into autonomous agent workflows.

5. **Citation Integrity & Verification**: The 4-layer citation verification (arXiv ID, DOI, title match, LLM relevance) is a model for ensuring generated knowledge is grounded in verifiable sources — critical for maintaining hallucination-resistant agent outputs.

6. **Self-Learning from Failures**: MetaClaw integration demonstrates cross-run knowledge transfer via captured lessons — applicable to Claude Code agents that need to retain and apply learnings from previous sessions.

7. **OpenClaw Integration Pattern**: The OpenClaw bridge (`RESEARCHCLAW_AGENTS.md` + natural language bootstrap) is a reusable pattern for making complex agent systems accessible to other AI assistants.

## References

- **Repository**: <https://github.com/aiming-lab/AutoResearchClaw> (accessed 2026-03-19)
- **README.md**: Full feature overview, quick start, pipeline diagram, phase descriptions
- **integration-guide.md**: Configuration walkthrough, manual setup, OpenClaw integration, ACP protocol, troubleshooting
- **researchclaw/pipeline/stages.py**: 23-stage state machine implementation, gate logic, transitions
- **pyproject.toml**: Project metadata, version 0.3.1, dependencies, license MIT
- **LICENSE**: MIT License copyright Aiming Lab 2026
- **Latest Release**: v0.3.1 (2026-03-18) — "OpenCode Beast Mode + Community Contributions"
- **Previous Releases**:
  - v0.3.0 (2026-03-17) — MetaClaw integration with +18.3% robustness improvement
  - v0.2.0 (2026-03-16) — Multi-agent subsystems, hardened Docker sandbox, 4-round paper quality audit
  - v0.1.0 (2026-03-15) — Initial release, 23-stage pipeline

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|------------|---------------|-------|
| **Identity/Metadata** | high | 2026-03-19 | Repository README, pyproject.toml, LICENSE — official sources |
| **Features** | high | 2026-03-19 | Extracted from README phases, integration guide, feature tables |
| **Architecture** | high | 2026-03-19 | Code structure verified in stages.py, component descriptions from official docs |
| **Installation & Usage** | high | 2026-03-19 | Exact commands from README quick start and integration guide |
| **Limitations** | medium | 2026-03-19 | Limitations inferred from documented constraints (10-round repair limit, timeout configs); no "Limitations" section in primary sources |
| **Relevance to Claude Code** | medium | 2026-03-19 | Pattern analysis based on documented architecture; Claude Code use cases inferred from design |

**Next Review**: 2026-06-19 (3 months)

**Changes Since Last Review**: N/A (first entry)

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
