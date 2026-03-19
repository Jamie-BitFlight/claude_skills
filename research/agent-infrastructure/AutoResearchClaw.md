# AutoResearchClaw

**GitHub**: <https://github.com/aiming-lab/AutoResearchClaw>
**Latest Release**: v0.3.1 (2026-03-18)
**License**: MIT
**Language**: Python 3.11+
**Repository**: Active (last commit 2026-03-19)

---

## Overview

AutoResearchClaw is a fully autonomous 23-stage research pipeline that converts a single research idea into a conference-ready academic paper end-to-end, without human intervention. Users provide a research topic as text, and the system generates a complete paper with real literature, executable experiments, multi-agent peer review, and publication-ready LaTeX.

**Tagline**: "Chat an Idea. Get a Paper. Fully Autonomous & Self-Evolving."

---

## Problem Addressed

Autonomous research generation faces multiple systemic challenges:

1. **Literature hallucination** — LLM-generated citations fabricate papers that don't exist or misrepresent existing work
2. **Experiment failure without recovery** — Generated code crashes in sandbox, and there is no adaptive re-generation
3. **Incomplete paper quality gates** — Few systems validate paper-evidence consistency or catch AI-generated slop
4. **Single-source evidence** — Most systems rely on one LLM model; failures cascade across entire pipeline
5. **No cross-run learning** — Pipeline repeats mistakes from previous runs instead of learning from them
6. **Lack of transparency in methodology** — Unclear which papers were cited or why experiments were designed a certain way

AutoResearchClaw addresses these by combining real literature APIs (OpenAlex, Semantic Scholar, arXiv), adaptive code repair in isolated sandboxes, multi-agent debate for hypothesis generation and result analysis, 4-layer citation integrity verification, MetaClaw integration for self-learning across runs, and explicit knowledge base tracking of decisions and findings.

---

## Key Statistics

- **GitHub Stars**: 6,246 (as of 2026-03-19)
- **Forks**: 624 (as of 2026-03-19)
- **Test Coverage**: 1,634 passing tests (as of README badges)
- **Python Files**: 90+ source modules across 16 domain and agent subsystems
- **Test Pass Rate**: 100% (1,634 tests, 0 open issues as of scan date)
- **Release Velocity**: 4 major releases in 5 days (v0.1.0 through v0.3.1, 2026-03-15 to 2026-03-18)

---

## Key Features

### 1. Real-World Literature Discovery (Not Hallucinated)

**Mechanism**: Multi-source search with deduplication and quality filtering.

- Queries **OpenAlex**, **Semantic Scholar**, and **arXiv** in parallel for each research question
- Deduplicates papers by arXiv ID and DOI
- Screens by relevance and citation count (configurable `quality_threshold`, default 4.0)
- Targets 8 papers per search query by default (`daily_paper_count: 8`)
- Extracted knowledge includes: abstract, authors, publication date, BibTeX, and semantic category

**Example output** (from README): `references.bib` with 30-50 real papers, manually pruned to match inline citations.

### 2. Four-Layer Citation Integrity Verification

**Mechanism**: Cascading validation gates with fallback.

1. **arXiv ID Check** — Validate paper exists on arXiv.org
2. **CrossRef/DataCite DOI** — Verify DOI resolves and matches paper metadata
3. **Semantic Scholar Title Match** — Cross-reference title against Semantic Scholar API
4. **LLM Relevance Scoring** — Final LLM pass: "Does this paper support the claim in the paper we generated?"

Hallucinated references are auto-removed before export. Output: `verification_report.json` with per-citation pass/fail status and confidence scores.

### 3. Hardware-Aware Code Generation & Execution

**Mechanism**: Detect local compute, adapt experiment design.

