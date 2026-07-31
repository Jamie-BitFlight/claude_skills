# MCP Quick Start Guide

## Adding MCP to Your Plugin in 30 Minutes

This guide walks you through adding an MCP server to a plugin using the proven agentskill-kaizen pattern.

---

## Prerequisites

- Python 3.11+ with uv installed
- Your plugin has Python scripts or utilities
- Basic understanding of async Python

---

## Step 1: Create MCP Directory (1 min)

```bash
cd plugins/your-plugin/
mkdir mcp
touch mcp/server.py
chmod +x mcp/server.py
```

---

## Step 2: Scaffold Server (5 min)

Copy this template to `mcp/server.py`:

```python
#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
# ]
# ///
"""Your Plugin MCP Server.

Brief description of what this MCP provides.

Tools:
    tool_one - Description
    tool_two - Description
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("your-plugin", mask_error_details=False)

_READONLY_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

_DESTRUCTIVE_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": True,
    "openWorldHint": False,
}

# Your tools go here

if __name__ == "__main__":
    mcp.run()
```

---

## Step 3: Add Your First Tool (10 min)

Example: Wrap an existing script function

```python
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def validate_something(file_path: str, *, context: Context) -> dict[str, Any]:
    """Validate a file against rules.

    Args:
        file_path: Path to file to validate
        context: FastMCP context for progress reporting

    Returns:
        Dict with 'status' and 'errors' if any found

    Raises:
        ToolError: If file not found or validation fails
    """
    await context.info(f"Validating {file_path}...")

    # If you have an existing script function:
    from your_plugin.validators import validate_file

    result = await asyncio.to_thread(validate_file, file_path)

    if result.errors:
        return {"status": "invalid", "errors": [str(e) for e in result.errors]}

    return {"status": "valid"}
```

**Tool anatomy:**
- `@mcp.tool(annotations=...)` - Declares this as an MCP tool
- `async def` - All tools are async
- Type hints on parameters - Required for schema generation
- `*, context: Context` - Keyword-only context parameter
- Docstring - First line = tool description, rest = details
- `await context.info(...)` - Progress updates for user
- `return dict` - Always return structured data

---

## Step 4: Add to plugin.json (2 min)

Edit `.claude-plugin/plugin.json`:

```json
{
  "name": "your-plugin",
  "version": "1.0.0",
  "mcpServers": {
    "your-plugin": {
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

---

## Step 5: Test with Inspector (5 min)

```bash
# Test the MCP server
npx @modelcontextprotocol/inspector \
  uv run --script plugins/your-plugin/mcp/server.py

# You should see:
# 1. Server starts successfully
# 2. Tools appear in the list
# 3. You can call tools interactively
# 4. Parameters are validated
# 5. Errors are caught gracefully
```

---

## Step 6: Add Tests (5 min)

Create `tests/test_mcp.py`:

```python
import pytest
from mcp.server import mcp


@pytest.mark.asyncio
async def test_validate_something_valid():
    """Test validation with valid file."""
    result = await mcp.tools["validate_something"](file_path="tests/fixtures/valid.md")
    assert result["status"] == "valid"


@pytest.mark.asyncio
async def test_validate_something_invalid():
    """Test validation with invalid file."""
    result = await mcp.tools["validate_something"](file_path="tests/fixtures/invalid.md")
    assert result["status"] == "invalid"
    assert len(result["errors"]) > 0
```

Run tests:

```bash
pytest tests/test_mcp.py -v
```

---

## Step 7: Document in README (2 min)

Add to your plugin's README.md:

```markdown
## MCP Server

This plugin provides an MCP server with programmatic access to its tools.

### Available Tools

**validate_something** - Validate files against plugin rules
- Input: `file_path` (string)
- Output: `{"status": "valid" | "invalid", "errors": [...]}`
- Annotations: read-only, idempotent

### Testing

```bash
npx @modelcontextprotocol/inspector \
  uv run --script "${CLAUDE_PLUGIN_ROOT}/mcp/server.py"
```
```

---

## Common Patterns

### Pattern 1: Wrapping CLI Scripts

```python
# If you have: scripts/my_tool.py with main(args)
import subprocess

