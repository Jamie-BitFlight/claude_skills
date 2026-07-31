---
name: holistic-linting-resolver
description: Linter-specific resolution workflows for ruff, mypy, pyright, and basedpyright. Provides systematic root-cause analysis procedures, suppression gates, and verification steps. Use when resolving linting errors as a sub-agent, implementing fixes systematically, or conducting type flow analysis.
---

# Holistic Linting: Resolution Workflows

This skill provides systematic resolution procedures for Python linting tools. Sub-agents executing linting resolution tasks MUST follow the appropriate workflow based on the linter reporting issues.

## When to Use This Skill

Use this skill when you are a **sub-agent** assigned to resolve linting issues in a specific file. This skill provides detailed workflows for:

- Ruff (style, import, and code quality checks)
- Mypy (type checking)
- Pyright/Basedpyright (strict type checking)

**Do NOT use this skill** if you are an orchestrator. Orchestrators should use the holistic-linting-orchestrator skill for delegation workflows.

## Common Resolution Methodology

All linter-specific workflows share these common steps. Apply them in order before the linter-specific procedures.

### 1. Load python3-development Skill

Before implementing any fixes:

```claude
Skill(skill: "python3-development:python3-development")
```

**Motivation**: Ensures fixes follow Python 3.11+ standards, modern typing patterns, and project conventions.

### 2. Suppression Gate (MANDATORY)

Before implementing any fix, verify it is a code change — not suppression. Each category below is an immediate STOP:

**Inline suppression comments:**
- Adding `# noqa`, `# type: ignore`, `# pyright: ignore`, `# pylint: disable`, or any suppression comment

**Configuration-level suppression (equally forbidden):**
- Adding a rule to `[tool.ruff.lint] ignore = [...]` in `pyproject.toml`
- Adding an entry to `[tool.ruff.lint.per-file-ignores]`
- Changing `[tool.pyright] reportX = "warning"` or any other severity downgrade
- Adding `disable_error_code = [...]` to `[tool.mypy]`
- Modifying any linter config file (`pyproject.toml`, `ruff.toml`, `mypy.ini`, `.flake8`, `setup.cfg`) to reduce the scope, severity, or applicability of a rule

**Reason**: A pyproject.toml severity downgrade achieves the same silencing effect as `# type: ignore` but at project scope, affecting all future code. Both are standards degradation. Neither is a code fix.

**Deletion-as-resolution (equally forbidden):**
- Removing a function, class, method, or test to eliminate the linting error within it
- Deleting lines of code solely because they contain a linting error

If any proposed fix falls into these categories: **STOP**.

**When no code restructuring works** (minimum 2 approaches attempted), document the constraint and return UNRESOLVED:

1. What you tried (each approach, minimum 2)
2. Why each approach failed (exact linter error produced)
3. The fundamental constraint (e.g., "ruff cannot evaluate `sys.platform` branches")

Return this as an **UNRESOLVED** item in your resolution report. The orchestrator will surface it to the user for a human decision on whether to suppress, reconfigure, or accept the limitation.

### 3. Check Architectural Context

Examine how this code fits into the broader system:

- What does this function/module do?
- How is it called by other code?
- Are there similar patterns elsewhere in the codebase?

Use Grep to find usage patterns:

```bash
uv run rg "function_name" --type py
```

### 4. Verify Resolution

After implementing fixes, rerun the appropriate linter on the primary file:

```bash
# For Ruff:
uv run ruff check /path/to/file.py

# For Mypy:
uv run mypy /path/to/file.py

# For Pyright/Basedpyright:
uv run pyright /path/to/file.py
# or
uv run basedpyright /path/to/file.py
```

**Verify incidentally modified files**: If you touched any file other than the primary target during the fix (e.g., added an import to a utility module, moved a function, updated a type alias), run the linter on those files too:

```bash
uv run ruff check /path/to/incidentally/modified/file.py
uv run mypy /path/to/incidentally/modified/file.py
```

All incidentally modified files must also produce zero errors before resolution is complete.

**Record the before and after issue counts** in the resolution report header:

```markdown
**Issues before resolution:** N (from initial linter run)
**Issues after resolution:** 0 (from final linter run — must be 0 for all touched files)
**UNRESOLVED items:** N (must be explicitly listed even if 0)
```

**Pre-existing issues detected**: If the initial linter run reveals issues in files you did not touch — see [Pre-Existing Issues Protocol](../holistic-linting/references/pre-existing-issues-protocol.md). Every detected issue gets recorded. Silence is not permitted.

## Ruff Resolution Workflow

**When to use**: Linting errors with ruff rule codes (E, F, W, B, S, I, UP, C90, N, etc.)

**Resolution Process**:

1. **Research the Rule**

   Use ruff's built-in documentation system:

   ```bash
   ruff rule {RULE_CODE}
   ```

   Examples:

   ```bash
   ruff rule F401  # unused-import
   ruff rule E501  # line-too-long
   ruff rule B006  # mutable-default-argument
   ```

   This command provides:

   - What the rule prevents (design principle)
   - When code violates the rule
   - Example of violating code
   - Example of resolved code
   - Configuration options

2. **Read Rule Documentation Output**

   The ruff rule output contains critical information:

   - **Principle**: Why this pattern is problematic
   - **Bad Pattern**: What code triggers the rule
   - **Good Pattern**: How to fix it correctly

   **Motivation**: Understanding the principle prevents similar issues in other locations.

3. **Read the Affected Code**

   Read the complete file containing the linting error:

   ```claude
   Read("/path/to/file.py")
   ```

   Focus on:

   - The line with the error
   - Surrounding context (5-10 lines before/after)
   - Related function/class definitions

4. **Apply Common Methodology**

   Follow steps 1-4 in the Common Resolution Methodology section above:
   - Load python3-development skill
   - Pass through Suppression Gate
   - Check Architectural Context
   - Verify Resolution

5. **Implement Elegant Fix**

   Apply the fix following these principles:

   - Address the root cause, not the symptom
   - Follow modern Python patterns from python3-development skill
   - Maintain or improve code readability
   - Consider performance and maintainability
   - Add comments only if the fix is non-obvious


## Mypy Resolution Workflow

**When to use**: Type checking errors with mypy error codes (attr-defined, arg-type, return-value, etc.)

**Resolution Process**:

1. **Research the Error Code**

   Mypy errors contain error codes in brackets like `[attr-defined]` or `[arg-type]`.

   Look up the error code in locally-cached documentation:

   ```claude
   Read("./references/mypy-docs/error_code_list.rst")
   Read("./references/mypy-docs/error_code_list2.rst")
   ```

   Search for the error code:

   ```bash
   grep -n "error-code-{CODE}" ./references/mypy-docs/*.rst
   ```

   **Motivation**: Mypy error codes map to specific type safety principles. Understanding the principle prevents misunderstanding type relationships.

2. **Read Error Code Documentation**

   The mypy documentation explains:

   - What type safety principle is violated
   - When this is an error (type violations)
   - When this is NOT an error (valid patterns)
   - Example of error-producing code
   - Example of corrected code

   **Key insight**: Mypy errors often indicate misunderstanding about what types a function accepts or returns.

3. **Trace Type Flow**

   Follow the data flow to understand type relationships:

   a. **Read the error location**:

   ```claude
   Read("/path/to/file.py")
   ```

   b. **Identify the type mismatch**:

   - What type does mypy think the variable is?
   - What type does mypy expect?
   - Where does the variable get its type?

   c. **Trace upstream**:

   - Read function signatures
   - Check return type annotations
   - Review variable assignments

   d. **Check library type stubs**:

   - If the error involves a library, check its type stubs
   - Use `python -c "import library; print(library.__file__)"` to locate
   - Read `.pyi` stub files or `py.typed` marker

4. **Apply Common Methodology**

   Follow steps 1-4 in the Common Resolution Methodology section above:
   - Load python3-development skill
   - Pass through Suppression Gate
   - Check Architectural Context
   - Verify Resolution

