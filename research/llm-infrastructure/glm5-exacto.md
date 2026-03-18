# GLM-5:exacto via OpenRouter

**Research Date**: 2026-03-18
**Source URL**: <https://openrouter.ai/z-ai/glm-5:exacto>
**Model Provider**: Z.ai (via OpenRouter)
**GitHub Repository**: <https://github.com/zai-org/GLM-5>
**Version at Research**: GLM-5 (released 2026-02-11)
**License**: MIT (open-source)

---

## Overview

GLM-5:exacto is Z.ai's flagship 744B-parameter open-source language model accessed through OpenRouter's Exacto provider routing system. The `:exacto` suffix indicates OpenRouter's intelligent provider selection for maximized tool-calling accuracy in agentic workflows. GLM-5 is engineered for complex systems design and long-horizon agent-based tasks, with state-of-the-art performance on code generation and reasoning-intensive applications.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Variable model performance across hosting providers | Exacto routing routes to pre-screened providers with measurably superior tool-calling accuracy (eliminates inference variance) |
| Cost and complexity of multi-provider LLM integration | OpenRouter unified API compatible with OpenAI SDK (single endpoint, no switching) |
| Insufficient context window for long agent traces | 80K input token context window + 131K max output window supports extended reasoning and agentic workflows |
| Hallucination and reliability in knowledge tasks | AA-Omniscience Index score of -1 (35-point improvement over predecessor), leading entire industry in knowledge reliability |
| Suboptimal code generation and tool use in production systems | SWE-bench Verified 77.8%, Terminal-Bench 56-61% with agentic frameworks (Claude Code, Cline, Roo Code) |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Model Parameters | 744B total (40B active via MoE) | 2026-02-11 |
| Pre-training Data | 28.5T tokens | 2026-02-11 |
| Context Window | 80,000 input tokens | 2026-02-11 |
| Max Output | 131,072 tokens | 2026-02-11 |
| Input Pricing (OpenRouter) | $0.72 per 1M tokens | 2026-03-18 |
| Output Pricing (OpenRouter) | $2.30 per 1M tokens | 2026-03-18 |
| SWE-bench Verified Score | 77.8% | 2026-02-11 |
| AIME 2026 I (Math) | 92.7% | 2026-02-11 |
| HumansLastExam Score | 30.5 (text), 50.4 (with tools) | 2026-02-11 |
| GitHub Monthly Downloads | 102,355+ | 2026-02-11 |
| Hugging Face Fine-tuned Variants | 41 (30 full, 10 adapters) | 2026-02-11 |

---

## Key Features

### Model Architecture & Scaling

