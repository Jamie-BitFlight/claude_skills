#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["fastmcp>=3.0"]
# ///
"""FastMCP v3 reference server for the fastmcp-creator plugin.

Exposes FastMCP v3 reference documentation as MCP resources via FileSystemProvider,
and provides tools for scaffolding, validating, version-checking, and searching docs.
"""

from __future__ import annotations

import ast
import importlib.metadata
import json
import re
import urllib.request
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

# ---------------------------------------------------------------------------
# Feature registry constants
# ---------------------------------------------------------------------------

KNOWN_FEATURES: frozenset[str] = frozenset(
    {
        "auth",
        "filesystem-provider",
        "tasks",
        "elicitation",
        "transforms",
        "tool-search",
        "code-mode",
        "multi-auth",
        "prefab-apps",
        "client",
        "middleware",
        "dependency-injection",
    }
)

# Features that map to server-level transforms (Fix 1)
TRANSFORM_FEATURES: dict[str, str] = {
    "tool-search": "BM25SearchTransform()",
    "code-mode": "CodeMode()",
}

# Features requiring fastmcp>=3.1 (Fix 3)
V31_FEATURES: frozenset[str] = frozenset(
    {
        "tool-search",
        "code-mode",
        "multi-auth",
        "prefab-apps",
    }
)

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns for validate_server (Fix 4)
# ---------------------------------------------------------------------------

_RE_TOOL_PARENS = re.compile(r"@\w+\.tool\s*\(\s*\)")
_RE_TASK_CONFIG = re.compile(r"task\s*=\s*TaskConfig\s*\(")
_RE_REQUIRE_AUTH = re.compile(r"\brequire_auth\b")
_RE_CONTRIB = re.compile(r"from\s+fastmcp\.contrib\b")

# ---------------------------------------------------------------------------
# Path resolution — uses __file__ for portability; NOT os.environ
# ---------------------------------------------------------------------------
_REFERENCES_DIR: Path = Path(__file__).parent.parent / "skills" / "fastmcp-creator" / "references"

_DOCS_WORKTREE: Path = (
    Path(__file__).parent.parent.parent.parent / ".claude" / "worktrees" / "fastmcp" / "docs"
)

# ---------------------------------------------------------------------------
# Server instantiation
# ---------------------------------------------------------------------------
mcp: FastMCP = FastMCP("fastmcp-creator-reference")

