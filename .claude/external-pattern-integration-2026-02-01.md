# External Pattern Integration

**Date**: 2026-02-01
**Sources**:
- https://raw.githubusercontent.com/glittercowboy/get-shit-done/main/agents/gsd-codebase-mapper.md
- https://raw.githubusercontent.com/glittercowboy/get-shit-done/main/agents/gsd-project-researcher.md
- https://raw.githubusercontent.com/glittercowboy/get-shit-done/main/agents/gsd-research-synthesizer.md
- https://raw.githubusercontent.com/glittercowboy/get-shit-done/main/agents/gsd-plan-checker.md
**Status**: IN_PROGRESS (Phase 1 Complete)

---

## Source Analysis

### Source 1: gsd-codebase-mapper.md

**Purpose**: Explores codebase for a specific focus area (tech, arch, quality, concerns) and writes structured analysis documents directly to `.planning/codebase/`.

**Key Patterns**:
- Focus-area driven exploration (tech, arch, quality, concerns)
- Template-based document generation
- Direct artifact writing (no handoff to orchestrator)
- Always includes file paths in findings
- Prescriptive guidance (HOW, not just WHAT)

**Artifacts**:
- Creates: `.planning/codebase/{STACK,ARCHITECTURE,STRUCTURE,CONVENTIONS,TESTING,INTEGRATIONS,CONCERNS}.md`
- Reads: package.json, requirements.txt, pyproject.toml, source files, git history

**Workflow Stage**: Discovery/Planning

**Local Candidates**:
| Local File | Similarity Reason | Priority |
|------------|-------------------|----------|
| `plugins/python3-development/agents/codebase-analyzer.md` | Nearly identical purpose - writes to `plan/codebase/` | **High** |
| `plugins/python3-development/agents/context-gathering.md` | Task-specific context, narrower scope | Low |

---

### Source 2: gsd-project-researcher.md

**Purpose**: Researches domain ecosystems before roadmap creation. Produces comprehensive research files (SUMMARY, STACK, FEATURES, ARCHITECTURE, PITFALLS) in `.planning/research/`.

**Key Patterns**:
- Three research modes: Ecosystem, Feasibility, Comparison
- Tool hierarchy: Context7 → Official docs → WebSearch → Verification
- Confidence levels (HIGH/MEDIUM/LOW) with source attribution
- Treats training data as hypothesis requiring verification

**Artifacts**:
- Creates: `.planning/research/{SUMMARY,STACK,FEATURES,ARCHITECTURE,PITFALLS}.md`
- Reads: PROJECT.md, Context7, WebFetch, WebSearch

**Workflow Stage**: Discovery (pre-Planning)

**Local Candidates**:
| Local File | Similarity Reason | Priority |
|------------|-------------------|----------|
| `plugins/plugin-creator/skills/feature-discovery/SKILL.md` | Autonomous research producing artifacts, identifies gaps | **High** |
| `.claude/skills/research-and-compare/SKILL.md` | Verification protocol, confidence levels | **High** |
| `plugins/python3-development/agents/feature-researcher.md` | Researches before implementation, surfaces questions | Medium |

---

### Source 3: gsd-research-synthesizer.md

**Purpose**: Synthesizes outputs from 4 parallel researcher agents into unified SUMMARY.md. Convergence point after parallel discovery research.

**Key Patterns**:
- Multi-source synthesis (reads 4 research files)
- Executive summary creation
- Pattern identification across domains
- Roadmap implications derivation
- Atomic commit of all research outputs

**Artifacts**:
- Creates: `.planning/research/SUMMARY.md`
- Reads: `.planning/research/{STACK,FEATURES,ARCHITECTURE,PITFALLS}.md`

**Workflow Stage**: Planning/Synthesis