@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def run_my_tool(
    target: str,
    *,
    context: Context,
) -> dict[str, Any]:
    """Run my_tool on target."""
    await context.info(f"Processing {target}...")

    result = await asyncio.to_thread(
        subprocess.run,
        ["python", "scripts/my_tool.py", target],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise ToolError(f"Tool failed: {result.stderr}")

    return {"output": result.stdout}
```

### Pattern 2: File Operations

```python
import pathlib


@mcp.tool(annotations=_DESTRUCTIVE_ANNOTATIONS)
async def modify_file(file_path: str, new_content: str, *, context: Context) -> dict[str, Any]:
    """Safely modify a file."""
    path = pathlib.Path(file_path)

    # Validate path (prevent traversal)
    if ".." in path.parts:
        raise ToolError("Path traversal not allowed")

    if not path.exists():
        raise ToolError(f"File not found: {file_path}")

    await context.info(f"Backing up {file_path}...")

    # Backup original
    backup = path.with_suffix(path.suffix + ".bak")
    await asyncio.to_thread(path.rename, backup)

    try:
        await context.info(f"Writing new content...")
        await asyncio.to_thread(path.write_text, new_content)
        return {"status": "success", "backup": str(backup)}
    except Exception as e:
        # Restore backup on failure
        await asyncio.to_thread(backup.rename, path)
        raise ToolError(f"Failed to modify: {e}") from e
```

### Pattern 3: Progress Updates

```python
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def analyze_directory(directory: str, *, context: Context) -> dict[str, Any]:
    """Analyze all files in directory."""
    path = pathlib.Path(directory)
    files = list(path.rglob("*.py"))

    await context.info(f"Found {len(files)} files to analyze")

    results = []
    for i, file in enumerate(files, 1):
        await context.info(f"Analyzing {file.name} ({i}/{len(files)})")
        result = await asyncio.to_thread(analyze_file, file)
        results.append(result)

    await context.info("Analysis complete")

    return {"total_files": len(files), "results": results}
```

### Pattern 4: Error Handling

```python
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def risky_operation(param: str, *, context: Context) -> dict[str, Any]:
    """Operation that might fail."""
    try:
        await context.info("Starting risky operation...")

        result = await asyncio.to_thread(do_something, param)

        if not result.success:
            raise ToolError(
                f"Operation failed: {result.error}. Try adjusting the {result.problematic_field} parameter."
            )

        return {"status": "success", "data": result.data}

    except FileNotFoundError as e:
        raise ToolError(f"Required file not found: {e.filename}") from e
    except ValueError as e:
        raise ToolError(f"Invalid parameter: {e}") from e
    except Exception as e:
        raise ToolError(f"Unexpected error: {e}") from e
```

---

## Debugging Tips

### Server won't start

```bash
# Check Python version
python --version  # Should be 3.11+

# Check if uv is installed
uv --version

# Try running directly
uv run --script mcp/server.py

# Check for syntax errors
python -m py_compile mcp/server.py
```

### Tools not appearing

```bash
# Check if @mcp.tool decorator is present
grep -n "@mcp.tool" mcp/server.py

# Verify if __name__ == "__main__" block exists
grep -A2 "__name__" mcp/server.py

# Test with verbose output
uv run --script mcp/server.py --help
```

### Tools failing

```bash
# Check error messages in inspector
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test tool in isolation
python -c "
import asyncio
from mcp.server import mcp
result = asyncio.run(mcp.tools['your_tool'](param='test'))
print(result)
"
```

---

## Checklist

Before committing your MCP implementation:

- [ ] Server starts without errors
- [ ] All tools have clear names and docstrings
- [ ] Type hints on all parameters
- [ ] Progress updates via `context.info()`
- [ ] Proper error handling with `ToolError`
- [ ] Annotations match tool behavior
- [ ] Tests cover happy path and errors
- [ ] README documents all tools
- [ ] plugin.json declares MCP server
- [ ] Inspector testing passes

---

## Next Steps

1. Add more tools (one per core operation)
2. Write comprehensive tests
3. Create evaluation questions
4. Update plugin README
5. Submit PR with MCP implementation

---

## Getting Help

- **Example:** `plugins/agentskill-kaizen/mcp/server.py`
- **Docs:** `docs/mcp-architecture-analysis.md`
- **Roadmap:** `docs/mcp-implementation-roadmap.md`
- **FastMCP:** <https://github.com/jlowin/fastmcp>
- **MCP Spec:** <https://modelcontextprotocol.io/>

---

*Time budget: 30 minutes for basic implementation, 1-2 hours for comprehensive tool coverage*
