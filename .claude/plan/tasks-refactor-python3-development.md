# Refactoring Tasks: python3-development Plugin

## Task 1.1: Create Skill Directory Structure

**Status**: ❌ NOT STARTED
**Dependencies**: None
**Priority**: 1
**Complexity**: Low
**Agent**: orchestrator

**Target**: `./plugins/python3-development/skills/`
**Issue Type**: STRUCTURE_FIX

**Acceptance Criteria**:

1. Five new skill directories created under `./plugins/python3-development/skills/`
2. Directory names match design spec: python3-workflow, python3-typing, python3-cli, python3-quality, python3-project
3. Each directory contains empty placeholder for SKILL.md creation
4. Directory permissions allow file creation by refactoring agents

**Required Inputs**:

- Design spec section: "Skill Splits" → "Proposed Split" table (lines 33-41)
- Existing plugin directory: `./plugins/python3-development/`

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-workflow/` (directory)
- `./plugins/python3-development/skills/python3-typing/` (directory)
- `./plugins/python3-development/skills/python3-cli/` (directory)
- `./plugins/python3-development/skills/python3-quality/` (directory)
- `./plugins/python3-development/skills/python3-project/` (directory)

**Can Parallelize With**: Task 1.2, Task 1.3
**Reason**: Operates on different directories - no file conflicts

**Verification Steps**:

1. Run `ls -la ./plugins/python3-development/skills/` and verify 5 new directories exist
2. Run `ls -la ./plugins/python3-development/skills/python3-workflow/` for each directory - should be empty but accessible
3. Verify directory permissions allow write access

---

## Task 1.2: Create plugin.json Metadata

**Status**: ❌ NOT STARTED
**Dependencies**: None
**Priority**: 1
**Complexity**: Low
**Agent**: orchestrator

**Target**: `./plugins/python3-development/plugin.json`
**Issue Type**: DOC_IMPROVE

**Acceptance Criteria**:

1. File created at `./plugins/python3-development/plugin.json`
2. Contains valid JSON matching schema from design spec
3. Lists all 5 new skills in "skills" array
4. Lists all 6 commands in "commands" object grouped by category
5. Keywords array includes all relevant technologies

**Required Inputs**:

- Design spec section: "Documentation Improvements" → "plugin.json Description" (lines 559-587)

**Expected Outputs**:

- `./plugins/python3-development/plugin.json` (file)

**Can Parallelize With**: Task 1.1, Task 1.3
**Reason**: Creates independent file - no conflicts with directory creation

**Verification Steps**:

1. Run `cat ./plugins/python3-development/plugin.json | jq .` to validate JSON syntax
2. Verify "skills" array contains exactly 5 entries matching directory names
3. Verify "commands" object contains "development" and "testing" keys with correct command names

---

## Task 1.3: Archive Orphan Planning Document

**Status**: ❌ NOT STARTED
**Dependencies**: None
**Priority**: 2
**Complexity**: Low
**Agent**: orchestrator

**Target**: `./plugins/python3-development/skills/python3-development/planning/reference-document-architecture.md`
**Issue Type**: ORPHAN_RESOLVE

**Acceptance Criteria**:

1. Archive directory created at `./plugins/python3-development/docs/archive/`
2. File moved to `./plugins/python3-development/docs/archive/reference-document-architecture.md`
3. Empty `planning/` directory removed
4. File content preserved exactly (no modifications)

**Required Inputs**:

- Design spec section: "Orphan Resolution" → "planning/reference-document-architecture.md" (lines 515-551)
- Source file: `./plugins/python3-development/skills/python3-development/planning/reference-document-architecture.md`

**Expected Outputs**:

- `./plugins/python3-development/docs/archive/reference-document-architecture.md` (moved file)
- `./plugins/python3-development/docs/archive/` (directory)

**Can Parallelize With**: Task 1.1, Task 1.2
**Reason**: Operates on different directory tree - no conflicts with skill directory creation

**Verification Steps**:

1. Run `cat ./plugins/python3-development/docs/archive/reference-document-architecture.md | head -5` to verify file exists and content preserved
2. Run `ls ./plugins/python3-development/skills/python3-development/planning/` - should return "no such directory"
3. Verify frontmatter still contains `status: "historical-proposal"`

---

## Task 2.1: Create python3-workflow Skill

**Status**: ❌ NOT STARTED
**Dependencies**: Task 1.1
**Priority**: 1
**Complexity**: Medium
**Agent**: skill-refactorer

**Target**: `./plugins/python3-development/skills/python3-workflow/SKILL.md`
**Issue Type**: SKILL_SPLIT

**Acceptance Criteria**:

1. SKILL.md created with frontmatter matching design spec lines 49-53
2. Content extracted from original SKILL.md lines: 11-35, 719-846, 924-940, 1227-1246
3. File length under 250 lines (target: ~200 lines)
4. ROLE_TYPE sections preserved for orchestrator-only content
5. References link to `../python3-project/references/python-development-orchestration.md`

**Required Inputs**:

- Design spec section: "Skill 1: python3-workflow" (lines 43-108)
- Source file: `./plugins/python3-development/skills/python3-development/SKILL.md` (lines 11-35, 719-846, 924-940, 1227-1246)

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-workflow/SKILL.md`

