---
title: "AirLLM: Memory-Optimized Large Language Model Inference"
description: "Python library enabling 70B+ LLM inference on 4GB GPUs through layer-sharded streaming architecture without quantization or distillation"
version: "2.11.0"
last_updated: "2024-08-20"
status: "active"
---

## Overview

**AirLLM** is a Python library that optimizes GPU memory consumption during large language model inference through layer-based sharding and streaming. It enables running 70-billion-parameter models on single GPUs with 4GB VRAM without quantization, distillation, or pruning. The flagship feature allows inference on Llama 3.1 405B models with 8GB of total VRAM.

**Key claim from source**: "AirLLM optimizes inference memory usage, allowing 70B large language models to run inference on a single 4GB GPU card without quantization, distillation and pruning. And you can run 405B Llama3.1 on 8GB vram now."

**Repository**: <https://github.com/lyogavin/airllm>
**Package**: Available on PyPI as `airllm`
**License**: Apache 2.0
**Primary Language**: Python with PyTorch

## Problem Addressed

Large language model inference is memory-intensive because model weights must typically be fully loaded into GPU memory during forward passes. For 70B parameter models requiring >140GB (at float16 precision), this exceeds consumer GPU capacity by orders of magnitude, confining inference to enterprise hardware clusters or requiring expensive quantization trade-offs.

AirLLM solves this by:

1. **Decomposing the model into layer-wise shards** - Each transformer layer is stored separately on disk
2. **Streaming inference** - Layers are loaded into GPU one at a time, processed, and unloaded before the next layer loads
3. **Memory reuse** - GPU memory is freed after each layer completes its computation, enabling sequential reuse

This approach avoids quantization (which degrades output quality) and distillation (which requires retraining).

## Key Statistics

**Version**: 2.11.0 (released 2024-08-20)
**Installation**: `pip install airllm`
**Repository commits**: 100+ commits as of June 2024
**PyPI downloads**: Badge indicates active distribution via PyPI

**Performance metrics** (from README):
- "3x inference speed improvement" claimed with model compression enabled
- Enables "70B large language models to run inference on a single 4GB GPU card"
- "405B Llama3.1 on 8GB vram"

## Key Features

### 1. AutoModel Dispatcher

The `AutoModel` class detects the model architecture automatically and instantiates the appropriate AirLLM variant without requiring manual class specification.

**Implementation detail**: From `auto_model.py`, the dispatcher reads the model config from Hugging Face and matches `config.architectures[0]` against known patterns:
- `"Qwen2ForCausalLM"` → `AirLLMQWen2`
- `"QWen"` → `AirLLMQWen`
- `"Baichuan"` → `AirLLMBaichuan`
- `"ChatGLM"` → `AirLLMChatGLM`
- `"InternLM"` → `AirLLMInternLM`
- `"Mistral"` → `AirLLMMistral`
- `"Mixtral"` → `AirLLMMixtral`
- `"Llama"` → `AirLLMLlama2`
- Unknown → defaults to `AirLLMLlama2`

**Usage example from README**:
```python
from airllm import AutoModel
model = AutoModel.from_pretrained("garage-bAInd/Platypus2-70B-instruct")
```

### 2. Layer-Sharded Model Decomposition

During initialization, the full model is decomposed into layer-wise shards stored on disk. The README states: "During inference, the original model will first be decomposed and saved layer-wise. Please ensure there is sufficient disk space in the huggingface cache directory."

**Customizable storage**: The `layer_shards_saving_path` parameter allows specifying a custom directory for sharded model storage instead of using Hugging Face's default cache.

### 3. Block-Wise Quantization Compression

Optional 4-bit and 8-bit quantization enables "3x inference speed improvement with almost ignorable accuracy loss" per the README. This compression quantizes only model weights (not activations), avoiding the accuracy impacts of full quantization approaches.

**Usage**: Pass `compression='4bit'` or `compression='8bit'` to `from_pretrained()`.

**Dependency**: Requires `bitsandbytes` library.

### 4. Prefetching and Overlapping

The `prefetching` parameter (default: enabled) overlaps disk I/O with GPU computation. From the config description: "prefetching to overlap the model loading and compute. By default, turned on. For now, only AirLLMLlama2 supports this."

This provides "10% speed improvement" according to the release notes for v2.5.

### 5. Model Architecture Abstraction

The codebase defines a `AirLLMBaseModel` class (in `airllm_base.py`) that implements the layer-streaming protocol. Each model variant (Llama, Qwen, ChatGLM, etc.) extends this base with model-specific layer-name mappings.

