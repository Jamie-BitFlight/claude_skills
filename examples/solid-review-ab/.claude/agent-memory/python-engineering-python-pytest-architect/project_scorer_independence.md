---
name: project-scorer-independence
description: solid-review-ab scorer independence test patterns — how to route through compute_metrics vs score_arm_a/b, E1 ablation sign, normalize_location edge cases
metadata:
  type: project
---

Independence test file: `examples/solid-review-ab/tests/test_scorer_independent.py`

**Why:** Scorer author also wrote original tests — tests proved code-test agreement, not correctness.

**Architecture of independence tests:**
- Route pure-math tests (P/R/F1 parametrize, decoy rate, empty-set guard) directly through `compute_metrics(reported, gold_positives, gold_decoys)` — takes pre-normalised sets, no file I/O noise
- Route file-parse tests through `score_arm_a(tmp_path/file, ...)` to cover the full stack
- Route E1 ablation through `score_arm_b(tmp_path, ...)` with worker files named `worker-1.md`, `worker-2.md` (stem.rsplit["-",1](-1) gives worker_id "1"/"2"; colliding ids collapse corroboration)

**E1 ablation sign:** If the lone weight-1 finding is a TRUE POSITIVE, threshold=2 DROPS it → recall falls → F1 goes DOWN (f1_delta negative). Gate only raises F1 if lone finding was FP/decoy.

**normalize_location edge cases:**
- Leading `/` stripped only for path+line form: `/path/file.py:12` → `path/file.py:12` — abs == relative
- No-line input (bare path): regex finds no match → raw.strip() returned unmodified — do NOT test slash stripping on bare paths
- Same basename in different dirs stays distinct: `src/foo/config.py:10` != `tests/foo/config.py:10`
- `slug_headings` keyword (default `False`): opt-in heading-slug normalization for `path:heading`
  locations, used only by the DH workflow-extraction pipeline. The scorer calls positionally, so it
  always gets the legacy default — heading-style inputs return `raw.strip()` unchanged. Locked by
  `test_normalize_location_heading_style_returns_stripped_unchanged` in test_scorer.py.

**RUF069:** Float equality comparisons to 0.0 must use `pytest.approx(0.0, abs=1e-9)` not `== 0.0`. Rule fires in preview mode but pyproject.toml enables preview for tests in this repo.

**coverage warnings:** Running isolated test file via `uv run --with pytest` produces no-data-collected coverage warnings because the repo pyproject.toml configures --cov but these test files run code outside the coverage source path. Not an error.

**How to apply:** Use this pattern for any future scorer-adjacent independence test work in this experiment.
