# Architecture Spec: Backlog CLI Deduplication

**Issue**: Fixes #611
**Scope**: Replace duplicated functions/constants in `backlog.py` with imports from `backlog_core/`
**Constraint**: No new dependencies, no behavioral changes (except SKIP_STATUS bug fix), all 12 test files pass

---

## 1. Executive Summary

Replace 12 duplicated functions and 7 duplicated constants in `backlog.py` (2563 lines) with imports from `backlog_core/`. The CLI becomes a thin Typer wrapper: argument parsing, output formatting (Rich), and exit code translation. All business logic delegates to `backlog_core/`.

The key architectural decision is **adapter placement at the CLI command boundary** (ADR-004). Each Typer command that currently works with `dict` items will call `backlog_core` functions that return `BacklogItem`, then convert to display format at the output boundary. No new adapter module is introduced -- conversion is a one-liner (`item.model_dump()`) at each call site.

The SKIP_STATUS bug (CLI missing `"CLOSED"`) is fixed as a natural consequence of importing the canonical constant from `backlog_core/models.py`.

**Design decisions resolved:**

| Question | Decision |
|----------|----------|
| Q1: Adapter placement | CLI boundary -- commands call core directly, convert BacklogItem to dict/display at output |
| Q2: Bug fix bundling | Step 1 is a standalone commit (constants only), SKIP_STATUS fix is verifiable in isolation |
| Q3: Core internal cleanup | Bundled -- core's `parse_item_file` will use `SKIP_STATUS` from models (FIND-14/15 fix) |
| Q4: CLI-only function migration | All 12 have confirmed core equivalents -- replace all with imports |
| Q5: Test adaptation | CLI re-exports `_build_issue_body_from_file` as thin wrapper so existing importlib tests pass |

## 2. Architecture Overview

### Current State (duplication)

```mermaid
graph LR
    subgraph CLI["backlog.py (2563 lines)"]
        CLI_CONST["Constants<br>BACKLOG_DIR, SKIP_STATUS, etc."]
        CLI_FUNCS["12 functions<br>find_item, build_issue_body, etc."]
        CLI_CMDS["Typer commands<br>add, list, sync, close, etc."]
        CLI_FMT["Display formatting<br>Rich tables, panels"]
    end

    subgraph CORE["backlog_core/"]
        CORE_MODELS["models.py<br>Constants + BacklogItem"]
        CORE_PARSE["parsing.py<br>11 canonical functions"]
        CORE_OPS["operations.py<br>CRUD + state transitions"]
        CORE_GH["github.py<br>create_issue_for_item"]
    end

    CLI_CONST -. "DUPLICATES" .-> CORE_MODELS
    CLI_FUNCS -. "DUPLICATES" .-> CORE_PARSE
    CLI_FUNCS -. "DUPLICATES" .-> CORE_GH
    CLI_CMDS --> CLI_FUNCS
    CLI_CMDS --> CLI_CONST
```

### Target State (thin wrapper)

```mermaid
graph LR
    subgraph CLI["backlog.py (~1800 lines)"]
        CLI_CMDS["Typer commands<br>add, list, sync, close, etc."]
        CLI_FMT["Display formatting<br>Rich tables, panels"]
        CLI_COMPAT["Re-exports<br>_build_issue_body_from_file"]
    end

    subgraph CORE["backlog_core/"]
        CORE_MODELS["models.py<br>Constants + BacklogItem"]
        CORE_PARSE["parsing.py<br>All parsing functions"]
        CORE_OPS["operations.py<br>CRUD + state transitions"]
        CORE_GH["github.py<br>GitHub operations"]
    end

    CLI_CMDS --> CORE_MODELS
    CLI_CMDS --> CORE_PARSE
    CLI_CMDS --> CORE_OPS
    CLI_CMDS --> CORE_GH
    CLI_FMT --> CORE_MODELS
    CLI_COMPAT --> CORE_PARSE
```

### Call Flow: CLI Command Execution (After Dedup)

```mermaid
sequenceDiagram
    participant User
    participant CLI as backlog.py (Typer)
    participant Core as backlog_core/parsing
    participant Ops as backlog_core/operations
    participant GH as backlog_core/github

    User->>CLI: backlog list --format text
    CLI->>Core: parse_backlog_from_directory()
    Core-->>CLI: list[BacklogItem]
    CLI->>CLI: Filter by SKIP_STATUS (from models)
    CLI->>CLI: Format as Rich Table
    CLI-->>User: Table output

    User->>CLI: backlog add --title "X"
    CLI->>Core: find_fuzzy_duplicates(title, items)
    Core-->>CLI: list[tuple] (matches)
    CLI->>Core: title_to_slug(title)
    Core-->>CLI: str (slug)
    CLI->>Ops: add_item(...)
    Ops-->>CLI: BacklogItem
    CLI-->>User: "Created: X"
```

## 3. Technology Stack

No new technology. This refactoring operates within the existing stack:

- **CLI**: Typer 0.21+ with Rich console output
- **Models**: Pydantic 2.x (`BacklogItem` in `backlog_core/models.py`)
- **Testing**: pytest 8+ (12 existing test files)
- **Distribution**: PEP 723 standalone script (`backlog.py`)

## 4. Component Design — Module Boundaries and Migration Categorization

<!-- PENDING: Component design with migration table -->

## 5. Data Architecture — Adapter Pattern

<!-- PENDING: Data architecture with adapter interfaces -->

## 6. Security Architecture

No changes. Credential management (GITHUB_TOKEN via environment variable) is unaffected. The refactoring does not alter any security surface.

## 7. Testing Architecture

<!-- PENDING: Testing architecture with coupling fix -->

## 8. Distribution Architecture

No changes. `backlog.py` remains a PEP 723 standalone script with the same shebang and dependency block. The `backlog_core/` package remains an unpackaged sibling directory imported via `sys.path`.

## 9. Architectural Decisions (ADRs)

<!-- PENDING: ADRs -->

## 10. Incremental Rollout Sequence

<!-- PENDING: Rollout sequence with steps -->
