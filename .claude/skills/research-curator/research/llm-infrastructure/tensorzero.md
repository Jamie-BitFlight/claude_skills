# TensorZero

| Field         | Value                                      |
| ------------- | ------------------------------------------ |
| Research Date | 2026-01-31                                 |
| Primary URL   | <https://tensorzero.com>                   |
| GitHub        | <https://github.com/tensorzero/tensorzero> |
| Documentation | <https://www.tensorzero.com/docs>          |
| PyPI          | <https://pypi.org/project/tensorzero/>     |
| Version       | 2026.1.8 (released 2026-01-30)             |
| License       | Apache-2.0                                 |
| Slack         | <https://www.tensorzero.com/slack>         |
| Discord       | <https://www.tensorzero.com/discord>       |

---

## Overview

TensorZero is an open-source stack for industrial-grade LLM applications, written in Rust for extreme performance (<1ms p99 latency). It unifies five core capabilities: a multi-provider LLM gateway, observability with feedback collection, prompt/model optimization, evaluation with LLM judges, and experimentation with A/B testing. The platform enables a data and learning flywheel where production metrics and human feedback continuously improve prompts, models, and inference strategies.

---

## Problem Addressed

| Problem                                     | Solution                                                              |
| ------------------------------------------- | --------------------------------------------------------------------- |
| LLM provider lock-in and fragmented APIs    | Unified gateway supporting 20+ providers through single API           |
| High latency overhead from LLM proxies      | Rust-based gateway with <1ms p99 latency at 10k+ QPS                  |
| No feedback loop for production LLMs        | Metrics and human feedback collection powers continuous optimization  |
| Prompt engineering is manual and ad-hoc     | Automated prompt engineering with GEPA algorithm and MIPROv2          |
| Fine-tuning requires complex data pipelines | Direct fine-tuning from production feedback (SFT, RLHF)               |
| A/B testing LLMs is complex                 | Built-in adaptive A/B testing with multi-armed bandits                |
| LLM evaluations lack standardization        | Inference and workflow evaluations with heuristics and LLM judges     |
| Observability scattered across tools        | Unified data store with UI, programmatic access, OpenTelemetry export |
| Type safety lacking in LLM interfaces       | Prompt templates with schemas enforce typed interface contracts       |

---

## Key Statistics

| Metric           | Value           | Date Gathered |
| ---------------- | --------------- | ------------- |
| GitHub Stars     | 10,886          | 2026-01-31    |
| GitHub Forks     | 763             | 2026-01-31    |
| Open Issues      | 368             | 2026-01-31    |
| Contributors     | ~105            | 2026-01-31    |
| PyPI Monthly DL  | 45,236          | 2026-01-31    |
| PyPI Weekly DL   | 12,957          | 2026-01-31    |
| Primary Language | Rust            | 2026-01-31    |
| Repository Age   | Since July 2024 | 2026-01-31    |
| Rust Version     | 1.88.0          | 2026-01-31    |

---

## Key Features

### LLM Gateway

- **Unified API**: Access 20+ LLM providers through single interface
- **Performance**: <1ms p99 latency overhead at 10k+ QPS (Rust-based)
- **Inference modes**: Streaming, tool use, structured outputs (JSON), batch, embeddings, multimodal (images, files), caching
- **Prompt templates**: Type-safe schemas enforce consistent interface between application and LLMs
- **High availability**: Routing, retries, fallbacks, load balancing, granular timeouts
- **Rate limiting**: Custom rate limits with granular scopes (user-defined tags)
- **Auth**: Clients access models without sharing provider API keys

### Supported Providers

Anthropic, AWS Bedrock, AWS SageMaker, Azure, DeepSeek, Fireworks, GCP Vertex AI (Anthropic), GCP Vertex AI (Gemini), Google AI Studio (Gemini), Groq, Hyperbolic, Mistral, OpenAI, OpenRouter, SGLang, TGI, Together AI, vLLM, xAI (Grok), and any OpenAI-compatible API (e.g., Ollama).

### Observability

- **Data storage**: Inferences and feedback stored in your own database
- **TensorZero UI**: Debug individual API calls or monitor aggregate metrics
- **Datasets**: Build datasets for optimization, evaluation, and workflows
- **Replay**: Replay historical inferences with new prompts/models/strategies
- **Export**: OpenTelemetry traces (OTLP) and Prometheus metrics export
- **Programmatic access**: Query inferences with filters, compound filters, search, pagination

### Optimization

- **Fine-tuning**: Supervised fine-tuning (SFT) and RLHF from production feedback
- **Prompt engineering**: Automated optimization with GEPA and MIPROv2 algorithms
- **Inference strategies**: Dynamic in-context learning (DICL), best-of-N sampling, mixture-of-N
- **Data flywheel**: Production data continuously improves models (better variants -> better data -> better variants)

### Evaluation

