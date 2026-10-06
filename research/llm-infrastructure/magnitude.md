---
name: magnitude
title: Magnitude
subtitle: Hardware-optimized local inference engine for AI agents
research_date: 2026-10-06
source_url: https://github.com/magnitudedev/magnitude
github_repository: https://github.com/magnitudedev/magnitude
version_at_research: 0.2.6 (@magnitudedev/cli package version in packages/launcher/package.json at commit 54a83cc, read 2026-10-06)
license: Apache License 2.0 (LICENSE file at commit 54a83cc, read 2026-10-06)
freshness_tracking:
  last_verified: 2026-10-06
  version_at_verification: 0.2.6 (packages/launcher/package.json, commit 54a83cc)
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
- **Flexible context handling**: `docs/reference/configuration-file.mdx` defines `contextLimits.softCapRatio` as the "Fraction of a model's context window used before compaction" (default `0.9`) and `contextLimits.softCapMaxTokens` as the "Absolute cap on context tokens, or `null`"; both apply on the next model load. How compaction is performed: Not mentioned in documentation
- **Intelligent model loading**: `docs/models.mdx` states that "Magnitude loads a model on demand when an agent requests it and unloads it when idle or memory is tight"; **Load model** and **Stop model** in My Models do the same manually. The idle threshold and the memory-pressure rule: Not mentioned in documentation

### Agent Integration

- **Direct connections**: One-click setup for Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, and Cline. Mechanism (`docs/integrations/overview.mdx`): clicking Connect in Connections writes Magnitude configuration into the agent's own configuration files, which the connected card lists; it configures the agent without launching it, and the copied command starts the agent with the selected model
- **OpenAI-compatible API**: HTTP endpoints at `http://127.0.0.1:10100/inference/v1` (OpenAI format) and `http://127.0.0.1:10100/inference/anthropic` (Anthropic format)
- **Model discovery and recommendations**: per `docs/models.mdx`, Discover "assesses your hardware and shows up to five recommendations", with Balanced as the starting point and Fastest, Faster, Smarter or Smartest shifting the speed-intelligence trade-off. The CLI exposes `hardware`, `catalog status`, and `catalog recommendations` (`docs/reference.mdx`), and assessment runs in the background. The assessment algorithm: Not mentioned in documentation

### Features for Model Selection and Management

- **Speculative decoding**: `docs/models.mdx` states that supported models use speculative decoding (MTP, DFlash, or DSpark) automatically, and the model details view's Speculation row shows "the speculative-decoding method prepared for the model" with setup handled by Magnitude. What MTP, DFlash and DSpark are, and how the method is selected per model: Not mentioned in documentation
- **Prompt caching**: Automatic for supported models (`docs/models.mdx`); the Usage view reports "Cached input" as tokens reused from cache, a subset of input tokens, and the FAQ says later turns reuse cached context. The cache data structure beyond the shared-history mechanism under Fast concurrent sessions: Not mentioned in documentation
- **Vision and tool support**: The model details view lists "Capabilities" such as vision or tool use per model (`docs/models.mdx`); how the flags are derived: Not mentioned in documentation
- **Quantization variants**: The model details view shows a "Fidelity / quantization" field; per `docs/models.mdx`, "Lower-bit variants generally use less memory and disk space; higher fidelity preserves more of the original model." Catalog entries carry the variants; the benchmark above used a 4-bit model

### Privacy and Deployment

- **Local-only execution**: The README states prompts, files and models stay on the machine and no internet is needed once a model is downloaded. Inference runs in a local service bound to `127.0.0.1:10100` by default, with remote access only when configured (`docs/api/network-access.mdx`)
- **Network access configuration**: `docs/reference/configuration-file.mdx` defines a `network` object in `config.json` with `enabled` (absent or `false` means this computer only), `bind` (one IP address; absent means all interfaces), `apiKey`, `requireApiKey` (default `true`) and `allowedHosts` (extra hostnames accepted); all apply on next start. Other devices send the key as `Authorization: Bearer KEY` or `x-api-key: KEY` (`docs/api/overview.mdx`), and `/rpc` returns `403` from other devices (`docs/api/network-access.mdx`)
- **Custom provider endpoints**: the `providers` key of `config.json` holds "OpenAI-compatible endpoints to expose alongside local models" and applies immediately (`docs/reference/configuration-file.mdx`). The schema is printed by `magnitude docs custom-endpoints`; the topic file (`cli/src/agent-docs/topics/custom-endpoints.md`) shows each provider with a `displayName`, a `connection` (`baseUrl`, `authentication` of type `none`, `bearer` or `header` with an environment-variable credential) and a `models` map

