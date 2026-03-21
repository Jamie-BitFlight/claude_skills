---
name: 'gitlab-skill: Remove hardcoded corporate URL'
description: '`validate_glfm.py` lines 152-153 hardcode `https://sourcery.assaabloy.net` as the default GitLab instance URL. `gitlab-ci-local-guide.md` line 51 also references this URL. This leaks a corporate internal URL into a public repository. Replace with a generic placeholder (e.g., `https://gitlab.example.com`) or make the URL a required argument with no default.'
metadata:
  topic: gitlab-skill-remove-hardcoded-corporate-url
  source: Plugin code review session 2026-02-21
  added: '2026-02-21'
  priority: P1
  type: Feature
  status: needs-grooming
  groomed: '2026-02-24'
  plan: ''
  issue: '#76'
  last_synced: '2026-03-21T03:46:54Z'
---

## Story

As a **developer**, I want **`validate_glfm** so that **backlog items are tracked in GitHub**.

## Description

`validate_glfm.py` lines 152-153 hardcode `https://sourcery.assaabloy.net` as the default GitLab instance URL. `gitlab-ci-local-guide.md` line 51 also references this URL. This leaks a corporate internal URL into a public repository. Replace with a generic placeholder (e.g., `https://gitlab.example.com`) or make the URL a required argument with no default.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Plugin code review session 2026-02-21
- **Priority**: P1
- **Added**: 2026-02-21
- **Research questions**: None

## Notes

## Groomed (2026-02-24)
### Reproducibility
**Original problem (pre-fix):**
1. Open `plugins/gitlab-skill/skills/gitlab-skill/scripts/validate_glfm.py` lines 152–153 — default `--gitlab-url` was `https://sourcery.assaabloy.net`
2. Open `plugins/gitlab-skill/skills/gitlab-skill/references/gitlab-ci-local-guide.md` line 51 — example URL referenced same corporate host
**Verification (post-fix):**
1. `rg "sourcery\.assaabloy\.net" plugins/gitlab-skill` returns no matches
2. Both locations use `https://gitlab.example.com`
### Output / Evidence
- **Commit**: 103cbf6c2d1e865bdd6afdef6e3d5912ff7bab2b — `fix(gitlab-skill): replace hardcoded corporate URL with generic placeholder`
- **Files changed**: `validate_glfm.py` (default arg + help text), `gitlab-ci-local-guide.md` (example URL), `plugin.json`, `marketplace.json`, `BACKLOG.md`
- **Fact-check**: All three claims verified (validate_glfm.py, gitlab-ci-local-guide.md, fix applied)
### Priority
8/10 — Corporate URL in a public repo is a security/privacy leak; affects all contributors and downstream users.
### Impact
- **Before**: Internal corporate host exposed in public code
- **After**: Generic placeholder; no internal infrastructure exposed
### Benefits
- Public repo no longer exposes internal URLs
- Script and docs use generic placeholder suitable for any GitLab instance
- `--gitlab-url` remains optional with a safe default
### Expected Behavior
- `validate_glfm.py --gitlab-url` defaults to `https://gitlab.example.com` (or equivalent generic placeholder)
- Documentation examples use generic URLs, not internal hosts
### Desired Structure
- Default URL: generic placeholder (e.g., `https://gitlab.example.com`)
- Alternative: make `--gitlab-url` required with no default
- Chosen approach: generic placeholder (keeps backward compatibility)
### Acceptance Criteria
1. [x] `validate_glfm.py` lines 152–153 use `https://gitlab.example.com` as default
2. [x] `gitlab-ci-local-guide.md` line 51 uses `https://gitlab.example.com` in examples
3. [x] No references to `sourcery.assaabloy.net` remain in the repo
### Resources
| Type | Item |
|------|------|
| Skill | gitlab-skill (`plugins/gitlab-skill/skills/gitlab-skill/`) |
| Skill | glab-cli-ci-debugging (Cursor skill for GitLab CI debugging) |
| Agent | @plugin-assessor (gitlab-skill audit) |
| Prior work | [completed-replace-requests-with-httpx-in-all-scripts](completed-replace-requests-with-httpx-in-all-scripts.md) — validate_glfm.py migrated to httpx |
| Prior work | [ideas-gitlab-skill-gitlab-ci-glfm-validation-mcp](ideas-gitlab-skill-gitlab-ci-glfm-validation-mcp.md) — MCP wrapper for validate_glfm |
| Commit | 103cbf6 |
### Effort
Small — two locations updated in a single commit.
