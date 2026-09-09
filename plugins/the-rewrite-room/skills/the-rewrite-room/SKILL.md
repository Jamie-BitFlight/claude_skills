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
| Convert source documentation into an AI-facing skill | `rwr:user-docs-to-ai-skill` |
| Analyze or refine an existing AI-facing artifact without dropping behavior | `rwr:optimize` |

3. Activate the selected workflow by its exact name and pass the original request unchanged.
4. Return the selected workflow's output after its completion criteria pass.

## Output

- The selected workflow name
- The selected workflow's result and validation evidence
- Any missing input that prevented a unique route or completed result

## Completion

- **DONE:** Exactly one row matched, that workflow ran, and all of its completion criteria passed.
- **BLOCKED:** No unique row matched or the selected workflow reported an unmet criterion. Name the missing decision or evidence.