---

## Technical Architecture

Magnitude's inference stack is divided into three primary components, laid out as directories of the `inference/` workspace (`inference/README.md`, read 2026-10-06):

**Engine** (`engine/`): Owns model interpretation, generation, scheduling, and state management. Handles model loading, prompt processing, and response generation.

**Seismic** (`seismic/`): Owns numerical compilation, device resource allocation, and execution across CPU, Metal (Apple Silicon), CUDA (NVIDIA), and Vulkan (AMD/other GPUs). Compiles and tunes kernels at deployment time.

**Service** (`service/`): Owns the public HTTP API, model inventory management, hardware assessment, model residency (download/load/unload lifecycle), and worker supervision.

The `inference/` layout table lists a `catalog/` directory described as "Model catalog and planner inputs" (`inference/README.md`). Downloaded models are stored in `~/.magnitude/models` (`docs/models.mdx`); `modelsDirectory` in `config.json` sets another folder, and absent means `~/.magnitude/models` (`docs/reference/configuration-file.mdx`).

Source: `inference/README.md` — Layout table, `docs/models.mdx`, `docs/reference/configuration-file.mdx`

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

- **OpenAI-compatible endpoints**: `/inference/v1/chat/completions`, `/inference/v1/responses`, `/inference/v1/models`, and `/health` (readiness, returns `200`)
- **Anthropic-compatible endpoint**: `/inference/anthropic/v1/messages`, `/inference/anthropic/v1/messages/count_tokens`

Source: the endpoint table in `docs/api/endpoints.mdx`.

Both families support JSON and server-sent event (SSE) streaming responses. Default base URLs use localhost (`127.0.0.1:10100`), with network access optional via configuration.

### Hardware Support

| Platform | Acceleration | Notes |
|----------|--------------|-------|
| Apple Silicon Mac | Metal GPU acceleration | "Metal support is supplied by macOS; you do not need a separate GPU toolkit." Unified memory is shared with the CPU and other apps (`docs/hardware.mdx`) |
| Intel Mac | CPU | Intel Macs use CPU inference (`docs/hardware.mdx`, `docs/installation/macos.mdx`); CUDA/Metal support on Intel Mac: Not mentioned in documentation |
| Windows x64 | CPU, supported NVIDIA CUDA GPUs, or supported Vulkan GPUs | `docs/hardware.mdx`: "The current CUDA builds target Ampere-class and newer GPUs"; Vulkan 1.1 or later required; no ROCm backend |
| Linux x64/ARM64 | CPU, supported NVIDIA CUDA GPUs, or supported Vulkan GPUs | The CUDA statement in `docs/hardware.mdx` covers Linux and Windows |

Source: the Supported configurations table in `docs/hardware.mdx`; the Intel Mac row is also in `docs/installation/macos.mdx`.

---

## Installation & Usage

### Get Started

