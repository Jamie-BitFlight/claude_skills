# slime

**Research Date**: 2026-06-29
**Source URL**: <https://github.com/THUDM/slime>
**GitHub Repository**: <https://github.com/THUDM/slime>
**Version at Research**: v0.3.0
**License**: Apache-2.0

---

## Overview

slime is THUDM's open-source LLM post-training framework for reinforcement-learning scaling. The project combines Megatron training, SGLang rollout/serving, custom data generation, reward computation, and a shared Data Buffer path so RL post-training workflows can stay close to the upstream training and inference engines rather than becoming a stack of disconnected services.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| RL post-training systems often split trainers, rollout services, rewards, and data buffers into hard-to-debug layers. | slime routes Megatron training, SGLang rollout, custom generation, rewards, verifier feedback, and environment interaction through the same training / rollout / Data Buffer path. |
| Large-model RL infrastructure needs both high-throughput rollout and correctness checks because failures can be silent. | The framework documents rollout-only and train-only debugging, reproducibility, fault tolerance, tracing, profiling, CI coverage, checkpointing, and weight synchronization as first-class engineering concerns. |
| Agentic RL needs custom multi-turn generation, tools, sandboxes, and verifier rewards without forking the training kernel. | slime exposes customization interfaces such as `--custom-generate-function-path`, `--custom-rm-path`, `--rollout-function-path`, and `--data-source-path` for agent loops, RAG, tool use, sandbox execution, and verifier reward computation. |
| Multi-backend abstractions can hide backend-specific serving features. | slime intentionally optimizes around SGLang as the rollout backend and exposes installed SGLang arguments through `--sglang-` pass-through while preserving Megatron argument access. |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 7,092 | 2026-06-29 |
| GitHub Forks | 1,004 | 2026-06-29 |
| Contributors | 153 | 2026-06-29 |
| Latest Release | v0.3.0, published 2026-05-31 | 2026-06-29 |
| Primary Language | Python | 2026-06-29 |
| Repository Activity | Last pushed 2026-06-29T07:45:12Z | 2026-06-29 |

---

## Key Features

### Megatron + SGLang RL Loop

- The main training entrypoint creates Ray placement groups, initializes a rollout manager, creates actor/critic training models, pushes actor weights to rollout, alternates rollout generation and model training, periodically saves checkpoints, and evaluates on configured intervals. Source: `train.py` — `train()`.
- SGLang rollout servers are represented by `ServerGroup` objects that capture homogeneous engine groups, worker type, GPU offset, router address, SGLang overrides, model paths, and offload needs. Source: `slime/ray/rollout.py` — `class ServerGroup`.
- The framework supports synchronous training via `train.py` and a separate asynchronous loop in `train_async.py` that starts the next rollout before training on the current rollout and syncs generation before scheduled weight updates. Source: `train_async.py` — `train()`.

### Native Engine Pass-Through

- Megatron arguments remain directly available to slime jobs, so tensor parallelism, optimizer, checkpointing, and model options do not require wrapper-specific redefinition.
- Installed SGLang arguments can be passed with a `--sglang-` prefix, such as mapping SGLang's `--mem-fraction-static` to slime's `--sglang-mem-fraction-static`.
- The argument parser separately parses SGLang arguments, parses Megatron plus slime arguments while ignoring `--sglang-*`, then merges the SGLang namespace into the main args object. Source: `slime/utils/arguments.py` — `parse_args()`.

### Agentic RL Customization

- `--custom-generate-function-path` overrides per-sample generation for tool-calling, RAG, multi-turn conversations, browser/terminal interaction, and sandbox execution while retaining the default rollout loop.
- `--custom-rm-path` supports custom reward computation, including verifier rewards, test-based rewards, environment success checks, rule-based rewards, and remote reward services.
- `--rollout-function-path` replaces full rollout orchestration when per-sample customization is insufficient; its documented signature returns `RolloutFnTrainOutput` or `RolloutFnEvalOutput`. Source: `slime/utils/arguments.py` — `add_rollout_arguments()`; `slime/rollout/base_types.py` — `RolloutFnTrainOutput`, `RolloutFnEvalOutput`, `call_rollout_fn()`.

### Deployment and Reliability Controls

- slime documents SGLang Config for topology-specific serving control, PD disaggregation for workloads with different prefill/decode resource needs, router policies such as session affinity, delta weight sync, and external rollout engines.
- Engineering documentation covers CI, debugging, reproducibility, fault tolerance, trace viewing, and profiling.
- The README says the framework has been used behind GLM-5.2, GLM-5.1, GLM-5, GLM-4.7, GLM-4.6, and GLM-4.5 post-training loops.

---

## Technical Architecture

slime is organized around a Ray-managed training and rollout pipeline. `train.py` parses arguments, creates placement groups with `create_placement_groups(args)`, creates a remote `RolloutManager`, builds actor and optional critic model groups, updates rollout weights from the actor, then loops over rollout IDs: generate rollout data, train actor/critic, save as needed, refresh rollout weights, and evaluate. Source: `train.py` — `train()`; `slime/ray/placement_group.py` — `create_placement_groups()`, `create_rollout_manager()`, `create_training_models()`.

