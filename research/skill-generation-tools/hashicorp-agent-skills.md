---
name: hashicorp-agent-skills
title: HashiCorp Agent Skills
subtitle: Official Agent Skills catalog for Terraform and Packer infrastructure workflows
research_date: 2026-10-02
source_url: https://github.com/hashicorp/agent-skills
github_repository: https://github.com/hashicorp/agent-skills
version_at_research: 1.0.0
license: MPL-2.0
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 1.0.0
  next_review: 2027-01-02
  confidence_map: "Overview: high, Features: high, Architecture: high, Installation & Usage: high, Limitations: medium"
---

# HashiCorp Agent Skills

## Overview

HashiCorp Agent Skills is an official collection of 20 independently installable AI agent skills for Terraform and Packer infrastructure workflows. The catalog comprises 16 Terraform skills covering configuration, modules, providers, testing, imports, stacks, and policy; plus 4 Packer skills for image building and HCP Packer registry workflows. Skills are distributed via product plugin bundles (`terraform@hashicorp` and `packer@hashicorp`) and individual skill installations across Claude Code, Codex, OpenCode, Cursor, and IBM Bob.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Terraform configuration generation and validation | Agent Skills provide SKILL.md templates and references for generating HCL following HashiCorp style conventions, with dedicated skills for configuration, modules, style guides, and policy |
| Terraform provider development workflow | Skills guide provider creation, configuration, framework migration, resource definition, ephemeral resource handling, testing patterns, and documentation |
| Packer image building across clouds | Skills automate AWS AMI building, Azure image generation, Windows image creation, and HCP Packer registry operations |
| Cross-platform LLM skill distribution | Product plugin bundles align with Claude Code and Codex marketplaces, supporting both direct installation and individual skill paths |

---

## Key Features

### Terraform Skills Catalog

- **Configuration and Style** (`terraform-style-guide`): Generate HCL following HashiCorp's official style conventions with file organization templates (terraform.tf, providers.tf, main.tf, variables.tf, outputs.tf, locals.tf)
- **Module and Stack Management** (`refactor-module`, `terraform-stacks`): Refactor existing modules and manage Terraform stacks with component and deployment block guidance
- **Provider Development** (`new-terraform-provider`, `provider-configuration`, `provider-framework-migration`, `provider-resources`, `provider-ephemeral-resources`, `provider-docs`): Full provider development lifecycle from scaffold to documentation, including framework migration patterns
- **Testing and Validation** (`run-acceptance-tests`, `terraform-test`, `provider-test-patterns`): Acceptance test execution, HCL testing, and test pattern guidance including sweepers and ephemeral test resources
- **Resource Management** (`terraform-search-import`): Discover and bulk import existing resources using Terraform Search
- **Policy as Code** (`terraform-policy`): Author and test HCP Terraform's native policy-as-code engine with TFPolicy syntax and verification examples

### Packer Skills Catalog

- **Image Building** (`aws-ami-builder`, `azure-image-builder`, `windows-builder`): Automated image creation across AWS, Azure, and Windows platforms with builder-specific guidance
- **Registry Operations** (`push-to-registry`): Push built images to HCP Packer registry for centralized artifact management

### Distribution and Cross-Platform Support

- **Product Bundles**: `terraform@hashicorp` and `packer@hashicorp` distribute all skills via Claude Code and Codex marketplaces
- **Individual Installation**: Each skill installable via `npx skills add hashicorp/agent-skills/plugins/<product>/skills/<skill-name>`
- **Multi-Harness Support**: Distributed to GitHub Copilot, Claude Code, OpenCode, Cursor, IBM Bob, and more
- **Lifecycle Governance**: All 20 skills marked as `active` (maintained, distributed, and recommended for normal use)

---

## Technical Architecture

The repository organizes skills under two product roots with aligned manifests:

```
agent-skills/
├── .claude-plugin/marketplace.json       [Claude Code marketplace]
├── .agents/plugins/marketplace.json      [Codex marketplace]
├── plugins/
│   ├── terraform/
│   │   ├── .claude-plugin/plugin.json    [Claude Code plugin manifest]
│   │   ├── .codex-plugin/plugin.json     [Codex plugin manifest]
│   │   └── skills/                       [16 Terraform skills]
│   └── packer/
│       ├── .claude-plugin/plugin.json    [Claude Code plugin manifest]
│       ├── .codex-plugin/plugin.json     [Codex plugin manifest]
│       └── skills/                       [4 Packer skills]
```

