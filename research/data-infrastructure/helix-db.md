---
title: HelixDB
category: data-infrastructure
resource: helix-db
published: 2026-06-18
last_reviewed: 2026-06-18
confidence:
  identity: high
  features: high
  architecture: high
  usage: high
  limitations: high
---

## Overview

**HelixDB** is a graph-vector database designed to unify the data infrastructure needed for AI applications. Built entirely in Rust from scratch, HelixDB targets the problem of managing multiple specialized storage systems (relational databases, vector databases, graph databases, KV stores) by consolidating them into a single platform.

Repository: <https://github.com/helixdb/helix-db>
Website: <https://helix-db.com>
Documentation: <https://docs.helix-db.com>

**Current Version**: v3.0.6 (released 2026-06-17)
**License**: Apache-2.0
**Language**: Rust (server), with SDKs in Rust, TypeScript, Go, and Python
**GitHub Stars**: 298 (as of 2026-06-18)
**Repository Created**: 2024-11-23
**Status**: Active development (last update 2026-06-18)

---

## Problem Addressed

"You don't need a separate application DB, relational DB, vector DB, graph DB, or application layers to manage the multiple storage locations. HelixDB gives your agents federated access to company data, for memory, company brains, and applications." (README.md)

Modern AI applications require multiple data storage patterns simultaneously:
- **Relational data**: structured business records
- **Vector embeddings**: for semantic search and retrieval
- **Graph data**: for knowledge representation and relationship traversal
- **Key-value storage**: for high-speed lookups
- **Document storage**: for flexible schema data

HelixDB consolidates these into a unified platform, eliminating the operational complexity and consistency challenges of federated storage systems. This is particularly valuable for AI agents that need to access heterogeneous company data while maintaining memory and context.

---

## Key Statistics

- **398 GitHub stars** (as of 2026-06-18)
- **v3.0.6** release (2026-06-17)
- **Started**: November 2024 (early-stage but rapidly evolving)
- **SDKs**: 4 language bindings (Rust, TypeScript, Go, Python)
- **Supported Data Models**: Graph + Vector (primary), plus KV, Documents, and Relational (secondary)

---

## Key Features

### 1. Unified Data Model

"Helix primarily operates with a graph + vector data model, but it also supports KV, documents, and relational data." (README.md)

HelixDB's core offering is tight integration between graph traversals and vector similarity search. This allows queries to:
- Navigate knowledge graphs while filtering by semantic similarity
- Store vector embeddings on nodes and edges
- Perform hybrid searches combining structural graph patterns with semantic matching

### 2. Multi-SDK Query DSL

"Queries are authored with the Rust, TypeScript, Go, or Python DSL and sent straight to a running instance as dynamic requests against POST /v1/query" (README.md)

The database exposes a language-agnostic query DSL with native bindings for four languages. All SDKs generate the same JSON Abstract Syntax Tree (AST) sent to the server via the `/v1/query` REST endpoint. This approach eliminates the need for a custom protocol or ORM layer — applications build and send queries dynamically without compilation or deployment.

### 3. Local CLI with Interactive Bootstrapping

"The Helix CLI runs and manages local instances and talks to Helix Cloud." (README.md)

The `helix` command-line tool provides:
- **Local instance management**: `helix start dev`, `helix stop dev`
- **Interactive bootstrapping**: `helix chef` — a one-shot command that scaffolds a complete project, installs MCP skills, starts a local instance, seeds example data, and generates a prompt for AI agents
- **Cloud integration**: Authenticate to HelixDB Cloud, switch workspaces/projects, and deploy to managed clusters
- **Configuration management**: `helix init` scaffolds `helix.toml`, `.helix/` workspace, and example queries

### 4. Cloud Deployment

"HelixDB Cloud is an object-storage-backed deployment with integrated vector and full-text search, full ACID transactions, a single writer with auto-scaling reader nodes, and high availability (3+ gateways and DB nodes)." (README.md)

For production use, HelixDB Cloud provides:
- Distributed, high-availability architecture (3+ gateway and DB nodes)
- Persistent storage backed by object storage (vs. in-memory)
- Full ACID transaction support
- Single-writer, auto-scaling reader architecture
- Integrated full-text search
- Managed operations and scaling

### 5. Agent-Ready MCP Integration

"helix chef ... installs the HelixDB query skills and docs MCP" (README.md)

