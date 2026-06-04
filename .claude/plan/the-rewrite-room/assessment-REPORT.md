# Plugin Assessment Report: the-rewrite-room

## Executive Summary

- **Overall Score**: 76/100
- **Marketplace Ready**: With Changes
- **Critical Issues**: 3
- **Warnings**: 7
- **Recommendations**: 6
- **Files Analyzed**: 24

### Key Findings

- Missing `/rwr:doc-to-skill` command file -- listed in SKILL.md Command Reference but no `commands/rwr/doc-to-skill.md` exists
- Both SKILL.md files exceed 4000-token threshold (SK005-level): `the-rewrite-room` at ~1933 tokens, `user-docs-to-ai-skill` at ~2786 tokens -- within limits but the latter is approaching the warning zone
- Broken cross-reference: `the-rewrite-room/workflows/audit.md` references a non-existent `validate.md` workflow file
- `plugin.json` is missing recommended fields (`version`, `description` are present but `repository` and `license` are absent)
- Absolute path to user home directory hardcoded in agent file `rewrite-room-auditor.md:44`
- `the-rewrite-room/` directory at the plugin root is a non-standard location for workflow files

## 1. Discovery Summary

| Category | Count | Files |
|----------|-------|-------|
| Skills | 2 | `the-rewrite-room`, `user-docs-to-ai-skill` |
| Commands | 4 | `rwr/audit`, `rwr/author`, `rwr/cite`, `rwr/optimize` |
| Agents | 5 | `rewrite-room-auditor`, `rewrite-room-author`, `rewrite-room-cite`, `rewrite-room-doc-converter`, `rewrite-room-optimizer` |
| Reference Docs | 5 | `input-resolution.md`, `extraction-patterns.md`, `workflow-identification.md`, `skill-structure-guide.md`, `quality-criteria.md` |
| Workflow Files | 3 | `audit.md`, `author.md`, `optimize.md` |
| Config Files | 2 | `plugin.json`, `hooks/hooks.json` |
| Other | 2 | `README.md`, `assets/hero.png` |

**Total Plugin Size**: ~2972 lines across 23 files (excluding binary asset)

## 2. Plugin Manifest

**Status**: Valid with warnings

**File**: `.claude-plugin/plugin.json`

### Issues

- [WARNING] `plugin.json:1`: Missing `license` field (recommended for marketplace distribution)
- [WARNING] `plugin.json:1`: Missing `repository` field (recommended for marketplace distribution)
- [WARNING] `plugin.json:1`: Missing `homepage` field (recommended for marketplace distribution)

### Valid Fields

- `name`: "rwr" -- valid kebab-case identifier
- `version`: "2.5.10" -- valid semver
- `description`: Present, comprehensive, includes trigger phrases
- `author`: Present with `name` and `url`
- `keywords`: Present, 9 relevant tags
- `mcpServers`: Properly configured `file-reader` MCP server

### Recommendations

- Add `license` field (e.g., `"MIT"`)
- Add `repository` field pointing to source repository
- Note: `agents`, `skills`, `commands` keys are correctly omitted -- auto-discovery handles all components in default locations

## 3. Skills Assessment

### Overview

| Skill | Status | Description Quality | Chars | Est. Tokens | References | Orphans |
|-------|--------|---------------------|-------|-------------|------------|---------|
| `the-rewrite-room` | Warn | 9/10 | 7730 | ~1933 | 0 (routing skill) | 0 |
| `user-docs-to-ai-skill` | Pass | 9/10 | 11143 | ~2786 | 5 linked | 0 |

### the-rewrite-room Details

**Location**: `skills/the-rewrite-room/SKILL.md`

**skilllint result**: Pass (PD001, PD002, PD003 informational -- no references/, examples/, scripts/ dirs; acceptable for a routing skill)

#### Frontmatter Validation

- `name`: "the-rewrite-room" -- matches directory name. PASS.
- `description`: Single line, no multiline indicators, no invalid colons. Contains trigger scenarios. PASS.
- `allowed-tools`: Comma-separated string format. PASS.
- No `model` field -- acceptable, inherits from caller.

#### Content Issues

- [CRITICAL] Line 26: Command Reference table lists `/rwr:doc-to-skill` with "rewrite-room-doc-converter" as Entry Agent, but no `commands/rwr/doc-to-skill.md` file exists. The command cannot be invoked via the slash command system without this file.
  - **Source**: `claude-skills-overview-2026` -- "Skills and slash commands are now unified"
  - **Fix**: Create `commands/rwr/doc-to-skill.md` with `agent: rewrite-room-doc-converter` frontmatter

