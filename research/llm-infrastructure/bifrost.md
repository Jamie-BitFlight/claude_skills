---
name: Bifrost AI Gateway
description: 'Bifrost is a high-performance open-source AI gateway written in Go that unifies access to 20+ LLM providers through a single OpenAI-compatible API. Benchmarked at <100 µs overhead per request at 5,000 RPS, it provides automatic failover, adaptive load balancing, semantic caching, MCP gateway support, and enterprise-grade governance.'
license: Apache-2.0
metadata:
  topic: bifrost
  category: llm-infrastructure
  source_url: https://docs.getbifrost.ai
  github: maximhq/bifrost
  version: "transports/v1.4.8"
  verified: "2026-02-26"
  next_review: "2026-05-26"
---

## Overview

Bifrost is a high-performance AI gateway built in Go by Maxim (maximhq) that provides a unified OpenAI-compatible HTTP API across 20+ LLM providers. It focuses on enterprise reliability (automatic fallbacks, adaptive load balancing, clustering) and developer ergonomics (drop-in URL replacement, zero-config startup, web UI). The gateway adds only 11 µs of overhead per request on adequate hardware at 5,000 RPS sustained load. The project also includes a Go SDK for embedded deployment without the HTTP layer.

Key differentiator from comparable tools (LiteLLM, TensorZero): the README explicitly benchmarks 50x faster than LiteLLM, positions as an enterprise gateway rather than an LLMOps platform, and ships MCP gateway support as a first-class feature.

---

## Problem Addressed

| Problem | Solution |
| ------- | -------- |
| Fragmented provider APIs requiring separate SDKs | Single OpenAI-compatible API wrapping 20+ providers |
| LLM provider downtime causing application failures | Automatic failover and fallback chains across providers/models |
| High gateway latency added by proxy layers | Go implementation with 11 µs overhead at 5k RPS |
| API key sprawl and budget visibility gaps | Virtual keys with hierarchical budget and rate limit controls |
| Expensive redundant LLM calls | Semantic caching with vector similarity (Weaviate, Redis, Qdrant, Pinecone) |
| Complex tool integration for AI agents | MCP gateway with OAuth 2.0, tool approval controls, agent auto-approval mode |
| Vendor lock-in requiring code refactoring | Drop-in base URL replacement with no code changes |
| Lack of observability across providers | Native Prometheus metrics and OpenTelemetry distributed tracing |
| Enterprise security requirements | HashiCorp Vault integration, SSO (Google/GitHub), RBAC |

---

## Key Statistics

| Metric | Value | Date Gathered |
| ------ | ----- | ------------- |
| GitHub Stars | 2,556 | 2026-02-26 |
| GitHub Forks | 265 | 2026-02-26 |
| Open Issues | 149 | 2026-02-26 |
| Contributors | ~45 (page 45 of per_page=1) | 2026-02-26 |
| Primary Language | Go (73% by bytes) | 2026-02-26 |
| Repository Age | Since March 2025 | 2026-02-26 |
| Latest Release | transports/v1.4.8 (2026-02-25) | 2026-02-26 |
| Docker Hub Tag | maximhq/bifrost:v1.4.8 | 2026-02-26 |
| Supported Providers | 22 provider directories in core | 2026-02-26 |
| Languages in Repo | Go, TypeScript, Python, HCL, Shell | 2026-02-26 |

SOURCE: GitHub API `https://api.github.com/repos/maximhq/bifrost` (accessed 2026-02-26), GitHub releases API (accessed 2026-02-26), repository languages API (accessed 2026-02-26), contributors API response headers showing page 45 as last page (accessed 2026-02-26).

---

## Key Features

### Unified Provider Gateway

- **OpenAI-compatible API**: Single endpoint accepts standard chat completion, embeddings, and multimodal requests regardless of target provider
- **22 provider implementations**: Anthropic, Azure OpenAI, AWS Bedrock, Cerebras, Cohere, ElevenLabs, Gemini (Google), Groq, Hugging Face, Mistral, Nebius, Ollama, OpenAI, OpenRouter, Parasail, Perplexity, Replicate, Runway, SGLang, Vertex AI, vLLM, xAI
- **Drop-in replacement**: Change only `base_url` in existing OpenAI/Anthropic/GenAI SDK code — no other modifications
- **Model addressing**: Use `provider/model-name` format (e.g., `openai/gpt-4o-mini`, `anthropic/claude-sonnet-4-5`)

