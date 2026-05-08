# CodeGraphContext (CGC)

**Research Date**: 2026-04-08
**Source URL**: <https://github.com/CodeGraphContext/CodeGraphContext>
**GitHub Repository**: <https://github.com/CodeGraphContext/CodeGraphContext>
**Version at Research**: v0.4.0
**License**: MIT License

---

## Overview

CodeGraphContext is a Python-based MCP (Model Context Protocol) server and CLI toolkit that transforms code repositories into queryable graph databases for AI agents and developers. Instead of relying on vector embeddings alone, CGC uses an exact knowledge graph built from Abstract Syntax Tree (AST) parsing to provide deterministic, precise code understanding across 14 programming languages. It bridges the gap between deep code analysis and AI context by storing code entities (classes, functions, modules) and their relationships (calls, imports, inheritance) in a graph database, enabling both natural language queries through AI IDEs and programmatic analysis via CLI commands.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents lack precise code context across large codebases | CGC indexes entire repositories into a queryable graph; natural language queries resolve to exact files, functions, and relationships without hallucination |
| Vector embedding-based code search returns approximate results | Cypher queries against the knowledge graph return deterministic, exact matches for code relationships and dependencies |
| Understanding impact of code changes across many files is manual | CGC traces direct and indirect callers/callees across hundreds of files using graph traversal, automating impact analysis |
| Developers cannot easily visualize code call chains and hierarchies | CGC provides interactive graph visualizations and supports dead code detection, cyclomatic complexity analysis, and dependency tracking |
| AI IDEs lack standardized protocol for deep code understanding | CGC implements the Model Context Protocol (MCP), integrating with Claude, Cursor, Windsurf, VS Code, and other MCP-compatible clients |
| Setting up code analysis for multiple languages is complex | CGC's Tree-sitter integration provides unified parsing across 14 languages; multi-language support is built-in and automatic |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | Not accessible via API | 2026-04-08 |
| License Type | MIT | 2026-04-08 |
| Latest Release | v0.4.0 | 2026-04-08 |
| Python Support | 3.10–3.14 | 2026-04-08 |
| Languages Supported | 14 (Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Dart, Perl) | 2026-04-08 |

**Note**: GitHub star count could not be retrieved due to API connectivity. Developers are advised to check the repository directly for current popularity metrics.

---

## Key Features

### Dual-Mode Operation

- **CLI Toolkit Mode**: Standalone command-line tool (`cgc` command) for indexing, querying, and analyzing code from the terminal
  - Commands: `cgc index`, `cgc analyze`, `cgc find`, `cgc list`, `cgc delete`, `cgc watch`
  - Supports filtering via `.cgcignore` (same syntax as `.gitignore`)
  - Live directory watching with `cgc watch` for incremental updates
- **MCP Server Mode**: Runs as an MCP-compatible server exposed to AI IDEs
  - Supports Claude, Cursor, Windsurf, VS Code, Gemini CLI, ChatGPT Codex, Cline, RooCode, Amazon Q Developer, Kiro
  - Automatic setup wizard (`cgc mcp setup`) for IDE/AI assistant configuration
  - Natural language querying through AI chat interfaces

### Multi-Language Parsing (14 Languages)

Uses **Tree-sitter** for reliable Abstract Syntax Tree extraction across:

- **Strongly Typed**: Java, C/C++, C#, Go, Rust, TypeScript, Kotlin, Swift
- **Dynamic/Scripting**: Python, JavaScript, Ruby, PHP, Perl, Dart

Each language parser extracts functions, classes, methods, parameters, inheritance relationships, function calls, and imports. Parser implementations stored in `src/codegraphcontext/tools/languages/` with corresponding query toolkits in `src/codegraphcontext/tools/query_tool_languages/`.

### Code Analysis and Relationship Querying

- **Caller/Callee Analysis**: Find all functions that call a target function, or all functions called by a target
  - "What functions call `authenticate_user`?"
  - "What does `process_payment` eventually call?"
