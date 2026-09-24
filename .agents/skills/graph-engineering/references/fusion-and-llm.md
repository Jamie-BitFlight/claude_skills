# Knowledge Fusion & Serving the Graph to LLMs
*(Course lectures 8-9, translated and adapted)*

## Contents
- [Why fusion is the make-or-break stage](#why-fusion-is-the-make-or-break-stage)
- [The fusion pipeline](#the-fusion-pipeline)
- [Ontology matching](#ontology-matching)
- [KG for LLM](#kg-for-llm)
- [LLM for KG](#llm-for-kg)
- [Graph-as-memory loop](#graph-as-memory-loop)

## Why fusion is the make-or-break stage

(Lecture 8.) Every extraction pass produces duplicates: "SEU", "Southeast University",
"东南大学" are one university; "Bob Smith (doc 3)" and "Robert Smith (doc 41)" may or may not
be one person. An unfused graph can answer multi-hop queries incorrectly because paths break at duplicate
identity boundaries. Treat fusion quality as an end-to-end concern and measure its effect on the
competency questions rather than assuming one universal dominant failure mode.

## The fusion pipeline

Three steps, from the course's large-scale entity-matching material:

1. **Blocking** — never compare all pairs (O(n²)). Group candidates cheaply first: same type +
   (shared token | matching acronym expansion | embedding similarity above threshold | same
   normalized key). Only pairs within a block get full comparison.
2. **Matching** — score candidate pairs on layered evidence:
   - String layer: normalized/alias/acronym match.
   - Attribute layer: compatible attributes (same founding year, same email domain).
   - **Structure layer** (the course's emphasis, and what naive dedup misses): compare
     neighborhoods — two "J. Smith" nodes sharing 3 coauthors and an affiliation are the same
     person; identical names with disjoint neighborhoods are not.
   - LLM adjudication for the ambiguous middle band only (cheap heuristics for the clear
     cases; the model sees both nodes' attributes + neighborhoods + evidence quotes).
3. **Merge policy** — deterministic code, not model judgment: keep canonical name, union
   aliases and edges, keep per-source attribute values with provenance when they conflict
   (do NOT silently overwrite — conflicting values are signal), record `merged_from` for undo.

Use separate auto-merge, auto-reject, and review/adjudication regions when automated identity
resolution is appropriate. Derive thresholds from labeled examples and the relative cost of false
merges versus missed merges; do not copy a universal confidence cutoff. Preserve merge evidence and
make consequential merges reversible where practical.

## Ontology matching

When fusing two graphs (not just instances), align schemas first: map entity types and
relation types between sources (course: 本体匹配 + match tuning). Practical order — align
types by name+definition with an LLM, verify with instance overlap (if source A's `Firm` nodes
mostly match source B's `Company` nodes, the type mapping is confirmed), then translate
source B's edges through the mapping before instance fusion.

## KG for LLM

(Lecture 9, direction 1.) Making the graph reduce hallucination and extend context:

- **GraphRAG retrieval:** entity-link the query → retrieve candidate paths/subgraphs → rank/prune
  against the query → serialize compact evidence-bearing facts/paths with provenance. Treat hop
  depth as a retrieval parameter: tune it against competency questions and graph density rather
  than assuming a fixed depth.
- **Serialization that works:** `(head)-[REL {time, source}]->(tail)` lines, grouped by head
  entity, deduplicated. Tables of triples beat prose summaries — the LLM can quote exact facts.
- **Multi-hop questions:** retrieve *paths* between the query's entities, not neighborhoods
  around each. The path IS the answer skeleton; the LLM narrates it.
- **Community summaries** for "what are the big themes" questions: cluster the graph,
  summarize per cluster offline, retrieve summaries at query time.

## LLM for KG

(Lecture 9, direction 2.) Already embedded in stages 3-8 of the pipeline: schema induction
(with human pruning), extraction (with ontology constraints + evidence quotes), fusion
adjudication (middle band only). The course's framing to keep: the LLM is a component inside
each stage with validation around it — not a replacement for the pipeline.

## Graph-as-memory loop

For agents that accumulate knowledge across sessions:

1. After each session/task, run extraction (stages 4-6) over new information with the same
   ontology.
2. Fuse new facts into the existing graph (stage 8) — same blocking/matching/merge machinery,
   incremental.
3. At session start or on demand, retrieve via GraphRAG (above) instead of dumping the whole
   graph into context.
4. **Contradiction handling:** when assertions conflict, retain the competing assertions with
   provenance and temporal semantics. Resolve at retrieval using the domain's authority, valid-time,
   observation-time, and confidence rules; recency alone is not a universal truth criterion.
5. Periodic hygiene pass: re-run fusion over the full graph and re-score stale confidences.
   Unmaintained memory graphs rot the same way unfused extractions do.


## End-to-end evaluation

Evaluate serving against the competency questions established during modeling. Keep these dimensions
separate so a strong result in one cannot hide a failure in another:

- identity/entity-linking correctness;
- path/subgraph retrieval relevance and evidence coverage;
- query/answer correctness;
- provenance traceability;
- temporal/contradiction handling where applicable;
- latency, context size, and cost telemetry.

Use failure cases to decide whether the correction belongs in schema, extraction, fusion, storage/query,
retrieval, or answer generation rather than patching the final prose response.
