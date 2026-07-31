# MCP Architecture Analysis: agentskill-kaizen Plugin Ecosystem

## Executive Summary

**Current State:** Only 1 of 27 plugins has MCP tooling (agentskill-kaizen)

**Goal:** Each plugin should provide a universal MCP interface for its tooling, enabling agents to access plugin capabilities programmatically through standardized tools.

**Architecture:** Two-tier MCP model:
1. **Plugin-level MCPs** - Universal interface per plugin for its core tooling
2. **Personal MCPs** - Custom tools individual agents can add to their workflow

---

## MCP Philosophy

From the Warp documentation and agentskill-kaizen implementation:

> MCP servers extend agents in a modular, flexible way by exposing custom tools or data sources through a standardized interface — essentially acting as plugins.

**Key Principles:**
- **Universal Interface** - Consistent tool access regardless of language or framework
- **Stateless Operations** - Tools should be self-contained and composable
- **Clear Tool Naming** - Action-oriented names with consistent prefixes
- **Rich Error Messages** - Actionable guidance when tools fail
- **Read-Only Annotations** - Proper tool metadata (readOnlyHint, destructiveHint, etc.)

---

## Plugin MCP Needs Assessment

### Tier 1: Critical - Complex Tooling Requiring MCP Interface

#### 1. **agentskill-kaizen** ✅ (Complete)
**Status:** Has comprehensive MCP server
- **MCP:** `kaizen-analysis` (FastMCP, Python)
- **Tools:** 7 tools for process mining, pattern detection, clustering
- **Location:** `plugins/agentskill-kaizen/mcp/server.py`
- **Transport:** stdio via `uv --script`
- **Quality:** Production-ready, includes dashboard

#### 2. **plugin-creator** 🔴 (Needs MCP)
**Purpose:** Plugin development, validation, refactoring
**Recommended Tools:**
- `validate_frontmatter` - Validate skill/agent frontmatter
- `auto_fix_frontmatter` - Auto-fix common issues
- `analyze_plugin_structure` - Analyze plugin organization
- `check_token_complexity` - Check skill token counts
- `scaffold_plugin` - Generate plugin structure
- `split_skill` - Split oversized skills

**Implementation:**
- Language: Python (FastMCP)
- Transport: stdio
- Script location: `plugins/plugin-creator/mcp/server.py`
- Wraps existing `plugin_validator.py` and `create_plugin.py`

#### 3. **python3-development** 🔴 (Needs MCP)
**Purpose:** Python code quality, testing, packaging
**Recommended Tools:**
- `run_quality_checks` - Run ruff, mypy, pyright
- `analyze_test_coverage` - pytest coverage analysis
- `detect_modern_patterns` - Find modernization opportunities
- `validate_pyproject` - Validate pyproject.toml
- `suggest_dependencies` - Recommend modern libraries
- `check_type_coverage` - Analyze type hint coverage

**Implementation:**
- Language: Python (FastMCP)
- Transport: stdio
- Script location: `plugins/python3-development/mcp/server.py`

#### 4. **holistic-linting** 🔴 (Needs MCP)
**Purpose:** Cross-language linting orchestration
**Recommended Tools:**
- `detect_project_linters` - Discover configured linters
- `run_linters` - Execute linters on files
- `explain_rule` - Fetch rule documentation
- `suggest_fixes` - Generate fix suggestions
- `check_suppressions` - Audit suppression comments
- `validate_config` - Validate linter configs

**Implementation:**
- Language: Python (FastMCP)
- Transport: stdio
- Script location: `plugins/holistic-linting/mcp/server.py`

#### 5. **dasel** 🔴 (Needs MCP)
**Purpose:** Structured data query and transformation
**Recommended Tools:**
- `query_structured_data` - Run dasel queries
- `discover_structure` - Explore data file structure
- `transform_data` - Safe in-place transformations
- `convert_format` - Convert between formats
- `validate_selector` - Validate dasel selector syntax
- `batch_extract` - Extract multiple values

**Implementation:**
- Language: Python (FastMCP) wrapping dasel binary
- Transport: stdio
- Script location: `plugins/dasel/mcp/server.py`

---

### Tier 2: Moderate - Utility Plugins with Programmatic Needs

