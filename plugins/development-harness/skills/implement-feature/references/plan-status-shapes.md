# Which Shape `plan status` Answered In

`plan status` answers from whichever store holds the plan, and the two stores answer in shapes that
share field names while disagreeing about where those fields sit. Tell them apart by the top-level
`row` key — the same discriminator `dh:context-refinement` uses.

## The ledger shape — a top-level `row` key is present

Every plan-level field is inside `row`: `row.autonomy`, `row.base_sha`, `row.context`, `row.feature`,
`row.issue`, `row.milestone`, and the rest of the plan's columns.

`tasks` is an array of task rows, each carrying its stored columns and its derived ones together —
`ready`, `status`, `accepted`, `attempts`, `attempts_allowed`, `stale`, `expired`, `returned`.

The plan-level `progress` is a word, not a percentage: `open`, `done`, `failed` or `archived`. It is
`done` when every task is accepted, deferred or skipped; `failed` when nothing is left outstanding
and at least one task failed; `archived` when the plan is archived; `open` otherwise.

There is no completion percentage and no top-level ready list. Both are derived from `tasks`: count
the rows that are done under the `progress` rule above, and take the rows whose `ready` is true.

## The content shape — no `row` key

A `feature` / `total_tasks` / `by_status` / `ready_tasks` / `blocked_tasks` / `completion_pct` /
`has_cycles` / `issue` / `autonomy` / `state` shape instead. Every plan-level field is at the top
level, and the response carries no per-task array at all — `--all` on this path widens the answer to
every plan, not to every task. It carries no `base_sha` field in any form.

## Why the discriminator is not optional

The names overlap, so a read written for one shape does not fail against the other — it returns
nothing. `autonomy`, `completion_pct` and `ready_tasks` are all top-level on the content store and
all absent from the top level of the ledger, and a reader that treats an absent key as a default
silently substitutes one. Where the key gates a confirmation, that substitution is a gate that never
fires and nothing raises.

The two response models are separate classes that happen to share a name —
`dh_core.ledger.queries.PlanStatus` and `sam_schema.core.models.PlanStatus` — so nothing in the
code makes the divergence visible either. Check `row` before reading any plan-level field.

## Where each shape appears in this skill

`implement-feature` runs `plan import --from content` before the Progress Loop, so the "Resolve
Plan" status is the content shape and every status from the import onward is the ledger shape. A
skill that reads a plan at an unknown point in its life — `dh:context-refinement` is the worked
example — has to run the discriminator every time instead.