- **GPU Detection**: NVIDIA CUDA (via `torch.cuda.is_available()`), Apple MPS (`torch.backends.mps.is_available()`), or CPU-only
- **Code Adaptation**: Package selection and import availability differ by tier (e.g., CUDA tier uses `torch` and `torchvision`; CPU tier uses only NumPy/scikit-learn)
- **Resource Estimation**: Pipeline estimates memory, compute time, and GPU VRAM before execution
- **Sandbox Execution**: Python code runs in isolated sandbox (AST-validated, immutable harness)
- **NaN/Inf Fast-Fail**: Detects NaN or Inf in metrics and halts experiment early

### 4. Self-Healing Experiment Code

**Mechanism**: Iterative repair with feedback loop.

- Runs experiment code in sandbox; captures stdout, stderr, and metrics
- If experiment fails (exception, NaN, runtime error):
  1. Parse error message
  2. Route to LLM with error context + original code
  3. LLM generates targeted fix
  4. Re-run in sandbox (up to 10 refinement cycles)
- Logs all repair attempts and final success/failure status

### 5. Multi-Agent Debate for Hypothesis Generation & Result Analysis

**Mechanism**: Structured perspective-taking without vote-counting.

- **Hypothesis Generation (Stage 8)**: Three synthetic personas (Optimist, Pessimist, Realist) independently propose hypotheses given the research gap; final hypothesis is union of perspectives
- **Result Analysis (Stage 14)**: Multi-agent analysis of experiment results; each agent scores on methodology soundness, result novelty, and evidence strength
- **Peer Review (Stage 18)**: Three independent reviewers generate critiques; paper is revised in response to each critique with explicit traceability

No democratic voting; instead, all perspectives are captured and rationales are preserved.

### 6. Autonomous PIVOT/REFINE Decision Loop

**Mechanism**: Stage 15 analyzes results and decides next action.

After experiments complete:
- **PROCEED** → advance to paper writing (Stage 16)
- **REFINE** → tweak hyperparameters, re-run experiments (jump to Stage 13), auto-versioning of artifacts
- **PIVOT** → new research direction identified, return to Stage 8 (Synthesis), new hypotheses generated

All versions are tagged and tracked in evolution history.

### 7. Self-Learning Across Runs (MetaClaw Integration)

**Mechanism**: Extract lessons from each run, inject into future runs.

When **MetaClaw bridge** is enabled (`metaclaw_bridge.enabled: true`):

1. After each run, extract lessons from:
   - Stage failures (decision rationale, runtime warnings)
   - Metric anomalies (NaN, Inf, convergence failures)
   - Citation mismatches (failed verification)
2. Convert lessons to reusable **skills** (prompts + examples) stored in `~/.metaclaw/skills/`
3. On next run, inject arc-* skills into all 23 stage prompts via LLM context overlay
4. Result: Documented +18.3% robustness improvement in controlled A/B experiments (stage retry rate -24.8%, refine cycles -40.0%)

Fully backward-compatible; off by default.

### 8. Conference-Grade Paper Export

**Mechanism**: Markdown-to-LaTeX pipeline with template switching.

- Supported templates: NeurIPS 2025, ICLR 2026, ICML 2026
- Output structure:
  - Introduction, Related Work, Method, Experiments, Results, Conclusion (5,000–6,500 words)
  - Auto-generated figures with error bars and confidence intervals
  - Inline citations: `\cite{key}` with matching `references.bib`
  - Mathematical typesetting: equations, tables, cross-references
- Anti-slop guards: NeurIPS/ICML checklist validation, disclaimer enforcement, fabrication detection

### 9. Domain-Specific Research Adapters

**Mechanism**: Research pipeline adapted per domain.

Eight domain adapters shipped:
- **Machine Learning**: typical PyTorch/scikit-learn imports, benchmarks (CIFAR-10, ImageNet)
- **Mathematics**: symbolic computation (SymPy), proof verification
- **Physics**: numerical simulation (Jax, SciPy), physical constants
- **Biology**: sequence analysis, omics tools, statistical tests
- **Chemistry**: molecular simulation, structure prediction
- **Economics**: time-series, causal inference, optimization
- **Security**: adversarial robustness, attack generation
- **Generic**: fallback for unmapped domains

Each adapter customizes literature search queries, experiment templates, and metric selection.