#### 6. **development-harness** 🟡 (Consider MCP)
**Purpose:** SAM workflow orchestration
**Potential Tools:**
- `detect_language` - Detect project language
- `resolve_manifest` - Load language manifest
- `create_artifact` - Create SAM artifact
- `validate_stage_output` - Validate stage completion
- `check_touchpoints` - ARL touchpoint analysis

**Implementation:** Python (FastMCP) if needed

#### 7. **gitlab-skill** 🟡 (Consider MCP)
**Purpose:** GitLab CI/CD and documentation
**Potential Tools:**
- `validate_pipeline` - Validate `.gitlab-ci.yml`
- `test_pipeline_local` - Run `gitlab-ci-local`
- `check_glfm_syntax` - Validate GitLab Markdown
- `generate_ci_cache_key` - Generate cache keys
- `analyze_pipeline_perf` - Pipeline performance analysis

**Implementation:** TypeScript (recommended) or Python

#### 8. **summarizer** 🟡 (Consider MCP)
**Purpose:** Content summarization
**Potential Tools:**
- `summarize_file` - Summarize single file
- `summarize_directory` - Summarize directory contents
- `extract_key_points` - Extract key information
- `compare_versions` - Diff summaries

**Implementation:** Python (FastMCP)

#### 9. **hallucination-detector** 🟡 (Consider MCP)
**Purpose:** Detect speculation and ungrounded claims
**Potential Tools:**
- `audit_text` - Scan for hallucination patterns
- `explain_trigger` - Explain why text was flagged
- `suggest_rewrite` - Suggest evidence-based alternative
- `check_citations` - Validate claim citations

**Implementation:** Python (FastMCP)

---

### Tier 3: Low Priority - Configuration/Knowledge Plugins

These plugins primarily provide knowledge (skills) rather than runtime tooling. MCP servers would add little value:

- **bash-development** - Bash scripting patterns (knowledge-based)
- **brainstorming-skill** - Brainstorming methodology (knowledge-based)
- **clang-format** - C/C++ formatting patterns (wraps existing tool)
- **commitlint** - Commit message validation (wraps existing tool)
- **conventional-commits** - Commit conventions (knowledge-based)
- **fastmcp-creator** - FastMCP creation guide (knowledge-based)
- **litellm** - LiteLLM proxy knowledge (knowledge-based)
- **llamafile** - Llamafile usage (knowledge-based)
- **orchestrator-discipline** - Orchestration patterns (knowledge-based)
- **perl-development** - Perl patterns (knowledge-based)
- **prompt-optimization-claude-45** - Prompt optimization (knowledge-based)
- **the-rewrite-room** - Content rewriting (knowledge-based)
- **uv** - uv package manager knowledge (knowledge-based)
- **verification-gate** - Verification patterns (knowledge-based)
- **xdg-base-directory** - XDG spec knowledge (knowledge-based)
- **agent-orchestration** - Orchestration theory (knowledge-based)

---

## MCP Implementation Priority

### Phase 1: Core Development Tools (Q1 2026)
1. **plugin-creator** - Critical for plugin ecosystem health
2. **python3-development** - High usage, clear tool needs
3. **holistic-linting** - Cross-cutting concern

### Phase 2: Specialized Tools (Q2 2026)
4. **dasel** - Unique data manipulation capabilities
5. **development-harness** - SAM orchestration if complex enough
6. **gitlab-skill** - CI/CD automation

### Phase 3: Analysis Tools (Q3 2026)
7. **summarizer** - Content analysis
8. **hallucination-detector** - Quality control

---

## MCP Server Design Pattern

Based on `agentskill-kaizen/mcp/server.py`, the standard pattern:

```python
#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     # ... plugin-specific deps
# ]
# ///
"""Plugin Name MCP Server.

Brief description of what this MCP exposes.

Tools:
    tool_one - Description
    tool_two - Description
"""

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("plugin-name", mask_error_details=False)

_READONLY_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def tool_name(param: str, *, context: Context) -> dict:
    """Tool description.

    Args:
        param: Parameter description
        context: FastMCP context for progress reporting

    Returns:
        Result dictionary

    Raises:
        ToolError: When operation fails
    """
    await context.info("Starting operation...")
    # Implementation
    return {"result": "data"}


if __name__ == "__main__":
    mcp.run()
```

