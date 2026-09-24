# Knowledge Representation & Ontology Modeling
*(Course lectures 2-3, translated and adapted)*

## Contents
- [Choosing a representation](#choosing-a-representation)
- [Ontology engineering method](#ontology-engineering-method)
- [Schema design rules](#schema-design-rules)
- [Worked example](#worked-example)
- [Ontology learning](#ontology-learning)

## Choosing a representation

The course surveys the historical inventory — semantic networks, production rules, frames,
conceptual graphs, formal concept analysis, description logic — converging on two survivors
plus one pragmatic shortcut:

| Representation | Choose when | Cost |
|---|---|---|
| **Property graph** (Neo4j, Kùzu, NetworkX) | Default for products and agent memory. Nodes/edges with arbitrary key-value properties. | No formal semantics; consistency is your job. |
| **RDF/OWL triples** | Interop with existing ontologies, standards compliance, need for description-logic reasoning (subsumption, consistency checking). | Verbose; reification needed for edge properties; steeper tooling. |
| **Typed edges in JSON/SQLite** | <50K nodes, single application, agent-local memory. | Query power capped; migrate when multi-hop queries get slow or frequent. |

Decide at this stage how assertions carry identity, time, and evidence when those dimensions matter:

- **Canonical identity** — the entity or event the assertion is about.
- **Valid time** — when the asserted state is true, distinct from when it was observed.
- **Observation/extraction time** — when the source was seen or processed.
- **Provenance** — source pointer plus extraction/observation method and confidence where useful.

Do not assume provenance belongs only on a canonical node or edge. When multiple sources can support,
contradict, or supersede the same fact, model the assertion/observation as the provenance-bearing unit
(or use an equivalent edge-assertion representation). Preserve enough evidence to explain a merge,
retraction, temporal change, or answer.

## Ontology engineering method

Condensed from the course's ontology-engineering process:

1. **Competency questions.** Write representative questions the graph must answer
   ("Which suppliers does product X depend on transitively?"). These are the graph's specification
   and end-to-end acceptance cases. Choose enough to cover materially different query shapes; do not
   impose a fixed count when a smaller or larger set better represents the system.
2. **Enumerate core entity types** from the competency questions. Start with the smallest set that
   answers them. Give each type a concise definition and representative examples where examples reduce ambiguity.
3. **Enumerate relation types** with **domain and range** (e.g. `EMPLOYED_BY: Person → Org`).
   Add only relations required by the competency questions and cardinality/constraint rules where
   violating them would change correctness.
4. **Attributes vs entities.** If it has its own relationships, it's an entity ("City" — has
   country, population). If it's a value you filter on, it's an attribute ("founding year").
5. **Type hierarchy only when queries need it.** `Company ⊂ Organization` is worth having if
   some queries span all organizations; otherwise skip subclassing — flat is easier to extract
   against.
6. **Validate against the competency questions** — walk each question through the schema on
   paper. Any question you can't path through the schema = missing type or relation.

## Schema design rules

- Precise verb names for relations: `ACQUIRED`, `CITES`, `DEPENDS_ON` — never `RELATED_TO`,
  `HAS_LINK`. Vague relations make every downstream query ambiguous.
- If two entity types are always queried together, merge them into one.
- If one entity type keeps needing qualifier attributes to disambiguate usage
  (`role: "author" | "editor"`), split it into two relation types instead.
- Name entities canonically at modeling time (define the canonical-form rule: full legal name?
  lowercase? language?) — fusion (stage 8) enforces whatever rule you state here.
- Keep an `ontology.md` (or `.yaml`) file in the project as the single source of truth; every
  extraction prompt embeds it verbatim.

## Worked example

Competency question: "Which engineers contributed to services that had incidents last quarter?"

```yaml
entities:
  Person:   {desc: engineer or manager, ex: [Jane Doe]}
  Service:  {desc: deployable software unit, ex: [payments-api]}
  Incident: {desc: production failure event, ex: [INC-4012]}
relations:
  CONTRIBUTED_TO: {domain: Person,  range: Service}
  AFFECTED:       {domain: Incident, range: Service, attrs: [severity]}
events:
  Incident: {trigger: outage/alert, args: [service, start_time, resolved_time, severity]}
```

Three types, two relations, one event type — fully answers the question. Resist adding more
until a competency question demands it.

## Ontology learning

The course covers semi-automatic schema induction (terms → concepts → hierarchy → relations).
LLM-era shortcut that preserves the same discipline: give an LLM 3-5 representative documents,
ask it to propose entity/relation types **with evidence quotes**, then manually prune to the
minimal set that answers the competency questions. Never auto-accept an induced schema —
induced ontologies overfit the sample documents.
