# Utilization Assessment: OpenSpace

**Research entry**: ./research/ai-research-tools/OpenSpace.md
**Assessment date**: 2026-03-28
**Status**: No utilization surface

---

## Integration Surfaces Identified

OpenSpace documents multiple callable integration mechanisms:

| Surface Type | Entry Point | Integration Method |
|---|---|---|
| **MCP Server** | `openspace-mcp` command | Expose 4 tools: `execute_task`, `search_skills`, `fix_skill`, `upload_skill` |
| **Python SDK** | `from openspace import OpenSpace` | Async context manager; `execute_task()` method |
| **CLI** | `openspace` (interactive, batch), `openspace-download-skill`, `openspace-upload-skill`, `openspace-dashboard` | Subprocess invocation |
| **pip package** | `pip install -e .` or `openspace @ git+https://...` | Dependency in pyproject.toml |

**Specific APIs documented**:
- `OpenSpace.execute(task_string)` returns `{"response": str, "evolved_skills": List[{name, origin}]}`
- MCP tool `execute_task` with auto-skill registration
- MCP tool `search_skills` for hybrid BM25 + embedding + LLM skill discovery
- SQLite SkillStore with version DAG, lineage tracking, and quality metrics

---

## Local Skill/Task Management Systems

This repository manages skills and agent tasks through:

1. **Skill storage**: Static Markdown files (`.claude/skills/*/SKILL.md`) versioned via git commits
2. **Task execution**: SAM (Structured Agent-Managed) workflow via `/dh:implement-feature`
3. **Skill discovery**: Manual references in delegation prompts, no registry or ranking system
4. **Quality gates**: `/dh:complete-implementation` with human touchpoints via ARL constraint analysis
5. **Skill evolution**: None — skills improve only through explicit human code review and commits

---

## Why No Utilization Surface Exists

### 1. **Incompatible Skill Lifecycle Model**

OpenSpace's core value is autonomous skill evolution:
- **FIX mode**: Repairs broken instructions in-place, producing new versions in a lineage DAG
- **DERIVED mode**: Creates specialized variants coexisting with parents
- **CAPTURED mode**: Extracts entirely novel skills from successful executions

**Local system**: Skills are static Markdown files. Version management happens via git commits with human review. There is no mechanism for:
- Generating skill variants autonomously
- Tracking lineage DAGs inside the repository
- Applying algorithmic diffs to skill instructions without human approval

**Incompatibility**: Integrating OpenSpace would require abandoning git-based skill versioning and replacing it with OpenSpace's autonomous evolution model. This conflicts with the repository's requirement that all skill changes go through `pre-commit`, code review, and explicit commits. Skills created by agents cannot be directly committed to the repository — they must be reviewed by humans first.

### 2. **No Execution Recording Layer**

OpenSpace's evolution engine depends on:
- Full execution recordings (stdout, stderr, screenshots, videos)
- Structured success/failure metrics per tool call
- Post-execution LLM analysis to suggest improvements

**Local system**: The `/dh:implement-feature` and `/dh:execution` workflows delegate tasks to agents but do not:
- Capture execution recordings
- Track tool success rates across all agent invocations
- Feed execution data into a metrics collection system
- Expose recordings to external analyzers

**Cost**: Building the recording layer would require instrumenting every agent execution, storing recordings, and exposing them to OpenSpace's `ExecutionAnalyzer`. This is a substantial architectural addition not currently in scope.

### 3. **Conflicting Quality Gate Models**

**OpenSpace's approach**: Validation gates are algorithmic. Safety checks flag dangerous patterns, and evolution is gated on quality thresholds. The process is autonomous and metric-driven.

**Local system's approach**: Quality gates use human touchpoints rooted in ARL (Attribute-Requirement Linking) constraint analysis. Decisions about whether a change is high-risk or requires review are made explicitly by orchestrators reading the `/dh:complete-implementation` gates and deciding escalation based on *unbound constraints*, *domain knowledge gaps*, *high-risk irreversible changes*, and *novel architecture decisions*.

**Incompatibility**: Merging these models would require either:
- Removing human ARL touchpoints and trusting algorithmic gates (contradicts project philosophy)
- Wrapping OpenSpace's evolution in human gates (defeats the purpose of autonomous evolution)

### 4. **Network-Scoped Collective Intelligence**

OpenSpace targets a **cloud skill community** where multiple agents contribute skills and improvements to a shared registry. Benefits emerge at network scale — "More agents → richer execution data → faster evolution for every agent."

