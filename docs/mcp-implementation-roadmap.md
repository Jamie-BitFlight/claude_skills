# MCP Implementation Roadmap

## Plugin MCP Status Matrix

| Plugin | Priority | Status | Tools Needed | Transport | Language |
|--------|----------|--------|--------------|-----------|----------|
| **agentskill-kaizen** | ✅ Complete | Production | 7 (process mining, clustering) | stdio | Python/FastMCP |
| **plugin-creator** | 🔴 Critical | Planned | 6 (validation, scaffolding) | stdio | Python/FastMCP |
| **python3-development** | 🔴 Critical | Planned | 6 (quality, testing) | stdio | Python/FastMCP |
| **holistic-linting** | 🔴 Critical | Planned | 6 (linter orchestration) | stdio | Python/FastMCP |
| **dasel** | 🔴 High | Planned | 6 (data queries) | stdio | Python/FastMCP |
| **development-harness** | 🟡 Medium | Consider | 5 (SAM orchestration) | stdio | Python/FastMCP |
| **gitlab-skill** | 🟡 Medium | Consider | 5 (CI/CD automation) | stdio | TypeScript |
| **summarizer** | 🟡 Medium | Consider | 4 (content analysis) | stdio | Python/FastMCP |
| **hallucination-detector** | 🟡 Medium | Consider | 4 (claim validation) | stdio | Python/FastMCP |

---

## Implementation Phases

### Phase 1: Core Development Tools (Q1 2026)

**Focus:** Enable plugin ecosystem health and Python development

```
┌─────────────────────────┐
│ plugin-creator          │  ← Critical for all plugins
│ • validate_frontmatter  │
│ • auto_fix_frontmatter  │
│ • analyze_structure     │
│ • check_complexity      │
│ • scaffold_plugin       │
│ • split_skill           │
└─────────────────────────┘
           │
           ├─────────────────────────┐
           │                         │
┌──────────▼──────────┐  ┌──────────▼────────────┐
│ python3-development │  │ holistic-linting      │
│ • run_quality_checks│  │ • detect_linters      │
│ • analyze_coverage  │  │ • run_linters         │
│ • detect_patterns   │  │ • explain_rule        │
│ • validate_pyproject│  │ • suggest_fixes       │
│ • suggest_deps      │  │ • check_suppressions  │
│ • check_type_coverage│ │ • validate_config     │
└─────────────────────┘  └───────────────────────┘
```

**Target Completion:** February 2026
**Expected Impact:**
- 80% of plugin development tasks now MCP-enabled
- Python quality workflows fully automated
- Consistent linting across all language plugins

---

### Phase 2: Specialized Tools (Q2 2026)

**Focus:** Data manipulation and workflow orchestration

```
┌─────────────────────┐
│ dasel               │
│ • query_data        │
│ • discover_structure│
│ • transform_data    │
│ • convert_format    │
│ • validate_selector │
│ • batch_extract     │
└──────────┬──────────┘
           │
           ├──────────────────────┐
           │                      │
┌──────────▼─────────┐  ┌─────────▼────────────┐
│ development-harness│  │ gitlab-skill         │
│ • detect_language  │  │ • validate_pipeline  │
│ • resolve_manifest │  │ • test_pipeline_local│
│ • create_artifact  │  │ • check_glfm_syntax  │
│ • validate_stage   │  │ • generate_cache_key │
│ • check_touchpoints│  │ • analyze_perf       │
└────────────────────┘  └──────────────────────┘
```

**Target Completion:** April 2026
**Expected Impact:**
- Unified data manipulation interface
- SAM workflow automation
- GitLab CI/CD fully programmatic

---

### Phase 3: Analysis Tools (Q3 2026)

**Focus:** Content analysis and quality control

```
┌──────────────────────┐  ┌─────────────────────────┐
│ summarizer           │  │ hallucination-detector  │
│ • summarize_file     │  │ • audit_text            │
│ • summarize_directory│  │ • explain_trigger       │
│ • extract_key_points │  │ • suggest_rewrite       │
│ • compare_versions   │  │ • check_citations       │
└──────────────────────┘  └─────────────────────────┘
```

