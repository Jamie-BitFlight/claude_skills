# AI Agents Frameworks - Comparative Learning Repository

**Research Date**: 2026-01-31
**Source URL**: <https://github.com/martimfasantos/ai-agents-frameworks>
**GitHub Repository**: <https://github.com/martimfasantos/ai-agents-frameworks>
**Version at Research**: Main branch (pushed 2026-01-24)
**License**: Not specified (no LICENSE file)

---

## Overview

AI Agents Frameworks is a hands-on learning repository that provides practical implementations and comprehensive benchmarks comparing 10 state-of-the-art AI agent frameworks. The repository enables developers to explore, test, and compare modern agent architectures through working examples ranging from simple "hello world" agents to complex multi-agent workflows with RAG and API integrations.

**Core Value Proposition**: Side-by-side comparison of agent frameworks using consistent benchmarks for response time, token usage, memory effects, and tool utilization accuracy.

---

## Problem Addressed

| Problem                                                                           | How This Repository Solves It                                                                |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Framework selection paralysis - too many agent frameworks with unclear trade-offs | Quantitative benchmarks comparing response time, tokens, and reliability across frameworks   |
| Learning curves for each framework require separate documentation exploration     | Unified example structure with progressive complexity (hello_world -> multi-agent workflows) |
| Unknown memory and scaling characteristics of agent frameworks                    | Explicit memory vs no-memory benchmarks showing performance degradation patterns             |
| Unclear tool integration reliability across frameworks                            | RAG and API integration tests with "miss rate" metrics (failed retrievals/tool calls)        |
| Framework-specific idioms obscure core agent patterns                             | Consistent agent designs across frameworks highlight paradigm differences                    |

---

## Key Statistics (as of 2026-01-31)

| Metric             | Value            |
| ------------------ | ---------------- |
| GitHub Stars       | 354              |
| Forks              | 43               |
| Contributors       | 1                |
| Open Issues        | 4                |
| Open Pull Requests | 0                |
| Primary Language   | Jupyter Notebook |
| Frameworks Covered | 10               |
| Created            | 2025-01-21       |
| Last Updated       | 2026-01-31       |

---

## Frameworks Covered

| Framework         | Organization | Documentation                                           | GitHub                                           |
| ----------------- | ------------ | ------------------------------------------------------- | ------------------------------------------------ |
| AG2               | AG2AI        | <https://docs.ag2.ai/latest/>                           | <https://github.com/ag2ai/ag2>                   |
| Agno              | Agno AGI     | <https://docs.agno.com/introduction>                    | <https://github.com/agno-agi/agno>               |
| Autogen           | Microsoft    | <https://microsoft.github.io/autogen/stable/index.html> | <https://github.com/microsoft/autogen>           |
| CrewAI            | CrewAI Inc   | <https://docs.crewai.com/>                              | <https://github.com/crewAIInc/crewAI>            |
| Google ADK        | Google       | <https://google.github.io/adk-docs/>                    | <https://github.com/google/adk-python>           |
| LangGraph         | LangChain    | <https://langchain-ai.github.io/langgraph/>             | <https://github.com/langchain-ai/langgraph>      |
| LlamaIndex        | LlamaIndex   | <https://docs.llamaindex.ai/en/stable/>                 | <https://github.com/run-llama/llama_index>       |
| OpenAI Agents SDK | OpenAI       | <https://openai.github.io/openai-agents-python/>        | <https://github.com/openai/openai-agents-python> |
| Pydantic-AI       | Pydantic     | <https://ai.pydantic.dev/>                              | <https://github.com/pydantic/pydantic-ai>        |
| smolagents        | Hugging Face | <https://huggingface.co/docs/smolagents/en/index>       | <https://github.com/huggingface/smolagents>      |

---

## Key Features

### Example Coverage by Framework

Each framework directory contains numbered, progressive examples:

**CrewAI Examples** (14 examples):

- hello_world, tools, built_in_tools, streaming
- structured_outputs, tasks, callbacks, memory
- reasoning, knowledge, multi_agent_collaboration
- flows, flows_with_agents, crew_simplification

**Pydantic-AI Examples** (11 examples):

- hello_world, tools_and_metrics, built_in_tools
- streaming, structured_outputs, output_validators
- message_history, agent_delegation
- programmatic_handoff, stateful_graphs, human_in_the_loop

**OpenAI Agents SDK Examples** (9 examples):

- hello_world, tools_and_metrics, structured_outputs
- parallelization_in_workflow, handoffs_and_streaming
- agents_as_tools, output_guardrails, llm_as_a_judge, tracing

