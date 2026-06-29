---
title: "Improvement Proposals: mcpskills-cli"
---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| MCP Skill Generation and Integration | Incompatible with local architecture. mcpskills-cli generates static SKILL.md files from MCP server tool discovery to work around platforms that lack native MCP tool access. Claude Code has native MCP tool integration -- agents invoke MCP tools directly at runtime without needing static skill file intermediaries. The fastmcp-creator skill (`plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md`) builds MCP servers, not skill files from MCP servers. The problem mcpskills-cli solves (token pollution from loading all MCP tools) does not apply because Claude Code loads tools on demand via MCP server configuration, not by injecting all tool schemas into context. |
| Token Optimization Patterns | Already covered. The research entry's recommendation to consolidate multiple tools into a single skill to reduce token consumption is a general principle already implemented in the local repo through: (1) skilllint SK006/SK007 token-based thresholds that govern skill size, (2) `/refactor-skill` for splitting oversized skills while maintaining consolidation where appropriate, (3) existing backlog item #120 "SAM: Cost/Token Management" tracking token management concerns. No concrete mechanism gap exists -- the pattern is a general guideline, not a specific implementable mechanism absent from the local system. |
