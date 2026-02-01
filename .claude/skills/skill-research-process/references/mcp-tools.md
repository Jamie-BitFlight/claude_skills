# MCP Tool Usage Guide

Guidelines for selecting the right MCP tool based on research needs.

## Tool Fidelity Levels

| Level  | Description                     | Use Case                          |
| ------ | ------------------------------- | --------------------------------- |
| High   | Verbatim, authoritative content | Implementation details, API specs |
| Medium | Formatted markdown with code    | Documentation, examples           |
| Low    | Summarized, may omit details    | Scoping, overviews                |

## Tool Selection Matrix

### WebFetch (Built-in)

**Fidelity**: Low (Summarized)

**Best For**:

- Initial scoping of documentation structure
- Finding what documentation exists
- High-level overviews of tools/libraries

**Never Use For**:

- Implementation details
- Code examples or file structures
- API specifications
- Anything requiring verbatim accuracy

**Why**: WebFetch summarizes content and may omit or hallucinate technical details.

### mcp**Ref**\* Tools

**Fidelity**: High (Detailed)

**Available Tools**:

- `mcp__Ref__ref_search_documentation` - Search for documentation
- `mcp__Ref__ref_read_url` - Read specific URL content

**Best For**:

- Official documentation
- API references
- Technical specifications
- Authoritative source content

**When to Use**: Always prefer Ref for primary documentation sources.

### mcp**exa**\* Tools

**Fidelity**: Medium (Markdown)

**Available Tools**:

- `mcp__exa__web_search_exa` - Search the web for content
- `mcp__exa__get_code_context_exa` - Extract code patterns from URLs

**Best For**:

- Code examples and snippets
- Tutorial content
- Implementation patterns
- Community documentation

**When to Use**: For code-heavy content or when Ref doesn't have the content indexed.

## Research Strategy

### Phase 1: Discovery (Low Fidelity OK)

Use WebFetch to:

1. Find official documentation site
2. Understand documentation structure
3. Identify key sections to research

### Phase 2: Deep Research (High Fidelity Required)

Use Ref and Exa to:

1. Read authoritative documentation
2. Extract code examples
3. Gather implementation details

### Phase 3: Validation

Cross-reference multiple sources:

1. Official docs (Ref) - primary authority
2. Code examples (Exa) - implementation validation
3. GitHub repos - real-world usage patterns

## Tool Availability Check

MCP tools are dynamically available based on server configuration. Before using, check if the tool exists in your current session's `<functions>` list.

**Fallback Strategy**:

If MCP tools unavailable:

1. Use WebFetch for initial discovery
2. Use WebSearch for finding specific content
3. Clone repositories locally and use Read tool for code analysis

## Citation Requirements

All research must include source attribution:

```markdown
According to the official documentation (https://example.com/docs, accessed 2026-02-01), ...
```

Include:

- Source URL
- Access date
- Section/page if applicable
