---
name: Tinybird - Real-Time Data Platform for Analytics APIs
description: Tinybird is a real-time data platform that helps developers build data products and analytics APIs. It provides a serverless platform for ingesting, transforming, and serving real-time data through...
license: Proprietary (SaaS) with open-source CLI and templates
metadata:
  topic: tinybird
  category: data-infrastructure
  source_url: https://www.tinybird.co/product
  version: "v6.0.1"
  verified: "2026-01-31"
  next_review: "2026-04-30"
---

## Overview

Tinybird is a real-time data platform that helps developers build data products and analytics APIs. It provides a serverless platform for ingesting, transforming, and serving real-time data through auto-generated RESTful APIs, built on managed ClickHouse infrastructure with zero maintenance overhead.

**Core Value Proposition**: Build, deploy, and iterate real-time APIs over massive data sets with fastest-database-in-the-world performance. Query billions of rows in milliseconds with 99.9% uptime, scale to 1k+ RPS at sub-second latency.

---

## Problem Addressed

| Problem                                                                                       | How Tinybird Solves It                                                              |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Building real-time analytics requires complex infrastructure (Kafka, ClickHouse, API servers) | Serverless platform abstracts infrastructure; ingest data and publish APIs with SQL |
| ClickHouse performance requires significant operational expertise                             | Managed ClickHouse with automatic materialized view updates and zero maintenance    |
| User-facing analytics require low-latency, high-concurrency APIs                              | Deploy any SQL query as scalable OpenAPI endpoint with built-in rate limiting       |
| Streaming data pipelines are complex to build and maintain                                    | Events API streams JSON at 1K+ RPS with direct POST from apps                       |
| Analytics for AI agents requires specialized infrastructure                                   | Native MCP server support and "Tinybird Code" agentic CLI for AI-native development |

---

## Key Statistics (as of January 31, 2026)

| Metric                    | Value                                           |
| ------------------------- | ----------------------------------------------- |
| GitHub Repositories       | 169                                             |
| PyPI CLI Version          | 6.0.1                                           |
| SLA Uptime                | 99.9%                                           |
| API Latency Target        | Sub-second at 1k+ RPS                           |
| Events API Throughput     | 1K+ RPS JSON streaming                          |
| Materialized View Speedup | Up to 100x query performance                    |
| Data Source Connectors    | 30+ (Kafka, S3, GCS, PostgreSQL, MySQL, etc.)   |
| BI Tool Integrations      | 15+ (Grafana, Tableau, Metabase, PowerBI, etc.) |

---

## Key Features

### 1. Hosted OLAP Database (Managed ClickHouse)

- **Incremental Materialized Views**: 100x query speed improvement with automatic updates
- **Zero maintenance overhead**: No cluster management, scaling, or optimization required
- **99.9% uptime guarantee**: Distributed, redundant, self-healing architecture
- **Separation of compute**: Zero-copy replication for isolated workloads
- **Schema iteration**: Safe migrations with zero downtime

### 2. Real-Time APIs

- **Instant SQL-to-API**: Deploy any query as a scalable OpenAPI endpoint
- **Auto-generated Swagger docs**: Built-in API documentation
- **Dynamic query parameters**: Template functions for flexible endpoints
- **Token-based authentication**: Static tokens and JWT support
- **Rate limiting**: Built-in protection against abuse
- **Observability**: Query logs, latency monitoring, health checks

### 3. Data Ingestion

- **Events API**: Stream JSON at 1K+ RPS via HTTP POST
- **Kafka Connector**: AWS MSK, Confluent Cloud, Redpanda support
- **Cloud Storage**: S3, GCS connectors with incremental sync
- **Database Connectors**: PostgreSQL, MySQL, MongoDB, DynamoDB
- **Table Functions**: Iceberg, remote URLs, cloud storage
- **Quarantine**: Automatic handling of malformed data

### 4. Developer Experience

- **CLI (`tb`)**: Complete local development workflow
- **Data-as-code**: Git-based version control for schemas and queries
- **Branches**: Isolated environments for testing with real data
- **CI/CD Integration**: Automated deployments with GitHub Actions
- **Local development**: `tb local` for offline development
- **Testing framework**: Built-in test file support