**Plugin Registration**: Each product defines a `name`, `version`, `description`, `category`, and `license` in plugin manifests. Marketplace metadata references:
- `"name": "terraform"` with `"source": "./plugins/terraform"`
- `"name": "packer"` with `"source": "./plugins/packer"`
- Both expose `"skills": "./skills/"` for skill discovery

**Skill Registration**: Each skill is a SKILL.md frontmatter directory containing:
- Required fields: `name` (matching directory name), `description`, `metadata.lifecycle-status`
- Supported lifecycle states: `active`, `deprecation-candidate`, `deprecated`, `retired`
- Reference materials in `references/`, `scripts/`, or `assets/` subdirectories

**Installation Flow**: Skills resolve through the product bundle (`terraform@hashicorp` installs all 16 Terraform skills) or directly via individual skill path (`npx skills add hashicorp/agent-skills/plugins/terraform/skills/terraform-style-guide`).

---

## Installation & Usage

### Install a Product Bundle

**Claude Code**:

```bash
claude plugin marketplace add hashicorp/agent-skills
claude plugin install terraform@hashicorp
claude plugin install packer@hashicorp
```

**Codex**:
Add the repository's `.agents/plugins/marketplace.json` as a repository marketplace, then install the `terraform` or `packer` plugin in Codex. Both marketplaces expose the same product bundles and skill directories.

### Install Individual Skills

List available skills:

```bash
npx skills add hashicorp/agent-skills
```

Install one skill by path:

```bash
npx skills add hashicorp/agent-skills/plugins/terraform/skills/terraform-style-guide
npx skills add hashicorp/agent-skills/plugins/packer/skills/aws-ami-builder
```

### Using a Skill

Once installed, invoke the skill in an LLM client. For example, when writing Terraform code, mention the goal and the terraform-style-guide skill activates to generate HCL following HashiCorp conventions.

---

## Relevance to Claude Code Development

### Applications

- **Agent Skills portable format implementation** -> `plugins/plugin-creator/skills/agentskills/SKILL.md`
  - Narrow term: `agent skills`; Broader term: `portable skill`
  - Anchor: Line 3 of `plugins/plugin-creator/skills/agentskills/SKILL.md` contains "Agent Skills portable format router. Use when creating cross-client skills, validating portable frontmatter, packaging skills for upload or API use, or implementing skill discovery and activation."
  - Today: The entry documents the portable Agent Skills format and its use cases
  - Change: HashiCorp Agent Skills exemplifies portable Agent Skills adoption at scale (20 active skills, multi-harness distribution); reference its plugin.json structure and lifecycle governance patterns in this skill's specification reference

- **Cross-harness skill distribution patterns** -> `plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md`
  - Narrow term: `agent skills`; Broader term: `portable skill`
  - Anchor: Line 28 of `plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md` contains "Claude Code accepts runtime fields beyond the portable Agent Skills schema."
  - Today: The entry documents Claude Code's role as a runtime host for portable Agent Skills
  - Change: HashiCorp Agent Skills demonstrates aligned multi-harness distribution (Claude Code, Codex, Cursor, GitHub Copilot); include as case-study example showing marketplace alignment requirements

- **Marketplace metadata versioning** -> `docs/marketplace-versioning.md`
  - Narrow term: `plugin version`; Broader term: `marketplace version`
  - Anchor: Line 1 of `docs/marketplace-versioning.md` is "# Marketplace versioning"
  - Today: The document defines marketplace versioning patterns and CI automation
  - Change: HashiCorp Agent Skills uses version 1.0.0 consistently across both marketplace.json and plugin.json with aligned CHANGELOG tracking, matching claude_skills' versioning pattern

### Absence Anchors

