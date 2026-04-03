# Agent Delegation Prompts

Pre-built prompts for delegating stinkysnake workflow phases to specialist agents.

## Phase 4: Plan Review Agent

<eg>
Agent(
  agent="code-reviewer",
  prompt="Review the modernization plan at {plan_dir}/stinkysnake-plan.md (resolve plan_dir via: uv run python -c 'from dh_paths import plan_dir; print(plan_dir())')

REVIEW CRITERIA:

1. **Pythonic Best Practices**
   - Are the proposed patterns idiomatic Python?
   - Do they follow PEP guidelines?
   - Are simpler solutions available?

2. **Online Verification**
   - Verify type patterns against ty docs and/or mypy/pyright docs per project checker
   - Check library recommendations against current best practices
   - Confirm version compatibility claims

3. **Feasibility Assessment**
   - Are the proposed changes realistic?
   - What is the effort vs benefit ratio?
   - Are there hidden dependencies?

4. **Breaking Change Analysis**
   - What interfaces change?
   - What downstream code is affected?
   - Is backward compatibility needed?

5. **Risk Assessment**
   - What could go wrong?
   - What tests are needed?
   - What rollback plan exists?

OUTPUT:
Create review report at .claude/reports/plan-review-{timestamp}.md with:
- Issues found (blocking, warning, suggestion)
- Verification results with sources
- Feasibility scores per change
- Breaking change inventory
- Recommended modifications"
)
</eg>

## Phase 8: Test Writing Agent

<eg>
Agent(
  agent="python-pytest-architect",
  prompt="Write failing tests for the interfaces defined in the modernization plan.

CONTEXT:
- Plan: {plan_dir}/stinkysnake-plan.md (resolve plan_dir via: uv run python -c 'from dh_paths import plan_dir; print(plan_dir())')
- Interfaces: src/types.py, src/protocols.py, src/schemas.py

REQUIREMENTS:

1. **Test Each Protocol**
   - Test that protocol can be satisfied
   - Test that non-conforming types are rejected
   - Test protocol runtime behavior if applicable

2. **Test Each TypedDict**
   - Test required keys
   - Test optional keys (NotRequired)
   - Test type validation

3. **Test Each Function Signature**
   - Test return type matches TypeAlias
   - Test parameter types
   - Test edge cases

4. **Test Behavioral Expectations**
   - Test that refactored code maintains behavior
   - Test error handling patterns
   - Test async behavior if applicable

OUTPUT:
- Create test files in tests/
- Tests MUST fail (implementations don't exist yet)
- Stop after tests are written
- Report test file locations"
)
</eg>
