# Accessing Online Resources: Definitive Guide

**Objective**: Ensure high-fidelity data retrieval for technical tasks by selecting the correct tool.

## Tool Selection Matrix

| Tool         | Fidelity              | Purpose            | Use When...                                                                                                           |
| :----------- | :-------------------- | :----------------- | :-------------------------------------------------------------------------------------------------------------------- |
| **WebFetch** | **Low** (Summarized)  | Scoping & Overview | You need to know _what_ something is or get a high-level summary. **NEVER** use for technical implementation details. |
| **Exa**      | **Medium** (Markdown) | Content Extraction | You need to read documentation, see code snippets, or extract specific content from a page.                           |
| **Ref**      | **High** (Detailed)   | Deep Reading       | You need authoritative, verbatim documentation or deep technical specs.                                               |

## Experimental Evidence

We benchmarked these tools against three targets: Anthropic Docs, GitHub, and PyPI.

### 1. WebFetch (The "Summarizer")

- **Behavior**: Aggressively summarizes content. Converts HTML to a high-level overview.
- **Data Loss**: Strips file lists, specific code comments, and detailed syntax.
- **Risk**: High risk of hallucination if asked for details it filtered out (e.g., "commit messages" in a file list).
- **Example Output**:
  > "The repository contains 6 essential slash commands... Design Philosophy: The collection intentionally limits itself..."
  > _(Missing: Actual file list, specific code, installation nuances)_

### 2. Exa (The "Extractor")

- **Behavior**: Returns Markdown-formatted content extracted from the HTML.
- **Data Retention**: Preserves code blocks, tables, and structure.
- **Example Output**:

  <eg>
  "├──yaml_optimizer.py # YAML anchor/alias optimization"
  (Visible: File tree, comments, code blocks)
</eg>

### 3. Ref (The "Reader")

- **Behavior**: High-fidelity retrieval, often verbatim.
- **Data Retention**: Maximum. Preserves exact syntax, version numbers, and directives.
- **Example Output**:
  > Detailed, verbatim documentation suitable for deep technical analysis.

## Critical Rules

1.  **NEVER use `WebFetch` for "How-To"**: If you need to know how to implement something, `WebFetch` will fail you. It will give you a summary of the _concept_, not the _code_.
2.  **ALWAYS use `Exa` or `Ref` for Code**: If you need to see file structures, specific comments, or configuration options, you must use a high-fidelity tool.
3.  **Verify, Don't Infer**: If a tool returns a summary, do not guess at the missing details. Switch to a higher-fidelity tool.
