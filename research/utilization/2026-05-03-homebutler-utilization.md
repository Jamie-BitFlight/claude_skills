# HomeButler Utilization Assessment

**Assessment Date**: 2026-05-03
**Source**: ./research/mcp-ecosystem/homebutler.md (v0.18.1)
**Assessed By**: Claude Code Agent

---

## Status

**UTILIZATION SURFACE**: `has_utilization_surface`

HomeButler presents **direct integration opportunities** as an MCP server dependency and as a reference pattern for skill design.

---

## Direct Integration Opportunities

### 1. MCP Server Dependency for Infrastructure Agents

**Proposal**: Bundle HomeButler as an optional MCP server within the development-harness plugin, enabling infrastructure-aware agent workflows.

**Details**:
- HomeButler is already a production-grade MCP server (implements Model Context Protocol spec)
- Provides operational context that agents can query: running containers, services, port mappings, systemd state
- Zero configuration required—installable via npm, Homebrew, or script
- MIT licensed, active maintenance (last updated 2026-05-03)

**Integration Points**:
- `.claude-plugin/plugin.json` — add homebutler as an optional MCP server with conditional installation check
- MCP server configuration — detect if homebutler is installed; if yes, expose tools to agents
- Documentation — link from development-harness skill references for agents requiring infrastructure visibility

**Use Cases**:
- Deployment validation agents that need to confirm running services match expected state
- Infrastructure monitoring agents that query container and systemd status
- Diagnostic workflows for troubleshooting resource allocation and port conflicts
- Chatops patterns where Claude agents restart services or inspect logs without SSH

**Implementation Scope**: Low
- HomeButler provides a stable, complete implementation
- No wrapper code required—use MCP config to expose tools directly
- Conditional check: if homebutler not installed, agents degrade gracefully (optional tools unavailable)

---

### 2. Single-Binary Distribution Pattern for Skills

**Proposal**: Adopt HomeButler's single-binary distribution pattern as a reference for future skill/agent tools that require system-level access (process introspection, port monitoring, file system operations).

**Details**:
- HomeButler demonstrates how to ship zero-dependency CLI tools via goreleaser
- Pattern enables installation across platforms (Linux, macOS, Raspberry Pi) from a single release
- Applies to skills that wrap external tools (e.g., diagnostics, infrastructure queries, system state inspection)

**Reference Points**:
- Build system: goreleaser configuration in HomeButler repo
- Installation methods: npm, Homebrew, direct script installation
- CLI design: root command with subcommands (e.g., `homebutler containers`, `homebutler services`, `homebutler logs`)

**When to Apply**:
- Skill wraps a system-level tool (diagnostics, process inspection, network queries)
- Tool should work across multiple platforms without a daemon or database
- Installation experience must be trivial for end-users

**Implementation Scope**: Reference only—no changes to current codebase

---

### 3. CLI-to-Protocol Extension Pattern

**Proposal**: Reference HomeButler's design (CLI-first with MCP protocol extension) as a pattern for skills that expose both direct CLI usage and AI tool integration.

**Details**:
- HomeButler provides identical functionality through both CLI and MCP
- Enables users to interact directly (`homebutler containers`) and via AI agents (`call homebutler.tools.containers`)
- Simplifies tool design: single business logic layer, two interface layers (CLI + MCP)

**Application to Skills**:
- Skills designed with dual-interface support reduce cognitive load for users
- CLI interaction enables experimentation; MCP integration enables agent automation
- Pattern reduces redundant implementations (no separate code paths)

**Reference Implementation**:
- See HomeButler `cmd/` (CLI) and MCP server handler (protocol layer)
- Model for implementing `/plugin-creator:skill-creator` output

**Implementation Scope**: Reference for future skill architecture

---

## Indirect Utilization: Workflow Patterns

### 4. Chatops and Agent Infrastructure Interaction

**Proposal**: Document HomeButler as a reference pattern for chatops workflows in agent documentation.

**Details**:
- HomeButler enables natural language infrastructure queries through Claude
- Example workflow: "Restart the Nextcloud service" → Claude calls homebutler.services.restart() → service restarted
- Eliminates SSH complexity; reduces operational friction for non-infrastructure specialists

**Documentation Artifacts**:
- Add reference to HomeButler in `/dh:implementation-manager` agent documentation for infrastructure-aware task workflows
- Link from development-harness SKILL.md under "Operational Visibility" section

