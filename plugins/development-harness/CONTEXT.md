# Development Harness

Vocabulary for the `development-harness` plugin — one bounded context covering all 8 of its
packages (`agent_profile`, `backlog_core`, `dh_core`, `dispatch_schema`, `hooks`,
`progressive_markdown`, `sam_schema`, `scripts`), not one context per package. Every consumer is
an agent; there is no human reader. The Markdown Consumption terms below (Collection, Generation,
Navigation, Control set, etc.) are normatively defined in
`docs/agent-markdown-consumption-contract.md` — this file is vocabulary only, for that area and
every other area of the plugin as it gets resolved.

## Dispatch Roles

Three roles govern who may dispatch further agents and on whose behalf, defined by relationship —
never by capability, and never by whether an agent happens to dispatch further work. See
[ADR-3113-1](./docs/adrs/ADR-3113-1-orchestrator-manager-worker-role-vocabulary.md) for the
incident that required stating this precisely.

**Orchestrator**:
The single interactive agent acting directly on behalf of the human. Exactly one per session,
always. Defined by relationship, not capability: the orchestrator is whichever agent received the
task directly from the human — not whichever agent happens to be dispatching subagents at a given
moment. A subagent dispatching further subagents does not become the orchestrator by doing so; it
remains a Manager or Worker, acting on behalf of whoever dispatched it.
_Avoid_: "the orchestrator" as a synonym for "whoever is executing this skill" — that usage is the
mechanism behind the #3060 incident (ADR-3113-1): a skill written in first person for the
orchestrator, handed to a dispatched Worker, was read as license to dispatch further agents the
Worker was never assigned to dispatch.

**Manager**:
A subagent explicitly assigned, by its own dispatcher, to decompose a scoped piece of work and
dispatch further subagents within that scope. The assignment is always stated as data — in the
delegation prompt, or in the SAM task's `executor` field once typed (see #3100) — never inferred
from a loaded skill's own voice, and never adopted on the subagent's own initiative. Sub-dispatch
is legitimate and valuable when assigned this way; see ADR-3113-1 for why unassigned adoption,
not dispatch itself, is the actual defect.
_Avoid_: "orchestrator" for this role — a Manager acts on behalf of its dispatcher, not on behalf
of the human directly, and the two roles carry different obligations (see Orchestrator above).