**Key fields in layer_names_dict** (from base class):
```python
'embed': 'model.embed_tokens',
'layer_prefix': 'model.layers',
'norm': 'model.norm',
'lm_head': 'lm_head',
```

These mappings allow the streamer to identify and load the correct transformer layers for each architecture.

### 6. macOS Support via MLX

The codebase includes `AirLLMLlamaMlx`, an alternative implementation using the `mlx` framework for Apple Silicon Macs. When running on macOS, the library automatically switches to MLX-based inference instead of PyTorch.

**Requirements from README**: "make sure you installed mlx and torch... only Apple silicon is supported"

### 7. HuggingFace Integration

Models are loaded directly from Hugging Face Hub or local cache. The library supports:
- Model repo IDs (e.g., `"meta-llama/Llama-2-7b-hf"`)
- Local filesystem paths
- Gated models via `hf_token` parameter

## Technical Architecture

### Core Data Flow

```
Input Text → Tokenize
  ↓
Token IDs + Attention Mask → Load Embedding Layer → GPU
  ↓
[For Each Transformer Layer]:
  Load Layer into GPU
  Forward Pass
  Free GPU Memory
  ↓
Final Layer Output → LM Head → Logits
  ↓
Decode to Output Text
```

### Component Hierarchy

**AirLLMBaseModel** (base class implementing streaming protocol)
- `__init__`: Decompose model into shards, initialize profiler
- `forward`: Implement layer-by-layer streaming
- `generate`: Inherit from `transformers.GenerationMixin` for auto-regressive generation

**Model-Specific Subclasses**:
- `AirLLMLlama2`: Llama 2 & Llama 3 variants
- `AirLLMQWen`, `AirLLMQWen2`: Alibaba Qwen models
- `AirLLMChatGLM`: Tsinghua ChatGLM
- `AirLLMBaichuan`: Baichuan models
- `AirLLMInternLM`: Shanghai AI Lab InternLM
- `AirLLMMistral`, `AirLLMMixtral`: Mistral variants
- `AirLLMLlamaMlx`: Apple Silicon MLX backend

**Utilities**:
- `utils.py`: Layer loading, memory management (`clean_memory`, `load_layer`)
- `persist/`: Model persistence (safetensors, MLX formatters)
- `profiler.py`: Timing instrumentation

### Extension Points

1. **Model registration**: Add a new model type by:
   - Creating `airllm_<modelname>.py` with a subclass of `AirLLMBaseModel`
   - Updating `AutoModel.get_module_class()` to recognize the architecture
   - Overriding `set_layer_names_dict()` with model-specific layer paths

2. **Custom layer naming**: Override `set_layer_names_dict()` to define embedding, layer prefix, norm, and head locations for new architectures

3. **Backend switching**: Override the forward/generate methods to implement alternative inference engines (e.g., MLX on macOS)

### Supported Models

**Explicitly implemented**:
- Llama 2, Llama 3, Llama 3.1 (including 405B variant)
- Qwen (1B to 72B), Qwen2.5
- ChatGLM (6B, 130B)
- Baichuan, InternLM
- Mistral, Mixtral

**Fallback**: Unknown architectures default to Llama2 pattern, with note: "unknown architecture: {config.architectures[0]}, try to use Llama2..."

## Installation & Usage

### Installation

```bash
pip install airllm
```

For quantization support (4bit/8bit compression):
```bash
pip install -U bitsandbytes
```

For macOS MLX support:
```bash
pip install mlx
```

### Basic Inference

```python
from airllm import AutoModel

# Load any supported model
model = AutoModel.from_pretrained("garage-bAInd/Platypus2-70B-instruct")

# Tokenize
input_text = ['What is the capital of United States?']
input_tokens = model.tokenizer(
    input_text,
    return_tensors="pt",
    return_attention_mask=False,
    truncation=True,
    max_length=128,
    padding=False  # Some models require padding=False
)

# Generate
generation_output = model.generate(
    input_tokens['input_ids'].cuda(),
    max_new_tokens=20,
    use_cache=True,
    return_dict_in_generate=True
)

# Decode
output = model.tokenizer.decode(generation_output.sequences[0])
print(output)
```

### Configuration Options