**Target Completion:** June 2026
**Expected Impact:**
- Automated content analysis
- Real-time hallucination prevention
- Quality gate enforcement

---

## Tool Architecture Pattern

Each MCP server follows this structure:

```
plugins/plugin-name/
├── mcp/
│   ├── server.py          # FastMCP server (PEP 723 script)
│   └── dashboard.py       # Optional: visualization/monitoring
├── tests/
│   └── test_mcp.py        # MCP tool tests
├── .claude-plugin/
│   └── plugin.json        # MCP server registration
└── README.md              # MCP documentation section
```

### Standard Tool Template

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,  # Safe to call anytime
        "destructiveHint": False,  # No data modification
        "idempotentHint": True,  # Same result on repeat
        "openWorldHint": False,  # No external API calls
    }
)
async def tool_name(param: str, *, context: Context) -> dict[str, Any]:
    """One-line tool description.

    Detailed explanation of what this tool does,
    when to use it, and what it returns.

    Args:
        param: Parameter description with type info
        context: FastMCP context for progress updates

    Returns:
        Dict with 'status' and result data

    Raises:
        ToolError: When validation or execution fails
    """
    await context.info("Starting operation...")
    # Implementation
    return {"status": "success", "data": result}
```

---

## Tool Naming Conventions

Follow consistent patterns for discoverability:

| Pattern | Example | Purpose |
|---------|---------|---------|
| `verb_noun` | `validate_frontmatter` | Primary actions |
| `verb_noun_modifier` | `analyze_test_coverage` | Specific variants |
| `get_noun` | `get_plugin_structure` | Read-only queries |
| `check_noun` | `check_token_complexity` | Validation checks |
| `suggest_noun` | `suggest_dependencies` | Recommendations |
| `explain_noun` | `explain_rule` | Documentation lookup |

**Avoid:**
- Generic verbs like `run`, `do`, `process` without context
- Abbreviations (`chk`, `val`, `cfg`)
- Implementation details (`_internal`, `_helper`)

---

## Testing Strategy

### Unit Tests (per tool)

```python
# tests/test_mcp.py
import pytest
from mcp.server import mcp


@pytest.mark.asyncio
async def test_validate_frontmatter_valid():
    """Test frontmatter validation with valid input."""
    result = await mcp.tools["validate_frontmatter"](file_path="/path/to/SKILL.md")
    assert result["status"] == "valid"
    assert "errors" not in result


@pytest.mark.asyncio
async def test_validate_frontmatter_invalid():
    """Test frontmatter validation with invalid input."""
    result = await mcp.tools["validate_frontmatter"](file_path="/path/to/invalid.md")
    assert result["status"] == "invalid"
    assert len(result["errors"]) > 0
```

### Integration Tests (tool chaining)

```python
@pytest.mark.asyncio
async def test_fix_workflow():
    """Test complete fix workflow: analyze → fix → validate."""
    # Analyze issues
    analysis = await mcp.tools["analyze_plugin_structure"](plugin_dir="/path/to/plugin")
    assert analysis["status"] == "complete"

    # Apply fixes for each issue
    for issue in analysis["issues"]:
        fix_result = await mcp.tools["auto_fix_frontmatter"](file_path=issue["file"])
        assert fix_result["status"] == "fixed"

    # Validate all files pass
    validation = await mcp.tools["validate_frontmatter"](plugin_dir="/path/to/plugin")
    assert validation["status"] == "valid"
```

### MCP Inspector Testing

```bash
# Interactive testing during development
npx @modelcontextprotocol/inspector \
  uv run --script plugins/plugin-creator/mcp/server.py

# Test tool discovery
# Test parameter validation
# Test error handling
# Test progress reporting
```

---

## Documentation Requirements

Each plugin's README must include:

### MCP Server Section

```markdown
## MCP Server

This plugin provides an MCP server exposing programmatic access to its core tools.

### Available Tools

**validate_frontmatter** - Validate skill/agent frontmatter YAML
- Input: `file_path` (string) - Path to SKILL.md or agent file
- Output: Validation status with error details
- Annotations: read-only, idempotent

**auto_fix_frontmatter** - Automatically fix common frontmatter issues
- Input: `file_path` (string) - Path to file to fix
- Output: Fix status and changes applied
- Annotations: destructive, idempotent