# Mount FileSystemProvider for hot-reloadable reference file resources
_fs_provider = FileSystemProvider(str(_REFERENCES_DIR), reload=True)
mcp.add_provider(_fs_provider)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
def scaffold_server(language: str, features: list[str], server_name: str) -> str:
    """Generate starter FastMCP v3 server code for the requested features.

    Args:
        language: Programming language — only "python" is supported (TypeScript
            was removed in v3 overhaul per Q2 resolution).
        features: List of features to include.  Recognised values:
            "auth", "filesystem-provider", "tasks", "elicitation", "transforms",
            "client", "middleware", "dependency-injection".  Unknown values are
            noted in a comment but do not cause an error.
        server_name: Python identifier used as the FastMCP instance name and
            filename suggestion, e.g. "my-server".

    Returns:
        A Python source string containing a runnable FastMCP v3 server starter
        with import stubs and feature-specific code blocks for each requested
        feature.  Includes PEP 723 inline metadata.
    """
    if language.lower() != "python":
        return (
            f"Language '{language}' is not supported. "
            "FastMCP v3 is Python-only (v3 overhaul removed TypeScript). "
            "Use @modelcontextprotocol/sdk for TypeScript."
        )

    feature_set = {f.lower() for f in features}
    unknown = feature_set - KNOWN_FEATURES

    safe_name = re.sub(r"[^a-z0-9_]", "_", server_name.lower())
    min_version = "3.1" if feature_set & V31_FEATURES else "3.0"

    # Build pip extras based on selected features (Fix 6)
    extras: list[str] = []
    if "tool-search" in feature_set:
        extras.append("search")
    if "code-mode" in feature_set:
        extras.append("code-mode")
    if "prefab-apps" in feature_set:
        extras.append("apps")
    if "tasks" in feature_set:
        extras.append("tasks")

    extras_suffix = "[" + ",".join(extras) + "]" if extras else ""
    fastmcp_dep = f"fastmcp{extras_suffix}>={min_version}"

    lines: list[str] = [
        "#!/usr/bin/env -S uv --quiet run --active --script",
        "# /// script",
        '# requires-python = ">=3.11"',
        f'# dependencies = ["{fastmcp_dep}"]',
        "# ///",
        '"""FastMCP v3 server: generated by fastmcp-creator scaffold_server."""',
        "",
        "from fastmcp import FastMCP",
        "from fastmcp import Context",
        "",
    ]

    if "auth" in feature_set:
        lines.append("from fastmcp.server.auth import require_scopes  # v3 auth")
    # multi-auth imports are emitted inside the commented config block (see below)
    if "filesystem-provider" in feature_set:
        lines.append("from fastmcp.server.providers import FileSystemProvider")
    if "tasks" in feature_set:
        pass  # tasks extra handled in PEP 723 dependencies
    if "tool-search" in feature_set:
        lines.append("from fastmcp.server.transforms.search import BM25SearchTransform  # v3.1")
    if "code-mode" in feature_set:
        lines.append(
            "from fastmcp.experimental.transforms.code_mode import CodeMode  # v3.1 experimental"
        )
    if "middleware" in feature_set:
        lines.append("from fastmcp.server.middleware import Middleware")
    if "dependency-injection" in feature_set:
        lines.append("from fastmcp.server.dependencies import Depends")
    if "elicitation" in feature_set:
        lines.append("from dataclasses import dataclass")
    if "prefab-apps" in feature_set:
        lines.append("from prefab_ui.components import Column, Heading")
        lines.append("from prefab_ui.app import PrefabApp")

    # Build transforms list for constructor (Fix 1: table-driven loop)
    transforms_args: list[str] = [
        TRANSFORM_FEATURES[f] for f in TRANSFORM_FEATURES if f in feature_set
    ]

    if transforms_args:
        transforms_str = ", ".join(transforms_args)
        lines += ["", f'mcp = FastMCP("{safe_name}", transforms=[{transforms_str}])', ""]
    else:
        lines += ["", f'mcp = FastMCP("{safe_name}")', ""]

    if "filesystem-provider" in feature_set:
        lines += [
            "# Mount FileSystemProvider for reference docs (reload=True for dev)",
            'mcp.add_provider(FileSystemProvider("./references", reload=True))',
            "",
        ]

    lines += [
        "@mcp.tool",
        "async def hello(message: str, ctx: Context) -> str:",
        '    """Echo a message back — replace with your tool implementation."""',
        "    await ctx.info(f'Processing: {message}')",
        "    return f'Hello from {safe_name}: {message}'",
        "",
        "@mcp.resource('resource://info')",
        "def server_info() -> str:",
        '    """Return basic server information."""',
        f'    return "Server: {safe_name}"',
        "",
    ]

    if "auth" in feature_set:
        lines += [
            "@mcp.tool(auth=require_scopes('read'))  # auth= kwarg, NOT stacked decorator",
            "async def protected_tool(ctx: Context) -> str:",
            '    """Tool requiring read scope — v3 auth pattern."""',
            "    return 'Authenticated!'",
            "",
        ]

    if "multi-auth" in feature_set:
        lines += [
            "# --- MultiAuth configuration (v3.1) ---",
            "# Uncomment the imports and config below to enable multi-auth:",
            "# from fastmcp.server.auth import MultiAuth, OAuthProxy",
            "# from fastmcp.server.auth.providers.jwt import JWTVerifier",
            "#",
            "# auth = MultiAuth(",
            "#     server=OAuthProxy(",
            '#         issuer_url="https://your-idp.example.com",',
            '#         client_id="...",',
            '#         client_secret="...",',
            '#         base_url="http://localhost:8000",',
            "#     ),",
            "#     verifiers=[",
            '#         JWTVerifier(jwks_uri="https://your-idp.example.com/.well-known/jwks.json"),',
            "#     ],",
            "# )",
            "# mcp = FastMCP('server', auth=auth)  # pass auth= to constructor",
            "",
        ]

    if "tasks" in feature_set:
        lines += [
            "@mcp.tool(task=True)  # task=True, NOT task=TaskConfig()",
            "async def long_running_task(payload: str, ctx: Context) -> str:",
            '    """Long-running task executed via Docket (requires fastmcp[tasks])."""',
            "    await ctx.report_progress(50, 100)",
            "    return f'Done: {payload}'",
            "",
        ]

    if "elicitation" in feature_set:
        lines += [
            "@dataclass",
            "class UserInfo:",
            '    """Schema for elicitation response."""',
            "    name: str",
            "",
            "@mcp.tool",
            "async def elicit_example(ctx: Context) -> str:",
            '    """Demonstrate multi-turn elicitation."""',
            "    result = await ctx.elicit(",
            "        message='What is your name?',",
            "        response_type=UserInfo,  # v3: response_type, NOT schema=",
            "    )",
            "    if hasattr(result, 'data') and result.data:",
            "        return f'Hello, {result.data.name}!'",
            "    return 'Elicitation was declined or cancelled.'",
            "",
        ]

    if "prefab-apps" in feature_set:
        lines += [
            "@mcp.tool(app=True)",
            "def dashboard() -> PrefabApp:",
            '    """Return an interactive UI dashboard — requires fastmcp[apps]."""',
            "    with Column(gap=4) as view:",
            f'        Heading("{safe_name} Dashboard")',
            "    return PrefabApp(view=view)",
            "",
        ]

    if "transforms" in feature_set and not transforms_args:
        lines += [
            "# transforms: use mcp.mount(sub_server, namespace='ns') for server composition",
            "# or mcp.add_transform(YourTransform()) for custom transforms",
            "",
        ]

    if unknown:
        lines += [
            f"# NOTE: Unrecognised features (not scaffolded): {', '.join(sorted(unknown))}",
            "",
        ]

    lines += ['if __name__ == "__main__":', "    mcp.run()"]

    return "\n".join(lines)


