# Memory Index

- [DH MCP-vs-CLI Documentation Structure](dh-mcp-cli-docs.md) — canonical CLI-mapping source, which
  dh docs already pair MCP-reference sections with a dedicated CLI section, and the drift patterns
  found there (stale tool names, overstated parity, extraction-rule blind spots).
- [Unenforced map guarantee](unenforced-map-guarantee.md) — backlog_view map mode's "under 2,000
  tokens" claim is not enforced by disclosure_handler.py; other locations asserting the same false
  bound; tracking issue #3059.
- [skilllint token threshold](skilllint-token-threshold.md) — prek passing does not mean
  skilllint's 4400-token SKILL.md ceiling still passes; re-run skilllint directly after edits.
