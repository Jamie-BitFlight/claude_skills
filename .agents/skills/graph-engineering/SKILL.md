---
name: graph-engineering
description: Design, build, evaluate, or teach graph-based systems. Use for knowledge graphs, ontology/schema design, entity/relation/event extraction, entity resolution and fusion, GraphRAG or graph memory, and agent/task dependency graphs with concurrency, joins, failure handling, verification, or human gates.
---

# Graph Engineering

Use graph structure only when relationships, paths, recurring identity, or execution dependencies are central to the problem. Prefer a simpler table, document index, vector search, or serial workflow when it satisfies the required questions or execution contract.

## Route the request

Choose the branch that matches the user's outcome:

- **Knowledge graph** — model and serve durable knowledge. Follow the knowledge-graph lifecycle below and load only the reference for the current stage.
- **Task graph** — model work, dependencies, data flow, readiness, failure, verification, and approval. Read [references/task-graphs.md](./references/task-graphs.md).
- **Learning** — teach only the relevant branch. Establish the learner's goal and current understanding, use their domain when available, and alternate concept → worked example → learner application → feedback. Visualize topology when it materially improves understanding; do not force the entire lifecycle when the user asks about one part.

## Knowledge-graph lifecycle

Treat competency questions as the graph's specification and end-to-end acceptance tests.

1. **Define value and competency questions.** Write representative questions the system must answer. Stop if a simpler representation answers them adequately.
2. **Choose representation and fact semantics.** Select property graph, RDF/OWL, or a simpler typed-edge representation. Define identity, temporal semantics, and how assertions retain evidence/provenance. Read [references/modeling.md](./references/modeling.md).
3. **Model the minimal ontology.** Define only the entity, relation, event, and constraint vocabulary required by the competency questions. Validate that each question has a plausible path through the schema.
4. **Map or extract source data.** Prefer deterministic mappings for structured data; use constrained extraction for open text. Separate entity, relation, and event extraction when doing so improves validation. Read [references/extraction.md](./references/extraction.md).
5. **Evaluate extraction.** Sample representative sources and measure the error dimensions that matter to the application. Set acceptance thresholds from consequence, source variability, and downstream cost rather than a universal fixed percentage.
6. **Resolve identity and fuse assertions.** Block candidate matches, compare identity evidence, preserve conflicting assertions and their provenance, and make merges reversible where practical. Read [references/fusion-and-llm.md](./references/fusion-and-llm.md).
7. **Store, query, and operate.** Choose storage and indexes from expected graph size, query shapes, update rate, consistency needs, access boundaries, and operational constraints. Define incremental ingestion, retraction/deletion, schema evolution, and integrity checks when the system persists beyond a prototype.
8. **Serve the graph.** For GraphRAG or memory, retrieve the smallest evidence-bearing subgraph or paths that answer the query. Keep retrieval strategy configurable and evaluate it against the competency questions rather than assuming a fixed hop count. Read [references/fusion-and-llm.md](./references/fusion-and-llm.md).
9. **Run end-to-end evaluation.** Execute the competency questions against the resulting system. Separate extraction quality, identity/fusion quality, retrieval/query quality, answer correctness, and operational telemetry so one metric cannot hide another's failure.

For academic background or the translated source-course map, read [references/curriculum.md](./references/curriculum.md).

## Knowledge-graph invariants

- Preserve evidence for assertions strongly enough to trace an answer or merge decision back to its source.
- Keep canonical entity identity separate from individual observations/assertions when multiple sources, changing facts, or contradictions matter.
- Validate relation/event types against the ontology where the ontology defines those constraints.
- Do not silently overwrite conflicting source claims during fusion.
- Treat LLMs as fallible components inside extraction, schema induction, adjudication, retrieval, or reasoning; validate their outputs at the boundary where an error becomes consequential.
- Pilot the complete path on representative data before scaling when scaling would make correction materially more expensive.

## Choosing instruction strength

Do not turn useful defaults into universal laws.

- **Invariant** — required to preserve the user's contract or prevent a consequential failure.
- **Default** — preferred when evidence and context do not indicate otherwise.
- **Heuristic** — a starting point to tune or evaluate.
- **Example parameter** — illustrative only; do not promote it to an acceptance threshold without evidence.

When a numeric threshold, hop count, sample size, agent cap, or retry limit matters, derive or validate it against the current system's consequence and evidence.

## Teaching artifacts

Generate diagrams or starter artifacts only when they advance the learner's stated goal. Useful outputs include an ontology, competency-question set, example subgraph, task DAG, or evaluation plan. Keep Mermaid as a compact representation of a semantic model, not proof that the model is correct.

## Reference map

- [references/modeling.md](./references/modeling.md) — representation, competency questions, ontology and assertion/provenance modeling.
- [references/extraction.md](./references/extraction.md) — structured mapping plus entity, relation, and event extraction.
- [references/fusion-and-llm.md](./references/fusion-and-llm.md) — identity resolution, fusion, GraphRAG, graph memory, and serving/evaluation.
- [references/task-graphs.md](./references/task-graphs.md) — task-node/edge contracts, readiness, concurrency, joins, failure/recovery, verification, human gates, and runtime projection.
- [references/curriculum.md](./references/curriculum.md) — translated academic source map; load for theory depth or provenance.

## Credits

Knowledge-graph material is distilled and adapted from Southeast University’s graduate Knowledge Graph course by Prof. Peng Wang: <https://github.com/npubird/KnowledgeGraphCourse>.