### 5. Analytics Agents (AI-Native Features)

- **Tinybird Code**: Agentic CLI for AI-powered data development
- **MCP Server**: Native Model Context Protocol integration
- **Agent Skills**: Pre-built capabilities for analytics agents
- **Best Practices for AI Agents**: Documentation for AI-native workflows
- **Analytics Agents Templates**: Ready-to-deploy agent architectures

### 6. Publishing & Integrations

- **ClickHouse Interface**: Direct database connection for BI tools
- **Sink Pipes**: Export to S3, GCS, Kafka
- **Prometheus Format**: Endpoints for monitoring systems
- **OpenTelemetry**: Native observability integration

---

## Technical Architecture

<eg>
Data Sources                    Tinybird Platform                      Consumers
─────────────────────────────────────────────────────────────────────────────────

┌─────────────┐    Events API    ┌─────────────────────────────────┐
│ Applications├───────────────→ │                                 │
└─────────────┘     HTTP POST    │     Data Sources (Tables)       │
                                 │   ┌─────────────────────────┐   │
┌─────────────┐    Connectors    │   │  Managed ClickHouse     │   │     ┌────────────┐
│ Kafka/MSK   ├───────────────→ │   │  - MergeTree Engines    │   │←───→│ REST APIs  │
└─────────────┘                  │   │  - Automatic Sharding   │   │     │ (OpenAPI)  │
                                 │   │  - Replication          │   │     └────────────┘
┌─────────────┐    Table         │   └─────────────────────────┘   │
│ S3/GCS      ├───────────────→ │              │                  │     ┌────────────┐
└─────────────┘    Functions     │              ▼                  │←───→│ BI Tools   │
                                 │   ┌─────────────────────────┐   │     │ (ODBC/JDBC)│
┌─────────────┐    CDC           │   │    Pipes (SQL Queries)  │   │     └────────────┘
│ PostgreSQL  ├───────────────→ │   │  - Transformations      │   │
│ MySQL       │                  │   │  - Materialized Views   │   │     ┌────────────┐
└─────────────┘                  │   │  - Copy Pipes           │   │←───→│ MCP Agents │
                                 │   │  - Sink Pipes           │   │     │ (AI/LLM)   │
                                 │   └─────────────────────────┘   │     └────────────┘
                                 │              │                  │
                                 │              ▼                  │     ┌────────────┐
                                 │   ┌─────────────────────────┐   │←───→│ Sinks      │
                                 │   │  Endpoints (APIs)       │   │     │ (S3/Kafka) │
                                 │   │  - Token Auth           │   │     └────────────┘
                                 │   │  - Rate Limiting        │   │
                                 │   │  - Observability        │   │
                                 │   └─────────────────────────┘   │
                                 └─────────────────────────────────┘
</eg>

---

## Installation & Usage

### CLI Installation

```bash
# PyPI (Python 3.8+)
pip install tinybird-cli

# Homebrew (macOS)
brew install tinybird-cli

# Verify installation
tb --version
```

### Quick Start Workflow

```bash
# 1. Authenticate
tb login

# 2. Create a new project
tb create --name my_analytics

# 3. Define a data source (datasource.datasource)
cat > events.datasource << 'EOF'
SCHEMA >
    timestamp DateTime,
    event_type String,
    user_id String,
    value Float64

ENGINE "MergeTree"
ENGINE_SORTING_KEY "timestamp, user_id"
EOF

# 4. Create an endpoint (analytics.pipe)
cat > analytics.pipe << 'EOF'
NODE endpoint
SQL >
    SELECT
        toStartOfHour(timestamp) as hour,
        event_type,
        count() as events,
        uniq(user_id) as users
    FROM events
    WHERE timestamp >= {{DateTime(start_date, '2024-01-01')}}
    GROUP BY hour, event_type
    ORDER BY hour DESC
EOF

# 5. Deploy to production
tb deploy

# 6. Test the endpoint
tb endpoint data analytics --start_date 2024-01-01
```

