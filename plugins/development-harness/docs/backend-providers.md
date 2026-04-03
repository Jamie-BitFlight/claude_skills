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
- **Backend selection**: `BACKLOG_BACKEND` env var → `backend.toml` → default `github`
- **GitHub backend**: GitHub Issues canonical; local files are derived cache updated by `backlog_sync` and `backlog_pull`. Bulk sync via `sync_issues_graphql` in `backlog_core/gh_client.py` — GraphQL cursor-paginated fetch with optional `since` filter. Full sync ~12s for 245 issues; incremental sync ~0.7s. `create_milestone` and `create_label` remain REST-only (no GraphQL mutations — ADR-004).

### Plans/Tasks (SAM MCP)

- **Source of truth**: Local YAML task files in `~/.dh/projects/{slug}/plan/` directory (resolved via `dh_paths.plan_dir()`)
- **GitHub link**: Each task YAML can contain a `github_issue` field linking to a GitHub sub-issue for status sync
- **Implementation**: `sam_schema/` package, exposed as FastMCP 3.x server (`mcp__plugin_dh_sam__*`)
- **Operations**: List plans, read/claim/update tasks, check readiness, create plans
- **Format**: YAML frontmatter per task file (legacy: monolithic markdown with `## Task {ID}` headers)

### Artifact Manifest (backlog MCP artifact tools)

- **Source of truth**: GitHub Issue body (structured section between `<!-- artifact-manifest:begin/end -->` delimiters)
- **Implementation**: `backlog_core/artifact_provider.py` defines the `ArtifactBackend` Protocol and `GitHubArtifactProvider`
- **Operations**: `get_manifest`, `set_manifest`, `read_artifact_content`
- **File content**: Always served from local filesystem regardless of manifest backend

## BacklogBackend Protocol

The `BacklogBackend` Protocol (defined in `backlog_core/backend_protocol.py`) decouples all backlog MCP operations from any specific storage platform. `BacklogConfig` wraps the active backend instance; `operations.py` and `server.py` receive it via dependency injection and never import from `gh_client`, `github_sync`, or `github_branches` directly.

All protocol methods are synchronous. The MCP layer wraps calls in `asyncio.to_thread()` when needed.

### Method Groups

- **Repository access**: `get_github`, `try_get_github`, `probe_backend_status`
- **GraphQL utilities**: `_graphql_request`, `_resolve_labels_graphql`
- **Issue CRUD**: `_fetch_issue_graphql`, `_fetch_issues_graphql`, `_update_issue_graphql`, `sync_issues_graphql`, `create_issue_for_item`, `close_github_issue`, `resolve_github_issue`, `fetch_open_issues_by_title`, `fetch_github_issue_body`, `check_open_prs_for_issue`, `batch_fetch_statuses`, `fetch_item_status`, `view_enrich_from_github`, `issue_to_local_fields`
- **Issue comments**: `_add_comment_graphql`, `_fetch_issue_comments_graphql`, `_fetch_comment_by_id_graphql`, `_update_issue_comment_graphql`
- **Status mutations**: `apply_status_in_progress`, `apply_status_verified`, `apply_status_groomed`, `sync_groomed_to_github_issue`
- **Milestones / projects**: `_fetch_milestones_graphql`, `_projects_v2_list_query`, `_projects_v2_create_mutation`
- **Task issues**: `create_task_issue`, `get_task_issues`, `update_task_status`
- **Sync / serialisation**: `render_issue_body`, `parse_issue_body`, `merge_item`, `unknown_key_to_heading`
- **Integration branches**: `create_integration_branch`, `get_integration_branch_status`, `merge_integration_branch`, `delete_integration_branch`, `list_integration_branches`

### Available Backends

| Backend | Identifier | Purpose |
|---------|-----------|---------|
| `GitHubBackend` | `github` | Default. Delegates to `gh_client.py`, `github_sync.py`, `github_branches.py`. Requires `GITHUB_TOKEN`. |
| `SQLiteBackend` | `sqlite` | Local 6-table schema via stdlib `sqlite3`, WAL mode. No external credentials required. |
| `InMemoryBackend` | `memory` | In-memory test double. No persistence. Use in tests and CI where GitHub is unavailable. |

### Configuration

Backend selection uses this resolution order:

1. `BACKLOG_BACKEND` environment variable
2. `[backend] name` key in `backend.toml` (project root searched first, then `~/.dh/`)
3. Default: `github`

**Environment variable:**

```bash
BACKLOG_BACKEND=sqlite uv run python plugins/development-harness/scripts/run_backlog_server.py
```

**`backend.toml` file:**

```toml
[backend]
name = "sqlite"
```

Place `backend.toml` in the project root or `~/.dh/` for a persistent override. Project root takes precedence over `~/.dh/`. Call `reset_config()` between tests to force re-resolution.

### Migration Guide

Existing users are unaffected. When no `BACKLOG_BACKEND` variable and no `backend.toml` file exist, the server selects `github` — identical behavior to before the pluggable architecture was introduced. No configuration changes are required unless switching backends.

---

## Backend Provider Concept