- [WARNING] Lines 54-56: Workflow file paths use non-standard location `plugins/the-rewrite-room/the-rewrite-room/workflows/`. This nested `the-rewrite-room/` directory is unusual; workflow files would be better placed under `skills/the-rewrite-room/references/workflows/` to follow the standard skill directory structure.

- [WARNING] Lines 96-98: Absolute path `/home/user/.claude/agents/doc-freshness-guardian.md` is hardcoded. This path is not portable across installations.

#### Link Validation

| Source | Target | Status |
|--------|--------|--------|
| SKILL.md:54 | `plugins/the-rewrite-room/the-rewrite-room/workflows/audit.md` | Valid (non-standard path) |
| SKILL.md:55 | `plugins/the-rewrite-room/the-rewrite-room/workflows/optimize.md` | Valid (non-standard path) |
| SKILL.md:56 | `plugins/the-rewrite-room/the-rewrite-room/workflows/author.md` | Valid (non-standard path) |

### user-docs-to-ai-skill Details

**Location**: `skills/user-docs-to-ai-skill/SKILL.md`

**skilllint result**: Pass (PD002, PD003 informational)

#### Frontmatter Validation

- `name`: "user-docs-to-ai-skill" -- matches directory name. PASS.
- `description`: Single line, comprehensive, includes format list and trigger scenarios. PASS.
- `allowed-tools`: Comma-separated string. PASS.
- `argument-hint`: Present. PASS.

#### Content Issues

- No issues found. Skill is well-structured with clear phase workflow, proper Mermaid flowcharts, and all 5 reference files linked.

#### Reference File Audit

All 5 reference files are linked from SKILL.md. No orphans detected.

| File | Lines | Status | Quality |
|------|-------|--------|---------|
| `references/input-resolution.md` | 178 | Linked (lines 73, 96) | ToC present, Mermaid diagrams, anti-patterns section |
| `references/extraction-patterns.md` | 845 | Linked (lines 106-108) | ToC present, comprehensive format coverage, verbatim examples |
| `references/workflow-identification.md` | 187 | Linked (lines 124, 208) | ToC present, detection criteria, delegation prompt template |
| `references/skill-structure-guide.md` | 337 | Linked (lines 179, 185, 193) | ToC present, frontmatter rules, progressive disclosure |
| `references/quality-criteria.md` | 233 | Linked (lines 200, 210) | ToC present, checklist format, failure mode catalog |

#### Link Validation

| Source | Target | Status |
|--------|--------|--------|
| SKILL.md:73 | `./references/input-resolution.md` | Valid |
| SKILL.md:96 | `./references/input-resolution.md` | Valid |
| SKILL.md:106 | `./references/extraction-patterns.md` | Valid |
| SKILL.md:124 | `./references/workflow-identification.md` | Valid |
| SKILL.md:179 | `./references/skill-structure-guide.md` | Valid |
| SKILL.md:185 | `./references/skill-structure-guide.md` | Valid |
| SKILL.md:193 | `./references/skill-structure-guide.md` | Valid |
| SKILL.md:200 | `./references/quality-criteria.md` | Valid |
| SKILL.md:206-210 | All 5 reference files | Valid |

## 4. Commands Assessment

### rwr/audit.md

**Location**: `commands/rwr/audit.md`

#### Frontmatter Validation

- `description`: Present, single line. PASS.
- `argument-hint`: Present, helpful. PASS.
- `agent`: "rewrite-room-auditor" -- references existing agent. PASS.
- `allowed-tools`: Comma-separated. PASS.
- No `name` field -- acceptable for commands (they derive name from path).

#### Issues

- No issues found.

### rwr/author.md

**Location**: `commands/rwr/author.md`

#### Issues

- No issues found. Frontmatter valid, agent reference valid.

### rwr/optimize.md

**Location**: `commands/rwr/optimize.md`

#### Issues

- No issues found. Frontmatter valid, agent reference valid.

### rwr/cite.md

**Location**: `commands/rwr/cite.md`

#### Issues

- No issues found. Frontmatter valid, agent reference valid. `allowed-tools` differs from other commands (adds `WebFetch, WebSearch` -- appropriate for citation work).

### Missing: rwr/doc-to-skill.md

- [CRITICAL] No command file exists for `/rwr:doc-to-skill`. The SKILL.md Command Reference table (line 26) lists this command with `rewrite-room-doc-converter` as its Entry Agent, but the command file `commands/rwr/doc-to-skill.md` does not exist.
  - **Impact**: Users cannot invoke `/rwr:doc-to-skill` via the slash command system.
  - **Fix**: Create `commands/rwr/doc-to-skill.md` following the same pattern as other commands in this directory.

