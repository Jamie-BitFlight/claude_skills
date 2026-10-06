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
  last_verified: 2026-10-06
  version_at_verification: 0.2.4
  next_review: 2027-01-06
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: medium | Technical Architecture: medium (doc + code-read) | Installation & Usage: high | Limitations and Caveats: medium"
---

# Magnitude

## Overview

Magnitude is an open source inference engine for agents that optimizes itself for your exact hardware. It compiles and tunes its kernels on your device, so open models run faster than llama.cpp on the README's benchmark (conditions under Key Features; README read 2026-10-06). One click connects the agent you already use (Pi, OpenCode, Hermes, Codex, and more). Works on Apple Silicon, NVIDIA, AMD, or nothing but a CPU.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Running open models at speed without cloud API costs | Hardware-optimized compilation and tuning of inference kernels on the user's device, not precompiled for broad hardware classes |
| Agent integration complexity with local models | One-click connection to the eight agents the docs name (Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, Cline), with OpenAI-compatible API for others |
| Memory waste and slowdown from concurrent inference sessions | Prefix cache sharing between concurrent sessions; memory release when agents stop is stated in the README; the README's per-agent memory percentage is not reproduced (baseline and method: Not mentioned in documentation; README read 2026-10-06) |
| Unpredictable performance on different hardware | Assessment tool in Discover recommends models matched to hardware capabilities |

---

## Key Features

### Performance Optimization

- **Faster than llama.cpp (vendor-reported)**: the README benchmark graphic (`assets/benchmarks/llama-cpp-light.svg`, read 2026-10-06 from main at commit 54a83cc) reports 92% faster decode and 9% faster prefill on Metal ("Mac M4 Pro 48 GB"), and 19% faster decode and 23% faster prefill on CUDA ("DGX Spark"), under the stated conditions "Qwen 3.6 35B A3B, 4-bit, 64k context, no speculative decoding." These figures hold only for that model, quantization, context size and hardware. The README headline "up to 2x" and the run count, llama.cpp version and build flags: Not mentioned in documentation, so those are not reproduced as figures here
- **Kernel tuning on device**: Kernels are compiled and tuned on hardware before a model runs, fitting exact chip characteristics. Mechanism (`inference/docs/seismic/overview.md`, read 2026-10-06): a `CandidateEvaluator` estimates or measures candidate implementations of an authored computation, and a `SelectionPolicy` selects among them to form a `PreparedKernel`; tuning results are keyed on the implementation, precision policy and search objective (`inference/docs/precision.md`)
- **Hand-optimized kernels**: The README FAQ states "We write optimized kernels for the most popular open-weight families, which is how we beat generalist engines." Seismic's standard library supplies "reusable computations and authored alternatives" that model programs compose (`inference/docs/seismic/overview.md`); which families have hand-written kernels beyond the README's statement: Not mentioned in documentation
- **Fast concurrent sessions**: The README states "sessions share prefix caches to prevent slowdown". Mechanism (`inference/docs/engine/state.md`): checkpoints and forks retain shared ownership claims on backing history extents and a fork copies ownership descriptions rather than history tensor bytes; one packed execution may serve multiple independent requests (`inference/docs/engine/overview.md`)

### Memory and Resource Management

- **Memory efficiency** (vendor-reported): the README states "Memory that flexes: ... freed when agents stop" (README read 2026-10-06); the percentage figure attached to it is omitted (baseline, hardware, model and workload: Not mentioned in documentation). Model loading and unloading, below, is the documented mechanism for freeing memory
- **Flexible context handling**: Configurable soft caps on context size (`contextLimits.softCapRatio`, `contextLimits.softCapMaxTokens`)
- **Intelligent model loading**: Models load on demand and unload when idle or memory is tight

### Agent Integration

- **Direct connections**: One-click setup for Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, and Cline. Mechanism (`docs/integrations/overview.mdx`): clicking Connect in Connections writes Magnitude configuration into the agent's own configuration files, which the connected card lists; it configures the agent without launching it, and the copied command starts the agent with the selected model
- **OpenAI-compatible API**: HTTP endpoints at `http://127.0.0.1:10100/inference/v1` (OpenAI format) and `http://127.0.0.1:10100/inference/anthropic` (Anthropic format)
- **Model discovery and recommendations**: Discover tool assesses hardware and recommends models by speed/intelligence trade-off (Balanced, Fastest, Faster, Smarter, Smartest)

### Features for Model Selection and Management

