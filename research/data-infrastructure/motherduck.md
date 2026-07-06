---
title: "MotherDuck"
research_date: "2026-02-23"
source_url: "https://motherduck.com/docs/getting-started/"
github_url: "<https://github.com/motherduckdb/mcp-server-motherduck> (local MCP server)"
version_at_research: "DuckDB 1.4.4 (supported client), MCP server v1.0.1"
license: "Proprietary (SaaS); MCP server: MIT License"
last_verified: "2026-02-23"
version_at_verification: "DuckDB 1.4.4 (client), MCP server v1.0.1"
next_review: "2026-05-23"
---

## Overview

MotherDuck is a serverless cloud data warehouse built on DuckDB that enables fast, interactive SQL analytics without infrastructure overhead. It extends local DuckDB instances into the cloud via a single `ATTACH 'md:';` command, enabling a unique **Dual Execution** model where queries are intelligently routed between your local machine and the cloud. MotherDuck targets the 99% of analytics workloads that do not need petabyte-scale infrastructure, positioning as a simpler, faster, and more cost-effective alternative to Snowflake or BigQuery for interactive analytics.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| DuckDB is powerful locally but lacks cloud persistence and collaboration | MotherDuck adds managed storage, sharing, and identity/access management on top of DuckDB |
| Cloud data warehouses require provisioning clusters and managing infrastructure | Serverless model: submit SQL and MotherDuck handles all execution resources automatically |
| Joining local data with cloud data requires manual ETL pipelines | Dual Execution automatically routes and joins queries across local and cloud data sources |
| AI agents need safe, structured access to analytical databases | Remote MCP server provides read-only SQL access with schema exploration tools for AI clients |
| Moving local DuckDB workflows to the cloud requires re-learning tools | MotherDuck uses standard DuckDB SQL dialect and the same DuckDB Python/CLI SDKs |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| DuckDB GitHub Stars | 36,247 | 2026-02-23 |
| MCP Server GitHub Stars | 424 | 2026-02-23 |
| MCP Server Forks | 70 | 2026-02-23 |
| MCP Server Latest Release | v1.0.1 | 2026-02-23 |
| Supported DuckDB Version | 1.4.4 | 2026-02-23 |
| AWS Regions Available | 2 (us-east-1, eu-central-1) | 2026-02-23 |
| Free Tier Storage | 10 GB | 2026-02-23 |
| Free Tier Compute | 10 CU-hours/month (Pulse) | 2026-02-23 |

---

## Key Features

### Dual Execution (Hybrid Query Routing)

- Automatically routes query stages to the most efficient location: local DuckDB, MotherDuck cloud, or split across both
- Queries referencing local files execute locally; queries referencing MotherDuck/S3 data execute in the cloud
- JOIN operations across local and cloud data are handled transparently — MotherDuck finds the optimal data movement strategy
- No configuration required; activated by connecting with `ATTACH 'md:';`

### Serverless Cloud Architecture

- No clusters, instances, or warehouses to provision or manage
- Hypertenancy model: each user gets isolated compute "Ducklings" sized as Pulse, Standard, Jumbo, Mega, or Giga
- Read scaling via additional Ducklings available for high-concurrency workloads
- Available on AWS `us-east-1` (DuckDB 1.3.0–1.4.4) and `eu-central-1` (DuckDB 1.4.1–1.4.4)

### MCP Server Integration (AI/Claude Native)

