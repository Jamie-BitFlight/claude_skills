# Evidence record and synthesis handoff

Use an evidence record for delegated, chunked, multi-source or audit-requested work. A short
inline summary may keep the same source/claim/coverage distinctions in context without writing
a sidecar. Do not impose a persistent artifact on a task that has no handoff or audit need.

The caller assigns a request ID, source inventory, format, summary path and evidence path before
dispatch. Pass these as task inputs; workers do not choose a different source set or reuse a cached
result as if it belonged to this request. Use distinct paths per worker and a separate synthesis
record. Preserve caller-specific status vocabulary rather than defining a new work-status protocol.

## Schema authority

Read the schema from the bundled model, not an independently maintained copy:

```bash
uv run --script "<plugin-root>/scripts/summary_record.py" schema
```

The record contains source identity/transport/media type/revision, inspected and omitted scope,
findings with claim-level support locations and qualifiers, selected findings, typed gaps,
conflicts, confidence rationale, and the digest/format of the delivered summary.
Use `null` for an unavailable source revision, with the acquisition limitation in coverage.
Do not invent hashes, counts, section totals or access dates. Obtain the output digest mechanically:

```bash
uv run --script "<plugin-root>/scripts/summary_record.py" digest "<summary-path>"
```

`complete` refers to the declared source scope, not the whole repository/site or the truth of its
contents. Require inspected locations and no omissions. `partial` requires both inspected and
omitted locations plus a reason. `unavailable` has no inspected locations and preserves the exact
failure reason. An empty readable source may record `empty file inspected` rather than inventing
content. Keep searched-absent, inaccessible and not-assessed gaps distinct.

## Build and consume

Extract independently meaningful findings before rendering. Keep each claim's conditions, units,
dates, versions, exceptions and attribution with its support. An excerpt is optional: retain a
resolvable source location, not unnecessary copies of sensitive material. Mark inferred conclusions
as inferred and retain their supporting observations.

For a requested merge, compare subject, predicate, scope, conditions, time/version and units before
deduplicating. A source supporting `100 requests/minute` does not also support `per key` unless that
qualification is present. Keep different support sets as separate findings or clauses. Record
shared origin when sources copy one original; apparent agreement is not independent corroboration.

Keep material omissions and conflicts visible in every output format. `selected_findings` identifies
the findings used in the presentation; it is not permission to hide a material qualification.
Semantic review must check both selected claims and consequential unselected evidence.

After rendering, fill the output digest and validate against caller-supplied expectations:

```bash
uv run --script "<plugin-root>/scripts/summary_record.py" validate "<evidence-path>" \
  --request-id "<caller-request-id>" --source "<exact-source-path>" \
  --output "<summary-path>" --format "<format-id>"
```

Repeat `--source` for each expected source, including failed sources. The validator never opens
source paths from a record; it checks their inventory against the caller and reads only the explicit
record/output arguments. Exit 0 means `RECORD_VALID`, with separate complete/partial coverage;
exit 1 is invalid and exit 2 is unverified. This checks schema, references and output identity,
not that the source was actually read or that a claim is true. Review raw evidence independently
where consequential. If the script/dependency is unavailable, report validation as unverified;
do not install packages or claim success without the host's permission/capability.

Run output-format validation as well, using the [execution contract](./execution-contract.md).
The caller repeats final checks after synthesis/relay transformations; changed output bytes invalidate
the previous record. Never treat a worker's passing checks as evidence for a different final artifact.
