---
title: HyperAgents
subtitle: Self-referential self-improving agents for autonomous optimization
slug: hyperagents
repository: https://github.com/facebookresearch/HyperAgents
license: CC BY-NC-SA 4.0
authors:
  - Jenny Zhang
  - Bingchen Zhao
  - Wannan Yang
  - Jakob Foerster
  - Jeff Clune
  - Minqi Jiang
  - Sam Devlin
  - Tatiana Shavrina
published_date: "2026-03-23"
---

## Overview

HyperAgents is a research framework from Meta (formerly Facebook) that implements self-referential self-improving agents capable of optimizing for any computable task. The system uses two primary agent types: a Meta Agent that iteratively improves the codebase, and Task Agents that solve domain-specific problems. The framework supports multiple evaluation domains including code synthesis, reinforcement learning, mathematical proof generation, and text-to-image generation, with experimental results tracked via Docker containerization and artifact storage.

SOURCE: GitHub README (<https://github.com/facebookresearch/HyperAgents>, accessed 2026-03-29)
arXiv paper metadata (Zhang et al., eprint:2603.19461, year 2026)

## Problem Addressed

HyperAgents addresses the fundamental challenge of developing AI systems that can autonomously improve their own capabilities and adapt to novel tasks. Rather than static models deployed after training, HyperAgents implements agents that can modify their own codebase, evaluate improvements through domain-specific metrics, and iterate based on performance feedback. This approach is particularly valuable for research into agent scalability, transfer learning, and the limits of model-driven self-improvement across diverse computational domains.

SOURCE: Abstract from arXiv badge and project description (2603.19461)

## Key Statistics

- **License**: CC BY-NC-SA 4.0 (noncommercial, attribution required, share-alike)
- **Primary language**: Python 3.12+
- **Latest commit**: March 23, 2026 ("adding paper citation")
- **Model support**: OpenAI (GPT series), Anthropic Claude, Google Gemini (via LiteLLM abstraction)
- **Domains**: 6 (Balrog, Genesis, IMO proof, paper review, polyglot coding, search arena)
- **Primary framework**: Docker containerization for isolated task evaluation

SOURCE: Repository metadata (README.md, requirements.txt, LICENSE.md accessed 2026-03-29)
Last commit date from git log (accessed 2026-03-29)

## Key Features

### Agent Architecture
Two-tier agent design with distinct responsibilities:
- **MetaAgent** (`meta_agent.py`): Receives instruction "Modify any part of the codebase at `{repo_path}`" and generates code modifications using all available tools. Uses `chat_with_agent` from `llm_withtools.py` with `tools_available='all'` parameter. Maintains `msg_history` across iterations to enable sequential improvement.
- **TaskAgent** (`task_agent.py`): Solves individual domain tasks with structured JSON response format. Receives `inputs` dict containing `domain` field and task-specific parameters. Returns `(prediction, msg_history)` tuple where prediction is extracted from agent response or defaults to "None" on extraction failure.

SOURCE: meta_agent.py lines 1-18, task_agent.py lines 1-44 (code read)

### Tool System
Foundation model agents operate with a unified tool interface supporting:
- **Bash execution** (`agent/tools/bash.py`): Execute shell commands in domain environments
- **File editing** (`agent/tools/edit.py`): Modify source code with precise edits
- **LLM tool use protocol** (`llm_withtools.py`): Agents format tool calls as `<json>{"tool_name": ..., "tool_input": ...}</json>` blocks. Parser validates JSON structure and requires both `tool_name` and `tool_input` fields. Supports retry logic when tool use markers appear near output boundary (2000+ character responses ending with incomplete tool JSON).

SOURCE: llm_withtools.py lines 7-80 (tool protocol), agent/tools/ directory structure (code read)

### Multi-Domain Evaluation
Six independent domain implementations under `domains/`:

1. **Balrog** (text RL / game playing): Environments include BabyAI (text-based), Crafter (resource management), MiniHack (dungeon exploration), NetHack Learning Environment (NLE), TextWorld (interactive fiction). Dataset-driven evaluation with configurable task splits.

2. **Genesis** (embodied robotics): Go2 hopping and walking control tasks. Differentiable simulation with RL training via `rsl_rl_lib`. Reward functions are Python files in `reward_functions/` directory enabling agent-driven reward design optimization.

3. **IMO** (mathematical proofs): Proof generation and auto-grading for International Math Olympiad problems. Proof verifier based on Lean proof assistant. Includes subset curation to control evaluation scope.

4. **Paper Review**: Document classification and analysis domain with subset curation.

5. **Polyglot** (code synthesis): Multi-language code generation tasks across diverse programming languages. Staged evaluation with small/medium subset progression (pass threshold: 0.4 on small subset triggers medium subset eval). Docker-per-task isolation for safe execution.

6. **Search Arena**: (domain purpose from structure indicates search-based task evaluation).

SOURCE: domains/ directory structure, domain harness implementations (domain configuration read)
generate_loop.py lines 49-77 (polyglot evaluation with staged eval threshold documented)

### Evolutionary Loop
`generate_loop.py` implements the core optimization algorithm:
- **Parent selection**: Selects highest-scoring previous agent variant as the base for next iteration
- **Patch application**: Meta Agent modifications are captured as diffs; applied to parent codebase via `apply_diffs_container`
- **Evaluation cascade**: Staged evaluation for efficiency (small→medium→large test sets with pass/fail gates)
- **Archive management**: Experiment logs stored as multi-part ZIP archive (`outputs_os_parts.zip`) with splitting/joining utilities for large datasets
- **Metadata tracking**: Node-level metadata (e.g., `run_full_eval` flag) records which evaluation path was taken

SOURCE: generate_loop.py lines 49-97 (harness_polyglot architecture, staged eval threshold)
README.md (archive extraction procedure documented)

## Technical Architecture

### Core Components and Data Flow

```
Input Domain Task
    ↓
[TaskAgent.forward(inputs)]
    ├─ Formats task as structured prompt with JSON schema
    ├─ Calls chat_with_agent with model and empty msg_history
    └─ Extracts JSON response, returns (prediction, msg_history)
    ↓
Domain Evaluator (domain-specific harness)
    ├─ Runs task in Docker container (polyglot) or native env (balrog/genesis/imo)
    └─ Computes numerical score
    ↓
[Agent Improvement Loop]
    ├─ MetaAgent.forward(repo_path, eval_path, iterations_left)
    ├─ Generates patches for codebase (tools: bash, file edit)
    └─ Applies patches via git diff/apply
    ↓
[Re-evaluation]
    ├─ Runs same task suite against modified code
    └─ Compares score against parent
    ↓
[Parent Selection & Archive]
    ├─ If improved: save as new parent for next iteration
    ├─ If not improved: retain current parent
    └─ Archive all logs, diffs, metadata
```

### LLM Integration Layer
`agent/llm.py` and `agent/llm_withtools.py` provide unified interface to multiple model providers:
- **Model abstraction**: `OPENAI_MODEL` constant with per-domain overridable selection
- **LiteLLM backend** (v1.74.9 in requirements): Routes requests to OpenAI, Anthropic, Gemini via `litellm` library. API key configuration via `.env` file (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).
- **Message history tracking**: Both agents maintain `msg_history` list of dicts with `text` field. Each agent call appends model response.
- **Tool-use loop**: `chat_with_agent` function iterates: model response → check for tool use → execute tool → append result to history → repeat until no more tools or context limit reached.

SOURCE: agent/base_agent.py (AbsractAgentSystem, model field), agent/llm.py (model abstraction), requirements.txt litellm==1.74.9
README setup section (API key configuration)

### Containerization Strategy
Docker containerization provides:
- **Sandboxing**: Each polyglot code task runs in isolated container
- **Compilation safety**: Run commands to check code compiles before evaluation (`run_commands_to_check_compilation`)
- **Output capture**: Logs streamed from container via docker SDK with safe logging (`safe_log`)
- **Ephemeral instances**: Containers cleaned up after task completion (`cleanup_container`)

SOURCE: generate_loop.py imports (docker, build_container, copy_to/from_container, cleanup_container)
utils/docker_utils.py module structure (code read)

### State and Logging
- **Chat history**: Per-agent execution history saved to markdown file (default: `./outputs/chat_history.md`)
- **Thread-safe logging**: `ThreadLoggerManager` stores logs in thread-local storage for parallel execution
- **Experiment outputs**: Saved to `outputs/` directory by default, organized by generation ID

SOURCE: agent/base_agent.py lines 10-20 (chat_history_file, ThreadLoggerManager)

## Installation & Usage

### Prerequisites
```bash
# System dependencies (Fedora/RHEL)
sudo dnf install -y python3.12-devel graphviz graphviz-devel cmake ninja-build bzip2-devel zlib-devel ncurses-devel libffi-devel
# Ubuntu/Debian equivalents: build-essential, graphviz, libgraphviz-dev, cmake, ninja-build, etc.

# For Genesis (robotics): CUDA 12.x required (installed separately in Dockerfile)
```

SOURCE: README.md setup section

### Setup
```bash
# Create environment file with API keys
cat > .env << EOF
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
EOF

# Create Python 3.12 virtual environment
python3.12 -m venv venv_nat
source venv_nat/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_dev.txt

# Run initial agent setup
bash ./setup_initial.sh

# Optional: build Docker image for containerized evaluation
docker build --network=host -t hyperagents .
```

SOURCE: README.md setup section (lines 21-48)

### Running Experiments
```bash
# Execute optimization loop for specified domain(s)
python generate_loop.py --domains <domain>

# Outputs saved to outputs/ directory by default
```

Available domains: `balrog`, `genesis`, `imo`, `paper_review`, `polyglot`, `search_arena`

SOURCE: README.md running section
generate_loop.py (domain argument handling)

### Analyzing Results
```bash
# Extract multi-part archived logs
zip -s 0 outputs_os_parts.zip --out unsplit_logs.zip
unzip unsplit_logs.zip

# Plot experiment progress across generations
python analysis/plot_progress.py
python analysis/plot_comparison.py

# Visualize archived run data
python analysis/visualize_archive.py
```

SOURCE: README.md logs section

## Limitations and Caveats

### Code Execution Safety
The system executes untrusted model-generated code. While implementation includes sandboxing via Docker and safety mechanisms like compilation checks, model-generated code may still behave destructively due to model capability limitations or alignment issues. The repository explicitly warns: "By using this repository, you acknowledge and accept these risks."

SOURCE: README.md safety consideration section (lines 77-79)

### Evaluation Scope and Reproducibility
- Staged evaluation with pass/fail thresholds (e.g., polyglot 0.4 threshold) may introduce variability in which tasks are fully evaluated
- Archive extraction procedure is multi-part ZIP splitting, adding operational complexity to result retrieval
- Domain-specific configurations scattered across separate `domains/*/` directories may require significant setup per domain

### Model Dependency
Framework delegates all reasoning to external LLM APIs (OpenAI, Anthropic, Gemini via LiteLLM). Performance and cost directly tied to model selection and API availability. No offline or local model defaults provided.

### Unresolved Questions from Source Review
Source code review did not explicitly document:
- Mechanism for handling multi-iteration improvement (iterations_left parameter in MetaAgent not fully traced through generate_loop.py)
- Detailed description of how parent selection works across domains (referenced as `select_parent` function but implementation not fully inspected)
- Specific constraints on max patch size or codebase modification scope

## Relevance to Claude Code Development

### Applicable Patterns
1. **Self-improving agent architecture**: The two-tier design (MetaAgent modifying code, TaskAgent solving tasks) is directly applicable to autonomous agent systems that must improve their own prompt engineering, tool definitions, or execution strategy.

2. **Tool-use protocol standardization**: The `<json>{"tool_name": ..., "tool_input": ...}</json>` format and retry logic for incomplete tool calls provide a reference implementation for robust tool invocation in streaming LLM contexts.

3. **Domain-driven evaluation**: The modular domain architecture (six independent environments) demonstrates how to design extensible evaluation frameworks where new task domains can be added without modifying core agent logic. Directly applicable to multi-task agent frameworks.

4. **Containerized safe execution**: Docker-based code execution with compilation checks provides a concrete pattern for safely executing agent-generated code without exposing the host system.

### Use Cases for Claude Code Agents
- Building agents that autonomously improve their own task decomposition strategies
- Implementing evaluation harnesses for multi-domain agent benchmarking
- Creating tool systems that agents can modify and optimize
- Designing safety-critical code generation workflows where agent-produced code must be validated before execution

## References

- **arXiv**: Zhang, J., Zhao, B., Yang, W., Foerster, J., Clune, J., Jiang, M., Devlin, S., Shavrina, T. "HyperAgents." arXiv:2603.19461 (2026). <https://arxiv.org/abs/2603.19461>
- **Blog post**: <https://ai.meta.com/research/publications/hyperagents/>
- **GitHub repository**: <https://github.com/facebookresearch/HyperAgents> (CC BY-NC-SA 4.0 license)
- **X (Twitter) announcement**: <https://x.com/jennyzhangzt/status/2036099935083618487>

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [OpenHands - Open Platform for Cloud Coding Agents](./openhands.md) | coding-agents | Autonomous coding agent platform with multi-domain task execution and evaluation benchmarking (SWE-bench) |
| [OpenAI Codex CLI - OpenAI's Terminal Coding Agent](./openai-codex-cli.md) | coding-agents | Agent execution with tool use protocol, sandbox isolation, and iterative code generation model |
| [Cline - Open-Source Autonomous Coding Agent](./cline.md) | coding-agents | Multi-step autonomous coding with tool integration and MCP extensibility for agent-driven improvements |
| [OpenAI Symphony](./openai-symphony.md) | coding-agents | Continuous agent automation loop: issue-driven dispatch, workspace isolation, and autonomous iteration |
| [Agno](../agent-frameworks/agno.md) | agent-frameworks | Learning agents with persistent memory, knowledge transfer across users, and multi-agent orchestration |
| [AgentScope - Alibaba's Multi-Agent Framework](../agent-frameworks/agentscope.md) | agent-frameworks | Actor-model multi-agent architecture with built-in agent introspection and prompt tuning |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Agent optimization system: 16 specialized subagents, 65+ skills, learning-based improvements from session patterns |
| [TrainLoop - Managed RL Fine-Tuning Platform](../ml-infrastructure/trainloop.md) | ml-infrastructure | Reinforcement learning for domain-specific agent improvement with reward model training and deployment |

---

## Freshness Tracking

**Entry created**: 2026-03-29
**Last reviewed**: 2026-03-29
**Next review recommended**: 2026-06-29 (3 months)

### Confidence Assessment

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Direct read of README, arXiv citation metadata from official badges |
| Problem Addressed | high | Extracted from official abstract and project description |
| Key Statistics | high | Repository metadata (commit dates), license file text, requirements.txt dependencies dated |
| Key Features | high | Full code read of meta_agent.py, task_agent.py, llm_withtools.py; domain structure inspected |
| Technical Architecture | high | Component-level code inspection with explicit source citations |
| Installation & Usage | high | Direct extraction from README.md setup and run instructions |
| Limitations | high | Safety warning from README (lines 77-79); design constraints inferred from code structure |
| Relevance | medium | Applicability assessment based on architecture patterns observed; specific use case coverage not explicitly documented in sources |

### Changes from Previous Version
N/A — entry created on 2026-03-29, no prior version exists.