- **Class Hierarchy Exploration**: Trace inheritance chains and method overrides
  - "Show me the inheritance hierarchy for `BaseController`"
  - "Find all implementations of the `render` method"
- **Dead Code Detection**: Identify unused functions across the codebase (`cgc analyze dead-code`)
- **Cyclomatic Complexity Analysis**: Calculate and rank functions by complexity
  - Specific function: `cgc analyze complexity my_function`
  - Top N complex functions: `cgc analyze complexity --threshold 10`
- **Dependency Tracking**: Map imports and module dependencies

All queries translate internally to Cypher (a standard graph query language) that executes against the underlying database. Example internal translation: "Who calls X?" → `MATCH (caller:Function)-[:CALLS]->(callee:Function {name: 'X'}) RETURN caller` (from `docs/docs/concepts/how_it_works.md`).

### Interactive Graph Visualizations

- Premium web-based explorers with dark mode and glassmorphism design
- Force-directed and hierarchical layout algorithms
- Click-through node inspection with file paths, symbols, and context
- Live search across graph nodes
- Standalone HTML files (zero-dependency) that render in any modern browser
- Invoked via `--viz` flag on analysis commands: `cgc analyze calls my_function --viz`

### Pre-Indexed Bundle Support

- Load famous repository "bundles" (`.cgc` files) without indexing
- Bundle registry available for download via `cgc` commands
- Enables instant analysis of popular open-source projects
- Reference: `docs/BUNDLES.md`, `docs/ON_DEMAND_BUNDLES.md`

### File Watching and Incremental Indexing

- `cgc watch <path>` monitors a directory for file changes
- Automatically re-indexes modified files without blocking the AI
- Background job tracking via `check_job_status` MCP tool
- Managed via `watchdog` library for cross-platform file system events

### Flexible Database Backend

- **KùzuDB** (default): Embedded C++ graph database, zero-config, cross-platform (Windows, macOS, Linux)
- **FalkorDB Lite**: In-process option for Unix/macOS/WSL (Python 3.12+), faster but Unix-only
- **Neo4j**: Enterprise option via Docker or native, supports massive graphs, external server
- Database abstraction layer in `src/codegraphcontext/core/database.py` with backend implementations for KùzuDB, FalkorDB (local and remote), and Neo4j

---

## Technical Architecture

### High-Level Data Flow

**Source Code → Tree-Sitter Parsers → AST Extraction → Graph Construction → Database Storage → Query Interface**

1. **Parsing Layer** (`src/codegraphcontext/tools/languages/`):
   - Tree-Sitter language-specific parsers extract Abstract Syntax Trees
   - Each language parser (e.g., `python.py`, `javascript.py`) walks the AST and emits standardized node types: `Class`, `Function`, `File`, `Module`, `Variable`
   - Relationship edges: `CALLS`, `IMPORTS`, `INHERITS`, `CONTAINS`, `DECLARES`

2. **Graph Construction** (`src/codegraphcontext/tools/graph_builder.py`):
   - Orchestrates full repository indexing and incremental updates
   - Reconciles imports and builds the complete graph in memory before persisting
   - Applies `.cgcignore` file filters to skip ignored paths

3. **Database Abstraction Layer** (`src/codegraphcontext/core/database.py`):
   - Unified interface for multiple graph database backends
   - Implementations: `database_kuzu.py`, `database_falkordb.py`, `database_falkordb_remote.py`
   - All backends support Cypher query language for consistency
   - Stores nodes (code entities) and edges (relationships) with properties (name, file path, line numbers, etc.)

4. **MCP Server** (`src/codegraphcontext/server.py`):
   - Implements Model Context Protocol (MCP) specification
   - Translates JSON-RPC requests from AI clients into standardized graph queries
   - Exposes 20+ MCP tools for indexing, analysis, monitoring, and querying

5. **CLI Interface** (`src/codegraphcontext/cli/main.py`):
   - Typer-based command-line interface
   - Commands mapped to underlying graph builder and query tools
   - Setup wizard (`setup_wizard.py`) for interactive IDE/AI assistant configuration
   - Registry commands (`registry_commands.py`) for bundle management

