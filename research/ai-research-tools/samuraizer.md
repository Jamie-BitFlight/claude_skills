---
title: "Samuraizer: Cyber-Security Knowledge Base Engine"
resource_name: "Samuraizer"
category: "ai-research-tools"
created: "2026-03-25"
---

## Overview

**Samuraizer** is a full-stack application for security researchers to organize, analyze, and retrieve security knowledge using AI-powered summarization and semantic search. Described as "NotebookLM on steroids — purpose-built for security researchers," Samuraizer solves the problem of scattered security research links drowning in chat histories by providing a centralized, AI-enhanced knowledge base with semantic search, vector embeddings, and RAG-based chat.

**Repository**: <https://github.com/zomry1/Samuraizer>
**License**: MIT
**Language**: Python (backend), JavaScript (frontend)
**Latest Release**: 2026-03-24 (most recent commit)
**GitHub Stars**: 7 (as of 2026-03-25)
**Status**: Active development (last commit 2026-03-24T14:19:09Z)

---

## Problem Addressed

Security researchers routinely discover valuable resources — GitHub repositories, CVE writeups, blog posts about exploitation techniques, research papers — but have no systematic way to store them. Forwarding links to themselves via chat (WhatsApp, Telegram) or email results in scattered, unsearchable archives that become inaccessible over time.

Samuraizer provides a purpose-built solution:
- **"Stop sending yourself links you'll never find again — send them to Samuraizer once, and they're summarized, tagged, and searchable forever."** (from README)
- Centralized, tagged knowledge base for security research
- AI-powered automatic categorization and tagging
- Semantic search over embeddings for intelligent retrieval
- Telegram bot for frictionless ingestion
- RAG-based chat to ask questions over the knowledge base

---

## Key Features

### 📝 Analysis & Ingestion
- **URL Analysis**: Paste one or more URLs (GitHub repos, CVE writeups, blog posts, YouTube videos). Results stream back in real time using Gemini 2.5 Flash for summarization.
- **PDF Upload**: Upload PDF files directly from browser or Telegram. Full text is extracted via PyMuPDF (fitz), analyzed, stored, and viewable in the UI.
- **Blog Scanner**: Paste a blog homepage and extract all article links for batch analysis in a single click.
- **Suggested Read**: A relevant unread entry is automatically surfaced on the Analyze tab each session.

**Mechanism**: Backend detects resource type (GitHub repo, blog post, RSS feed, PDF, etc.), fetches or extracts content, sends to Gemini 2.5 Flash for summarization, and stores results in SQLite with embeddings.

### 🗂️ Knowledge Base Management
- **Inline Tag Editing**: Add/remove tags on entries, feeds, and list items; edits persist via `PATCH /entries/<id>`.
- **Dual Search**: Semantic search (vector search via Gemini embeddings) AND classic full-text search.
- **Tag Cloud + Multi-Filtering**: Filter by tag, category, source, list, read/useful status.
- **List Management**: Group entries into manual lists, RSS lists, or channel-based lists.
- **Hover Preview**: Summary cards and quick-copy buttons for entries.

### 🗺️ Knowledge Graph
- Visualize entire knowledge base as an interactive force-directed graph (D3.js v7.9.0).
- Entries and tags are graph nodes; edges show tag-to-article relationships.
- Click to preview, double-click to open original URL.
- Color-coded by category (CVE, article, tool, video, blog, etc.).
- Search tags to highlight related clusters.

### 📡 RSS Feeds & YouTube Subscriptions
- **RSS/Atom Feeds**: Add feeds; server polls hourly and auto-ingests and summarizes new posts.
- **New posts** automatically added to Knowledge Base; each feed becomes its own list.
- **YouTube Channels**: Subscribe via URL (e.g., `https://www.youtube.com/@handle` or `/channel/UCxxx`).
  - Preview latest videos before subscribing and select which to analyze.
  - On subscribe, selected videos are analyzed immediately; future uploads auto-polled hourly.
  - Accessed via `/yt-channels` API.