**LangGraph/LlamaIndex/Agno**: Similar progressive example structure

### Unified Benchmark Study

The `study-agents-differences/` directory provides:

1. **Unified Agent Interfaces**: Consistent implementation across Agno, LangGraph, LlamaIndex, OpenAI, Pydantic-AI
2. **Performance Metrics**: Response time, token usage, tool utilization
3. **Configurable Benchmarks**: Memory on/off, agent recreation per iteration
4. **Streamlit UI**: Interactive comparison interface (`streamlit run agent-ui.py`)

### Benchmark Categories

| Benchmark Type                 | What It Measures                                      |
| ------------------------------ | ----------------------------------------------------- |
| Response Time (with Memory)    | Performance degradation as conversation history grows |
| Response Time (without Memory) | Baseline cold-start performance                       |
| Token Usage                    | Input/output token efficiency                         |
| RAG Performance                | Retrieval accuracy and latency                        |
| API Integration                | Multi-tool orchestration reliability                  |
| Miss Rate                      | Tool call failures and hallucinations                 |

---

## Technical Architecture

### Benchmark Infrastructure

```text
study-agents-differences/
├── *_agent.py              # Framework-specific agent implementations
├── *_rag_api_agent.py      # RAG + API integrated variants
├── prompts.py              # Consistent system prompts across agents
├── settings.py             # Shared configuration
├── shared_functions/       # Reusable tool implementations
├── knowledge_base/         # RAG vector store data
├── tests/                  # Benchmark output files
└── agent-ui.py             # Streamlit comparison interface
```

### Benchmark Command Pattern

```bash
python llama_index_rag_api_agent.py \
  --mode metrics-loop \
  --iter 30 \
  --create \
  --no-memory \
  --verbose \
  --file tests/test100_llamaindex_rag.txt
```

**Flags**:

- `--provider [azure|openai|other]`: LLM backend
- `--mode [None|metrics|metrics-loop]`: Execution mode
- `--iter [int]`: Iteration count for loops
- `--no-memory`: Disable conversation memory
- `--create`: Recreate agent instance per iteration
- `--file [path]`: Output results file

---

## Benchmark Results Summary

### Response Time with Memory (100 iterations)

| Framework  | Time (seconds) | Notes                                          |
| ---------- | -------------- | ---------------------------------------------- |
| LlamaIndex | 2.64 +/- 2.29  | Fastest, direct answers                        |
| Agno       | 4.39 +/- 0.73  | Consistent, markdown formatting                |
| LangGraph  | 9.45 +/- 4.73  | Memory bottleneck - degrades with history size |

**Key Finding**: LangGraph shows significant performance degradation as conversation history grows. At iteration 100, performance drops substantially due to memory overhead.

### Response Time without Memory (100 iterations)

| Framework  | Time (seconds) |
| ---------- | -------------- |
| LangGraph  | 3.31 +/- 0.59  |
| OpenAI     | 3.61 +/- 0.83  |
| LlamaIndex | 3.63 +/- 0.66  |
| Agno       | 4.28 +/- 0.76  |

**Key Finding**: Without memory, all frameworks perform similarly. LangGraph's memory implementation is the primary performance differentiator.

### Token Usage Comparison

| Framework  | Prompt Tokens | Completion Tokens | Total  |
| ---------- | ------------- | ----------------- | ------ |
| OpenAI     | 1888.5        | 58.3              | 1946.7 |
| LangGraph  | 1946.1        | 53.5              | 1999.7 |
| Agno       | 1999.2        | 65.3              | 2064.5 |
| LlamaIndex | 2121.7        | 76.9              | 2198.6 |

**Key Finding**: Token usage heavily depends on system prompt design. OpenAI and LangGraph are most token-efficient.

### RAG Performance (100 iterations)

| Framework  | Time (s)      | Tokens | Miss Rate |
| ---------- | ------------- | ------ | --------- |
| LangGraph  | 2.68 +/- 1.35 | 4877.2 | 4%        |
| LlamaIndex | 2.86 +/- 1.05 | 3279.9 | 2%        |
| Agno       | 3.30 +/- 0.75 | 4439.3 | 2%        |

**Key Finding**: LlamaIndex achieves best token efficiency for RAG. All frameworks show <5% miss rate for retrieval tasks.

### API Integration (100 iterations, multi-tool prompt)

| Framework  | Time (s)      | Tokens | Miss Rate |
| ---------- | ------------- | ------ | --------- |
| LangGraph  | 4.24 +/- 1.35 | 1412.2 | 0%        |
| Agno       | 5.49 +/- 1.40 | 1849.2 | 0%        |
| LlamaIndex | 6.41 +/- 2.47 | 3913.4 | 0%        |

