# Utilization Proposals: Samuraizer

**Research entry**: ./research/ai-research-tools/samuraizer.md
**Generated**: 2026-03-25
**Integration surfaces found**: 3 (API: /analyze, /search/semantic, /chat)
**Proposals written**: 1
**Skipped**: 2 — individual agents not suitable standalone callers; workflow-level integration is the correct unit of analysis

---

## Utilization 1: research-curator workflow → Samuraizer

**Research entry**: ./research/ai-research-tools/samuraizer.md
**Caller**: `.claude/agents/research-curator.md` + `.claude/skills/research-curator/SKILL.md`
**Integration mechanism**: API call (self-hosted REST)
**Replaces or adds**: Replaces the current markdown-file + Grep/Glob storage and retrieval
architecture with a purpose-built knowledge base providing vector embeddings, semantic search,
and RAG chat over the research corpus.
**Setup cost**: High (requires a self-hosted Samuraizer instance with Gemini API key and
SQLite database; cannot be used as a stateless dependency)
**Integration surface**: `POST /analyze` (URL ingestion with LLM summary), `GET /search/semantic`
(vector similarity search), `POST /chat` (RAG over stored entries)

### Why this caller

The research-curator workflow (curator agent + cross-referencer + insight-extractor + README.md
index) is a hand-built knowledge base: entries are written as markdown files, retrieval is done
via Grep/Glob pattern matching across 162+ files, and cross-references are found by keyword
scoring. This is a weaker implementation of exactly what Samuraizer provides as a product:
URL ingestion with LLM summarization, SQLite storage with vector embeddings, semantic search
that finds conceptually related entries without keyword overlap, and RAG chat over the full
corpus.

The `@research-cross-referencer` agent is the most directly affected component: it currently
scores 162+ entries by keyword overlap (scoring documented in
`.claude/agents/research-cross-referencer.md`). Samuraizer's `GET /search/semantic` endpoint
would surface conceptually related entries even when terminology differs — the gap that
keyword scoring cannot close.

The `@research-curator` agent's `WebFetch` + `Write` cycle (fetch URL, extract content, write
markdown) maps directly to Samuraizer's `POST /analyze` endpoint, which performs the same
fetch-extract-summarize pipeline and stores the result in a queryable database.

SOURCE: `research/ai-research-tools/samuraizer.md` §API Reference, §Architecture (accessed
2026-03-25); `.claude/agents/research-cross-referencer.md` §Scoring Reference (read
2026-03-25).

### Integration sketch

```python
# Current pattern (research-curator agent):
# 1. WebFetch(url) → raw HTML
# 2. Extract key sections manually
# 3. Write(research/{category}/{name}.md, content)
# 4. Grep/Glob to find cross-references (keyword scoring)

# With Samuraizer as backend:
# 1. POST /analyze — Samuraizer fetches, extracts, summarizes, stores
import httpx
response = httpx.post(
    f"{SAMURAIZER_URL}/analyze",
    json={"url": "https://github.com/zomry1/Samuraizer", "tags": ["ai-research-tools"]}
)
entry_id = response.json()["id"]

# 2. GET /search/semantic — replace Grep/Glob cross-referencing
results = httpx.get(
    f"{SAMURAIZER_URL}/search/semantic",
    params={"q": "vector search knowledge base security research", "limit": 8}
).json()
# Returns semantically similar entries without keyword matching

# 3. POST /chat — RAG over full corpus (no current equivalent)
answer = httpx.post(
    f"{SAMURAIZER_URL}/chat",
    json={"message": "Which entries cover RAG architecture patterns?"}
).json()
```

API endpoints are documented in `research/ai-research-tools/samuraizer.md` §API Reference.
No invented surfaces — all endpoints verified against `server.py` (2,736 lines, read by
research-curator agent 2026-03-25).

### Adoption path

1. **Prototype**: Deploy Samuraizer locally alongside the existing markdown workflow. Run both
   in parallel for one research session to compare cross-reference quality.
2. **Evaluate**: Compare `@research-cross-referencer` keyword-scored results against Samuraizer
   `/search/semantic` results for the same entry. Measure recall improvement on entries where
   terminology differs.
3. **Migrate or augment**: Either replace the Grep/Glob cross-reference step (breaking change
   requiring Samuraizer instance always available) or augment it (call semantic search as
   tiebreaker when keyword scoring returns < 3 candidates).

**Constraint**: Samuraizer requires a running Flask server with persistent SQLite state.
This makes it infrastructure, not a stateless tool dependency. The research-curator workflow
would need to treat Samuraizer as an optional backend (graceful degradation to markdown+Grep
when unavailable).

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/agents/research-curator.md` (standalone) | The agent itself is a suitable caller only as part of the full workflow — assessed at workflow level above. |
| `.claude/agents/research-cross-referencer.md` (standalone) | Cross-referencer is the highest-value integration point but replacing it in isolation (while research-curator still writes markdown) creates an inconsistent hybrid. Workflow-level integration is the correct unit. |
