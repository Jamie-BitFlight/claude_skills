---
name: Living Architecture
description: Living Architecture extracts operational flow-based architecture from code as living documentation using the Rivière schema. Created by Nick Tune, it provides a language-agnostic approach to...
license: Apache-2.0
metadata:
  topic: living-architecture
  category: documentation-tools
  source_url: https://github.com/NTCoding/living-architecture
  github: NTCoding/living-architecture
  version: "0.0.0"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

Living Architecture extracts operational flow-based architecture from code as living documentation using the Rivière schema. Created by Nick Tune, it provides a language-agnostic approach to visualizing how operations flow through systems (UI → API → UseCase → DomainOp → Event → EventHandler) rather than static structural dependencies. The project includes tools for extraction, modeling, querying, and interactive visualization of software architecture with AI-assisted workflows.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual architecture diagrams become stale and disconnected from code | Extracts architecture directly from codebase, ensuring documentation stays synchronized with implementation |
| Traditional dependency graphs show technical structure but not operational flow | Models operational flow through architectural layers (UI, API, UseCase, DomainOp, Event, EventHandler) rather than just technical dependencies |
| Cross-domain architecture understanding requires manual analysis | Provides tools to trace flows end-to-end, identify cross-domain connections, and visualize component interactions |
| Architecture documentation requires manual effort and domain expertise | Leverages AI assistance through CLAUDE.md integration to extract and document architectural patterns from code |
| Language-specific architecture tools limit polyglot systems | Language-agnostic Rivière JSON schema works with TypeScript, Java, Python, Go, or any combination |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 79 | 2026-02-20 |
| Downloads/month | 2,404 | 2026-02-20 |
| Contributors | Unable to verify (API rate limited) | 2026-02-20 |
| Latest Release | No formal releases yet | 2026-02-20 |
| Forks | 9 | 2026-02-20 |
| Created | 2025-12-23 | 2026-02-20 |
| Last Updated | 2026-02-08 | 2026-02-20 |
| Language | TypeScript | 2026-02-20 |

---

## Key Features

### Architecture Extraction

- TypeScript AST-based component extraction using ts-morph (`@living-architecture/riviere-extract-ts`)
- Decorator-based marking of architectural components (`@living-architecture/riviere-extract-conventions`)
- JSON Schema-based extraction config DSL (`@living-architecture/riviere-extract-config`)
- AI-assisted extraction workflows via Claude Code integration
- Language-agnostic schema supports manual or tooling-based extraction for any language

### Component Type System

Standard component types model operational flow:

- **UI**: User-facing routes and screens with route definitions
- **API**: HTTP endpoints (REST, GraphQL) with method and path metadata
- **UseCase**: Application-level orchestration logic
- **DomainOp**: Domain logic and entity operations with state transitions
- **Event**: Async events published between domains
- **EventHandler**: Event subscribers and handlers
- **Custom**: Extensible type system (message queues, external APIs, cron jobs)

### Architecture Modeling

- Graph-based builder API for programmatic architecture construction (`@living-architecture/riviere-builder`)
- Source location tracking with repository, file path, line number, method name
- Domain and module organization with multi-domain system support
- State transition modeling for domain operations
- Signature and behavior documentation (parameters, return types, validates, modifies, emits)

### Architecture Querying

- Browser-safe query library with no Node.js dependencies (`@living-architecture/riviere-query`)
- Find entry points (components with no incoming links)
- Trace operational flows from specific components
- Identify cross-domain connections
- Filter components by type, domain, or module
- Query by component properties or metadata

### Visualization

- **Éclair**: Interactive web-based visualizer for architecture graphs
- Trace flows end-to-end through multiple domains
- Filter by domain or component type
- Search components by name or properties
- Click-through to source code locations
- Demo mode with sample e-commerce architecture

### CLI Tooling

