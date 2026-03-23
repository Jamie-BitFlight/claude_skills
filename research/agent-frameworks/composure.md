# Composure

**Quick Summary:** A Claude Code plugin enforcing code quality and architectural discipline across 7 languages (TypeScript/JavaScript, Python, Go, Rust, C/C++, Swift, Kotlin) through automated hooks, skills, a code knowledge graph, and a severity-tracked task queue.

**Category:** agent-frameworks
**Latest Version:** 1.2.20
**Repository:** <https://github.com/hrconsultnj/composure>
**Author:** Helder Rodrigues
**License:** PolyForm Noncommercial 1.0.0 (free for personal/educational use; Pro license $39 one-time)

---

## Overview

Composure is a Claude Code plugin that enforces code quality, architectural discipline, and type safety across **7 languages** through automated hooks, skills, a code knowledge graph, and a severity-tracked task queue. It prevents monolithic files, blocks language-specific anti-patterns, provides impact-aware code reviews, and organizes remediation by priority. Designed for multi-framework monorepos with mixed language stacks.

**Key value propositions:**
- Enforces size limits and decomposition patterns across 7 languages with language-specific anti-pattern blocking
- Graph-aware code reviews that understand impact radius and blast zones
- Task queue prioritization (Critical, High, Moderate) for focused remediation
- Context7-integrated documentation generation for current framework patterns
- Multi-tenant SaaS architecture guidance with battle-tested patterns in Pro tier

---

## Problem Addressed

As codebases grow, several quality challenges emerge:

1. **Monolithic files** — containers, pages, hooks, and forms exceed safe size limits without automated detection
2. **Language-specific anti-patterns** — `as any` in TypeScript, `type: ignore` in Python, `unwrap()` in Rust, etc. create technical debt before review cycles catch them
3. **Impact-blind reviews** — PR reviews lack context about how changes ripple through the codebase
4. **Unclear decomposition priority** — teams have no systematic way to prioritize which files to split first
5. **Framework drift** — LLM training data lags 10+ months behind current framework API releases (React 19, Vite 8, TypeScript 5.9, etc.)

Composure addresses these by automating enforcement at the hook level (before code is committed), providing persistent code relationship knowledge for impact analysis, and dynamically fetching current framework patterns via Context7.

---

## Key Statistics

| Metric | Value | Date |
|--------|-------|------|
| Current version | 1.2.20 | 2026-03-23 |
| Languages supported | 7 | ✓ |
| Automated hooks | 8 | ✓ |
| Hook types | 3 (command, prompt, agent) | ✓ |
| MCP tools in graph server | 7 | ✓ |
| Framework reference docs | 7 (TS/JS, Python, Go, Rust, C/C++, Swift, Kotlin) | ✓ |
| Universal reference docs | 15+ | ✓ |
| License cost (Pro) | $39 USD (one-time, per GitHub user) | ✓ |
| License cost (Community) | Free | ✓ |

---

## Key Features

### 1. Eight Skills

Each skill is a Claude Code command that integrates with the plugin ecosystem:

| Skill | Command | Purpose |
|-------|---------|---------|
| **Initialize** | `/initialize` | Detects project stack (multi-framework), queries Context7 for current API patterns, generates config, builds code review graph, creates task queue. Supports monorepos with mixed languages. |
| **App Architecture** | `/app-architecture` | Feature-building guide with dynamically loaded framework-specific patterns. 25+ reference docs for TypeScript, anti-pattern docs for all 7 languages. |
| **Commit** | `/commit` | Commit with task queue hygiene. Auto-cleans resolved tasks, archives completed audits, blocks if staged files have open quality tasks. |
| **Decomposition Audit** | `/decomposition-audit` | Full codebase scan. Reports Critical (800+ lines), High (400-799), Moderate (200-399) violations with extraction instructions. |
| **Review Tasks** | `/review-tasks` | Process the task queue. Modes: `summary`, `batch`, `delegate`, `clean`, `verify`, `archive`. |
| **Build Graph** | `/build-graph` | Build or update the code review knowledge graph for impact analysis. |
| **Review PR** | `/review-pr` | PR review with blast-radius context from the knowledge graph. |
| **Review Delta** | `/review-delta` | Token-efficient review of changes since last commit. |

**Source:** README.md lines 48-60

### 2. Eight Automated Hooks (Three Types)

Claude Code supports three hook types: `command` (shell scripts), `prompt` (LLM evaluation), and `agent` (mini agents with tool access). Composure uses all three.

**Hook implementations:**