### 10. Multi-Agent Subsystems

**Mechanism**: Specialized agents for code, benchmarks, and figures.

- **CodeAgent** (Stage 10): Generates experiment code; coordinated with OpenCode Beast Mode for complex projects
- **BenchmarkAgent** (Stages 12–13): Searches and acquires public benchmarks; validates dataset availability; selects appropriate metrics
- **FigureAgent** (Stage 22): Generates publication-quality figures; includes style config, rendering, and critic feedback loop

---

## Technical Architecture

### Core Components

1. **Pipeline Executor** (`researchclaw/pipeline/executor.py`)
   - Implements 23-stage orchestration DAG
   - Manages stage transitions, gate checkpoints, and rollback on failure
   - Supports parallel stage execution (configurable `max_parallel_tasks`)

2. **LLM Client Layer** (`researchclaw/llm/`)
   - **OpenAI-compatible provider** (default): HTTP-based API with `base_url`, `api_key`, and model fallback chain
   - **ACP (Agent Client Protocol) adapter** (`acp_client.py`): Delegates to external coding agents (Claude Code, OpenCode, Codex, Gemini, Kimi) via `acpx` protocol
   - **Anthropic adapter** (`anthropic_adapter.py`): Direct integration for Anthropic models
   - Automatic fallback: if primary model fails, retry with fallback models in chain

3. **Literature Search & Verification** (`researchclaw/literature/`)
   - **OpenAlex client** (`openalex_client.py`): Real-time academic paper database, millions of papers
   - **Semantic Scholar adapter** (`semantic_scholar.py`): Title/abstract matching, citation graphs, author profiles
   - **arXiv client** (`arxiv_client.py`): Preprint server, direct arXiv ID lookup
   - **Citation verification** (`verify.py`): 4-layer pipeline (arXiv → CrossRef → Semantic Scholar → LLM)
   - **Novelty detection** (`novelty.py`): Detect and filter duplicate papers
   - **Cache** (`cache.py`): Local SQLite cache to reduce API calls and latency

4. **Experiment Sandbox** (`researchclaw/experiment/`)
   - **Python Sandbox** (`sandbox.py`): AST validation, immutable harness, capability restrictions (allowed imports)
   - **Docker Sandbox** (`docker_sandbox.py`): GPU-aware Docker execution; network policy-aware (setup_only, pip_only, full)
   - **SSH Remote** (`ssh_sandbox.py`): Delegate to remote GPU server (multi-GPU support)
   - **Colab Sandbox** (`colab_sandbox.py`): Google Colab integration
   - **Validator** (`validator.py`): Pre-execution code validation, AST safety checks
   - **Runner** (`runner.py`): Execute code, capture metrics, detect NaN/Inf, iterative repair trigger
   - **Evaluators** (convergence, metrics): Assess experiment results across multiple criteria

5. **Agent System** (`researchclaw/agents/`)
   - **BaseAgent** (`base.py`): Abstract base for all agents; defines `execute(context) -> AgentStepResult` interface
   - **AgentOrchestrator** (`base.py`): Coordinates multi-agent workflows with dependency management
   - **CodeAgent**, **BenchmarkAgent**, **FigureAgent**: Specialized subsystem orchestrators
   - Each agent receives context (prior stage outputs, knowledge base state, config) and returns structured results

6. **Knowledge Base** (`researchclaw/knowledge/base.py`)
   - Markdown-based KB tracked in `docs/kb/` (or Obsidian vault)
   - Six categories: decisions, experiments, findings, literature, questions, reviews
   - Per-run accumulation; time-decay aging for lessons (30-day window)
   - Queryable by pipeline stages for context injection

7. **MetaClaw Bridge** (`researchclaw/metaclaw_bridge/`)
   - **Config** (`config.py`): Proxy URL, skills directory, fallback API endpoint
   - **Lesson-to-Skill conversion** (`lesson_to_skill.py`): Extract structured lessons from run failures, convert to LLM prompts
   - **Stage skill map** (`stage_skill_map.py`): Map lessons to relevant pipeline stages for future injection
   - **Session** (`session.py`): Manage cross-run state, skill versioning, lesson history
   - **PRM gate** (`prm_gate.py`): Process reward model integration (optional)