**YouTube Transcript Note**: Originally used open-source `youtube-transcript-api`, but YouTube aggressively blocks automated transcript requests from cloud provider IPs and high-frequency IPs, causing failures. Now uses [transcriptapi.com](https://transcriptapi.com) — a paid managed REST API — to avoid IP blocks. Free tier available with credit-based billing. Alternative solutions documented: `yt-dlp`, YouTube Data API v3, or `Supadata`.

### 🤖 Telegram Bot (Optional)
- Send any URL to the bot; it analyzes via the same backend and returns a formatted result card.
- Send a PDF file; the bot downloads, analyzes, and returns a result card with view/download link.
- Live progress updates streamed as analysis runs.
- Receives **Suggested Read** notifications — proactively surfaces unread entries at configured intervals (default: 8 hours).
- Commands: `/help`, `/list`, `/search`, `/setcat`, `/suggest`.

### 💬 Chat (RAG + Streaming + Pinned Context)
- Ask questions over knowledge base; answers are cited from best matching entries.
- **Streaming responses** with live typing and per-source relevance scores (cosine similarity).
- **Multiple chat sessions** with saved history and model selection.
- **Pin specific articles**: Type `@` for autocomplete or use browse button.
  - When entries are pinned, Gemini answers **only** from those articles — no RAG noise.
  - Pinned entries appear as chips above input; sources show 📌 badge instead of score.
  - Ideal for deep-diving a specific PDF, writeup, or CVE.

**Mechanism**: Semantic search retrieves best-matching entries; Gemini processes user query + top matches (or pinned entries) and streams response. Relevance scores computed via cosine similarity over Gemini embeddings.

---

## Technical Architecture

### Core Components

```
Browser UI (React 19.2.4 + Vite)
    ↓ (HTTP/REST/NDJSON)
Flask API Backend (Python)
    ├→ SQLite DB (samuraizer.db)
    ├→ Gemini 2.5 Flash (summarization, embeddings)
    ├→ GitHub API (for repo analysis)
    ├→ RSS Feeds (feedparser)
    └→ Telegram Bot (python-telegram-bot v20+)
```

### Data Flow

1. **URL/PDF Submission**: User pastes URL or uploads PDF via browser or Telegram.
2. **Content Extraction**: Backend fetches/extracts text using:
   - GitHub API + git clone for repos
   - Trafilatura for article content
   - PyMuPDF (fitz) for PDF text extraction
   - transcriptapi.com for YouTube transcripts
3. **AI Summarization**: Content sent to Gemini 2.5 Flash; returns:
   - Concise summary
   - Category and tags
   - Embeddings (if semantic search is enabled) via `_store_entry_embedding()`
4. **Storage**: Entry stored in SQLite with full content, metadata, and embeddings.
5. **Retrieval**: Frontend queries via:
   - Full-text search (SQL LIKE queries)
   - Semantic search (cosine similarity over embeddings)
   - Tag/category/list filtering
6. **Graph Visualization**: D3.js renders entries and tags as nodes; edges reflect tag membership.
7. **Chat**: Semantic search retrieves top-K entries; Gemini synthesizes answer with citations.

### Database Schema

Central table: `entries` with columns for:
- `id`, `title`, `summary`, `url`, `category`, `tags` (JSON), `content` (full text), `embeddings` (BLOB)
- `created_at`, `updated_at`, `is_read`, `is_useful`, `source` (manual/rss/youtube/telegram)
- Foreign keys to `lists`, `rss_feeds`, `yt_channels`, `chat_sessions`

Supporting tables:
- `lists` — custom groupings of entries
- `rss_feeds` — configured feeds with last_checked timestamp
- `yt_channels` — subscribed YouTube channels
- `chat_sessions` — chat history grouped by session

### Key Classes and Functions (from source code)

**Server initialization and logging**:
- `_MemoryLogHandler` — thread-safe ring-buffer keeping last 2000 log records; exposed via `GET /logs`
- `_start_backup_scheduler()` — auto-backup DB every N hours (default: 12)

**Content extraction**:
- `_fetch_github_content(url)` — extracts README, structure from repos
- `_fetch_youtube_content(url)` — uses transcriptapi.com for transcripts
- `_fetch_article_content(url)` — uses Trafilatura to extract article text
- `_extract_pdf_text(file_bytes)` — PyMuPDF text extraction from PDFs
- `_extract_blog_links(base_url, page)` — scrapes links from blog homepages

**AI processing**:
- `_call_gemini(content, custom_cats)` — sends content to Gemini 2.5 Flash for summarization; returns `(response_dict, embedding_list)`
- `_store_entry_embedding(db, entry_id, name, bullets, tags, embedding)` — stores embeddings for semantic search
- `_cosine_sim(a, b)` — computes cosine similarity for vector search

**Async processing**:
- `_process_url(url, source)` — orchestrates extraction, summarization, and storage (blocking)
- `_process_blog_listing(url, selected_urls, listing_title)` — batch processes blog articles
- `_process_playlist(url)` — processes YouTube playlists

**API response helpers**:
- `_row_to_dict(row, db)` — converts DB rows to JSON with full embedding vectors
- `_bulk_list_ids(db, entry_ids)` — retrieves list memberships for entries

### Extension Points

1. **Custom Content Extractors**: Add new content types by implementing extractor functions (e.g., `_fetch_X_content(url)`) and registering in `_process_url()`.
2. **Custom LLM Models**: Replace Gemini calls in `_call_gemini()` with alternative providers (swap `google.genai` for OpenAI, Anthropic, etc.).
3. **Custom Embedding Models**: Replace Gemini embeddings in `_get_embedding()` with alternatives (e.g., local sentence-transformers).
4. **Notification Channels**: Extend Telegram bot or add Discord/Slack integrations by implementing handler patterns similar to telegram_bot.py.
5. **Feed Types**: Add new feed sources beyond RSS/YouTube by extending `_process_url()` and database schema.

---

## Installation & Usage

### Local Setup

**1. Configuration**:
```bash
cp .env.example .env
# Edit .env with required keys
```

Required:
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/app/apikey)