@mcp.tool
def validate_server(path: str) -> dict[str, list[str]]:
    """Check a FastMCP server file for v3 syntax errors and deprecated patterns.

    Validates:
    - ``@mcp.tool()`` with parentheses (should be ``@mcp.tool``)
    - ``task=TaskConfig(...)`` usage (should be ``task=True``)
    - ``require_auth`` usage (removed in v3; use ``require_scopes``)
    - Missing ``mcp = FastMCP(...)`` constructor

    Does NOT validate MCP protocol compliance or plugin YAML frontmatter.

    Args:
        path: Absolute or relative path to a Python file containing a FastMCP server.

    Returns:
        A dict with keys ``"errors"`` and ``"warnings"``, each a list of strings.
        An empty ``"errors"`` list means no v3 pattern violations were found.
    """
    errors: list[str] = []
    warnings: list[str] = []

    file_path = Path(path)
    if not file_path.exists():
        errors.append(f"File not found: {path}")
        return {"errors": errors, "warnings": warnings}

    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"Cannot read file: {exc}")
        return {"errors": errors, "warnings": warnings}

    # Check syntax first
    try:
        ast.parse(source)
    except SyntaxError as exc:
        errors.append(f"Python syntax error at line {exc.lineno}: {exc.msg}")
        return {"errors": errors, "warnings": warnings}

    # Pattern checks (line-by-line for precise line numbers)
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()

        # @mcp.tool() with parentheses — canonical v3 is @mcp.tool
        if _RE_TOOL_PARENS.search(stripped):
            errors.append(
                f"Line {lineno}: `@mcp.tool()` with empty parentheses — "
                "v3 canonical syntax is `@mcp.tool` (no parentheses)"
            )

        # task=TaskConfig(...) — v3 uses task=True
        if _RE_TASK_CONFIG.search(stripped):
            errors.append(
                f"Line {lineno}: `task=TaskConfig(...)` is invalid in v3 — use `task=True` instead"
            )

        # require_auth — removed in v3
        if _RE_REQUIRE_AUTH.search(stripped):
            errors.append(
                f"Line {lineno}: `require_auth` was removed in v3 — use `require_scopes` from `fastmcp.server.auth`"
            )

        # v2-only import patterns
        if _RE_CONTRIB.search(stripped):
            warnings.append(
                f"Line {lineno}: `fastmcp.contrib` import — verify this module exists in v3 (contrib was restructured)"
            )

    # Check for FastMCP constructor
    if not re.search(r"\bFastMCP\s*\(", source):
        errors.append(
            "No `FastMCP(...)` constructor found — the server object must be created with `mcp = FastMCP('name')`"
        )

    return {"errors": errors, "warnings": warnings}