8. **Template & Export** (`researchclaw/templates/`)
   - **Converter** (`converter.py`): Markdown → LaTeX AST transformation
   - **Conference** (`conference.py`): NeurIPS/ICLR/ICML template classes
   - **Compiler** (`compiler.py`): LaTeX compilation to PDF (if pdflatex installed)

9. **OpenCode Beast Mode Bridge** (`researchclaw/pipeline/opencode_bridge.py`)
   - Complexity scoring for generated experiment code
   - Auto-route complex code (multi-file, custom training loops, ablation studies) to OpenCode
   - Fallback to local code generation on OpenCode timeout or error
   - Configurable complexity threshold (0.0–1.0)

10. **Domain Adapters** (`researchclaw/domains/adapters/`)
    - Per-domain search query customization, import allowlists, metric selection
    - Pluggable architecture: new adapters can be added by subclassing `PromptAdapter`

### Data Flow

```
User Input (topic, config)
    ↓
Stage 1-2: Problem Decomposition
    ├─ LLM decomposes topic into research questions
    ├─ Stores structured questions in KB
    ↓
Stage 3-6: Literature Discovery & Screening
    ├─ Search queries → OpenAlex + Semantic Scholar + arXiv
    ├─ Dedup, screen by relevance, extract knowledge cards
    ├─ Gate: Human approval (Stage 5) or --auto-approve
    ├─ Stores papers in KB + references.bib (draft)
    ↓
Stage 7-8: Knowledge Synthesis
    ├─ Cluster papers, identify gaps
    ├─ Multi-agent debate: Hypothesis generation
    ├─ Stores hypotheses in KB
    ↓
Stage 9-11: Experiment Design & Code Gen
    ├─ Design experiment plan given hypotheses
    ├─ CodeAgent generates hardware-aware Python
    ├─ Gate: Human approval (Stage 9) or --auto-approve
    ├─ Stores code, resource estimates in KB
    ↓
Stage 12-15: Execution & Analysis
    ├─ Sandbox execution (Python/Docker/SSH)
    ├─ Self-healing repair on failure (up to 10 cycles)
    ├─ Multi-agent result analysis
    ├─ Stage 15: Autonomous PIVOT/REFINE/PROCEED decision
    ├─ Stores experiment runs, metrics, logs in KB + evolution/
    ↓
Stage 16-19: Paper Writing & Review
    ├─ Stage 16: Outline generation
    ├─ Stage 17: Section-by-section drafting
    ├─ Stage 18: Multi-agent peer review with evidence checks
    ├─ Stage 19: Revision with length guard
    ├─ Stores drafts + reviews in KB
    ↓
Stage 20-23: Quality Gate & Export
    ├─ Stage 20: 4-dimensional review scoring + NeurIPS checklist
    ├─ Stage 21: Archive KB into knowledge snapshot
    ├─ Stage 22: Markdown → LaTeX conversion, compile to PDF
    ├─ Stage 23: Citation verification (4-layer), export to deliverables/
    ├─ Stores final paper.tex + references.bib + verification_report.json
    ↓
Output to artifacts/rc-{timestamp}-{hash}/deliverables/
    ├─ paper_draft.md
    ├─ paper.tex + paper.pdf
    ├─ references.bib
    ├─ verification_report.json
    ├─ experiment_runs/ (generated code + results)
    ├─ charts/ (figures with error bars)
    ├─ reviews.md (multi-agent critique)
    ├─ evolution/ (self-learning lessons)
    └─ knowledge_base/ (snapshot of KB)
```

---

## Installation & Usage

### Quick Start

