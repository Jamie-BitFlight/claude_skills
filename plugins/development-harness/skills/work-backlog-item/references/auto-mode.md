# Auto Mode Rules

When `$0` is `--auto`, the following substitutions apply at every interactive decision point:

| Normal behaviour | `--auto` substitution |
|---|---|
| No title given (`$1` is empty) | Call `mcp__plugin_dh_backlog__backlog_list` and scan P0 then P1 sections for the first open item. Log `[AUTO] No title — auto-selected: {title}` and proceed. If none found, log `[AUTO] STOP — no open P0/P1 items found` and stop. |
| No title given and no open P0/P1 items found | Log `[AUTO] STOP — no open P0/P1 items found`, stop. Do not attempt to create a new item. |
| Auto-selected P0/P1 item already has RT-ICA BLOCKED status | Log `[AUTO] STOP — RT-ICA BLOCKED on auto-selected item: {title}. {missing inputs}`, stop. Cannot resolve without human — select a different item manually. |
| Step 1.2: issue not found | Log `[AUTO] STOP — Issue #N not found`, stop |
| Step 1.3: zero matches → ask user to create | Auto-invoke `create-backlog-item --auto {title}`, log `[AUTO] No item found — invoking create-backlog-item --auto`. If `create-backlog-item --auto` itself fails (e.g., GitHub issue creation error, invalid title), log `[AUTO] STOP — create-backlog-item --auto failed: {error}` and stop. |
| Step 1: multiple matches → ask user to pick | Log `[AUTO] Multiple matches — picking first: {title}`, proceed with first match |
| Step 2.2: offer GitHub issue for P0/P1 | Log `[AUTO] Skipping GitHub issue offer`, continue without issue |
| Step 2.2: ask milestone assignment | Log `[AUTO] Skipping milestone assignment`, skip |
| RT-ICA BLOCKED | Log `[AUTO] STOP — RT-ICA BLOCKED: {missing inputs}`, stop (cannot resolve without human) |
| Step 3.4: Feasibility WARN (effort absent) | Log `[AUTO] WARN: effort not estimated — proceeding`, continue |
| Step 3.4: Feasibility WARN (over 10 systems) | Log `[AUTO] WARN: high blast radius ({N} systems) — proceeding`, continue |
| Step 3.4: Feasibility WARN (prior attempt) | Log `[AUTO] WARN: prior attempt referenced — including in feature request`, continue |
| Step 3.4: Feasibility BLOCKED (any criterion) | Log `[AUTO] STOP — feasibility blocked: {criterion}`, stop |
| Step 5.1–5.7 interactive questions (summary, method, notes, follow_ups, findings) | Log `[AUTO] Decision: {chosen option} — reason: {evidence}`, proceed with agent-derived values for each field |
| Step 3.1: Phase 2 agent returns `FUNCTIONAL_DRIFT` | Log `[AUTO] STALENESS: FUNCTIONAL_DRIFT — {one-line reason from diff}`. Write 'staleness context' section via `backlog_groom`, invoke `groom-backlog-item`, proceed to Step 3.2. |
| Step 3.1: Phase 2 agent returns `SUPERSEDED` | Log `[AUTO] STALENESS: SUPERSEDED — {commit refs}`. Call `backlog_close(reason='superseded', comment='{commits}')`. Stop — do not proceed to planning. |
| Step 3.1: Phase 2 agent returns `COSMETIC_ONLY` | Log `[AUTO] STALENESS: COSMETIC_ONLY — cached groom content valid`. Proceed to Step 3.2 without re-grooming. |
| Any other `AskUserQuestion` | Log `[AUTO] Decision: {chosen option} — reason: {evidence}`, proceed with logged choice |

`--auto` does NOT change the behaviour of Steps 3.2–4.5 (RT-ICA evaluation, SAM planning, backlog update) — those are already agent-executable without human input. Step 3.1 staleness outcomes are now handled by the explicit rows above.
