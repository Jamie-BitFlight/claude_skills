# CUA Utilization Assessment
**Date:** 2026-05-03
**Subject:** Computer-Use Agents (CUA) Integration Opportunities for Claude Skills Repository

---

## STATUS: has_utilization_surface

CUA presents **4 direct integration surfaces** for this codebase. The platform is feature-complete, actively maintained (476 releases, last update May 2, 2026), and provides infrastructure that complements the agent-centric architecture already present in claude_skills.

---

## Executive Summary

| Dimension | Assessment |
|-----------|-----------|
| **Direct applicability** | High — CUA solves autonomous screen interaction, which agents spawned via `/dh:kage-bunshin` cannot currently perform |
| **Integration complexity** | Low — Python SDK (`pip install cua`) + minimal scaffolding required |
| **Dependency risk** | Moderate — CUA is active/maintained but adds runtime dependency on Docker/VM infrastructure |
| **Effort to integrate** | Medium — 1-2 skills + MCP server bridge + documentation |

---

## Utilization Surface Analysis

### 1. Agent-Centric Testing & Validation (Primary Surface)

**Problem:** Current `/dh:kage-bunshin` agents execute via subprocess (bounded to CLI/programmatic access). Cannot interact with GUI applications, web UIs, or graphical tools.

**CUA Capability:** Desktop automation via sandboxed agent execution with screen capture and GUI element interaction.

**Integration Proposal:**
- **Skill:** `/dh:agent-gui-validator` — Spawn CUA sandbox, inject kage-bunshin agents into visual environment, run acceptance tests against graphical UIs (e.g., Electron apps, web dashboards).
- **Use case:** Validate agent behavior in real GUI contexts (e.g., test if `/python-engineering:python3-cli` CLI outputs render correctly in terminal UI frameworks like Textual).
- **Artifact:** `.tmp/scratch/gui-validation-report.md` — screenshot trajectories, interaction sequences, validation results.

**Implementation scope:**
1. MCP server wrapping CUA Sandbox Python API
2. Skill boilerplate calling the MCP server
3. Agent prompt tailoring GUI validation logic
4. Documentation of CUA environment setup

---

### 2. Cross-Platform Agent Benchmarking (Secondary Surface)

**Problem:** Agent performance is measured on CLI tasks only. No standardized framework for measuring agent capability across different environments or task types.

**CUA Capability:** Integrated benchmarking with OSWorld, ScreenSpot, and Windows Arena datasets. Trajectory export for analysis.

**Integration Proposal:**
- **Artifact:** `./research/benchmarks/cua-agent-benchmarks/` directory
  - `benchmark-harness.py` — Python script integrating CUA's evaluation framework with SAM task execution
  - `results/` — Trajectory exports and performance metrics per agent type
  - `METHODOLOGY.md` — Benchmark protocol documentation
- **Use case:** Measure agent quality across interaction modalities (CLI, GUI, web). Compare agent architectures objectively.
- **SAM integration:** Add benchmark results as part of `/dh:complete-implementation` quality gates.

**Implementation scope:**
1. Script to initialize CUA-Bench environment
2. SAM task extension to capture benchmark runs
3. Dashboard or report aggregator for trajectory analysis

---

### 3. Skill Coverage for Desktop Automation Tasks (Tertiary Surface)

**Problem:** No mechanism for agents to interact with desktop applications directly. Workflow automation tasks (e.g., "extract data from proprietary software", "automate UI workflows") cannot be automated by agents.

**CUA Capability:** Non-disruptive background automation on macOS (Cua Driver), seamless VM/container execution on Linux/Windows/Android.

**Integration Proposal:**
- **Skill:** `/dh:desktop-task-executor` — High-level interface for delegating screen interaction tasks to CUA agents
- **Use case:** "Automate opening a PDF, extracting table data, and formatting it" — agent operates GUI, extracts content, returns structured data
- **Artifact:** `.tmp/scratch/desktop-automation-log/` — screen recordings, action sequences, extracted data

**Implementation scope:**
1. Wrapper skill simplifying CUA API
2. Example tasks (PDF extraction, web scraping via GUI)
3. Integration with SAM for long-running automation workflows

---

### 4. Research Infrastructure for Agent Perception & Reasoning (Exploratory Surface)

**Problem:** Agent reasoning about visual information is not benchmarked. Vision-language models used by agents are evaluated in isolation, not in end-to-end task contexts.

**CUA Capability:** Real-world visual perception via screen capture. Integration with visual grounding datasets (ScreenSpot, OmniParser).