## 5. Agents Assessment

### rewrite-room-auditor

**Location**: `agents/rewrite-room-auditor.md` (64 lines)

#### Frontmatter Validation

- `name`: Present, matches filename convention. PASS.
- `description`: Present, quoted string, single line, no invalid colons. PASS.
- `tools`: Comma-separated string. PASS.
- `model`: "sonnet" -- valid alias. PASS.
- `color`: "orange" -- valid. PASS.

#### Content Issues

- [WARNING] Line 44: Hardcoded absolute path `/home/user/.claude/agents/doc-freshness-guardian.md`. This makes the agent non-portable across installations.
  - **Fix**: Use a relative path or note that this is a personal agent that must exist on the user's machine.
- Delegation trigger keywords in description are clear ("audits", "syncs", "tracks doc freshness"). PASS.
- Output contract present and well-structured. PASS.
- Mermaid task routing diagram present. PASS.

### rewrite-room-author

**Location**: `agents/rewrite-room-author.md` (107 lines)

#### Frontmatter Validation

- All required fields present and valid. PASS.

#### Content Issues

- No issues found. Well-structured with task routing Mermaid, specialist agent table, reference files table, no-loss rewrite rule, fidelity rules, and output contract.

### rewrite-room-cite

**Location**: `agents/rewrite-room-cite.md` (135 lines)

#### Frontmatter Validation

- All required fields present and valid. PASS.
- `tools` includes `WebFetch, WebSearch` -- appropriate for citation work. PASS.

#### Content Issues

- [RECOMMENDATION] This agent at 135 lines is the largest agent but well within acceptable limits. No optimization needed.
- Strong quality standards section with explicit MUST/MUST NOT constraints. PASS.

### rewrite-room-doc-converter

**Location**: `agents/rewrite-room-doc-converter.md` (65 lines)

#### Frontmatter Validation

- All required fields present and valid. PASS.

#### Content Issues

- No issues found. Properly references the `user-docs-to-ai-skill` skill as the SOP to follow.

### rewrite-room-optimizer

**Location**: `agents/rewrite-room-optimizer.md` (62 lines)

#### Frontmatter Validation

- All required fields present and valid. PASS.

#### Content Issues

- No issues found. Clear task routing, reference files table, critical rules section, output contract.

## 6. Hooks Validation

**File**: `hooks/hooks.json`

### Structure Validation

- `description` field: Present. PASS.
- `hooks` object: Present with `SubagentStop` event. PASS.
- Event name `SubagentStop`: Valid Claude Code hook event (confirmed in `claude-plugins-reference-2026`). PASS.
- Hook type `prompt`: Valid hook type. PASS.
- `timeout`: 10000ms -- reasonable for LLM evaluation. PASS.

### Content Validation

- The prompt correctly filters by agent name prefix `rewrite-room-` before applying validation. PASS.
- Validates all 4 STATUS block fields (STATUS, SUMMARY, ARTIFACTS, VALIDATION). PASS.
- Returns `{"ok": true}` for non-rewrite-room agents (no false positives). PASS.

### Issues

- No issues found. Hook is well-designed with proper scoping.

## 7. MCP Configuration

**Location**: Inline in `plugin.json` under `mcpServers` key.

### Validation

- Server name: `file-reader` -- valid identifier. PASS.
- `command`: "uvx" -- valid command. PASS.
- `args`: `["mcp-file-contents-reader"]` -- valid array. PASS.
- No `env` or `cwd` configuration -- acceptable for this simple server. PASS.

### Issues

- No issues found. The MCP server is properly configured and aligned with the `user-docs-to-ai-skill` workflow which references the `file-reader` MCP server for binary document formats.

## 8. Cross-Reference Analysis

### Documentation Link Graph

