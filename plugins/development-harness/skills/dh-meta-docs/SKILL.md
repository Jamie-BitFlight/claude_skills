---
name: dh-meta-docs
description: Development harness plugin documentation index. Use when looking up SAM pipeline, backlog lifecycle, SDLC layers, task file format, plan artifacts, quality gates, or dispatch schema documentation.
user-invocable: false
---

# Development Harness Documentation

<sam_cli>
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
</sam_cli>

Available documentation:

!`find ${CLAUDE_PLUGIN_ROOT}/docs -name '*.md' -type f | sort`

Read any file above to learn about that topic. CLI examples in those docs use bare
grouped commands (e.g. `plan list`, `backlog groom`) — prefix them with the
`<sam_cli>` value above.