**Worker**:
A subagent assigned one unit of work to execute directly — a SAM task, or a direct prompt with no
SAM reference (`dh:task-worker` is dispatched both ways; see AGENTS.md's Dispatch Pattern). A
Worker's own assignment may explicitly name a specific skill to invoke, including one that itself
dispatches a fixed, bounded set of subagents to complete that one unit of work — a quality-gate
task naming `dh:multi-perspective-review`, which fans out four reviewers, is the Worker's
assignment, not a role it inferred. What a Worker never does is independently drive an open-ended,
multi-round dispatch loop across an entire plan — that requires the Manager role, explicitly
assigned. On receiving an instruction to run a plan-managing skill it was not assigned to run, a
Worker reports the conflict (`STATUS: BLOCKED`) rather than complying. `dh:task-worker` is this
plugin's canonical Worker implementation.
_Avoid_: assuming role is detectable from the environment or harness — role is always explicit,
asserted by the dispatcher. This plugin targets Claude Code, Codex, and OpenCode; a detection
mechanism tied to one harness's internals (e.g. inspecting a system prompt) does not port to the
others and is not a sanctioned pattern even where it happens to work.

## Language

**SAM (Stateless Agent Methodology)**:
A constraint-driven development framework, external to this repo, treating an agent as a
stateless computation engine — complete context in, one verified artifact out, no memory carried
between calls. The canonical specification lives at `../stateless-agent-methodology/`
(`bitflight-devops/stateless-agent-methodology` on GitHub) — this plugin implements SAM patterns
for backlog-driven feature work, it does not define SAM.
_Avoid_: "the SAM plugin" (there is no such thing — SAM is the methodology; `development-harness`
is the plugin implementing it); "stateless agent" alone as a synonym for SAM itself (ambiguous
between the methodology and one literal stateless agent instance).

**Backend**:
The data provider Collection reaches. Confirmed by the repo owner: "backend" always means the
data-providing system, never a call to the MCP tool or CLI — those are Frontend below. Not one
universal instance: backlog items route through `WorkItemBackend` (GitHub, SQLite, Beads, or
Memory; see `docs/backend-providers.md`), accessed through `MarkdownContentProvider` (a thinner,
markdown-specific adapter in front of it). SAM plans and tasks currently do **not** share that
`WorkItemBackend` — they route through a separate `TaskBackend` protocol
(`dh_core/protocols.py`), confirmed by the repo owner and verified against `dh_core/operations.py`
(`create_plan(backend: TaskBackend, ...)` etc.). This contradicts `AGENTS.md`'s current "that same
backend... there is no TASKBACKEND" claim — tracked as [#3088](https://github.com/Jamie-BitFlight/claude_skills/issues/3088),
not corrected here since it's outside this document's scope.
_Avoid_: "backend call" for an MCP tool invocation or CLI request — that ambiguity caused real
confusion in this session's design discussion. A backend call is specifically Collection
reaching a data provider. Also avoid assuming "the backend" means one shared instance across
backlog items and SAM — verify which protocol (`WorkItemBackend` vs `TaskBackend`) a given
subsystem actually uses before making that claim.

**Frontend**:
MCP, CLI, and the local navigator together — everything on the agent-facing side of a backend
call. The control set (below) is part of the Frontend: it's Navigation's local cache, not
something the Backend knows about or participates in.

**Collection**:
Gathering source content from wherever it lives — issue body, plan file, task file, artifact.
Unbounded: never truncated, never budget-checked. Unrelated to Control set below or to session
identity. For remote-capable providers (GitHub today), Collection's primary path is a live
network read, not a local cache hit — `GitHubContentCache.get_content()` reads online whenever
GitHub is reachable, and `backlog_view`'s issue-body fetch has no cache layer at all. `FileCache`
(`backlog_core/file_cache.py`) exists but only serves the offline-fallback path (GitHub
unreachable, or the online read fails) plus write durability — `FileCache.__init__` takes no
session parameter and has no session concept. Beads, SQLite, and
Memory read and write native state directly and never instantiate `FileCache` (see
`docs/backend-providers.md`'s provider table) — for those backends Collection has no local-cache
layer to hit; a re-run reads the native store directly. `FileCache` predates this document and
is not part of the Navigation pipeline described here.

**Generation**:
Assembling the complete markdown document for a requested scope — description, and every
section or artifact content the request covers — before any windowing. Unbounded, same as
Collection. Generation supplies Navigation the document to parse; it does not assign addresses
or build the table of contents itself — those are Navigation's, derived from the parsed tree
(see Navigation and Table of contents below).

**Navigation** (pipeline stage):
The one system that takes a generated document, gives it a content identity, caches it in the
global control set, and windows it to the agent. The only stage where a size budget applies. Source-agnostic:
it has no knowledge of what kind of thing it is windowing — issue, PR, plan, artifact, local
file — the same relationship a browser's chrome has to the page it renders. Global, not
per-source: one Navigation stage serves every source, never one implementation per source type.
_Avoid_: "pagination layer" as a synonym for the whole stage — pagination is one of the things
Navigation does, not the stage's name.

**Provider**:
The seam that makes Navigation source-agnostic. Implements `get_markdown(source) -> str`;
supplies markdown text for a source without Navigation ever knowing what that source is.
Matches `MarkdownContentProvider` already in code.

**Control set**:
Navigation's local cache — the browser-cache half of the browser-chrome analogy above: it serves
an already-fetched document back to the same navigation task without hitting the source again,
not a shared server-side cache meant to save a different task or a later visit from re-fetching.
Every full request still runs Collection and Generation and always writes; only a follow-up page
request within one task reads the cache instead of hitting the source. One store for every
caller, not one per tool, subcommand, transport, or session. Out-of-process by necessity, not by
preference: the CLI is not a running service — it's a fresh OS process per invocation with no
memory of any prior call, so it needs external storage regardless, and an in-process cache (an
MCP server's lifespan context, a module-level dict) cannot be shared with it either way. One
SQLite database at `state_root()/control-set.db` (per-project, WAL mode), rows keyed by
`content_id` alone — no `session_id`, not a directory of loose files — with a bounded global storage budget (LRU
eviction by size, not entry count) and a periodic, rate-limited age-based cleanup pass (hourly to
daily, not on every write). Holds no authoritative data — every row is a disposable cache
Collection and Generation can rebuild on demand, so losing the whole database costs nothing but a
cold cache. See ADR-3082-1.
_Avoid_: "in-process cache" or "shared dict" as a mental model — that shape cannot satisfy
"same entry regardless of transport" no matter how carefully it's wired. Also avoid describing
this as "a directory per session" — that was ADR-3075-4's original storage mechanism, superseded
by ADR-3082-1.

**Navigate** (action):
Requesting content at a specific address from the table of contents. Matches the `navigate`
parameter and `NavigateResponse` type already in code. Distinct from the Navigation stage above —
one is the system, the other is a single request against it.
_Avoid_: "content navigation", "browse"

**Table of contents (TOC)**:
The addressable index of an item's sections. `map` is the parameter name used to request it;
"table of contents" is the concept's name in prose.
_Avoid_: "map" outside of naming the literal parameter

**Budget**:
The size limit applied exclusively at the Navigation stage when windowing a generated document
to an agent. Never applied at Collection or Generation — there is nothing to fit a budget to
until Navigation has a complete document in hand.