5. **Implement Elegant Fix**

   Choose the appropriate fix strategy:

   **Strategy A: Fix the type annotation** (if annotation is wrong)

   ```python
   # Before: Function returns dict but annotated as returning Response
   def get_data() -> Response:
       return {"key": "value"}  # mypy error: Incompatible return value type


   # After: Correct annotation to match actual return
   def get_data() -> dict[str, str]:
       return {"key": "value"}
   ```

   **Strategy B: Fix the implementation** (if annotation is correct)

   ```python
   # Before: Function should return Response but returns dict
   def get_data() -> Response:
       return {"key": "value"}  # mypy error: Incompatible return value type


   # After: Fix implementation to return correct type
   def get_data() -> Response:
       return Response(data={"key": "value"})
   ```

   **Strategy C: Add type narrowing** (if type is conditional)

   ```python
   # Before: Mypy can't prove value is not None
   def process(value: str | None) -> str:
       return value.upper()  # mypy error: Item "None" has no attribute "upper"


   # After: Add type guard
   def process(value: str | None) -> str:
       if value is None:
           raise ValueError("value cannot be None")
       return value.upper()
   ```

   **Strategy D: Use TypeGuard for complex narrowing**

   ```python
   from typing import TypeGuard


   def is_valid_response(data: dict[str, Any]) -> TypeGuard[dict[str, str]]:
       return all(isinstance(v, str) for v in data.values())


   def process(data: dict[str, Any]) -> dict[str, str]:
       if not is_valid_response(data):
           raise ValueError("Invalid data format")
       return data  # mypy now knows this is dict[str, str]
   ```


## Pyright/Basedpyright Resolution Workflow

**When to use**: Type checking errors with pyright diagnostic rules (reportGeneralTypeIssues, reportOptionalMemberAccess, reportUnknownVariableType, etc.)

**Resolution Process**:

1. **Research the Diagnostic Rule**

   Pyright errors reference diagnostic rule names like `reportOptionalMemberAccess` or `reportGeneralTypeIssues`.

   Look up the rule in basedpyright documentation:

   **For rule settings and descriptions**:

   Use MCP tools for documentation lookup (in order of preference):

   ```claude
   # Option 1 (Preferred): Use Ref MCP for high-fidelity documentation
   mcp__Ref__ref_search_documentation(query="basedpyright {RULE_NAME} diagnostic rule configuration")
   # Then read the URL from results:
   mcp__Ref__ref_read_url(url="<exact_url_from_search_results>")

   # Option 2: Use exa for code context if Ref doesn't have it
   mcp__exa__get_code_context_exa(query="basedpyright {RULE_NAME} diagnostic rule examples")

   # Fallback: Use WebFetch only if MCP tools don't work
   WebFetch(url="https://docs.basedpyright.com/latest/configuration/config-files/",
           prompt="Find documentation for diagnostic rule {RULE_NAME}")
   ```

   **For features and PEP support**:

   ```claude
   # Option 1 (Preferred): Use Ref MCP for high-fidelity documentation
   mcp__Ref__ref_search_documentation(query="basedpyright Python typing features PEP {RULE_NAME}")
   mcp__Ref__ref_read_url(url="<exact_url_from_search_results>")

   # Fallback: Use WebFetch only if MCP tools don't work
   WebFetch(url="https://docs.basedpyright.com/latest/getting_started/features/",
           prompt="Explain what Python typing features and PEPs are covered related to {RULE_NAME}")
   ```

   **Motivation**: Pyright is more strict than mypy in many areas. Understanding what the rule enforces helps identify whether the issue is a genuine type safety problem or overly strict checking.

2. **Read Diagnostic Rule Documentation**

   The basedpyright documentation explains:

   - What type safety issue the rule detects
   - Configuration levels (basic, standard, strict, all)
   - Whether the rule can be disabled per-project
   - Related typing features and PEPs

3. **Read the Affected Code**

   Read the complete file containing the type error:

   ```claude
   Read("/path/to/file.py")
   ```

   Focus on:

   - The exact line with the error
   - Type annotations in the surrounding function/class
   - Import statements for typing constructs

