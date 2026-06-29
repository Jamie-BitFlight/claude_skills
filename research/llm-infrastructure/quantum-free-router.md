---
title: quantum-free-router
resource_url: https://github.com/spacepirate15/quantum-free-router
resource_type: LLM Router / Infrastructure
category: llm-infrastructure
status: active
research_date: 2026-06-18
last_reviewed: 2026-06-18
next_review: 2026-09-18
---

## Overview

`quantum-free-router` is a professional-grade OpenAI-compatible LLM router that aggregates free-tier models from multiple providers (OpenCode Zen, KiloCode, NVIDIA NIM, Gemini, Mistral, Cerebras, SambaNova, Groq, Cohere) into a single local endpoint at `http://127.0.0.1:4000/v1`. It is built on Bifrost, the Portkey-AI multi-provider routing engine, and designed specifically for long-running AI agents and research tasks where single-provider failures should not stop work.

**Latest commit (verified 2026-06-11):** "Professionalize router docs and tooling" — documentation and repository structure improvements.

## Problem Addressed

Free LLM endpoints are individually unreliable for agent workflows:

> "Free LLM endpoints are useful, but they are operationally unstable when used one at a time: quotas reset at different times, rate limits can appear mid-task, provider catalogs change without warning, some model IDs work directly but not through a router, long-context or large models can timeout under load, agent replies can fail if a single primary model is unavailable."

`quantum-free-router` solves this by:

1. **Aggregating diverse providers** — OpenCode Zen, KiloCode, NVIDIA NIM, Gemini, Mistral, Cerebras, SambaNova, Groq, Cohere exposed under a single local endpoint.
2. **Transparent fallback routing** — Clients call a single URL; Bifrost routes based on model name prefix.
3. **Conservative certification** — Models progress through four reliability tiers (active, retry-later, configured-only, quarantine) before being trusted for long-running work.
4. **Operator control** — Fallback ordering lives in `configs/certification-models.txt` or client config, keeping policy visible and auditable.

## Key Statistics

- **Repository:** <https://github.com/spacepirate15/quantum-free-router>
- **License:** MIT
- **Bifrost version pinned:** 1.5.11 (verified in `install.sh`)
- **Supported architectures:** Linux and WSL2 on x86_64 and aarch64
- **Service port:** 4000 (hardcoded)
- **Active reference fallback chain models (2026-06-11 certification):** 14 models across 8 providers
- **Installation method:** Single-command Bash installer with SHA256 verification

Source: README.md lines 1–52, installation.md lines 1–50, CHANGELOG.md (latest 2026-06-11).

## Key Features

### 1. OpenAI-Compatible API

The router exposes a standard OpenAI-compatible `/v1/chat/completions` endpoint. Clients using the Python OpenAI SDK, curl, or any HTTP client can swap `base_url` to route through `quantum-free-router` without code changes.

**Exact behavior:** Client sends OpenAI-format request to `http://127.0.0.1:4000/v1`. Bifrost reads the provider prefix from the model name (e.g., `opencode` from `opencode/deepseek-v4-flash-free`), forwards the request to the configured provider endpoint, and returns the response through the same OpenAI-compatible interface.

Source: architecture.md lines 41–54, examples/openai-python.py.

**Example Python client:**

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:4000/v1",
    api_key="local-dev",
)

response = client.chat.completions.create(
    model="opencode/deepseek-v4-flash-free",
    messages=[{"role": "user", "content": "Reply with exactly: ok"}],
    temperature=0,
    max_tokens=8,
)

print(response.choices[0].message.content)
```

Source: examples/openai-python.py (verbatim from repository).

### 2. Multi-Provider Aggregation

Nine free-tier providers are supported with specific model catalogs:

| Provider | Local Name | Base URL | Typical Models |
|---|---|---|---|
| OpenCode Zen | `opencode` | `https://opencode.ai/zen` | `deepseek-v4-flash-free`, `big-pickle`, `mimo-v2.5-free`, `nemotron-3-ultra-free` |
| KiloCode | `kilocode` | `https://api.kilo.ai/api/gateway` | `stepfun/step-3.7-flash:free`, `nvidia/nemotron-3-super-120b-a12b:free` |
| NVIDIA NIM | `nvidia-nim` | `https://integrate.api.nvidia.com` | `stepfun-ai/step-3.7-flash`, `meta/llama-3.1-70b-instruct`, `qwen/qwen3.5-122b-a10b`, `nvidia/nemotron-3-ultra-550b-a55b` |
| Gemini | `gemini` | Bifrost default | `gemini-3.5-flash` |
| Mistral | `mistral` | Bifrost default | `mistral-medium-3-5` |
| Cerebras | `cerebras` | Bifrost default | `zai-glm-4.7` |
| SambaNova | `sambanova` | Bifrost default | `DeepSeek-V3.2` |
| Groq | `groq` | Bifrost default | `openai/gpt-oss-120b` |
| Cohere | `cohere` | Bifrost default | `command-a-03-2025` |