@mcp.tool
def version_check() -> dict[str, str]:
    """Return installed fastmcp version and latest available on PyPI.

    Compares the locally installed fastmcp package against the current PyPI
    release.  Does NOT compare against the local worktree version (which may
    be a development pre-release).

    Returns:
        A dict with keys ``"installed"``, ``"latest"``, and ``"up_to_date"``.
        ``"up_to_date"`` is the string ``"true"`` or ``"false"`` for easy
        downstream string comparisons.  If either version cannot be determined,
        the corresponding key contains an error message string.
    """
    # Installed version
    try:
        installed = importlib.metadata.version("fastmcp")
    except importlib.metadata.PackageNotFoundError:
        installed = "not-installed"

    # Latest on PyPI
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/fastmcp/json", timeout=5) as resp:
            data = json.loads(resp.read())
        latest = data["info"]["version"]
    except Exception as exc:  # noqa: BLE001
        latest = f"pypi-error: {exc}"

    up_to_date = "true" if installed == latest else "false"
    return {"installed": installed, "latest": latest, "up_to_date": up_to_date}


@mcp.tool
def search_docs(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the local FastMCP v3 docs worktree for matching content.

    Performs case-insensitive keyword search across ``.mdx`` files in
    ``.claude/worktrees/fastmcp/docs/``.  Returns file paths and matching
    snippets — does not summarise or interpret results.

    Args:
        query: Free-text search query.  All words must appear in a matching
            line (AND logic).
        max_results: Maximum number of results to return (default 5).

    Returns:
        A list of dicts, each with keys ``"file"`` (relative path from docs
        root), ``"section"`` (nearest preceding heading or empty string), and
        ``"snippet"`` (the matching line, stripped of leading/trailing whitespace).
        Returns an empty list if the docs worktree does not exist.
    """
    if not _DOCS_WORKTREE.is_dir():
        return []

    terms = [t.lower() for t in query.split() if t]
    results: list[dict[str, str]] = []
    heading_pattern = re.compile(r"^#+\s+(.+)$")

    for mdx_file in sorted(_DOCS_WORKTREE.rglob("*.mdx")):
        if len(results) >= max_results:
            break
        try:
            lines = mdx_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        current_heading = ""
        for line in lines:
            heading_match = heading_pattern.match(line)
            if heading_match:
                current_heading = heading_match.group(1)
            lower_line = line.lower()
            if all(t in lower_line for t in terms):
                results.append(
                    {
                        "file": str(mdx_file.relative_to(_DOCS_WORKTREE)),
                        "section": current_heading,
                        "snippet": line.strip(),
                    }
                )
                if len(results) >= max_results:
                    break

    return results


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt
def scaffold_new_server() -> str:
    """Prompt: guide the user through scaffolding a new FastMCP v3 server.

    Asks for server name, required features, and transport type, then instructs
    the model to call ``scaffold_server()`` with the collected inputs.

    Returns:
        A structured prompt string.
    """
    return """\
You are helping a developer scaffold a new FastMCP v3 server.

Ask the user the following questions (you may ask all at once):

1. **Server name** — what should the server be called? (used as the FastMCP instance name)
2. **Features** — which features do you need? Choose any that apply:
   - `auth` — OAuth / token-based authentication with `require_scopes`
   - `multi-auth` — compose OAuth + multiple token verifiers (v3.1)
   - `filesystem-provider` — serve files as MCP resources via FileSystemProvider
   - `tasks` — long-running background tasks (requires `fastmcp[tasks]` extra)
   - `elicitation` — multi-turn user input prompts
   - `transforms` — mount sub-servers with namespace transforms
   - `tool-search` — BM25/regex search transforms for large tool catalogs (v3.1)
   - `code-mode` — experimental CodeMode sandbox transform (v3.1)
   - `prefab-apps` — declarative UI components via Prefab Apps (v3.1, experimental)
   - `middleware` — request/response middleware
   - `dependency-injection` — FastAPI-style dependency injection
3. **Transport** — how will clients connect?
   - `stdio` — default, works with Claude Desktop and Claude Code
   - `sse` / `streamable-http` — HTTP transport for remote clients

Once you have the answers, call the `scaffold_server` tool with:
- `language="python"`
- `features=[<list of chosen features>]`
- `server_name=<chosen name>`

Show the generated code to the user and explain what each section does.
"""


@mcp.prompt
def choose_provider() -> str:
    """Prompt: help the user choose the right FastMCP provider for their use case.

    Presents the provider decision flowchart and asks clarifying questions to
    guide the user toward the correct provider type.

    Returns:
        A structured prompt string with the decision flowchart.
    """
    return """\
You are helping a developer choose the right FastMCP v3 Provider for their server.

FastMCP v3 built-in providers:

| Provider | Use case |
|---|---|
| `LocalProvider` | Default — tools/resources/prompts defined directly on the server |
| `FileSystemProvider` | Serve files (markdown, JSON, etc.) as MCP resources with hot-reload |
| `FastMCPProvider` | Mount another local FastMCP server as a sub-server |
| `ProxyProvider` | Bridge a remote HTTP/SSE MCP server behind local stdio |
| `SkillsProvider` | Expose Claude/Cursor skill files (`skill://` URIs) as resources |
| `OpenAPIProvider` | Auto-generate tools from an OpenAPI 3.x spec |

Ask the user these questions to guide the choice:

1. Are you serving **files** (docs, configs, reference material) as resources? → `FileSystemProvider`
2. Are you **wrapping a remote HTTP MCP server** for local stdio access? → `ProxyProvider`
3. Are you **composing multiple FastMCP servers** into one? → `FastMCPProvider` + `mount()`
4. Are you exposing **Claude/Cursor skills** as resources? → `SkillsProvider`
5. Do you have an **OpenAPI spec** and want tools auto-generated? → `OpenAPIProvider`
6. None of the above? → `LocalProvider` (default, no explicit import needed)

After identifying the right provider, show the user the correct import and usage pattern.
Reference: `search_docs(query="provider overview")` for the latest docs.
"""


@mcp.prompt
def migrate_from_v2() -> str:
    """Prompt: guide migration of a FastMCP v2 server to v3.

    Asks for the v2 server file path, then returns a migration checklist
    sourced from the FastMCP v3 migration documentation.

    Returns:
        A structured prompt string with the migration checklist.
    """
    return """\
You are helping a developer migrate a FastMCP v2 server to v3.

First, ask the user for the path to their v2 server file.

Then run `validate_server(path=<provided path>)` to identify v3 pattern violations.

After validation, apply this migration checklist:

## Required changes (breaking)

- [ ] `@mcp.tool()` → `@mcp.tool` (remove empty parentheses — v3 canonical syntax)
- [ ] `task=TaskConfig(mode="required")` → `task=True` (TaskConfig removed in v3)
- [ ] `require_auth(...)` → `@mcp.tool(auth=require_scopes('scope'))` from `fastmcp.server.auth` (require_auth removed; use auth= kwarg, not stacked decorator)
- [ ] Provider imports: update from `fastmcp.server.providers` (v3 module path)

## Recommended changes

- [ ] Switch to `async def` for all tools that perform I/O (v3 is fully async)
- [ ] Replace `@mcp.resource("template://{id}")` with explicit `@mcp.resource` patterns
- [ ] Review context usage: `ctx.log()` → `ctx.info()` / `ctx.warning()` / `ctx.error()`

## New v3 features to consider

- `FileSystemProvider` for serving reference files without manual resource registration
- `SkillsProvider` for exposing skills as `skill://` URI resources
- `require_scopes` for fine-grained per-tool auth
- `@mcp.tool(task=True)` for long-running operations (requires `fastmcp[tasks]` extra)

## New v3.1 features to consider

- `transforms=[BM25SearchTransform()]` — server-level search transforms for large tool catalogs
- `CodeMode()` transform — experimental sandboxed Python execution for tool invocation
- `MultiAuth` — compose OAuth proxy with JWT verifiers for hybrid auth
- `PropelAuthProvider` — PropelAuth integration for OAuth + token introspection
- `@mcp.tool(app=True)` + Prefab Apps — declarative UI components (experimental)
- `fastmcp run -m module` — run servers as Python modules
- `FASTMCP_TRANSPORT` env var — set default transport without CLI flag

For full migration details, call: `search_docs(query="migrating from fastmcp 2")`
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
