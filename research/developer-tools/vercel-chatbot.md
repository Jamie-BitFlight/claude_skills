---
title: "Vercel Chatbot (vercel/chatbot)"
research_date: "2026-02-26"
source_url: "https://github.com/vercel/chatbot"
documentation_url: "<https://chatbot.dev> (redirects to chatbot.com/docs)"
version_at_research: "v3.1.0 (package.json, no GitHub releases published)"
license: "Other (proprietary template license, not OSI-approved)"
last_verified: "2026-02-26"
version_at_verification: "v3.1.0 (package.json)"
next_review: "2026-05-26"
---

## Overview

Vercel Chatbot (formerly AI Chatbot) is an open-source, production-ready Next.js 16 template for building full-featured AI chatbot applications. It serves as Vercel's official reference implementation for the [Vercel AI SDK](https://ai-sdk.dev) and the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway), providing a complete end-to-end chatbot architecture with authentication, persistent chat history, multi-model support, artifact generation, file uploads, and resumable streaming. The project is marked as a GitHub template repository (`is_template: true`), designed to be forked and deployed with one click to Vercel.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Starting a production chatbot from scratch requires weeks of boilerplate | Ready-to-deploy Next.js template with all infrastructure wired up |
| Multi-provider LLM integration is repetitive and fragile | Unified Vercel AI Gateway routes all models through a single interface |
| Chat history persistence requires custom backend work | Neon Serverless Postgres + Drizzle ORM schema provided and migrated automatically |
| Resumable streaming is hard to implement correctly | `resumable-stream` library + `Stream` table in DB enables mid-response resumption |
| File and image handling requires separate storage setup | Vercel Blob integration for attachment uploads |
| Authentication for chatbots requires custom session handling | Auth.js (NextAuth v5) with guest and regular user types |
| Generative documents alongside chat is complex | Artifact system with text, code, image, and sheet artifact types |
| Reasoning model output needs special parsing | `extractReasoningMiddleware` wraps any model to surface `<thinking>` tokens |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 19,691 | 2026-02-26 |
| GitHub Forks | 6,354 | 2026-02-26 |
| Open Issues | 68 | 2026-02-26 |
| Contributors | ~74 | 2026-02-26 |
| Package Version | 3.1.0 | 2026-02-26 |
| Primary Language | TypeScript | 2026-02-26 |
| Repository Created | 2023-05-19 | GitHub API |
| Last Push | 2026-02-24 | GitHub API |
| Template Repository | Yes | GitHub API |
| License | Other (proprietary) | GitHub API |

