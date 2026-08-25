The purpose and explicit goals of the skill `research-curator`:

1. `Turn any tool/library/resource URL into a structured, quote-grounded research entry under ./research/{category}/, with confidence levels attached to each claim rather than presented as flat fact`
2. `Avoid duplicate or stale research — detect existing entries by URL and route automatically into a refresh (--rerun) instead of creating a redundant entry, using freshness-tracking metadata (last verified date, version at verification)`
3. `Scale research intake via parallel batch processing (--batch, up to 5 concurrent agents per wave) without losing per-URL failure detail or overwhelming MCP rate limits`
4. `Keep the research corpus structurally valid and enforce fixable issues automatically (--validate mode: auto-fix error-severity structural problems, surface warning/info issues for human review) rather than letting entries silently drift out of schema`
5. `Convert passive research into actionable follow-through — automatically extract improvement proposals into the backlog, assess direct utilization/integration opportunities, and build a bidirectional cross-reference graph linking related entries, so a new entry doesn't sit inert`
6. `Preserve fidelity of agent-reported results end-to-end (exact counts, exact failure reasons, structured status blocks) when relaying multi-agent research results back to the user, preventing information loss/generalization across the orchestration chain`