- **Product-scoped skill organization** — neither term has matches in this repository
  - Narrow term: `product bundle` (0 matches)
  - Broader term: `product plugin` (0 matches)
  - Absence pattern: claude_skills does not currently organize skills under product-scoped directories with separate manifests per product family
  - Pattern adoption opportunity: HashiCorp agent-skills groups Terraform and Packer skills into separate product root directories, each with independent Claude Code and Codex manifests; this organizational pattern could be adopted as claude_skills scales to support more domain-specific skill collections

---

## Limitations and Caveats

**Internal-contribution phase**: The repository is in an "internal-contribution-only phase" until further notice. Contributions from external developers are not currently accepted; the maintained pathway is for HashiCorp-internal contributors. External usage of the skills is supported, but skill contribution or modification pathways are restricted.

**Model support baseline**: Supported models are limited to Claude Opus (Latest and N-1), Claude Sonnet (Latest with temporary Inference Availability Exception for N-1), and OpenAI GPT (Latest and N-1) as of 2026-08-31. Behavior is not guaranteed to be identical across models or harnesses, and models outside this matrix are unsupported or unevaluated.

**Marketplace alignment requirement**: Claude Code and Codex plugin manifests (`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`) are hand-maintained and must expose the same `skills/` directory. Manual synchronization is required; automated alignment is not documented.

**Legal responsibility caveat**: "Your use of a third-party MCP client or LLM is subject solely to that provider's terms. IBM is not responsible for the performance of those third-party tools and may be unable to support issues caused by them." (Note: The legal notice names IBM rather than HashiCorp, suggesting this may be carry-forward language from an earlier context.)

---

## References

- [HashiCorp Agent Skills Repository](https://github.com/hashicorp/agent-skills) (accessed 2026-10-02)
- [HashiCorp Agent Skills README](https://github.com/hashicorp/agent-skills/blob/main/README.md) (accessed 2026-10-02)
- [Skill Catalog (SKILLS.md)](https://github.com/hashicorp/agent-skills/blob/main/SKILLS.md) (accessed 2026-10-02)
- [Supported Models Matrix](https://github.com/hashicorp/agent-skills/blob/main/SUPPORTED_MODELS.md) (accessed 2026-10-02)
- [Agent Instructions (AGENTS.md)](https://github.com/hashicorp/agent-skills/blob/main/AGENTS.md) (accessed 2026-10-02)
- [Terraform Skills Plugin](https://github.com/hashicorp/agent-skills/blob/main/plugins/terraform/README.md) (accessed 2026-10-02)
- [Packer Skills Plugin](https://github.com/hashicorp/agent-skills/blob/main/plugins/packer/README.md) (accessed 2026-10-02)
- [Claude Code Marketplace Configuration](./.claude-plugin/marketplace.json) (accessed 2026-10-02)
- [Terraform Style Guide Skill](https://github.com/hashicorp/agent-skills/blob/main/plugins/terraform/skills/terraform-style-guide/SKILL.md) (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [ClawHub](./clawhub.md) | skill-generation-tools | semantic skill registry implementing vector-based discovery for cross-harness skill distribution |
| [mcpskills-cli](./mcpskills-cli.md) | skill-generation-tools | MCP-to-skill converter generating portable Agent Skills from external tool specifications |
| [Skrills](./skrills.md) | skill-generation-tools | multi-harness skill validator synchronizing portable Agent Skills across Claude Code, Codex, and Copilot CLI |
| [Vercel Labs Skills](./vercel-labs-skills.md) | skill-generation-tools | universal skill installer pattern distributing portable skills across 40+ agent platforms |
| [Claude Code Skills Library](./claude-code-skills-alirezarezvani.md) | skill-generation-tools | comparable scale (362 skills) with overlapping multi-harness distribution (Claude Code, Codex, Cursor) |
| [Claude Code Templates](./claude-code-templates.md) | skill-generation-tools | cross-platform skill ecosystem (100+ agents/commands/skills/MCPs) extending distribution beyond product bundles |
| [Everything Claude Code](./everything-claude-code.md) | skill-generation-tools | comprehensive harness performance system (65+ skills, 16 agents) with lifecycle governance and multi-agent orchestration |
| [Skill Seekers](./skill-seekers.md) | skill-generation-tools | documentation-to-skills automation extending portable Agent Skills creation beyond manual SKILL.md authorship |