HelixDB provides MCP (Model Context Protocol) servers for Claude Code and similar AI agents:
- Query skills (DSL documentation and examples)
- Documentation MCP (full API reference accessible in-context)
- Seamless handoff from CLI bootstrapping to AI agent implementation

---

## Technical Architecture

### Execution Model

HelixDB operates as a client-server system:
- **Server**: Single Rust process running on a configurable port (default: `6969`)
- **Clients**: Language-specific SDKs that build query ASTs and POST them to `/v1/query`
- **No compilation phase**: Queries are dynamic — built at runtime and sent immediately

### Query Builder Pattern

All SDKs implement a fluent query-builder DSL with two core entry points:

"DSL entry points: read_batch() for read-only transactions and write_batch() for write-capable ones" (sdks/rust/src/lib.rs)

```text
Read transactions: read_batch() → .var_as(...) → .returning([...])
Write transactions: write_batch() → .var_as(...) → .returning([...])
```

Graph traversal starts with `g()` and chains methods for navigation:
- Node selection by label: `g().n_with_label("User")`
- Predicate filtering: `.where(Predicate.eq("name", name))`
- Edge traversal: `.out("FOLLOWS")`, `.in("FOLLOWS")`
- Result projection: `.project([PropertyProjection.new("name")])`

### Storage Options

**Local Development** (in-memory by default):
```bash
helix start dev              # in-memory, ephemeral
helix start dev --disk       # persistent to local disk
```

**Cloud** (object-storage backed, managed service)

### Multi-Language SDK Design

All SDKs share a consistent design:
1. **Builder API** — fluent DSL for constructing queries
2. **Client class** — async HTTP wrapper (`Client::new()`)
3. **Dynamic query execution** — JSON AST sent to `/v1/query` endpoint
4. **Response deserialization** — generic `<T>` for type-safe results

Languages differ only in syntax; the underlying query semantics and wire format are identical.

---

## Installation & Usage

### CLI Installation

```bash
curl -sSL "https://install.helix-db.com" | bash
helix update  # Update to latest version
```

### Project Initialization (Fastest Path)

**Interactive bootstrapper** (recommended for agents):
```bash
helix chef
```
This single command:
- Scaffolds a new project directory
- Installs HelixDB query skills + docs MCP
- Starts a local instance
- Seeds example data
- Writes `HELIX_CHEF_PROMPT.md` for AI agents

**Manual setup**:
```bash
mkdir my-helix-app && cd my-helix-app
helix init                              # Creates helix.toml, .helix/, examples/request.json
helix start dev                         # Start local instance on port 6969
helix query dev --file examples/request.json  # Send a query
helix stop dev                          # Stop the instance
```

### Rust SDK

Install the crate (published as `helix-db`, imported as `helix_db`):

```bash
cargo init && cargo add helix-db tokio sonic-rs
```

**Example query** (from README.md):
```rust
use helix_db::Client;
use helix_db::dsl::prelude::*;

#[register]
pub fn add_user(name: String) {
    write_batch()
        .var_as(
            "user",
            g().add_n("User", vec![("name", name)])
                .value_map(None::<Vec<String>>),
        )
        .returning(["user"])
}

#[tokio::main]
async fn main() {
    let client = Client::new(None).unwrap(); // Defaults to http://localhost:6969
    let new_user = client
        .query::<sonic_rs::Value>()
        .dynamic(add_user("John Doe".to_string()))
        .send()
        .await
        .unwrap();
    println!("new user: {:#}", sonic_rs::to_string_pretty(&new_user).unwrap());
}
```

**Rust SDK Requirements**:
- Version: 2.0.5
- Rust: 1.75 or later
- Key dependencies: `reqwest` (async HTTP), `tokio` (async runtime), `sonic-rs` (JSON), `inventory` (registration macros), `helix-dsl-macros` (query builder)

### TypeScript SDK

Install the package (requires Node.js 20+):

```bash
npm init -y && npm install @helix-db/helix-db
```

