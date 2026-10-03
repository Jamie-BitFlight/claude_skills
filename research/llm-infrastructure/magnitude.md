---
name: magnitude
title: Magnitude
subtitle: Hardware-optimized local inference engine for AI agents
research_date: 2026-10-02
source_url: https://github.com/magnitudedev/magnitude
github_repository: https://github.com/magnitudedev/magnitude
version_at_research: 0.2.4 (@magnitudedev/cli, latest release tag from magnitudedev/magnitude)
license: Apache 2.0
freshness_tracking:
  last_verified: 2026-10-03
  version_at_verification: 0.2.4
  next_review: 2027-01-02
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: medium | Technical Architecture: medium | Installation & Usage: high | Limitations: medium | Relevance: medium"
---

# Magnitude

## Overview

Magnitude is an open source inference engine for agents that optimizes itself for your exact hardware. It compiles and tunes its kernels on your device, so open models run up to 2x faster than llama.cpp. One click connects the agent you already use (Pi, OpenCode, Hermes, Codex, and more). Works on Apple Silicon, NVIDIA, AMD, or nothing but a CPU.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Running open models at speed without cloud API costs | Hardware-optimized compilation and tuning of inference kernels on the user's device, not precompiled for broad hardware classes |
| Agent integration complexity with local models | One-click connection to 8+ agents (Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, Cline), with OpenAI-compatible API for others |
| Memory waste and slowdown from concurrent inference sessions | Prefix cache sharing between concurrent sessions; the Magnitude README states "27% less memory per agent" (vendor-reported; measurement method: Not mentioned in documentation) |
| Unpredictable performance on different hardware | Assessment tool in Discover recommends models matched to hardware capabilities |

---

## Key Features

### Performance Optimization

- **Up to 2x faster than llama.cpp** (vendor-reported): the Magnitude README states "Up to 2x faster than llama.cpp: 92% faster decode on Metal, 19% on CUDA". The "up to 2x" figure has no measurement method in the README or docs (Measurement method: Not mentioned in documentation). The 92% and 19% decode figures come from the README benchmark graphic (`assets/benchmarks/llama-cpp-light.svg`), whose text gives the conditions: Metal on "Mac M4 Pro 48 GB" and CUDA on "DGX Spark", with "Qwen 3.6 35B A3B, 4-bit, 64k context, no speculative decoding." The graphic also lists 9% faster prefill on Metal and 23% faster prefill on CUDA. Run count, llama.cpp version and build flags: Not mentioned in documentation
- **Kernel tuning on device**: Kernels are compiled and tuned on hardware before a model runs, fitting exact chip characteristics
- **Hand-optimized kernels**: Built specifically for popular open-weight model families, not a generalist engine
- **Fast concurrent sessions**: Sessions share prefix caches to prevent slowdown when running multiple models or agents

### Memory and Resource Management

- **Memory efficiency** (vendor-reported): the Magnitude README states "Memory that flexes: 27% less memory per agent, freed when agents stop". Baseline, hardware, model and workload for the 27%: Not mentioned in documentation
- **Flexible context handling**: Configurable soft caps on context size (`contextLimits.softCapRatio`, `contextLimits.softCapMaxTokens`)
- **Intelligent model loading**: Models load on demand and unload when idle or memory is tight

### Agent Integration

- **Direct connections**: One-click setup for Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, and Cline
- **OpenAI-compatible API**: HTTP endpoints at `http://127.0.0.1:10100/inference/v1` (OpenAI format) and `http://127.0.0.1:10100/inference/anthropic` (Anthropic format)
- **Model discovery and recommendations**: Discover tool assesses hardware and recommends models by speed/intelligence trade-off (Balanced, Fastest, Faster, Smarter, Smartest)

### Features for Model Selection and Management

