# URL Fetch Specification

## SOURCE: URL Extraction

The upstream drift agent (`plugin-creator:skill-content-updater` in read role) extracts URLs from skill content matching these patterns:

```text
SOURCE: <url> (accessed YYYY-MM-DD)
SOURCE: [Title](url) (accessed YYYY-MM-DD)
SOURCE: url
```

Extract the URL portion (not the surrounding text) for fetching.

## Fetch Behavior

| HTTP Status | Verdict | Action |
|---|---|---|
| 200 | Assess content (see below) | Compare fetched content against skill claim |
| 301/302 | Follow redirect, then assess | Use final response status |
| 404 | UNVERIFIABLE | Preserve current text; note dead URL in report |
| 403/401 | UNVERIFIABLE | Preserve current text; note access denied |
| Timeout (>10s) | UNVERIFIABLE | Preserve current text; note timeout |
| DNS failure | UNVERIFIABLE | Preserve current text; note DNS failure |

**Key rule**: Non-200 responses never block the pipeline. Mark the claim UNVERIFIABLE and continue.

## Content Comparison (200 responses)

1. Locate the section in the fetched page that addresses the same topic as the skill claim
2. Compare semantically — not character-for-character
3. Skill claim matches upstream intent: `VERIFIED`
4. Upstream text supersedes or contradicts skill claim: `STALE` — quote the upstream text in the report
5. Upstream contains new relevant material not in the skill: `NEW` — quote the new text in the report

## Access Date Updates

When including a VERIFIED or STALE claim in the change plan: update the access date in the SOURCE: line to the current date.