**Example query** (from README.md):
```typescript
import {
  Predicate, PropertyInput, PropertyProjection,
  defineParams, g, param, readBatch, writeBatch,
} from "@helix-db/helix-db";

const addUserParams = defineParams({ name: param.string() });
function addUser(p = addUserParams) {
  return writeBatch()
    .varAs("user",
      g().addN("User", { name: PropertyInput.param("name") })
        .project([PropertyProjection.new("name")]),
    )
    .returning(["user"]);
}

const HELIX_URL = "http://localhost:6969/v1/query";
const newUser = await fetch(HELIX_URL, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: addUser().toDynamicJson(addUserParams, { name: "John Doe" }),
}).then((r) => r.json());
console.log("new user:", newUser);
```

**TypeScript SDK Requirements**:
- Version: 2.0.5
- Node.js: 20 or later
- Package: `@helix-db/helix-db` (npm)

### Python SDK

Install from the repository (or PyPI when available):

```bash
pip install helix-db  # or: pip install -e sdks/python
```

**Example query** (from README.md):
```python
from helixdb import Client, Predicate, g, param, define_params, read_batch, write_batch

add_user_params = define_params({"name": param.string()})
add_user = (
    write_batch()
    .var_as("user", g().add_n("User", {"name": add_user_params.name}))
    .returning(["user"])
)

client = Client("http://localhost:6969")
new_user = client.query().dynamic(
    add_user.to_dynamic_request(add_user_params, {"name": "John Doe"})
).send()
print("new user:", new_user)
```

**Python SDK Requirements**:
- Version: 0.1.1
- Python: 3.10 or later
- Status: Alpha (per pyproject.toml classifier)

### Cloud Deployment

For managed HelixDB Cloud:

```bash
helix auth login                    # Authenticate to HelixDB Cloud
helix workspace switch <workspace>  # Select workspace
helix project switch <project>      # Select project
helix init cloud --cluster-id <id>  # Bootstrap cloud project
helix sync production               # Pull gateway URL + auth contract
helix query production --file examples/request.json  # Run queries against cloud
```

---

## Limitations and Caveats

### 1. Local Storage is Ephemeral by Default

"The default storage mode is in-memory — stopping the instance wipes its data. Use helix start dev --disk to persist data across restarts, or --foreground to stream logs." (README.md line 69)

**Impact**: Development instances lose all data when restarted. The `--disk` flag must be explicitly used for persistence; without it, every `helix start dev` creates a fresh, empty instance.

### 2. Early-Stage Ecosystem

HelixDB repository was created November 2024 (7 months old at review time). While the core database is functional and actively developed, the surrounding ecosystem (third-party integrations, mature client libraries, battle-tested patterns) is nascent. SDK versions reflect alpha/early status:
- Python SDK: version 0.1.1 (alpha)
- Rust/TypeScript SDKs: version 2.0.5 (stable, but product is young)

### 3. Single-Writer Cloud Architecture

HelixDB Cloud uses a single-writer pattern with read replicas for scalability. Applications requiring multi-region writes, peer-to-peer replication, or conflict-free distributed writes must work within this constraint.

### 4. Dynamic Queries Only (No Stored Procedures in v3)

Queries are authored dynamically in client code and sent to `/v1/query` on each request. There is no native stored procedure or compiled query language; every query is a dynamic AST. This provides flexibility but may impact query plan caching in high-throughput scenarios.

### 5. Limited Query Optimization Documentation

No publicly documented query optimizer, index selection strategy, or performance tuning guidance was found in reviewed sources. Optimization patterns and best practices for large graphs are not yet documented.

### 6. No Limitations Documented for Graph Size, Query Latency, or Throughput

HelixDB documentation does not state limits on:
- Maximum graph size (nodes, edges)
- Query latency expectations (p50, p99)
- Throughput (queries/sec)
- Transaction isolation levels
- Vector index configuration

These must be validated through testing or direct communication with the HelixDB team.

---

## Relevance to Claude Code Development

### Primary Use Case: Knowledge Graph + Embedding Store for AI Agents

HelixDB directly supports the pattern of AI agents that need:
1. **Dynamic knowledge graphs**: Represent relationships between domain entities (users, documents, concepts)
2. **Vector embeddings**: Enable semantic search and retrieval-augmented generation (RAG)
3. **Unified access**: Query both structural and semantic patterns in a single request

**Example**: An agent building a customer support system could:
- Store support tickets and customer information as graph nodes
- Embed ticket descriptions as vectors
- Query for similar tickets using semantic similarity while filtering by customer metadata in the same transaction

### Integration Pattern: MCP Skills + Bootstrapping