- **Speculative decoding**: Automatic setup for supported models (MTP, DFlash, or DSpark)
- **Prompt caching**: Automatic prompt cache reuse
- **Vision and tool support**: Capability indicators for vision and tool use features per model
- **Quantization variants**: Support for multiple fidelity levels to balance speed and quality

### Privacy and Deployment

- **Local-only execution**: No tokens costs, prompts and files stay on machine, no internet required after model download
- **Network access configuration**: Optional remote server mode with API key authentication and network binding controls
- **Custom provider endpoints**: Support for OpenAI-compatible endpoints configured in `config.json`

---

## Technical Architecture

Magnitude's inference stack is divided into three primary components:

**Engine** (`engine/`): Owns model interpretation, generation, scheduling, and state management. Handles model loading, prompt processing, and response generation.

**Seismic** (`seismic/`): Owns numerical compilation, device resource allocation, and execution across CPU, Metal (Apple Silicon), CUDA (NVIDIA), and Vulkan (AMD/other GPUs). Compiles and tunes kernels at deployment time.

**Service** (`service/`): Owns the public HTTP API, model inventory management, hardware assessment, model residency (download/load/unload lifecycle), and worker supervision.

The system uses a model catalog system that stores model metadata, compatibility information, and configuration. Models can be downloaded to `~/.magnitude/models` or a custom configured directory.

### API Design

Magnitude exposes two API families:

- **OpenAI-compatible endpoints**: `/inference/v1/chat/completions`, `/inference/v1/completions`, `/inference/v1/responses`, `/inference/v1/models`, `/health`
- **Anthropic-compatible endpoint**: `/inference/anthropic/v1/messages`, `/inference/anthropic/v1/messages/count_tokens`

Both families support JSON and server-sent event (SSE) streaming responses. Default base URLs use localhost (`127.0.0.1:10100`), with network access optional via configuration.

### Hardware Support

| Platform | Acceleration | Notes |
|----------|--------------|-------|
| Apple Silicon Mac | Metal (native, no separate toolkit) | Unified memory shared with GPU; app memory constraints apply |
| Intel Mac | CPU only | No CUDA or Metal support |
| Windows x64 | CPU, NVIDIA CUDA, Vulkan-compatible GPUs | CUDA targets Ampere-class (RTX 30/40 series) and newer |
| Linux x64/ARM64 | CPU, NVIDIA CUDA, Vulkan-compatible GPUs | Same CUDA generation requirements as Windows |

---

## Installation & Usage

### Get Started

