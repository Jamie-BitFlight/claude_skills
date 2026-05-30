# Development Harness Backend Providers

Reference for implementers planning backend integrations across the full development harness. Covers coordination state (issues, tasks) and durable handoff content (documents) for GitHub (current), Linear, GitLab, and Supabase.

For artifact-specific Protocol details, see [artifact-manifest-backends.md](./artifact-manifest-backends.md).
For detailed platform research with citations, see [research/task-management/artifact-manifest-backend-providers.md](../../../research/task-management/artifact-manifest-backend-providers.md).
For the architect spec, see `~/.dh/projects/{slug}/plan/architect-artifact-manifest.md` (state artifact, access via `artifact_read(artifact_type="architect")`).
For the feature context and desired outcomes, see `~/.dh/projects/{slug}/plan/feature-context-artifact-manifest.md` (state artifact, access via `artifact_read(artifact_type="feature-context")`).

## SAM Storage Model

SAM (Stateless Agent Methodology) treats agents as stateless computation engines. Each agent receives complete context, produces verified artifacts, and terminates. All continuity lives in durable storage, not conversation history.

For the complete process that produces and consumes these primitives, see [Backlog Item End-to-End Lifecycle](./backlog-item-lifecycle.md). That document maps each lifecycle phase to the artifacts it produces and the state transitions it enacts.

This creates two distinct storage workloads:

- **Coordination state** — scheduling, claiming, gating, tracking execution. Properties needed: atomic claim/update, status transitions, dependency graphs, assignee metadata, ready-queue queries.
- **Durable handoff content** — the actual artifacts agents produce and consume to resume work across sessions. Properties needed: stable addressability, efficient full-content read, version/update semantics, large markdown support, linking to work items.

These workloads must not be forced into a single primitive. Three primitives serve them:

| Primitive | Workload | Purpose | Has own state? |
|---|---|---|---|
| **Work Item** | Coordination | Initiative, plan, or feature — the top-level container that owns goal, ACs, and lifecycle | Yes |
| **Sub-item** | Coordination | Individually dispatchable, claimable task with dependency relationships and agent assignment | Yes |
| **Document** | Handoff | Versioned stage or task artifact — the content agents hand off between stages | No |

**Design rule**: if an object exists so another agent can resume work from its content, it is a Document. If an object exists so the system can schedule, claim, gate, or track execution, it is a Work Item or Sub-item.

**How SAM maps to the three primitives:**

The current plan YAML is a compound container that bundles coordination state (task status, dependencies, claim metadata) with artifact references (feature context, architect spec). In the target model, that bundle normalizes:

- Plan metadata (goal, ACs, lifecycle) → **Work Item**
- Task rows (status, dependencies, agent assignment, claim) → **Sub-items**
- Stage/task outputs (discovery, design, context, reports, validation) → **Documents**

**Document schema:**

```text
document.id           — backend-assigned identifier
document.owner_type   — work_item | sub_item
document.owner_id     — references parent issue or task sub-issue
document.stage        — S1 | S2 | S3 | S4 | S5 | S6 | S7
document.type         — discovery | design | context | planning | execution | validation | report | etc
document.title        — human-readable name
document.content      — the actual artifact body
document.format       — md | yaml | json | rst
document.version      — revision number (native in Gist/Snippet revision history)
document.backend_ref  — backend-native URL for direct access
```

Every Document must be queryable by owning work item, optionally owning sub-item, artifact type, stage, and version — preserving the logical locality that the filesystem gave for free.

**SAM MCP tool mapping to primitives:**

```text
sam_create  → IssueBackend (create work item) + TaskBackend (bootstrap sub-items)
sam_read    → IssueBackend + TaskBackend + DocumentBackend (aggregation)
sam_claim   → TaskBackend (atomic claim on sub-item)
sam_state   → TaskBackend (status mutation on sub-item)
sam_ready   → TaskBackend (dependency/status query across sub-items)
sam_update  → DocumentBackend (append/update document against work item or sub-item)
sam_list    → IssueBackend (list work items)
```

The lifecycle phases that invoke each tool are documented in [Backlog Item End-to-End Lifecycle](./backlog-item-lifecycle.md) — Phase 1 uses `backlog_add` (IssueBackend), Phases 3-4 use `sam_create`/`artifact_register` (TaskBackend + DocumentBackend), Phase 5 uses `sam_claim`/`sam_state` (TaskBackend), and Phase 7 uses `backlog_close`/`backlog_resolve` (IssueBackend).

**Source**: [Stateless Software Engineering Framework §2.1.3](../../../stateless-agent-methodology/stateless-software-engineering-framework.md) — "This framework is intentionally storage-agnostic. Any concrete filename or path should be treated as an example implementation, not the canonical representation."

## Current Architecture

The development harness uses three subsystems. The backlog MCP now uses a pluggable `BacklogBackend` Protocol; plans/tasks and artifact manifest remain as described below.

### Issues/Backlog (backlog MCP)

- **Source of truth**: Determined by the active backend (default: GitHub Issues)
- **Local cache**: `~/.dh/projects/{slug}/backlog/` per-item markdown files (resolved via `dh_paths.backlog_dir()`)
- **Implementation**: `backlog_core/` package with pluggable `BacklogBackend` Protocol, exposed as FastMCP 3.x server (`mcp__plugin_dh_backlog__*`)
- **Operations**: CRUD on issues, label management, grooming, syncing, milestone/project management
- **Backend selection**: `BACKLOG_BACKEND` env var → `backlog.backend` in `.dh/config.yaml` → `.beads/dh-backend` marker file auto-detect → default `github`
- **GitHub backend**: GitHub Issues canonical; local files are derived cache updated by `backlog_sync` and `backlog_pull`. Bulk sync via `sync_issues_graphql` in `backlog_core/gh_client.py` — GraphQL cursor-paginated fetch with optional `since` filter. Full sync ~12s for 245 issues; incremental sync ~0.7s. `create_milestone` and `create_label` remain REST-only (no GraphQL mutations — ADR-004).

### Plans/Tasks (SAM MCP)

- **Source of truth**: Determined by the active backend (default: local YAML in `~/.dh/projects/{slug}/plan/`, resolved via `dh_paths.plan_dir()`)
- **GitHub link**: Each task YAML can contain a `github_issue` field linking to a GitHub sub-issue for status sync
- **Implementation**: `sam_schema/` package with pluggable `TaskBackend` Protocol, exposed as FastMCP 3.x server (`mcp__plugin_dh_sam__*`)
- **Operations**: List plans, read/claim/update tasks, check readiness, create plans
- **Format**: YAML frontmatter per task file (legacy: monolithic markdown with `## Task {ID}` headers)
- **Backend selection**: `TASKBACKEND` env var → `taskbackend.toml` (git project root, then `~/.dh/`) → default `local`