**Local Candidates**:
| Local File | Similarity Reason | Priority |
|------------|-------------------|----------|
| `plugins/python3-development/agents/codebase-analyzer.md` | Writes analysis docs, similar aggregation | Medium |
| `plugins/plugin-creator/agents/refactor-planner.md` | Creates comprehensive plans from analysis | Medium |
| `plugins/python3-development/agents/swarm-task-planner.md` | Transforms docs into dependency-based plans | Medium |

---

### Source 4: gsd-plan-checker.md

**Purpose**: Verifies plans will achieve phase goal before execution. Goal-backward analysis with 7 verification dimensions.

**Key Patterns**:
- Goal-backward verification (7 dimensions)
- Requirement coverage checking
- Dependency graph analysis with cycle detection
- Artifact wiring verification (key_links)
- Structured YAML issue reporting (blocker/warning/info)
- Context compliance checking

**Artifacts**:
- Reads: ROADMAP.md, CONTEXT.md, PLAN.md files
- Returns: Structured verification report (PASSED/ISSUES_FOUND)

**Workflow Stage**: Planning/Pre-Execution Verification

**Local Candidates**:
| Local File | Similarity Reason | Priority |
|------------|-------------------|----------|
| `plugins/python3-development/agents/plan-validator.md` | Goal-backward validation BEFORE execution | **High** |
| `plugins/python3-development/agents/feature-verifier.md` | Goal-backward verification, structured issues | **High** |
| `plugins/plugin-creator/agents/plugin-assessor.md` | Multi-dimension validation approach | Medium |

---

## Deduplicated Candidate Assignments

| Local File | Primary Match | Secondary Matches |
|------------|--------------|-------------------|
| `plugins/python3-development/agents/codebase-analyzer.md` | gsd-codebase-mapper | gsd-research-synthesizer |
| `plugins/plugin-creator/skills/feature-discovery/SKILL.md` | gsd-project-researcher | - |
| `plugins/python3-development/agents/feature-researcher.md` | gsd-project-researcher | - |
| `plugins/python3-development/agents/plan-validator.md` | gsd-plan-checker | - |
| `plugins/python3-development/agents/feature-verifier.md` | gsd-plan-checker | - |

---

## Phase 2: Enhancement Plan

**Files to enhance** (High priority only):
1. `codebase-analyzer.md` ← patterns from gsd-codebase-mapper
2. `feature-discovery/SKILL.md` ← patterns from gsd-project-researcher
3. `feature-researcher.md` ← patterns from gsd-project-researcher
4. `plan-validator.md` ← patterns from gsd-plan-checker
5. `feature-verifier.md` ← patterns from gsd-plan-checker

**Cross-cutting enhancement**:
- Add GSD artifact recognition to context-gathering agents for interoperability

---

## Results

**Files Modified**:
| File | Enhancements Applied | Source |
|------|---------------------|--------|
| `plugins/python3-development/agents/codebase-analyzer.md` | Added "concerns" focus area, CONCERNS.md template, prescriptive guidance section, Python-specific issue detection patterns | gsd-codebase-mapper |
| `plugins/python3-development/agents/plan-validator.md` | Added 7→8 verification dimensions (artifact wiring, scope sanity), cycle detection algorithm, structured YAML issue reporting with severity levels | gsd-plan-checker |
| `plugins/python3-development/agents/context-gathering.md` | Added GSD/BMAD artifact recognition for interoperability | gsd-codebase-mapper (cross-cutting) |
| `.claude/skills/external-pattern-integrator/SKILL.md` | Fixed description to remove colons | (linting fix) |

**Deferred Enhancements** (didn't fit current files):
| Enhancement | Reason Deferred | Suggested Location |
|-------------|-----------------|-------------------|
| Research modes (Ecosystem/Feasibility/Comparison) | feature-researcher is task-scoped, not ecosystem-scoped | New dedicated ecosystem-researcher agent |
| Multi-source synthesis pattern | No direct equivalent in current workflow | Could enhance swarm-task-planner |
| Context compliance checking (Decisions/Discretion/Deferred) | GSD-specific artifact format | Adapt if adopting GSD CONTEXT.md format |

**Status**: COMPLETE