"helix chef ... installs the HelixDB query skills and docs MCP" (README.md)

HelixDB provides MCP servers that expose:
- Query DSL documentation (in-context for agents)
- Full API reference
- Example queries

This enables Claude Code agents to:
1. Bootstrap a complete HelixDB project with a single command
2. Receive MCP-exposed documentation in-context
3. Build and execute queries without leaving the agent environment

### Secondary Use Cases

1. **Session Memory**: Store agent session state and conversation history as graph nodes with vector embeddings of conversation content for similarity search
2. **Company Brain**: Federated access to company data (docs, structured records, relationships) with semantic search
3. **RAG Backend**: Document store + vector embeddings + graph relationships for multi-hop retrieval

### Current Limitations for Integration

- Python SDK is alpha (version 0.1.1); stability and API breakage risk should be assessed before production adoption
- No documented patterns for agent-specific use cases (memory management, session lifecycle, cleanup)
- MCP server details are not yet public (feature may still be in development at review time)

---

## References

- **Official Website**: <https://helix-db.com>
- **GitHub Repository**: <https://github.com/helixdb/helix-db>
- **Documentation**: <https://docs.helix-db.com>
- **Querying Guide**: <https://docs.helix-db.com/database/querying-guide/overview>
- **Changelog**: <https://docs.helix-db.com/change-log/helixdb>
- **Community**: Discord <https://discord.gg/2stgMPr5BD>, Twitter/X <https://x.com/helixdb>
- **Rust SDK Crate**: <https://crates.io/crates/helix-db> (v2.0.5)
- **TypeScript SDK Package**: `@helix-db/helix-db` (v2.0.5) on npm
- **Python SDK Package**: `helix-db` (v0.1.1) on PyPI

**Access dates**: All sources accessed 2026-06-18 via repository clone and gh API.

---

## Freshness Tracking

**Last Updated**: 2026-06-18
**Next Review**: 2026-09-18 (3 months)

**Confidence Summary**:
- **Identity/Metadata** (high) — official GitHub repository, multiple sources confirm name, version, license
- **Features** (high) — extracted from official README and source code inspection
- **Architecture** (high) — SDK source code read directly, DSL patterns extracted from public API
- **Usage Examples** (high) — all examples verbatim from official README.md
- **Limitations** (high) — storage behavior and SDK status verified from source; acknowledged gaps (query optimization, size limits) documented as absent from reviewed sources

**Change Notes**:
- v3.0.6 released 2026-06-17 (CLI updated from prior version)
- Python SDK still at v0.1.1 (alpha)
- Rust and TypeScript SDKs at v2.0.5 (stable relative to product age)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Chroma](./chroma.md) | data-infrastructure | Vector database alternative: both provide embeddings storage + similarity search, Chroma offers Python/JS/Rust clients with metadata filtering |
| [Dolt](./dolt.md) | data-infrastructure | Version-controlled SQL database for agentic memory: complementary relational layer to Helix's graph-vector model, Git-like merge/branch semantics |
| [Honker](./honker.md) | data-infrastructure | Event streaming + pub/sub for agent workflows: provides the message queue and task notification layer agents query from Helix storage |
| [zvec](../ml-infrastructure/zvec.md) | ml-infrastructure | Alibaba's embedded vector database: alternative dense+sparse vector approach with in-process deployment, similar multi-language SDK strategy |
| [CocoIndex](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | Semantic code search via MCP: queries embeddings over code AST to find patterns; compatible with Helix's embedding storage layer |
| [MemPalace](../context-management/mempalace.md) | context-management | AI memory system with semantic search: alternative agent memory backend using ChromaDB; Helix could replace the embedding store for improved graph traversal |
| [Local Memory](../context-management/local-memory.md) | context-management | Persistent memory infrastructure for agents: provides MCP interface for agent memory; Helix could serve as the backend knowledge graph |
| [Micro-Agent](../agent-frameworks/micro-agent.md) | agent-frameworks | Python ReAct agent framework with MCP multi-server support: primary consumer of Helix for dynamic knowledge graph queries and semantic memory |
| [OpenFang](../agent-frameworks/openfang.md) | agent-frameworks | Rust Agent OS with native SKILL.md and MCP integration: target deployment platform for Helix-backed autonomous agents requiring persistent knowledge graphs |
