---
name: code-review-architecture
description: Use when a task asks for architecture review, dependency graph visualization, module coupling analysis, or circular dependency detection. Builds a module-dependency graph from import/include/require relationships across Python, TypeScript, JavaScript, Go, Rust, and Java. Emits a Mermaid flowchart with severity color-coding (red = circular dep / critical, yellow = high-coupling / warning, green = clean). When the graph exceeds 40 nodes, applies recursive semantic partitioning to produce linked parent/child diagrams instead of truncating. Registers each diagram as a codebase-analysis artifact.
user-invocable: true
---

# Architecture Audit — Module Dependency Graph

Generates a Mermaid module-dependency graph with severity color-coding from import/include analysis of the project source. Registers the result as a `codebase-analysis` artifact.

## When to Invoke

Invoke when:

- A task explicitly asks for an architecture review, dependency graph, or coupling analysis
- Circular dependencies need to be detected and visualized
- Module-level coupling must be communicated visually to stakeholders
- Running as part of a broader code review that requires structural analysis

Do NOT invoke for:

- Line-level code quality findings — use `dh:code-review-python`, `dh:code-review-typescript`, etc.
- Test quality analysis (out of scope for this skill)

## SOP (Architecture Audit)

<workflow>

### Step 1: Discover Source Modules

**1a. Probe for AST / knowledge-graph tools**

Before falling back to Glob, check whether a richer indexing skill is available in the current session. Try each probe in order and stop at the first success:

| Tool | Probe command | What it provides |
|---|---|---|
| `ccc` (CocoIndex Code) | `ccc search --limit 1 module imports` | Semantic index of modules, paths, and relationships already built from the codebase |
| `graphify` (global CLI, PyPI: `graphifyy`) | `which graphify` | AST knowledge graph via tree-sitter — local extraction, no API calls for code; outputs `graphify-out/graph.json` + `GRAPH_REPORT.md` |

**If `ccc` is available and initialized:**

1. Run a broad semantic search to enumerate the primary source modules:

   ```bash
   ccc search --limit 50 "module definition class function"
   ccc search --limit 50 "import dependency package"
   ```

2. Collect the returned file paths — these form the initial module set. Deduplicate and normalize to relative paths from the project root.
3. For each module file returned, also check its immediate file-level neighbors with a targeted search:

   ```bash
   ccc search --path '<module_dir>/*' --limit 20 "imports dependencies"
   ```

4. Merge all discovered file paths into the candidate module list and proceed to Step 1b for any gaps.

**If `graphify` is available (globally installed via `uv tool install graphifyy` / `pipx install graphifyy`):**

1. Probe availability: `graphify --version`. If the command fails or is not found, skip this branch.

2. Check whether `graphify-out/graph.json` already exists in the project root.
   - If it **does**, use it directly (it may have been committed to the repo for team use). Treat it as fresh unless it is older than 24 hours or the working tree has uncommitted source file changes, in which case run step 3.
   - If it **does not**, continue to step 3.

3. Build the graph (AST extraction is local — no API calls required for code files):

   ```bash
   graphify . --no-viz
   ```

   `--no-viz` skips the HTML output and produces only `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`.