- `riviere builder init`: Initialize new architecture graph
- Extract architecture with domain and module organization
- Output as JSON conforming to Rivière schema
- Support for multi-repository systems

### AI-Assisted Workflows

- CLAUDE.md integration with project-specific instructions
- Task workflow automation (docs/workflow/task-workflow.md)
- Separation of concerns skill enforcement
- Domain terminology management with Contextive glossary
- Automated architecture extraction guidance

---

## Technical Architecture

### Monorepo Structure

Living Architecture uses NX monorepo with pnpm workspaces:

<eg>
packages/         - npm-publishable libraries
  riviere-schema              - Schema definitions and validation
  riviere-query               - Browser-safe query library
  riviere-builder             - Node.js builder API
  riviere-cli                 - CLI tool (binary: "riviere")
  riviere-extract-config      - Extraction config DSL
  riviere-extract-conventions - Component marking decorators
  riviere-extract-ts          - TypeScript AST-based extractor

apps/             - Deployable applications (not published)
  eclair                      - Interactive visualizer
  docs                        - Documentation website
</eg>

### Rivière Schema

JSON-based schema with three main sections:

```json
{
  "version": "0.1",
  "metadata": {
    "domains": { },
    "sources": [ ],
    "customTypes": { }
  },
  "components": [ ],
  "links": [ ]
}
```

**Component Structure**:

```typescript
{
  "id": "domain:module:type:name",
  "type": "API | UI | UseCase | DomainOp | Event | EventHandler | Custom",
  "name": "Component Name",
  "domain": "domain-name",
  "module": "module-name",
  "sourceLocation": {
    "repository": "repo-name",
    "filePath": "src/path/file.ts",
    "lineNumber": 42,
    "methodName": "methodName"
  },
  // Type-specific fields (apiType, httpMethod, eventName, etc.)
}
```

**Link Types**:
- `sync`: Synchronous call (API → UseCase)
- `async`: Asynchronous event (Event → EventHandler)

### Dependency Strategy

- Browser-safe query package has zero Node.js dependencies
- Builder depends on query (server-side only)
- CLI bundles dependencies via esbuild
- NX `updateDependents: "auto"` triggers automatic CLI patch bumps when bundled packages update

### Quality Gates

- 100% test coverage enforced via vitest
- Lint (ESLint with TypeScript rules)
- Type checking (TypeScript strict mode)
- Markdown linting (markdownlint-cli2)
- Dependency cruiser for architectural boundaries
- Knip for unused dependencies
- Husky pre-commit hooks
- Full `pnpm verify` gate required before commit

---

## Installation & Usage

### Install CLI Globally

```bash
npm install -g @living-architecture/riviere-cli
```

### Initialize Architecture Graph

```bash
riviere builder init --domain orders --output graph.json
```

### Build Graph Programmatically

```typescript
import { RiviereBuilder } from '@living-architecture/riviere-builder';

const builder = RiviereBuilder.new({
  sources: [{ repository: 'https://github.com/your-org/repo' }],
  domains: {
    orders: { description: 'Order management', systemType: 'domain' }
  }
});

const api = builder.addApi({
  name: 'Create Order',
  domain: 'orders',
  module: 'checkout',
  apiType: 'REST',
  httpMethod: 'POST',
  path: '/orders',
  sourceLocation: {
    repository: 'repo',
    filePath: 'src/api/orders.ts'
  }
});

const useCase = builder.addUseCase({
  name: 'PlaceOrder',
  domain: 'orders',
  module: 'checkout',
  sourceLocation: {
    repository: 'repo',
    filePath: 'src/usecases/place-order.ts'
  }
});

builder.link({ from: api.id, to: useCase.id, type: 'sync' });

const graph = builder.build();
```

### Query Architecture Graph

