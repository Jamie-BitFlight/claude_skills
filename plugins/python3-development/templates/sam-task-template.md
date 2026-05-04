---
task: ''
title: ''
status: not-started
agent: ''
dependencies: []  # Task IDs that must complete before this task
                  # Example: ["T1", "T2"]
                  # Use [] for no dependencies
priority: 3
complexity: medium
created: ''
started: ''
completed: ''
blocked-by: []  # External blockers preventing progress
                # Example: ["API access", "Design approval"]
                # These are NOT task IDs - use dependencies for task dependencies
parallelize-with: []  # Task IDs that can run concurrently
                      # Example: ["T2", "T3"]
                      # Use when tasks share no dependencies
---

## Context

Provide background and rationale for this task. Explain why it exists, what problem it solves, and how it fits into the larger project or feature.

Example: Implement core data structures for validation results, issues, and error codes. These models are used by all validators and reporters to ensure consistent error handling across the system.

## Objective

Single clear sentence describing what this task achieves. Focus on the end state, not the implementation steps.

Example: Create type-safe data models for ValidationResult, ValidationIssue, and ComplexityMetrics with complete error code catalog.

## Requirements

Numbered list of specific, testable requirements that define task completion.

1. First specific requirement with measurable outcome
2. Second specific requirement with clear deliverable
3. Third specific requirement with validation criteria

Example:
1. Create ValidationResult dataclass with passed/errors/warnings/info fields
2. Create ValidationIssue dataclass with field/severity/message/code/line fields
3. All dataclasses must be frozen or use __post_init__ validation

## Constraints

Technical, architectural, or policy constraints that must be respected during implementation.

- Technical constraint (e.g., "Use Python 3.11+ syntax only")
- Architectural constraint (e.g., "Follow repository Factory pattern")
- Performance constraint (e.g., "Response time <100ms")
- Quality constraint (e.g., "Code coverage minimum 80%")

Example:
- Use Python 3.11+ syntax (str | None, not Optional[str])
- All dataclasses must be frozen or use __post_init__ validation
- Error codes must remain stable across versions (no code reuse)

## Expected Outputs

Concrete artifacts, files, or deliverables produced by this task. Be specific about file paths and formats.

- File created: path/to/file.py
- Artifact generated: description of artifact
- Configuration updated: description of changes
- Documentation updated: path/to/docs.md

Example:
- File created: plugins/plugin-creator/scripts/ecosystem_registry.py
- Models: EcosystemSpec, _REGISTRY
- Constants: get_ecosystem_owned_skill_keys, get_ecosystem_for_key

## Acceptance Criteria

Testable pass/fail conditions that verify task completion. Each criterion should be independently verifiable.

1. First testable condition with clear pass/fail outcome
2. Second testable condition with verification method
3. Third testable condition with success criteria

Example:
1. All dataclasses type-check clean under the project type checker (`ty check` or `mypy` per pyproject)
2. Error code constants match architecture catalog exactly (23 codes)
3. ValidationIssue.format() produces expected output format

## Verification Steps

Executable commands or procedures to verify acceptance criteria are met. Include expected outputs where helpful.

```bash
# Type checking
uv run mypy --strict path/to/file.py

# Unit tests
uv run pytest tests/test_module.py -v

# Integration tests
uv run pytest tests/integration/ -k test_feature

# Linting
uv run prek run --files path/to/file.py
```

Example:

```bash
# Type checking
uv run ty check plugins/plugin-creator/scripts/ecosystem_registry.py

# Unit test data models
uv run pytest tests/test_data_models.py -v

# Verify function count
grep -c "def get_" plugins/plugin-creator/scripts/ecosystem_registry.py
```

## Can Parallelize With

List task IDs that can run concurrently with this task, and explain why parallelization is safe.

Task IDs: T2, T3, T4

**Reason**: These tasks operate on independent modules with no shared dependencies. Task T2 handles validation logic, T3 handles reporters, and T4 handles CLI commands. All depend only on the data models from T1.

## Handoff

Information to report to orchestrator when task completes. Include paths, counts, status, and any blockers encountered.

Report to orchestrator:
- File paths for all created/modified files
- Count of key artifacts (e.g., "23 error codes implemented")
- Status of acceptance criteria (all passed/specific failures)
- Any blockers or issues encountered during implementation
- Recommendations for follow-up tasks or improvements

Example:
- Data model file: plugins/plugin-creator/scripts/ecosystem_registry.py
- Error codes implemented: 23 (matches architecture catalog)
- Type checking: passed (ty or project mypy command)
- Unit tests: passed (100% coverage on data models)
- Ready for: T2 (ValidationProtocol), T3 (FrontmatterValidator port)
