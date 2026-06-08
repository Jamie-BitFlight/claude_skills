# Development-Harness Skill Taxonomy Report

Date: 2026-06-08
Plugin: `plugins/development-harness`
Framework lens: the nine skill categories shown in the Anthropic "Types of skills" taxonomy image

## Purpose

This report evaluates the existing `development-harness` skills against the following taxonomy:

1. Library & API Reference
2. Product Verification
3. Data & Analysis
4. Business Automation
5. Scaffolding & Templates
6. Code Quality & Review
7. CI/CD & Deployment
8. Incident Runbooks
9. Infrastructure Ops

The goal is not to force perfect one-to-one mapping. It is to identify:

- where the plugin already has strong durable skills
- where skills are present but packaged awkwardly
- where major gaps still exist
- which skills are overloaded and straddle too many categories

## Method

This analysis used the local `ensemble-rule-review` skill as the framing device for the review approach: treat the taxonomy as a large rubric, split the work across parallel bounded reviewers, and then synthesize the results.

Parallel analysis threads covered:

- category mapping across all `development-harness` skills
- overloaded and straddling skills
- category coverage gaps and missing opportunities
- exemplar skills that fit one category especially well

Local synthesis then reconciled those findings against the plugin's own framing in:

- `plugins/development-harness/CLAUDE.md`
- `plugins/development-harness/skills/development-harness/SKILL.md`

## Executive Summary

`development-harness` is strongest as a structured software-delivery and orchestration plugin, not as a broad operational skills library.

Its deepest coverage is in:

- Business Automation
- Code Quality & Review
- Product Verification

It has partial but less clean coverage in:

- Library & API Reference
- Data & Analysis
- Scaffolding & Templates
- CI/CD & Deployment

It is weak or missing in:

- Incident Runbooks
- Infrastructure Ops

The main structural issue is not lack of capability alone. It is also packaging. Several of the most important `dh` skills act as lifecycle orchestrators that span multiple categories, which makes them powerful but harder for an agent to classify and invoke cleanly.

## Category Coverage

| Category | Coverage | Notes |
|---|---|---|
| Library & API Reference | Moderate | Present through research/reference angles such as `api-state`, `ecosystem-research`, `dh-meta-docs`, and `codebase-auditor`, but fragmented rather than packaged as one durable reference surface. |
| Product Verification | Strong | One of the cleanest areas: `validation-protocol`, `forensic-review`, `final-verification`, `verify-done`, and `complete-implementation`. |
| Data & Analysis | Moderate | Good engineering-analysis skills exist, especially `impact-measurement`, `codebase-auditor`, and `research-note`, but this is not operational data analysis in the dashboard/query/log sense. |
| Business Automation | Strong | A core strength of the plugin: backlog CRUD, grooming, milestone flows, plan/work routing, and GitHub/Project automation. |
| Scaffolding & Templates | Moderate | Strong for task-plan scaffolding and artifact generation, weak for framework- or code-level scaffolding. |
| Code Quality & Review | Strong | The richest category: stack-specific code review skills, architectural review, test review, multi-perspective review, and file classification. |
| CI/CD & Deployment | Thin | Present mainly through `gate-push` and milestone execution/closure flows, but not as a full deployment toolbox. |
| Incident Runbooks | Thin | Investigation-oriented skills exist, but not many explicit symptom-to-investigation operational runbooks. |
| Infrastructure Ops | Weak | Only a few adjacent fits such as `kage-bunshin`, `backlog-tools-administrator`, and `codemod-runner`; little true infra or maintenance coverage. |

## Best-Fit Exemplars

These are the clearest examples of skills that fit one taxonomy category well.

| Skill | Primary category | Why it fits |
|---|---|---|
| `api-state` | Library & API Reference | Narrowly focused on current API syntax, changelogs, and breaking changes for a named library or protocol version. |
| `validation-protocol` | Product Verification | Clear observe-broken, define-success, apply-fix, observe-working verification loop. |
| `final-verification` | Product Verification | Goal-backward certification against original requirements and acceptance tests. |
| `codebase-auditor` | Data & Analysis | Derives actual contracts, conventions, insertion points, and available data from source. |
| `impact-measurement` | Data & Analysis | Clean quantitative analysis of token cost, payload size, and context impact. |
| `complete-milestone` | Business Automation | Tight workflow for milestone audit, carry-forward decisions, closure, and summary. |
| `generate-task` | Scaffolding & Templates | Single-purpose task prompt scaffolding with a standard output shape. |
| `task-decomposition` | Scaffolding & Templates | Converts a contextualized plan into atomic executable task files. |
| `code-review-architecture` | Code Quality & Review | Strong single-purpose architectural review and dependency graph analysis. |
| `comprehensive-test-review` | Code Quality & Review | Clear checklist-driven audit of test quality and coverage. |
| `gate-push` | CI/CD & Deployment | Best direct branch-to-PR gate flow in the plugin. |
| `find-cause` | Incident Runbooks | Strong evidence-chain investigation wrapper, even if broader than classic on-call runbooks. |

## Meta Skills vs Category Skills

Some of the most important `dh` skills are not good single-category exemplars because they are intentionally orchestration-heavy:

- `development-harness`
- `dispatch`
- `implement-feature`
- `work-backlog-item`
- `work-milestone`

These are better understood as control-plane skills. They route, coordinate, or manage lifecycle state across other skills rather than fitting neatly into one taxonomy bucket.

## Overloaded or Straddling Skills

