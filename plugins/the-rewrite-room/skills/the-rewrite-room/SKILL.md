---
name: the-rewrite-room
description: Use when the user explicitly asks Rewrite Room to route documentation work, or when audit/sync/freshness, user-facing authoring, citation-driven writing, docs-to-skill conversion, and AI-instruction optimization overlap and exactly one workflow must be chosen.
---

# The Rewrite Room

## Input

- The documentation request
- Any supplied source, target, audience, format, and editing constraints

## Route

1. Identify the request's primary outcome. This step is complete when the requested outcome and any
   overlap among the five route classes are named.
2. Select exactly one workflow:

| Primary outcome | Workflow |
|---|---|
| Compare documentation with implementation, synchronize docs, or assess freshness | `rwr:audit` |
| Author, rewrite, summarize, or validate user-facing documentation | `rwr:author` |
| Produce source-attributed content with verified citations | `rwr:cite` |
| Convert source documentation into an AI-facing skill | `rwr:doc-to-skill` |
| Analyze or refine an existing AI-facing artifact without dropping behavior | `rwr:optimize` |

   This step is complete when exactly one row matches. When no unique row matches, return router-level
   `STATUS: BLOCKED` with the unresolved route decision and stop.
3. Activate the selected workflow by its exact name and pass the original request unchanged. This
   step is complete when dispatch starts with that exact workflow name and unchanged request, or a
   pre-leaf dispatch failure is named.
4. Return the selected workflow's terminal output unchanged when it reaches any terminal state
   defined by that workflow. This step is complete when the caller receives every terminal field and
   validation result exactly as the leaf returned it.

## Output

- The selected workflow name
- The selected workflow's complete terminal result and validation evidence, unchanged
- On route ambiguity or dispatch failure, `STATUS: BLOCKED` and the failure that prevented a leaf
  terminal report

## Completion

- Routing is complete when exactly one row matched, dispatch succeeded, and the selected workflow
  reached a terminal state defined by its own contract.
- **BLOCKED:** No unique row matched, or dispatch failed before the selected workflow produced a
  terminal report. Name the missing route decision or dispatch failure without reclassifying a leaf
  result.
