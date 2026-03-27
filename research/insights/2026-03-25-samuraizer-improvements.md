# Improvement Proposals: Samuraizer

**Research entry**: ./research/ai-research-tools/samuraizer.md
**Generated**: 2026-03-25
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Multi-modal content handling (PDF/video extraction for research-curator) | Low | The research-curator agent (`.claude/agents/research-curator.md`) has no PDF or video/transcript extraction capability. Samuraizer uses PyMuPDF for PDF text extraction and transcriptapi.com for YouTube transcripts. However, the research-curator is designed to research tools/libraries by reading documentation and source code via MCP tools and shallow clones -- not arbitrary PDFs or videos. The gap is real but the mechanism does not map cleanly: adding PyMuPDF-based PDF extraction to the research-curator would change its purpose (from researching tools to ingesting arbitrary documents). To raise confidence, one would need to verify: (1) how often research targets publish documentation only as PDFs, (2) whether existing MCP URL-reading tools already extract text from PDF URLs, and (3) whether the research-curator's scope should expand to cover non-web documentation formats. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Security research agents (extraction pipeline) | Too abstract for this repo. Samuraizer is a web application for security researchers; the local repo produces Claude Code plugins and skills. The extraction pipeline pattern (Trafilatura, PyMuPDF, Gemini summarization) describes a product feature, not a workflow or skill pattern that maps to any local system. |
| Knowledge base for AI agents (semantic search + RAG chat) | Implementing semantic search over research entries would require replacing the current architecture (markdown files searched via Grep/Glob) with a vector database and embedding pipeline. This violates gap rule 4: it would require replacing the local system, not extending it. |
| Telegram integration pattern (bidirectional agent-to-chat-app) | Incompatible with this repo's architecture. The local repo produces Claude Code plugins that run inside the Claude Code CLI. Chat app integration (Telegram bot, streaming progress updates, scheduled notifications) is outside the plugin system's capabilities and would require a separate service. |
| Streaming API design (NDJSON for long-running analysis) | Irrelevant to the local architecture. Claude Code uses its own tool-call streaming protocol. Skills and agents do not expose HTTP endpoints or produce NDJSON streams. The pattern has no local system to map to. |