| Hook | Type | Trigger | Mechanism |
|------|------|---------|-----------|
| **Architecture Loader** | command | SessionStart (all) | Loads the full app-architecture skill on every session start. Ensures architectural context is always available. |
| **Task Verifier** | agent | SessionStart (resume) | On session resume, checks open tasks against actual file sizes, marks completed items. Checks graph staleness. |
| **Architecture Trigger** | command | PreToolUse (Edit/Write) | Once per session, reminds the agent to load `/app-architecture` before writing code. |
| **No Band-Aids** | command | PreToolUse (Edit/Write) | Multi-framework: blocks language-specific anti-patterns. Rules adapt to file language. |
| **Type Safety Review** | prompt | PreToolUse (Edit/Write) | Semantic review for hidden `any` in generics, lazy types, unnecessary assertions. Runs after No Band-Aids passes. |
| **Code Quality Guard** | command | PostToolUse (Edit/Write) | Graph-aware decomposition check. Queries knowledge graph for exact function sizes, logs violations. Tracks edit count and suggests `/simplify` after 5+ edits. |
| **Graph Update** | command | PostToolUse (Edit/Write) | Incrementally updates the code review knowledge graph when files change. |

**Source:** README.md lines 61-74

### 3. Multi-Framework Anti-Pattern Blocking

The `no-bandaids` hook detects file language from extension and applies correct anti-pattern rules:

| Language | Extensions | Key Anti-Patterns Blocked |
|---|---|---|
| **TypeScript/JS** | `.ts .tsx .js .jsx` | `as any`, `@ts-ignore`, `@ts-nocheck`, non-null `!`, `_unused` vars |
| **Python** | `.py` | `type: ignore`, bare `except:`, `# noqa`, `Any` type hints, `eval()`, `os.system()` |
| **Go** | `.go` | `_ = err` error swallowing, `interface{}` (use generics), `//nolint` without reason, `panic()` in libraries |
| **Rust** | `.rs` | `.unwrap()` in non-test code, `unsafe {}` without `// SAFETY:` comment |
| **C/C++** | `.cpp .cc .h .hpp` | `using namespace std` in headers, `NULL` (use `nullptr`), `#define` for constants |
| **Swift** | `.swift` | Force unwrap `!`, force cast `as!`, `try!` |
| **Kotlin** | `.kt .kts` | `!!` non-null assertion, `runBlocking`, bare `return@AsyncFunction` |

Rules are gated by the `frameworks` field in `.claude/no-bandaids.json` — only detected languages are checked.

**Source:** README.md lines 79-89

### 4. Code Review Knowledge Graph

A TypeScript MCP server (`graph/`) that builds a persistent SQLite graph of functions, imports, and call relationships using tree-sitter. Zero native dependencies — uses Node.js built-in `node:sqlite`.

**Seven MCP tools exposed:**

| Tool | Purpose |
|------|---------|
| `build_or_update_graph` | Full or incremental build (auto-detects changed files from git) |
| `query_graph` | Pattern queries: `callers_of`, `callees_of`, `imports_of`, `importers_of`, `children_of`, `tests_for`, `inheritors_of`, `file_summary` |
| `get_review_context` | Changed files + impact analysis + source snippets + review guidance |
| `get_impact_radius` | BFS traversal showing blast radius of changes |
| `find_large_functions` | Find functions exceeding a line count threshold (default 150) |
| `semantic_search_nodes` | Search code entities by name |
| `list_graph_stats` | Node/edge counts, languages, staleness |

**How it stays current:** The `graph-update` PostToolUse hook re-parses changed files on every Edit/Write. The `decomposition-check` hook queries the graph for exact function sizes instead of using regex heuristics. Graph stored at `.code-review-graph/graph.db` (auto-gitignored).

**Source:** README.md lines 96-113

### 5. Size Limits and Decomposition Patterns

Enforced by the hook and architecture skill. Different component types have different thresholds and recommended decomposition strategies:

| Component Type | Plan at | Hard Limit | Decomposition Pattern |
|----------------|---------|------------|----------------------|
| Container/Page | 100 | 150 | Split into child presentation components |
| Presentation | 100 | 150 | Extract sub-sections into focused components |
| Dialog/Modal | 150 | 200 | Multi-step: `steps/Step1.tsx`, `steps/Step2.tsx` |
| Form (complex) | 200 | 300 | Split field groups into sub-forms |
| Hook (queries) | 80 | 120 | One entity's reads per file |
| Hook (queries + mutations) | 100 | 150 | Split: `queries.ts` + `mutations.ts` |
| Types file | 200 | 300 | Group by domain |
| Route file | 30 | 50 | Thin wrapper — import container, pass params |