- **Inference evaluations**: Evaluate individual LLM calls with heuristics or LLM judges (unit tests for LLMs)
- **Workflow evaluations**: Evaluate end-to-end workflows with complete flexibility (integration tests for LLMs)
- **Judge optimization**: Optimize LLM judges like any TensorZero function to align with human preferences
- **CLI and UI**: Run evaluations from command line or through the TensorZero UI

### Experimentation

- **Adaptive A/B testing**: Multi-armed bandits for efficient variant selection
- **Principled experiments**: Support for multi-turn systems and sequential testing
- **Confidence**: Ship with statistical confidence in prompt/model changes

---

## Technical Architecture

### Stack Components

| Component     | Technology                                  |
| ------------- | ------------------------------------------- |
| Core Gateway  | Rust (tensorzero-core)                      |
| Python Client | tensorzero PyPI package                     |
| Rust Client   | clients/rust workspace member               |
| Evaluations   | evaluations workspace member                |
| Optimizers    | tensorzero-optimizers workspace member      |
| Database      | User-owned (Postgres, ClickHouse supported) |
| UI            | TensorZero UI (open-source)                 |
| Deployment    | Docker (tensorzero/gateway image)           |

### Workspace Structure

```text
tensorzero/
├── tensorzero-core/          # Core gateway logic
├── gateway/                  # Gateway service
├── clients/
│   ├── rust/                 # Rust client
│   └── python/               # Python client (PyPI: tensorzero)
├── evaluations/              # Evaluation framework
├── tensorzero-optimizers/    # Optimization algorithms
├── provider-proxy/           # Provider proxy layer
└── internal/                 # Internal utilities
    ├── tensorzero-types/     # Type definitions
    ├── tensorzero-auth/      # Authentication
    └── autopilot-*/          # Autopilot components
```

### Data Flow

1. Application sends inference request to TensorZero gateway
2. Gateway routes to configured provider(s) with fallback/retry logic
3. Inference logged to database with request/response data
4. Application sends feedback (metrics, human edits) via feedback API
5. Feedback linked to inference for training data collection
6. Optimization jobs consume feedback to improve prompts/models
7. New variants deployed via A/B testing framework
8. Cycle repeats: better variants -> better data -> better variants

### Configuration Model

TensorZero uses TOML configuration with GitOps-friendly structure:

```toml
# tensorzero.toml
[functions.my_function]
type = "chat"

[functions.my_function.variants.gpt4o]
type = "chat_completion"
model = "gpt-4o"

[functions.my_function.variants.claude]
type = "chat_completion"
model = "claude-sonnet-4-20250514"
weight = 0.5  # A/B test allocation
```

---

## Installation and Usage

### Installation

```bash
# Python client
pip install tensorzero

# Using uv (recommended)
uv pip install tensorzero
```

### Gateway Deployment

```bash
# Docker deployment
docker run -p 3000:3000 tensorzero/gateway

# With configuration
docker run -p 3000:3000 -v $(pwd)/config:/app/config tensorzero/gateway
```

### Basic Inference (TensorZero SDK)

```python
from tensorzero import TensorZeroGateway  # or AsyncTensorZeroGateway

with TensorZeroGateway.build_embedded(...) as t0:
    response = t0.inference(
        model_name="openai::gpt-4o-mini",
        # Switch providers easily: "anthropic::claude-sonnet-4-5"
        input={
            "messages": [
                {"role": "user", "content": "Write a haiku about TensorZero."}
            ]
        },
    )
```

### Using with OpenAI SDK

```python
from openai import OpenAI
from tensorzero import patch_openai_client

client = OpenAI()
patch_openai_client(client, ...)

response = client.chat.completions.create(
    model="tensorzero::model_name::openai::gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### Feedback Collection

```python
# Record feedback for optimization
t0.feedback(
    inference_id=response.inference_id,
    metric_name="user_rating",
    value=5,
)
```

### Running Evaluations (CLI)

```bash
docker compose run --rm evaluations \
  --evaluation-name extract_data \
  --dataset-name hard_test_cases \
  --variant-name gpt_4o \
  --concurrency 5
