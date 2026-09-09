---
name: the-rewrite-room
description: Use when routing documentation work to one Rewrite Room workflow, including documentation audit or synchronization, user-facing authoring or summaries, citation-driven writing, docs-to-skill conversion, and AI-instruction optimization.
---

# The Rewrite Room

## Input

- The documentation request
- Any supplied source, target, audience, format, and editing constraints

## Route

1. Identify the request's primary outcome.
2. Select exactly one workflow:

| Primary outcome | Workflow |
|---|---|
| Compare documentation with implementation, synchronize docs, or assess freshness | `rwr:audit` |
| Author, rewrite, summarize, or validate user-facing documentation | `rwr:author` |
| Produce source-attributed content with verified citations | `rwr:cite` |
| Convert source documentation into an AI-facing skill | `rwr:doc-to-skill` |
| Analyze or refine an existing AI-facing artifact without dropping behavior | `rwr:optimize` |

3. Activate the selected workflow by its exact name and pass the original request unchanged.
4. Return the selected workflow's terminal output unchanged when it reaches any terminal state
   defined by that workflow.

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