**Key Elements:**
- PEP 723 inline metadata for uv script execution
- FastMCP 3.0+ with proper error handling
- Tool annotations for safety metadata
- Async functions with Context for progress reporting
- Type hints on all parameters and returns
- ToolError for explicit failure modes

---

## MCP Configuration Pattern

Each plugin's `.claude-plugin/plugin.json` should declare its MCP server:

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "mcpServers": {
    "plugin-name": {
      "command": "uv",
      "args": [
        "run",
        "--script",
        "${CLAUDE_PLUGIN_ROOT}/mcp/server.py"
      ],
      "env": {
        "CLAUDE_PROJECT_DIR": "${CLAUDE_PROJECT_DIR}"
      }
    }
  }
}
```

**Notes:**
- `${CLAUDE_PLUGIN_ROOT}` resolves to plugin directory
- `${CLAUDE_PROJECT_DIR}` resolves to project root
- `command: "uv"` for Python (universal Python packaging tool)
- `command: "npx"` for TypeScript/Node.js

---

## Testing MCP Servers

Use MCP Inspector for development testing:

```bash
# Test Python MCP server
npx @modelcontextprotocol/inspector uv run --script plugins/plugin-name/mcp/server.py

# Test TypeScript MCP server
npx @modelcontextprotocol/inspector npx tsx plugins/plugin-name/mcp/server.ts
```

Create pytest tests in `plugins/plugin-name/tests/test_mcp.py`:

```python
import pytest
from mcp.server import mcp


@pytest.mark.asyncio
async def test_tool_name():
    result = await mcp.tools["tool_name"](param="value")
    assert result["status"] == "success"
```

---

## Personal MCP vs Plugin MCP

**Plugin MCPs** (what we're building):
- Universal interface to plugin's core tooling
- Installed automatically with plugin
- Versioned with plugin
- Documented in plugin README

**Personal MCPs** (user-added):
- Individual agent customization
- External services (GitHub, Sentry, etc.)
- Personal workflows
- Not distributed with plugin

Example personal MCPs an agent might use alongside plugin MCPs:
- GitHub MCP (for issue tracking)
- Linear MCP (for task management)
- Sentry MCP (for error monitoring)
- Custom workspace MCPs

---

## Next Steps

### For plugin-creator
1. Create `plugins/plugin-creator/mcp/` directory
2. Implement `server.py` with 6 core tools
3. Add MCP config to `plugin.json`
4. Write tests in `tests/test_mcp.py`
5. Update README with MCP section
6. Create evaluation questions (see evaluation guide)

### For python3-development
1. Create `plugins/python3-development/mcp/` directory
2. Implement `server.py` with 6 quality tools
3. Add MCP config to `plugin.json`
4. Write tests in `tests/test_mcp.py`
5. Update README with MCP section
6. Create evaluation questions

### For holistic-linting
1. Create `plugins/holistic-linting/mcp/` directory
2. Implement `server.py` with 6 linting tools
3. Add MCP config to `plugin.json`
4. Write tests in `tests/test_mcp.py`
5. Update README with MCP section
6. Create evaluation questions

---

## References

- **MCP Best Practices:** `./reference/mcp_best_practices.md`
- **TypeScript Guide:** `./reference/node_mcp_server.md`
- **Python Guide:** `./reference/python_mcp_server.md`
- **Evaluation Guide:** `./reference/evaluation.md`
- **Example Implementation:** `plugins/agentskill-kaizen/mcp/server.py`
- **Warp MCP Docs:** External context attached to this query

---

## Conclusion

The agentskill-kaizen MCP implementation provides a proven template. Rolling out MCP servers to 7 additional high-value plugins will:

1. **Standardize access** - Agents use consistent tool interfaces
2. **Enable composition** - Tools can be chained programmatically
3. **Improve reliability** - Well-defined error handling
4. **Support testing** - Tools are testable units
5. **Document capabilities** - Tool schemas serve as API docs

Each plugin should expose its core capabilities as MCP tools, following the FastMCP pattern established by agentskill-kaizen.