### Artifact Manifest (backlog MCP artifact tools)

- **Source of truth**: Determined by the active artifact backend (default: GitHub Gist linked from issue body)
- **Implementation**: `backlog_core/artifact_provider.py` defines the `ArtifactBackend` Protocol, `GitHubGistArtifactProvider` (default), `LinearArtifactProvider`, `GitLabArtifactProvider`, and `LocalFilesystemArtifactProvider` (automatic fallback)
- **Operations**: `get_manifest`, `set_manifest`, `read_artifact_content`
- **File content**: Always served from local filesystem regardless of manifest backend
- **Backend selection**: `BACKLOG_BACKEND` env var → default `github`; set `BACKLOG_BACKEND=local` or `backlog:\n  backend: local` in `.dh/config.yaml` to always use local storage
- **Fallback**: When the configured remote backend raises `GitHubUnavailableError` or `BacklogError` during initialisation, `_get_artifact_provider()` in `server.py` silently activates `LocalFilesystemArtifactProvider`; callers receive the same response shape with a `warnings` entry: `"Artifacts stored in local filesystem provider. Remote sync unavailable."`
- **Factory**: `create_artifact_provider(backend_name=None, repo=None, root_worktree=None)` in `backlog_core/artifact_provider.py`

## BacklogBackend Protocol

The `BacklogBackend` Protocol (defined in `backlog_core/backend_protocol.py`) decouples all backlog MCP operations from any specific storage platform. `BacklogConfig` wraps the active backend instance; `operations.py` and `server.py` receive it via dependency injection. Rendering utilities (`section_heading`, `render_groomed_section`, `section_display_title`) are accessed through the protocol rather than imported directly from `github_sync`.

All protocol methods are synchronous. The MCP layer wraps calls in `asyncio.to_thread()` when needed.

### Method Groups

- **Repository access**: `get_github`, `try_get_github`, `probe_backend_status`
- **GraphQL utilities**: `_graphql_request`, `_resolve_labels_graphql`
- **Issue CRUD**: `_fetch_issue_graphql`, `_fetch_issues_graphql`, `_update_issue_graphql`, `sync_issues_graphql`, `create_issue_for_item`, `close_github_issue`, `resolve_github_issue`, `fetch_open_issues_by_title`, `fetch_github_issue_body`, `check_open_prs_for_issue`, `batch_fetch_statuses`, `fetch_item_status`, `view_enrich_from_github`, `issue_to_local_fields`
- **Issue comments**: `_add_comment_graphql`, `_fetch_issue_comments_graphql`, `_fetch_comment_by_id_graphql`, `_update_issue_comment_graphql`
- **Status mutations**: `apply_status_in_progress`, `apply_status_verified`, `apply_status_groomed`, `sync_groomed_to_github_issue`
- **Milestones / projects**: `_fetch_milestones_graphql`, `_projects_v2_list_query`, `_projects_v2_create_mutation`
- **Task issues**: `create_task_issue`, `get_task_issues`, `update_task_status`
- **Sync / serialisation**: `render_issue_body`, `parse_issue_body`, `merge_item`, `unknown_key_to_heading`, `section_heading` (property), `render_groomed_section`, `section_display_title`
- **Integration branches**: `create_integration_branch`, `get_integration_branch_status`, `merge_integration_branch`, `delete_integration_branch`, `list_integration_branches`

### Available Backends

| Backend | Identifier | Purpose |
|---------|-----------|---------|
| `GitHubBackend` | `github` | Default. Delegates to `gh_client.py`, `github_sync.py`, `github_branches.py`. Requires `GITHUB_TOKEN`. |
| `SQLiteBackend` | `sqlite` | Local 6-table schema via stdlib `sqlite3`, WAL mode. No external credentials required. |
| `InMemoryBackend` | `memory` | In-memory test double. No persistence. Use in tests and CI where GitHub is unavailable. |
| `BeadsBackend` | `beads` | Routes to `bd` CLI via lazy subprocess wrapper (`backlog_core/backends/bd_runner.py`). Auto-detected when `.beads/dh-backend` marker file exists at project root (explicit opt-in required). `bd` binary is NOT probed at server startup — validated on first `run_json()` call. Failure raises `BdNotInstalledError`; no silent fallback to `github`. |

### Capability Properties

Two class-level properties on the `BacklogBackend` Protocol allow `operations.py` to branch on
backend capabilities without `isinstance` checks. Concrete backends assign these as class
attributes.

**`supports_batch_status_fetch: bool`**

`True` when `batch_fetch_statuses()` is fully implemented and can return
`dict[int, IssueStatus]` keyed by integer issue numbers. `False` for backends whose issue IDs
are not integers — those backends raise `NotImplementedError` from `batch_fetch_statuses`.

Consumed in `list_items()` (`operations.py`): when `True`, live status is fetched in a single
batch call; when `False`, the local YAML status field is authoritative and the batch call is
skipped entirely.

**`issue_id_type: Literal["integer", "string"]`**

`"integer"` for backends that use GitHub-style numeric issue IDs. `"string"` for backends that
use opaque string IDs (e.g. beads nanoids). Controls whether integer-keyed operations are
meaningful and determines how `item.issue` is interpreted.

Consumed in `_apply_issue_status_labels()` (`operations.py`): string-ID backends write status
directly to the local YAML cache file via `update_item_metadata` to prevent a silent no-op,
while integer-ID backends apply status labels via the backend call only (BUG-3 fix — see
comment at `operations.py` line 3311).

**Why these properties exist**

Branching on capabilities instead of concrete backend types means future string-ID backends
(e.g. Linear, GitLab) inherit the correct `operations.py` behaviour automatically — neither
`list_items()` nor `_apply_issue_status_labels()` needs to be modified when a new backend is
added. A new backend author needs only to set the two properties correctly.

**Capability comparison across all backends**

| Backend | `supports_batch_status_fetch` | `issue_id_type` |
|---------|-------------------------------|-----------------|
| `github` | `True` | `"integer"` |
| `sqlite` | `True` | `"integer"` |
| `memory` | `True` | `"integer"` |
| `beads` | `False` | `"string"` |

