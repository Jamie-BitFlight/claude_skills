# Plan and Report Templates

Document templates for stinkysnake workflow phases. Use these formats when creating modernization plans, review reports, and refined plans.

## Modernization Plan Template (Phase 3 Output)

<eg>
## Modernization Plan

### Type System Changes

1. **Eliminate Any in api.py**
   - Line 23: response: Any -> response: APIResponse (TypeAlias)
   - Line 45: callback: Any -> callback: Callable[[Event], None]
   - Line 67: data: Any -> data: UserData (TypedDict)

2. **Add Protocols for duck typing**
   - Create Handler protocol for plugin system
   - Create Serializable protocol for export functions

3. **Add Generics for containers**
   - Cache[T] generic class
   - Result[T, E] for error handling

### Library Migrations

1. **requests -> httpx**
   - Files affected: api.py, client.py
   - Breaking changes: Session -> Client, response.json() typing
   - Async opportunity: Yes

2. **json -> orjson**
   - Files affected: serialization.py
   - Breaking changes: orjson.dumps returns bytes
   - Performance gain: ~10x

### Estimated Impact
- Files to modify: 12
- New type definitions: 8
- Breaking changes: 3 (internal only)
</eg>

## Plan Review Report Template (Phase 4 Output)

<eg>
## Plan Review Report

### Summary
- Blocking Issues: N
- Warnings: N
- Suggestions: N
- Overall Feasibility: High/Medium/Low

### Blocking Issues

#### Issue 1: Protocol misuse in Handler
**Location**: Plan section 2.1
**Problem**: Protocol used where ABC is more appropriate
**Evidence**: [link to mypy docs on Protocol vs ABC]
**Recommendation**: Use ABC with @abstractmethod

### Warnings

#### Warning 1: orjson bytes return
**Location**: Library migration section
**Risk**: Downstream code expects str from json.dumps
**Mitigation**: Add .decode() or update all callers

### Verification Results

| Claim | Verified | Source |
|-------|----------|--------|
| TypeGuard narrows in if blocks | Y | mypy docs |
| httpx is drop-in for requests | N | API differs |
| orjson 10x faster | Y | benchmark link |

### Breaking Change Inventory

| Change | Affected Code | Severity |
|--------|--------------|----------|
| APIResponse type | 5 functions | Medium |
| httpx migration | 12 call sites | High |

### Recommended Modifications

1. Split httpx migration into separate PR
2. Add compatibility shim for json.dumps
3. Use ABC instead of Protocol for Handler
</eg>

## Revised Plan Template (Phase 5 Output)

<eg>
## Modernization Plan (Revised)

### Changes from Review

1. **Handler: Protocol -> ABC**
   - Reason: Plugin system requires inheritance
   - Evidence: [reviewer's mypy docs link]

2. **httpx migration: Deferred**
   - Reason: High breaking change risk
   - Alternative: Create separate PR after core changes

3. **orjson: Added decode shim**
   - Added: compat.dumps() wrapper returning str

### Updated Implementation Order

1. Type aliases and TypedDicts (no breaking changes)
2. Protocol/ABC additions (additive)
3. Generic containers (additive)
4. Any elimination (may require caller updates)
5. [DEFERRED] httpx migration
</eg>

## Documentation Update Plan Template (Phase 6 Output)

<eg>
## Documentation Update Plan

### Files to Update

| Doc File | Section | Change Needed |
|----------|---------|---------------|
| README.md | Installation | Add orjson dependency |
| docs/api.md | fetch_data() | Update return type |
| CHANGELOG.md | Unreleased | Add type improvements |

### Docstrings to Update

| Code File | Function | Docstring Change |
|-----------|----------|------------------|
| api.py | fetch_data | Update return type docs |
| models.py | User | Add field descriptions |

### New Documentation Needed

- docs/types.md: Document TypeAliases
- docs/migration.md: Breaking change guide
</eg>