1. Download Magnitude from [magnitude.dev/download](https://magnitude.dev/download) for macOS, Windows, or Linux
2. Install and open the app
3. Use **Discover** to assess hardware and select a recommended model
4. Download the model
5. Open **Connections** to connect your agent (Pi, OpenCode, Hermes, Codex, Claude Code, etc.)
6. Copy and run the displayed command to start the agent with your selected model

The desktop app includes the `magnitude` CLI. No separate installation needed.

### CLI Reference

```bash
# Run the service
magnitude serve              # Run in foreground without opening Desktop

# Manage models
magnitude catalog list       # List compatible models
magnitude catalog show <model-id>  # Show model details
magnitude catalog pull <model-id>  # Download a model
magnitude models load <model-id>   # Load into memory
magnitude models stop        # Stop active model

# Manage integrations
magnitude connections list   # Show connected agents
magnitude connections add <harness>  # Configure an agent (pi, opencode, hermes, openclaw, codex, claude-code, oh-my-pi, cline)
magnitude connections sync   # Refresh integrations

# Check status
magnitude status             # Check if running and inspect service/model state
magnitude hardware           # Inspect detected hardware and memory
```

### HTTP API Example

OpenAI-compatible chat completion:

```bash
curl http://127.0.0.1:10100/inference/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "MODEL_ID",
    "messages": [{"role": "user", "content": "Explain inference optimization."}],
    "max_tokens": 256
  }'
```

Anthropic-compatible message:

```bash
curl http://127.0.0.1:10100/inference/anthropic/v1/messages \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -d '{
    "model": "MODEL_ID",
    "max_tokens": 256,
    "messages": [{"role": "user", "content": "Explain inference optimization."}]
  }'
```

---

## Limitations and Caveats

- **First-response latency**: Magnitude loads models on demand, so the first response after idle time takes longer than subsequent responses
- **API scope**: The HTTP API provides inference only (listing models and generating text). Model downloading, management, and the Magnitude app itself are not available over the API
- **GPU memory sharing**: On dedicated-GPU systems (non-unified-memory), GPU memory and system RAM are not interchangeable; a machine with 64 GB system RAM and 8 GB GPU does not have 72 GB available for models
- **Context size trade-offs**: Longer context windows increase memory demand and can slow response generation. Soft caps (`contextLimits.softCapRatio`, `contextLimits.softCapMaxTokens`) allow user-configured context limits
- **Unified memory constraints**: On Apple Silicon, macOS and other applications use the same memory pool as the GPU, so available memory for models may be less than total unified memory

---

## Relevance to Claude Code Development

### Applications

- **Local model serving in plugins** -> `plugins/llamafile/README.md`
  - Term: `local model`
  - Today: "- Building developer tools (commit message generators, code reviewers) backed by local models"
  - Change: none — out of scope (Magnitude's kernel tuning happens inside its own inference engine; this README documents how to run llamafile and has no engine-internals surface to edit)

- **OpenAI-compatible API exposure** -> `plugins/llamafile/skills/llamafile/SKILL.md`
  - Term: `OpenAI-compatible`
  - Today: "Llamafile exposes these OpenAI-compatible endpoints when running with `--server`"
  - Change: none — Magnitude's dual-API (OpenAI and Anthropic) endpoint design pattern already covered by LiteLLM abstraction skill

- **Model lifecycle management (residency: download, load, unload)** -> nothing in `plugins/`, `.claude/skills/`, `.claude/agents/`, `rules/`, `docs/`, `AGENTS.md`
  - Today: `git grep --full-name -il "model residency" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md` → 0 matches
  - Today: `git grep --full-name -il "residency" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md` → 0 matches
  - Change: none — out of scope (Magnitude's `service/` owns model residency per the Technical Architecture section; no file here operates a model-residency manager, and these two terms returning nothing does not establish that no such capability exists here)

### Patterns Worth Adopting

- **Agent integration through a standard API** -> `plugins/litellm/skills/litellm/SKILL.md`
  - Term: `OpenAI message format`
  - Today: "- **Unified Format**: All requests use OpenAI message format"
  - Change: none — `plugins/litellm/skills/litellm/SKILL.md` already routes every provider, including local servers, through one standard API rather than agent-specific adapters

---

## References

- [Magnitude GitHub Repository](https://github.com/magnitudedev/magnitude) (accessed 2026-10-02)
- [Magnitude Documentation](https://docs.magnitude.dev) (accessed 2026-10-02)
- [Magnitude Download Page](https://magnitude.dev/download) (accessed 2026-10-02)
- [Magnitude Models](https://magnitude.dev/models) (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [LocalAI](./localai.md) | llm-infrastructure | Open-source local inference server with OpenAI-compatible API and no GPU requirement |
| [Bifrost](./bifrost.md) | llm-infrastructure | High-performance AI gateway unifying access to 20+ providers with adaptive load balancing and semantic caching |
| [TensorZero](./tensorzero.md) | llm-infrastructure | Industrial-grade LLM gateway with fine-tuning pipelines and A/B testing for continuous model optimization |
| [AirLLM](./airllm.md) | llm-infrastructure | Resource-optimized inference for large models on GPU-constrained hardware via layer sharding and streaming |
| [quantum-free-router](./quantum-free-router.md) | llm-infrastructure | Free-tier LLM router aggregating 9 providers into single OpenAI-compatible endpoint with fallback chain |