```bash
# 1. Clone and install
git clone https://github.com/aiming-lab/AutoResearchClaw.git
cd AutoResearchClaw
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Setup (installs OpenCode, checks Docker/LaTeX)
researchclaw setup

# 3. Interactive config
researchclaw init   # Prompts for LLM provider, creates config.arc.yaml
# OR manually copy config
cp config.researchclaw.example.yaml config.arc.yaml

# 4. Run
export OPENAI_API_KEY="sk-..."
researchclaw run --config config.arc.yaml --topic "Your research idea" --auto-approve
```

**Minimum Config** (`config.arc.yaml`):

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

### Advanced: ACP Protocol (No API Key Required)

Run with Claude Code or any ACP-compatible coding agent:

```yaml
# config.yaml
llm:
  provider: "acp"
  acp:
    agent: "claude"   # or codex, gemini, opencode, kimi
    cwd: "."
```

```bash
researchclaw run --config config.yaml --topic "Your research idea" --auto-approve
```

### Integration with OpenClaw

AutoResearchClaw is OpenClaw-compatible. From OpenClaw chat:

```
"Research [your topic]"
```

OpenClaw auto-reads `RESEARCHCLAW_AGENTS.md`, clones, installs, configures, and runs the pipeline. All outputs returned in chat.

---

## Relevance to Claude Code Development

AutoResearchClaw demonstrates three high-impact patterns for Claude Code agents:

### 1. **Multi-Agent Orchestration with Dependency Management**

The pipeline's 23 stages form a DAG with gates, loops, and autonomous decision points. Claude Code agents can learn from this for coordinating complex workflows:
- Stage dependencies prevent premature execution
- Gate stages demonstrate human-in-the-loop integration
- PIVOT/REFINE loops show how agents can re-route based on intermediate results

**Use Case for Claude Code**: Building research assistants, code review pipelines, or autonomous refactoring workflows that adapt based on intermediate feedback.

### 2. **Self-Healing & Iterative Repair**

The experiment sandbox's self-healing loop (up to 10 repair cycles with targeted LLM feedback) is a pattern for robust agent-generated code:
- Capture execution errors in structured format
- Route error + context back to LLM with repair prompt
- Re-execute and evaluate
- Provide fallback on repeated failure

**Use Case for Claude Code**: Autonomous code generation tasks where first-pass code may be imperfect; agents can improve code quality without human intervention.

### 3. **Knowledge Base as Persistent Context**

The KB tracks decisions, experiments, findings, and lessons across runs. Persistent context enables:
- Cross-run learning (what failed before, what succeeded)
- Explicit audit trails (why was this decision made)
- Time-decay freshness (old lessons gradually deprioritized)

**Use Case for Claude Code**: Long-running research or development projects where agents need persistent memory of prior decisions and failures to make better choices.

---

## Limitations and Caveats

1. **LLM Model Quality Dependency** — Paper quality directly depends on the primary LLM model. Weaker models (e.g., GPT-3.5) produce lower-quality papers. Fallback chain only helps on API failures, not on inherent model limitation.

2. **Experiment Complexity Limits** — OpenCode Beast Mode handles complex experiments, but very large ML projects (distributed training, hyperparameter sweeps) may exceed generation capacity. Remote SSH mode has not been tested with multi-GPU setups at scale.

3. **Citation Verification Not Foolproof** — 4-layer verification catches most hallucinations, but a clever hallucination that passes all four gates cannot be ruled out. Semantic Scholar API rate limits may cause occasional verification failures (circuit breaker in place).

4. **Sandbox Execution Restrictions** — Python sandbox only allows a hardcoded import list (math, random, json, numpy, torch, sklearn). Experiments requiring uncommon packages may fail. Docker mode is more permissive but slower.

5. **Conference Template Coverage** — Only NeurIPS 2025, ICLR 2026, ICML 2026 are supported. Other conferences require custom template definition.

6. **No Live Web Search by Default** — Literature search uses APIs to academic databases (OpenAlex, Semantic Scholar, arXiv); live web search requires OpenClaw bridge integration (`use_web_fetch: true`). Standalone mode is limited to academic literature.