**Constructor parameters** (from `AirLLMBaseModel.__init__`):
- `model_local_path_or_repo_id` (required): Path or Hugging Face repo ID
- `device` (default: `"cuda:0"`): GPU device to use
- `dtype` (default: `torch.float16`): Precision (float16, float32)
- `max_seq_len` (default: 512): Context window size
- `layer_shards_saving_path` (optional): Custom directory for storing layer shards
- `profiling_mode` (default: False): Enable timing instrumentation
- `compression` (default: None): Set to `'4bit'` or `'8bit'` for quantized inference
- `hf_token` (optional): Hugging Face API token for gated models
- `prefetching` (default: True): Enable load-compute overlap
- `delete_original` (default: False): Remove original model weights after sharding

### CPU Inference

**Release note** (v2.10.1): "Support CPU inference. Support non sharded models." Inference is possible on CPU, though slower, without quantization or sharding.

### Model Compression Trade-offs

From README: "Quantization normally needs to quantize both weights and activations to really speed things up... While in our case the bottleneck is mainly at the disk loading, we only need to make the model loading size smaller. So, we get to only quantize the weights' part, which is easier to ensure the accuracy."

## Relevance to Claude Code Development

AirLLM is relevant to Claude Code as a **cost-reduction pattern** for agent development in resource-constrained environments and a **model-loading optimization** for integrating large models into agentic workflows.

### Use Cases

1. **Running agents on consumer hardware** - Developers building Claude Code plugins and agents on laptops or single-GPU machines can use AirLLM to run local LLM instances for off-line reasoning, without depending on remote API quotas.

2. **Offline agentic RAG** - Agents that need both local LLM inference and vector search (for retrieval-augmented generation) can use AirLLM to keep the LLM local while managing memory footprint.

3. **Hardware-minimal deployments** - Plugins deployed to resource-constrained CI/CD runners or container environments can use AirLLM to run larger context windows than quantization alone would allow.

4. **Cost optimization for high-volume agent workflows** - For batch workflows that invoke Claude Code agents many times, running models locally via AirLLM (despite slower per-token speed) can reduce cumulative API costs.

### Integration Pattern

An MCP server wrapping AirLLM inference could expose LLM completion as a tool to agents:

```python
# Hypothetical AirLLM MCP server
class AirLLMCompletionServer:
    def __init__(self, model_id, compression='4bit'):
        self.model = AutoModel.from_pretrained(model_id, compression=compression)

    @mcp_tool
    def complete(self, prompt: str, max_tokens: int = 100) -> str:
        tokens = self.model.tokenizer(prompt, return_tensors="pt")
        output = self.model.generate(tokens['input_ids'].cuda(), max_new_tokens=max_tokens)
        return self.model.tokenizer.decode(output.sequences[0])
```

## Limitations and Caveats

### Documented Limitations

1. **Disk space requirement** - Model decomposition requires ~2x the model size in disk space during the one-time sharding process. The README states: "During inference, the original model will first be decomposed and saved layer-wise. Please ensure there is sufficient disk space in the huggingface cache directory."

2. **First-run overhead** - The layer decomposition and storage is a one-time operation per model, but adds significant overhead to the first inference call. Subsequent calls reuse pre-sharded layers.

3. **Slower per-token speed vs. full GPU loading** - Layer streaming incurs disk I/O latency on each layer. While compression enables 3x speedup via prefetching, inference is still slower than loading the entire model once if GPU memory permits.

4. **Tokenizer requirement** - Models must expose a Hugging Face-compatible tokenizer. Models without standard tokenizers may fail during initialization.

5. **Gated model authentication** - Gated models (e.g., `meta-llama/Llama-2-7b-hf`) require `hf_token` parameter; requests without valid tokens fail with `401 Client Error`.

6. **Model architecture coverage** - Only explicitly implemented architectures are fully supported. Unknown architectures fall back to Llama2 patterns, which may fail. From README FAQ: "Most likely you are loading QWen or ChatGLM model with Llama2 class" as a common failure pattern.

7. **macOS MLX limitations** - macOS support is restricted to Apple Silicon hardware; Intel Macs are not supported. The README states: "only Apple silicon is supported."

8. **Prefetching support** - Prefetch overlap is "For now, only AirLLMLlama2 supports this" according to configuration docs.

### External Dependencies

- `torch` (PyTorch)
- `transformers` (Hugging Face)
- `accelerate`
- `safetensors`
- `optimum` (BetterTransformer integration)
- `huggingface-hub`
- `scipy`
- `bitsandbytes` (optional, for compression)
- `mlx` (optional, for macOS)

## References

