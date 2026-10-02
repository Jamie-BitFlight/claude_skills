# Utilization Proposals: GitDiagram

**Research entry**: ./research/mcp-ecosystem/gitdiagram.md
**Generated**: 2026-10-02
**Integration surfaces found**: 1 (MCP server)
**Proposals written**: 1
**Skipped**: 2 — ecosystem-research and discovery have different problem domains (ecosystem patterns and feature discovery vs. repository architecture visualization)

---

## Utilization 1: research-curator analysis agents → GitDiagram MCP

**Research entry**: ./research/mcp-ecosystem/gitdiagram.md
**Caller**: `.claude/agents/research-insight-extractor.md` (spawned by `.claude/skills/research-curator/SKILL.md`)
**Integration mechanism**: MCP server call via `get_repository_diagram` tool
**Replaces or adds**: Adds visual architecture documentation to research entries
**Setup cost**: Low (add MCP server to `.mcp.json` and call from analysis agents)
**Integration surface**: MCP server at `https://gitdiagram.com/mcp` with three tools: `get_repository_diagram`, `find_repository_diagrams`, `get_explainer_video`

### Why this caller

**Current behavior**: When research-curator documents an external GitHub repository (lines 1–200 of `/home/user/claude_skills/.claude/agents/research-curator.md`), it clones the repo shallowly to `.worktrees/` and reads source files, README, and metadata via GitHub API. The spawned analysis agents (research-insight-extractor, research-utilization-assessor, research-cross-referencer) extract patterns, improvements, and cross-references from the collected metadata and source code. However, no agent currently generates or includes visual architecture diagrams of the repository structure in the research output.

**Gap identified**: Research entries document external tools, libraries, and frameworks but lack visual context about how these systems are architected internally. When extracting insights or understanding ecosystem patterns, having an AI-generated architecture diagram would provide visual grounding for readers (both humans and agents) about:
- Component relationships and modularity
- Core modules and their dependencies
- How different parts of the system connect

Research entry `/home/user/claude_skills/research/mcp-ecosystem/gitdiagram.md` (lines 232–238) explicitly states: "claude_skills could integrate GitDiagram's MCP server directly as a built-in connector, enabling agents to analyze external repositories without fetching them locally. This would provide codebase context for tasks like **cross-repository analysis or pattern research**." This is exactly what research-curator does—it analyzes external repositories to extract patterns and insights.

**Integration opportunity**: The research-insight-extractor agent could call GitDiagram's MCP `get_repository_diagram` tool (documented in `/home/user/claude_skills/research/mcp-ecosystem/gitdiagram.md`, lines 118–126) with the external repository owner/repo pair, retrieve the generated Mermaid diagram plus component explanations, and embed these in the improvement proposals and insights written to `./research/insights/{date}-{name}-improvements.md`. This adds a new capability—visual architecture documentation—without replacing any existing functionality.

### Integration sketch

**Location**: `.claude/agents/research-insight-extractor.md` (after reading the research entry, within the pattern extraction phase)

```python
# Pseudocode for integration point
import mcp_client


def analyze_with_architecture(repo_owner: str, repo_name: str, research_entry_path: str):
    # Read research entry
    entry_content = read_file(research_entry_path)

    # Extract repository URL from entry
    github_url = extract_github_url(entry_content)
    owner, repo = parse_repo_url(github_url)  # e.g., "ahmedkhaleel2004/gitdiagram"

    # Call GitDiagram MCP tool
    diagram_response = mcp_client.call(
        server_url="https://gitdiagram.com/mcp", tool="get_repository_diagram", args={"owner": owner, "repo": repo}
    )

    # diagram_response contains:
    # - explanation: AI-generated architecture narrative
    # - components: list of components with paths
    # - connections: relationships between components
    # - mermaid_source: raw Mermaid diagram code
    # - links: GitHub links to source files

    # Embed in improvement proposal
    improvement_proposal = {
        "architecture_context": {
            "diagram_explanation": diagram_response["explanation"],
            "mermaid": diagram_response["mermaid_source"],
        },
        "patterns_observed": extract_patterns(entry_content),
        "improvements": [...],  # existing logic
    }

    return improvement_proposal
```

**Setup steps**:
1. Add GitDiagram MCP server to `.mcp.json`:

   ```json
   {
     "mcpServers": {
       "gitdiagram": {
         "command": "node",
         "args": ["./scripts/npx-run.cjs", "-y", "gitdiagram-mcp"],
         "env": {}
       }
     }
   }
   ```

   (Installation per research entry lines 158–174: `claude mcp add --transport http gitdiagram https://gitdiagram.com/mcp`)

2. Modify research-insight-extractor agent to:
   - Extract repository owner/name from research entry
   - Call GitDiagram via MCP (documented in research entry lines 118–126)
   - Embed diagram explanation and Mermaid source in output insights

3. No authentication required (public MCP server per research entry lines 52–54)

**Rate limiting note**: Research entry line 128 documents rate limiting at 120 requests/hour per network. For batch research-curator runs processing multiple repositories, this is sufficient (typical research-curator processes ~5 repos per wave per research-curator skill line 153).

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| ecosystem-research (plugins/development-harness/skills/ecosystem-research/SKILL.md) | Focuses on GitHub issues/discussions analysis and community patterns (per step summaries in indexed results), not repository architecture visualization. Research entry's MCP tools (`get_repository_diagram`) are for internal code structure, not ecosystem patterns. No integration point. |
| discovery (plugins/development-harness/skills/discovery/SKILL.md) | Part of SAM Stage 1 feature discovery workflow; focuses on identifying problem domains and gathering requirements, not analyzing external repository architecture. GitDiagram provides architecture context, but discovery's workflow stage is upstream of implementation phases where architecture matters. No integration point. |