7. **Rejection Handling** — Gate stages (5, 9, 20) pause for human approval. Rejection triggers rollback, but the rollback mechanism preserves prior artifacts; large failed runs generate significant disk usage.

8. **MetaClaw Bridge Requires External Proxy** — Cross-run learning via MetaClaw requires a running MetaClaw proxy (`http://localhost:30000`). Fallback to direct LLM works, but lessons are not persisted across runs without MetaClaw.

9. **No Multi-Topic Orchestration** — Pipeline is single-topic per run. Batch research on multiple topics requires multiple invocations; no built-in scheduler or multi-run coordination.

---

## References

- **GitHub Repository**: <https://github.com/aiming-lab/AutoResearchClaw> (accessed 2026-03-19)
- **README.md**: Full feature documentation, quick start, configuration reference
- **Integration Guide**: `docs/integration-guide.md` — OpenClaw and MetaClaw integration patterns
- **Testing Guide**: `docs/TESTER_GUIDE.md` — instructions for community feedback
- **License**: MIT License (LICENSE file)
- **PyPI Package**: `researchclaw` v0.3.1
- **Official Docs**: <https://github.com/aiming-lab/AutoResearchClaw/docs/>
- **OpenClaw Compatibility**: Declared in README; compatible with Claude Code, OpenCode, Codex, Gemini, Kimi via ACP protocol
- **MetaClaw Integration**: <https://github.com/aiming-lab/MetaClaw> — cross-run learning framework
- **Test Coverage**: 1,634 tests in `tests/` directory, 100% pass rate as of 2026-03-19

---

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|-----------|-------------|------------|
| Identity/Metadata | high | 2026-03-19 | 2026-06-19 |
| Key Statistics | high | 2026-03-19 (GitHub API) | 2026-06-19 |
| Problem Addressed | high | 2026-03-19 (README) | 2026-06-19 |
| Key Features | high | 2026-03-19 (README + SKILL.md context) | 2026-06-19 |
| Architecture | high | 2026-03-19 (source code structure + README) | 2026-06-19 |
| Installation & Usage | high | 2026-03-19 (README quick start) | 2026-06-19 |
| Limitations | medium | 2026-03-19 (README + source code review) | 2026-06-19 |
| References | high | 2026-03-19 (GitHub API + local files) | 2026-06-19 |

**Overall Confidence**: HIGH — All sections sourced from official README, GitHub API metadata, and repository structure inspection. Latest release v0.3.1 (2026-03-18) reviewed in full.

**Next Review Date**: 2026-06-19 (3 months from today)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Gas Town](../research-agent-patterns/gastown.md) | research-agent-patterns | Shared multi-agent orchestration architecture: persistent state management, supervisor-worker coordination, terminal-based session transport for autonomous development workflows |
| [Oh My OpenCode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Parallel multi-agent execution with category-based model routing; both systems route specialized agents based on task type rather than user selection |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | 16-agent orchestration system with specialized subagents and hook-based automation; mirrors AutoResearchClaw's multi-agent subsystem architecture |
| [LiteAgents](../agent-frameworks/liteagents.md) | agent-frameworks | 11-agent framework with orchestrator routing and session memory pipeline; both systems implement intent-to-agent routing for workflow coordination |
| [OpenHands](../coding-agents/openhands.md) | coding-agents | Sandbox code execution with iterative repair patterns; both systems generate code, execute in isolated environments, and auto-recover from execution failures |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | Persistent cross-session knowledge base with progressive disclosure; both systems maintain learnings across runs to improve future performance |
| [The Claw Loop](../research-agent-patterns/claw-loop.md) | research-agent-patterns | Autonomous orchestration via supervisor agent polling; both implement fail-gracefully principles with automatic state recovery and context clearing |

---

## Entry Metadata

- **Category**: agent-infrastructure
- **Created**: 2026-03-19
- **Last Updated**: 2026-03-19
- **Resource Name**: AutoResearchClaw
- **Author**: aiming-lab organization
- **Repository URL**: <https://github.com/aiming-lab/AutoResearchClaw>