- **GitHub Repository**: <https://github.com/lyogavin/airllm> (accessed 2026-06-18)
- **PyPI Package**: <https://pypi.org/project/airllm/> (accessed 2026-06-18)
- **README.md**: Layer streaming architecture, quickstart, and configuration reference (accessed 2026-06-18)
- **setup.py**: Version 2.11.0, dependencies, build configuration (accessed 2026-06-18)
- **airllm_base.py**: Core `AirLLMBaseModel` class, streaming protocol, profiling (accessed 2026-06-18)
- **auto_model.py**: Architecture detection and model class dispatching (accessed 2026-06-18)
- **Related work cited in README**: SimJeg's Kaggle competition submission for 70B model inference on consumer hardware (<https://www.kaggle.com/code/simjeg/platypus2-70b-with-wikipedia-rag>)
- **Block-wise quantization research**: Paper referenced for compression methodology (<https://arxiv.org/abs/2212.09720>, accessed via README)
- **Model Zoo**: Top 10 models in Open LLM Leaderboard supported (ChatGLM, Qwen, Baichuan, Llama, Mistral) as of v2.6 release notes

## Freshness Tracking

- **Entry created**: 2026-06-18
- **Last source verification**: 2026-06-18 (README, setup.py, source code)
- **Recommended next review**: 2026-09-18 (3 months)

### Confidence Summary

| Section | Confidence | Rationale |
|---------|-----------|-----------|
| Overview | high | Source: README headline + setup.py description, exact quote-grounding available |
| Problem Addressed | high | Source: README §Problem + architecture docs in base class, mechanistic explanation extractable from code |
| Key Statistics | high | Version, downloads, performance metrics extracted from README, setup.py, release notes |
| Key Features | high | Feature descriptions sourced from README §Configurations, §Model Compression, auto_model.py logic, and base class implementation |
| Technical Architecture | high | Layer names, class hierarchy, and component interactions extracted from source code (auto_model.py, airllm_base.py) |
| Installation & Usage | high | Examples copied verbatim from README §Quickstart and configuration sections |
| Supported Models | medium | Model list inferred from auto_model.py dispatcher logic; comprehensive list not explicitly documented in single location |
| Relevance to Claude Code | medium | Use cases derived from feature analysis; integration pattern is hypothetical (not documented in source) |
| Limitations | high | Limitations extracted from README §FAQ and §Configurations, plus caveats inferred from code structure |

### Known Gaps

- **Detailed performance benchmarks** - README references "3x speed improvement" and includes an image (airllm2_time_improvement.png) but detailed numbers are not in text form in the README. The paper reference (<https://arxiv.org/abs/2212.09720>) may contain fuller analysis.
- **Comparison with quantization methods** - README contrasts AirLLM with quantization conceptually but does not benchmark against specific quantization libraries (bitsandbytes, GPTQ).
- **Inference latency characteristics** - Layer-streaming overhead (disk I/O per layer) is not quantified in available docs.

---

**Status**: COMPLETED (all 10 required sections present with extracted evidence)
**Extraction methodology**: Two-phase extractive approach — Phase 1 collected exact passages from README, setup.py, and Python source files; Phase 2 organized passages by section and composed prose grounded in each extraction.

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [LocalAI](../llm-infrastructure/localai.md) | llm-infrastructure | alternative local inference engine with different optimization strategy (quantization-first) for consumer-hardware LLM deployment |
| [TensorZero](../llm-infrastructure/tensorzero.md) | llm-infrastructure | LLM inference gateway with multi-model routing that could expose AirLLM as a selectable provider backend |
| [OpenBao](../llm-infrastructure/openbao.md) | llm-infrastructure | secrets management system (Vault fork) for authenticating gated models and securing locally-deployed AirLLM in agent workflows |
| [Ray](../ml-infrastructure/ray.md) | ml-infrastructure | distributed compute engine for orchestrating AirLLM inference across multi-GPU clusters and horizontally scaled deployments |
| [TrainLoop](../ml-infrastructure/trainloop.md) | ml-infrastructure | managed fine-tuning platform enabling efficient local inference of custom-trained models via AirLLM layer-streaming |
| [Chroma](../data-infrastructure/chroma.md) | data-infrastructure | vector database completing RAG workflows by pairing AirLLM's local inference with semantic vector search and retrieval |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | memory compression system sharing conceptual approach with AirLLM's layer-streaming for reducing token consumption |
| [Micro-Agent](../agent-frameworks/micro-agent.md) | agent-frameworks | lightweight Python ReAct agent framework designed to integrate AirLLM for local offline reasoning without API dependencies |

