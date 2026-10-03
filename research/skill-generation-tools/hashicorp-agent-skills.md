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
  confidence_map: "Overview: high, Features: high, Architecture: high, Installation & Usage: medium, Limitations: medium, Problem Addressed: high, Relevance to Claude Code Development: medium"
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
- **Module and Stack Management** (`refactor-module`, `terraform-stacks`, `azure-verified-modules`): Refactor existing modules and manage Terraform stacks with component and deployment block guidance; `azure-verified-modules` has the SKILL.md description "Azure Verified Modules (AVM) requirements and best practices for developing certified Azure Terraform modules. Use when creating or reviewing Azure modules that need AVM certification." (`plugins/terraform/skills/azure-verified-modules/SKILL.md`)
- **Provider Development** (`new-terraform-provider`, `provider-configuration`, `provider-framework-migration`, `provider-resources`, `provider-ephemeral-resources`, `provider-docs`, `provider-actions`): Full provider development lifecycle from scaffold to documentation, including framework migration patterns; `provider-actions` has the SKILL.md description "Implement Terraform Provider actions using the Plugin Framework. Use when developing imperative operations that execute at lifecycle events (before/after create, update, destroy)." (`plugins/terraform/skills/provider-actions/SKILL.md`)
- **Testing and Validation** (`run-acceptance-tests`, `terraform-test`, `provider-test-patterns`): Acceptance test execution, HCL testing, and test pattern guidance including sweepers and ephemeral test resources
- **Resource Management** (`terraform-search-import`): Discover and bulk import existing resources using Terraform Search. Mechanism per `plugins/terraform/skills/terraform-search-import/SKILL.md`: the agent creates `.tfquery.hcl` files with `list` blocks, runs `terraform query`, generates configuration with `-generate-config-out=<file>`, then runs `terraform plan` and `terraform apply` to import; it first runs `./scripts/list_resources.sh <provider>` to check provider support, and falls back to `references/MANUAL-IMPORT.md` when the resource type is unsupported or Terraform is below 1.14.0
- **Policy as Code** (`terraform-policy`): Author and test HCP Terraform's native policy-as-code engine with TFPolicy syntax and verification examples

### Packer Skills Catalog

- **Image Building** (`aws-ami-builder`, `azure-image-builder`, `windows-builder`): Image creation with builder-specific templates: `aws-ami-builder` uses the `amazon-ebs` builder (`source "amazon-ebs"`), `azure-image-builder` uses the `azure-arm` builder (`source "azure-arm"`, managed images and Azure Compute Gallery), and `windows-builder` uses a WinRM communicator with `powershell` provisioners (examples for `amazon-ebs` and `azure-arm` sources); `aws-ami-builder` and `azure-image-builder` list `packer init .`, `packer validate .` and `packer build .` as build commands, while build commands in `windows-builder`: Not mentioned in documentation (`plugins/packer/skills/*/SKILL.md`)
- **Registry Operations** (`push-to-registry`): Push Packer build metadata to HCP Packer registry: the `push-to-registry` SKILL.md states "Builds push metadata only (not actual images)"; the template adds a `hcp_packer_registry` block (`bucket_name`, optional `bucket_labels` and `build_labels`) inside `build {}`, authenticates with the environment variables `HCP_CLIENT_ID`, `HCP_CLIENT_SECRET`, `HCP_ORGANIZATION_ID`, `HCP_PROJECT_ID`, then runs `packer build .` (`plugins/packer/skills/push-to-registry/SKILL.md`)

### Distribution and Cross-Platform Support

- **Product Bundles**: `terraform@hashicorp` and `packer@hashicorp` distribute all skills via Claude Code and Codex marketplaces
- **Individual Installation**: Each skill installable via `npx skills add hashicorp/agent-skills/plugins/<product>/skills/<skill-name>`
- **Multi-Harness Support**: Distributed to GitHub Copilot, Claude Code, OpenCode, Cursor, IBM Bob, and more
- **Lifecycle Governance**: All 20 skills marked as `active` (maintained, distributed, and recommended for normal use)

---

