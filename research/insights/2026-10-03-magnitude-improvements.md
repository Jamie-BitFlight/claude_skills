# Improvement Proposals: Magnitude

**Research entry**: ./research/llm-infrastructure/magnitude.md
**Generated**: 2026-10-03
**Patterns assessed**: 8
**Backlog items created**: 1 (issue: #4039)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 5

**Backlog note**: Improvement 1 is high confidence. The `dh` backlog duplicate check was unavailable (GraphQL not available), so the duplicate check ran through GitHub issue search and found none; the item was filed as #4039
---

## Improvement 1: Add a memory-fit sizing section to the llamafile skill

**Source pattern**: Magnitude entry, "Limitations and Caveats": "On dedicated-GPU systems (non-unified-memory), GPU memory and system RAM are not interchangeable; a machine with 64 GB system RAM and 8 GB GPU does not have 72 GB available for models." Also "Unified memory constraints" and "Context size trade-offs: Longer context windows increase memory demand". These are paired with the Discover hardware assessment (Problem Addressed table: "recommends models matched to hardware capabilities").
**Local system**: plugins/llamafile/skills/llamafile/SKILL.md
**Absence evidence**: `git grep -n -i -E "vram|unified memory|memory|--mlock|hardware" -- plugins/llamafile plugins/litellm` -> only 2 matches: README.md:18 ("optimal flags for your hardware", no sizing content) and SKILL.md:149 (the `--mlock` table row). `git grep -il "vram" -- plugins .claude/skills` -> 0 matches.
**Confidence**: High
**Impact**: Low
**Backlog**: #4039 (P2)

### Current state

SKILL.md's model table (lines 91-96) lists download sizes (~500MB to ~5GB) and a "Use Case" column. "Performance-Optimized Configuration" (lines 122-137) recommends `--n-gpu-layers 99` and `--ctx-size 4096`. Nowhere does it say how to decide whether a model fits the machine. It does not cover VRAM versus system RAM on discrete GPUs, the shared pool on Apple Silicon, or the memory cost of raising `--ctx-size`. The only memory-related content is the `--mlock` row. Pitfall 8 covers `--n-gpu-layers` on CPU-only systems but not oversubscribing VRAM. File: plugins/llamafile/skills/llamafile/SKILL.md.

### Target state

SKILL.md has a "Choosing a model that fits your hardware" section containing:

- the rule that discrete-GPU VRAM and system RAM are separate pools, not additive;
- the rule that on Apple Silicon the GPU shares the pool with macOS and other apps;
- the rule that a larger `--ctx-size` raises memory use and slows generation;
- a hardware-detection command for each platform that already appears in the skill (`nvidia-smi`, `rocm-smi`), with the Apple Silicon unified-memory case described in prose.

Pitfall list entry 9 covers model plus context exceeding VRAM, with the symptom and the fix (lower `--n-gpu-layers` or `--ctx-size`, or use a smaller quant).

### Measurable signal

`git grep -n -i -E "vram|unified memory" -- plugins/llamafile/skills/llamafile/SKILL.md` returns at least 3 matches. The "Common Pitfalls" list contains an entry about memory oversubscription.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Per-hardware kernel tuning as llamafile performance guidance (formerly a Relevance item, "Hardware-specific inference acceleration"; removed from the entry because no second repo path anchors it) | Low | The entry says only that this "could improve performance guidance". Magnitude tunes kernels inside its own engine, and llamafile exposes no equivalent knob beyond the flags SKILL.md already documents. No concrete observable target state is named. |
| Unified inference-service selection across llamafile and other engines (formerly a Relevance item, "Integration Opportunities"; removed from the entry because the only path matching its term, plugins/llamafile/skills/llamafile/SKILL.md, anchors another item) | Low | The entry gives no mechanism beyond "could extend the llamafile skill's abstraction". Raising confidence needs a defined set of engines and a decision criterion, for example comparing against research/llm-infrastructure/localai.md. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Local model serving / kernel tuning informing llamafile README | The entry now records this as "none — out of scope": kernel tuning lives inside Magnitude's engine and the README has no engine-internals surface. Earlier speculative wording had no observable target state and failed gap rule 3. |
| Dual OpenAI and Anthropic endpoint design | The entry itself says "Change: none". plugins/litellm/README.md already carries provider prefixes. |
| Model lifecycle (residency: download, load, unload) | The entry records an absence anchor: `model residency` and `residency` each return 0 matches over the root-anchored repo scope, and "Change: none — out of scope". The earlier litellm provider-prefix anchor asserted naming, not lifecycle, and was removed. |
| Agent integration through standard API | The entry itself says "Change: none" (now anchored to plugins/litellm/skills/litellm/SKILL.md:31). SKILL.md's "API Integration" section (OpenAI SDK, LiteLLM) already uses the standard-API approach. |
| On-demand load, first-response latency | SKILL.md's API Errors table has a "Timeout / Model loading slowly" row, and the `/health` wait loop covers readiness. |
