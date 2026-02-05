# Pydantic Logfire

| Field         | Value                                                                     |
| ------------- | ------------------------------------------------------------------------- |
| Research Date | 2026-02-05                                                                |
| Primary URL   | <https://logfire.pydantic.dev/docs/>                                      |
| GitHub        | <https://github.com/pydantic/logfire>                                     |
| PyPI          | <https://pypi.org/project/logfire/>                                       |
| Version       | 4.22.0 (released 2026-02-04)                                              |
| License       | MIT                                                                       |
| Slack         | <https://logfire.pydantic.dev/docs/join-slack/>                           |
| Managed       | <https://logfire.pydantic.dev/> (Pydantic - cloud platform)               |
| MCP Server    | <https://github.com/pydantic/logfire-mcp>                                 |

---

## Overview

Pydantic Logfire is an AI-native observability platform built by the team behind Pydantic. It provides full-stack tracing for LLM applications using OpenTelemetry, combining AI-specific features (conversation panels, token tracking, cost monitoring, tool call inspection) with traditional application observability. Unlike AI-only observability tools that only see the LLM layer, Logfire traces the entire application stack, enabling debugging of both AI reasoning and backend infrastructure issues.

---

## Problem Addressed

| Problem                                              | Solution                                                                        |
| ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| AI-only tools miss backend context                   | Full-stack OpenTelemetry tracing shows what happened inside tool calls          |
| Debugging LLM conversations is difficult             | Human-readable conversation panels with tool call inspection                    |
| Token usage and costs are opaque                     | Built-in token tracking and cost monitoring across providers                    |
| Observability tools have proprietary query languages | SQL-based analysis (PostgreSQL-compatible) queryable by AI agents               |
| Existing tools cannot be queried by AI               | MCP server provides SQL access for AI agents to query production data           |
| Pydantic validation errors are hard to trace         | Native Pydantic integration with validation analytics                           |
| Agent debugging requires multiple tools              | Single platform for traces, metrics, logs with agent-specific visualization     |
| Streaming responses are hard to observe              | Full visibility into streamed chunks with dedicated span handling               |
| Evaluations are UI-managed in other tools            | Code-first evaluations via pydantic-evals, version-controlled and CI-integrated |
| Lock-in with proprietary instrumentation             | Built on OpenTelemetry standard, data portable to any OTel backend              |

---

## Key Statistics

| Metric           | Value        | Date Gathered |
| ---------------- | ------------ | ------------- |
| GitHub Stars     | 3,984        | 2026-02-05    |
| GitHub Forks     | 204          | 2026-02-05    |
| Open Issues      | N/A          | 2026-02-05    |
| Primary Language | Python       | 2026-02-05    |
| Python Requires  | >=3.9        | 2026-02-05    |
| Repository Age   | Since April 2024 | 2026-02-05 |

---

## Key Features

### AI/LLM Observability

- **LLM Panels**: Visual inspection of conversations, tool calls, and responses
- **Token Tracking**: Per-request and per-model token usage visibility
- **Cost Monitoring**: Spending tracking across providers with threshold alerts
- **Tool Call Inspection**: Arguments, responses, and latency for each tool call
- **Streaming Support**: Debug streaming responses with chunk-level visibility
- **Multi-turn Conversations**: Trace entire conversation flows across turns

### LLM Framework Integrations

| Framework       | Integration Method                          |
| --------------- | ------------------------------------------- |
| Pydantic AI     | `logfire.instrument_pydantic_ai()`          |
| OpenAI          | `logfire.instrument_openai()`               |
| OpenAI Agents   | `logfire.instrument_openai_agents()`        |
| Anthropic       | `logfire.instrument_anthropic()`            |
| Claude Agent SDK| Via Langsmith OTel bridge                   |
| LangChain       | Built-in OTel support                       |
| LlamaIndex      | `logfire.instrument_llamaindex()`           |
| LiteLLM         | `logfire.instrument_litellm()`              |
| Google GenAI    | `logfire.instrument_google_genai()`         |
| Magentic        | Built-in Logfire support                    |
| Mirascope       | `@with_logfire` decorator                   |

