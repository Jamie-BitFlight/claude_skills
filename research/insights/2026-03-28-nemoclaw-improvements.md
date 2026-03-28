# Improvement Proposals: NVIDIA NemoClaw

**Research entry**: ./research/agent-infrastructure/nemoclaw.md
**Generated**: 2026-03-28
**Patterns assessed**: 3
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 3

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Agent Sandbox Reference Implementation (policy-enforced isolation with Landlock, seccomp, network namespaces) | Incompatible with local architecture. NemoClaw operates at the container/OS isolation layer, deploying agents into sandboxed OpenShell environments. This repo is a Claude Code plugin marketplace providing skills, agents, and workflows. Agent sandboxing is owned by the Claude Code runtime, not by plugin content. Implementing sandbox policies would require extending the Claude Code runtime itself, not this repo. |
| Inference Routing Patterns (credential isolation, transparent provider routing via gateway) | Incompatible with local architecture. NemoClaw intercepts inference calls at a network proxy layer and routes them to configured providers while keeping credentials outside the sandbox. This repo uses Claude Code's built-in `model:` frontmatter field for model selection (see `.claude/rules/model-selection.md`). Inference routing and credential management are owned by the Claude Code runtime. The repo has no inference proxy or credential store to extend. |
| Supply Chain and Versioning (blueprint digest verification, immutable versioned artifacts) | Incompatible with local architecture. NemoClaw verifies artifact digests (hashes) before executing blueprints as a supply chain security measure. This repo has version bumping via `auto_sync_manifests.py` and plugin validation via `skilllint` and `claude plugin validate`, but plugin loading and cache integrity are managed by the Claude Code runtime (plugins are copied to `~/.claude/plugins/cache/`). Adding digest verification would require changes to the Claude Code plugin loader, which is outside this repo's control. The version bumping and structural validation already present in the repo are the extent of what can be controlled at the plugin content layer. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | -- | All three patterns were skipped as architecturally incompatible rather than deferred for low confidence |