```

---

## Example Use Cases

The repository includes complete runnable examples:

| Example                       | Description                                             |
| ----------------------------- | ------------------------------------------------------- |
| Data Extraction (NER)         | Optimize extraction pipeline with fine-tuning and DICL  |
| Agentic RAG                   | Multi-hop retrieval agent searching Wikipedia           |
| Haiku with Hidden Preferences | Fine-tune GPT-4o Mini for specific taste using feedback |
| Multimodal Vision Fine-tuning | Fine-tune VLMs for document image categorization        |
| Chess Puzzles with Best-of-N  | Improve LLM chess ability with best-of-N sampling       |

---

## Relevance to Claude Code Development

### Direct Applications

1. **LLM Gateway Patterns**: Unified API with fallbacks, retries, and rate limiting provides reference architecture for resilient LLM integrations.

2. **Feedback Loop Design**: Metrics and human feedback collection enabling continuous improvement could inform Claude Code skill refinement workflows.

3. **Evaluation Framework**: Inference-level and workflow-level evaluations with LLM judges offer testing patterns for skill quality assurance.

4. **Observability Patterns**: Structured logging with programmatic query access provides model for tracking Claude Code operations.

5. **Configuration-as-Code**: TOML-based prompt templates and variant management demonstrate GitOps approach for LLM configurations.

### Patterns Worth Adopting

1. **Dynamic In-Context Learning (DICL)**: Automatically selecting relevant examples from historical data improves LLM performance without fine-tuning.

2. **Adaptive A/B Testing**: Multi-armed bandits efficiently identify best prompts/models with statistical confidence.

3. **Type-Safe LLM Interfaces**: Schema enforcement on prompts creates contracts between application and LLM.

4. **Feedback-to-Training Pipeline**: Direct path from production feedback to fine-tuning enables continuous improvement.

5. **Evaluation Categories**: Separating inference evaluations (unit tests) from workflow evaluations (integration tests) provides clear testing taxonomy.

### Integration Opportunities

1. **Gateway for Multi-Provider Access**: TensorZero could serve as backend for Claude Code operations requiring multiple LLM providers.

2. **Feedback Collection**: Integrate TensorZero feedback API to collect metrics on Claude Code skill effectiveness.

3. **Prompt Optimization**: Use GEPA/MIPROv2 algorithms to optimize Claude Code prompts and instructions.

4. **Evaluation Infrastructure**: Leverage evaluation framework to test skill quality with LLM judges.

5. **Observability Export**: Export Claude Code operations to TensorZero for unified LLM observability.

### Comparison with Claude Code

| Aspect            | TensorZero                    | Claude Code                   |
| ----------------- | ----------------------------- | ----------------------------- |
| Primary Use       | LLMOps platform               | Developer workflow automation |
| Model Support     | 20+ providers                 | Claude models (Anthropic)     |
| Optimization      | Fine-tuning, prompt eng, DICL | Manual skill iteration        |
| Evaluation        | Built-in with LLM judges      | Manual testing                |
| Feedback          | Structured collection & use   | Session-based                 |
| Configuration     | TOML with GitOps              | Skills, CLAUDE.md             |
| Performance Focus | <1ms latency, 10k+ QPS        | Developer experience          |
| Deployment        | Self-hosted Docker            | CLI + IDE integration         |

---

## References

| Source                   | URL                                                                                              | Accessed   |
| ------------------------ | ------------------------------------------------------------------------------------------------ | ---------- |
| GitHub Repository        | <https://github.com/tensorzero/tensorzero>                                                       | 2026-01-31 |
| GitHub README            | <https://github.com/tensorzero/tensorzero/blob/main/README.md>                                   | 2026-01-31 |
| Official Documentation   | <https://www.tensorzero.com/docs>                                                                | 2026-01-31 |
| Quick Start Guide        | <https://www.tensorzero.com/docs/quickstart>                                                     | 2026-01-31 |
| PyPI Package             | <https://pypi.org/project/tensorzero/>                                                           | 2026-01-31 |
| PyPI Stats               | <https://pypistats.org/packages/tensorzero>                                                      | 2026-01-31 |
| GitHub API               | <https://api.github.com/repos/tensorzero/tensorzero>                                             | 2026-01-31 |
| Seed Round Announcement  | <https://www.tensorzero.com/blog/tensorzero-raises-7-3m-seed-round>                              | 2026-01-31 |
| VentureBeat Coverage     | <https://venturebeat.com/ai/tensorzero-nabs-7-3m-seed>                                           | 2026-01-31 |
| GEPA Algorithm           | <https://www.tensorzero.com/docs/optimization/gepa>                                              | 2026-01-31 |
| DICL Documentation       | <https://www.tensorzero.com/docs/gateway/guides/inference-time-optimizations>                    | 2026-01-31 |
| Example: Data Extraction | <https://github.com/tensorzero/tensorzero/tree/main/examples/data-extraction-ner>                | 2026-01-31 |
| Example: Agentic RAG     | <https://github.com/tensorzero/tensorzero/tree/main/examples/rag-retrieval-augmented-generation> | 2026-01-31 |

**Research Method**: Information gathered from official GitHub repository README, GitHub API (stars, forks, issues, contributors, releases), PyPI package metadata, PyPI download statistics API, and Cargo.toml workspace configuration. Statistics verified via direct API calls on 2026-01-31.

---

## Freshness Tracking

| Field              | Value                     |
| ------------------ | ------------------------- |
| Version Documented | 2026.1.8                  |
| Release Date       | 2026-01-30                |
| GitHub Stars       | 10,886 (as of 2026-01-31) |
| Monthly Downloads  | 45,236 (as of 2026-01-31) |
| Next Review Date   | 2026-05-01                |

**Review Triggers**:

- Major version release
- Significant new optimization algorithm
- GitHub stars milestone (15K, 20K)
- PyPI downloads milestone (100K monthly)
- TensorZero Autopilot general availability
- New model provider integrations of note
- Breaking changes to gateway API or configuration format
- Significant updates to evaluation framework