**Implementation Scope**: Documentation update only

---

## Evaluation: Can HomeButler Be Used as a Dependency vs. Reference?

| Criterion | Assessment | Implication |
|-----------|-----------|-------------|
| License | MIT | ✅ Compatible—can use as dependency |
| Stability | v0.18.1, active (2026-05-03) | ✅ Production-ready |
| Installation | npm, Homebrew, script | ✅ Low-friction user experience |
| Protocol | MCP (standard) | ✅ Integrates directly via MCP config |
| Maintenance | 135 stars, 11 forks, 4 open issues | ✅ Community-supported |
| Dependencies | Go single binary—zero runtime deps | ✅ No dependency bloat |
| Scope Alignment | Infrastructure visibility for agents | ✅ Directly relevant to agent workflows |
| Breaking Changes Risk | Low—protocol-stable, recent activity suggests maintenance | ✅ Safe to depend on |

**Conclusion**: HomeButler can be used as a **direct MCP dependency** in development-harness. No wrapper required—configuration-based integration only.

---

## Proposed Integration Steps

### Phase 1: Optional MCP Server Addition (1-2 hours)

1. **Conditional MCP Configuration** — Update `.claude-plugin/plugin.json` to optionally include homebutler
   ```json
   {
     "mcpServers": {
       "homebutler": {
         "command": "npx",
         "args": ["-y", "homebutler@latest"],
         "disabled": true
       }
     }
   }
   ```

2. **Documentation Update** — Add HomeButler reference to development-harness SKILL.md
   - Link to [HomeButler GitHub](https://github.com/Higangssh/homebutler)
   - Document use cases (deployment validation, service monitoring)
   - Provide MCP activation instructions

### Phase 2: Agent Documentation (1 hour)

1. **Update `/dh:implementation-manager` references** to mention HomeButler for infrastructure-aware workflows
2. **Add chatops pattern examples** to relevant skill documentation

### Phase 3: Reference Integration (2-4 hours)

1. **Document single-binary pattern** in `.claude/rules/` for future skill developers
2. **Add HomeButler to MCP ecosystem references** in research files

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| HomeButler breaks MCP compatibility | Low | Use MCP protocol version pinning in config |
| User's homelab lacks Docker/systemd | Low | HomeButler degrades gracefully (optional tools unavailable) |
| Installation failure | Low | Script and npm fallbacks; document troubleshooting |
| Security (MCP server executing system commands) | Medium | Document access control: HomeButler requires explicit user trust (same as SSH) |

---

## Recommendations

### DO Integrate (Immediate)
1. Add HomeButler as optional MCP server in development-harness plugin.json
2. Document in SKILL.md with use cases and activation instructions
3. No code changes required—configuration only

### DO Reference (Documentation)
1. Single-binary distribution pattern → future skill architecture reference
2. CLI-to-protocol extension pattern → skill design documentation
3. Chatops workflows → agent documentation

### DO NOT Integrate (Out of Scope)
1. Fork or modify HomeButler—stable upstream is preferred
2. Wrapper code around HomeButler—MCP config is sufficient
3. Direct dependencies in Python/Node skill code—keep as separate MCP process

---

## Summary

| Aspect | Finding |
|--------|---------|
| **Has Utilization Surface** | Yes—direct MCP integration + reference patterns |
| **Integration Complexity** | Low—configuration-based, zero code changes |
| **Risk Level** | Low—optional feature, graceful degradation |
| **Time to Integrate** | 2-3 hours (Phase 1 + Phase 2) |
| **Value Delivered** | Infrastructure visibility for agents + operational visibility patterns |
| **Maintenance Burden** | Minimal—upstream maintenance tracked via version updates |

---

## Files Affected

If Phase 1–2 integrated:
- `.claude-plugin/plugin.json` — add optional homebutler MCP server
- `plugins/development-harness/SKILL.md` — reference and use cases
- `plugins/development-harness/references/` — new reference file (optional)

---

## Cross-References

- Source: `./research/mcp-ecosystem/homebutler.md`
- Related: `./research/mcp-ecosystem/model-context-protocol.md`
- Agent: `/dh:implementation-manager`, `/dh:development-harness`
- Pattern: Single-binary distribution, CLI-to-protocol extension, chatops workflows