SOURCE: `backlog_core/backend_protocol.py` — Protocol property declarations with docstrings;
`backlog_core/backends/github_backend.py`, `sqlite_backend.py`, `memory_backend.py`,
`beads_backend.py` — per-backend class attribute assignments;
`backlog_core/operations.py` lines 2326–2333 (`list_items`) and 3311–3322
(`_apply_issue_status_labels`) — consumption sites.

### Configuration

Backend selection uses this resolution order:

1. `BACKLOG_BACKEND` environment variable
2. `backlog.backend` key in `.dh/config.yaml` (project root searched first, then `~/.dh/`)
3. Auto-detect: `beads` when `.beads/dh-backend` marker file exists at the project root (explicit opt-in)
4. Default: `github`

**Environment variable:**

```bash
BACKLOG_BACKEND=sqlite uv run --script plugins/development-harness/scripts/run_backlog_server.py
BACKLOG_BACKEND=beads uv run --script plugins/development-harness/scripts/run_backlog_server.py
```

**Beads auto-detection and lazy `bd` validation**: When `BACKLOG_BACKEND` is not set and no `.dh/config.yaml` `backlog.backend` key exists, the server inspects the project root for a `.beads/dh-backend` marker file. If the marker file is present, `beads` is selected automatically — this is the explicit opt-in mechanism for beads workspaces. The `bd` binary is **not** probed at startup; it is validated on the first `run_json()` call. If `bd` is absent or not executable at that point, `BdNotInstalledError` is raised. There is no silent fallback to `github`.

**`.dh/config.yaml` backend configuration:**

```yaml
backlog:
  backend: sqlite
```

Place `.dh/config.yaml` in the project root or `~/.dh/` for a persistent override. Project root takes precedence over `~/.dh/`. Call `reset_config()` between tests to force re-resolution.

### Migration Guide

Existing users are unaffected. When no `BACKLOG_BACKEND` variable, no `.dh/config.yaml` `backlog.backend` key, and no `.beads/dh-backend` marker file exist, the server selects `github` — identical behavior to before the pluggable architecture was introduced. No configuration changes are required unless switching backends.

---

## TaskBackend Protocol

The `TaskBackend` Protocol (defined in `sam_schema/core/task_backend.py`) decouples all SAM MCP operations from any specific storage platform. `TaskConfig` wraps the active backend instance; `server.py` receives it via dependency injection.

`TaskBackend` is an **orchestration Protocol**, not a storage Protocol. It composes over `IssueBackend` (coordination state) and `DocumentBackend` (durable handoff content) rather than owning its own storage primitives. The dependency graph evaluation stays in the query layer (`sam_schema/core/query.py`), not in backend implementations — backends return raw task data; callers evaluate readiness.

All protocol methods are synchronous. The MCP layer wraps calls in `asyncio.to_thread()` when needed.

### Method Groups

- **Plan lifecycle**: `create_plan`, `read_plan`, `list_plans`, `update_plan_fields`
- **Task access**: `read_task`, `claim_task`, `update_task_status`, `update_task_fields`, `append_task_section`, `get_ready_tasks`, `get_plan_status`
- **Incremental append**: `append_task`, `finalize_plan`
- **Documents**: `store_document`, `read_document`

`append_task` adds a single validated task to a plan. The method validates the task via
`Task.model_validate()` before writing. Current backends do not enforce a `state="drafting"`
precondition — callers must not assume `append_task` will reject appends based solely on plan
state. **Single-writer assumption**: `append_task` is NOT required to be atomic under concurrent
writers. Callers must serialize writes to the same plan. Behavior under concurrent `append_task`
calls for the same plan is **undefined** — backends are not required to detect, reject, or
recover from concurrent appends.

`finalize_plan` sets a plan's state to `state="ready"` for backends that implement the drafting
workflow. Creating a plan with an empty task list enters `state="drafting"`; `finalize_plan`
transitions it to `state="ready"`, making its tasks visible to `get_ready_tasks` and
`get_plan_status`. Callers should treat readiness and task visibility as backend-defined
behavior rather than assuming tasks become visible only after finalization. Both methods return
`dict[str, Any]`.

### Available Backends

| Backend | Identifier | Purpose |
|---------|-----------|---------|
| `LocalYamlTaskProvider` | `local` | Default. Wraps `yaml_reader.py` / `yaml_writer.py` + query layer. **In the MCP server context**, wrapped by `GistTaskLayer` — plans with an issue are Gist-backed and portable. CLI/direct use without the wrapper is single-machine only. |
| `InMemoryTaskProvider` | `memory` | In-memory test double. No persistence. Use in tests and CI where filesystem access is unavailable. |
| `GitHubTaskProvider` | `github` | Fully implemented (13 methods). Not selectable via factory — `create_task_backend("github")` raises `NotImplementedError` until #984 lands. Instantiate directly: `GitHubTaskProvider(issue_backend, doc_backend)`. Current `issue_backend` type is `BacklogBackend` (from `backlog_core.backend_protocol`) — stand-in until #984 delivers a standalone `IssueBackend`. `doc_backend` type is the `DocumentBackend` stub in `github_task.py`. |
| `BeadsTaskProvider` | `beads` | Maps SAM plans to beads epics; tasks to child issues with `--parent` links. Uses `bd` CLI subprocess. Active-task context persisted via `bd remember` under `dh.active-task.<session_id>` keys. |

### Configuration

Backend selection uses this resolution order:

1. `TASKBACKEND` environment variable
2. `[backend] name` in `taskbackend.toml` (project root searched first, then `~/.dh/`)
3. Default: `local`

**Environment variable:**

```bash
TASKBACKEND=memory uv run python plugins/development-harness/scripts/run_sam_server.py
```

**`taskbackend.toml` file:**

```toml
[backend]
name = "memory"
```

Place `taskbackend.toml` in the project root or `~/.dh/` for a persistent override. Project root takes precedence over `~/.dh/`. Call `reset_task_config()` between tests to force re-resolution.

### Lazy Migration

Plans without a `backend_ref` field continue using `LocalYamlTaskProvider` unchanged — existing deployments require no configuration changes. Plans migrated to a remote backend carry a `backend_ref` field with a backend-native resource identifier (e.g. a GitHub Issue number). When no `TASKBACKEND` variable and no `taskbackend.toml` file exist, the server selects `local` — identical behavior to before the Protocol was introduced.

---

## Backend Provider Concept

The development harness uses Protocol-based abstraction to decouple MCP tools from any specific platform. Three Protocols correspond to the three primitives:

| Protocol | Primitive | Backlog item | Current state |
|---|---|---|---|
| `IssueBackend` | Work Items + Sub-items | #389 (P2, groomed) | Operations hardcoded to GitHub in `backlog_core/gh_client.py` |
| `DocumentBackend` | Documents (durable handoff content) | #984 (P2, complete) | `ArtifactBackend` Protocol in `backlog_core/artifact_provider.py`; `GitHubGistArtifactProvider`, `LinearArtifactProvider`, `GitLabArtifactProvider`, `LocalFilesystemArtifactProvider` all implemented |
| `TaskBackend` | SAM orchestration over IssueBackend + DocumentBackend | #912 (P1, complete) | Protocol in `sam_schema/core/task_backend.py`, three backends: LocalYaml, GitHub, InMemory |

`TaskBackend` is a SAM-specific orchestration layer. It does not own its own storage — it composes over `IssueBackend` (for coordination state: create work items, create/claim/update sub-items) and `DocumentBackend` (for handoff content: store/read stage artifacts). This keeps SAM's semantic operations (readiness, dependency resolution, atomic claiming) separate from the storage primitives.

## Platform Capabilities

All data below is sourced from verified research. See [research/task-management/artifact-manifest-backend-providers.md](../../../research/task-management/artifact-manifest-backend-providers.md) for full citations and access dates.

### GitHub (Current Backend)

- **Issues API**: GraphQL (bulk fetch via `sync_issues_graphql`) + REST/PyGithub (single-item CRUD, label/milestone creation), 65,536 char body limit
- **Projects V2**: Project-level custom fields (5 types, 50 field max), GraphQL CRUD, text fields support exact match only
- **Issue Fields**: Org-level typed fields (25 max), public preview since 2026-03-12, full GraphQL + REST API, searchable/filterable
- **Sub-issues**: Native parent-child issue relationships
- **Labels**: Unlimited, cross-repo within org
- **Milestones**: Per-repo, title + description + due date + open/closed issue counts

### Linear

- **Issues**: Full GraphQL API for CRUD, rich state machine (backlog/triage/in-progress/done/cancelled)
- **Attachments**: Key-value metadata pairs, fully queryable/writable via GraphQL, used for external resource linking
- **Labels**: Label groups supported, no custom fields
- **Sub-issues**: Native parent-child issue relationships
- **MCP server**: Exposes labels, standard properties, attachments
- **Limits**: Attachment metadata limits not publicly documented

SOURCE: [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)

### GitLab

- **Issues**: REST + GraphQL API, description body (similar to GitHub)
- **Epics**: Group-level containers for issues (Premium/Ultimate)
- **Linked items**: Three relationship types ("relates to", "blocks", "is blocked by"), bi-directional, cross-project, full REST API support
- **Custom fields**: Premium/Ultimate only, 4 types (text, number, single-select, multi-select), 50 per group, 10 per work item type, 1,024 char max. REST API has NO custom field access as of 2026-03; GraphQL `CustomField` type queries/mutations are undocumented
- **Attachments**: Upload supported via REST; download via API NOT supported

