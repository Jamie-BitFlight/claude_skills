# Summarizer architecture

The [purpose](./PURPOSE.md) defines outcomes. [Change-contract evaluation](./evals/change-contract.md)
records the pre-change comparison criteria and original semantic inventory.

## Responsibilities

| Component | Owns | Does not establish |
| --- | --- | --- |
| summarizer skill | Request scope, transport/media routing, format and coordination | Source contents from metadata |
| source skills | Type-specific acquisition/extraction and coverage | User intent different from the request |
| agent adapters | Loading the canonical source method in a delegated context | A second copy of the methodology |
| fidelity/execution references | Shared meaning, handoff and completion requirements | Automatic semantic correctness |
| summary_record.py | Versioned record schema, reference checks and caller/output identity | Actual source access or factual support |
| source_tools.py | Complete text partitions, receipt reconciliation and full CSV/TSV aggregates | Agent comprehension or universal streaming performance |
| templates | The selected presentation | Different truth/coverage rules |
| output-contract.cjs | Structural checks and a host-independent CLI | Complete YAML parsing or semantic fidelity |
| SubagentStop hook | Claude payload adaptation and one correction opportunity | A fail-closed acceptance boundary |
| caller | Final artifact validation, status adjudication and worker lifecycle | Success from an unperformed check |

Normal flow: request -> acquisition/coverage -> evidence findings -> optional synthesis -> selected
presentation -> final record/structure/evidence checks -> caller return. Error paths preserve exact
reasons and incomplete scope instead of joining a successful terminal state silently.

## Canonical resources

Runtime rules stay at the established `skills/summarizer/references/` paths to preserve existing
consumers. Each source skill explicitly loads shared contracts; each agent loads its source skill.
A short inline summary need not create a sidecar. Delegated, chunked, multi-source and audited work
use caller-assigned evidence/output paths. The Pydantic model emits its schema; no second checked-in
schema must drift with it. The evidence validator reads only explicit record/output paths and does
not execute or fetch locations contained in a record.

## Validation boundaries

Output structure and evidence-record consistency are distinct checks. Their result names are
`STRUCTURE_VALID` and `RECORD_VALID`, not verified fidelity. A digest binds the record to the
rendered output at check time; later mutation requires revalidation. It is not an authenticity
signature. An author can still write a self-consistent false claim, so consequential semantic
support requires raw-evidence review independently of the author.

The hook intentionally fails open with a visible NOT_VALIDATED notice when payload metadata or
artifacts cannot be inspected, or one correction was exhausted. The caller must run explicit final
checks before accepting DONE. A host without hooks uses those same checks; that is a documented
execution path, not measured parity. No installed-host smoke result is claimed by these sources.
