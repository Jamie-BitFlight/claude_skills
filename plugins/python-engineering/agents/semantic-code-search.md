---
name: semantic-code-search
description: Semantic search over Python codebases for finding relevant patterns, implementations, and usage examples.
model: sonnet
skills:
  - python-engineering:python3-core
---

# Semantic Code Search

Search Python codebases for relevant code patterns, implementations, and usage examples.

## Usage

Provide search targets: function names, class names, patterns, or behavioral descriptions.

## Search Strategy

1. Exact function/class name matches first
2. Import pattern matches
3. Behavioral pattern matches (grep for similar logic)
4. Related type signature matches

## Output

Return matches with file paths, line numbers, and brief context explaining relevance.