```text
skills/the-rewrite-room/SKILL.md (routing skill)
|-- Commands referenced:
|   |-- commands/rwr/audit.md (EXISTS)
|   |-- commands/rwr/author.md (EXISTS)
|   |-- commands/rwr/optimize.md (EXISTS)
|   |-- commands/rwr/cite.md (EXISTS)
|   |-- commands/rwr/doc-to-skill.md (MISSING -- CRITICAL)
|
|-- Agents referenced:
|   |-- agents/rewrite-room-auditor.md (EXISTS)
|   |-- agents/rewrite-room-author.md (EXISTS)
|   |-- agents/rewrite-room-optimizer.md (EXISTS)
|   |-- agents/rewrite-room-cite.md (EXISTS)
|   |-- agents/rewrite-room-doc-converter.md (EXISTS)
|
|-- Workflow files referenced:
|   |-- the-rewrite-room/workflows/audit.md (EXISTS)
|   |-- the-rewrite-room/workflows/author.md (EXISTS)
|   |-- the-rewrite-room/workflows/optimize.md (EXISTS)
|
|-- External agents referenced (not bundled):
|   |-- development-harness:doc-drift-auditor (EXTERNAL)
|   |-- development-harness:service-docs-maintainer (EXTERNAL)
|   |-- doc-freshness-guardian (PERSONAL AGENT -- non-portable)
|   |-- plugin-creator:contextual-ai-documentation-optimizer (EXTERNAL)
|   |-- plugin-creator:subagent-refactorer (EXTERNAL)
|   |-- gitlab-docs-expert (EXTERNAL -- unclear source)
|   |-- documentation-expert (EXTERNAL -- unclear source)
|   |-- summarizer:file-summarizer (EXTERNAL)
|   |-- summarizer:url-summarizer (EXTERNAL)
|   |-- summarizer:image-summarizer (EXTERNAL)
|   |-- process-siren:process-siren (EXTERNAL)

skills/user-docs-to-ai-skill/SKILL.md
|-- references/input-resolution.md (LINKED)
|-- references/extraction-patterns.md (LINKED)
|-- references/workflow-identification.md (LINKED)
|-- references/skill-structure-guide.md (LINKED)
|-- references/quality-criteria.md (LINKED)
```

### Workflow File Cross-References

```text
the-rewrite-room/workflows/audit.md
|-- References validate.md workflow (BROKEN -- file does not exist)

the-rewrite-room/workflows/optimize.md
|-- No broken references

the-rewrite-room/workflows/author.md
|-- No broken references
```

### Link Validation Summary

| Status | Count |
|--------|-------|
| Valid internal links | 16 |
| Broken internal links | 1 (validate.md workflow) |
| Missing command file | 1 (doc-to-skill.md) |
| Orphaned files | 0 |
| Non-portable paths | 2 (absolute home directory paths) |

### Declared vs Actual Capabilities

- `plugin.json` description mentions: audit, drift, sync, summarization, prompt-optimization, GLFM, routing
- Actual capabilities match -- all described capabilities have corresponding agents and commands
- Exception: `/rwr:doc-to-skill` is declared but not fully wired (missing command file)

## 9. Workflow Files Assessment

**Location**: `the-rewrite-room/workflows/` (non-standard)

### Issues

- [WARNING] Workflow files are located at `the-rewrite-room/workflows/` under the plugin root. This creates a `the-rewrite-room/the-rewrite-room/` nesting when viewed from the plugin root. Standard convention would place these under `skills/the-rewrite-room/references/workflows/` or similar.

- [CRITICAL] `audit.md:78`: References non-existent workflow file `plugins/the-rewrite-room/the-rewrite-room/workflows/validate.md`. This file does not exist in the plugin.
  - **Impact**: The audit workflow's "chain to validate" branch will fail at runtime.
  - **Fix**: Either create the `validate.md` workflow file or remove the reference.

### Content Quality

- `audit.md` (99 lines): Well-structured with Mermaid flowcharts for task classification and return handling. Output contract present.
- `optimize.md` (114 lines): Includes revision cycle logic with escalation. Frontmatter validation step integrated.
- `author.md` (159 lines): Comprehensive routing for summarization, GLFM validation, and authoring subtypes.

## 10. Enhancement Opportunities

### High Priority

1. **Create missing `/rwr:doc-to-skill` command file** -- Type: Structure Fix -- Benefit: Enables the declared doc-to-skill command -- Effort: Low
2. **Create or remove `validate.md` workflow reference** -- Type: Structure Fix -- Benefit: Eliminates broken cross-reference -- Effort: Low
3. **Remove hardcoded absolute paths** -- Type: Portability Fix -- Benefit: Plugin works across installations -- Effort: Low

### Medium Priority

4. **Move workflow files to standard location** -- Type: Structure Improvement -- Benefit: Follows plugin directory conventions, eliminates confusing `the-rewrite-room/the-rewrite-room/` nesting -- Effort: Medium
5. **Add dependency documentation** -- Type: Documentation -- Benefit: Users know which external plugins are required (development-harness, plugin-creator, summarizer, gitlab-skill, process-siren) -- Effort: Low

