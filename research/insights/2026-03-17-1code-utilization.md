---
title: "Utilization Proposals: 1Code"
---

## Utilization 1: `.github/workflows/code-quality.yml` → 1Code REST API

**Research entry**: ./research/coding-agents/1code.md
**Caller**: .github/workflows/code-quality.yml
**Integration mechanism**: API call (curl in GitHub Actions step)
**Replaces or adds**: Adds a new capability — automated remediation dispatch on CI failure. No existing step in the workflow triggers an agent when quality checks regress.
**Setup cost**: Medium (API key stored as GitHub Actions secret + auth header)
**Integration surface**: `POST https://1code.dev/api/v1/tasks` with `Authorization: Bearer YOUR_API_KEY`, JSON body `{"repository": "<repo-url>", "prompt": "<fix-description>"}`

### Why this caller

The `code-quality.yml` workflow runs lint, type-check, plugin validation, manifest sync, and test jobs aggregated under a `quality-gate` job using `re-actors/alls-green`. When the gate fails there is no remediation step — a developer must manually investigate, fix, and re-push. The 1Code REST API accepts a repository URL and a natural-language prompt, runs an agent in an isolated cloud sandbox, commits changes, pushes a branch, and opens a PR automatically. A new job added to `code-quality.yml` that fires on `quality-gate` failure could POST to the API with the failing job names extracted from the `needs` context as the prompt, producing a fix PR without manual intervention. This adds a capability the workflow currently lacks entirely and is directly grounded in the research entry's documented automation use case: "complementing the SAM workflow defined in this repository" when triggered by CI failures (./research/coding-agents/1code.md, Integration Opportunities section).

### Integration sketch

The research entry documents the exact API call pattern (README.md API section, accessed 2026-03-17):

```yaml
# Add to .github/workflows/code-quality.yml, after the quality-gate job
auto-remediate-on-failure:
  name: Auto-remediate CI failure
  if: failure() && needs.quality-gate.result == 'failure'
  needs: [quality-gate]
  runs-on: ubuntu-latest
  permissions:
    contents: read
  steps:
    - name: Dispatch 1Code remediation agent
      env:
        ONE_CODE_API_KEY: ${{ secrets.ONE_CODE_API_KEY }}
        REPO_URL: ${{ github.server_url }}/${{ github.repository }}
      run: |
        curl -X POST https://1code.dev/api/v1/tasks \
          -H "Authorization: Bearer $ONE_CODE_API_KEY" \
          -H "Content-Type: application/json" \
          -d "{
            \"repository\": \"$REPO_URL\",
            \"prompt\": \"CI quality gate failed on branch ${{ github.ref_name }}. Fix the failing checks. Failing jobs context: ${{ toJSON(needs) }}\"
          }"
```

Constraints from the research entry that apply here:

- The call is fire-and-forget; the agent result is delivered as a GitHub PR, not as a synchronous response. The workflow step does not need to poll.
- Requires a Pro or Max subscription at `1code.dev/pro` for cloud sandbox execution (research entry, Background Agents section).
- API key must be stored as a GitHub Actions secret (`ONE_CODE_API_KEY`). The research entry documents Bearer token authentication; no OAuth flow is needed for CI use.
- The `toJSON(needs)` context injection is a GitHub Actions native pattern and is not documented in the research entry — that specific expansion should be verified against GitHub Actions docs before implementation.