### Reliability and Load Management

- **Automatic fallbacks**: Configurable fallback chains across providers and models; requests retry transparently on provider failure
- **Adaptive load balancing**: Weighted distribution across multiple API keys; ~10 ns key selection time
- **Routing rules**: CEL (Common Expression Language) builder for conditional request routing; case-insensitive header matching
- **Clustering**: Multi-node deployment mode for high-availability production workloads (enterprise)

### Performance

- **11 µs gateway overhead** at 5,000 RPS on t3.xlarge (59 µs on t3.medium)
- **100% success rate** sustained at 5,000 RPS in benchmark tests
- **Sub-microsecond queue wait** (1.67 µs average on t3.xlarge)
- **Asynchronous inference support** added in v1.4.8

### Semantic Caching

- Dual-layer: exact hash match first, then vector similarity search (configurable threshold, default 0.8)
- Direct hash mode for exact matching without embedding API calls
- Backend options: Weaviate, Redis (RediSearch), Qdrant, Pinecone
- TTL configuration, per-model/provider cache isolation
- Cache key via `x-bf-cache-key` request header

### MCP Gateway

- Acts as both MCP client and MCP server
- Tool execution with approval controls and auto-approval agent mode
- Code mode for Python orchestration (50% fewer tokens, 40% lower latency per documentation)
- OAuth 2.0 authentication with token refresh for MCP tool providers
- Custom tool registration and exposure

### Governance and Access Control

- Virtual keys with permission scopes and allowed model lists
- Hierarchical budgets: virtual key, team, and customer-level cost limits
- Rate limiting with configurable policies
- Required headers enforcement on every request (added v1.4.8)
- SSO via Google and GitHub; Okta/Entra for enterprise

### Observability

- Native Prometheus metrics export
- OpenTelemetry distributed tracing (OTLP)
- Request logging with header capture (added v1.4.8) and metadata
- Datadog integration (enterprise)
- Audit logging (enterprise)

### Developer Experience

- Zero-config startup: `npx -y @maximhq/bifrost` or `docker run -p 8080:8080 maximhq/bifrost`
- Web UI for visual provider configuration, real-time monitoring, analytics
- SQLite-backed configuration (web UI mode) or static `config.json` (file mode)
- Go SDK (`go get github.com/maximhq/bifrost/core`) for embedded deployment
- WASM plugin support for extending middleware

---

## Technical Architecture

### Module Structure

<eg>
bifrost/
├── npx/                  # NPX launcher script for easy installation
├── core/                 # Core Go library (go get github.com/maximhq/bifrost/core)
│   ├── providers/        # 22 provider implementations (one directory per provider)
│   ├── schemas/          # Shared interfaces and structs
│   └── bifrost.go        # Main gateway logic
├── framework/            # Persistence adapters
│   ├── configstore/      # Configuration storage backends
│   ├── logstore/         # Request logging storage backends
│   └── vectorstore/      # Vector database adapters (for semantic cache)
├── transports/
│   └── bifrost-http/     # HTTP gateway service (versioned at transports/v1.x.x)
├── ui/                   # React/TypeScript web interface
├── plugins/              # Modular plugin system (separate semver per plugin)
│   ├── governance/       # Budget management and access control
│   ├── jsonparser/       # JSON parsing utilities
│   ├── logging/          # Request logging
│   ├── maxim/            # Maxim observability integration
│   ├── mocker/           # Mock responses for testing
│   ├── semanticcache/    # Semantic caching plugin
│   └── telemetry/        # Prometheus/OpenTelemetry telemetry
├── docs/                 # Documentation source
└── tests/                # Test suites
</eg>

### Configuration Model

Two mutually exclusive configuration modes:

1. **Web UI mode**: SQLite database (`config.db`) stores configuration; changes apply without restart via the web interface
2. **File-based mode**: Static `config.json` loaded at startup; requires restart for changes; held in memory only

Data directories:

- `config.db` — provider and gateway configuration (web UI mode)
- `logs.db` — request log database
- Vector store connection — external (Weaviate, Redis, Qdrant, Pinecone)

### Request Flow

1. Client sends OpenAI-compatible request to Bifrost HTTP endpoint
2. Routing rules (CEL expressions) evaluated against request headers/body
3. Provider and model resolved from `provider/model` identifier in request
4. API key selected from weighted pool (~10 ns selection time)
5. Request forwarded to provider with auth headers injected
6. On failure: automatic retry or fallback chain traversal
7. Response logged to `logs.db` with metadata
8. Governance plugin enforces budget and rate limit accounting
9. Semantic cache populated if caching is enabled for the key

### Language Breakdown

| Language | Bytes | Role |
| -------- | ----- | ---- |
| Go | 11,234,410 | Core gateway, providers, plugins |
| TypeScript | 2,887,260 | Web UI (React) |
| Python | 942,699 | Test scripts, tooling |
| HCL | 160,646 | Terraform/infrastructure configs |
| Shell | 30,896 | Build and CI scripts |

SOURCE: GitHub languages API `https://api.github.com/repos/maximhq/bifrost/languages` (accessed 2026-02-26).

---

## Installation and Usage

### Quickstart (30 seconds)

```bash
# NPX — installs and launches latest version
npx -y @maximhq/bifrost

# NPX — specific version
npx -y @maximhq/bifrost --transport-version v1.4.8

# Docker — production deployment
docker run -p 8080:8080 -v $(pwd)/data:/app/data maximhq/bifrost

# Docker — pinned version
docker run -p 8080:8080 maximhq/bifrost:v1.4.8
```

After startup, open `http://localhost:8080` for the web UI.

### First API Call

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello, Bifrost!"}]
  }'
```

### Drop-in Replacement

```diff
# Existing OpenAI SDK usage
- base_url = "https://api.openai.com"
+ base_url = "http://localhost:8080/openai"

# Existing Anthropic SDK usage
- base_url = "https://api.anthropic.com"
+ base_url = "http://localhost:8080/anthropic"

# Existing Google GenAI SDK usage
- api_endpoint = "https://generativelanguage.googleapis.com"
+ api_endpoint = "http://localhost:8080/genai"
```

### Go SDK (Embedded)

```bash
go get github.com/maximhq/bifrost/core
```

```go
import "github.com/maximhq/bifrost/core"

// Use Bifrost as a Go library, no HTTP layer required
```

### Semantic Cache Configuration (config.json snippet)

```json
{
  "semanticCache": {
    "provider": "redis",
    "threshold": 0.8,
    "ttl": 300,
    "cacheByModel": true,
    "cacheByProvider": true
  }
}
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Multi-Provider Routing for Skill Agents**: Bifrost's fallback chains and load balancing provide a reference pattern for routing Claude Code agent tasks across multiple providers when Anthropic APIs are unavailable or rate-limited.

2. **MCP Gateway Reference Implementation**: Bifrost's MCP gateway feature (OAuth 2.0 tool auth, approval controls, agent auto-approval mode) offers implementation patterns relevant to building Claude Code skills that orchestrate MCP tools at scale.

3. **Virtual Key Governance**: The hierarchical virtual key system (key-level, team-level, customer-level budgets) demonstrates access control patterns applicable to multi-tenant Claude Code deployments where different teams need isolated LLM budget controls.

4. **Semantic Caching for Repeated Skill Calls**: Skills that invoke similar prompts repeatedly (e.g., code review, documentation generation) could benefit from Bifrost's dual-layer semantic cache to reduce latency and API costs.

5. **OpenAI-Compatible Interface as Abstraction Layer**: Using Bifrost as a backend allows Claude Code skill integrations to target a stable OpenAI-compatible API regardless of which underlying provider is active.

### Patterns Worth Adopting

1. **Dual-layer caching**: Exact hash check before vector similarity avoids embedding API calls for repeated identical requests — applicable to skill response caching.

2. **CEL-based routing rules**: Using Common Expression Language for request routing conditions provides a declarative, testable routing DSL that could inform Claude Code's task dispatch logic.