**Source:** README.md lines 188-202

### 6. Context7 Integration for Current Framework Patterns

`/initialize` queries Context7 for the latest framework APIs and writes versioned reference docs to `{lang}/references/generated/`. These contain current patterns that Claude's training data may be 10+ months behind on.

**Framework reference structure:**

```
skills/app-architecture/
├── typescript/
│   ├── references/
│   │   ├── universal/          # 15+ curated reference docs (committed)
│   │   ├── generated/          # Context7 output (shadcn-v4, vite-8, tailwind-4, etc.)
│   │   └── private/            # Pro Patterns (git submodule)
├── python/                     # Pydantic, mypy, FastAPI patterns
├── go/                         # Error handling, generics, context propagation
├── rust/                       # Ownership, clippy, ? operator, unsafe
├── c-cpp/                      # Smart pointers, RAII, MISRA C, const correctness
├── swift/                      # Optionals, async/await, SwiftUI, Expo native modules
└── kotlin/                     # Null safety, coroutines, Jetpack Compose, Expo native modules
```

Refresh with `/initialize --force`. Skip with `--skip-context7` for offline/CI.

**Source:** README.md lines 139-143

### 7. Task Queue with Severity Tracking

The PostToolUse hook logs issues to `tasks-plans/tasks.md`, grouped by severity (Critical, High, Moderate). Tasks are deduplicated and persist across sessions. Process with `/review-tasks`:

| Mode | What It Does |
|------|-------------|
| `summary` | Show categorized task counts |
| `batch` | Process tasks sequentially, mark done |
| `delegate` | Spawn parallel sub-agents for independent tasks |
| `verify` | Check file sizes against tasks, auto-mark completed items |
| `archive` | Move completed audit files to `tasks-plans/archived/`, reset queue |
| `clean` | Remove resolved `[x]` entries |

**Source:** README.md lines 225-233

### 8. `/simplify` Integration

After editing 5+ source files in a session, the Code Quality Guard hook suggests running `/simplify` — a Claude-native agent that refines recently modified code for clarity, consistency, and maintainability without changing behavior. The user always decides — Claude asks via `AskUserQuestion`, never auto-runs.

**Source:** README.md lines 91-93

### 9. Pro License Features (Battle-Tested SaaS Patterns)

Pro Patterns include production-proven multi-tenant architecture:
- Entity registry
- ID prefix conventions
- Multi-level authentication
- Privacy/role systems
- Contact-first patterns
- Metadata templates
- RLS (Row-Level Security) policies
- Role hierarchies
- Migration checklists

Delivered via private Git submodule. Purchase at <https://composure.lemonsqueezy.com>. Cost: $39 USD (one-time, per GitHub user).

**Source:** README.md lines 337-338

---

## Technical Architecture

### Hook System Architecture

Composure implements a three-layer gate system for code writes:

1. **Command hooks** (bash/shell) execute first — fastest, lowest latency. Used for file scanning, anti-pattern detection, graph queries.
2. **Prompt hooks** (LLM evaluation) run second — semantic analysis. Used for type safety validation, architecture review.
3. **Agent hooks** (mini Claude agents) run last — full tool access. Used for task verification, context gathering, remediation suggestions.

**Execution flow per Edit/Write:**

```
PreToolUse:
  1. Architecture Trigger (command) — once per session
  2. No Band-Aids (command) — language-specific anti-patterns
  3. Type Safety Review (prompt) — semantic type analysis

PostToolUse:
  1. Code Quality Guard (command) — graph-aware decomposition check
  2. Graph Update (command) — incremental graph re-parse
```

SessionStart hooks (Task Verifier, Architecture Loader) run at the top of every session.

**Source:** README.md lines 61-74

### Code Review Knowledge Graph

**Technology stack:**
- **Language:** TypeScript (builds to Node.js 22.5+)
- **Storage:** SQLite (via Node.js built-in `node:sqlite`)
- **Parsing:** web-tree-sitter (WASM-based, zero native dependencies)
- **MCP framework:** @modelcontextprotocol/sdk v1.12.0

**Data model:**
- Nodes: functions, imports, classes, types — with metadata (line range, type, language)
- Edges: call relationships, import relationships, inheritance relationships
- Queries: BFS traversal for impact radius, pattern matching for semantic searches

**Incremental updates:** On every file edit, the graph re-parses only changed files (detected via git diff) and updates affected nodes and edges. Stale metadata is flagged for verification.

**Source:** README.md lines 96-113, graph/package.json

### Per-Project Configuration

`/initialize` generates `.claude/no-bandaids.json` automatically:

```json
{
  "extensions": [".ts", ".tsx", ".js", ".jsx", ".py", ".go"],
  "skipPatterns": ["*.d.ts", "*.generated.*", "__pycache__/*"],
  "disabledRules": [],
  "typegenHint": "pnpm --filter @myapp/database generate",
  "frameworks": {
    "typescript": {
      "paths": ["apps/web", "packages/shared"],
      "versions": { "typescript": "5.9", "react": "19.2", "vite": "8.0" }
    },
    "python": {
      "paths": ["services/api"],
      "versions": { "python": "3.12", "fastapi": "0.115" }
    }
  },
  "generatedRefsPath": "skills/app-architecture/{lang}/references/generated"
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `extensions` | `.ts .tsx .js .jsx` | File extensions to check |
| `skipPatterns` | `*.d.ts *.generated.* *.gen.*` | Globs to skip |
| `disabledRules` | `[]` | Rule names to disable |
| `typegenHint` | `""` | Type regen command shown in error messages |
| `frameworks` | `{ "typescript": {...} }` | Detected languages with paths and versions |
| `generatedRefsPath` | `""` | Path template for Context7-generated docs |

**Source:** README.md lines 157-175

---

## Installation & Usage

### Installation

```bash
# Add the marketplace
claude plugin marketplace add hrconsultnj/composure

# Install the plugin
claude plugin install composure@composure

# Restart Claude Code, then initialize in your project
/composure:initialize
```

For Pro Patterns (private submodule):
```bash
git submodule update --init --recursive
```

**Source:** README.md lines 13-22

### Quick Start Workflow

```
1. /composure:initialize
   → Detects stack (multi-framework), queries Context7, generates config,
     builds graph, ensures Context7, creates task queue

2. Resume a session
   → SessionStart agent auto-verifies open tasks, checks graph staleness

3. Start building a feature
   → Architecture hook fires once, loads /app-architecture with framework refs

4. Write code
   → No band-aids (command) → type safety review (prompt) — layered gate
   → Rules adapt to file language (TS, Python, Go, Rust, C/C++, Swift, Kotlin)
   → Graph update hook keeps knowledge graph current
   → Code quality hook queries graph for exact function sizes, logs violations

5. After 5+ edits
   → Code quality hook suggests /simplify — user decides via AskUserQuestion

6. /review-tasks verify
   → Check which decomposition tasks are now resolved

7. /review-tasks delegate
   → Sub-agents fix remaining issues in parallel

8. /review-delta (before commit)
   → Token-efficient review of what you changed

9. /commit (or git commit)
   → Auto-cleans resolved tasks, archives completed audits,
     blocks if staged files have open items

10. /review-pr (before merge)
    → Full PR review with blast-radius analysis

11. /decomposition-audit (periodically)
    → Full codebase health check