- **Speculative decoding**: Automatic setup for supported models (MTP, DFlash, or DSpark)
- **Prompt caching**: Automatic for supported models (`docs/models.mdx`); the Usage view reports "Cached input" as tokens reused from cache, a subset of input tokens, and the FAQ says later turns reuse cached context. The cache data structure beyond the shared-history mechanism under Fast concurrent sessions: Not mentioned in documentation
- **Vision and tool support**: The model details view lists "Capabilities" such as vision or tool use per model (`docs/models.mdx`); how the flags are derived: Not mentioned in documentation
- **Quantization variants**: The model details view shows a "Fidelity / quantization" field; per `docs/models.mdx`, "Lower-bit variants generally use less memory and disk space; higher fidelity preserves more of the original model." Catalog entries carry the variants; the benchmark above used a 4-bit model

### Privacy and Deployment

- **Local-only execution**: The README states prompts, files and models stay on the machine and no internet is needed once a model is downloaded. Inference runs in a local service bound to `127.0.0.1:10100` by default, with remote access only when configured (`docs/api/network-access.mdx`)
- **Network access configuration**: Optional remote server mode with API key authentication and network binding controls
- **Custom provider endpoints**: Support for OpenAI-compatible endpoints configured in `config.json`

---

## Technical Architecture

Magnitude's inference stack is divided into three primary components, laid out as directories of the `inference/` workspace (`inference/README.md`, read 2026-10-06):

**Engine** (`engine/`): Owns model interpretation, generation, scheduling, and state management. Handles model loading, prompt processing, and response generation.

**Seismic** (`seismic/`): Owns numerical compilation, device resource allocation, and execution across CPU, Metal (Apple Silicon), CUDA (NVIDIA), and Vulkan (AMD/other GPUs). Compiles and tunes kernels at deployment time.

**Service** (`service/`): Owns the public HTTP API, model inventory management, hardware assessment, model residency (download/load/unload lifecycle), and worker supervision.

The system uses a model catalog system (`catalog/`) that stores model metadata, compatibility information, and configuration. Models can be downloaded to `~/.magnitude/models` or a custom configured directory.

### Data flow

`inference/docs/overview.md` gives the flow as: HTTP/SSE requests pass through chat preparation and streaming to the Engine; an embedded application calls the Engine directly. The Engine runs model programs, which use the Seismic standard library and the Seismic compiler and runtime, which execute on CPU, Metal, CUDA or Vulkan. `inference/docs/engine/overview.md` gives the request lifecycle: artifact and model library produce a loaded executor; input preparation produces model input and request admission; a legal work proposal leads to capacity preparation and packed submission, physical completion, per-request validation and state acceptance, then queued output and publication. In Seismic, authored computation is checked, lowered to a `LogicalEntry`, expanded to a `CandidateDomain`, evaluated by a `CandidateEvaluator`, selected under a `SelectionPolicy`, and prepared as a `PreparedKernel` that is bound and executed with the actual invocation arguments (`inference/docs/seismic/overview.md`).

### Extension and integration points

- **Library embedding**: library callers can request state-only advancement, raw logits, selected vocabulary readout, or generation without HTTP, and "Local library use shares the production execution path without implicitly starting a server or scheduler" (`inference/docs/overview.md`, `inference/docs/engine/overview.md`)
- **HTTP APIs**: OpenAI-compatible and Anthropic-compatible endpoints (see API Design) and the `magnitude connections` agent configuration
- **Seismic**: kernel authors supply mathematical structure and alternative algorithms; the standard library supplies reusable computations (`inference/docs/seismic/overview.md`)

### Documented design rationale

`inference/docs/overview.md` lists governing principles, including "Separate policy from mechanism" ("The engine decides residency, admission, and acceptance; Seismic executes explicit work and retains resources safely") and "Keep hardware below the model" ("Model programs express dataflow and precision; backend implementations own hardware mechanisms"). The same document states that these files "describe intended architecture", so they record design intent and are not a verified description of the shipped code.

Source: `inference/README.md` — Layout table, `inference/docs/overview.md` — System structure and Governing principles, `inference/docs/engine/overview.md` — Request lifecycle, `inference/docs/seismic/overview.md` — The system

### API Design

Magnitude exposes two API families:

- **OpenAI-compatible endpoints**: `/inference/v1/chat/completions`, `/inference/v1/completions`, `/inference/v1/responses`, `/inference/v1/models`, `/health`
- **Anthropic-compatible endpoint**: `/inference/anthropic/v1/messages`, `/inference/anthropic/v1/messages/count_tokens`

Both families support JSON and server-sent event (SSE) streaming responses. Default base URLs use localhost (`127.0.0.1:10100`), with network access optional via configuration.

### Hardware Support

| Platform | Acceleration | Notes |
|----------|--------------|-------|
| Apple Silicon Mac | Metal (native, no separate toolkit) | Unified memory shared with GPU; app memory constraints apply |
| Intel Mac | CPU | Intel Macs use CPU inference (docs/installation/macos.mdx); CUDA/Metal support on Intel Mac: Not mentioned in documentation |
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
