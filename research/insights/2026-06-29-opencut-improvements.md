# Improvement Proposals: OpenCut

**Research entry**: ./research/coding-agents/opencut.md
**Generated**: 2026-06-29
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered, incompatible, or not yet implemented)**: 5

---

## Summary

The research entry's "Relevance to Claude Code Development" section is populated with five
patterns, but none clears the actionability bar defined in the gap assessment rules. The decisive
factor is the entry's own "Limitations and Caveats" section: OpenCut is a video editor undergoing a
ground-up rewrite, and every feature cited as relevant (Editor API, plugin system, MCP server, Rust
core, headless mode, scripting tab) is explicitly recorded as **announced but not yet implemented,
documented, or visible in the repository**. There is no concrete external mechanism to map against a
local system.

The Relevance items are aspirational analogies ("OpenCut's *plan* to...", "OpenCut's *announced*
design..."), not observed mechanisms. The single item grounded in an actually-observed practice
(TypeScript + Zod runtime validation at boundaries) is architecturally incompatible with this
repo's plugin contracts (Python PEP 723 scripts + markdown skills/agents, not TypeScript), and the
underlying intent — comprehensive error handling, no swallowed exceptions — is already covered by
existing repo rules.

No backlog items are created. Each pattern's disposition is recorded below.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| 1. Plugin-First Architecture | No concrete mechanism exists to extract. Entry Limitation 3: "no public plugin API documentation, plugin development guide, or plugin examples are currently available. The plugin registration mechanism and extension points are not yet exposed." A gap requires an observable external mechanism to map against the local plugin system — there is none. Fails gap rule 1 (concrete mechanism) and 3 (observable). |
| 2. MCP Server as Integration Layer | Not implemented. Entry Limitation 7: "the MCP server for AI agents is listed as a coming feature but no implementation, schema, or usage guide is currently available." Nothing to compare against `.claude/skills/fastmcp-creator/` or local MCP servers. Fails gap rules 1 and 3. |
| 3. Cross-Platform Monorepo via Rust Core | Not observable. Entry Limitation 5: "the Rust implementation is not visible in this repository; it may be in a separate private or unreleased repository." Also architecturally incompatible — this repo is a Claude Code plugin marketplace (Python + markdown), not a cross-platform application runtime. Fails gap rules 1, 3, and the architecture-incompatibility exclusion. |
| 4. Type-Safe Plugin Contract (TypeScript + Zod) | Architecturally incompatible and already covered. This repo's plugin/skill/hook contracts are Python (PEP 723 scripts) and markdown — not TypeScript/Zod (see `.claude/rules/python-development.md`). The underlying intent (boundary validation, comprehensive error handling, no swallowed exceptions) is already enforced locally by `.claude/rules/silent-failure-prevention.md` and `.claude/rules/exception-handling.md`. Fails gap rule 2 (local system already implements equivalent) and the architecture-incompatibility exclusion. |
| 5. Headless Mode and Scripting | Not implemented. Entry Limitation 1 lists "headless mode, scripting tab" among features that "are planned but not yet fully implemented or documented." No mechanism to study. Fails gap rules 1 and 3. |

---

## Deferred Proposals (confidence too low to backlog)

None. No pattern reached even medium confidence — each was eliminated at the actionability gate by
the entry's own statement that the relevant feature is unimplemented, undocumented, not visible, or
architecturally incompatible with this repo.