SOURCE: [GitHub API repos/vercel/chatbot](https://api.github.com/repos/vercel/chatbot) (accessed 2026-02-26)

---

## Key Features

### Multi-Model Support via AI Gateway

The template uses the `@ai-sdk/gateway` package to route all LLM requests through the Vercel AI Gateway, providing a single authentication surface for multiple providers. Supported models in the default configuration include:

- **Anthropic**: Claude Haiku 4.5, Claude Sonnet 4.5, Claude Opus 4.5, Claude 3.7 Sonnet (reasoning)
- **OpenAI**: GPT-4.1 Mini, GPT-5.2
- **Google**: Gemini 2.5 Flash Lite (default), Gemini 3 Pro
- **xAI**: Grok 4.1 Fast, Grok Code Fast (reasoning)
- **Title model**: Google Gemini 2.5 Flash Lite (dedicated lightweight model)
- **Artifact model**: Anthropic Claude Haiku 4.5 (dedicated artifact generation model)

SOURCE: `lib/ai/models.ts` and `lib/ai/providers.ts` in repository (accessed 2026-02-26)

### Artifact System

A structured document generation system with four artifact types, each with a client renderer and server handler:

- **Text** (`artifacts/text/`): ProseMirror-based rich text editor with AI-driven suggestions and diffs
- **Code** (`artifacts/code/`): CodeMirror 6 editor supporting JavaScript and Python with syntax highlighting
- **Image** (`artifacts/image/`): AI-generated image artifacts with display component
- **Sheet** (`artifacts/sheet/`): `react-data-grid` spreadsheet with PapaParse CSV support

Each artifact type implements `onCreateDocument` and `onUpdateDocument` handlers using `streamObject` from the AI SDK, streaming structured output directly into the document via a `dataStream`.

### Resumable Streaming

The template implements stream resumption so users can close and reopen the browser mid-generation without losing the response. The architecture uses:

- `resumable-stream` npm package for server-side stream state
- `Stream` table in PostgreSQL recording active stream IDs per chat
- `/api/chat/[id]/stream` route for reconnecting to in-progress streams
- `useAutoResume` hook on the client to detect and resume incomplete messages

### Authentication with User Tiers

Auth.js (NextAuth v5 beta) handles authentication with two user types and rate limiting:

| User Type | Max Messages / 24h |
|-----------|--------------------|
| `guest` | 20 |
| `regular` | 50 |

Guest users are created via `/api/auth/guest` with a server-side session. Regular users register with email + bcrypt-hashed password stored in PostgreSQL.

### Message Voting and Chat Visibility

- Per-message upvote/downvote stored in `Vote_v2` table linked to `Message_v2`
- Chat visibility toggle: `public` or `private` per conversation
- Chat sharing allows public chats to be viewed without authentication

### File Upload and Attachments

- File uploads handled at `/api/files/upload` route
- Files stored in Vercel Blob (`@vercel/blob`)
- Multimodal input component (`components/multimodal-input.tsx`) with attachment preview

### Observability

- OpenTelemetry instrumentation via `@vercel/otel` and `@opentelemetry/api`
- `instrumentation.ts` registers the OTEL provider for Next.js instrumentation hook
- Vercel Analytics integrated via `@vercel/analytics`

---

## Technical Architecture

### Stack

<eg>
Frontend
  ├── Next.js 16 (App Router, React 19, Server Components, Server Actions)
  ├── React 19.0.1
  ├── Tailwind CSS 4.x + shadcn/ui (Radix UI primitives)
  ├── @ai-sdk/react — useChat hook for streaming chat UI
  ├── CodeMirror 6 — code artifact editor
  ├── ProseMirror — text artifact editor
  └── react-data-grid — sheet artifact editor

Transport / Streaming
  ├── createUIMessageStream / createUIMessageStreamResponse (AI SDK 6.x)
  ├── resumable-stream — stream state persistence across reconnects
  └── Server-Sent Events via Next.js route handlers

Backend (Next.js API Routes)
  ├── /api/chat — main streaming chat endpoint (POST)
  ├── /api/chat/[id]/stream — stream resumption endpoint
  ├── /api/document — artifact CRUD
  ├── /api/files/upload — Vercel Blob upload
  ├── /api/history — paginated chat history
  ├── /api/suggestions — AI-generated document suggestions
  └── /api/vote — message voting

AI Layer
  ├── Vercel AI Gateway (@ai-sdk/gateway) — unified multi-provider routing
  ├── Vercel AI SDK 6.x (ai package) — streamText, streamObject, tool calls
  ├── extractReasoningMiddleware — surfaces <thinking> tokens from reasoning models
  └── customProvider — mock models for Playwright tests

Data Layer
  ├── Neon Serverless Postgres (postgres npm package)
  ├── Drizzle ORM + drizzle-kit migrations
  └── Schema: User, Chat, Message_v2, Vote_v2, Document, Suggestion, Stream

Auth
  └── Auth.js / NextAuth v5 (beta.25)

Storage
  └── Vercel Blob — file attachments

Testing
  └── Playwright e2e tests (auth, chat, model selector, API)
</eg>

### Database Schema

<eg>
User         id (uuid), email, password (bcrypt)
Chat         id, createdAt, title, userId, visibility (public/private)
Message_v2   id, chatId, role, parts (json), attachments (json), createdAt
Vote_v2      chatId + messageId (composite PK), isUpvoted
Document     id + createdAt (composite PK), title, content, kind, userId
Suggestion   id, documentId, documentCreatedAt, originalText, suggestedText, isResolved, userId
Stream       id, chatId, createdAt
</eg>

SOURCE: `lib/db/schema.ts` in repository (accessed 2026-02-26)

### AI SDK Version

The template uses AI SDK v6 (`ai: 6.0.37`, `@ai-sdk/react: 3.0.39`, `@ai-sdk/gateway: ^3.0.15`). This is a major version of the Vercel AI SDK with changes to the message format (parts-based messages in `Message_v2`, migration guide referenced in schema deprecation comments).

---

## Installation & Usage

```bash
# 1. Install Vercel CLI and link project
npm i -g vercel
vercel link

# 2. Pull environment variables
vercel env pull

# 3. Install dependencies and run migrations
pnpm install
pnpm db:migrate

# 4. Start development server
pnpm dev
```

For non-Vercel deployment, set `AI_GATEWAY_API_KEY` in `.env.local` to authenticate with the Vercel AI Gateway. Alternatively, replace `@ai-sdk/gateway` with a direct provider package (`@ai-sdk/openai`, `@ai-sdk/anthropic`, etc.) by modifying `lib/ai/providers.ts`.

```bash
# Key environment variables (from .env.example)
# AUTH_SECRET=           — NextAuth secret
# POSTGRES_URL=          — Neon connection string
# BLOB_READ_WRITE_TOKEN= — Vercel Blob token
# AI_GATEWAY_API_KEY=    — For non-Vercel deployments only
```

### One-Click Vercel Deploy

<eg>
https://vercel.com/templates/next.js/chatbot
</eg>

The Vercel template integration provisions Neon Postgres, Vercel Blob, and environment variables automatically.

---

## Relevance to Claude Code Development

### Direct Model Support

The `lib/ai/models.ts` file lists Claude Haiku 4.5, Claude Sonnet 4.5, and Claude Opus 4.5 as first-class supported models alongside OpenAI and Google. Claude Haiku 4.5 is the dedicated artifact generation model (`getArtifactModel()`), making this a direct reference implementation for Claude-powered document generation.

### Artifact System as Agent Tool Pattern

The artifact architecture (`onCreateDocument` / `onUpdateDocument` handlers) mirrors the tool-use pattern in Claude Code: a structured schema is passed to `streamObject`, and the model streams JSON output matching the schema. This pattern is directly applicable to building Claude Code skills that generate structured artifacts.

### Resumable Streaming Reference

The `resumable-stream` integration solves the same problem that long-running Claude Code agent tasks face — what happens if the connection drops. The `Stream` table + resume route pattern is a concrete implementation worth studying for any agentic web UI.

### AI SDK v6 Patterns

The template uses `createUIMessageStream`, `convertToModelMessages`, and parts-based message format from AI SDK v6 — the current version of the SDK. Reviewing the chat route (`app/(chat)/api/chat/route.ts`) provides working examples of multi-turn conversation, tool call routing, rate limiting, and message persistence patterns.

### Reasoning Model Integration

The `extractReasoningMiddleware` wrapper for `wrapLanguageModel` shows how to surface chain-of-thought tokens from models that use `<thinking>` tags (Claude 3.7 Sonnet extended thinking, xAI Grok). This is relevant for any application displaying agent reasoning steps.

### Multi-Tier User Entitlements

The `entitlements.ts` pattern (per-user-type rate limits stored as config) is a clean, extensible approach for adding usage quotas to any Claude-powered product — applicable to Claude Code skill access controls.

---

## References

- [GitHub Repository — vercel/chatbot](https://github.com/vercel/chatbot) (accessed 2026-02-26)
- [GitHub API — repos/vercel/chatbot](https://api.github.com/repos/vercel/chatbot) (accessed 2026-02-26)
- [Live Demo — chat.vercel.ai](https://chat.vercel.ai/) (accessed 2026-02-26)
- [Vercel Template](https://vercel.com/templates/next.js/chatbot) (accessed 2026-02-26)
- [Documentation — chatbot.dev](https://chatbot.dev) (redirects to chatbot.com/docs, accessed 2026-02-26)
- [Vercel AI SDK](https://ai-sdk.dev/docs/introduction) (accessed 2026-02-26)
- [Vercel AI Gateway](https://vercel.com/docs/ai-gateway) (accessed 2026-02-26)

**Research Method**: GitHub API for metadata (stars, forks, contributors, file contents). Repository source files read directly via `gh api repos/vercel/chatbot/contents/{path}`. README, `package.json`, `lib/ai/models.ts`, `lib/ai/providers.ts`, `lib/db/schema.ts`, `lib/ai/entitlements.ts`, `artifacts/code/server.ts`, and `app/(chat)/api/chat/route.ts` inspected directly.

---