4. Query the graph to enumerate modules and their dependency edges:

   ```bash
   graphify query "list all source code files and their import dependencies"
   graphify query "show circular imports and highly coupled modules"
   ```

   Also read `graphify-out/GRAPH_REPORT.md` — it summarizes **god nodes** (most-connected modules), **surprising connections**, and confidence-tagged relationships (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`).

5. Use the graphify output to directly populate the module list (Step 1b candidate set), the import edges (Step 2), and the coupling/cycle pre-analysis (Steps 3–4). Only fall back to Grep for intra-project import parsing on nodes where graphify reported `AMBIGUOUS` confidence.

**1b. Glob-based fallback (always run if 1a produced < 20 modules or no tool was available)**

Use `Glob` to enumerate source files. Exclude generated code, vendor trees, and build artifacts:

| Language | Include patterns | Exclude |
|---|---|---|
| Python | `**/*.py` | `**/test_*.py`, `**/__pycache__/**`, `**/.venv/**` |
| TypeScript / JS | `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.mjs` | `**/node_modules/**`, `**/dist/**`, `**/.next/**` |
| Go | `**/*.go` | `**/vendor/**` |
| Rust | `**/*.rs` | `**/target/**` |
| Java / Kotlin | `**/*.java`, `**/*.kt` | `**/build/**`, `**/target/**` |

**Merge** Glob results with any paths already discovered in Step 1a, deduplicate, then limit the combined set to at most **200 modules**. If more exist, restrict to the top-level source directories and note the exclusion in the report.

### Step 2: Parse Import Relationships

For each module, use `Grep` to extract import/include/require statements:

| Language | Grep pattern |
|---|---|
| Python | `^(import\|from\s+\S+\s+import)` |
| TypeScript / JS | `^(import\s\|const .* = require\()` |
| Go | `"` inside `import (…)` blocks |
| Rust | `^(use\|mod\s)` |
| Java / Kotlin | `^import\s` |

Map each import to its source module. Only record **intra-project** imports — ignore stdlib and third-party packages. A dependency exists when module A imports module B and B is in the discovered module set.

Normalize identifiers to short PascalCase labels for graph readability (e.g., `src/api/handler.ts` → `ApiHandler`, `auth/users.py` → `AuthUsers`).

### Step 3: Detect Circular Dependencies

Perform DFS cycle detection over the dependency adjacency list:

1. Build `{module → [imported modules]}`.
2. For each unvisited node run DFS, tracking the recursion stack.
3. A back-edge (target is already in the recursion stack) marks a cycle — record every module in it as **critical**.

Also compute in-degree + out-degree for each node:

- Degree ≥ 10 → **high-coupling** (warning) unless also critical.
- All others → **clean**.

### Step 4: Color-Code Nodes

| Class | Condition | Fill | Stroke |
|---|---|---|---|
| Critical | Participates in a circular dependency | `#FF4444` | `#CC0000` |
| Warning | Degree ≥ 10 (not critical) | `#FFD700` | `#B8860B` |
| Clean | No circular dep, degree < 10 | `#44BB44` | `#228822` |

### Step 5: Emit the Mermaid Flowchart(s)

**5a — Check diagram size**

Count the distinct nodes in the complete graph (from Steps 1–4).

- If count ≤ 40 → emit a single standalone diagram (skip to 5d).
- If count > 40 → partition before emitting (proceed through 5b–5c, then apply 5d to each resulting sub-graph).

**5b — Partition: semantic clustering (Pass 1)**

Group nodes into clusters by natural domain or responsibility. A cluster boundary is optimal when nodes within the group share more import/call edges with each other than with nodes outside it. Measure this as the ratio of intra-cluster edges to cross-boundary edges.

Rules:
- Target 2–N clusters such that each cluster contains ≤ 40 nodes.
- If a candidate cluster would contain < 5 nodes, merge it into the sibling cluster it shares the most edges with.
- Name each cluster by its dominant responsibility (e.g., `Auth`, `DataLayer`, `NotificationPipeline`).

The partitioning algorithm is **system-agnostic** — it operates on the abstract directed graph built in Steps 1–4 and does not depend on language or framework.

**5c — Gateway selection and edge-cut validation (Pass 2 + Pass 3)**

For each cluster boundary, identify the **gateway node**: the single node with the highest cross-boundary degree (most connections to nodes outside its own cluster). The gateway node:

- Appears in the **parent diagram** as a condensed **reference node** linking to the child diagram.
- Appears as the **entry node** at the top of the **child diagram**.

If two candidate partitions are equally semantically coherent (Pass 1 score tied), prefer the one that severs fewer cross-boundary edges (minimum edge cut — Pass 3 tiebreaker).

**Recursion:** After producing the initial set of child sub-graphs, check each child's node count. If any child still exceeds 40 nodes, repeat 5b–5c on that child. Recursion terminates when all leaf diagrams contain ≤ 40 nodes, or when further splitting would produce a fragment < 5 nodes (merge that fragment into the sibling cluster it shares the most edges with).

**5d — Emit one diagram per sub-graph**

Produce a `flowchart TD` block for each diagram (the parent and every child). Rules that apply to every diagram:

- Each edge `A --> B` means A imports B.
- Circular back-edges are annotated: `A -->|circular| C`.
- Every node gets a `style` directive with its class fill/stroke colors (from Step 4).
- Node IDs are short camelCase — no spaces or special characters.

**Additional rules for the parent diagram** (only when partitioned):

Replace each partitioned child cluster with a single **reference node** using the gateway node name. Use the cluster's human-readable name (e.g., `Auth`, `DataLayer`) as `{cluster-name}` in the artifact ID:

```mermaid
ClusterName["ClusterName (→ architecture-graph-{slug}-{cluster-name}.md)"]
click ClusterName href "architecture-graph-{slug}-{cluster-name}.md" "Open child diagram"
```

The `click` directive makes the node navigable in Mermaid-supporting renderers (GitHub, Obsidian, etc.). The reference node inherits the shape the gateway node would have in a flat (non-partitioned) diagram.

**Additional rules for each child diagram** (only when partitioned):

Add a backreference node as the very first node, linked to the gateway node with a dashed arrow. Replace `{GatewayNodeId}` with the actual camelCase node ID determined in Step 5c:

```mermaid
ParentRef["↑ Parent: architecture-graph-{slug}.md"]
click ParentRef href "architecture-graph-{slug}.md" "Back to parent"
{GatewayNodeId}["{GatewayNodeLabel} — cluster entry"]
ParentRef -.-> {GatewayNodeId}
```

`{GatewayNodeId}` must match the node ID used for the reference node in the parent diagram.

Example — parent diagram (illustrative):

````markdown
```mermaid
flowchart TD
    %% Parent diagram — Auth cluster replaced by reference node
    AuthCluster["AuthService (→ architecture-graph-myapp-auth.md)"]
    click AuthCluster href "architecture-graph-myapp-auth.md" "Open Auth child diagram"
    OrderService[OrderService] --> AuthCluster
    PaymentGateway[PaymentGateway] --> OrderService
    style AuthCluster fill:#FF4444,stroke:#CC0000,color:#fff
    style OrderService fill:#FFD700,stroke:#B8860B,color:#000
    style PaymentGateway fill:#44BB44,stroke:#228822,color:#fff
```
````

Example — child diagram for the Auth cluster (illustrative):

````markdown
```mermaid
flowchart TD
    %% Child diagram: Auth cluster
    ParentRef["↑ Parent: architecture-graph-myapp.md"]
    click ParentRef href "architecture-graph-myapp.md" "Back to parent"
    AuthService["AuthService — cluster entry"]
    ParentRef -.-> AuthService
    AuthService --> TokenValidator
    AuthService --> UserRepo
    TokenValidator --> JwtParser
    UserRepo -->|circular| AuthService
    style AuthService fill:#FF4444,stroke:#CC0000,color:#fff
    style UserRepo fill:#FF4444,stroke:#CC0000,color:#fff
    style TokenValidator fill:#FFD700,stroke:#B8860B,color:#000
    style JwtParser fill:#44BB44,stroke:#228822,color:#fff
```
````

### Step 6: Assemble and Register the Report

Assemble the markdown report (see Output Format below).

**When the graph was NOT partitioned (single diagram — ≤ 40 nodes):**

Register one artifact:

```text
mcp__plugin_dh_backlog__artifact_register(
  issue_number={issue_number},
  type="codebase-analysis",
  artifact_id="architecture-graph-{slug}",
  content={report_markdown},
  status="complete",
  agent="code-review-architecture"
)
```

**When the graph WAS partitioned (parent + child diagrams):**

Register each diagram as a separate artifact. Register the parent first, then each child in the order they appear in the parent diagram:

```text
%% Parent
mcp__plugin_dh_backlog__artifact_register(
  issue_number={issue_number},
  type="codebase-analysis",
  artifact_id="architecture-graph-{slug}",
  content={parent_report_markdown},
  status="complete",
  agent="code-review-architecture"
)

%% Each child cluster
mcp__plugin_dh_backlog__artifact_register(
  issue_number={issue_number},
  type="codebase-analysis",
  artifact_id="architecture-graph-{slug}-{cluster-name}",
  content={child_report_markdown},
  status="complete",
  agent="code-review-architecture"
)
```

If `issue_number` is not available, output all reports inline (parent first, then children) and note that artifact registration was skipped.

</workflow>

## Output Format

### Single-Diagram Report (≤ 40 nodes — no partitioning)

````markdown
# Architecture Audit — Module Dependency Graph

**Scope:** {language} — {N} modules analyzed

---

## Dependency Graph

```mermaid
flowchart TD
    ...
    style NodeId fill:#FF4444,stroke:#CC0000,color:#fff
```

---

## Findings

### 🔴 Circular Dependencies (Critical)

| Cycle | Modules Involved |
|---|---|
| Cycle 1 | `ModuleA → ModuleB → ModuleA` |

### 🟡 High-Coupling Modules (Warning)

| Module | In-Degree | Out-Degree | Total Degree |
|---|---|---|---|
| `ServiceFacade` | 8 | 5 | 13 |

### 🟢 Clean Modules

{N} modules with no circular dependencies and total degree < 10.

---

## Summary

**Total modules analyzed:** {N}
**Circular dependency participants:** {count} — Critical
**High-coupling modules:** {count} — Warning
**Clean modules:** {count}

{One paragraph describing overall architecture health and the most important findings.}
````

### Partitioned Report — Parent Diagram (> 40 nodes)

The parent report is the entry point. Each over-budget cluster is collapsed to a reference node with a link to its child report.

````markdown
# Architecture Audit — Module Dependency Graph

**Scope:** {language} — {N} modules analyzed ({C} clusters — see child diagrams for detail)

---

## Dependency Graph

> This diagram is partitioned. Nodes marked `(→ ...)` expand into child diagrams.

```mermaid
flowchart TD
    ClusterName["ClusterName (→ architecture-graph-{slug}-{cluster-name}.md)"]
    click ClusterName href "architecture-graph-{slug}-{cluster-name}.md" "Open child diagram"
    ...
```

---

## Child Diagrams

| Cluster | Artifact ID | Nodes | Gateway Node |
|---------|-------------|-------|--------------|
| {ClusterName} | `architecture-graph-{slug}-{cluster-name}` | {N} | `{GatewayNodeId}` |

---

## Findings

{Same Findings sections as single-diagram report — report findings across ALL nodes, not only those visible in the parent diagram.}

---

## Summary

**Total modules analyzed:** {N}
**Diagrams produced:** {1 parent + C children}
**Circular dependency participants:** {count} — Critical
**High-coupling modules:** {count} — Warning
**Clean modules:** {count}

{One paragraph describing overall architecture health, partitioning rationale, and the most important findings.}
````

### Partitioned Report — Child Diagram

One child report is produced per cluster. Each links back to the parent.

````markdown
# Architecture Audit — {ClusterName} Cluster

**Parent diagram:** [architecture-graph-{slug}.md](architecture-graph-{slug}.md)
**Scope:** {N} modules in {ClusterName} cluster

---

## Dependency Graph

```mermaid
flowchart TD
    ParentRef["↑ Parent: architecture-graph-{slug}.md"]
    click ParentRef href "architecture-graph-{slug}.md" "Back to parent"
    GatewayNode["GatewayNode — cluster entry"]
    ParentRef -.-> GatewayNode
    ...
```

---

## Findings

{Findings scoped to this cluster only.}

---

## Summary

{One paragraph describing the health of this cluster and any cross-boundary concerns.}
````

## Color Legend

| Color | Meaning | Recommended Action |
|---|---|---|
| 🔴 Red (`#FF4444`) | Circular dependency — breaks build tooling, causes runtime errors, prevents safe refactoring | Break the cycle by extracting shared types to a common module or applying dependency inversion |
| 🟡 Yellow (`#FFD700`) | High coupling (degree ≥ 10) — high change-propagation risk | Extract a façade or split responsibilities across smaller modules |
| 🟢 Green (`#44BB44`) | Clean — no circular dependency, low coupling | No action required |