### Web Framework Integrations

- **FastAPI**: `logfire.instrument_fastapi()`
- **Django**: `logfire.instrument_django()`
- **Flask**: `logfire.instrument_flask()`
- **Starlette**: `logfire.instrument_starlette()`
- **AIOHTTP**: `logfire.instrument_aiohttp_client()`, `logfire.instrument_aiohttp_server()`
- **ASGI/WSGI**: Generic middleware support

### Database Integrations

- **Psycopg**: `logfire.instrument_psycopg()`
- **SQLAlchemy**: `logfire.instrument_sqlalchemy()`
- **Asyncpg**: `logfire.instrument_asyncpg()`
- **PyMongo**: `logfire.instrument_pymongo()`
- **MySQL**: `logfire.instrument_mysql()`
- **SQLite3**: `logfire.instrument_sqlite3()`
- **Redis**: `logfire.instrument_redis()`
- **BigQuery**: Built-in, no config needed

### HTTP Client Integrations

- **HTTPX**: `logfire.instrument_httpx()`
- **Requests**: `logfire.instrument_requests()`
- **AIOHTTP**: `logfire.instrument_aiohttp_client()`

### Additional Integrations

- **AWS Lambda**: `logfire.instrument_aws_lambda()`
- **Celery**: `logfire.instrument_celery()`
- **Airflow**: Built-in, config needed
- **FastStream**: Built-in, config needed
- **Pytest**: `pytest --logfire` plugin
- **Standard Logging**: Integration with logging, loguru, structlog
- **System Metrics**: `logfire.instrument_system_metrics()`
- **Stripe**: Via HTTP instrumentation

### Platform Features

- **SQL Query Interface**: PostgreSQL-compatible SQL for data analysis
- **MCP Server**: Native Model Context Protocol server for AI agent querying
- **Live View**: Real-time trace visualization dashboard
- **Natural Language Search**: LLM-powered SQL generation via Pydantic AI
- **Standard Dashboards**: Pre-built dashboards for web server metrics, system metrics
- **Evaluations**: Integration with pydantic-evals for code-first testing

---

## Technical Architecture

### Stack Components

| Component       | Technology                                    |
| --------------- | --------------------------------------------- |
| Protocol        | OpenTelemetry (traces, metrics, logs)         |
| Query Engine    | DataFusion (PostgreSQL-compatible SQL)        |
| Python SDK      | Python 3.9+ with async support                |
| JS/TS SDK       | Node.js, browsers, Next.js, Cloudflare, Deno  |
| Rust SDK        | Native Rust implementation                    |
| MCP Server      | logfire-mcp PyPI package                      |

### Architectural Layers

```text
Application Code
       |
Logfire SDK (logfire.configure() + instrument_*)
       |
OpenTelemetry Exporters
       |
Logfire Backend (Cloud)
       |
DataFusion SQL Engine -> MCP Server -> AI Agents
```

### Data Model

- **Spans**: Operations with duration, parent/child relationships
- **Traces**: Tree structures of related spans
- **Metrics**: Aggregated values over time (histograms, counters)
- **Logs**: Timestamped events without duration

### MCP Server Tools

1. `find_exceptions(age: int)` - Get exception counts grouped by file
2. `find_exceptions_in_file(filepath: str, age: int)` - Detailed trace info for file
3. `arbitrary_query(query: str, age: int)` - Custom SQL queries on traces/metrics
4. `get_logfire_records_schema()` - Schema for custom queries

---

## Installation and Usage

### Installation

```bash
# Basic installation
pip install logfire

# Using uv
uv pip install logfire

# MCP server
pip install logfire-mcp
# or run directly
uvx logfire-mcp@latest
```

### Authentication

```bash
logfire auth
```