**Local system scope**: This repository is a single plugin with agents coordinating within one codebase. Network effects do not apply. Skill sharing is manual (committing new skills to git) and happens within one project context.

**Incompatibility**: The cloud community architecture (`open-space.cloud` registry, BM25 + embedding skill discovery, skill namespace management across agents) provides no value in a single-project context. The cost of integrating cloud skill sync and community governance far outweighs the benefit.

---

## Candidate Systems Assessment

### `/dh:implement-feature`

**Scope**: Executes tasks from SAM task files via agent delegation loop.

**Opportunity to integrate?** No.

**Reason**: OpenSpace's value is post-execution skill improvement. For OpenSpace to add value, `/dh:implement-feature` would need to:
1. Record every agent execution with full I/O, screenshots, and metrics
2. Run ExecutionAnalyzer on each execution recording
3. Accept OpenSpace's autonomous skill modifications
4. Commit evolved skills back to the repository without human review

Steps 1-2 add significant overhead. Step 3 contradicts the repository's commit discipline. Step 4 violates code review requirements. None of these are acceptable changes.

### `/dh:add-new-feature`

**Scope**: Plans features through discovery → analysis → architecture → task decomposition.

**Opportunity to integrate?** No.

**Reason**: OpenSpace's `/skill-discovery` and `/delegate-task` host skills teach agents when to search for and use existing skills. The local system already has `/skill-research-process` that orchestrates parallel research agents to build skills *from official documentation*. OpenSpace's skill discovery solves a different problem — finding and ranking already-evolved skills based on execution history.

The local system doesn't have execution history (no recordings), so hybrid BM25 + embedding + LLM ranking has no signal to work from. Manual delegation based on task description is already sufficient.

### `@dh:swarm-task-planner`

**Scope**: Decomposes features into parallel task streams with dependencies and acceptance criteria.

**Opportunity to integrate?** No.

**Reason**: OpenSpace's skill evolution is *post-execution feedback*. The task planner runs *before* execution. There is no execution data to feed OpenSpace's evolution engine at planning time. The two systems operate at different lifecycle stages with no overlap.

### `@dh:feature-verifier`

**Scope**: Verifies whether implemented features meet acceptance criteria.

**Opportunity to integrate?** No.

**Reason**: Feature verification runs post-implementation to check acceptance criteria. It does not suggest improvements to the skills or agents used during implementation. OpenSpace's post-execution analysis is designed to suggest skill improvements. Feature verification's concern is whether the *feature* works, not whether the *agents' skills* improved.

The data produced by feature verification (did ACs pass? yes/no) is not rich enough to drive OpenSpace's algorithmic skill evolution. Evolution requires execution recordings with detailed tool call metrics, error patterns, and latency data.

---

## Summary

**OpenSpace is well-integrated as a callable service** (MCP server, Python SDK, CLI, pip package). However, **the architectural models are incompatible**:

- OpenSpace assumes autonomous skill evolution; this repo enforces human code review
- OpenSpace requires execution recording layer; repo has no recording infrastructure
- OpenSpace targets cloud communities; repo operates locally within one project
- OpenSpace's quality gates are algorithmic; repo's gates use human ARL touchpoints

**A proposal to integrate OpenSpace would require:**

1. Building execution recording and metrics collection across all agent invocations
2. Restructuring skill versioning from git commits to OpenSpace's lineage DAG model
3. Removing human code review gates or wrapping algorithmic evolution in manual approval
4. Adding cloud sync, community governance, and skill namespace management

**These changes are disproportionate to the value gained** because:
- The local system benefits from autonomous skill improvement primarily at network scale (multiple agents)
- Single-project contexts see diminishing returns from evolution if execution data is sparse
- Manual skill creation via research agents and human-reviewed commits aligns better with the repository's quality and auditability requirements

**Recommendation**: Monitor OpenSpace's evolution as a reference architecture for future multi-agent systems. Do not integrate into this single-project development harness at this time.

---

## References

- OpenSpace repository: <https://github.com/HKUDS/OpenSpace> (accessed 2026-03-28)
- OpenSpace MCP server integration: Research entry lines 97-103
- SAM workflow documentation: `plugins/development-harness/CLAUDE.md`
- Skill lifecycle model: `plugins/development-harness/skills/add-new-feature/SKILL.md`
- Execution system: `plugins/development-harness/skills/implementation-manager/SKILL.md`