### Low Priority

6. **Add examples/ directory** -- Type: Progressive Disclosure -- Benefit: Show example inputs and outputs for doc-to-skill conversion -- Effort: Medium

## 11. Scoring Breakdown

| Component | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Structural validity | 20% | 70/100 | 14.0 |
| Manifest completeness | 15% | 80/100 | 12.0 |
| Frontmatter correctness | 20% | 95/100 | 19.0 |
| Description quality | 15% | 90/100 | 13.5 |
| Reference organization | 15% | 85/100 | 12.75 |
| Documentation quality | 10% | 80/100 | 8.0 |
| Enhancement potential | 5% | 60/100 | 3.0 |
| **Total** | **100%** | -- | **82.25 -> 76/100** |

**Score adjustment**: -6 points for 3 critical issues (missing command file, broken workflow reference, non-portable absolute paths).

### Scoring Rationale

- **Structural validity (70)**: Correct directory structure overall, but missing command file and non-standard workflow location cost points. The `the-rewrite-room/the-rewrite-room/` nesting is structurally confusing.
- **Manifest completeness (80)**: All required fields present, MCP server configured, but missing recommended fields (license, repository, homepage).
- **Frontmatter correctness (95)**: All frontmatter across all files is valid. Single-line descriptions, correct field types, proper comma-separated tools. Near-perfect.
- **Description quality (90)**: Descriptions are actionable with trigger phrases and clear scope. The main skill description covers routing well. Agent descriptions clearly state delegation intent.
- **Reference organization (85)**: `user-docs-to-ai-skill` has excellent reference organization -- all 5 files linked, ToCs present, no orphans. The main routing skill appropriately has no references.
- **Documentation quality (80)**: Workflow files are well-documented with Mermaid diagrams. Output contracts are consistent. Missing: dependency documentation for external plugins.
- **Enhancement potential (60)**: Clear gaps identified but none are novel features -- they are structural fixes.

## 12. Action Items

### Critical (Must Fix Before Release)

- [ ] Create `commands/rwr/doc-to-skill.md` with frontmatter `agent: rewrite-room-doc-converter` to match the Command Reference table in SKILL.md
- [ ] Fix broken reference to `validate.md` in `the-rewrite-room/workflows/audit.md:78` -- either create the file or remove the Mermaid branch
- [ ] Replace absolute path `/home/user/.claude/agents/doc-freshness-guardian.md` in `agents/rewrite-room-auditor.md:44` and `skills/the-rewrite-room/SKILL.md:98` with a note that this is a personal agent dependency

### Recommended (Should Fix)

- [ ] Add `license`, `repository`, and `homepage` fields to `plugin.json`
- [ ] Move workflow files from `the-rewrite-room/workflows/` to `skills/the-rewrite-room/references/workflows/` to follow standard skill directory structure
- [ ] Add a "Dependencies" or "Required Plugins" section to the README or SKILL.md listing external plugin dependencies: `development-harness`, `plugin-creator`, `summarizer`, `gitlab-skill`, `process-siren`
- [ ] Document that `doc-freshness-guardian` is a personal agent (not bundled) and must be installed separately

### Optional (Nice to Have)

- [ ] Add `examples/` directory to `user-docs-to-ai-skill` with sample input docs and expected output
- [ ] Add `scripts/` directory if any automation is planned
- [ ] Consider adding a `validate` workflow file for the markdown validation chain referenced in the audit workflow

### Refactoring Recommendations

| Target | Issue Type | Severity | Recommended Agent | Expected Outcome |
|--------|-----------|----------|-------------------|------------------|
| `commands/rwr/doc-to-skill.md` | STRUCTURE_FIX | Critical | Manual creation (follows existing pattern) | `/rwr:doc-to-skill` command becomes invocable |
| `the-rewrite-room/workflows/audit.md:78` | STRUCTURE_FIX | Critical | Manual edit | Broken validate.md reference resolved |
| `agents/rewrite-room-auditor.md:44` | STRUCTURE_FIX | Critical | `plugin-creator:contextual-ai-documentation-optimizer` | Absolute path replaced with portable reference |
| `the-rewrite-room/workflows/` | STRUCTURE_FIX | Medium | Manual move + link updates | Standard directory structure |
| `plugin.json` | DOC_IMPROVE | Medium | Manual edit | Marketplace-ready metadata |
| SKILL.md dependency docs | DOC_IMPROVE | Medium | `plugin-creator:contextual-ai-documentation-optimizer` | Users know what external plugins are required |