**Integration Proposal:**
- **Research artifact:** `./research/agent-infrastructure/cua-vision-integration.md`
  - Document vision model selection for agent perception
  - Benchmark agent reasoning on visual reasoning tasks (e.g., "locate the submit button in this screenshot")
  - Integrate CUA's ScreenSpot dataset for evaluating agent visual grounding
- **Use case:** Improve agent quality by measuring and optimizing visual reasoning capability

**Implementation scope:**
1. Research documentation linking CUA perception to agent architecture
2. Benchmark script using ScreenSpot dataset
3. Visualization dashboard for perception performance

---

## Integration Dependency Tree

```
CUA Core (pip install cua)
├─ Python 3.11+
├─ Docker or VM runtime (QEMU/KVM/VirtualBox/Parallels)
└─ ~500MB+ disk space for sandbox images

MCP Server (proposed: `scripts/run_cua_server.py`)
├─ Depends: CUA Core
└─ Exposes: tools for sandbox creation, screen capture, interaction, trajectory export

Skills (proposed)
├─ `/dh:agent-gui-validator` — requires MCP server + CUA Core
├─ `/dh:desktop-task-executor` — requires MCP server + CUA Core
└─ Documentation files — no runtime dependency

SAM Integration (proposed)
├─ Quality gates calling agent-gui-validator
├─ Benchmark tasks running via desktop-task-executor
└─ Trajectory capture as implementation artifact
```

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| **Runtime environment:** CUA requires Docker/VM | Document setup; provide install script; mark as optional dependency in pyproject.toml |
| **Learning curve:** CUA API is new to codebase | Write comprehensive MCP server wrapping; provide example tasks; link to CUA docs |
| **Maintenance burden:** CUA is external project | Pin version in pyproject.toml; monitor GitHub releases; use Dependabot |
| **Scope creep:** Desktop automation is orthogonal to core skills | Isolate in `/dh:desktop-task-executor` skill; keep core skills CLI-centric |

---

## Recommendations

### Phase 1 (Immediate): Infrastructure
1. Add `cua` to `pyproject.toml` as optional dependency (`extras = ["desktop"]`)
2. Create `plugins/development-harness/scripts/run_cua_server.py` — MCP server wrapping CUA Sandbox
3. Write `./research/agent-infrastructure/cua-integration-guide.md` — setup and API reference

### Phase 2 (Short-term): Validation Skill
1. Create `/dh:agent-gui-validator` skill
2. Document GUI validation use cases
3. Add example task (e.g., validate Textual CLI renders correctly in CUA environment)

### Phase 3 (Medium-term): Benchmarking
1. Create `./research/benchmarks/cua-agent-benchmarks/` directory
2. Integrate OSWorld or ScreenSpot dataset
3. Run baseline benchmarks on existing agents

### Phase 4 (Long-term): Vision Research
1. Analyze agent perception performance on visual tasks
2. Document findings in research/ directory
3. Propose improvements to vision-language model selection

---

## Success Criteria

- [ ] CUA installed and verified in development environment (`uv run cua --version` succeeds)
- [ ] MCP server created and tested (`uv run scripts/run_cua_server.py list` returns available tools)
- [ ] At least one skill (agent-gui-validator) created and documented
- [ ] Integration guide written with setup instructions
- [ ] Zero breaking changes to existing plugins/skills
- [ ] Benchmark results collected for at least one agent type

---

## Alignment with Project Directives

**Directive: "Boil the ocean"** — CUA provides a new domain (visual interaction) for agent capability. Integrating it unlocks autonomous behavior in GUI environments, expanding the scope of tasks agents can complete.

**Directive: "No invented limits"** — Desktop automation is currently unavailable to agents. Adding CUA removes an architectural limitation.

**Directive: "Search before building"** — CUA solves the desktop automation problem at scale. No need to build a custom solution.

---

## References

- **CUA Repository:** <https://github.com/trycua/cua>
- **CUA Documentation:** <https://cua.ai/docs>
- **Python SDK:** <https://pypi.org/project/cua/>
- **Benchmarks:** OSWorld, ScreenSpot, Windows Arena (integrated in CUA)
- **Research entry:** `/home/user/claude_skills/research/agent-infrastructure/cua.md`

---

## Author Notes

CUA is a **strategic dependency**, not a tactical fix. It solves a class of problems (visual interaction automation) that the current codebase cannot address. Integration is low-risk because:

1. It's optional (desktop skills are orthogonal to CLI skills)
2. It's mature (476 releases, active maintenance)
3. It's compatible (Python SDK fits naturally into uv workspace)

The utilization surface is **real and substantial**. Recommend proceeding with Phase 1 infrastructure immediately.