SOURCE: [GitLab Custom Fields](https://docs.gitlab.com/ee/user/custom_fields.html), [GitLab Linked Issues API](https://docs.gitlab.com/ee/api/issue_links.html)

### Supabase

- **Storage**: PostgreSQL tables with columns matching domain models
- **API**: Auto-generated REST API (PostgREST) + client SDK
- **Query**: Full SQL capability, no field type or count limits beyond PostgreSQL constraints
- **Realtime**: WebSocket subscriptions for row-level changes
- **Auth**: Row-level security policies for multi-tenant access control

## Platform Mapping

How each platform maps to the three SAM primitives:

| Primitive | GitHub | Linear | GitLab | Supabase |
|-----------|--------|--------|--------|----------|
| **Work Item** (plan/feature) | Issue | Issue | Issue | `work_items` table |
| **Sub-item** (task) | Sub-issue (native parent-child) | Sub-issue (native parent-child) | Linked issue ("relates to") + Epics (Premium) | `tasks` table with `work_item_id` FK |
| **Document** (stage artifact) | Gist (versioned, multi-file) | Attachment (key-value metadata) | Snippet (versioned, multi-file) | `documents` table + storage object |
| **Document manifest** | Issue body section (HTML comment delimiters) | Attachment metadata pairs | Issue description section (HTML comment delimiters) | `document_manifests` table |
| **Status tracking** | Labels + Projects V2 status field | Built-in state machine (backlog/triage/in-progress/done/cancelled) | Labels + board lists | `status` column (enum) |
| **Dependency/relationships** | Sub-issues, cross-references, Projects V2 | Parent/child issues, relations | Linked items (relates/blocks/blocked by), Epics | Foreign keys, junction tables |

## Design Principles

1. **Follow each platform's native primitive** -- Linear uses Attachments for structured metadata, not fake custom fields. GitLab uses issue description sections until its custom field API matures. Each provider maps to what the platform actually supports.

2. **Backend as source of truth, local files as cache** -- same pattern as the current backlog MCP where GitHub Issues are canonical and `~/.dh/projects/{slug}/backlog/` files are derived. Future backends maintain this direction: the remote platform is authoritative, local state is a sync target.

3. **Protocol-based abstraction** -- consumers call the same MCP tools (`backlog_*`, `sam_*`, `artifact_*`) regardless of which backend is active. Backend selection is a server configuration concern, not a consumer concern.

4. **Implement GitHub first, define interfaces for others** -- the existing `ArtifactBackend` Protocol and `GitHubArtifactProvider` demonstrate the pattern. New backends implement the same Protocol. Interfaces are defined during architecture; implementations are added incrementally.

5. **Separate coordination state from handoff content** -- Work Items and Sub-items handle scheduling, claiming, gating, and tracking (coordination state). Documents handle the actual content agents produce and consume across stages (durable handoff). These are different workloads with different access patterns and must not be collapsed into a single primitive. See "SAM Storage Model" above.

6. **Backend is responsible for durable content storage** -- Documents store a `content_ref` (a backend-opaque identifier, not a filesystem path). The backend implementation resolves `content_ref` to bytes using its own native primitive (e.g., a GitHub Gist ID, a GitLab Snippet ID, a Supabase storage object key). Local filesystem is a valid implementation only for CLI or direct use of `LocalYamlTaskProvider` without GistTaskLayer. In the MCP server context, `LocalYamlTaskProvider` is wrapped by `GistTaskLayer`, which makes issue-backed plans durable in GitHub Gists and accessible from any environment. Any backend intended for sandbox, CI, or distributed agent access must store content remotely.

## Implementation Roadmap

Three Protocol abstractions are needed, one per subsystem:

### DocumentBackend Protocol (#984 — implemented)

Defined as `ArtifactBackend` in `backlog_core/artifact_provider.py`. Four provider implementations are available: `GitHubGistArtifactProvider` (default), `LinearArtifactProvider`, `GitLabArtifactProvider`, and `LocalFilesystemArtifactProvider` (automatic fallback when the remote backend is unreachable). The factory function `create_artifact_provider()` selects the provider based on `BACKLOG_BACKEND` env var or `backend_name` argument. Future evolution to `DocumentBackend` will reflect the full SAM storage model for durable handoff content between agents and stages.

**What a backend must provide to be pluggable**: durable, versioned content storage addressable by a backend-opaque `content_ref`. Content must be accessible from any environment with valid credentials. The backend must support querying documents by owner (work item or sub-item), type, and stage.

```python
@runtime_checkable
class DocumentBackend(Protocol):
    def list_documents(self, owner_id: int, owner_type: str = "work_item",
                       stage: str | None = None, doc_type: str | None = None) -> list[DocumentMeta]:
        """Return document metadata for the given owner, optionally filtered.

        owner_type is "work_item" or "sub_item". stage is S1-S7 or None for all.
        doc_type filters by document type (discovery, design, validation, etc.)
        or None for all.

        Returns metadata only (id, owner_type, owner_id, stage, type, title,
        format, version, backend_ref). Does NOT return content — use
        read_document for that.

        Must return an empty list (not raise) when no documents exist.
        """
        ...

    def store_document(self, owner_id: int, owner_type: str, stage: str,
                       doc_type: str, title: str, content: str,
                       fmt: str = "md") -> DocumentMeta:
        """Store a document durably and return its metadata including content_ref.

        The backend persists content using its native storage primitive (e.g.
        create/update a Gist, Snippet, or storage object).

        Must be idempotent: calling with the same (owner_id, owner_type, stage,
        doc_type) updates the existing document in place and increments the
        version. The content_ref must remain stable across updates.

        Content stored here must be accessible from any environment with valid
        backend credentials — not just the machine where this method ran.
        """
        ...

    def read_document(self, content_ref: str) -> str:
        """Retrieve document content by content_ref.

        The backend resolves content_ref (from a prior store_document call or
        from list_documents metadata) to the full content string.

        Must work from any environment with valid backend credentials.
        Raises ContentNotFoundError if the ref is invalid or the content
        has been deleted from the backend.
        """
        ...

    def get_manifest(self, issue_number: int) -> ArtifactManifest:
        """Return the document manifest for the given work item.

        The manifest is a structured list of registered documents with their
        type, content_ref, status, and agent. The backend retrieves this from
        wherever it stores structured metadata (e.g. issue body section,
        attachment key, table row).

        Must return an empty manifest (not raise) when no manifest exists yet.

        NOTE: This is the backward-compatible method from the existing
        ArtifactBackend Protocol. It will be superseded by list_documents
        once the migration from path-based to content_ref-based identification
        is complete.
        """
        ...

    def set_manifest(self, issue_number: int, manifest: ArtifactManifest) -> None:
        """Persist the document manifest for the given work item.

        The backend writes the manifest to its native structured metadata store.
        This operation must be atomic — a partial write must not corrupt an
        existing manifest.

        NOTE: Backward-compatible method. Will be superseded by store_document
        which manages manifest entries automatically.
        """
        ...
```

#### Artifact Provider Implementations

##### GitHubGistArtifactProvider (default)

`GitHubGistArtifactProvider` stores the artifact manifest as `manifest.json` in a private GitHub Gist. The Gist is linked to the issue body via the sentinel comment `<!-- artifact-gist:{gist_id} -->`.

Artifact file content (plan documents, research files) is stored as additional files in the same Gist, with `/` in the path replaced by `--` to form valid Gist filenames (e.g. `plan/architect-foo.md` → `plan--architect-foo.md`).

**Lazy migration**: Issues that still use the legacy `<!-- artifact-manifest:begin/end -->` inline format are automatically migrated to Gist storage on the first `get_manifest` call. The inline block is replaced with the Gist sentinel.

**Credentials**: `GITHUB_TOKEN` (must include the `gist` OAuth scope). No additional credentials required.

**Backward-compat alias**: `GitHubArtifactProvider` remains importable as an alias for `GitHubGistArtifactProvider`. No callers need to update their imports.

Source: `backlog_core/artifact_provider.py` — `GitHubGistArtifactProvider`

##### LinearArtifactProvider

`LinearArtifactProvider` stores the artifact manifest in Linear Attachments metadata using the `dh://artifact-manifest/{issue_number}` URL scheme as an idempotency key.

The manifest JSON is stored in the `metadata["manifest_json"]` field of the attachment. Linear treats attachments with the same URL on the same issue as idempotent — `set_manifest` updates the existing attachment rather than creating a duplicate.

**Issue ID note**: The provider passes `str(issue_number)` as the Linear issue UUID. Backlog items must store the Linear UUID (not the short sequence number) in their `issue_number` field.

**Size warning**: Linear attachment metadata has undocumented size limits. The provider logs a warning when the serialised manifest exceeds 10,000 characters.

**Credentials**:

- `LINEAR_API_KEY` — Linear personal API key (required)
- `LINEAR_TEAM_ID` — Linear team UUID (required; stored for team-scoped queries)

Source: `backlog_core/artifact_provider.py` — `LinearArtifactProvider`

##### GitLabArtifactProvider

`GitLabArtifactProvider` stores the artifact manifest as `manifest.json` in a private GitLab project snippet. The snippet is linked to the issue via a note (comment) containing the sentinel `<!-- artifact-snippet:{snippet_id} -->`.

Artifact file content is stored as additional files in the same snippet, with `/` replaced by `--` and `.txt` appended to the filename.

**Credentials**:

- `GITLAB_TOKEN` — GitLab personal access token (required)
- `GITLAB_PROJECT_ID` — GitLab project ID as an integer (required)
- `GITLAB_URL` — GitLab instance base URL (optional; defaults to `https://gitlab.com`)

Source: `backlog_core/artifact_provider.py` — `GitLabArtifactProvider`

#### Factory Function

`create_artifact_provider(backend_name=None, repo=None, root_worktree=None)` in `backlog_core/artifact_provider.py` selects and instantiates an artifact provider.

**Selection order**:

1. `backend_name` argument (explicit override)
2. `BACKLOG_BACKEND` environment variable
3. Default: `github`

**Supported values**: `github`, `linear`, `gitlab`, `local`, `beads`. Values `sqlite` and `memory` raise `BacklogError` — those backends do not support artifact storage. The `beads` provider stores artifact manifests as a JSON blob in `bd update --metadata dh.artifacts={...}`.

**Environment variables summary**:

| Variable | Required for | Default |
|---|---|---|
| `GITHUB_TOKEN` | `github` backend | — |
| `LINEAR_API_KEY` | `linear` backend | — |
| `LINEAR_TEAM_ID` | `linear` backend | — |
| `GITLAB_TOKEN` | `gitlab` backend | — |
| `GITLAB_PROJECT_ID` | `gitlab` backend | — |
| `GITLAB_URL` | `gitlab` backend | `https://gitlab.com` |

**`backend.toml` extensions** for Linear and GitLab — set `BACKLOG_BACKEND` in environment or use the `backend_name` argument. There is no `backend.toml` key specific to artifact providers; artifact backend selection uses the same `BACKLOG_BACKEND` mechanism as the `BacklogBackend`.

### IssueBackend Protocol (#389 — to be created)

Abstracts the backlog/issue operations currently hardcoded to GitHub in `backlog_core/gh_client.py` and `backlog_core/operations.py`. The current GitHub implementation uses `sync_issues_graphql` as the bulk fetch primitive; the Protocol interface expresses this as `list_issues`.

**What a backend must provide to be pluggable**: CRUD on work items (issues) and sub-items (child issues/tasks), label/status management, parent-child relationship traversal, and incremental sync for bulk fetch. Backends that lack native sub-issues must emulate the relationship via labels, linked items, or custom fields — the relationship must be traversable via `list_sub_issues`.

```python
class IssueBackend(Protocol):
    def get_issue(self, number: int) -> IssueData:
        """Return a single issue/item by its backend-assigned identifier.

        Must include title, body, labels/status, and any structured metadata
        fields the backend supports. Raises IssueNotFoundError if absent.
        """
        ...

    def create_issue(self, title: str, body: str, labels: list[str], **kwargs) -> IssueData:
        """Create a new issue/item and return it with its assigned identifier.

        The backend assigns a stable numeric or string identifier. All
        subsequent operations reference this identifier, not the title.
        """
        ...

    def update_issue(self, number: int, **kwargs) -> None:
        """Update mutable fields on an existing issue/item.

        Implementations must accept unknown kwargs gracefully — callers may
        pass fields the backend does not support. Unsupported fields are
        silently ignored (not an error).
        """
        ...

    def close_issue(self, number: int) -> None:
        """Mark an issue/item as closed/resolved in the backend."""
        ...

    def list_issues(self, state: str, labels: list[str], since: str | None = None) -> list[IssueData]:
        """Return all issues/items matching the given filters.

        `since` is an ISO 8601 datetime string for incremental sync. Backends
        that support incremental fetch must honour it; backends that do not
        may return all matching items and let the caller filter by updated_at.

        This is the bulk fetch primitive — implementations should use the most
        efficient query mechanism the platform provides (e.g. GraphQL cursor
        pagination, SQL WHERE clause, REST ?updated_after param).
        """
        ...

    def add_label(self, number: int, label: str) -> None:
        """Attach a label/tag to an issue/item. No-op if already present."""
        ...

    def remove_label(self, number: int, label: str) -> None:
        """Remove a label/tag from an issue/item. No-op if not present."""
        ...

    def create_sub_issue(self, parent: int, title: str, body: str, **kwargs) -> IssueData:
        """Create a child item under the given parent and return it.

        Backends that do not support native sub-issues must emulate the
        relationship (e.g. via a label, a linked-item relation, or a
        custom field). The relationship must be traversable via
        `list_sub_issues`.
        """
        ...

    def list_sub_issues(self, parent: int) -> list[IssueData]:
        """Return all child items of the given parent item."""
        ...

    def sync_status(self, number: int, status: str) -> None:
        """Set the workflow status of an issue/item.

        Status values are backend-agnostic strings (e.g. "in-progress",
        "done"). The backend maps these to its native status/state field.
        Backends with fixed state machines (e.g. Linear) must map to the
        nearest equivalent state; unmappable values raise StatusMappingError.
        """
        ...
```

### TaskBackend Protocol (#912 — implemented)

SAM-specific orchestration layer that composes over `IssueBackend` (for coordination state on work items and sub-items) and `DocumentBackend` (for durable handoff content). TaskBackend does not own its own storage — it adds SAM semantics (dependency resolution, readiness queries, atomic claiming) on top of the two storage Protocols.

Defined in `sam_schema/core/task_backend.py`. All protocol methods are synchronous. The MCP layer wraps calls in `asyncio.to_thread()` when needed — matching the pattern established in `backlog_core.backend_protocol`.

**What a backend must provide to be pluggable**: atomic task claiming (conditional write on status), dependency graph evaluation for readiness queries, and durable status persistence visible to all agents immediately. The backend delegates work item and document operations to `IssueBackend` and `DocumentBackend` respectively.

#### Method Groups

- **Plan lifecycle**: `create_plan`, `read_plan`, `list_plans`, `update_plan_fields`
- **Task access**: `read_task`, `claim_task`, `update_task_status`, `update_task_fields`, `append_task_section`, `get_ready_tasks`, `get_plan_status`
- **Incremental append**: `append_task`, `finalize_plan`
- **Documents**: `store_document`, `read_document`

#### Protocol Interface (13 methods)

```python
@runtime_checkable
class TaskBackend(Protocol):
    # -- Plan lifecycle --

    def create_plan(
        self,
        slug: str,
        goal: str,
        tasks: list[TaskDefinition],
        *,
        context: str | None = None,
        issue: int | None = None,
        acceptance_criteria: str | None = None,
    ) -> PlanData:
        """Create a new plan. Raises PlanExistsError if slug collides."""
        ...

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by backend-assigned identifier (e.g. 'Pd9e0f1a2')."""
        ...

    def list_plans(
        self, *, search: str | None = None, offset: int = 0, limit: int | None = None
    ) -> list[PlanSummary]:
        """Return lightweight summaries, optionally filtered by substring."""
        ...

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None,
        set_fields: dict[str, str | int | list[str]] | None = None,
    ) -> None:
        """Update top-level fields on a plan."""
        ...

    # -- Task access --

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task from a plan. Raises TaskNotFoundError."""
        ...

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Atomically claim a task (not-started → in-progress).

        Returns True on success, False if already claimed or terminal.
        """
        ...

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Set task status. Valid: not-started, in-progress, complete, blocked, deferred, skipped."""
        ...

    def update_task_fields(
        self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]
    ) -> None:
        """Set one or more scalar fields on a task."""
        ...

    def append_task_section(
        self, plan_id: str, task_id: str, section_name: str, content: str
    ) -> None:
        """Append markdown content to a named section of a task body."""
        ...

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return tasks where status is not-started and all dependencies are complete."""
        ...

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return summary dict: feature, total_tasks, by_status, ready_tasks, blocked_tasks, completion_pct, has_cycles."""
        ...

    # -- Documents --

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str,
        title: str, content: str, fmt: str = "md",
    ) -> DocumentHandle:
        """Persist a document and return an opaque retrieval handle."""
        ...

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Retrieve a document by its handle."""
        ...
```

#### Available Backends

| Backend | Identifier | Class | Purpose |
|---------|-----------|-------|---------|
| `LocalYamlTaskProvider` | `local` | `sam_schema.core.backends.local_yaml` | Default. Wraps existing YAML I/O stack (yaml_reader, yaml_writer, query). **In the MCP server context**, wrapped by `GistTaskLayer` (`sam_schema.core.gist_task_layer`) — issue-backed plans write through to Gist and are portable. CLI/direct use without GistTaskLayer is single-machine only. |
| `GitHubTaskProvider` | `github` | `sam_schema.core.backends.github_task` | Maps plans → GitHub Issues (`sam:plan` label), tasks → sub-issues (`sam:{status}` labels). Constructor: `GitHubTaskProvider(issue_backend: BacklogBackend, doc_backend: DocumentBackend)`. `BacklogBackend` is from `backlog_core.backend_protocol`; `DocumentBackend` is a stub in `github_task.py` pending #984. |
| `InMemoryTaskProvider` | `memory` | `sam_schema.core.backends.memory` | In-memory test double. No persistence. Use in tests and CI. |
| `BeadsTaskProvider` | `beads` | `sam_schema.core.backends.beads_task` | Maps plans → beads epics, tasks → child issues with `--parent` links. Context persistence via `bd remember` under `dh.active-task.<session_id>` keys. Artifacts stored as JSON blob in `bd update --metadata dh.artifacts={...}`. |

#### Configuration

Backend selection uses this resolution order (mirrors BacklogBackend pattern):

1. `TASKBACKEND` environment variable
2. `[backend] name` key in `taskbackend.toml` (project root searched first, then `~/.dh/`)
3. Default: `local`

**Environment variable:**

```bash
TASKBACKEND=memory uv run python plugins/development-harness/scripts/run_sam_server.py
```

**`taskbackend.toml` file:**

```toml
[backend]
name = "local"
```

Place `taskbackend.toml` in the project root or `~/.dh/` for a persistent override. Project root takes precedence over `~/.dh/`. Call `reset_task_config()` between tests to force re-resolution.

The factory function `create_task_backend(name)` in `sam_schema.core.task_config` resolves the backend name and returns a configured `TaskBackend` instance. The `TaskConfig` dataclass wraps the active backend for dependency injection into the MCP server.

#### Migration Guide

Existing users are unaffected. When no `TASKBACKEND` variable and no `taskbackend.toml` file exist, the server selects `local` — identical behavior to before the pluggable architecture was introduced. The `local` backend wraps the existing YAML I/O stack without modifying underlying modules. No configuration changes are required unless switching backends.

#### GistTaskLayer — Gist-Backed Plan Storage (#2509)

`GistTaskLayer` (`sam_schema/core/gist_task_layer.py`) is a `TaskBackend` wrapper that the MCP server applies on top of `LocalYamlTaskBackend`. It is NOT a backend identifier — selecting `task.backend: local` in `.dh/config.yaml` activates `GistTaskLayer(LocalYamlTaskBackend)` in the server context automatically. CLI or test code that instantiates `LocalYamlTaskBackend` directly does not receive this wrapping.

**Write-path (mandatory, raises on failure):**

Plans and mutations write through to a GitHub Gist via `ArtifactRegistryClient.store(issue, yaml_content)`, which calls `artifact_register(item_id=issue, artifact_type="task-plan", content=yaml_content)`. If the Gist write fails, `ArtifactWriteError` is raised and propagated as a structured MCP error — no silent success. Plans with `issue=None` skip Gist upload and emit a non-portability warning; all write-path operations on `issue=None` plans complete locally only.

**Read-path (Gist-first with annotated local fallback):**

`read_plan` resolves `plan_id → issue` via `PlanIdIndex`, then fetches YAML from Gist. If the Gist fetch fails or the index has no entry for the plan (pre-fix local-only plans), it falls back to `LocalYamlTaskProvider.read_plan()`. The fallback is annotated in the response (`source="local"`) — it is never silent. `PlanNotFoundError` is raised when both Gist and local miss.

**Asymmetry summary:**

| Operation | On failure |
|---|---|
| Gist write (create/mutation) | Raises `ArtifactWriteError` — hard error |
| Gist read (read_plan) | Falls back to local with `source="local"` annotation |
| Plan index write (register) | Warning only — content is still in Gist |
| Plan index read (resolve) | Returns `None` — silent fallback to local read |

**claim_task atomicity decision (ADR-2509-3 resolution — Option 3: Serialized Dispatch):**

The GitHub REST and GraphQL APIs as of 2026-05-30 provide no conditional/atomic mutation primitive for labels. `addLabels`/`removeLabels` are idempotent, not conditional; Gist blob read-modify-write provides no compare-and-swap.

**Chosen mechanism**: Serialized Dispatch. The exactly-once guarantee is enforced by the caller — the `implement-feature` dispatch orchestrator claims one task at a time per dispatch wave, waiting for the claim response before dispatching the next task. Under this pattern, two agents never race on the same task.

**Declared contract deviation**: `GistTaskLayer.claim_task()` does NOT guarantee exactly-once in isolation. Two concurrent callers may both receive `True`. Exactly-once holds only when dispatch is serialized at the orchestrator level. This deviation is documented in the `claim_task` docstring and in `CLAUDE.md`.

Why the other ADR-2509-3 options were rejected:

- **Option 1 (GitHub conditional mutation)**: No such primitive exists in the GitHub API as of 2026-05-30.
- **Option 2 (external lock)**: Adds operational complexity (Redis or a Gist-based lock file with its own race conditions) with no benefit when Option 3 already serializes.
- **Option 4 (accept eventual consistency)**: Requires idempotent task outputs, which the `TaskBackend` Protocol does not guarantee.

`claim_task` for `issue=None` plans raises `ConcurrentClaimUnsupportedError` immediately — local-only plans have no GitHub anchor for cross-agent coordination.

After a successful claim, `GistTaskLayer` performs a best-effort Gist write-back so `read_plan` returns consistent task status. Write-back failure logs a `WARNING` and does not roll back the claim.

**PlanIdIndex and `sam.plan_index_issue` configuration:**

`PlanIdIndex` maintains a `plan_id → issue` reverse-map YAML blob stored on a sentinel GitHub issue. Configure it via `.dh/config.yaml`:

```yaml
sam:
  plan_index_issue: 2509  # replace with a dedicated 'SAM Plan Registry' issue number
```

Recommendation: create a dedicated pinned issue labelled "SAM Plan Registry" and use its number. Using a working-feature issue as the sentinel is valid during development but not for long-lived deployments.

What happens when `sam.plan_index_issue` is unset:

- `create_plan` with `issue` set: content uploads to Gist successfully, but index registration raises `PlanIndexConfigError`. The MCP response includes a warning: "Set sam.plan_index_issue in .dh/config.yaml to enable plan_id reverse lookup." The plan is still in Gist and readable via its issue number, but cross-environment `plan_id`-based lookup will fail.
- `read_plan(plan_id)`: index resolution returns `None` (no exception) → falls back to `LocalYamlTaskProvider.read_plan(plan_id)`. Local file must exist for the read to succeed.
- `list_plans`: `PlanIdIndex.list_all()` returns an empty list (no exception); only local plans appear.

**Scope note**: `GistTaskLayer` is the fix for #2509 (environment-independent plan storage). Full `GitHubTaskProvider` support (#984, mapping tasks to GitHub sub-issues) remains a separate, out-of-scope initiative.

### Composition

`IssueBackend` and `DocumentBackend` are storage Protocols — they own primitives. `TaskBackend` is an orchestration Protocol — it composes over the other two. A deployment selects one provider per storage Protocol; `TaskBackend` uses whatever storage Protocols are configured.

```text
backlog MCP server
  ├── IssueBackend     (GitHubIssueProvider | LinearIssueProvider | ...)
  └── DocumentBackend  (GitHubDocumentProvider | LinearDocumentProvider | ...)

sam MCP server
  └── TaskBackend  (composes over IssueBackend + DocumentBackend)
       ├── uses IssueBackend for: create/read work items, create/update/claim sub-items
       └── uses DocumentBackend for: store/read stage artifacts, attach reports to tasks
```

Current deployment: GitHub for issues, local files for tasks, GitHub issue comments for documents.

Target deployment: GitHub for issues + sub-items, GitHub Gists for documents, TaskBackend orchestrating both.

Backend selection is configured via a config file at server startup. Each MCP server receives its provider instances via dependency injection. The two storage Protocols compose independently — a deployment can mix backends (e.g., GitHub for issues, Supabase for documents).

## References

- [graphql-usage-guide.md](./graphql-usage-guide.md) -- `sync_issues_graphql` usage, parameters, anti-patterns, and performance data
- [research/task-management/artifact-manifest-backend-providers.md](../../../research/task-management/artifact-manifest-backend-providers.md) -- cross-platform research with full citations
- `~/.dh/projects/{slug}/plan/architect-artifact-manifest.md` -- architecture spec for ArtifactBackend Protocol (access via `artifact_read`)
- `~/.dh/projects/{slug}/plan/feature-context-artifact-manifest.md` -- problem space and desired outcomes (access via `artifact_read`)
- [artifact-manifest-backends.md](./artifact-manifest-backends.md) -- artifact-specific backend details
- [backlog_core/artifact_provider.py](../backlog_core/artifact_provider.py) -- ArtifactBackend Protocol definition; GitHubGistArtifactProvider, LinearArtifactProvider, GitLabArtifactProvider, LocalFilesystemArtifactProvider implementations; create_artifact_provider factory
- [backlog_core/artifact_provider_local.py](../backlog_core/artifact_provider_local.py) -- LocalFilesystemArtifactProvider implementation; atomic manifest writes with fcntl advisory locking
- [backlog_core/linear_client.py](../backlog_core/linear_client.py) -- Linear Attachments API client (linear_get_attachments, linear_create_attachment)
- [backlog_core/gitlab_client.py](../backlog_core/gitlab_client.py) -- GitLab Snippets and Notes API client (gitlab_create_snippet, gitlab_get_snippet, gitlab_update_snippet, gitlab_create_issue_note, gitlab_list_issue_notes)
- [backlog_core/gh_client.py](../backlog_core/gh_client.py) -- current GitHub-specific issue operations
- [sam_schema/core/task_backend.py](../sam_schema/core/task_backend.py) -- TaskBackend Protocol definition (13 methods)
- [sam_schema/core/task_backend_types.py](../sam_schema/core/task_backend_types.py) -- TypedDict shapes: TaskDefinition, TaskData, PlanData, PlanSummary, DocumentHandle, DocumentData
- [sam_schema/core/task_config.py](../sam_schema/core/task_config.py) -- create_task_backend factory, TaskConfig dataclass, reset_task_config
- [sam_schema/core/exceptions.py](../sam_schema/core/exceptions.py) -- SAM exception hierarchy: SamError, PlanNotFoundError, PlanExistsError, TaskNotFoundError, TaskValidationError, DocumentNotFoundError, ArtifactWriteError, PlanIndexError, PlanIndexConfigError, ConcurrentClaimUnsupportedError
- [sam_schema/core/gist_task_layer.py](../sam_schema/core/gist_task_layer.py) -- GistTaskLayer wrapper: write-through create/mutation, Gist-first dual-read, claim_task atomicity decision (ADR-2509-3 Option 3)
- [sam_schema/core/plan_id_index.py](../sam_schema/core/plan_id_index.py) -- PlanIdIndex: plan_id↔issue reverse-map stored on sentinel GitHub issue; create_plan_id_index factory reads sam.plan_index_issue from .dh/config.yaml
- [sam_schema/core/artifact_registry_client.py](../sam_schema/core/artifact_registry_client.py) -- ArtifactRegistryClient: thin wrapper over artifact_register/artifact_read for Gist storage
- [sam_schema/core/backends/](../sam_schema/core/backends/) -- LocalYamlTaskProvider, InMemoryTaskProvider, GitHubTaskProvider implementations
