---
name: semantic-code-search
description: Teaches agents to use the CocoIndex Code MCP server for semantic code search — find code by meaning, concept, or natural language description. Use when searching by behavior or intent rather than exact identifiers, exploring unfamiliar codebases, or locating implementations without knowing exact names.
user-invocable: false
---

Use `mcp__cocoindex-code__search` for semantic code search when:

- Searching for code by meaning or description rather than exact text
- Exploring unfamiliar parts of the codebase
- Looking for implementations without knowing exact names
- Finding similar code patterns or related functionality

Prefer Grep/Glob when you know exact identifiers, filenames, or string literals. Prefer semantic search when you know what the code *does* but not what it's *called*.

The CocoIndex Code MCP server is bundled with this plugin via `.mcp.json` and launches automatically using `uvx cocoindex-code==0.1.11` — no pre-installation required. If `mcp__cocoindex-code__search` is not listed in available tools, report BLOCKED — this is a configuration error, not a fallback scenario.

SOURCE: [CocoIndex Code GitHub Repository](https://github.com/cocoindex-io/cocoindex-code) (accessed 2026-03-10)
