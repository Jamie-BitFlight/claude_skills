The purpose and explicit goals of the skill boil:

1. Complete tasks fully in a single pass — deliver the finished, working result rather than a plan, partial implementation, or "add tests/edge-cases later" deferral
2. Eliminate prohibited exits (tabling work, cosmetic workarounds, "exercise for the reader") in favor of the permanent, root-cause solve whenever it is reachable
3. Prevent silent data loss from invented content limits (hard-coded slices, MAX_LEN constants, truncation flags) — output full content by default, with explicit pagination and truncation disclosure when shortening is unavoidable
4. Surface pre-existing issues found mid-task as an explicit act-or-backlog decision point, instead of dismissing them as out of scope
5. Enforce a bounded, high-integrity escape hatch (the BLOCKED declaration) for the rare case where a genuine external constraint — not difficulty or uncertainty — makes the permanent solve unreachable, requiring named constraint, completed work, remaining steps, and an observable unblocking condition
6. Provide a self-review gate (Dangling Thread Checklist) run before marking any task complete, catching open TODOs, workarounds, unsearched/untested work, and truncation before they ship