Source: providers.md, config.template.json, fallback-chain.md.

### 3. Four-Tier Reliability Model

Models are classified by their operational status:

1. **`active`** — Passed router certification; suitable for inclusion in fallback chains.
2. **`retry-later`** — Free model exists but is quota-limited, slow, or transiently timing out; keep configured but rank lower.
3. **`configured-only`** — Plausible provider candidate not yet certified through this router.
4. **`quarantine`** — Wrong account entitlement, model retired, empty response, or incompatible endpoint.

Source: README.md lines 182–188, architecture.md lines 72–81.

This avoids both premature removal and false trust. As stated in fallback-chain.md: "Do not remove a free model just because it failed once. Remove or quarantine it only after identifying a durable cause."

### 4. Systemd Service Installation

The included `install.sh` automates setup:

1. Downloads Bifrost binary with SHA256 verification from GitHub releases
2. Creates `~/.quantum-free-router/` directory
3. Installs `config.template.json` as a model
4. Generates `~/.quantum-free-router/config.json` (local keys never committed)
5. Registers a systemd service named `quantum-free-router`
6. Starts the router on port 4000

Service commands include:
- `sudo systemctl start quantum-free-router`
- `sudo systemctl restart quantum-free-router`
- `sudo systemctl status quantum-free-router --no-pager`
- `journalctl -u quantum-free-router -n 50 --no-pager`

Source: install.sh (full script and automation steps), installation.md lines 1–130.

### 5. Certification and Health Checks

Three operational tools are provided:

1. **Health Check** (`scripts/health-check.sh`):

   ```bash
   curl -fsS http://127.0.0.1:4000/health
   ```

   Returns HTTP 200 with status JSON when router is operational.

2. **Config Validation** (`scripts/validate-config.py`):

   ```bash
   python3 scripts/validate-config.py ~/.quantum-free-router/config.json --allow-real-keys
   ```

   Validates JSON shape and checks for secret-pattern violations in the local config.

3. **Live Certification** (`scripts/certify-router.sh`):

   ```bash
   QFR_BASE_URL=http://127.0.0.1:4000/v1 \
   QFR_MODEL_FILE=configs/certification-models.txt \
   scripts/certify-router.sh
   ```

   Sends a small deterministic request to every model in the file, prints PASS or FAIL. Current state evidence, not a guarantee of future availability.

Source: installation.md lines 36–99, limits-and-reliability.md lines 1–52, SECURITY.md.

### 6. Curated Reference Fallback Chain

The repository documents a recommended fallback order in `configs/certification-models.txt`, verified as of 2026-06-11:

```text
opencode/deepseek-v4-flash-free (primary)
mistral/mistral-medium-3-5
cerebras/zai-glm-4.7
nvidia-nim/stepfun-ai/step-3.7-flash
kilocode/stepfun/step-3.7-flash:free
kilocode/nvidia/nemotron-3-super-120b-a12b:free
nvidia-nim/meta/llama-4-maverick-17b-128e-instruct
opencode/big-pickle
opencode/mimo-v2.5-free
opencode/nemotron-3-ultra-free
sambanova/DeepSeek-V3.2
groq/openai/gpt-oss-120b
nvidia-nim/qwen/qwen3.5-122b-a10b
cohere/command-a-03-2025
```

Fallback ordering balances "current router compatibility, quality for coding and agent work, free-tier stability, latency under bounded timeouts, diversity across providers, quota reset behavior." Source: fallback-chain.md lines 31–41.

### 7. Provider-Specific Timeout and Retry Configuration

Each provider can be configured with:
- `default_request_timeout_in_seconds` (typically 45–90 seconds depending on model type)
- `max_retries` (typically 1, allowing fast failover to next provider rather than repeated attempts)

Example from config.template.json:

```json
"opencode": {
  "network_config": {
    "default_request_timeout_in_seconds": 70,
    "max_retries": 1
  }
}
```

Source: config.template.json (lines 40–65), limits-and-reliability.md (timeout policy section).

## Technical Architecture

### Components

1. **Bifrost HTTP Service** — Multi-provider routing engine (external dependency, version 1.5.11 pinned).
2. **Provider Configuration** — JSON file at `~/.quantum-free-router/config.json` with API keys and per-provider timeout/retry settings.
3. **Systemd Service** — Runs Bifrost as `quantum-free-router` process bound to `127.0.0.1:4000`.
4. **Scripts** — Certification, health checks, config validation provided as shell and Python utilities.

### Request Flow

```
OpenAI-compatible client
  → POST http://127.0.0.1:4000/v1/chat/completions
      → Bifrost reads model name prefix (e.g., "opencode")
          → Routes to configured provider endpoint
              → Provider response
          → Returns through OpenAI-compatible response format
```