### Basic Instrumentation

```python
import logfire

logfire.configure()
logfire.info('Hello, {name}!', name='world')

# Manual spans
with logfire.span('Processing {item}', item='data'):
    # ... processing code ...
    logfire.debug('Step completed')
```

### OpenAI Instrumentation

```python
import openai
import logfire

client = openai.Client()
logfire.configure()
logfire.instrument_openai()

response = client.chat.completions.create(
    model='gpt-4',
    messages=[{'role': 'user', 'content': 'Hello!'}],
)
```

### Anthropic Instrumentation

```python
import anthropic
import logfire

client = anthropic.Anthropic()
logfire.configure()
logfire.instrument_anthropic()

response = client.messages.create(
    max_tokens=1000,
    model='claude-3-haiku-20240307',
    system='You are a helpful assistant.',
    messages=[{'role': 'user', 'content': 'Hello!'}],
)
```

### FastAPI + Database Example

```python
from fastapi import FastAPI
import logfire

app = FastAPI()

logfire.configure()
logfire.instrument_fastapi(app)
logfire.instrument_httpx()
logfire.instrument_sqlalchemy()
```

### Pydantic AI Integration

```python
from pydantic_ai import Agent
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

agent = Agent('openai:gpt-4', system_prompt='You are helpful.')
result = agent.run_sync('Hello!')
```

### MCP Server Configuration (Claude Code)

```bash
claude mcp add logfire -e LOGFIRE_READ_TOKEN="your-token" -- uvx logfire-mcp@latest
```

### SQL Query Example