6. **Watchers and Background Jobs** (`src/codegraphcontext/core/watcher.py`, `src/codegraphcontext/core/jobs.py`):
   - `watchdog` library monitors file system changes
   - Long-running indexing and bundle processing runs asynchronously
   - Job status tracking for CLI and MCP clients

### Component Relationships

```
┌─────────────────────────────────────────────┐
│  AI Client / CLI / Editor                   │
│  (Claude, Cursor, VS Code, terminal)       │
└────────────────────────┬────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
┌────▼──────────┐  ┌────▼──────────┐  ┌────▼──────────┐
│ MCP Server    │  │ CLI Interface │  │ Visualization │
│ (server.py)   │  │ (main.py)     │  │ (visualizer.py)
└────┬──────────┘  └────┬──────────┘  └────┬──────────┘
     │                  │                   │
     └──────────────────┼───────────────────┘
                        │
              ┌─────────▼─────────┐
              │  Core Engine      │
              │  Graph Builder    │
              │  Code Finder      │
              │  Tools            │
              └─────────┬─────────┘
                        │
              ┌─────────▼──────────────┐
              │ Database Abstraction   │
              │ Layer                  │
              └─────────┬──────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐     ┌────▼────┐    ┌────▼────┐
   │  KùzuDB │     │FalkorDB │    │ Neo4j   │
   │(default)│     │(Unix)   │    │(Enterprise)
   └─────────┘     └─────────┘    └─────────┘
```

Source: `docs/docs/architecture.md`

### Cypher Query Translation

All code queries internally translate to Cypher, a standard graph query language:

**Example translations** (from `docs/docs/concepts/how_it_works.md`):

```cypher
-- Query: "Who calls authenticate_user?"
MATCH (caller:Function)-[:CALLS]->(callee:Function {name: 'authenticate_user'})
RETURN caller

-- Query: "What does process_payment eventually call?"
MATCH (start:Function {name: 'process_payment'})-[:CALLS*]->(target:Function)
RETURN target
```

The graph database engine executes these queries natively, returning exact results without approximation.

---

## Installation & Usage

### Installation (Both CLI and MCP Modes)

```bash
pip install codegraphcontext
```

If the `cgc` command is not found after installation, run the PATH fix script:

```bash
curl -sSL https://raw.githubusercontent.com/CodeGraphContext/CodeGraphContext/main/scripts/post_install_fix.sh | bash
source ~/.bashrc  # or ~/.zshrc for zsh
```

**Database Setup**: KùzuDB is the default and requires no additional setup. It installs automatically as a dependency.

For alternative databases:

```bash
# To use FalkorDB Lite (Unix/macOS only, Python 3.12+)
pip install falkordblite

# To use Neo4j, run the setup wizard
cgc neo4j setup
```

### CLI Toolkit Mode

**Index a codebase:**

```bash
cgc index /path/to/my-project
```

**List indexed repositories:**

```bash
cgc list
```

**Analyze code relationships:**

```bash
# Find functions that call a target
cgc analyze callers my_function

# Find functions called by a target
cgc analyze callees my_function

# Explore class hierarchies
cgc analyze tree MyClass

# Find dead/unused code
cgc analyze dead-code

# Calculate cyclomatic complexity
cgc analyze complexity my_function --threshold 10

# Find 5 most complex functions
cgc analyze complexity --limit 5
```

**Visualize relationships:**

```bash
# Generate interactive visualization of call chains
cgc analyze calls my_function --viz

# Visualize class hierarchy
cgc analyze tree MyClass --viz

# Visualize search results
cgc find pattern "Auth" --viz
```

**Watch for live changes:**

```bash
cgc watch /path/to/active-project
```

**See all commands:**

```bash
cgc help
```

**Full reference**: `docs/CLI_COMPLETE_REFERENCE.md`

### MCP Server Mode

**Setup for your AI IDE:**

```bash
cgc mcp setup
```