**Can Parallelize With**: Task 2.2, Task 2.3, Task 2.4, Task 2.5
**Reason**: Each skill writes to different file - no shared dependencies during creation

**Verification Steps**:

1. Run `wc -l ./plugins/python3-development/skills/python3-workflow/SKILL.md` - should be under 250 lines
2. Run `grep -c "ROLE_TYPE" ./plugins/python3-development/skills/python3-workflow/SKILL.md` - should find orchestrator sections
3. Verify frontmatter description contains "Use when:" and "Provides:" sections

---

## Task 2.2: Create python3-typing Skill

**Status**: ❌ NOT STARTED
**Dependencies**: Task 1.1
**Priority**: 1
**Complexity**: High
**Agent**: skill-refactorer

**Target**: `./plugins/python3-development/skills/python3-typing/SKILL.md`
**Issue Type**: SKILL_SPLIT

**Acceptance Criteria**:

1. SKILL.md created with frontmatter matching design spec lines 117-121
2. Content extracted from original SKILL.md lines: 274-712
3. File length under 400 lines (target: ~350 lines)
4. All mypy-docs references preserved with correct relative paths
5. No ROLE_TYPE sections (applies to all roles)

**Required Inputs**:

- Design spec section: "Skill 2: python3-typing" (lines 111-168)
- Source file: `./plugins/python3-development/skills/python3-development/SKILL.md` (lines 274-712)

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-typing/SKILL.md`

**Can Parallelize With**: Task 2.1, Task 2.3, Task 2.4, Task 2.5
**Reason**: Each skill writes to different file - no shared dependencies during creation

**Verification Steps**:

1. Run `wc -l ./plugins/python3-development/skills/python3-typing/SKILL.md` - should be under 400 lines
2. Run `grep -c "mypy-docs" ./plugins/python3-development/skills/python3-typing/SKILL.md` - should find multiple references
3. Verify all sections from design spec present: Generics, Protocols, TypedDict, Type Narrowing, attrs vs dataclasses vs pydantic

---

## Task 2.3: Create python3-cli Skill

**Status**: ❌ NOT STARTED
**Dependencies**: Task 1.1
**Priority**: 1
**Complexity**: Low
**Agent**: skill-refactorer

**Target**: `./plugins/python3-development/skills/python3-cli/SKILL.md`
**Issue Type**: SKILL_SPLIT

**Acceptance Criteria**:

1. SKILL.md created with frontmatter matching design spec lines 177-181
2. Content extracted from original SKILL.md lines: 127-273
3. File length under 250 lines (target: ~200 lines)
4. References link to `../python3-project/references/exception-handling.md` and assets
5. No ROLE_TYPE sections (applies to all roles)

**Required Inputs**:

- Design spec section: "Skill 3: python3-cli" (lines 172-217)
- Source file: `./plugins/python3-development/skills/python3-development/SKILL.md` (lines 127-273)

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-cli/SKILL.md`

**Can Parallelize With**: Task 2.1, Task 2.2, Task 2.4, Task 2.5
**Reason**: Each skill writes to different file - no shared dependencies during creation

**Verification Steps**:

1. Run `wc -l ./plugins/python3-development/skills/python3-cli/SKILL.md` - should be under 250 lines
2. Run `grep "exception-handling.md" ./plugins/python3-development/skills/python3-cli/SKILL.md` - should find reference link
3. Verify Rich Panel/Table width handling section preserved with code examples

---

## Task 2.4: Create python3-quality Skill

**Status**: ❌ NOT STARTED
**Dependencies**: Task 1.1
**Priority**: 1
**Complexity**: Medium
**Agent**: skill-refactorer

**Target**: `./plugins/python3-development/skills/python3-quality/SKILL.md`
**Issue Type**: SKILL_SPLIT

**Acceptance Criteria**:

1. SKILL.md created with frontmatter matching design spec lines 226-230
2. Content extracted from original SKILL.md lines: 944-1129
3. File length under 300 lines (target: ~250 lines)
4. Linting discovery protocol section preserved completely
5. References link to tool-library-registry.md and user-project-conventions.md

**Required Inputs**:

- Design spec section: "Skill 4: python3-quality" (lines 220-258)
- Source file: `./plugins/python3-development/skills/python3-development/SKILL.md` (lines 944-1129)

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-quality/SKILL.md`

**Can Parallelize With**: Task 2.1, Task 2.2, Task 2.3, Task 2.5
**Reason**: Each skill writes to different file - no shared dependencies during creation

**Verification Steps**:

1. Run `wc -l ./plugins/python3-development/skills/python3-quality/SKILL.md` - should be under 300 lines
2. Run `grep -c "pre-commit\|prek" ./plugins/python3-development/skills/python3-quality/SKILL.md` - should find both tool references
3. Verify quality gates section includes type checker detection logic

---

## Task 2.5: Create python3-project Skill

**Status**: ❌ NOT STARTED
**Dependencies**: Task 1.1
**Priority**: 1
**Complexity**: Medium
**Agent**: skill-refactorer

**Target**: `./plugins/python3-development/skills/python3-project/SKILL.md`
**Issue Type**: SKILL_SPLIT

**Acceptance Criteria**:

1. SKILL.md created with frontmatter matching design spec lines 268-272
2. Content extracted from original SKILL.md lines: 98-126, 1130-1226, 1248-1304, 848-923
3. File length under 300 lines (target: ~200 lines)
4. Asset template usage section preserved with examples
5. Command usage section references external command files

**Required Inputs**:

- Design spec section: "Skill 5: python3-project" (lines 262-311)
- Source file: `./plugins/python3-development/skills/python3-development/SKILL.md` (lines 98-126, 848-923, 1130-1226, 1248-1304)

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-project/SKILL.md`

**Can Parallelize With**: Task 2.1, Task 2.2, Task 2.3, Task 2.4
**Reason**: Each skill writes to different file - no shared dependencies during creation

**Verification Steps**:

1. Run `wc -l ./plugins/python3-development/skills/python3-project/SKILL.md` - should be under 300 lines
2. Run `grep "PEP 723" ./plugins/python3-development/skills/python3-project/SKILL.md` - should find inline script metadata section
3. Verify asset templates section includes paths to `./assets/` directory

---

## Task 2.6: Fix Command Frontmatter (All 6 Commands)

**Status**: ❌ NOT STARTED
**Dependencies**: None
**Priority**: 1
**Complexity**: Low
**Agent**: contextual-ai-documentation-optimizer

**Target**: All 6 command files in `./plugins/python3-development/commands/`
**Issue Type**: DOC_IMPROVE

**Acceptance Criteria**:

1. All 6 command files have standardized frontmatter removing `title`, `command_type`, `last_updated`, `related_docs`
2. All frontmatter includes `name` and trigger-optimized `description`
3. Commands with arguments include `argument-hint` field
4. Template command includes `user-invocable: false`
5. All descriptions contain "Use when:" trigger phrases

**Required Inputs**:

- Design spec section: "Command Frontmatter Fixes" (lines 377-510)
- Source files:
  - `./plugins/python3-development/commands/development/create-feature-task.md`
  - `./plugins/python3-development/commands/development/use-command-template.md`
  - `./plugins/python3-development/commands/development/templates/command-template.md`
  - `./plugins/python3-development/commands/testing/analyze-test-failures.md`
  - `./plugins/python3-development/commands/testing/comprehensive-test-review.md`
  - `./plugins/python3-development/commands/testing/test-failure-mindset.md`

**Expected Outputs**:

- Modified frontmatter in all 6 command files
- Content below frontmatter preserved exactly

**Can Parallelize With**: Task 2.1, Task 2.2, Task 2.3, Task 2.4, Task 2.5
**Reason**: Operates on command files separate from skill creation - no file conflicts

**Verification Steps**:

1. Run `grep -h "^title:" ./plugins/python3-development/commands/**/*.md` - should return no results
2. Run `grep -h "^description:" ./plugins/python3-development/commands/**/*.md | wc -l` - should return 6
3. Verify command-template.md includes `user-invocable: false`

---

## Task 3.1: Move References Directory to python3-project

**Status**: ❌ NOT STARTED
**Dependencies**: Task 2.1, Task 2.2, Task 2.3, Task 2.4, Task 2.5, Task 2.6
**Priority**: 1
**Complexity**: Low
**Agent**: orchestrator

**Target**: `./plugins/python3-development/skills/python3-development/references/`
**Issue Type**: STRUCTURE_FIX

**Acceptance Criteria**:

1. Entire `references/` directory moved to `./plugins/python3-development/skills/python3-project/references/`
2. All 26 reference files preserved with exact content
3. Directory structure under references/ preserved (mypy-docs/, modern-modules/)
4. Original references/ directory removed after successful move

**Required Inputs**:

- Design spec section: "Shared Reference Strategy" (lines 313-374)
- Source directory: `./plugins/python3-development/skills/python3-development/references/`

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-project/references/` (directory with all files)

**Can Parallelize With**: Task 3.2
**Reason**: Operates on different directory trees - references vs assets

**Verification Steps**:

1. Run `ls -la ./plugins/python3-development/skills/python3-project/references/ | wc -l` - should match original count
2. Run `ls ./plugins/python3-development/skills/python3-development/references/` - should return "no such directory"
3. Verify subdirectories exist: `./plugins/python3-development/skills/python3-project/references/mypy-docs/` and `./plugins/python3-development/skills/python3-project/references/modern-modules/`

---

## Task 3.2: Move Assets Directory to python3-project

**Status**: ❌ NOT STARTED
**Dependencies**: Task 2.1, Task 2.2, Task 2.3, Task 2.4, Task 2.5, Task 2.6
**Priority**: 1
**Complexity**: Low
**Agent**: orchestrator

**Target**: `./plugins/python3-development/skills/python3-development/assets/`
**Issue Type**: STRUCTURE_FIX

**Acceptance Criteria**:

1. Entire `assets/` directory moved to `./plugins/python3-development/skills/python3-project/assets/`
2. All asset files preserved with exact content (version.py, hatch_build.py, typer_examples/)
3. Directory structure under assets/ preserved
4. Original assets/ directory removed after successful move

**Required Inputs**:

- Design spec section: "Directory Structure After Split" (lines 332-367)
- Source directory: `./plugins/python3-development/skills/python3-development/assets/`

**Expected Outputs**:

- `./plugins/python3-development/skills/python3-project/assets/` (directory with all files)

**Can Parallelize With**: Task 3.1
**Reason**: Operates on different directory trees - assets vs references

**Verification Steps**:

1. Run `ls -la ./plugins/python3-development/skills/python3-project/assets/ | wc -l` - should match original count
2. Run `ls ./plugins/python3-development/skills/python3-development/assets/` - should return "no such directory"
3. Verify typer_examples/ subdirectory exists with executable Python files

---

## Task 3.3: Update Relative Paths in Skills

**Status**: ❌ NOT STARTED
**Dependencies**: Task 3.1, Task 3.2
**Priority**: 1
**Complexity**: Medium
**Agent**: skill-refactorer

**Target**: `./plugins/python3-development/skills/python3-{workflow,typing,cli,quality}/SKILL.md`
**Issue Type**: SKILL_SPLIT

**Acceptance Criteria**:

1. All reference links in python3-workflow, python3-typing, python3-cli, python3-quality updated to `../python3-project/references/`
2. No broken links when verifying with Read tool
3. Links use markdown syntax: `[text](./path)` not backticks
4. Asset references updated to `../python3-project/assets/`

**Required Inputs**:

- Design spec section: "Shared Reference Strategy" (lines 313-374)
- All 4 skill files created in Task 2.1-2.4

**Expected Outputs**:

- Modified SKILL.md files with updated relative paths

**Can Parallelize With**: None
**Reason**: Must wait for references/assets to be moved to correct location

**Verification Steps**:

1. Run `grep -r "\.\./python3-project/references/" ./plugins/python3-development/skills/python3-{workflow,typing,cli,quality}/*.md | wc -l` - should find multiple references
2. Use Read tool to verify each referenced file exists at new path
3. Run `grep -r "references/" ./plugins/python3-development/skills/python3-{workflow,typing,cli,quality}/*.md | grep -v "\.\./python3-project"` - should return no results (all paths updated)

---

## Task 3.4: Delete Original python3-development Skill Directory

**Status**: ❌ NOT STARTED
**Dependencies**: Task 3.1, Task 3.2, Task 3.3
**Priority**: 1
**Complexity**: Low
**Agent**: orchestrator

**Target**: `./plugins/python3-development/skills/python3-development/`
**Issue Type**: STRUCTURE_FIX

**Acceptance Criteria**:

1. Original skill directory completely removed
2. Verify all content migrated to new skills before deletion
3. No orphaned files remain
4. Directory deletion confirmed with file system check

**Required Inputs**:

- Verification that Task 3.1, 3.2, 3.3 completed successfully

**Expected Outputs**:

- Deleted directory: `./plugins/python3-development/skills/python3-development/`

**Can Parallelize With**: None
**Reason**: Must verify all migrations complete before deletion to prevent data loss

**Verification Steps**:

1. Run `ls ./plugins/python3-development/skills/python3-development/` - should return "no such directory"
2. Run `ls ./plugins/python3-development/skills/ | wc -l` - should return 5 (only new skills remain)
3. Verify SKILL.md no longer exists at old path

---

## Task V1: Validate Plugin Structure

**Status**: ❌ NOT STARTED
**Dependencies**: Task 1.1, Task 1.2, Task 1.3, Task 2.1, Task 2.2, Task 2.3, Task 2.4, Task 2.5, Task 2.6, Task 3.1, Task 3.2, Task 3.3, Task 3.4
**Priority**: 1
**Complexity**: Low
**Agent**: plugin-assessor

**Target**: `./plugins/python3-development/`
**Issue Type**: STRUCTURE_FIX

**Acceptance Criteria**:

1. Plugin passes structural validation from plugin-assessor
2. All reference links resolve correctly (no 404s)
3. No orphaned files detected
4. Frontmatter validates against schema for all skills and commands
5. Assessment score improved from 62/100 baseline

**Required Inputs**:

- Refactored plugin directory structure
- All tasks from Phase 1-3 completed

**Expected Outputs**:

- Assessment report showing structural improvements
- List of any remaining issues to address

**Can Parallelize With**: None
**Reason**: Requires all refactoring tasks complete to validate final state

**Verification Steps**:

1. Delegate to plugin-assessor: `Agent(subagent_type="plugin-assessor", prompt="Assess ./plugins/python3-development for marketplace readiness")`
2. Verify score improved from 62/100 baseline
3. Verify no critical issues remain in assessment report

---

## Task V2: Update Plugin Documentation

**Status**: ❌ NOT STARTED
**Dependencies**: Task V1
**Priority**: 2
**Complexity**: Low
**Agent**: plugin-docs-writer

**Target**: `./plugins/python3-development/README.md`
**Issue Type**: DOC_IMPROVE

**Acceptance Criteria**:

1. README.md updated to reflect 5 new skills instead of monolithic skill
2. All skills documented with descriptions and use cases
3. Command usage examples accurate for all 6 commands
4. Installation instructions updated if needed
5. Navigation structure improved for progressive disclosure

**Required Inputs**:

- Design spec section: "Documentation Improvements" (lines 556-627)
- Plugin structure validation from Task V1

**Expected Outputs**:

- `./plugins/python3-development/README.md` (updated)
- Optionally: `./plugins/python3-development/docs/skills.md`, `./plugins/python3-development/docs/commands.md`

**Can Parallelize With**: None
**Reason**: Requires validation complete to document accurate state

**Verification Steps**:

1. Delegate to plugin-docs-writer: `Agent(subagent_type="plugin-docs-writer", prompt="Generate complete documentation for ./plugins/python3-development")`
2. Verify README.md lists all 5 skills with descriptions
3. Verify command examples match frontmatter argument-hint fields

---

## Task V3: Test Plugin Loading

**Status**: ❌ NOT STARTED
**Dependencies**: Task V1
**Priority**: 1
**Complexity**: Low
**Agent**: orchestrator

**Target**: Plugin loading verification
**Issue Type**: STRUCTURE_FIX

**Acceptance Criteria**:

1. Plugin loads successfully with `--plugin-dir`
2. All 5 skills available when plugin loaded
3. Skills load without errors when activated
4. Test each skill with `/skill-name` in chat to verify loading

**Required Inputs**:

- Refactored plugin structure from Phase 3

**Expected Outputs**:

- Plugin loads cleanly via `claude --plugin-dir ./plugins/python3-development`
- Verified skill loading via CLI test

**Can Parallelize With**: Task V2
**Reason**: Documentation updates independent of plugin testing

**Verification Steps**:

1. Run `claude --plugin-dir ./plugins/python3-development` from repository root
2. Test skill loading: Activate each skill and verify no errors
3. Run `/plugin validate ./plugins/python3-development` to verify structure

---

## Task V4: Run Pre-Commit on Modified Files

**Status**: ❌ NOT STARTED
**Dependencies**: Task V1, Task V2
**Priority**: 2
**Complexity**: Low
**Agent**: orchestrator

**Target**: All modified files in refactoring
**Issue Type**: DOC_IMPROVE

**Acceptance Criteria**:

1. Pre-commit hooks pass on all modified skill files
2. Pre-commit hooks pass on all modified command files
3. Pre-commit hooks pass on plugin.json
4. No linting errors remain in refactored files

**Required Inputs**:

- All modified files from Tasks 1.1-3.4, V2

**Expected Outputs**:

- Clean pre-commit run with no errors

**Can Parallelize With**: Task V3
**Reason**: Linting independent of symlink testing

**Verification Steps**:

1. Run `uv run pre-commit run --files ./plugins/python3-development/**/*.md ./plugins/python3-development/plugin.json`
2. Verify exit code 0 (all hooks passed)
3. Address any formatting issues identified by hooks

---

## Context Manifest

**Generated**: 2026-01-23 by context-gathering agent

### How the Current Skill Architecture Works

The python3-development plugin at `./plugins/python3-development/` contains a single monolithic SKILL.md file spanning 1,318 lines that covers five distinct domains: orchestration/workflow patterns, type safety with mypy, CLI development with Typer/Rich, linting/quality workflows, and project structure standards. This monolithic design violates the recommended skill size guideline of 400 lines maximum per skill.

When a user activates the skill via `@python3-development` or `Skill(skill: "python3-development")`, Claude Code loads the entire 1,318-line SKILL.md into context. The skill's frontmatter (lines 1-7) defines 10 trigger conditions covering any Python-related work. The description field uses a `<hint>` XML tag to provide additional context about what the skill provides without triggering early activation.

The skill distinguishes between orchestrator and sub-agent roles through `<section ROLE_TYPE="orchestrator">` tags at four locations:

- Lines 713-846: Agent orchestration and pre-delegation protocol
- Lines 924-940: Core workflows overview
- Lines 1227-1246: Common delegation patterns
- Lines 1305-1318: Summary for orchestrators

Sub-agents reading this skill receive all content EXCEPT sections wrapped in `<section ROLE_TYPE="orchestrator">` tags. This allows the same skill to provide different guidance based on the reader's role.

### Domain Content Line Ranges for Skill Split

Based on analysis of SKILL.md content and the design spec, the five new skills will extract content from these specific line ranges:

**python3-workflow (~200 lines target)**

| Section             | Lines     | Description                                                 |
| ------------------- | --------- | ----------------------------------------------------------- |
| Role Identification | 11-35     | Mandatory role echo statement                               |
| Agent Orchestration | 713-846   | Pre-delegation protocol, delegation table, required reading |
| Core Workflows      | 924-940   | TDD, Feature Addition, Refactoring, Debugging, Code Review  |
| Common Patterns     | 1227-1246 | Delegation anti-patterns table                              |

**python3-typing (~350 lines target)**

| Section                          | Lines   | Description                                       |
| -------------------------------- | ------- | ------------------------------------------------- |
| Type Safety Requirements         | 274-279 | Introduction to typing requirements               |
| When to Use Generics             | 281-364 | TypeVar patterns, bounds, restrictions, Self type |
| When to Use Protocols            | 365-436 | Structural typing, runtime_checkable              |
| TypedDict                        | 438-506 | Required/optional fields, mixed patterns          |
| Type Narrowing                   | 507-569 | isinstance, None checks, TypeGuard, TypeIs        |
| attrs vs dataclasses vs pydantic | 570-639 | Decision matrix                                   |
| Additional Mypy Features         | 641-677 | Generic dataclasses, Self type chaining           |
| Mypy Configuration               | 679-711 | pyproject.toml strict mode                        |

**python3-cli (~200 lines target)**

| Section                      | Lines   | Description                           |
| ---------------------------- | ------- | ------------------------------------- |
| Script Dependency Trade-offs | 127-156 | Typer+Rich vs stdlib decision         |
| Rich Panel/Table Width       | 157-217 | get_rendered_width() pattern          |
| Rich Emoji Usage             | 218-247 | Token patterns for cross-platform     |
| Exception Handling           | 249-271 | Fail-fast principle with code example |

**python3-quality (~250 lines target)**

| Section                      | Lines     | Description                                              |
| ---------------------------- | --------- | -------------------------------------------------------- |
| Linting Discovery Protocol   | 942-1046  | Discovery sequence, format-first, type checker detection |
| Quality Gates                | 1047-1086 | Gate sequence with CI verification                       |
| Linting Exception Conditions | 1087-1129 | Acceptable exceptions, rule codes to fix                 |

**python3-project (~200 lines target)**

| Section                      | Lines     | Description                                           |
| ---------------------------- | --------- | ----------------------------------------------------- |
| Python Development Standards | 98-126    | Core concepts, docstring standard, template variables |
| Command Usage                | 848-923   | /modernpython and /shebangpython                      |
| Standard Project Structure   | 1130-1162 | Directory layout, hatchling config                    |
| Integration                  | 1163-1181 | External reference example                            |
| Using Asset Templates        | 1182-1226 | Template copy instructions                            |
| Detailed Documentation       | 1248-1304 | Reference file links                                  |

### Reference Files Inventory

**Total reference files**: 26 files across 3 subdirectories

**Top-level references/** (9 files):

| File                                | Lines   | Size  | Used By                                                  |
| ----------------------------------- | ------- | ----- | -------------------------------------------------------- |
| tool-library-registry.md            | 4,647   | 114KB | python3-typing, python3-quality, python3-project         |
| modern-modules.md                   | 1,477   | 31KB  | python3-project                                          |
| user-project-conventions.md         | 836     | 24KB  | python3-quality, python3-project                         |
| python-development-orchestration.md | 612     | 19KB  | python3-workflow (primary)                               |
| PEP723.md                           | 556     | 13KB  | python3-project                                          |
| exception-handling.md               | 419     | 15KB  | python3-cli                                              |
| api_reference.md                    | 45      | 1KB   | python3-project                                          |
| accessing_online_resources.md       | SYMLINK | -     | python3-workflow (symlink to agent-orchestration plugin) |

**references/mypy-docs/** (5 files):

| File                    | Lines | Used By        |
| ----------------------- | ----- | -------------- |
| generics.rst            | 723   | python3-typing |
| protocols.rst           | 416   | python3-typing |
| type_narrowing.rst      | 396   | python3-typing |
| additional_features.rst | 239   | python3-typing |
| typed_dict.rst          | 220   | python3-typing |

**references/modern-modules/** (18 files):

| File                | Lines |
| ------------------- | ----- |
| python-diskcache.md | 951   |
| copier.md           | 803   |
| paho-mqtt.md        | 712   |
| fabric.md           | 703   |
| box.md              | 686   |
| datasette.md        | 684   |
| robotframework.md   | 657   |
| python-dotenv.md    | 652   |
| httpx.md            | 639   |
| bidict.md           | 604   |
| blinker.md          | 588   |
| arrow.md            | 569   |
| GitPython.md        | 554   |
| boltons.md          | 521   |
| prefect.md          | 512   |
| attrs.md            | 496   |
| uvloop.md           | 486   |
| shiv.md             | 470   |

### Assets Inventory

**assets/** directory contains:

| Path                                         | Type     | Purpose                                        |
| -------------------------------------------- | -------- | ---------------------------------------------- |
| version.py                                   | Python   | Dual-mode version management template          |
| hatch_build.py                               | Python   | Build hook for binary/asset handling           |
| .markdownlint.json                           | Config   | Markdown linting configuration                 |
| .claude/settings.local.json                  | Config   | Claude settings template                       |
| typer_examples/index.md                      | Markdown | Index of Typer/Rich examples                   |
| typer_examples/console_no_wrap_example.py    | Python   | Plain text wrapping solutions                  |
| typer_examples/console_containers_no_wrap.py | Python   | Panel/Table width handling                     |
| typer_examples/.mypy_cache/                  | Cache    | Mypy cache (should be excluded from migration) |

### Commands Inventory

**commands/development/** (3 files):

| File                          | Purpose                                 | Needs Frontmatter Fix                                        |
| ----------------------------- | --------------------------------------- | ------------------------------------------------------------ |
| create-feature-task.md        | Feature development task setup          | YES - remove title, command_type, last_updated, related_docs |
| use-command-template.md       | Create new slash commands from template | YES - same fixes                                             |
| templates/command-template.md | Template file (not invocable)           | YES - add user-invocable: false                              |

**commands/testing/** (3 files):

| File                         | Purpose                   | Needs Frontmatter Fix |
| ---------------------------- | ------------------------- | --------------------- |
| analyze-test-failures.md     | Test failure analysis     | YES                   |
| comprehensive-test-review.md | Test suite review         | YES                   |
| test-failure-mindset.md      | Test debugging guidelines | YES                   |

**commands/development/config/** (directory exists but not documented for migration)

### Cross-Reference Map

**Internal references within SKILL.md (31 total)**:

- `./references/user-project-conventions.md` - referenced 3 times (lines 46, 117, 1225)
- `./references/modern-modules.md` - referenced 2 times (lines 47, 1260)
- `./references/tool-library-registry.md` - referenced 4 times (lines 48, 121, 643, 711, 1262)
- `./references/api_reference.md` - referenced 2 times (lines 49, 1264)
- `./references/python-development-orchestration.md` - referenced 7 times (lines 50, 154, 725, 810, 826, 928, 1244, 1252)
- `./references/exception-handling.md` - referenced 2 times (lines 271, 1256)
- `./references/PEP723.md` - referenced 2 times (lines 910, 1254)
- `./references/mypy-docs/generics.rst` - referenced 1 time (line 292)
- `./references/mypy-docs/protocols.rst` - referenced 1 time (line 376)
- `./references/mypy-docs/typed_dict.rst` - referenced 1 time (line 449)
- `./references/mypy-docs/type_narrowing.rst` - referenced 1 time (line 518)
- `./references/mypy-docs/additional_features.rst` - referenced 2 times (lines 597, 643)
- `./references/accessing_online_resources.md` - referenced 1 time (line 880)

**Asset references within SKILL.md**:

- `./assets/typer_examples/index.md` - referenced 2 times (lines 155, 213)
- `~/.claude/skills/python3-development/assets/*` - referenced 6 times in template copy instructions (lines 1187, 1194, 1201, 1207, 1213, 1222)

**Symlink dependency**:

- `./references/accessing_online_resources.md` is a symlink pointing to `/home/user/repos/claude_skills/plugins/agent-orchestration/skills/agent-orchestration/references/accessing_online_resources.md`
- This symlink must be preserved or recreated after migration

### External Dependencies on This Skill

**Skills that reference python3-development** (6 external skills):

| Plugin             | File                                  | Reference Type                                                              |
| ------------------ | ------------------------------------- | --------------------------------------------------------------------------- |
| holistic-linting   | SKILL.md                              | Activates skill via `Skill(skill: "python3-development")` (lines 449-580) |
| holistic-linting   | linting-root-cause-resolver.md        | Requires loading skill (line 20-22)                                         |
| holistic-linting   | post-linting-architecture-reviewer.md | Standards checklist reference (line 41)                                     |
| fastmcp-creator    | SKILL.md                              | RULE requiring activation before Python MCP projects (lines 182-199)        |
| xdg-base-directory | SKILL.md                              | Related skill reference (line 587)                                          |
| toml-python        | SKILL.md, README.md                   | Related skill reference (lines 624, 75)                                     |
| verification-gate  | SKILL.md                              | Activation trigger example (line 315)                                       |

**Agents that reference python3-development** (3 agents):

| Agent                                      | Reference                            |
| ------------------------------------------ | ------------------------------------ |
| agent-creator/references/agent-examples.md | Skills dependency example (line 339) |
| plugin-refactor:refactor-skill.md          | Breaking changes warning (line 376)  |
| plugin-assessor.md                         | Assessment example (line 802)        |

**Commands/workflows that reference python3-development**:

| File                  | Reference                         |
| --------------------- | --------------------------------- |
| how-to-delegate.md    | Flowchart reference (line 67)     |
| implement-refactor.md | Task file example (lines 98, 103) |
| complete-refactor.md  | Progress tracking (line 423)      |

**CRITICAL**: After refactoring, the original skill name `python3-development` MUST continue to work as an alias or redirect to maintain backward compatibility with all external dependencies listed above.

### Orphaned Files

**planning/reference-document-architecture.md** (65,328 bytes, 1 file):

- Status: `historical-proposal`, `implementation_status: not-implemented`
- Not linked from any active documentation
- Resolution: Move to `./plugins/python3-development/docs/archive/`

### Migration Path Summary

**Phase 1**: Create 5 skill directories + plugin.json + archive orphan

- New directories: python3-workflow, python3-typing, python3-cli, python3-quality, python3-project
- Create plugin.json with skill and command metadata
- Move planning/ to docs/archive/

**Phase 2**: Create 5 new SKILL.md files (parallelizable) + fix 6 command frontmatter files

- Each skill extracts content from line ranges documented above
- Commands get standardized frontmatter with trigger-optimized descriptions

**Phase 3**: Move references/ and assets/ to python3-project, update relative paths

- All 26 reference files move to `./skills/python3-project/references/`
- All asset files move to `./skills/python3-project/assets/`
- Other 4 skills reference via `../python3-project/references/`
- Delete original python3-development/ directory

**Phase 4**: Validation

- Test plugin with `claude --plugin-dir ./plugins/python3-development`
- Test skill loading for all 5 skills
- Verify all cross-references resolve
- Run pre-commit on modified files
- Update README.md

### Technical Reference Details

**Frontmatter schema for new skills**:

```yaml
---
name: python3-{domain}
description: 'Use when: [trigger conditions]. Provides: [capabilities].'
---
```

**Relative path patterns after migration**:

- From python3-workflow to references: `../python3-project/references/python-development-orchestration.md`
- From python3-typing to mypy-docs: `../python3-project/references/mypy-docs/generics.rst`
- From python3-cli to assets: `../python3-project/assets/typer_examples/index.md`

**Symlink recreation command**:

```bash
ln -sf /home/user/repos/claude_skills/plugins/agent-orchestration/skills/agent-orchestration/references/accessing_online_resources.md \
  ./plugins/python3-development/skills/python3-project/references/accessing_online_resources.md
```

---

## Dependency Summary

### Phase 1: Foundation (Parallel Execution)

- **Task 1.1** (directories), **Task 1.2** (plugin.json), **Task 1.3** (archive orphan)
- No dependencies between tasks - all can run simultaneously
- **Blocking**: Phase 2 skill creation

### Phase 2A: Skill Creation (Parallel Execution)

- **Task 2.1** (workflow), **Task 2.2** (typing), **Task 2.3** (cli), **Task 2.4** (quality), **Task 2.5** (project)
- All depend on **Task 1.1** only
- No dependencies between tasks - all can run simultaneously
- **Blocking**: Phase 3 migrations

### Phase 2B: Command Fixes (Parallel with Phase 2A)

- **Task 2.6** (fix 6 command frontmatter files)
- No dependencies - can run simultaneously with Phase 2A
- **Blocking**: None (independent work)

### Phase 3: Migration (Sequential with Some Parallelism)

- **Task 3.1** (move references) and **Task 3.2** (move assets) - PARALLEL
- Both depend on Phase 2 completion
- **Task 3.3** (update paths) depends on **Task 3.1** + **Task 3.2**
- **Task 3.4** (delete old) depends on **Task 3.3**
- **Blocking**: Validation phase

### Phase 4: Validation (Mostly Sequential)

- **Task V1** (plugin assessment) depends on all Phase 1-3 tasks
- **Task V2** (docs) depends on **Task V1**
- **Task V3** (plugin testing) depends on **Task V1** - PARALLEL with **Task V2**
- **Task V4** (pre-commit) depends on **Task V1** + **Task V2** - PARALLEL with **Task V3**

### Parallelization Summary

- **Maximum parallel tasks**: 5 (during Phase 2A skill creation) or 6 (if including Phase 2B)
- **Critical path**: Phase 1 → Phase 2 → Phase 3 → Phase 4 (minimum 4 sequential stages)
- **Total tasks**: 19

---

## Success Metrics

### Quantitative Targets

- [ ] Each new skill under 400 lines (python3-typing ≤400, others ≤300)
- [ ] All 5 skills load without errors via symlinks
- [ ] All 6 commands appear in `/help` menu with descriptions
- [ ] All reference file links resolve (0 broken links)
- [ ] Pre-commit passes on all modified files
- [ ] Assessment score ≥85/100 (from 62/100 baseline)

### Qualitative Targets

- [ ] Each skill has single, focused domain
- [ ] Skill descriptions contain "Use when:" and "Provides:" trigger keywords
- [ ] Progressive disclosure maintained (SKILL.md → references/)
- [ ] Orchestrator-only sections preserved in python3-workflow only
- [ ] Asset templates accessible from python3-project with clear usage instructions
