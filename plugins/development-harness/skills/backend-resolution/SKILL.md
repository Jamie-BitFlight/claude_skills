---
name: backend-resolution
description: How to determine which backlog backend a project is configured to use, and what to do with the answer. Use when about to call a backend-specific tool, choosing between a GitHub-only and a Beads-native operation, or reporting which store a result came from.
user-invocable: false
---

# Backend Resolution

A dh project has exactly one configured backlog backend. Everything backlog-shaped — work items,
grooming, plans, task state, artifact manifests, artifact content — belongs to that one backend.
Your job is to find out which one it is before you act, and to act consistently with the answer.

<chain>

## The chain

Resolution runs in this order, first hit wins:

1. The `BACKLOG_BACKEND` environment variable, when set to a non-empty value.
2. `backlog.backend` in `.dh/config.yaml`.
3. `backend.name` in the same file — the global fallback, checked only when the subsystem key
   above is absent. Steps 2 and 3 are applied per config file, in the config search order, so a
   nearer file's global key wins over a farther file's subsystem key.
4. The `.beads/dh-backend` **marker file**. Its presence, and nothing else, opts a project into
   the Beads backend.
5. Otherwise `github`.

`create_backend()` in `backlog_core/backend_protocol.py` is the implementation; it delegates the
chain to `DHConfig.get_backend(subsystem="backlog")` in `dh_config.py`, and `_auto_detect_beads()`
implements step 4. `docs/backend-providers.md` under "One configured backend" is the canonical
description of the contract — read it when you need the storage model, per-backend capabilities,
or the cache and revision rules rather than the resolution procedure.

</chain>

## Do not re-derive this

Resolve the backend by reading the chain above and applying it in full, or by asking the harness
for the answer. Do not write your own detection snippet. Two shapes have already shipped in agent
prompts and both returned a confidently wrong answer:

- **Stopping at the environment variable.** A heuristic that reads `BACKLOG_BACKEND`, then falls
  through to a default, never consults `.dh/config.yaml`. In a project that configures its backend
  there — the normal case, since the environment variable is the override, not the setting — it
  reports the default while the rest of the plugin uses the configured backend.
- **Testing for a `.beads` directory instead of the marker.** Step 4 requires the file
  `.beads/dh-backend`. The directory alone is explicitly not sufficient: a project may keep a
  `.beads` directory for other purposes without intending to use the Beads backlog backend. A
  heuristic that tests the directory reads such a project as Beads even when it configures
  `github`.

Both failures are silent. Nothing errors, no tool refuses the call — you get a different backend
than the rest of the process is using, and you then report that backend's answer as the project's.
That is why this is a skill rather than a paragraph in each agent: a rule copied into several
prompts drifts, and each copy fails this way independently.

## Acting on the answer

**Before a backend-specific call.** Some operations exist only on some backends. `docs/backend-providers.md`
carries the per-backend capability table and the `supports_*` flags; consult it rather than
probing behavior or catching an exception to find out. When the resolved backend cannot do what a
step needs, say so and stop that step — do not substitute a filesystem read, a cache read, or a
second backend.

**When a capability is missing.** Report the gap in the output the step was going to fill, in the
place a reader will look for the result. "Not applicable — backend does not support this
capability" tells a reader the check did not run. Silently omitting the section tells them
nothing, and reads identically to a check that ran and found nothing.

**When you report a result.** A result is a fact about one backend. If which backend produced it
could change how a reader acts, name it.

## Identifier shapes

`issue_number` is not always an integer. On `beads` it is a bead ID — a string such as `bd-a3f8`.
The MCP layer accepts both types transparently, so this matters when you parse, format, sort, or
pattern-match an identifier yourself, not when you pass one through.