- **Remote MCP server** (managed, read-only): Listed in the Claude connector directory; zero-setup OAuth authentication
- **Local MCP server** ([mcp-server-motherduck](https://github.com/motherduckdb/mcp-server-motherduck), MIT): Self-hosted, supports read-write access to local DuckDB files and MotherDuck cloud
- Provides 14+ MCP tools: `list_databases`, `list_tables`, `list_columns`, `search_catalog`, `query`, `ask_docs_question`, and Dives management tools
- `ask_docs_question` tool lets AI assistants query DuckDB and MotherDuck documentation inline
- Supports Claude, ChatGPT, Cursor, Claude Code, and any MCP-compatible client

### Data Connectivity and Formats

- Load data from local files, HTTPS endpoints, Amazon S3 (including private buckets with stored secrets)
- Native support for Parquet, CSV, and JSON formats
- COPY between local DuckDB and MotherDuck storage; materialize query results to S3
- Managed secrets for AWS credentials stored securely in MotherDuck
- Third-party connectivity via JDBC, Go driver, SQLAlchemy

### Web UI and Collaboration

- Notebook UI with SQL IDE and interactive results panel (sort, filter, pivot without re-querying)
- Data catalog with schema browser
- Database sharing with team members ("shares" — zero-copy clones)
- Fine-grained access controls and audit monitoring for enterprise governance

### DuckDB-Native SQL

- Runs the full DuckDB SQL dialect in the cloud (with some limitations: no custom Python UDFs, no server-side attach of Postgres/SQLite, no community extensions)
- `DESCRIBE`, `SUMMARIZE`, and `USING SAMPLE` clauses supported for rapid EDA
- `COMMENT ON` for table/column documentation, surfaced to AI via MCP schema exploration

---

## Technical Architecture

MotherDuck is a distributed analytical system with four key components:

1. **MotherDuck Cloud Service**: Serverless DuckDB execution in AWS regions with managed storage, identity (OAuth/token), authorization, and monitoring
2. **DuckDB SDK (Client-side)**: Standard DuckDB Python (`pip install duckdb==1.4.4`) or CLI — connecting via `ATTACH 'md:';` supercharges the local instance with cloud capabilities
3. **Dual Execution Engine**: A distributed query optimizer that splits query plans across the client DuckDB process and the cloud Duckling; data movement is minimized automatically
4. **MotherDuck Web UI**: Browser-based notebook + SQL IDE with cached, interactive results panel

**Storage model**: MotherDuck-managed data lives on cloud object storage (AWS S3 under the hood). External data (S3 buckets, HTTPS, local files) is queried in-place without ingestion. Fail-safe retention maintains 7 days of data recovery capability. Shares (zero-copy clones) enable collaboration without data duplication.

**Authentication**: Browser-based OAuth flow or access token (`motherduck_token` parameter in connection string). Remote MCP uses OAuth; local MCP uses token or environment variable `motherduck_token`.

**Instance sizing** (Ducklings): Pulse (smallest, free tier) → Standard → Jumbo → Mega → Giga, enabling vertical scaling for large workloads without cluster management.

---

## Installation & Usage

```bash
# Install DuckDB with MotherDuck support (Python)
pip install duckdb==1.4.4

# Install local MCP server (for Claude Code / AI agents with write access)
uvx mcp-server-motherduck  # or: pip install mcp-server-motherduck
```

```python
import duckdb

# Browser-based auth (interactive sessions)
con = duckdb.connect('md:')

# Token-based auth (automated scripts / CI)
con = duckdb.connect('md:?motherduck_token=<your_token>')

# Connect to a specific database
con = duckdb.connect('md:my_db')

# Dual Execution: join local file with cloud table
con.sql("ATTACH 'md:my_db'")
con.sql("""
    SELECT local.id, cloud.revenue
    FROM read_parquet('local_data.parquet') AS local
    JOIN my_db.sales AS cloud ON local.id = cloud.customer_id
""")

# Copy local DuckDB file to MotherDuck
con.sql("COPY DATABASE 'local.duckdb' TO 'md:my_db'")

# Store AWS credentials as a managed secret
con.sql("""
    CREATE OR REPLACE SECRET IN MOTHERDUCK (
        TYPE s3,
        PROVIDER credential_chain
    )
""")
```

```json
// Claude Code MCP config (~/.claude/claude_desktop_config.json)
{
  "mcpServers": {
    "motherduck": {
      "command": "uvx",
      "args": ["mcp-server-motherduck", "--db-path", "md:"],
      "env": {
        "motherduck_token": "<your_token>"
      }
    }
  }
}
```

---

## Relevance to Claude Code Development

### Applications

- **Agent data analysis**: Claude Code agents can query analytical datasets in MotherDuck using the MCP server — no manual SQL wiring needed; the agent discovers schemas and crafts queries autonomously
- **Local-to-cloud analytics pipeline**: Agents working with local DuckDB files (e.g., Parquet exports from tools) can seamlessly promote data to MotherDuck for persistence and sharing
- **Embedded analytics**: Claude-powered applications can use MotherDuck as the analytical backend with SQL results returned directly to the LLM context via MCP
- **Log and telemetry analysis**: Load agent session logs or tool call traces into MotherDuck for interactive SQL investigation using Claude as the query interface

### Patterns Worth Adopting

- **Context engineering via schema-first prompting**: The MotherDuck MCP workflow recommends always starting with schema exploration (`DESCRIBE`, `list_columns`) to hydrate the LLM context before asking analytical questions — a pattern applicable to any data-connected agent
- **Iterative query refinement**: Complex analysis as a multi-turn conversation, starting simple and validating against known data before building up — reduces hallucinated SQL
- **Managed secrets pattern**: Storing external credentials (S3, etc.) in MotherDuck's secure secrets store rather than passing them in agent prompts
- **`COMMENT ON` for data documentation**: Annotating tables and columns with business meaning improves AI-generated query accuracy — directly applicable to any schema used with LLM tooling

### Integration Opportunities

- **MCP server in Claude Code**: Add `mcp-server-motherduck` to `.claude/settings.json` for any project needing analytical data access; agents can explore schemas and run queries without manual tool wiring
- **Research data persistence**: Store research findings, benchmark results, or evaluation data in MotherDuck; use Claude to analyze across sessions via the MCP
- **Plugin analytics**: Skills that generate structured data (e.g., session historian JSONL analysis) could use DuckDB/MotherDuck as the query layer rather than custom parsing scripts
- **Local DuckDB as intermediate format**: Use DuckDB files as a lingua franca between agents — one agent writes results as `.duckdb`, another reads via MotherDuck Dual Execution

---

## References

- [MotherDuck Getting Started](https://motherduck.com/docs/getting-started/) (accessed 2026-02-23)
- [MotherDuck Architecture and Capabilities](https://motherduck.com/docs/concepts/architecture-and-capabilities/) (accessed 2026-02-23)
- [MotherDuck MCP Server Reference](https://motherduck.com/docs/sql-reference/mcp/) (accessed 2026-02-23)
- [MotherDuck MCP Workflows Guide](https://motherduck.com/docs/key-tasks/ai-and-motherduck/mcp-workflows/) (accessed 2026-02-23)
- [DuckDB Python Client: Installation & Authentication](https://motherduck.com/docs/getting-started/interfaces/client-apis/python/installation-authentication/) (accessed 2026-02-23)
- [MotherDuck Pricing](https://motherduck.com/product/pricing/) (accessed 2026-02-23)
- [mcp-server-motherduck GitHub](https://github.com/motherduckdb/mcp-server-motherduck) (accessed 2026-02-23)
- [MotherDuck: DuckDB in the Cloud and in the Client — DuckDB.org](https://duckdb.org/library/motherduck/) (accessed 2026-02-23)
- [MotherDuck CIDR 2024 Paper](https://www.cidrdb.org/cidr2024/papers/p46-atwal.pdf) (accessed 2026-02-23)

---