[... document all tools ...]

### Usage

The MCP server starts automatically when the plugin is loaded. Tools are available to all agents.

**Example:** Validate all skills in a plugin

```bash
# From within Claude session
validate_frontmatter(plugin_dir="./plugins/my-plugin")
```

### Testing

```bash
# Test MCP server with inspector
npx @modelcontextprotocol/inspector \
  uv run --script "${CLAUDE_PLUGIN_ROOT}/mcp/server.py"
```
```

---

## Quality Checklist

Before marking an MCP implementation complete:

- [ ] All tools have clear, action-oriented names
- [ ] All tools have complete docstrings (Args, Returns, Raises)
- [ ] All tools have proper type hints
- [ ] All tools use appropriate annotations
- [ ] All tools handle errors with ToolError
- [ ] All tools report progress via context.info()
- [ ] Unit tests cover happy path and error cases
- [ ] Integration tests verify tool chaining
- [ ] MCP Inspector testing completed
- [ ] README documents all tools
- [ ] plugin.json declares MCP server
- [ ] PEP 723 metadata is complete
- [ ] Dependencies are minimal and justified

---

## Migration Path for Existing Scripts

Many plugins have existing Python scripts that can be wrapped:

### Example: plugin-creator

**Existing:** `scripts/plugin_validator.py` (CLI script)

**Migration:**
1. Extract core logic into reusable functions
2. Create MCP tool wrappers around functions
3. Keep CLI script as convenience wrapper
4. Document both interfaces

```python
# mcp/server.py
from scripts.plugin_validator import (
    validate_frontmatter_file,
    auto_fix_file
)

@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def validate_frontmatter(
    file_path: str,
    *,
    context: Context
) -> dict[str, Any]:
    """Validate frontmatter YAML in skill/agent file."""
    await context.info(f"Validating {file_path}...")
    result = await asyncio.to_thread(
        validate_frontmatter_file,
        file_path
    )
    return result
```

**Benefits:**
- Preserves existing functionality
- Adds programmatic interface
- No breaking changes to scripts
- Enables tool composition

---

## Success Metrics

Track these metrics per plugin:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tool coverage | 100% of core operations | % operations with MCP tools |
| Test coverage | >90% | pytest coverage report |
| Tool usage | >50% of workflows | MCP call logs |
| Error rate | <5% | ToolError frequency |
| Response time | <2s median | Tool execution timing |
| Documentation | 100% tools documented | README completeness |

---

## Risk Mitigation

### Backwards Compatibility

- Keep existing CLI scripts functional
- MCP tools are additive, not replacement
- Version MCP protocol in server name
- Document breaking changes in CHANGELOG

### Performance

- Use asyncio.to_thread for CPU-bound operations
- Implement timeout handling
- Cache expensive computations
- Stream large result sets

### Security

- Validate all file paths (prevent traversal)
- Sanitize shell command parameters
- Use subprocess with explicit args (not shell=True)
- Document destructive operations clearly

---

## Resources

- **MCP Protocol Spec:** <https://modelcontextprotocol.io/specification/draft>
- **FastMCP Docs:** <https://github.com/jlowin/fastmcp>
- **TypeScript SDK:** <https://github.com/modelcontextprotocol/typescript-sdk>
- **Python SDK:** <https://github.com/modelcontextprotocol/python-sdk>
- **Example Server:** `plugins/agentskill-kaizen/mcp/server.py`
- **MCP Best Practices:** `./reference/mcp_best_practices.md`
- **Evaluation Guide:** `./reference/evaluation.md`

---

## Next Actions

1. **Review analysis** - Team reviews `mcp-architecture-analysis.md`
2. **Prioritize Phase 1** - Confirm plugin-creator, python3-development, holistic-linting
3. **Create templates** - Generate boilerplate for each Phase 1 plugin
4. **Implement plugin-creator** - First complete implementation
5. **Document patterns** - Capture learnings in shared docs
6. **Iterate** - Apply patterns to python3-development and holistic-linting
7. **Review & adjust** - Team retrospective on Phase 1
8. **Begin Phase 2** - Apply refined patterns to dasel, development-harness, gitlab-skill

---

*Last updated: 2026-02-23*