3. **Plugin architecture with separate semver**: Each plugin (governance, semanticcache, telemetry) has its own semantic versioning. This pattern reduces coupling and allows selective upgrades.

4. **Zero-config startup with progressive configuration**: Start with defaults via `npx` or Docker, then configure progressively through the web UI — a UX pattern applicable to Claude Code skill installation.

5. **10 ns key selection**: Weighted API key selection at nanosecond speed demonstrates that load balancing overhead need not be measurable at the application level.

### Integration Opportunities

1. **Anthropic API Proxy**: Run Bifrost as a local proxy for Claude API calls to get automatic retry, fallback to other models when Claude is overloaded, and semantic caching of repeated prompts.

2. **MCP Tool Orchestration Layer**: Use Bifrost as a centralized MCP gateway for Claude Code multi-agent workflows where agents need to share access to external tools with proper authentication.

3. **Cost Governance for Agent Workflows**: Apply Bifrost's budget enforcement to control LLM spend across parallel Claude Code agent tasks spawned via the Agent tool.

4. **Observability Pipeline**: Route all LLM calls through Bifrost to collect unified Prometheus metrics and OpenTelemetry traces for Claude Code skill performance monitoring.

### Comparison with TensorZero

| Aspect | Bifrost | TensorZero |
| ------ | ------- | ---------- |
| Primary Language | Go | Rust |
| Latency Overhead | 11 µs (t3.xlarge, 5k RPS) | <1 ms p99 |
| MCP Support | First-class gateway feature | Not documented |
| Optimization | Not included | GEPA, MIPROv2, DICL fine-tuning |
| Web UI | Built-in | Built-in |
| Semantic Cache | Built-in plugin | Not included |
| Configuration | SQLite DB or JSON file | TOML (GitOps) |
| License | Apache-2.0 | Apache-2.0 |
| Enterprise Clustering | Yes | Not documented |
| Feedback/Evaluation | Not included | Core feature |

Bifrost excels at high-throughput gateway infrastructure and MCP orchestration. TensorZero excels at LLM optimization, evaluation, and feedback-driven improvement. They address complementary concerns.

---

## References

| Source | URL | Accessed |
| ------ | --- | -------- |
| GitHub Repository | <https://github.com/maximhq/bifrost> | 2026-02-26 |
| GitHub README | <https://github.com/maximhq/bifrost/blob/main/README.md> | 2026-02-26 |
| Official Documentation | <https://docs.getbifrost.ai> | 2026-02-26 |
| Gateway Setup Guide | <https://docs.getbifrost.ai/quickstart/gateway/setting-up> | 2026-02-26 |
| Semantic Caching Docs | <https://docs.getbifrost.ai/features/semantic-caching> | 2026-02-26 |
| GitHub API — Repo | <https://api.github.com/repos/maximhq/bifrost> | 2026-02-26 |
| GitHub API — Releases | <https://api.github.com/repos/maximhq/bifrost/releases/latest> | 2026-02-26 |
| GitHub API — Languages | <https://api.github.com/repos/maximhq/bifrost/languages> | 2026-02-26 |
| GitHub API — Contributors | <https://api.github.com/repos/maximhq/bifrost/contributors?per_page=1> | 2026-02-26 |
| GitHub API — Providers | <https://api.github.com/repos/maximhq/bifrost/contents/core/providers> | 2026-02-26 |
| Docker Hub Image | <https://hub.docker.com/r/maximhq/bifrost> | 2026-02-26 |
| NPM Package | <https://www.npmjs.com/package/@maximhq/bifrost> | 2026-02-26 |

**Research Method**: Information gathered from GitHub API (repository metadata, releases, languages, contributors, directory contents), GitHub README decoded from API response, official documentation pages (docs.getbifrost.ai), and gateway setup documentation. All statistics verified via direct API calls on 2026-02-26.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [glm5-exacto](./glm5-exacto.md) | llm-infrastructure | referenced by glm5-exacto (llm-infrastructure) |
| [openbao](./openbao.md) | llm-infrastructure | referenced by openbao (llm-infrastructure) |
| [quantum-free-router](./quantum-free-router.md) | llm-infrastructure | referenced by quantum-free-router (llm-infrastructure) |
