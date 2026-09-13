---
name: ClawHub
description: ClawHub is described as "a fast skill registry for agents, with vector search." The platform appears to be a web-based registry for discovering and potentially sharing AI agent skills, utilizing...
license: Unknown
metadata:
  topic: clawhub
  category: skill-generation-tools
  source_url: https://www.clawhub.ai/skills
  version: "Unknown"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

ClawHub is the public skill registry for the OpenClaw / Clawdbot agent ecosystem — described as "npm for AI agents." It lets developers publish, version, search, and install reusable `AgentSkills` bundles (a `SKILL.md` plus optional supporting files). Discovery is powered by OpenAI embedding-based vector search rather than keyword matching, making it possible to find skills by intent rather than exact name.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Skills are scattered across repos with no central discovery surface | Centralized public registry with web UI and CLI |
| Keyword search fails when users don't know exact skill names | Vector (semantic) search via OpenAI embeddings finds by intent |
| No standard versioning or rollback for agent skills | semver versioning with changelogs and tags (e.g. `latest`) |
| Manually sharing skill bundles is error-prone | `clawhub publish` / `clawhub sync` one-command publish workflow |
| Difficult to audit what a skill does before installing | Full `SKILL.md` rendered in browser; `clawhub inspect <slug>` in CLI |
| No community trust signals for community-submitted skills | Stars, comments, moderation, 3-report auto-hide, VirusTotal scanning |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars (openclaw/clawhub) | Not yet public (private at time of launch) | 2026-02-23 |
| npm package | `clawhub` | 2026-02-23 |
| License | MIT | 2026-02-23 |
| Discord | Active (discord.gg/clawd) | 2026-02-23 |
| Skills in registry | 3,286+ (per third-party aggregator) | 2026-02-23 |

---

## Key Features

### Skill Registry

- Stores versioned skill bundles: `SKILL.md` + optional supporting files
- Full browse and render of `SKILL.md` in the web UI
- Soft-delete/restore with hard-delete for admins only
- Download as zip per version
- Companion SOUL.md registry at `onlycrabs.ai` for agent system lore

### Vector Search

- Semantic search powered by OpenAI `text-embedding-3-small` embeddings
- Stored in Convex vector index — query by intent ("web scraper") not just exact name
- `clawhub search "query"` in CLI mirrors the web search experience

### Versioning & Lifecycle

- semver versioning; tags (including `latest`) point to specific versions
- Full changelog per version; content-hash comparison for local vs. registry drift
- `clawhub update --all` bulk-updates installed skills

### CLI (`clawhub`)

- Install: `npm i -g clawhub` / `pnpm add -g clawhub`
- Auth flow: `clawhub login` (GitHub OAuth browser flow or `--token`)
- Discover: `clawhub search "..."`, `clawhub explore`
- Manage: `clawhub install <slug>`, `clawhub update --all`, `clawhub list`
- Inspect without installing: `clawhub inspect <slug>`
- Publish: `clawhub publish <path>`, `clawhub sync` (bulk scan + publish)

### Security & Moderation

- GitHub account must be ≥1 week old to publish
- Any signed-in user can report; skills auto-hidden after 3 unique reports
- Moderators can view, unhide, delete, or ban
- VirusTotal partnership for malware scanning (post-ClawHavoc February 2026)
- Skills declare runtime requirements (env vars, binaries) in `SKILL.md` frontmatter for security analysis

### Nix Plugin Support

- `SKILL.md` frontmatter supports `metadata.clawdbot.nix` pointer to Nix package bundle
- Enables nix-clawdbot plugin install for fully declarative agent environments

---

## Technical Architecture

**Frontend**:

- TanStack Start (React + Vite/Nitro) with SSR
- Host-based routing: `clawhub.ai` → skills mode; `onlycrabs.ai` → souls mode
- Module preloading for performance

**Backend**:

- Convex: database, file storage, HTTP action routes, vector index
- Convex Auth with GitHub OAuth
- OpenAI `text-embedding-3-small` for search embeddings

**CLI**:

- npm package `clawhub`; also installable via pnpm/bun
- Lockfile at `.clawhub/lock.json` tracks installed skills
- Config stored in `CLAWHUB_CONFIG_PATH` (overridable)

**API / Schema**:

- Shared API types in `packages/schema` (`clawhub-schema`)
- CLI-friendly API for automation and scripting

---

## Installation & Usage