4. **Understand the Type Inference Issue**

   Pyright has sophisticated type inference. Common issues:

   **Optional member access**:

   ```python
   # Error: reportOptionalMemberAccess
   value: str | None = get_value()
   result = value.upper()  # Error: 'value' could be 'None'
   ```

   **Unknown variable type**:

   ```python
   # Error: reportUnknownVariableType
   result = some_function()  # some_function has no return type annotation
   ```

   **Type narrowing not recognized**:

   ```python
   # Error: pyright doesn't recognize the narrowing
   value: int | str = get_value()
   if type(value) == int:  # Use isinstance() instead
       result = value + 1
   ```

5. **Apply Common Methodology**

   Follow steps 1-4 in the Common Resolution Methodology section above:
   - Load python3-development skill
   - Pass through Suppression Gate
   - Check Architectural Context
   - Verify Resolution

6. **Implement Elegant Fix**

   Choose the appropriate fix strategy:

   **Strategy A: Add type narrowing guards**

   ```python
   # Before:
   def process(value: str | None) -> str:
       return value.upper()  # reportOptionalMemberAccess


   # After:
   def process(value: str | None) -> str:
       if value is None:
           raise ValueError("value is required")
       return value.upper()  # pyright knows value is str here
   ```

   **Strategy B: Add missing type annotations**

   ```python
   # Before:
   def fetch_data():  # reportUnknownVariableType on callers
       return {"key": "value"}


   # After:
   def fetch_data() -> dict[str, str]:
       return {"key": "value"}
   ```

   **Strategy C: Use assert for type narrowing**

   ```python
   # Before:
   value: int | str = get_value()
   result = value + 1  # reportGeneralTypeIssues

   # After:
   value: int | str = get_value()
   assert isinstance(value, int), "Expected int"
   result = value + 1  # pyright knows value is int
   ```

   **Strategy D: Use typing.cast for complex cases**

   ```python
   from typing import cast

   # Before:
   data: dict[str, Any] = get_data()
   name: str = data["name"]  # reportUnknownVariableType

   # After (if you've validated data structure):
   from typing import TypedDict


   class UserData(TypedDict):
       name: str
       age: int


   data = cast(UserData, get_data())
   name: str = data["name"]  # pyright knows this is str
   ```

   **When all strategies fail**: Apply the Suppression Gate — document approaches tried and fundamental constraint, then return UNRESOLVED to the orchestrator. The pyproject.toml severity level is a project configuration decision, not a linting resolution action. Config changes require explicit user approval via the UNRESOLVED escalation path, not autonomous agent action.

## Integration: Resolution Process with python3-development

All linter resolution workflows integrate with the python3-development skill at the implementation stage. This integration ensures:

1. **Modern Python Patterns**: Fixes use Python 3.11+ syntax

   - Native generics (`list[str]` not `List[str]`)
   - Union syntax (`str | None` not `Optional[str]`)
   - Structural pattern matching where appropriate

2. **Idiomatic Code**: Solutions follow Python best practices

   - Clear naming conventions
   - Appropriate use of comprehensions
   - Proper exception handling
   - Single Responsibility Principle

3. **Type Safety**: Type annotations are complete and accurate

   - Precise return types
   - Correct parameter types
   - Proper use of generics and protocols

4. **Project Consistency**: Fixes align with existing codebase patterns
   - Consistent with project's CLAUDE.md standards
   - Matches existing module organization
   - Follows project-specific conventions

**Activation pattern**:

```text
[Identify linting issue] → [Research rule] → [Read code] → [Check architecture]
→ [Load python3-development skill] → [Implement elegant fix] → [Verify]
```

## Related Skills

- [holistic-linting](../holistic-linting/SKILL.md) - Core linting skill with linter detection and resource documentation
- [holistic-linting-orchestrator](../holistic-linting-orchestrator/SKILL.md) - Orchestrator delegation workflows
- [Pre-Existing Issues Protocol](../holistic-linting/references/pre-existing-issues-protocol.md) - Recording and triage pipeline for issues found outside current task scope
