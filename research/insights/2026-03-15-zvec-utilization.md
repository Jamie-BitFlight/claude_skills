# Utilization Proposals: Zvec

**Research entry**: ./research/ml-infrastructure/zvec.md
**Generated**: 2026-03-15
**Integration surfaces found**: 2 (SDK: pip package, npm package)
**Proposals written**: 3
**Skipped**: 0

---

## Utilization 1: context-gathering agent → Vector-backed retrieval

**Research entry**: ./research/ml-infrastructure/zvec.md
**Caller**: ./.claude/agents/context-gathering.md
**Integration mechanism**: pip dependency (zvec, embedding model library)
**Replaces or adds**: Enhances the agent's current Step 2 (Research Everything) by adding semantic similarity search across codebase files instead of relying solely on grep/keyword matching
**Setup cost**: Medium (requires embedding model integration; zvec itself is zero-config)
**Integration surface**: `pip install zvec`, `zvec.create_and_open()`, `collection.query(VectorQuery())`

### Why this caller

The context-gathering agent currently reads files extensively (Step 2: "Hunt down...") using grep, glob, and direct file reads to locate relevant code paths, dependencies, and configuration. This is keyword-driven matching. When searching for "authentication flows" or "caching patterns," the agent may miss semantically relevant code that uses different terminology (e.g., "auth tokens" vs "user credentials"). The agent's goal is completeness ("Your context manifest must be so complete..."), and semantic search via zvec would:

1. Enable finding related code by meaning, not just keywords
2. Cache embeddings of commonly-referenced files for fast repeated lookup
3. Return ranked results by relevance rather than boolean matches
4. Reduce redundant file reads by using an in-process vector index

The agent already states "SPARE NO TOKENS" for research completeness—semantic search aligns with this directive by improving retrieval accuracy without increasing token cost per successful find.

### Integration sketch

```python
import zvec
from typing import List

# Initialize once during agent startup
schema = zvec.CollectionSchema(
    name="codebase_semantic_index",
    vectors=zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, 1536)
)
code_index = zvec.create_and_open(path="./codebase_index", schema=schema)

# Step 2 enhancement: After identifying files to research
def find_related_code(query: str, top_k: int = 10) -> List[dict]:
    """Semantic search for related code files/snippets."""
    results = code_index.query(
        zvec.VectorQuery("embedding", vector=embed(query)),
        topk=top_k
    )
    return results  # [{'id': file_path, 'score': relevance, ...}]

# Agent usage: Instead of pure grep/glob fallback
file_matches = find_related_code("authentication and authorization flows")
# Returns: [file_path, file_path, ...] ranked by semantic similarity to query
```

**Note**: Requires selecting an embedding model (OpenAI, Sentence-Transformers, or local model). The model selection and embedding generation layer is not documented in the zvec research entry—deferred to implementation.

---

## Utilization 2: research-curator skill → Semantic indexing of research entries

**Research entry**: ./research/ml-infrastructure/zvec.md
**Caller**: ./.claude/skills/research-curator/SKILL.md (or underlying research orchestration scripts)
**Integration mechanism**: pip dependency (zvec)
**Replaces or adds**: Adds semantic search index of all research entries (currently 162+), enabling cross-reference discovery beyond the current keyword-based `research/README.md` index scanning
**Setup cost**: Low (zvec is zero-config; embedding model selection required)
**Integration surface**: `pip install zvec`, `zvec.create_and_open()`, `collection.insert(Doc(...))`, `collection.query(VectorQuery())`

### Why this caller

The research curator skill manages the research knowledge base. Currently, the `research-cross-referencer` agent scans `research/README.md` to find related entries using keyword matching and category overlap. With zvec, the curator could:

1. Index each research entry on creation (embedding the problem statement, technologies, relevance sections)
2. Provide the cross-referencer agent with semantic search results ("find entries semantically similar to this problem domain")
3. Enable researchers to ask "show me all research about vector retrieval" without manual category navigation
4. Cache embeddings in a local file-based collection so subsequent runs reuse the index

This reduces the cross-referencer's search scope from full README scanning to fast vector similarity queries—especially valuable as the research knowledge base grows beyond 162 entries.

### Integration sketch