**Key Finding**: LangGraph excels at multi-tool orchestration with lowest token overhead. LlamaIndex requires prompt tuning for complex tool scenarios.

---

## Installation and Usage

### Quick Start

```bash
# Clone repository
git clone https://github.com/martimfasantos/ai-agents-frameworks.git
cd ai-agents-frameworks

# Navigate to specific framework
cd crewai  # or langgraph, pydantic-ai, etc.

# Check framework-specific README
cat README.md

# Install dependencies (varies by module)
pip install -r requirements.txt  # or use PDM/uv as specified
```

### Running Benchmarks

```bash
cd study-agents-differences

# Create environment
python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys

# Run Streamlit UI for interactive comparison
streamlit run agent-ui.py
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Agent Design Patterns**: Working examples of tool integration, memory management, and multi-agent coordination applicable to Claude Code agent development
2. **Benchmark Methodology**: Reproducible framework for comparing Claude Code sub-agent configurations and delegation strategies
3. **Memory Trade-offs**: Empirical data on memory impact showing when stateless agents outperform stateful ones
4. **Tool Integration Patterns**: RAG and API integration examples transferable to MCP tool development

### Patterns Worth Adopting

1. **Progressive Example Structure**: Numbered examples from simple to complex (hello_world -> multi_agent) for skill documentation
2. **Consistent Benchmark CLI**: Standardized flags (`--mode`, `--iter`, `--no-memory`) for reproducible testing
3. **Miss Rate Metric**: Tracking tool call failures as reliability indicator for agent evaluation
4. **Memory Impact Testing**: Explicit with/without memory comparisons to inform delegation decisions
5. **Streamlit Comparison UI**: Interactive framework for evaluating agent configurations

### Integration Opportunities

1. **Benchmark Adaptation**: Adapt benchmark methodology for Claude Code sub-agent performance testing
2. **Memory Guidelines**: Use findings to inform when to use stateless vs stateful agents in orchestration
3. **Tool Design**: Apply token efficiency patterns from RAG/API benchmarks to MCP tool design
4. **Example Template**: Use progressive example structure for skill documentation

### Key Insights for Claude Code

| Finding                                               | Implication for Claude Code                               |
| ----------------------------------------------------- | --------------------------------------------------------- |
| Memory degrades LangGraph by 3x at 100 iterations     | Prefer stateless sub-agents for long-running tasks        |
| LlamaIndex most token-efficient for RAG               | RAG tool implementations should minimize context overhead |
| System prompts dominate token usage                   | Invest in prompt optimization before scaling              |
| Multi-tool orchestration varies 50% across frameworks | Sub-agent tool bundles need careful benchmarking          |
| All frameworks achieve <5% RAG miss rate              | Retrieval reliability is framework-independent            |

---

## References

1. **GitHub Repository**: <https://github.com/martimfasantos/ai-agents-frameworks> (accessed 2026-01-31)
2. **Study Methodology**: study-agents-differences/README.md (accessed 2026-01-26)
3. **Author Profile**: Martim Santos, daredata.ai - <https://martimfasantos.github.io>

### Framework Documentation (accessed 2026-01-26)

- AG2: <https://docs.ag2.ai/latest/>
- Agno: <https://docs.agno.com/introduction>
- Autogen: <https://microsoft.github.io/autogen/stable/index.html>
- CrewAI: <https://docs.crewai.com/>
- Google ADK: <https://google.github.io/adk-docs/>
- LangGraph: <https://langchain-ai.github.io/langgraph/>
- LlamaIndex: <https://docs.llamaindex.ai/en/stable/>
- OpenAI Agents SDK: <https://openai.github.io/openai-agents-python/>
- Pydantic-AI: <https://ai.pydantic.dev/>
- smolagents: <https://huggingface.co/docs/smolagents/en/index>

---

## Freshness Tracking

| Field                        | Value                 |
| ---------------------------- | --------------------- |
| Last Verified                | 2026-01-31            |
| Last Push at Verification    | 2026-01-24            |
| GitHub Stars at Verification | 354                   |
| Forks at Verification        | 43                    |
| Next Review Recommended      | 2026-04-30 (3 months) |

**Change Detection Indicators**:

- Monitor GitHub releases and commits for new framework additions
- Check for updated benchmark results
- Review issues for methodology changes
- Track star growth indicating community adoption
- Watch for new framework integrations (Claude SDK, etc.)
