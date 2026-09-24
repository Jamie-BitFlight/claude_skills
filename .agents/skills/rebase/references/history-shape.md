# History shape

Use this procedure when the replay set has a merge, a commit Git reports as empty, or an equivalent change.

1. Inspect each special commit's parents, patch, message, task intent, affected contracts, and relevant checks.
2. Assign exactly one supported disposition: preserve topology/intent, already equivalent, superseded by the
   bound transformation goal, or incompatible.
3. For a merge, account for its resolution intent as well as every parent-side change before preserving or
   flattening topology.
4. For an empty or equivalent commit, distinguish retained intent from an outcome already present or one the
   bound goal deliberately supersedes.
5. Use commit evidence, task intent, affected contracts, and passing checks as selectors. Treat apparent
   recency and side labels only as observations.
6. Continue only when every special commit has one disposition and the dispositions do not conflict.
7. Otherwise pause and report each supported alternative, its evidence, and the fact still needed to choose.