The placement layer computes actor and rollout GPU layout from flags such as `debug_train_only`, `rollout_external`, `debug_rollout_only`, and `colocate`, then builds packed Ray placement-group bundles and maps logical bundle indices to physical GPU IDs. Source: `slime/ray/placement_group.py` — `_get_placement_group_layout()`, `_create_placement_group()`.

The rollout layer is centered on `RolloutManager` and `ServerGroup`. `ServerGroup.start_engines()` creates Ray actors for `SGLangEngine`, assigns placement-group bundle indices and base GPU IDs, injects SGLang-related environment variables, and initializes engines by group. Source: `slime/ray/rollout.py` — `ServerGroup.start_engines()`.

Customization enters through function-path loading and typed rollout outputs. The default rollout function path is `slime.rollout.sglang_rollout.generate_rollout`; custom generation, reward, filtering, logging, conversion, loss, and data-source paths can be supplied through CLI arguments. `call_rollout_fn()` normalizes legacy outputs into `RolloutFnTrainOutput` or `RolloutFnEvalOutput`, keeping the train/eval contract explicit. Source: `slime/utils/arguments.py` — `add_rollout_arguments()`; `slime/rollout/base_types.py` — `call_rollout_fn()`.

---

## Installation & Usage

The upstream repository is designed for GPU clusters with Ray, Megatron-LM, and SGLang. The quick-start documentation is the authoritative setup path; the README points users to `docs/en/get_started/quick_start.md` for environment setup, data preparation, training startup, and code analysis.

```bash
# Clone the source repository
git clone https://github.com/THUDM/slime.git
cd slime

# Follow the upstream quick start for environment setup and data preparation.
# Example launch scripts live in scripts/, such as scripts/run-qwen3-4B.sh.
bash scripts/run-qwen3-4B.sh
```

Agentic customization typically starts by keeping the default rollout loop and injecting generation and reward functions:

```bash
python train.py \
  --custom-generate-function-path my_agent_rollout.generate \
  --custom-rm-path my_agent_rewards.score \
  --data-source-path my_tasks.load_data \
  --sglang-mem-fraction-static 0.8
```

The exact model, checkpoint, parallelism, data, and SGLang flags depend on the target model and cluster topology.

---

## Relevance to Claude Code Development

### Applications

- slime is a reference architecture for training coding agents or tool-using Claude Code-like agents with RL from sandbox/test rewards while preserving a high-performance training backend.
- Its examples and customization interfaces are directly relevant to research entries about coding-agent RL, multi-agent rollout, search/RAG rollouts, and long-tail asynchronous agent generation.
- The framework's debug rollout-then-train path and correctness-first positioning are useful patterns for any local agent evaluation or reinforcement-learning harness.

### Patterns Worth Adopting

- Treat rollout generation, reward/verifier computation, and training conversion as separate extension points instead of hard-coding a single agent workflow.
- Preserve native backend control surfaces where possible rather than hiding upstream engine features behind lowest-common-denominator abstractions.
- Use explicit train-only, rollout-only, trace, profiling, reproducibility, and fault-tolerance modes because RL failures can be silent even when jobs complete.
- Model asynchronous rollout as a first-class loop for long-tail agentic tasks, where some samples take much longer than others.

### Integration Opportunities

- Future Claude Code RL experiments could use slime-style `custom_generate` functions to run coding-agent trajectories and `custom_rm` functions to score test outcomes or verifier judgments.
- Research-curator entries about agentic RL systems can cross-reference slime when discussing the Megatron + SGLang substrate for scalable post-training.
- The repository's argument pass-through pattern suggests a design for local plugin tooling: expose underlying engine options directly and add only orchestration-specific flags.

---

## References

- [THUDM/slime GitHub repository](https://github.com/THUDM/slime) (accessed 2026-06-29)
- [slime README](https://github.com/THUDM/slime/blob/main/README.md) (accessed 2026-06-29)
- [Customization Guide](https://github.com/THUDM/slime/blob/main/docs/en/get_started/customization.md) (accessed 2026-06-29)
- [GitHub API: THUDM/slime repository metadata](https://api.github.com/repos/THUDM/slime) (accessed 2026-06-29)
- [GitHub API: THUDM/slime latest release](https://api.github.com/repos/THUDM/slime/releases/latest) (accessed 2026-06-29)
- [GitHub API: THUDM/slime contributors](https://api.github.com/repos/THUDM/slime/contributors?per_page=1&anon=true) (accessed 2026-06-29)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Ray](./ray.md) | ml-infrastructure | slime uses Ray actors and placement groups for distributed training and rollout orchestration. |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-06-29 |
| Version at Verification | v0.3.0 |
| Next Review Recommended | 2026-08-10 |
| Confidence Map | `Overview: high (docs); Problem Addressed: high (docs); Key Statistics: high (GitHub API); Key Features: medium (doc + code-read); Technical Architecture: medium (doc + code-read); Installation & Usage: medium (docs); Relevance: medium (inference from docs + code-read)` |