```typescript
import { RiviereQuery } from '@living-architecture/riviere-query';

const query = RiviereQuery.fromJSON(graphData);

// Find entry points (no incoming links)
const entryPoints = query.entryPoints();

// Trace operational flow from component
const flow = query.traceFlow('orders:checkout:api:create-order');

// Find cross-domain connections
const crossDomain = query.crossDomainLinks('orders');

// Filter components by type
const events = query.componentsByType('Event');
```

### Visualize with Éclair

```bash
git clone https://github.com/NTCoding/living-architecture.git
cd living-architecture
pnpm install
pnpm nx serve eclair
```

Open <http://localhost:5173/eclair> and load your graph JSON file.

---

## Relevance to Claude Code Development

### Applications

- **Living documentation for claude_skills**: Extract architecture showing how skills, agents, plugins, and hooks interact operationally
- **Multi-plugin flow visualization**: Trace how operations flow through plugin activation, skill loading, agent delegation, and tool execution
- **Agent orchestration patterns**: Document and visualize agent coordination patterns (orchestrator → sub-agent flows)
- **MCP integration mapping**: Model MCP server interactions as external API components with event flows
- **Skill dependency analysis**: Identify cross-skill references and activation patterns

### Patterns Worth Adopting

- **CLAUDE.md integration**: Structured AI context file with project overview, conventions, and workflow guidance
- **Separation of concerns enforcement**: Development skill that audits code against architectural patterns
- **Domain terminology management**: Contextive glossary.yml for consistent vocabulary across documentation and code
- **Task workflow automation**: Formal workflow documentation in docs/workflow/ with step-by-step agent guidance
- **Process before fix philosophy**: Improve tooling/process when encountering issues, not just symptom fixes
- **Quality gate with 100% coverage**: Strict verification gate prevents degradation
- **Bundled dependency auto-update**: NX updateDependents pattern keeps CLI in sync with bundled libraries
- **Browser-safe vs server packages**: Clear separation of browser-compatible query library from Node.js builder

### Integration Opportunities

- **Extract claude_skills architecture**: Create Rivière graph showing:
  - UI: Claude Code CLI interface
  - API: Plugin marketplace endpoints, MCP tool calls
  - UseCase: Skill activation workflows, agent delegation patterns
  - DomainOp: Core skill operations (research, validation, transformation)
  - Event: Hook triggers (session-start, pre-commit, post-task)
  - EventHandler: Hook implementations responding to lifecycle events
- **Visualize plugin interactions**: Use Éclair to show how skills in research-curator orchestrate research-agent-patterns
- **Document agent workflows**: Model context-gathering → task execution → validation patterns
- **MCP tool flow mapping**: Trace mcp__Ref__ref_search_documentation → skill references → agent responses
- **Cross-plugin dependency analysis**: Identify which skills reference or depend on others

---

## References

- [Living Architecture Repository](https://github.com/NTCoding/living-architecture) (accessed 2026-02-20)
- [Living Architecture Documentation](https://living-architecture.dev) (accessed 2026-02-20)
- [Éclair Demo](https://living-architecture.dev/eclair/?demo=true) (accessed 2026-02-20)
- [npm @living-architecture org](https://www.npmjs.com/org/living-architecture) (accessed 2026-02-20)
- [Nick Tune (creator)](https://nick-tune.me) (accessed 2026-02-20)
- [Sample Architecture: ecommerce-complete.json](https://raw.githubusercontent.com/NTCoding/living-architecture/main/apps/eclair/public/ecommerce-complete.json) (accessed 2026-02-20)
- [GitHub API Repository Metadata](https://api.github.com/repos/NTCoding/living-architecture) (accessed 2026-02-20)
- [npm Downloads Statistics](https://api.npmjs.org/downloads/point/last-month/@living-architecture/riviere-cli) (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [codewiki-google](../ai-research-tools/codewiki-google.md) | ai-research-tools | referenced by codewiki-google (ai-research-tools) |
| [graphify](../skill-generation-tools/graphify.md) | skill-generation-tools | referenced by graphify (skill-generation-tools) |