Model names use the format `provider/model-id` (e.g., `opencode/deepseek-v4-flash-free`). The provider prefix before the slash tells Bifrost which provider configuration to use.

Source: architecture.md lines 40–54.

### Fallback Strategy

Fallback ordering can be implemented in two ways:

1. **Client-side** — Agent/application config specifies fallback order and retries on failure.
2. **Wrapper script** — External script wraps the router, catches failures, and retries the next model.

The repository recommends `configs/certification-models.txt` as the reference list, keeping fallback policy visible to the operator. Source: architecture.md lines 56–70.

## Installation & Usage

### One-Command Install (Linux / WSL2)

```bash
curl -fsSL https://raw.githubusercontent.com/spacepirate15/quantum-free-router/main/install.sh | bash
```

The installer:
- Detects OS (Linux) and architecture (x86_64 or aarch64)
- Downloads Bifrost 1.5.11 binary with SHA256 checksum verification
- Creates `~/.quantum-free-router/` directory
- Installs `config.template.json` as a reference
- Creates `~/.quantum-free-router/config.json` if not present
- Registers systemd service `quantum-free-router`
- Starts router on port 4000

Source: install.sh (lines 1–150), installation.md (steps 1–7).

### Add API Keys

```bash
nano ~/.quantum-free-router/config.json
```

Replace placeholder values only for providers you have keys for. Do not commit this file.

Source: installation.md lines 23–34.

### Validate Configuration

```bash
python3 scripts/validate-config.py ~/.quantum-free-router/config.json --allow-real-keys
```

Checks JSON shape and detects secret-pattern violations. Source: installation.md lines 36–48.

### Start and Verify

```bash
sudo systemctl restart quantum-free-router
curl -fsS http://127.0.0.1:4000/health
```

Expected health response: `{"status":"ok"}` (HTTP 200). Source: installation.md lines 50–71.

### Test a Request

```bash
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local-dev" \
  -d '{
    "model": "opencode/deepseek-v4-flash-free",
    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    "temperature": 0,
    "max_tokens": 8
  }'
```

Source: installation.md lines 72–87, README.md lines 77–87.

### Run Certification

```bash
QFR_BASE_URL=http://127.0.0.1:4000/v1 \
QFR_MODEL_FILE=configs/certification-models.txt \
scripts/certify-router.sh
```

Sends deterministic requests to every model in the file. Output shows PASS or FAIL per model. Source: installation.md lines 86–99.

## Limitations and Caveats

### 1. Inherits Free-Tier Unreliability

The router does not bypass free-tier constraints. It mitigates them by providing fallback routes, but does not guarantee service availability. As documented:

> "Free-tier model routing is useful because it gives broad access at low cost. It is unreliable if treated like a paid SLA. This project makes the limits visible and recoverable."

Source: limits-and-reliability.md lines 1–10.

### 2. Provider Quotas Reset Independently

Different providers reset quotas at different times. A model may be available early in the day and unavailable later due to free-tier quota exhaustion. The router cannot predict this. Certification reflects current state, not future state. Source: limits-and-reliability.md lines 11–30.

### 3. Model IDs and Catalogs Change Without Warning

Provider catalogs are not stable. Model IDs documented in the reference chain may be retired or renamed. The operator must re-certify after provider updates.

> "Provider catalogs change without warning; some model IDs work directly but not through a router."

Source: README.md lines 35–41.

### 4. Large Models May Timeout Under Router Bounds

