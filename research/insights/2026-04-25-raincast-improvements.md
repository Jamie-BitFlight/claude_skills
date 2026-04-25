# Improvement Proposals: Raincast

**Research entry**: ./research/coding-agents/raincast.md
**Generated**: 2026-04-25
**Patterns assessed**: 6
**Backlog items created**: 1 (issues: #1936)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Domain-specific skill scaffolding templates analogous to Raincast's 9 layout templates

**Source pattern**: "Nine layout templates (src/lib/generation/templates/) emit production-ready React code. Each template is a pure function: metadata → scaffold." (Relevance to Claude Code Development, section 3 — Template-Driven Code Scaffolding)
**Local system**: /home/user/claude_skills/plugins/plugin-creator/skills/skill-creator/scripts/init_skill.py
**Confidence**: High
**Impact**: Medium
**Backlog**: #1936 created

### Current state

`init_skill.py` (scripts/init_skill.py) emits a single SKILL_TEMPLATE constant with TODO placeholders regardless of the skill's intended purpose. The template is generic — every new skill produced by `init_skill.py my-skill --path X` starts from the same skeleton with bracketed `[TODO: ...]` markers and no domain-aware scaffolding. The companion reference at `references/agent-templates.md` documents archetype categories (Standard Templates, Role-Based Contract Archetypes) but provides no executable scaffold-emitting code. Authors selecting a skill type (workflow-based, task-based, reference-based, MCP-integration, doc-updater) must hand-edit the skeleton each time. There is no `templates/` directory under the skill-creator skill that maps a chosen archetype to a concrete starter file.

### Target state

`init_skill.py` accepts a `--template <name>` flag selecting from a set of starter templates stored under `plugins/plugin-creator/skills/skill-creator/templates/`. Each template is a `.md.j2` (or `.md` with `{placeholder}` substitutions) file emitting a SKILL.md tailored to a concrete skill archetype. Initial templates cover the categories already documented in `agent-templates.md`: `workflow` (sequential procedures), `task-collection` (operations menu), `reference` (standards/specifications), `mcp-integration` (FastMCP-backed tool), and `doc-updater` (auto-updating external docs wrapper). When `--template` is omitted, behavior is unchanged (emits the existing generic skeleton — backward compatible).

### Measurable signal

Run: `uv run plugins/plugin-creator/skills/skill-creator/scripts/init_skill.py example-workflow --path /tmp/test-skills --template workflow`. The emitted `/tmp/test-skills/example-workflow/SKILL.md` contains a "Workflow Decision Tree" section, numbered Step headings, and zero `[TODO: Choose the structure that best fits this skill's purpose...]` blocks. Run `ls plugins/plugin-creator/skills/skill-creator/templates/` and verify the directory contains template files for each documented archetype. Run `init_skill.py without --template` and confirm the generic SKILL_TEMPLATE output is byte-identical to the pre-change version.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Lightweight file manifests + tool-calling agent loop (Raincast agentLoop.ts) | Medium | The local SAM/`implement-feature` system already implements an iterative agent dispatch loop with task-file-based state. Raincast's specific innovation is the *plain-English file manifest* fed to the LLM before each tool decision — distinct from SAM's task YAML. To raise confidence, would need to (a) verify that no existing skill provides a "plain-English summary manifest" for code generation, (b) identify a concrete consumer in the local repo that would benefit from such a manifest (e.g., codebase-analyzer producing a summary index), and (c) define what file would receive the manifest. Until then the gap is interpretive rather than directly observable. |
| Multimodal input handling (image attachments to discovery / backlog items) | Medium | `discovery/SKILL.md` lists "screenshots, logs, expected outputs" as reference types in Step 3 but provides no mechanism to ingest image attachments — neither the backlog item creation flow (`create-backlog-item`) nor the discovery template (`# ARTIFACT:DISCOVERY`) has an "Attachments" or "Images" section. The gap is real but spans multiple files and depends on platform support (whether GitHub Issue body image links survive `backlog_view` round-trips, whether agents can fetch and analyze them). To raise confidence, would need to (a) verify whether `gh issue create --body` preserves image markdown, (b) test whether Claude's WebFetch can retrieve GitHub-hosted issue images, and (c) decide whether the gap belongs in `discovery/SKILL.md`, `create-backlog-item/SKILL.md`, or the `backlog_core` MCP server. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Proxy binary for dev/prod separation (proxyExtract.ts) | Tauri-specific build-time pattern. The repo's plugin/skill artifacts have no compiled-binary analog — skills are loaded from source on every session. The proxy concept does not map to any local system without inventing a new abstraction layer. |
| Provider-agnostic AI integration (baseProvider.ts, registry.ts) | The Claude Code plugin and MCP system already provides this abstraction at a different level (any plugin can be swapped). The research entry itself notes "Claude Code already does this with the plugin system." No actionable gap. |
| Error boundaries / graceful degradation (ErrorBoundary.tsx) | Local system already has equivalent mechanisms: hook profile fallback (`CLAUDE_SKILLS_HOOK_PROFILE=minimal` in implementation-manager/SKILL.md lines 207–209), agent BLOCKED status signaling (subagent-contract skill), and explicit exception handling rules (`.claude/rules/exception-handling.md`). The Raincast pattern is React-component-specific; no analogous file in this repo would benefit from a per-component try/catch wrapper. |

---

## Notes

The Raincast research entry is dominated by Tauri/React-specific architecture. Five of the six "Relevance to Claude Code Development" entries are plausibility statements ("Applicability: ...could be adapted") rather than concrete mechanism transfers. Only the template-scaffolding observation maps to a directly observable file in this repo (`init_skill.py`) where the absence of domain-specific templates is verifiable in a few seconds.