### Ingest Data via Events API

```bash
# Send events via HTTP POST
curl -X POST 'https://api.tinybird.co/v0/events?name=events' \
  -H "Authorization: Bearer $TINYBIRD_TOKEN" \
  -d '{"timestamp": "2024-01-15 10:30:00", "event_type": "click", "user_id": "u123", "value": 1.5}'
```

### MCP Server Configuration

```json
{
  "mcpServers": {
    "tinybird": {
      "command": "uvx",
      "args": ["mcp-tinybird"],
      "env": {
        "TINYBIRD_TOKEN": "your_token",
        "TINYBIRD_API_URL": "https://api.tinybird.co"
      }
    }
  }
}
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Backend for Analytics Skills**: Use Tinybird as the data layer for Claude Code skills that need real-time analytics
2. **MCP Integration**: Native MCP server enables Claude to query analytics data directly
3. **Agentic Workflows**: "Analytics Agents" templates provide patterns for AI-driven analytics
4. **LLM-Ready Documentation**: Comprehensive llms.txt files for AI consumption

### Patterns Worth Adopting

1. **Data-as-Code**: Treating data schemas and queries as version-controlled code
2. **SQL-to-API Pattern**: Converting any SQL query into a deployable API endpoint
3. **Materialized Views for Performance**: Pre-computing aggregations for fast queries
4. **Branch-Based Testing**: Isolated environments with real data for testing
5. **MCP Server Architecture**: Reference implementation for data-focused MCP servers

### Integration Opportunities

1. **Claude Code Skills**: Build skills that leverage Tinybird for persistent analytics state
2. **Agent Observability**: Use Tinybird to store and query agent execution metrics
3. **Usage Tracking**: Real-time usage-based billing and monitoring for AI applications
4. **Research Data Management**: Store and query research findings with SQL

### Example Use Cases from Customer Stories

- **Vercel**: Developer-facing deployment analytics
- **Resend**: Email delivery metrics
- **Framer**: User-facing real-time analytics
- **Raindrop**: AI observability at petabyte scale
- **LocalStack**: Product analytics for 100K+ instances

---

## Pricing Model

| Tier       | Description                             | Use Case                 |
| ---------- | --------------------------------------- | ------------------------ |
| Free       | Limited compute, ideal for testing      | Development, prototyping |
| Pro        | Pay-per-compute, elastic scaling        | Production workloads     |
| Enterprise | Custom pricing, SLAs, dedicated support | Large-scale deployments  |

**Pricing Philosophy**: Elastic scaling based on compute consumption, pay for value delivered to users.

---

## References

1. **Official Website**: <https://www.tinybird.co/> (accessed 2026-01-31)
2. **Product Page**: <https://www.tinybird.co/product> (accessed 2026-01-31)
3. **Documentation**: <https://www.tinybird.co/docs> (accessed 2026-01-31)
4. **LLM Documentation (Site)**: <https://www.tinybird.co/llms.txt> (accessed 2026-01-31)
5. **LLM Documentation (Docs)**: <https://www.tinybird.co/docs/llms.txt> (accessed 2026-01-31)
6. **PyPI Package**: <https://pypi.org/project/tinybird-cli/> (accessed 2026-01-31)
7. **GitHub Organization**: <https://github.com/tinybirdco> (accessed 2026-01-31)
8. **Analytics Agents Documentation**: <https://www.tinybird.co/docs/forward/analytics-agents> (accessed 2026-01-31)
9. **MCP Server Documentation**: <https://www.tinybird.co/docs/forward/analytics-agents/mcp> (accessed 2026-01-31)
10. **Best Practices for AI Agents**: <https://www.tinybird.co/blog/md/tinybird-best-practices-for-ai-agents> (published 2026-01-27)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [pandera](./pandera.md) | data-infrastructure | referenced by pandera (data-infrastructure) |
| [pocketbase](./pocketbase.md) | data-infrastructure | referenced by pocketbase (data-infrastructure) |
