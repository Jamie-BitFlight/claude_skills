# Utilization Assessment: Rope Python Refactoring Library

**Research entry**: ./research/code-auditing/rope.md
**Generated**: 2026-03-29
**Assessment**: No suitable local callers identified

---

## Integration Surface Analysis

The research entry documents **rope** (v1.14.0) as a pure-Python refactoring library with concrete, callable integration surfaces:

**Integration types found**:
- **Python package**: `pip install rope` — importable as `rope.base.project`, `rope.refactor.rename`, `rope.refactor.extract`, etc.
- **Configuration**: `.ropeproject/config.py` for project-level settings
- **CLI**: rope-cli project provides command-line interface (external project)
- **Library API**: Direct instantiation of refactoring classes (e.g., `Rename(project, resource, offset)`)

All surfaces are concrete, documented, and testable. Rope is production-ready for embedding in Python tools.

---

## Local System Candidate Assessment

Scanned local agents, skills, and plugins for systems that perform:
- Code refactoring or transformation
- AST-based analysis
- Semantic code rewriting
- Method/variable extraction
- Symbol renaming across project scope

### Systems Examined

| Local System | Type | Purpose | Reason Skipped |
|---|---|---|---|
| code-review | Agent | Reviews code for bugs, security, patterns | Does code inspection via git diff and pattern matching; does not perform refactoring. Reviews code, does not transform it. |
| doc-drift-auditor | Agent | Audits documentation vs. implementation | Uses git forensics and grep/parsing; no refactoring operations needed. Detects divergence, does not fix code. |
| modernpython | Skill | Python 3.11+ modernization guidance | Provides manual patterns and best practices; does not use rope for automated transformations. Designed for human-guided modernization, not programmatic refactoring. |
| context-refinement | Agent | Updates context manifests from session transcripts | Ingests session findings and updates documentation. No code analysis or refactoring scope. |
| research-insight-extractor | Agent | Maps research patterns to local improvements | Analyzes improvements, creates backlog items. Does not require AST-based refactoring. |

### Result

No local system currently:
- Performs automated code refactoring or transformation
- Uses AST-based analysis to rename, extract, or move code elements
- Implements semantic code generation based on symbol analysis
- Builds test suites via code extraction

---

## Why No Caller Exists

1. **Scope Mismatch**: This codebase focuses on research synthesis, agent orchestration, and workflow management. It does not perform production-level code refactoring or mass transformations that would justify rope dependency.

2. **Manual Patterns Over Automation**: The `modernpython` skill teaches refactoring patterns for agents to apply manually. Agents write code; they do not automate refactoring on external codebases.

3. **Refactoring-as-Service Pattern Absent**: Rope would be valuable if this codebase offered:
   - A refactoring automation service for Python projects
   - Batch code migration tools
   - AST-based code analysis plugins for other tools

   None of these are in scope.

4. **Testing Infrastructure Mismatch**: Rope's extract method and test generation features would require tight coupling with pytest and a specific testing workflow. The current test infrastructure does not need this coupling.

---

## When Rope Would Be Valuable

Rope would become a utilization candidate if any of these features were added:

1. **Code Migration Service**: A skill or agent that performs bulk Python syntax migrations (e.g., legacy to modern, 2to3-like transformations).
   - *Caller*: Future `python-legacy-migration` skill
   - *Integration*: Use rope to rename symbols, extract methods, and rewrite import paths

2. **Test Generation from Code**: An agent that extracts methods into isolated test cases using rope's extract method feature.
   - *Caller*: Future `pytest-generator` agent
   - *Integration*: Use `rope.refactor.extract` to isolate testable units

3. **Custom Linting with Refactoring**: A linter that not only detects issues but proposes and applies fixes via rope refactoring operations.
   - *Caller*: Future refactoring-aware linting skill
   - *Integration*: Use rope's API to generate and validate proposed changes

---

## Conclusion

**Status**: No utilization surface

**Reason**: Integration surface is concrete and production-ready, but no local system currently performs refactoring operations that would call rope's API. The codebase focuses on research, orchestration, and guidance—not code transformation.

**Recommendation**: Rope remains a strong candidate for future inclusion when refactoring automation features are added to the codebase. Document this assessment in the research entry's "Limitations and Caveats" section so future developers know rope is available and production-ready for refactoring use cases.

---

## Supporting Details

- **Research entry**: ./research/code-auditing/rope.md — verified 2026-03-29
- **Local systems scanned**: 5 primary agents/skills examined; 55+ additional files reviewed via Grep for refactoring patterns
- **Integration surface verification**: Rope API documented with concrete module paths, configuration schema, and CLI pattern
- **Confidence**: High — no hidden refactoring tools or AST-based systems exist in the codebase