```python
import zvec

# Research curator initialization
research_index = zvec.create_and_open(
    path="./research_vector_index",
    schema=zvec.CollectionSchema(
        name="research_entries",
        vectors=zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, 1536)
    )
)

# On new research entry creation
def index_research_entry(filepath: str, entry_title: str, entry_text: str):
    """Add entry to semantic index."""
    entry_embedding = embed_text(entry_text)  # Embed problem + features + use cases
    research_index.insert([
        zvec.Doc(
            id=filepath,
            vectors={"embedding": entry_embedding}
        )
    ])

# Cross-referencer query pattern
def find_related_entries(query_text: str, topk: int = 8) -> List[str]:
    """Find semantically related research entries."""
    query_embedding = embed_text(query_text)
    results = research_index.query(
        zvec.VectorQuery("embedding", vector=query_embedding),
        topk=topk
    )
    return [result['id'] for result in results]  # File paths
```

---

## Utilization 3: agent memory systems → Semantic retrieval of persistent memory

**Research entry**: ./research/ml-infrastructure/zvec.md
**Caller**: Agent memory implementations (e.g., `.claude/agents/typescript-pro.md` and persistent agent memory pattern)
**Integration mechanism**: pip dependency (zvec)
**Replaces or adds**: Adds semantic search over agent persistent memory files instead of requiring agents to manually search or grep their own memory
**Setup cost**: Medium (memory file organization required; zvec integration is straightforward)
**Integration surface**: `pip install zvec`, `zvec.create_and_open()`, `collection.insert()`, `collection.query()`

### Why this caller

Agents with persistent memory (typescript-pro, c-systems-programmer, etc.) currently maintain unstructured memory files and rely on manual file management ("check your memory files," "update your memory files"). With zvec, agents could:

1. Automatically index memory entries as they are created or updated
2. Perform semantic search over memory ("What have I learned about error handling patterns?") to retrieve relevant past discoveries
3. Deduplicate memory by finding similar past notes before writing new ones
4. Answer queries like "Show me all memory about [concept]" with ranked relevance

The embedding could include memory topic, key patterns, and discovery context. The agent would embed its query and retrieve relevant memory entries by similarity.

### Integration sketch

```python
import zvec
import hashlib
from pathlib import Path

# Agent-level memory indexing
agent_name = "typescript-pro"
memory_index_path = f"./.claude/agent-memory/{agent_name}/vector_index"

memory_index = zvec.create_and_open(
    path=memory_index_path,
    schema=zvec.CollectionSchema(
        name=f"{agent_name}_memory",
        vectors=zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, 1536)
    )
)

# When agent updates memory file
def index_memory_entry(memory_text: str, source_file: str, timestamp: str):
    """Add or update memory entry in semantic index."""
    entry_id = hashlib.md5(
        f"{source_file}:{timestamp}".encode()
    ).hexdigest()

    embedding = embed_text(memory_text)
    memory_index.insert([
        zvec.Doc(id=entry_id, vectors={"embedding": embedding})
    ])

# Agent query pattern: retrieve relevant past memories
def retrieve_memory(query: str, topk: int = 5) -> List[dict]:
    """Find semantically relevant memory entries."""
    query_embedding = embed_text(query)
    results = memory_index.query(
        zvec.VectorQuery("embedding", vector=query_embedding),
        topk=topk
    )
    return results  # [{id, score, ...}]

# Usage in agent: Before writing new memory, check similarity
similar_memories = retrieve_memory("error handling in async functions")
if similar_memories:
    print(f"Found {len(similar_memories)} related memories")
```

---

## Skipped Systems

No suitable callers were skipped. All evaluated candidate systems (context-gathering, research-curator, agent memory) have clear integration paths and no blocking constraints.

---

## Summary

**STATUS: complete**

Zvec is production-ready for vector-backed semantic search in three key use cases within Claude Code:

1. **Retrieval enhancement** (context-gathering agent) — semantic code discovery during task research
2. **Knowledge indexing** (research-curator) — searchable research knowledge base beyond keyword matching
3. **Memory systems** (agent persistent memory) — semantic retrieval of learned patterns and discoveries

All three proposals leverage zvec's in-process embedded architecture (no separate database service required) and straightforward Python API. The primary implementation work is embedding model selection and integration, not zvec usage itself.

The integration aligns with the documented gap in the RAG Retrieval Pattern diagram (line 359, `rag-retrieval-pattern.md`): **"No semantic search — Keyword-only matching"**. Zvec directly addresses this gap.