1. Download Magnitude from [magnitude.dev/download](https://magnitude.dev/download) for macOS, Windows, or Linux
2. Install and open the app
3. Use **Discover** to assess hardware and select a recommended model
4. Download the model
5. Open **Connections** to connect your agent (Pi, OpenCode, Hermes, Codex, Claude Code, or another listed agent)
6. Copy and run the displayed command to start the agent with your selected model

The desktop app includes the `magnitude` CLI. No separate installation needed.

### CLI Reference

Source: command tables in `docs/reference.mdx` (comments below paraphrase its Purpose column).

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

Source: `docs/api/endpoints.mdx` (Chat completion and Anthropic Messages examples). Replace `MODEL_ID` with an ID from the models endpoint.

OpenAI-compatible chat completion:

```bash
curl http://127.0.0.1:10100/inference/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "MODEL_ID",
    "messages": [{"role": "user", "content": "Explain prompt caching in one paragraph."}],
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
    "messages": [{"role": "user", "content": "Explain prompt caching in one paragraph."}]
  }'
```

---

## Limitations and Caveats

- **On-demand model loading**: `docs/models.mdx` states that "Magnitude loads a model on demand when an agent requests it and unloads it when idle or memory is tight". Any latency effect on the first response: Not mentioned in documentation
- **API scope**: The HTTP API provides inference only (listing models and generating text). Per `docs/api/overview.mdx` (Scope): "Downloading models, managing them, and the Magnitude app itself are not available over the API"
- **GPU memory sharing**: On dedicated-GPU systems (non-unified-memory), GPU memory and system RAM are not interchangeable; `docs/hardware.mdx` gives the example that a machine with 64 GB of system RAM and an 8 GB GPU "does not have 72 GB of interchangeable GPU memory"
- **Context size trade-offs**: `docs/hardware.mdx` states longer context "increases memory demand and can slow responses". Soft caps (`contextLimits.softCapRatio`, `contextLimits.softCapMaxTokens`) allow user-configured context limits
- **Unified memory constraints**: On Apple Silicon, macOS and other applications use the same memory pool as the GPU, so available memory for models may be less than total unified memory (`docs/hardware.mdx`: a 32 GB Mac "does not have all 32 GB available for a model")

---

## References

All paths below are files in the shallow clone of magnitudedev/magnitude at commit `54a83ccec57fee944ea2b550364f1a666ddc06a2` (54a83cc), read 2026-10-06; the `docs/` files are the source of the docs site, which was also read on 2026-10-06. The Magnitude download page and models page were not fetched; the entry cites the download link only as given in `docs/get-started.mdx`.

- [Magnitude GitHub Repository](https://github.com/magnitudedev/magnitude), commit 54a83cc (accessed 2026-10-06)
- [Magnitude Documentation](https://docs.magnitude.dev) (accessed 2026-10-06)
- `README.md` (accessed 2026-10-06, commit 54a83cc)
- `assets/benchmarks/llama-cpp-light.svg` (accessed 2026-10-06, commit 54a83cc)
- `inference/README.md` (accessed 2026-10-06, commit 54a83cc)
- `inference/docs/overview.md` (accessed 2026-10-06, commit 54a83cc)
- `inference/docs/precision.md` (accessed 2026-10-06, commit 54a83cc)
- `inference/docs/engine/overview.md` (accessed 2026-10-06, commit 54a83cc)
- `inference/docs/engine/state.md` (accessed 2026-10-06, commit 54a83cc)
- `inference/docs/seismic/overview.md` (accessed 2026-10-06, commit 54a83cc)
- `docs/get-started.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/integrations/overview.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/models.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/reference.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/reference/configuration-file.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/api/overview.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/api/network-access.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/installation/macos.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/hardware.mdx` (accessed 2026-10-06, commit 54a83cc)
- `docs/api/endpoints.mdx` (accessed 2026-10-06, commit 54a83cc)
- `LICENSE` (accessed 2026-10-06, commit 54a83cc)
- `packages/launcher/package.json` (accessed 2026-10-06, commit 54a83cc)
- `cli/src/agent-docs/topics/custom-endpoints.md` (accessed 2026-10-06, commit 54a83cc)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [LocalAI](./localai.md) | llm-infrastructure | Open-source local inference server with OpenAI-compatible API and no GPU requirement |
| [Bifrost](./bifrost.md) | llm-infrastructure | High-performance AI gateway unifying access to 20+ providers with adaptive load balancing and semantic caching |
| [TensorZero](./tensorzero.md) | llm-infrastructure | Industrial-grade LLM gateway with fine-tuning pipelines and A/B testing for continuous model optimization |
| [AirLLM](./airllm.md) | llm-infrastructure | Resource-optimized inference for large models on GPU-constrained hardware via layer sharding and streaming |
| [quantum-free-router](./quantum-free-router.md) | llm-infrastructure | Free-tier LLM router aggregating 9 providers into single OpenAI-compatible endpoint with fallback chain |