- **Sparse Mixture of Experts (MoE)**: 744B total parameters with 40B activated per token — integrates DeepSeek Sparse Attention (DSA) to reduce deployment costs while preserving 80K token context window (same as predecessor GLM-4.5's 128K context is improved to 200K in base GLM-5)
- **Training Innovation**: Uses SLIME (asynchronous agent reinforcement learning infrastructure) for improved training throughput and enables pre-training knowledge unlock through extended agent interactions
- **Native Reasoning Support**: Built-in `<think>` tag support for multi-step reasoning with streaming output

### Tool Use & Agentic Capabilities

- **Tool Invocation**: Powerful native function calling enabling integration with external toolsets; auto-tool-choice supported in vLLM deployments
- **Structured Output**: JSON schema support and structured output generation
- **Context Caching**: Intelligent mechanism for optimizing long conversations and repeated patterns
- **Terminal-Bench Performance**: 56.2-61.1% on Claude Code agent benchmarks, 56.2-60.7% on Terminus 2

### Code Generation & Engineering

- **SWE-bench Verified**: 77.8% success on real-world software engineering tasks
- **SWE-bench Multilingual**: 73.3% on code tasks across multiple languages
- **Real-world IDE Integration**: Measurably superior performance in autonomous coding agents (Cline, Roo Code, Kilo Code, Claude Code)

### Input/Output Modalities

- **Text input/output only** (no image support)
- **Quantization Variants**: BF16 full precision and FP8 quantized (754GB total model size, ~400GB FP8)

### API Compatibility

- **OpenAI SDK compatible** via OpenRouter API
- **Native Z.AI SDK** (Python, Java)
- **cURL and RESTful** support
- **Temperature, top_p, frequency_penalty** configurable; default temperature 1, top_p 0.95

---

## Technical Architecture

```
┌─────────────────────────────────────────────────┐
│         OpenRouter Unified API Endpoint         │
│      (OpenAI-compatible SDK support)            │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│    OpenRouter Exacto Provider Router            │
│  (selects from top-performing inference hosts)  │
└────────────┬────────────────────────────────────┘
             │
        ┌────┴────┬─────┐
        ▼         ▼     ▼
     Provider Provider Provider
       (A)     (B)     (C)
        │       │       │
        └───┬───┴───┬───┘
            │       │
            ▼       ▼
        Z.ai GLM-5 Model
      (744B MoE parameters,
        40B active per token)
            │
        ┌───┴────────┬──────────┐
        ▼            ▼          ▼
    Input Tok.   Reasoning    Function
    Processing   Engine       Calls
    (80K window) (<think>)    (tool inv.)
        │            │          │
        └────┬───────┴──────────┘
             │
             ▼
        Output Token Stream
       (up to 131K tokens)
```

**Data Flow for Agentic Workflows:**

1. **Request Routing**: User sends request via OpenRouter API with model slug `z-ai/glm-5:exacto`
2. **Provider Selection**: Exacto router evaluates provider performance metrics (tool-calling success rate, uptime, latency)
3. **Model Inference**: Request routes to qualifying provider; GLM-5 processes with MoE sparse activation
4. **Reasoning Activation**: If reasoning mode requested, model generates `<think>` blocks for intermediate reasoning
5. **Tool Invocation**: Model outputs function calls with auto-tool-choice or structured JSON
6. **Output Streaming**: Tokens streamed back to client with reasoning and tool-call separation
7. **Context Caching**: Repeated patterns or long conversations benefit from cached key-value pairs

**Provider Qualification for Exacto:**

OpenRouter measures three dimensions to qualify providers for Exacto routing:
- Tool-calling accuracy (top performers only)
- Normal tool-calling propensity (no artificial suppression)
- User blacklist rate (excluded if frequently reported as problematic)

---

## Installation & Usage

### Via OpenRouter API (Recommended for Claude Code Integration)

```bash
# 1. Obtain OpenRouter API key from https://openrouter.ai

# 2. Set environment variable
export OPENROUTER_API_KEY="sk-or-..."

# 3. Use with OpenAI Python SDK
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-or-...",
    base_url="https://openrouter.ai/api/v1"
)

# Basic completion
response = client.chat.completions.create(
    model="z-ai/glm-5:exacto",
    messages=[{"role": "user", "content": "Explain agentic workflows"}],
    max_tokens=4000
)

# With tool use
response = client.chat.completions.create(
    model="z-ai/glm-5:exacto",
    messages=[{"role": "user", "content": "Write a Python script using tools"}],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "run_code",
                "description": "Execute Python code",
                "parameters": {"type": "object", "properties": {...}}
            }
        }
    ],
    max_tokens=8000
)

# With reasoning enabled
response = client.chat.completions.create(
    model="z-ai/glm-5:exacto",
    messages=[{"role": "user", "content": "Solve this math problem..."}],
    reasoning={"type": "enabled", "budget_tokens": 5000},
    max_tokens=4000
)
```

### Self-Hosted Deployment via vLLM

```bash
# Install vLLM with CUDA support
pip install vllm

# Serve GLM-5-FP8 (quantized variant, ~400GB VRAM)
vllm serve zai-org/GLM-5-FP8 \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.85 \
  --speculative-config.method mtp \
  --tool-call-parser glm47 \
  --reasoning-parser glm45 \
  --enable-auto-tool-choice

# Send requests to localhost:8000 using OpenAI API format
```

### Configuration Options

```python
# Temperature (0.0–2.0, default 1.0)
response = client.chat.completions.create(
    model="z-ai/glm-5:exacto",
    temperature=0.5,  # More deterministic
    ...
)

# Top-p sampling (0.0–1.0, default 0.95)
response = client.chat.completions.create(
    model="z-ai/glm-5:exacto",
    top_p=0.9,
    ...
)

# Frequency penalty (0.0–2.0, default 0.0)
response = client.chat.completions.create(
    model="z-ai/glm-5:exacto",
    frequency_penalty=0.1,
    ...
)
```

---

## Relevance to Claude Code Development

### Applications

- **Agent Framework Integration**: GLM-5's 77.8% SWE-bench score and proven performance on Claude Code benchmarks makes it a strong candidate for multi-turn coding agent workflows
- **Tool-Use Reliability**: Exacto routing specifically optimizes for tool-calling accuracy, critical for autonomous code generation and CLI agent scripting
- **Long-Context Reasoning**: 80K input token window supports extended agent traces, error recovery loops, and multi-file context for complex refactoring tasks
- **Cost-Effective Agentic Workloads**: MoE sparse activation (40B active of 744B total) reduces per-token cost while maintaining state-of-the-art reasoning

### Patterns Worth Adopting

- **Provider Variance Awareness**: Exacto's explicit measurement and routing around provider variance suggests Claude Code agent systems should monitor inference provider behavior (latency, tool-calling accuracy, hallucination rate) and adapt routing
- **Streaming Reasoning Output**: GLM-5's native `<think>` tag support with streaming indicates value in making intermediate agent reasoning visible to end users (transparent agentic workflows)
- **Sparse Expert Routing**: MoE architecture's efficiency pattern (activate only necessary experts per request) parallels agent skill selection — activate only relevant tools/skills per task

### Integration Opportunities

- **Primary Model for Coding Tasks**: GLM-5:exacto via OpenRouter as drop-in replacement for code-generation workloads in agent systems (SWE-bench 77.8%)
- **Fallback Model for Tool Use**: When high tool-calling accuracy is required (e.g., complex multi-tool orchestration), route to GLM-5:exacto instead of general-purpose models
- **Multi-Model Evaluation Framework**: Build evaluation harness comparing GLM-5:exacto vs. Claude Opus on identical agent benchmarks (Terminal-Bench, MCP-Atlas, CyberGym) to assess relative strengths
- **Self-Hosted Option for Enterprise**: For on-premises deployments, vLLM deployment path enables private GLM-5 access with full tool-use and reasoning support

---

## References

- [OpenRouter GLM-5 Model Page](https://openrouter.ai/z-ai/glm-5) (accessed 2026-03-18)
- [OpenRouter Exacto Provider Variance Announcement](https://openrouter.ai/announcements/provider-variance-introducing-exacto) (accessed 2026-03-18)
- [Z.ai GLM-5 Official Documentation](https://docs.z.ai/guides/llm/glm-5) (accessed 2026-03-18)
- [Z.ai GLM-5 GitHub Repository](https://github.com/zai-org/GLM-5) (accessed 2026-03-18)
- [Hugging Face GLM-5 Model Card](https://huggingface.co/zai-org/GLM-5) (accessed 2026-03-18)
- [Artificial Analysis GLM-5 Intelligence & Performance Report](https://artificialanalysis.ai/models/glm-5) (accessed 2026-03-18)
- [VentureBeat: Z.ai's GLM-5 Achieves Record Low Hallucination Rate](https://venturebeat.com/technology/z-ais-open-source-glm-5-achieves-record-low-hallucination-rate-and-leverages/) (accessed 2026-03-18)
- [Z.ai Blog: GLM-5 — From Vibe Coding to Agentic Engineering](https://z.ai/blog/glm-5) (accessed 2026-03-18)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Opus](../llm-infrastructure/claude-opus.md) | llm-infrastructure | Primary Claude Code model; comparison baseline for coding benchmarks (Opus 4.5 vs. GLM-5 on SWE-bench, Terminal-Bench) |
| [OpenRouter](../llm-infrastructure/openrouter.md) | llm-infrastructure | Unified API provider for GLM-5:exacto access; Exacto routing mechanism |
| [MCP-Atlas Benchmark](../evaluation-testing/mcp-atlas-benchmark.md) | evaluation-testing | GLM-5 scores 67.8% on MCP-Atlas Public Set; reference benchmark for agentic capability |
| [Bifrost AI Gateway](./bifrost.md) | llm-infrastructure | Multi-provider LLM gateway with 22+ providers; comparable unified API abstraction for provider variance mitigation and MCP integration |
| [LocalAI](./localai.md) | llm-infrastructure | Self-hosted LLM alternative with MCP support and function calling; contrasts cloud-hosted GLM-5 with on-premises open-source option |
| [TensorZero](./tensorzero.md) | llm-infrastructure | LLMOps platform for optimization and evaluation; complementary infrastructure for benchmarking GLM-5 in production workflows |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-18 |
| Version at Verification | GLM-5 (2026-02-11 release) |
| Next Review Recommended | 2026-06-18 |
| Confidence Map | Overview: high (official docs + multiple sources) \| Key Statistics: high (official release notes + benchmarks) \| Architecture: high (Z.ai technical docs + GitHub model card) \| Features: high (official docs + benchmarks) \| Usage Examples: high (tested against OpenRouter API docs + OpenAI SDK compatibility) \| Relevance: medium (inferred from benchmark performance, not validated in Claude Code integration) |