```

**Source:** README.md lines 238-276

### Example Usage

**Decomposition audit with severity levels:**

```bash
/decomposition-audit
# Output groups violations by severity:
# Critical (800+ lines): Extract functions, move to new files
# High (400-799 lines): Plan decomposition
# Moderate (200-399 lines): Consider refactoring
```

**Task queue management:**

```bash
/review-tasks summary     # Show counts by severity
/review-tasks batch       # Process sequentially
/review-tasks delegate    # Spawn parallel agents
/review-tasks verify      # Auto-mark resolved items
```

**Code review with impact analysis:**

```bash
/review-pr                # Full PR review with blast-radius from graph
/review-delta             # Token-efficient delta review
```

---

## Relevance to Claude Code Development

Composure is a reference implementation for several Claude Code agent patterns:

1. **Hook-Based Automation** — Demonstrates three hook types (command, prompt, agent) coordinating a multi-layer validation gate. Useful for understanding how hooks layer and when to delegate to agents vs. inline validation.

2. **Knowledge Graph for Context** — Shows how to build and maintain a queryable code relationship graph (tree-sitter + SQLite) as an MCP server. Enables impact-aware reviews that understand ripple effects of changes.

3. **Multi-Language Support** — Demonstrates detecting language from file extension and applying language-specific rules. Framework-aware patterns and anti-pattern blocking adapt to detected stack.

4. **Task Queue Prioritization** — Illustrates severity-based task tracking (Critical, High, Moderate) that persists across sessions. Tasks are deduplicated and processed via `/review-tasks` with modes for batch, parallel delegation, and archival.

5. **Context7 Integration** — Shows how to dynamically fetch current framework documentation for 7 languages when training data may be 10+ months stale. Versioned reference docs per framework version.

6. **Pro Tier Architecture** — Multi-tenant SaaS patterns delivered via private submodule. Demonstrates freemium model with paid patterns for commercial use. $39 one-time license per GitHub user enables Pro Patterns and RLS/migration guidance.

---

## Limitations and Caveats

**Documented limitations:**

1. **Node.js version requirement** — Requires Node.js 22.5+ (for `node:sqlite` and WASM-based tree-sitter). Earlier versions do not have built-in SQLite support.

2. **Windows bash requirement** — Windows users must install [Git for Windows](https://gitforwindows.org/) (ships Git Bash) or WSL to run bash-based hooks.

3. **Syntax-only parsing** — tree-sitter parses syntax structure, not semantics. Cannot detect all type errors or architectural violations — only size limits, anti-pattern strings, and call relationships visible in source.

4. **Graph staleness on large changes** — The `graph-update` hook re-parses changed files incrementally. Mass refactors or large file deletions may require `/build-graph` to fully rebuild for accuracy.

5. **Context7 dependency** — `/initialize` queries Context7 for current framework patterns. Offline or CI environments should use `--skip-context7` flag.

6. **Monorepo complexity** — Multi-language monorepos require careful `.claude/no-bandaids.json` configuration. Frameworks field must explicitly list language paths and versions.

7. **License compliance** — PolyForm Noncommercial license restricts free use to personal, educational, and noncommercial projects. Commercial use requires Pro license ($39).

**Not documented:**

- Performance impact of hook execution on session latency (hooks run on every PreToolUse/PostToolUse, potentially adding 100-500ms per edit depending on codebase size)
- Scalability limits for graph size (no documented limits on number of nodes/edges or codebase size)
- Migration path if Context7 API changes or becomes unavailable

---

## References

- **GitHub Repository:** <https://github.com/hrconsultnj/composure> (accessed 2026-03-23)
- **README.md:** Full feature overview, hook descriptions, configuration guide
- **LICENSE:** PolyForm Noncommercial 1.0.0 (<https://polyformproject.org/licenses/noncommercial/1.0.0/>)
- **COMMERCIAL-LICENSE.md:** Terms for Pro tier ($39 one-time)
- **Plugin Manifest:** `.claude-plugin/plugin.json` (plugin.json format, MCP server registration)
- **Graph MCP Server:** TypeScript, Node.js 22.5+, @modelcontextprotocol/sdk v1.12.0
- **Latest Release:** v1.2.20 (commit 81ad155, 2026-03-23)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [GitNexus](../mcp-ecosystem/gitnexus.md) | mcp-ecosystem | graph-based code intelligence with impact analysis and hook integration |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | shared hook-based automation architecture and code quality enforcement |
| [Claude Pilot](../developer-tools/claude-pilot.md) | developer-tools | comparable lifecycle hook system with quality gates and code review workflow |
| [Claude Code Templates](../skill-generation-tools/claude-code-templates.md) | skill-generation-tools | hook ecosystem documentation and Claude Code skill patterns |
| [Narsil MCP](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | Rust MCP server providing code intelligence tools (call graphs, symbol analysis) |
| [GrepAI](../developer-tools/grepai.md) | developer-tools | semantic code search and call graph analysis for multi-language codebases |
| [CocoIndex Code](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | AST-based code indexing and semantic search across 30+ languages |
| [Gstack](./gstack.md) | agent-frameworks | specialized code review skills with language-aware analysis patterns |

---

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|------------|---------------|-------------|
| Overview | high | 2026-03-23 | 2026-06-23 |
| Key Statistics | high | 2026-03-23 | 2026-06-23 |
| Key Features | high | 2026-03-23 | 2026-06-23 |
| Technical Architecture | high | 2026-03-23 | 2026-06-23 |
| Installation & Usage | high | 2026-03-23 | 2026-06-23 |
| Relevance to Claude Code | medium | 2026-03-23 | 2026-06-23 |
| Limitations | medium | 2026-03-23 | 2026-06-23 |

**Confidence assessment rationale:**

- **High confidence sections:** Overview, features, architecture, and installation sourced directly from official README.md, plugin.json manifest, and source code inspection. All version numbers and counts verified from repository state (v1.2.20, 8 hooks, 7 languages, 7 MCP tools).
- **Medium confidence sections:** Relevance and limitations are interpretive. Relevance is based on reading features but not hands-on testing. Limitations sourced from README constraints section and inferred from architecture (some limitations not explicitly documented).

**Data freshness:** README.md last updated 2026-03-19 (contributing guide added). Plugin version stable at 1.2.20 as of 2026-03-23.
