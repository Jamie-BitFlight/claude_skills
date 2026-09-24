# History shape

Use this procedure when the replay set has a merge, a commit Git reports as empty, or an equivalent change.

1. Inspect each special commit's parents, patch, message, intent, affected contracts, and relevant checks.
2. Assign one state-specific action: fresh-start topology, preserve/continue active topology or commit, skip
   current active commit as equivalent/superseded, or incompatible.
3. For a merge, account for resolution intent and every parent-side change before choosing topology.
4. For an empty or equivalent commit, distinguish retained intent from an outcome already present or one the
   bound goal deliberately supersedes.
5. Use commit/task evidence, affected contracts, and passing checks; recency and side labels are observations.
6. Return only the matching router action; active metadata never routes to a fresh replay start.
7. Continue only when every special commit has one disposition and the dispositions do not conflict.
8. Otherwise pause and report each supported alternative, its evidence, and the fact still needed to choose.
