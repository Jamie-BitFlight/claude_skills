# Plugin Assessment Report Format

Use this template when writing assessment reports. Write the report inline in your response unless the plugin is large (>20 files), in which case write it to `.claude/reports/plugin-assessment-{plugin-name}.md`.

## Report Structure

```markdown
# Plugin Assessment Report: {plugin-name}

## Executive Summary

- **Overall Score**: X/100
- **Marketplace Ready**: Yes / No / With Changes
- **Critical Issues**: N
- **Warnings**: N
- **Recommendations**: N
- **Files Analyzed**: N

### Key Findings
- {Most important finding 1}
- {Most important finding 2}
- {Most important finding 3}

## 1. Discovery Summary

| Category | Count | Files |
|----------|-------|-------|
| Skills | N | {list} |
| Commands | N | {list} |
| Agents | N | {list} |
| Reference Docs | N | {list} |
| Config Files | N | {list} |

**Total Plugin Size**: ~N lines across N files

## 2. Plugin Manifest

**Status**: Valid / Invalid / Incomplete

### Issues
- [CRITICAL/WARNING] {description}

### Recommendations
- {specific improvement}

## 3. Skills Assessment

### Overview
| Skill | Status | Description Quality | Lines | References | Orphans |
|-------|--------|---------------------|-------|------------|---------|
| {name} | Pass/Warn/Fail | X/10 | N | N linked | N orphaned |

### {skill-name} Details

**Location**: `skills/{name}/SKILL.md`

#### Frontmatter Issues
- [{severity}] {description}

#### Reference File Audit

**Orphaned Files** (NOT referenced from SKILL.md):
| File | Classification | Lines | Recommendation |
|------|----------------|-------|----------------|
| ./references/{file} | New Content / Duplicate / Notes / Examples | N | {action} |

**Orphan Details** (for each orphaned file):

```
ORPHANED: ./references/{filename}.md
CONTENT: {N} lines of {brief description}
ANALYSIS: {unique vs duplicate, extends vs outdated}
RECOMMENDATION: {specific action}
SUGGESTED LINK: [Display Text](./references/{filename}.md) — add under "## {Section}"
```

#### Link Validation

| Source | Target | Status |
|--------|--------|--------|
| SKILL.md:{line} | ./references/api.md | Valid / Broken |

## 4. Commands Assessment

### {command-name}

**Location**: `commands/{name}.md`

#### Issues
- [{severity}] {description}

## 5. Agents Assessment

### {agent-name}

**Location**: `agents/{name}.md`

#### Issues
- [{severity}] {description}

## 6. Cross-Reference Analysis

### Documentation Link Graph

```
SKILL.md
├── ./references/api.md (linked)
└── ./references/advanced.md (NOT LINKED — orphaned)
```

### Link Validation Summary

| Status | Count |
|--------|-------|
| Valid links | N |
| Broken links | N |
| Orphaned files | N |
| Missing back-links | N |

## 7. Enhancement Opportunities

### High Priority
1. **{Enhancement Name}** — Type: Script/Tool/MCP/Documentation/Structure — Benefit: {specific benefit} — Effort: Low/Medium/High

## 8. Scoring Breakdown

| Component | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Structural validity | 20% | X/100 | X |
| Manifest completeness | 15% | X/100 | X |
| Frontmatter correctness | 20% | X/100 | X |
| Description quality | 15% | X/100 | X |
| Reference organization | 15% | X/100 | X |
| Documentation quality | 10% | X/100 | X |
| Enhancement potential | 5% | X/100 | X |
| **Total** | **100%** | — | **X/100** |

## 9. Action Items

### Critical (Must Fix Before Release)
- [ ] {action item with file:line reference}

### Recommended (Should Fix)
- [ ] {action item}

### Optional (Nice to Have)
- [ ] {action item}

### Orphan Resolution Checklist
- [ ] {specific file}: {specific action}
```