The development harness uses Protocol-based abstraction to decouple MCP tools from any specific platform. Three Protocols correspond to the three primitives:

| Protocol | Primitive | Backlog item | Current state |
|---|---|---|---|
| `IssueBackend` | Work Items + Sub-items | #389 (P2, groomed) | Operations hardcoded to GitHub in `backlog_core/gh_client.py` |
| `DocumentBackend` | Documents (durable handoff content) | #984 (P2, groomed) | `ArtifactBackend` Protocol exists in `backlog_core/artifact_provider.py` with `GitHubArtifactProvider` |
| `TaskBackend` | SAM orchestration over IssueBackend + DocumentBackend | #912 (P1, grooming) | Local YAML in `sam_schema/`, no Protocol yet |

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

6. **Backend is responsible for durable content storage** -- Documents store a `content_ref` (a backend-opaque identifier, not a filesystem path). The backend implementation resolves `content_ref` to bytes using its own native primitive (e.g., a GitHub Gist ID, a GitLab Snippet ID, a Supabase storage object key). Local filesystem is a valid implementation only for `LocalYamlTaskProvider` in single-machine, non-distributed use. Any backend intended for sandbox, CI, or distributed agent access must store content remotely.

## Implementation Roadmap

Three Protocol abstractions are needed, one per subsystem:

### DocumentBackend Protocol (#984 — evolves from existing ArtifactBackend)

Currently defined as `ArtifactBackend` in `backlog_core/artifact_provider.py` with `GitHubArtifactProvider`. Evolves to `DocumentBackend` to reflect the SAM storage model: Documents are durable handoff content between agents and stages, not just metadata manifests.

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

### TaskBackend Protocol (#912 — to be created)

SAM-specific orchestration layer that composes over `IssueBackend` (for coordination state on work items and sub-items) and `DocumentBackend` (for durable handoff content). TaskBackend does not own its own storage — it adds SAM semantics (dependency resolution, readiness queries, atomic claiming) on top of the two storage Protocols.

Currently implemented as local YAML files in `sam_schema/`. The local YAML implementation (`LocalYamlTaskProvider`) is a valid backend for single-machine use only — it cannot be accessed from sandboxes, CI runners, or distributed agents without filesystem access. Any deployment requiring environment portability must use a remote-backed implementation that delegates to `IssueBackend` + `DocumentBackend`.

**What a backend must provide to be pluggable**: atomic task claiming (conditional write on status), dependency graph evaluation for readiness queries, and durable status persistence visible to all agents immediately. The backend delegates work item and document operations to `IssueBackend` and `DocumentBackend` respectively.

```python
class TaskBackend(Protocol):
    def list_plans(self) -> list[PlanSummary]:
        """Return summary metadata for all plans visible to this backend.

        For remote backends, this fetches from the authoritative remote store.
        For local backends, this scans the local plan directory.
        Must not require filesystem access to succeed on remote backends.
        """
        ...

    def read_plan(self, plan_id: str) -> PlanData:
        """Return the full plan including all task definitions.

        plan_id is the backend-assigned stable identifier (e.g. issue number,
        slug, or UUID). Raises PlanNotFoundError if absent.

        Remote backends must serve this from the remote store, not a local
        cache, to ensure consistency across distributed agents.
        """
        ...

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Return a single task from the given plan.

        task_id is the task key within the plan (e.g. "T1", "T03"). Raises
        TaskNotFoundError if the plan exists but the task does not.
        """
        ...

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Atomically claim a task for execution. Returns True if claimed.

        A task may only be claimed if its current status is "not-started".
        The backend must use its platform's atomic primitive (e.g. conditional
        write, compare-and-swap, optimistic locking) to prevent two agents
        claiming the same task concurrently.

        Returns False (not raises) if the task is already claimed or in a
        terminal state. Callers must check the return value.
        """
        ...

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update the status of a task to one of the recognised SAM states.

        Valid statuses: not-started, in-progress, complete, failed, skipped.
        The backend persists this durably so other agents see the update
        immediately without requiring a local file or cache refresh.
        """
        ...

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return all tasks whose dependencies are satisfied and status is not-started.

        The backend evaluates the dependency graph and returns only tasks that
        are unblocked. This must be computed from the authoritative store, not
        a local snapshot, to avoid race conditions in parallel execution.
        """
        ...

    def create_plan(self, slug: str, goal: str, tasks: list[TaskDefinition], **kwargs) -> PlanData:
        """Persist a new plan with its task definitions and return it.

        The backend assigns a stable plan_id and stores all task definitions
        durably. The plan must be readable by `read_plan` from any environment
        immediately after this call returns.

        kwargs may include issue_number (to link the plan to a backlog item),
        acceptance_criteria, and other plan-level metadata fields.
        """
        ...
```

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
- [backlog_core/artifact_provider.py](../backlog_core/artifact_provider.py) -- ArtifactBackend Protocol definition and GitHubArtifactProvider
- [backlog_core/gh_client.py](../backlog_core/gh_client.py) -- current GitHub-specific issue operations
- [sam_schema/](../sam_schema/) -- current local YAML task implementation