```sql
SELECT
    span_name,
    attributes->>'gen_ai.usage.input_tokens' as input_tokens,
    attributes->>'gen_ai.usage.output_tokens' as output_tokens,
    duration
FROM records
WHERE span_name LIKE 'llm%'
ORDER BY start_timestamp DESC
LIMIT 100
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Agent Debugging**: Logfire's full-stack tracing reveals both AI reasoning and backend behavior when agents call tools, enabling diagnosis of whether issues are in prompts or infrastructure.

2. **MCP Server for AI Self-Debugging**: The Logfire MCP server allows Claude Code to query its own production traces via SQL, enabling self-diagnosis of errors and performance issues.

3. **Claude Agent SDK Support**: Native instrumentation for Claude Agent SDK via Langsmith OTel bridge provides visibility into Claude-based agent systems.

4. **Pydantic AI Integration**: First-class support for Pydantic AI (used in many Claude Code skills) with automatic conversation tracing.

5. **Evaluation Pipeline**: Integration with pydantic-evals provides code-first, version-controlled evaluation framework for testing agent behaviors.

### Patterns Worth Adopting

1. **Full-Stack Context for AI**: Logfire's approach of combining AI observability with backend tracing ensures debugging includes the complete picture (the "Scenario A vs B" diagnostic pattern).

2. **SQL-Queryable Telemetry**: Exposing observability data via SQL enables both human analysis and AI-powered querying - a pattern applicable to other debugging tools.

3. **Code-First Evaluations**: pydantic-evals treats evaluations as code (version-controlled, CI-integrated) rather than UI-managed, a pattern for rigorous testing.

4. **MCP-Enabled Observability**: Providing MCP server access to telemetry data enables AI agents to autonomously investigate production issues.

5. **Progressive Instrumentation**: One-line `instrument_*()` calls provide immediate value with minimal code changes - a pattern for tool adoption.

### Integration Opportunities

1. **Session Debugging**: Add Logfire instrumentation to Claude Code skills/agents for production debugging.

2. **Self-Healing Agents**: Use Logfire MCP to enable agents to detect and diagnose their own failures.

3. **Cost Tracking**: Monitor token usage across different agent configurations to optimize costs.

4. **Performance Baselines**: Establish latency and throughput baselines for agent operations.

5. **Evaluation Framework**: Adopt pydantic-evals patterns for systematic skill/agent testing.

### Comparison with AI-Only Tools

| Aspect                  | Logfire                              | Langfuse/Arize/LangSmith        |
| ----------------------- | ------------------------------------ | ------------------------------- |
| Primary Focus           | Full-stack AI observability          | LLM-only observability          |
| Backend Visibility      | Yes (via OpenTelemetry)              | No (tool call input/output only)|
| Query Interface         | PostgreSQL-compatible SQL            | Proprietary APIs/UI             |
| AI Agent Queryable      | Yes (MCP server with SQL)            | Limited to predefined endpoints |
| Protocol                | OpenTelemetry standard               | Proprietary                     |
| Lock-in                 | None (OTel portable)                 | Vendor-specific                 |
| Pydantic Integration    | Native (same team)                   | External integration            |

---

## Pricing

| Tier        | Price                           | Retention | Notes                                |
| ----------- | ------------------------------- | --------- | ------------------------------------ |
| Free        | $0 (first 10M units/month)      | 30 days   | Equivalent to $20 of usage           |
| Pro         | $2 per million units            | 30 days   | Spans, logs, or metrics metered      |
| Enterprise  | Contact sales                   | Extended  | Custom retention, self-hosting       |

- **Unit**: One span, log, or metric
- **Payload**: 5 KB average per unit (generous)
- **No**: Per-host, per-seat, or per-project charges

---

## References

| Source                       | URL                                                                        | Accessed   |
| ---------------------------- | -------------------------------------------------------------------------- | ---------- |
| Official Documentation       | <https://logfire.pydantic.dev/docs/>                                       | 2026-02-05 |
| GitHub Repository            | <https://github.com/pydantic/logfire>                                      | 2026-02-05 |
| GitHub README                | <https://raw.githubusercontent.com/pydantic/logfire/main/README.md>        | 2026-02-05 |
| PyPI Package                 | <https://pypi.org/project/logfire/>                                        | 2026-02-05 |
| AI Observability Guide       | <https://logfire.pydantic.dev/docs/ai-observability/>                      | 2026-02-05 |
| Integrations Index           | <https://logfire.pydantic.dev/docs/integrations/>                          | 2026-02-05 |
| OpenAI Integration           | <https://logfire.pydantic.dev/docs/integrations/llms/openai/>              | 2026-02-05 |
| Anthropic Integration        | <https://logfire.pydantic.dev/docs/integrations/llms/anthropic/>           | 2026-02-05 |
| Claude Agent SDK Integration | <https://logfire.pydantic.dev/docs/integrations/llms/claude-agent-sdk/>    | 2026-02-05 |
| Pydantic AI Integration      | <https://logfire.pydantic.dev/docs/integrations/llms/pydanticai/>          | 2026-02-05 |
| MCP Server Guide             | <https://logfire.pydantic.dev/docs/how-to-guides/mcp-server/>              | 2026-02-05 |
| MCP Server Repository        | <https://github.com/pydantic/logfire-mcp>                                  | 2026-02-05 |
| Concepts Documentation       | <https://logfire.pydantic.dev/docs/concepts/>                              | 2026-02-05 |
| Pricing/Costs                | <https://logfire.pydantic.dev/docs/logfire-costs/>                         | 2026-02-05 |

**Research Method**: Information gathered from official GitHub repository README, GitHub API (stars, forks, description, topics), PyPI package metadata, and official documentation markdown files fetched directly from GitHub. Statistics verified via direct API calls on 2026-02-05.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | 4.22.0                              |
| Release Date       | 2026-02-04                          |
| GitHub Stars       | 3,984 (as of 2026-02-05)            |
| Next Review Date   | 2026-05-05                          |

**Review Triggers**:

- Major version release (5.x)
- Significant new LLM framework integrations
- MCP server feature additions
- pydantic-evals major updates
- GitHub stars milestone (5K, 10K)
- New AI-specific dashboard features
- Claude Code native integration announcements