## Technical Architecture

The repository organizes skills under two product roots with aligned manifests:

```text
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

How to invoke an installed skill in an LLM client: Not mentioned in documentation (README.md, plugins/terraform/README.md, AGENTS.md and the terraform-style-guide SKILL.md describe installation and the skill description "Use when writing, reviewing, or generating Terraform configurations.", but give no invocation example).

---

## Relevance to Claude Code Development

### Applications

- **Agent Skills portable format implementation** -> `plugins/plugin-creator/skills/agentskills/SKILL.md`
  - Term: `agent skills`
  - Today: "Use this skill for the portable Agent Skills boundary." (line 9 of `plugins/plugin-creator/skills/agentskills/SKILL.md`)
  - Change: HashiCorp Agent Skills exemplifies portable Agent Skills adoption at scale (20 active skills, multi-harness distribution); reference its plugin.json structure and lifecycle governance patterns in this skill's specification reference

- **Cross-harness skill distribution patterns** -> `plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md`
  - Term: `agent skills`
  - Today: "Claude Code accepts runtime fields beyond the portable Agent Skills schema." (line 28 of `plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md`)
  - Change: HashiCorp Agent Skills demonstrates aligned multi-harness distribution (Claude Code, Codex, Cursor, GitHub Copilot); include as case-study example showing marketplace alignment requirements

- **Marketplace metadata versioning** -> `docs/marketplace-versioning.md`
  - Term: `plugin version`
  - Today: "`chore(plugins): assign plugin versions`" (line 47 of `docs/marketplace-versioning.md`)
  - Change: HashiCorp's Claude Code and Codex manifests are hand-maintained (see Limitations and Caveats); `docs/marketplace-versioning.md` could gain a note contrasting its CI-assigned patch bumps with that manual model

---

## Limitations and Caveats

**Internal-contribution phase**: The repository is in an "internal-contribution-only phase" until further notice. Contributions from external developers are not currently accepted; the maintained pathway is for HashiCorp-internal contributors. External usage of the skills is supported, but skill contribution or modification pathways are restricted.

**Model support baseline**: Supported models are limited to Claude Opus (Latest and N-1), Claude Sonnet (Latest with temporary Inference Availability Exception for N-1), and OpenAI GPT (Latest and N-1) as of 2026-08-31. Behavior is not guaranteed to be identical across models or harnesses, and models outside this matrix are unsupported or unevaluated.

**Marketplace alignment requirement**: Claude Code and Codex plugin manifests (`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`) are hand-maintained and must expose the same `skills/` directory. Manual synchronization is required; automated alignment is not documented.

**Legal responsibility caveat**: "Your use of a third-party MCP client or LLM is subject solely to that provider's terms. IBM is not responsible for the performance of those third-party tools and may be unable to support issues caused by them." The notice names IBM; the repository does not state why.

---

## References

- [HashiCorp Agent Skills Repository](https://github.com/hashicorp/agent-skills) (accessed 2026-10-02)
- [HashiCorp Agent Skills README](https://github.com/hashicorp/agent-skills/blob/main/README.md) (accessed 2026-10-02)
- [Skill Catalog (SKILLS.md)](https://github.com/hashicorp/agent-skills/blob/main/SKILLS.md) (accessed 2026-10-02)
- [Supported Models Matrix](https://github.com/hashicorp/agent-skills/blob/main/SUPPORTED_MODELS.md) (accessed 2026-10-02)
- [Agent Instructions (AGENTS.md)](https://github.com/hashicorp/agent-skills/blob/main/AGENTS.md) (accessed 2026-10-02)
- [Terraform Skills Plugin](https://github.com/hashicorp/agent-skills/blob/main/plugins/terraform/README.md) (accessed 2026-10-02)
- [Packer Skills Plugin](https://github.com/hashicorp/agent-skills/blob/main/plugins/packer/README.md) (accessed 2026-10-02)
- [Claude Code Marketplace Configuration](https://github.com/hashicorp/agent-skills/blob/main/.claude-plugin/marketplace.json) (accessed 2026-10-02)
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