The wizard automatically detects and configures:
- VS Code
- Cursor
- Windsurf
- Claude
- Gemini CLI
- ChatGPT Codex
- Cline
- RooCode
- Amazon Q Developer
- Kiro

**Start the MCP server:**

```bash
cgc mcp start
```

**Manual configuration** (if not using setup wizard):

Add to your AI IDE's MCP configuration (e.g., `.claude.json` for Claude, `settings.json` for VS Code):

```json
{
  "mcpServers": {
    "CodeGraphContext": {
      "command": "cgc",
      "args": ["mcp", "start"],
      "env": {
        "NEO4J_URI": "YOUR_NEO4J_URI",
        "NEO4J_USERNAME": "YOUR_NEO4J_USERNAME",
        "NEO4J_PASSWORD": "YOUR_NEO4J_PASSWORD"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

**Query via natural language** (from your AI chat):

```text
// Finding code locations
"Where is the process_payment function?"
"Find the User class for me."

// Analyzing relationships
"What other functions call get_user_by_id?"
"If I change calculate_tax, what parts of the code are affected?"
"Show me the inheritance hierarchy for BaseController."
"What methods does the Order class have?"

// Complex call chain tracing
"Show me the full call chain from main to process_data."
"Find all functions that directly or indirectly call validate_input."
"What are all the functions that initialize_system eventually calls?"

// Code quality
"Is there any dead or unused code in this project?"
"Calculate the cyclomatic complexity of process_data in src/utils.py."
"Find the 5 most complex functions in the codebase."
```

---

## MCP Tools Reference

CGC exposes 20+ MCP tools to AI assistants. Key categories:

### Indexing & Management

- `add_code_to_graph(path, is_dependency)` — scan and add code to graph
- `add_package_to_graph(package_name, language, is_dependency)` — add external package
- `list_indexed_repositories()` — list all indexed repositories
- `delete_repository(repo_path)` — remove a repository
- `check_job_status(job_id)` — track indexing progress
- `list_jobs()` — list all background jobs

### Code Search & Analysis

- `find_code(query, fuzzy_search, edit_distance)` — find code snippets by keyword
- `analyze_code_relationships(query_type, target, context)` — find callers, callees, hierarchy, overrides
- `find_dead_code(exclude_decorated_with)` — identify unused functions
- `calculate_cyclomatic_complexity(function_name, path)` — complexity for one function
- `find_most_complex_functions(limit)` — rank functions by complexity
- `get_repository_stats(repo_path)` — count files, functions, classes, modules

### Monitoring & Watching

- `watch_directory(path)` — enable live updates for a directory
- `list_watched_paths()` — list monitored directories
- `unwatch_directory(path)` — stop watching a directory

### Bundle Management

- `load_bundle(bundle_name, clear_existing)` — load a pre-indexed `.cgc` bundle
- `search_registry_bundles(query, unique_only)` — search the bundle registry

### Advanced Querying

- `execute_cypher_query(cypher_query)` — run a direct read-only Cypher query
- `visualize_graph_query(cypher_query)` — generate a visualization URL for query results

**Full reference**: `docs/MCP_TOOLS.md`

---

## File Ignoring (`.cgcignore`)

Create a `.cgcignore` file in your project root using `.gitignore` syntax:

```text
# Ignore build artifacts
/build/
/dist/

# Ignore dependencies
/node_modules/
/vendor/