Timeout values are bounded (45–90 seconds typical) to prevent agent tasks from hanging indefinitely. Very large models (e.g., NVIDIA NIM's Nemotron 3 Ultra 550B) may legitimately exceed these bounds and be suitable for ranking lower or manual investigation only.

Source: limits-and-reliability.md lines 19–24, providers.md lines 56–90 (NVIDIA NIM section).

### 5. Not All Provider Models Have Chat Completion Entitlement

A model may appear in a provider's catalog but the account may lack entitlement to use it. NIM specifically notes: "NIM catalog visibility does not always mean the account has chat completion entitlement for every model." Source: providers.md lines 86–89.

### 6. Certification Is Point-in-Time Evidence

Certification scripts reflect the state of the router *at the moment the script runs*. They do not predict future availability. A model that passes certification in the morning may fail in the afternoon due to quota exhaustion or provider-side changes. Source: limits-and-reliability.md lines 46–51.

### 7. Bifrost Dependency

The router depends on Bifrost (external, version 1.5.11 pinned). Security vulnerabilities in Bifrost are out of scope for this repository and should be reported to [Portkey-AI/bifrost](https://github.com/Portkey-AI/bifrost/security). Source: SECURITY.md (scope section).

### 8. API Key Management Burden on Operator

The operator must manage API keys for multiple providers and update the local config when keys are rotated or new providers are added. The template includes placeholders for 9 providers, which represents ongoing maintenance overhead. Source: config.template.json, SECURITY.md (secret handling section).

## Relevance to Claude Code Development

### Direct Use Cases

1. **Agent Fallback Strategy** — Long-running Claude Code agents (e.g., research, code generation, planning) can use `quantum-free-router` as a fallback LLM backend when the primary Claude API is unavailable or rate-limited. The router's certification model ensures agents degrade gracefully rather than crash.

2. **Cost Reduction for Development** — Developers testing long-running agent workflows can route non-critical tasks through `quantum-free-router` to reduce API costs during development iterations.

3. **Multi-Provider Resilience** — Claude Code agents currently depend on a single LLM provider. Integrating `quantum-free-router` as an optional secondary backend would allow agents to survive provider outages or quota exhaustion events.

### Architectural Alignment

The router's four-tier reliability model (active, retry-later, configured-only, quarantine) aligns with Claude Code's need for observable failure modes in agent workflows. Instead of binary "works/doesn't work," operators get granular state visibility and can make informed routing decisions. This is consistent with Claude Code's philosophy of failing explicitly rather than silently.

The separation of policy (fallback ordering in `configs/certification-models.txt` or client config) from infrastructure (Bifrost service) matches Claude Code's pattern of making operational decisions visible to the user rather than burying them in code.

### Integration Notes

- The router exposes an OpenAI-compatible API, which means any Claude Code integration would require wrapping the router client to match Claude's internal LLM interface.
- The router runs as a local systemd service, making it suitable for development environments and self-hosted deployments but not for SaaS deployments.
- The four-tier model could be extended with Claude-specific status categories (e.g., "primary", "verified-fallback", "experimental", "blocked") to support more granular routing logic.

## References

| Source | URL | Access Date |
|---|---|---|
| Repository | <https://github.com/spacepirate15/quantum-free-router> | 2026-06-18 |
| README | <https://github.com/spacepirate15/quantum-free-router/blob/main/README.md> | 2026-06-18 |
| Architecture Docs | <https://github.com/spacepirate15/quantum-free-router/blob/main/docs/architecture.md> | 2026-06-18 |
| Installation Docs | <https://github.com/spacepirate15/quantum-free-router/blob/main/docs/installation.md> | 2026-06-18 |
| Provider Reference | <https://github.com/spacepirate15/quantum-free-router/blob/main/docs/providers.md> | 2026-06-18 |
| Fallback Chain | <https://github.com/spacepirate15/quantum-free-router/blob/main/docs/fallback-chain.md> | 2026-06-18 |
| Limits & Reliability | <https://github.com/spacepirate15/quantum-free-router/blob/main/docs/limits-and-reliability.md> | 2026-06-18 |
| Security Policy | <https://github.com/spacepirate15/quantum-free-router/blob/main/SECURITY.md> | 2026-06-18 |
| Install Script | <https://github.com/spacepirate15/quantum-free-router/blob/main/install.sh> | 2026-06-18 |
| Bifrost Router | <https://github.com/Portkey-AI/bifrost> | 2026-06-18 (pinned version 1.5.11) |

## Freshness Tracking

| Section | Confidence | Notes |
|---|---|---|
| Overview & Identity | high | Latest commit date and Bifrost version verified from git log and install.sh. |
| Problem Addressed | high | Extracted directly from README.md problem statement (lines 31–52). |
| Key Features | high | All features extracted from official documentation (architecture.md, installation.md, providers.md) and verified against code (config.template.json, scripts). |
| Technical Architecture | high | Architecture description and request flow extracted verbatim from architecture.md. |
| Installation & Usage | high | All commands and steps verified against install.sh and installation.md. |
| Limitations | high | Limitations documented explicitly in limits-and-reliability.md, SECURITY.md, and fallback-chain.md. No inferred limitations. |
| Relevance to Claude Code | medium | Direct integration is speculative; alignment is based on architectural patterns observed in Claude Code's approach to agent resilience. No integration currently confirmed. |

**Next review scheduled:** 2026-09-18 (3 months from 2026-06-18).

**Review trigger conditions:** New Bifrost version released, provider catalog changes documented in CHANGELOG.md, certification model list updated, security advisory filed.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [bifrost](./bifrost.md) | llm-infrastructure | external dependency: Bifrost v1.5.11 is the routing engine powering the router |
| [localai](./localai.md) | llm-infrastructure | alternative local LLM serving: free-tier endpoint without multi-provider aggregation |
| [tensorzero](./tensorzero.md) | llm-infrastructure | similar gateway problem: industrial-grade LLM routing with A/B testing and latency optimization |
| [openbao](./openbao.md) | llm-infrastructure | complementary infrastructure: secret engine for managing provider API keys and credential rotation |