The largest concentration of ambiguity comes from lifecycle orchestrators that mix state mutation, orchestration, review policy, and synthesis in one skill body.

### Most important examples

- `work-backlog-item`
  Primary straddle: Business Automation + Scaffolding & Templates + Data & Analysis
  Why: bridges backlog browsing, auto-groom, RT-ICA gating, GitHub sync, SAM planning, close/resolve flows, and status-oriented control operations.

- `add-new-feature`
  Primary straddle: Scaffolding & Templates + Data & Analysis + Code Quality & Review
  Why: owns discovery, codebase analysis, architecture spec, task decomposition, validation, artifact storage, and planning policy.

- `implement-feature`
  Primary straddle: Business Automation + CI/CD & Deployment + Code Quality & Review
  Why: combines execution loop management, teammate orchestration, concern collection, contract enforcement, and commit/merge policy.

- `complete-implementation`
  Primary straddle: Product Verification + Code Quality & Review + Business Automation
  Why: combines quality gates, independent review, verification, follow-up task creation, and completion-state mutation.

- `work-milestone`
  Primary straddle: Business Automation + CI/CD & Deployment + Infrastructure Ops
  Why: combines milestone orchestration, worktree/session management, merge sequencing, and branch landing.

- `groom-milestone`
  Primary straddle: Data & Analysis + Business Automation + CI/CD & Deployment
  Why: combines dependency analysis, conflict grouping, wave planning, and execution-readiness shaping.

- `backlog-tools-administrator`
  Primary straddle: Infrastructure Ops + Business Automation + Code Quality & Review
  Why: handles tooling gaps across scripts, process, docs, tests, and registry maintenance.

- `setup-skill-discovery`
  Primary straddle: Scaffolding & Templates + Data & Analysis + Library & API Reference
  Why: mixes repo scanning, skill inventory, candidate evaluation, stack detection, and config generation.

### Heuristics that emerged

- Clean-fit skills tend to have one dominant verb and one terminal output.
- Skills become confusing when they mix orchestration, review policy, and state mutation.
- Router skills are fine if they route only; they become noisy when they also execute substantial workflow logic.
- Lifecycle skills can remain broad if most substantive work is delegated into narrower child skills.

## Present But Not Cleanly Packaged

Several categories are more present than they first appear, but the skills are fragmented or named in a way that hides the taxonomy fit.

### Library & API Reference

Present through:

- `api-state`
- `ecosystem-research`
- `dh-meta-docs`
- `codebase-auditor`
- `fact-check`

Problem: this behaves more like a research toolkit than a clean reference shelf.

### Product Verification

Present through:

- `validation-protocol`
- `forensic-review`
- `final-verification`
- `verify-done`
- `complete-implementation`

Problem: this is strong functionally, but spread across multiple phase-oriented names rather than an obvious verification family.

### Data & Analysis

Present through:

- `impact-measurement`
- `codebase-auditor`
- `code-review-architecture`
- `research-note`

Problem: this is engineering-analysis, not operational data analysis in the sense implied by the taxonomy image.

### CI/CD & Deployment

Present through:

- `gate-push`
- pieces of `implement-feature`
- pieces of `complete-implementation`
- milestone execution flows

Problem: these are release-adjacent gates and orchestration steps, not a mature CI/deploy toolbox.

## True Gaps

The following gaps look real rather than merely mislabeled.

### Data & Analysis

Missing or underdeveloped:

- query- and dashboard-oriented investigation
- IDs, field names, and schema lookup surfaces
- production evidence gathering patterns
- logs/metrics/traces analysis skills

### CI/CD & Deployment

Missing or underdeveloped:

- CI failure triage
- deploy execution flows
- deploy verification
- rollback guidance
- cherry-pick and release-candidate handling
- PR babysitting / check shepherding

### Incident Runbooks

Missing or underdeveloped:

- symptom-first operational playbooks
- outage-specific investigation runbooks
- queue/backlog processing incident diagnostics
- auth/webhook/dependency failure playbooks

### Infrastructure Ops

Missing or underdeveloped:

- dependency maintenance and hygiene
- orphan/cleanup tasks
- environment drift checks
- cost investigation
- secrets/config/infra safety procedures

### Scaffolding & Templates

Missing or underdeveloped:

- actual app/service scaffolds
- migration scaffolds
- workflow boilerplate beyond planning artifacts
- test harness or starter-project scaffolds

## Most Obvious New Skill Opportunities

- `dashboard-investigator`
- `query-production-signal`
- `triage-ci-failure`
- `deploy-and-verify`
- `rollback-runbook`
- `incident-queue-debug`
- `incident-auth-debug`
- `incident-webhook-debug`
- `deps-maintenance`
- `orphan-cleanup`
- `cost-investigation`
- `new-service-scaffold`
- `migration-scaffold`

## Bottom Line

`development-harness` is already a mature process harness. It is not weak overall. It is specialized.

The plugin clearly excels at:

- orchestrating tracked feature delivery
- automating backlog and milestone workflows
- applying review and verification gates
- scaffolding planning artifacts and task files

Its next level of improvement is not "add more general capability everywhere." It is:

1. package existing strengths more cleanly where categories are currently fragmented
2. split or clarify overloaded orchestrator skills where one body spans too many concerns
3. add a small number of explicit operational skill families in CI/CD, incident response, infra ops, and production-facing data analysis

If the taxonomy is being used as a design lens, the biggest recommendation is this:

Keep `development-harness` as the orchestration/process plugin, but grow adjacent, cleaner operational skills around it rather than making the main lifecycle skills even broader.