Optional:
- `TELEGRAM_BOT_TOKEN` — from @BotFather on Telegram
- `GITHUB_TOKEN` — increases GitHub API rate limit from 60 to 5,000 req/hr
- `TRANSCRIPTAPI` — from [transcriptapi.com](https://transcriptapi.com/dashboard/api-keys) for YouTube transcripts
- `SAMURAIZER_URL` — backend URL for Telegram bot (default: `http://localhost:8000`)
- `FLASK_DEBUG` — enable Flask debug mode (development only)

**2. Install dependencies**:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install
```

**3. Run backend**:
```bash
python server.py
```

**4. Run frontend** (separate terminal):
```bash
cd frontend
npm run dev
```

**5. (Optional) Run Telegram bot**:
```bash
python telegram_bot.py
```

### Key APIs

**Analyze URLs**:
```
POST /analyze
Body: { "url": "https://github.com/owner/repo" }
Response: Stream NDJSON events (status, summary, category, tags, entry_id)
```

**Analyze PDFs**:
```
POST /analyze-pdf
Body: multipart/form-data with file field
Response: Stream NDJSON events (same shape as /analyze)
```

**Retrieve PDFs**:
```
GET /entries/<id>/pdf               (inline view)
GET /entries/<id>/pdf?dl=1          (download)
```

**List entries** (with filters):
```
GET /entries?search=query&category=cve&tag=rce&list_id=5&read=false&useful=true
Response: JSON array of entries
```

**Semantic search**:
```
GET /search/semantic?q=privilege+escalation
Response: JSON array sorted by cosine similarity
```

**RAG chat**:
```
POST /chat
Body: { "session_id": 3, "query": "How does this CVE work?", "pinned_entry_ids": [5, 7] }
Response: Stream NDJSON events (token, sources, final_answer)
```

**YouTube subscriptions**:
```
GET /yt-channels
POST /yt-channels/preview  Body: { "url": "https://www.youtube.com/@handle" }
POST /yt-channels         Body: { "url": "...", "analyze_urls": [...] }
POST /yt-channels/<id>/poll  (manual refresh)
DELETE /yt-channels/<id>
```

**RSS feeds**:
```
GET /rss-feeds
POST /rss-feeds           Body: { "url": "...", "name": "..." }
POST /rss-feeds/<id>/poll  (manual refresh)
DELETE /rss-feeds/<id>
```

**Chat sessions**:
```
GET /chat/sessions
POST /chat/sessions       Body: { "name": "...", "model": "gemini-2.5-flash" }
PATCH /chat/sessions/<id> Body: { "name": "..." }
DELETE /chat/sessions/<id>
GET /chat/sessions/<id>/messages
```

---

## Tech Stack

| Layer | Technology | Version/Notes |
|-------|-----------|--------------|
| **Backend** | Python 3.11+ | Flask, SQLite, feedparser, Trafilatura, PyMuPDF |
| **Frontend** | React 19.2.4, Vite 8.0.2 | Tailwind CSS 4.2.2, D3.js 7.9.0 |
| **LLM** | Gemini 2.5 Flash | Via google-genai SDK |
| **Vector Search** | Gemini embeddings | Cosine similarity |
| **Bot** | python-telegram-bot v20+ | job-queue for scheduled tasks |
| **Web scraping** | Trafilatura, Scrapling, curl-cffi, Playwright, browserforge | Content extraction and rendering |
| **Transcripts** | transcriptapi.com (paid REST API) | YouTube transcript fetching via external service |
| **Graph visualization** | D3.js v7.9.0 | Force-directed graph |

**Key Python dependencies** (from requirements.txt):
- `flask`, `flask-cors` — web framework
- `feedparser` — RSS/Atom parsing
- `trafilatura`, `lxml_html_clean` — article extraction
- `google-genai` — Gemini API client
- `python-telegram-bot[job-queue]>=21.0` — Telegram bot
- `pymupdf` — PDF text extraction
- `youtube-transcript-api` — legacy (blocked; now using transcriptapi.com)
- `pytubefix`, `scrapling`, `curl-cffi`, `playwright`, `browserforge` — web scraping
- `json-repair` — JSON repair for malformed API responses
- `requests`, `python-dotenv` — HTTP and config

---

## Limitations & Caveats

1. **YouTube Transcript Dependency**: YouTube transcript fetching requires transcriptapi.com (paid, credit-based). Open-source alternatives (`youtube-transcript-api`, `yt-dlp`) exist but face IP blocking by YouTube; see README for detailed analysis and alternatives.

2. **Gemini API Rate Limits**: Backend relies entirely on Gemini 2.5 Flash for summarization and embeddings. Rate limits and quota exhaustion will block analysis. No fallback LLM implemented.

3. **Vector Search Scaling**: Storing full embedding vectors in SQLite (BLOB column) scales poorly for large knowledge bases (>10k entries). Alternative vector stores (Pinecone, Weaviate, FAISS) not integrated.

4. **No User Authentication**: No multi-user or access control. Single instance serves one user; Telegram bot is the only ingress control point.

5. **Chat Streaming via NDJSON**: Real-time streaming uses newline-delimited JSON (NDJSON). Browser integration must parse streaming responses; no Server-Sent Events (SSE) fallback for compatibility.

6. **PDF Storage**: Uploaded PDFs stored as BLOBs in SQLite. No external blob storage (S3, GCS). Large PDFs multiply DB size.

7. **No Batch Export**: Knowledge base is locked into Samuraizer's UI. No built-in export to Obsidian, Markdown, or other formats (though a feature vote is open for Obsidian export).

8. **RSS Feed Polling**: Hourly polling is hardcoded; no fine-grained schedule per feed or manual trigger UI (manual trigger API exists: `POST /rss-feeds/<id>/poll`).

9. **Blog Scraping Brittleness**: Homepage scraping to extract blog article links (`_extract_blog_links()`) relies on DOM structure and CSS selectors; layout changes break it.

10. **No Offline Mode**: Entirely cloud-dependent for LLM calls and transcript fetching; cannot function without Gemini API and transcriptapi.com access.

---

## Relevance to Claude Code Development

**Moderately relevant** for security-focused Agent development and knowledge management workflows.

### High-Value Use Cases

1. **Security Research Agents**: Building agents that analyze CVEs, GitHub repos, or security writeups can integrate Samuraizer's extraction pipeline (Trafilatura, PyMuPDF, Gemini summarization) to auto-document findings in a searchable knowledge base.

2. **Knowledge Base for AI Agents**: Samuraizer's semantic search and RAG chat provide a blueprint for agents needing to retrieve context from large document collections. The D3 graph visualization is a strong UI pattern for exploring agent-analyzed artifacts.

3. **Telegram Integration Pattern**: Samuraizer's Telegram bot demonstrates a full example of bidirectional agent-to-chat-app integration, including file upload handling, streaming progress updates, and scheduled notifications — valuable for building Claude-based agents that live in Telegram.

4. **Multi-Modal Content Handling**: The stack (Trafilatura for articles, PyMuPDF for PDFs, transcriptapi for videos, GitHub API for repos) shows practical patterns for analyzing diverse input types — useful for agents consuming mixed content.

5. **Streaming API Design**: NDJSON streaming for long-running analysis (URL processing, PDF ingestion) and chat is a clean pattern for agents that emit intermediate results before final output.

### Lower-Value Use Cases

- **Custom LLM Integration**: Samuraizer is tightly coupled to Gemini. Claude Code users wanting to integrate Claude instead would need significant refactoring.
- **Multi-User/SaaS**: Samuraizer is single-user by design; no multi-tenancy or RBAC. Not a direct template for collaborative agent systems.

### Related Claude Code Artifacts

- **Agents that analyze code or docs**: Samuraizer's architecture demonstrates how to pipe multiple content types through a centralized LLM for summarization and tagging — a pattern valuable for code-auditing agents.
- **RAG-based agents**: The vector search + pinned context pattern is directly applicable to Claude-powered agents that reason over document corpora.

---

## References

- **Repository**: <https://github.com/zomry1/Samuraizer>
- **License**: MIT (viewed 2026-03-25)
- **README**: Full feature documentation, architecture diagram, API endpoints, setup instructions, YouTube transcript analysis (viewed 2026-03-25 from repo)
- **Source code**: server.py (2,736 lines), telegram_bot.py (24,273 bytes), frontend React structure (viewed 2026-03-25)
- **GitHub API**: Repository metadata (viewed via curl, 2026-03-25)
  - Stars: 7
  - Forks: 0
  - Language: JavaScript (frontend DOM)
  - License: MIT
  - Created: 2026-03-18T12:50:40Z
  - Last push: 2026-03-24T14:19:09Z
- **Dependencies**: requirements.txt and frontend/package.json (viewed 2026-03-25)
- **Transcript service**: <https://transcriptapi.com> — mentioned in README with detailed rationale and alternatives (viewed via repo content, 2026-03-25)

---

## Freshness Tracking

**Last reviewed**: 2026-03-25
**Next review due**: 2026-06-25 (3 months)

### Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Identity/Metadata** | high | Official GitHub API, recent repo created 2026-03-18 |
| **Problem Addressed** | high | Directly quoted from README introduction |
| **Key Features** | high | Extracted from README feature sections and verified against source code routes |
| **Technical Architecture** | high | Source code review (server.py routes, function signatures, data structures) |
| **Installation & Usage** | high | Verified against .env.example, requirements.txt, README setup, and source code |
| **Tech Stack** | high | requirements.txt, package.json, source imports, and README tech table |
| **Limitations** | high | YouTube transcript detailed analysis in README; other limitations inferred from code inspection and feature gaps |
| **Relevance to Claude Code** | medium | Based on feature analysis; limited direct integration evidence but high relevance for security agent patterns |

---

## Session Notes

- Repository is very recent (created 2026-03-18, 7 days old at review time); under active development
- Strong focus on security research use case; clear product-market fit in target audience
- Clean separation of concerns: Flask backend (content extraction, LLM integration), React frontend (graph viz, search UI), Telegram bot (mobile/chat ingress)
- Key architectural decision: Gemini-centric (no LLM abstraction layer); limits portability to other models
- YouTube transcript handling shows pragmatic engineering: acknowledged IP blocking problem, evaluated alternatives, chose managed service
- Extensive README documentation with feature deep-dives and detailed setup; codebase is well-commented

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [NotebookLM](./notebooklm.md) | ai-research-tools | Similar AI-assisted document summarization and Q&A interface for research workflows |
| [Awesome AI Apps](./awesome-ai-apps.md) | ai-research-tools | Curated collection of RAG and memory agent patterns applicable to knowledge base architectures |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | Hybrid semantic+keyword search and progressive disclosure pattern mirrors Samuraizer's vector search architecture |
| [MCPJam Inspector](../mcp-ecosystem/mcpjam.md) | mcp-ecosystem | Local testing tool for MCP servers; Samuraizer knowledge base could be exposed as MCP backend for integration |
| [CopilotKit](../agent-frameworks/copilotkit.md) | agent-frameworks | Agentic UI framework with bi-directional state sync applicable to knowledge base frontend patterns |