# Ignore logs
*.log
```

Matching patterns prevent files and directories from being indexed.

---

## Limitations and Caveats

1. **Database Backend Selection**: Default KùzuDB is embedded and zero-config, but FalkorDB Lite is Unix-only (Linux/macOS/WSL). Windows users must use KùzuDB or run Neo4j via Docker. Switching databases requires re-indexing the codebase.

2. **Language Coverage**: While 14 languages are supported, language-specific features (e.g., decorators in Python, interfaces in Java) may not be fully extracted. Tree-Sitter accuracy varies by language grammar maturity.

3. **Large Repository Performance**: Indexing massive repositories (1M+ lines of code) can be memory-intensive and time-consuming. The MCP server does not provide real-time updates during large indexing jobs — the graph is in a transient state until indexing completes.

4. **Cyclic Dependency Detection**: The system tracks direct and indirect call chains but does not explicitly mark or warn about circular dependencies. Developers must interpret cycle detection manually.

5. **Dynamic Code Analysis**: CGC is a static analysis tool. Runtime behavior, dynamic dispatch, reflection-based code loading, and metaprogramming are not captured in the graph. This can lead to incomplete call chains in highly dynamic languages like Python or JavaScript.

6. **Visualization Rendering Complexity**: Interactive visualizations with force-directed graphs become difficult to read for very large codebases (1000+ nodes). Developers may need to filter or segment queries to generate readable visualizations.

7. **API Stability**: Version 0.4.0 is an alpha release (per `pyproject.toml` classifiers). MCP tool APIs and CLI commands may change in future releases without backward compatibility guarantee.

---

## Relevance to Claude Code Development

### Applications

1. **Context Window Optimization for Code Analysis**: CodeGraphContext can be integrated as an MCP server into Claude Code's IDE plugins. When Claude processes code understanding requests, it can query CGC to resolve exact function definitions, callers, and dependencies instead of relying on chunked file reads or vector search. This reduces token consumption and improves accuracy.

2. **Autonomous Code Modification Workflows**: For autonomous coding agents (similar to Copilot's "Edit" features), CGC's impact analysis (`find_callers`, `find_callees`) enables agents to understand the ripple effects of changes before writing code. The agent can confidently modify a function knowing which other functions depend on it.

3. **Multi-File Refactoring Automation**: Tools like `/refactor-code` or `/extract-method` can leverage CGC's relationship queries to automatically identify where refactored code needs to be imported, where old references need updating, and what tests might be affected.

4. **Dead Code and Complexity Auditing**: Periodic audits via `find_dead_code` and `find_most_complex_functions` can feed into backlog items, code review checklists, or quality gates in CI/CD pipelines.

5. **Repository Onboarding Acceleration**: When a developer joins a team or clones a new codebase, CGC's visualizations and relationship queries accelerate comprehension of code structure. An MCP server can be auto-configured during project setup to provide instant code graph access.

### Patterns Worth Adopting

1. **Tree-Sitter for Language-Agnostic Parsing**: Instead of writing language-specific regex or custom parsers, Tree-Sitter provides robust AST extraction for 14+ languages. If Claude Code's agents need to parse or analyze code, Tree-Sitter is a proven, battle-tested approach.

2. **Graph Database for Relationship Queries**: Cypher is more expressive and efficient for traversing code dependencies than sequential file reads or SQL queries. If Claude Code maintains its own code analysis engine, adopting a graph database (even embedded like KùzuDB) would improve agent reasoning about impact and dependencies.

3. **MCP Protocol for Tooling Integration**: CodeGraphContext's dual-mode design (CLI + MCP server) shows how to create tools that work both standalone and integrated. Claude Code plugins and MCP servers should follow this pattern: useful on their own, but also composable with IDEs and agents.

4. **Bundle/Cache Pattern for Offline Analysis**: CGC's pre-indexed bundles allow instant analysis without indexing. A similar pattern could be applied to Claude Code: pre-compute and cache code graphs for popular open-source projects, allowing offline code understanding without network requests.

### Integration Opportunities

1. **Direct MCP Integration**: Register CodeGraphContext as an MCP server in Claude Code, enabling agents to query code relationships via natural language without manual CLI invocation.

2. **Skill Development**: Create a `/codegraphcontext` skill that wraps CGC's CLI and MCP tools, providing agents with a standard interface for code analysis tasks (finding callers, detecting dead code, analyzing complexity).

3. **Context-Aware Code Search**: Enhance Claude Code's existing `@codebase` features with graph-powered relationship discovery. Instead of "search files for `my_function`", users could ask "what calls `my_function`?" and get exact results from the graph.

4. **Autonomous Testing Integration**: Agents performing refactoring or bug fixes could use CGC to identify tests that exercise a modified function, automatically selecting tests to validate changes.

5. **Plugin Marketplace**: Publish a Claude Code plugin that wraps CGC setup and configuration, allowing users to add sophisticated code analysis in one click.

---

## References

- [CodeGraphContext GitHub Repository](https://github.com/CodeGraphContext/CodeGraphContext) (accessed 2026-04-08)
- [CodeGraphContext Architecture Documentation](https://codegraphcontext.github.io/CodeGraphContext/) (accessed 2026-04-08)
- [CodeGraphContext How It Works](./docs/docs/concepts/how_it_works.md) — Tree-Sitter parsing, graph construction, Cypher querying (accessed 2026-04-08)
- [CodeGraphContext System Architecture](./docs/docs/architecture.md) — MCP server, graph builder, database abstraction, data flow (accessed 2026-04-08)
- [MCP Tools Reference](./docs/MCP_TOOLS.md) — Complete list of MCP tools exposed by CGC (accessed 2026-04-08)
- [CLI Complete Reference](./docs/CLI_COMPLETE_REFERENCE.md) — Full CLI command reference (accessed 2026-04-08)
- [Project Metadata](./pyproject.toml) — Version 0.4.0, Python 3.10–3.14 support, dependencies (accessed 2026-04-08)
- [MIT License](./LICENSE) — License text and copyright (accessed 2026-04-08)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Model Context Protocol (MCP)](../mcp-ecosystem/model-context-protocol.md) | mcp-ecosystem | CGC implements MCP for IDE/AI integration; MCP is its primary protocol |
| [Narsil-MCP](./narsil-mcp.md) | mcp-ecosystem | Alternative MCP code intelligence server with 90 tools; both provide Tree-sitter-powered graph-based code analysis for AI agents |
| [GitNexus](./gitnexus.md) | mcp-ecosystem | Graph-based knowledge platform MCP server with 7 code intelligence tools; overlapping architecture for codebase indexing and impact analysis |
| [CocoIndex Code](./cocoindex-code.md) | mcp-ecosystem | Lightweight MCP server providing semantic code search via AST analysis and embeddings; complementary approach to code retrieval |
| [Kythe](../developer-tools/kythe.md) | developer-tools | Google's language-agnostic code intelligence ecosystem using graph-based semantic indexing; foundational approach to cross-language code analysis |
| [GrepAI](../developer-tools/grepai.md) | developer-tools | Go-based MCP server for semantic code search and call graph analysis; shares Tree-sitter parsing and MCP integration patterns |
| [Repomix](../developer-tools/repomix.md) | developer-tools | Codebase packaging tool using Tree-sitter for code extraction; shares language-agnostic parsing approach and generates agent skills |
| [SigMap](../developer-tools/sigmap.md) | developer-tools | referenced by SigMap (developer-tools) |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-08 |
| Version at Verification | v0.4.0 |
| Next Review Recommended | 2026-07-08 |
| Confidence Map | Identity/Metadata: high \| Features: high \| Architecture: high (code-read) \| MCP Tools: high \| Usage Examples: high \| Limitations: high \| Relevance: medium |

**Confidence Qualifiers**:
- **Identity/Metadata**: high — version, license, language support extracted directly from `pyproject.toml` and README
- **Features**: high — documentation-based, verified against multiple source files (`docs/MCP_TOOLS.md`, CLI reference, README)
- **Architecture**: high (code-read) — architectural claims sourced from `docs/docs/architecture.md` and `docs/docs/concepts/how_it_works.md`; component structure verified by reading directory layout and key source files (`server.py`, `graph_builder.py`, `database.py`)
- **MCP Tools**: high — official MCP tools reference document provided
- **Usage Examples**: high — extracted verbatim from official documentation and README
- **Limitations**: high — derived from documentation and observed limitations of static analysis approaches
- **Relevance**: medium — integration points and pattern adoption are informed speculation based on CGC's design; actual integration would require prototyping