```bash
# Install the CLI
npm i -g clawhub
# or
pnpm add -g clawhub

# Authenticate (GitHub OAuth)
clawhub login

# Search by intent
clawhub search "postgres backups"

# Inspect before installing
clawhub inspect my-skill-pack

# Install a skill
clawhub install my-skill-pack

# Update all installed skills
clawhub update --all

# Publish a skill
clawhub publish ./my-skill --slug my-skill --name "My Skill" --version 1.0.0 --tags latest

# Bulk publish / sync all local skills
clawhub sync --all
```

**Disable telemetry**:

```bash
export CLAWHUB_DISABLE_TELEMETRY=1
```

**Skill `SKILL.md` frontmatter example with metadata**:

```yaml
---
name: my-skill
description: Does a thing with an API.
metadata:
  openclaw:
    requires:
      env:
        - MY_API_KEY
      bins:
        - curl
    primaryEnv: MY_API_KEY
---
```

---

## Relevance to Claude Code Development

### Applications

- **Skill Discovery Surface**: ClawHub is a direct peer to this repository's plugin marketplace. Skills published here are consumable by Clawdbot/OpenClaw agents; the architecture validates the `SKILL.md`-centric model used in claude_skills.
- **Competitive Benchmark**: Provides a reference implementation of a functioning public skill registry to compare against when evolving the local marketplace manifest.
- **Publishing Channel**: claude_skills plugins could be cross-published to ClawHub to reach the OpenClaw community, since both use `SKILL.md` bundles.

### Patterns Worth Adopting

- **Vector Search for Skill Discovery**: Semantic search (`text-embedding-3-small` + vector index) significantly outperforms keyword search — worth evaluating for the local marketplace search.
- **Semver + Changelog Versioning**: ClawHub's per-version changelog model is more robust than the current `plugin.json` version field; adopting changelogs would help users track breaking changes.
- **Content-Hash Drift Detection**: CLI compares local file hash to registry versions before overwriting — a useful safety pattern for any future `claude skills update` command.
- **Security Declarations in Frontmatter**: Requiring skills to declare `env` and `bin` requirements in `SKILL.md` frontmatter enables static security analysis before install.

### Integration Opportunities

- **Cross-publish**: Use `clawhub publish` to mirror selected claude_skills plugins to ClawHub for discovery by the OpenClaw community.
- **Import from ClawHub**: `clawhub install <slug>` into a Claude Code workspace would be immediately useful if skill formats align (both use `SKILL.md`).
- **Registry Architecture Reference**: The Convex + vector-search architecture is a proven blueprint for a hosted version of the claude_skills marketplace.

### Competitive Analysis

| Feature | ClawHub | claude_skills marketplace |
|---------|---------|--------------------------|
| Public registry | ✅ hosted at clawhub.ai | ❌ local `.claude-plugin/marketplace.json` only |
| Vector search | ✅ OpenAI embeddings | ❌ not implemented |
| CLI install | ✅ `clawhub install` | ✅ `/plugin install` in Claude Code |
| Versioning | ✅ semver + changelogs | ✅ `plugin.json` version field |
| Community moderation | ✅ reports, stars, comments | ❌ not implemented |
| Open source | ✅ MIT | ✅ repository is public |

---

## References

- [ClawHub Skills Website](https://www.clawhub.ai/skills) (accessed 2026-02-23)
- [GitHub: openclaw/clawhub](https://github.com/openclaw/clawhub) (accessed 2026-02-23)
- [OpenClaw Docs: ClawHub](https://docs.openclaw.ai/tools/clawhub) (accessed 2026-02-23)
- [EveryDev.ai: ClawHub listing](https://www.everydev.ai/tools/clawhub) (accessed 2026-02-23)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-02-23 |
| Version at Verification | CLI v1.x (npm `clawhub`) |
| Next Review Recommended | 2026-05-23 |

**Review Triggers**:

- Public API documentation expanded
- GitHub repository star count becomes significant
- New skill format features (SOUL.md, nix plugins) stabilise
- Integration between Claude Code and OpenClaw ecosystems emerges
- [ClawHub Skills Website](https://www.clawhub.ai/skills) (accessed 2026-02-20)
- [ClawHub Homepage](https://www.clawhub.ai) (accessed 2026-02-20)
- Site meta description: "ClawHub — a fast skill registry for agents, with vector search." (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [OpenSpace](../ai-research-tools/OpenSpace.md) | ai-research-tools | referenced by OpenSpace (ai-research-tools) |
